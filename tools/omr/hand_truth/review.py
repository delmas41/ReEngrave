"""Measure-by-measure side by side: the print beside LilyPond's engraving of Sean's labels (plan C6).

    python3 -m tools.omr.hand_truth.review build <page.json> --pdf <score> --musicxml <perfect-eyes.musicxml>
    python3 -m tools.omr.hand_truth.review serve <page.json>        # open it, mark each bar
    python3 -m tools.omr.hand_truth.session advance <page.json> --to verified

Sean 2026-10-08: *"send out a copy of the work to lilypond so that I could
visually check each measure side by side."* One row per printed BAR (a column
of the page: every staff, one measure): on the left the crop of the scan at the
page's own DPI, on the right LilyPond's engraving of the same bar from the
perfect-eyes MusicXML (``perfect_eyes``). Sean marks each row

    ok            the engraving is the print
    label wrong   a box is wrong — back to that cell
    reader wrong  the boxes are right and the reader misread them (a Phase 2 finding)

HOW A BAR IS FOUND IN THE FILE. The k-th printed bar of the page (reading
order, system by system) is the k-th measure of EVERY part, by ordinal — what
the print does, and what ``build_sidebyside.slice_measures`` does too. A part
whose measure count is not the page's bar count cannot be aligned that way (a
staff suppressed on one system leaves it short); it is SHOWN as "not aligned",
never guessed into place (rule 8). The last clef / key / time / divisions
before the bar are carried into each one-bar slice, or LilyPond would draw it
in treble, in C.

A REVIEW IS OF ONE SET OF LABELS. ``review.json`` records a hash of the page's
boxes; ``verified`` needs every bar ``ok`` AND that hash still current — a
label edited after the review makes the review stale.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from tools.omr.hand_truth import store
from tools.omr.hand_truth.store import PageTruth, Rect, StoreError

MARKS = ("ok", "label wrong", "reader wrong")
_ATTR_ORDER = ("divisions", "key", "time", "staves", "clef")  # as build_sidebyside carries them


def boxes_hash(page: PageTruth) -> str:
    rows = sorted((b.id, b.cls, tuple(round(v, 2) for v in b.rect), b.text or "") for b in page.boxes)
    return hashlib.sha256(json.dumps(rows).encode()).hexdigest()[:16]


def bar_columns(page: PageTruth) -> List[Dict]:
    """Printed bars in reading order: (system, measure) -> the union of its cells."""
    cols: Dict[Tuple[int, int], List[Rect]] = {}
    for c in page.cells:
        if c.kind == "measure" and c.system is not None and c.measure is not None:
            cols.setdefault((c.system, c.measure), []).append(c.rect)
    out = []
    for k, ((sy, m), rects) in enumerate(sorted(cols.items())):
        out.append({"bar": k + 1, "system": sy, "measure": m,
                    "rect": (min(r[0] for r in rects), min(r[1] for r in rects),
                             max(r[2] for r in rects), max(r[3] for r in rects))})
    return out


def slice_bar(xml_text: str, ordinal: int, n_bars: int) -> Tuple[Optional[str], List[str], List[str]]:
    """A score-partwise holding bar ``ordinal`` (1-based) of every ALIGNED part.

    Returns (xml or None, aligned part names, not-aligned part names).
    """
    root = ET.fromstring(xml_text)
    names = {sp.get("id"): (sp.findtext("part-name") or sp.get("id")) for sp in root.iter("score-part")}
    out = ET.Element("score-partwise", {"version": "3.1"})
    plist = ET.SubElement(out, "part-list")
    aligned, not_aligned = [], []
    for part in root.findall("part"):
        pid = part.get("id")
        measures = part.findall("measure")
        if len(measures) != n_bars:
            not_aligned.append(f"{names.get(pid, pid)} ({len(measures)} bars in the file, {n_bars} printed)")
            continue
        carried: Dict[str, ET.Element] = {}
        for m in measures[:ordinal - 1]:
            att = m.find("attributes")
            if att is not None:
                for child in att:
                    if child.tag in _ATTR_ORDER:
                        carried[child.tag] = child
        m = ET.fromstring(ET.tostring(measures[ordinal - 1]))
        att = m.find("attributes")
        have = {c.tag for c in att} if att is not None else set()
        need = [t for t in _ATTR_ORDER if t in carried and t not in have]
        if need:
            if att is None:
                att = ET.Element("attributes")
                m.insert(0, att)
            for i, t in enumerate(need):
                att.insert(i, ET.fromstring(ET.tostring(carried[t])))
        m.set("number", "1")
        src = next(sp for sp in root.iter("score-part") if sp.get("id") == pid)
        plist.append(ET.fromstring(ET.tostring(src)))
        ET.SubElement(out, "part", {"id": pid}).append(m)
        aligned.append(names.get(pid, pid))
    if not aligned:
        return None, aligned, not_aligned
    return ET.tostring(out, encoding="unicode"), aligned, not_aligned


def render_bar(xml_slice: str, work: Path, stem: str) -> Tuple[Optional[Path], str]:
    """musicxml2ly + lilypond -dcrop -> a PNG of one bar. (png or None, why)."""
    lily, m2l = shutil.which("lilypond"), shutil.which("musicxml2ly")
    if not lily or not m2l:
        return None, "lilypond / musicxml2ly not on PATH"
    work.mkdir(parents=True, exist_ok=True)
    xml_p, ly_p = work / f"{stem}.musicxml", work / f"{stem}.ly"
    xml_p.write_text(xml_slice)
    r = subprocess.run([m2l, "--output", str(ly_p), str(xml_p)], capture_output=True, text=True, timeout=120)
    if r.returncode or not ly_p.exists():
        return None, f"musicxml2ly failed: {r.stderr.strip()[-200:]}"
    r = subprocess.run([lily, "-dcrop", "-dresolution=150", "--png", "-o", str(work / stem), str(ly_p)],
                       capture_output=True, text=True, timeout=300)
    for cand in (work / f"{stem}.cropped.png", work / f"{stem}.png"):
        if cand.exists():
            return cand, ""
    return None, f"lilypond failed: {r.stderr.strip()[-200:]}"


def _png_b64(path: Path) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def build(page: PageTruth, page_rgb, xml_text: str, out_dir: Path) -> Dict:
    """Write ``bars.json`` + crops + renders for every printed bar of the page."""
    import cv2

    out_dir = Path(out_dir)
    (out_dir / "print").mkdir(parents=True, exist_ok=True)
    cols = bar_columns(page)
    rows = []
    for col in cols:
        x0, y0, x1, y1 = (int(round(v)) for v in col["rect"])
        crop = page_rgb[max(0, y0):y1, max(0, x0):x1]
        scale = min(1.0, 900.0 / max(1, crop.shape[0]))
        if scale < 1.0:
            crop = cv2.resize(crop, (max(1, int(crop.shape[1] * scale)), max(1, int(crop.shape[0] * scale))),
                              interpolation=cv2.INTER_AREA)
        pp = out_dir / "print" / f"bar{col['bar']:03d}.png"
        cv2.imwrite(str(pp), crop[..., ::-1] if crop.ndim == 3 else crop)
        sl, aligned, not_aligned = slice_bar(xml_text, col["bar"], len(cols))
        png, why = (None, "no part of the file aligns with this bar") if sl is None else \
            render_bar(sl, out_dir / "lily", f"bar{col['bar']:03d}")
        rows.append({**col, "print": str(pp.relative_to(out_dir)),
                     "lilypond": str(png.relative_to(out_dir)) if png else None,
                     "not_rendered_because": why or None,
                     "parts_aligned": aligned, "parts_not_aligned": not_aligned})
    bars = {"page": f"{page.edition}:{page.pdf_page_index}", "boxes_hash": boxes_hash(page), "bars": rows}
    (out_dir / "bars.json").write_text(json.dumps(bars, indent=1))
    return bars


def review_path(page_path: Path) -> Path:
    return Path(page_path).with_suffix(".review.json")


def load_review(page_path: Path) -> Dict:
    p = review_path(page_path)
    return json.loads(p.read_text()) if p.exists() else {"marks": {}}


def mark(page_path: Path, page: PageTruth, bar: int, value: str, note: str = "") -> Dict:
    if value not in MARKS:
        raise StoreError(f"a bar is marked one of {MARKS}, not {value!r}")
    rv = load_review(page_path)
    h = boxes_hash(page)
    if rv.get("boxes_hash") not in (None, h):
        rv = {"marks": {}}  # the labels changed since: the old review is of different boxes
    rv.update({"page": f"{page.edition}:{page.pdf_page_index}", "boxes_hash": h})
    rv["marks"][str(bar)] = {"mark": value, "note": note,
                             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    review_path(page_path).write_text(json.dumps(rv, indent=1, sort_keys=True))
    return rv


def verdict(page_path: Path, page: PageTruth) -> Dict:
    """Is every printed bar marked ok, on THESE labels?"""
    rv = load_review(page_path)
    n = len(bar_columns(page))
    marks = rv.get("marks", {})
    stale = rv.get("boxes_hash") is not None and rv.get("boxes_hash") != boxes_hash(page)
    not_ok = sorted(int(k) for k, v in marks.items() if v["mark"] != "ok")
    unmarked = [k for k in range(1, n + 1) if str(k) not in marks]
    return {"verified": bool(n) and not stale and not not_ok and not unmarked,
            "bars": n, "stale": stale, "not_ok": not_ok, "unmarked": unmarked}


def _page_html(review_dir: Path, bars: Dict, rv: Dict) -> str:
    rows = []
    for b in bars["bars"]:
        m = rv.get("marks", {}).get(str(b["bar"]), {})
        right = (f'<img src="data:image/png;base64,{_png_b64(review_dir / b["lilypond"])}">' if b["lilypond"]
                 else f'<p class="why">not rendered: {html.escape(b["not_rendered_because"] or "")}</p>')
        warn = ("<p class='why'>not aligned: " + html.escape("; ".join(b["parts_not_aligned"])) + "</p>"
                if b["parts_not_aligned"] else "")
        buttons = "".join(
            f'<button class="{"on" if m.get("mark") == v else ""}" onclick="mk({b["bar"]},\'{v}\')">{v}</button>'
            for v in MARKS)
        rows.append(f'<section id="bar{b["bar"]}"><h2>bar {b["bar"]} · system {b["system"]}, measure '
                    f'{b["measure"]}</h2><div class="pair"><img src="data:image/png;base64,'
                    f'{_png_b64(review_dir / b["print"])}">{right}</div>{warn}<div>{buttons}'
                    f'<input id="n{b["bar"]}" placeholder="note" value="{html.escape(m.get("note", ""))}"></div>'
                    "</section>")
    return ("<!doctype html><meta charset=utf-8><title>Bar review</title><style>"
            "body{font:15px system-ui;margin:16px;background:#fafafa}section{background:#fff;margin:0 0 16px;"
            "padding:12px;border:1px solid #ddd}.pair{display:flex;gap:16px;align-items:flex-start;overflow-x:auto}"
            ".pair img{max-height:600px}button{margin:6px 6px 0 0;padding:6px 12px}button.on{background:#1a7f37;"
            "color:#fff}.why{color:#b35900}input{margin-left:8px;width:40%}</style>"
            f"<h1>{html.escape(bars['page'])} — mark every bar</h1>" + "".join(rows) +
            "<script>async function mk(b,v){const n=document.getElementById('n'+b).value;"
            "const r=await fetch('/api/mark',{method:'POST',headers:{'content-type':'application/json'},"
            "body:JSON.stringify({bar:b,mark:v,note:n})});if(!r.ok){alert(await r.text());return}"
            "document.querySelectorAll('#bar'+b+' button').forEach(x=>x.classList.toggle('on',x.textContent==v))}"
            "</script>")


def create_app(page_path: Path, review_dir: Path):
    from fastapi import Body, FastAPI, HTTPException
    from fastapi.responses import HTMLResponse

    app = FastAPI(title="ReEngrave bar review")

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        bars = json.loads((Path(review_dir) / "bars.json").read_text())
        page = store.load(page_path)
        if bars["boxes_hash"] != boxes_hash(page):
            return ("<p>The labels changed after these renders were built. Re-run perfect_eyes and "
                    "<code>review build</code> first.</p>")
        return _page_html(Path(review_dir), bars, load_review(page_path))

    # The JSON body comes in through `Body(...)`, a default VALUE: this module's
    # annotations are postponed strings, and FastAPI cannot resolve a `Request`
    # imported inside this function from one.
    @app.post("/api/mark")
    def api_mark(d: Dict = Body(...)) -> Dict:
        try:
            rv = mark(page_path, store.load(page_path), int(d["bar"]), str(d["mark"]), str(d.get("note", "")))
        except (StoreError, KeyError, ValueError) as e:
            raise HTTPException(400, detail=str(e))
        return {"ok": True, "marked": len(rv["marks"])}

    return app


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("page")
    b.add_argument("--pdf", required=True)
    b.add_argument("--musicxml", required=True)
    b.add_argument("--out", type=Path)
    s = sub.add_parser("serve")
    s.add_argument("page")
    s.add_argument("--dir", type=Path)
    s.add_argument("--port", type=int, default=5051)
    a = ap.parse_args(list(argv) if argv is not None else None)
    page_path = Path(a.page)
    from tools.omr.hand_truth.session import SESSIONS_DIR

    head = store.load(page_path)
    # Crops and renders are REGENERABLE and large: they live in the session dir
    # (gitignored). Only Sean's marks (`<page>.review.json`) sit beside the page.
    default_dir = SESSIONS_DIR / f"{head.edition}-p{head.pdf_page_index}" / "review"
    if a.cmd == "build":
        from tools.omr.preprocessing import render_page

        page = store.load(page_path)
        img = render_page(Path(a.pdf), page.pdf_page_index, dpi=page.dpi)
        bars = build(page, img.rgb, Path(a.musicxml).read_text(), a.out or default_dir)
        print(json.dumps({"bars": len(bars["bars"]),
                          "rendered": sum(1 for r in bars["bars"] if r["lilypond"]),
                          "not_aligned": sum(1 for r in bars["bars"] if r["parts_not_aligned"])}, indent=1))
        return 0
    import uvicorn

    print(f"open http://127.0.0.1:{a.port}/")
    uvicorn.run(create_app(page_path, a.dir or default_dir), host="127.0.0.1", port=a.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
