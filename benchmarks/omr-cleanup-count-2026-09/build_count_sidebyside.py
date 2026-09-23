"""Build the three count-page side-by-sides for Sean's OWN cleanup count
(ROADMAP.md 1.4, CLAUDE.md Sec.6a) — one self-contained HTML per acceptance
document, the print beside our output, one PRINTED SYSTEM per row, at a
resolution a human can read accidentals at.

    python3 benchmarks/omr-cleanup-count-2026-09/build_count_sidebyside.py

Reuses, does not reinvent:
  - `system_bands` / `crop_system` from `build_sidebyside.py` — the crop is
    cut from the SAME page raster the pipeline itself read (aligned to the
    record's own pixel coordinates), not a fresh guess at a DPI.
  - `slice_measures` / `render_svg` from `build_sidebyside.py` — the same
    attribute-carry-forward slice (a system that is not a part's first often
    opens with no clef/key/divisions at all; the slice injects the last-seen
    ones so the excerpt renders correctly).
  - `tools.omr.preprocessing.render_page` (READ-ONLY call — never edited)
    for the two scans, at the GATHER'S OWN dpi (600, from manifest.json),
    matching CLAUDE.md's "a print check is a crop with a ruler, cut from the
    PDF at the gather's own DPI".
  - `tools.omr.staged.record_io.load_record` (the one way to read a record
    file) to get the printed-system pixel bands.
  - `tools.library.score_library.library_root()` so this runs unmodified
    from a worktree.

Does NOT gather (the whole-movement records already exist and a re-gather is
hours). Does NOT touch anything under tools/. Reads the freshest exported
MusicXML already sitting in `benchmarks/acceptance/out/<doc>/<doc>.musicxml`
(written by the last `python3 -m tools.omr.acceptance` run) rather than
re-exporting.

The engraved document's "print" is not a scan — it IS a Verovio rendering of
the exact page truth (CLAUDE.md Sec.6a), already sitting at native
resolution (2500x4322 @300dpi, this document's own gather dpi) in
`benchmarks/omr-staged-engraved-2026-09/out/fixture/`. That asset is reused
byte-for-byte rather than re-derived from the fixture PDF at a possibly
different rounding.

Per-system bar ranges are HARDCODED below rather than parsed from
`works.json`'s prose `established_by` field, because that field is English
text written for a human, not a machine format, and this script serves
exactly three fixed, already-verified rows (works.json marks each
`confidence: "verified"`, Sean 2026-09-04/05). A change to any of the three
count pages is a ROADMAP decision, not a parsing bug here.
"""
from __future__ import annotations

import base64
import html
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import build_sidebyside as SBS  # system_bands, crop_system, slice_measures, render_svg
from tools.omr import preprocessing
from tools.omr.staged.record_io import load_record
import tools.library.score_library as sl

OUT_DIR = HERE / "out"
LIB = sl.library_root()
TODAY = "2026-09-23"

# ── the three documents, hardcoded per the verified works.json rows / the
#    engraved fixture's own known bar range (manifest.json) ────────────────

DOCS = [
    {
        "id": "beethoven5-litolff",
        "page_tag": "p3",
        "title": "Beethoven 5 mvt 1, Litolff 984073 (scan, bitonal, MERGING plate) "
                 "— pdf page index 3",
        "kind": "scan",
        "pdf": LIB / "editions/beethoven/symphony-5-op67/"
                     "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "record": LIB / "_shared-records/beethoven5-litolff-mvt1-whole-20260923.record.json",
        "xml": ROOT / "benchmarks/acceptance/out/beethoven5-litolff/beethoven5-litolff.musicxml",
        "pdf_page_index": 3,
        "dpi": 600,
        "systems": [
            {"system": 0, "first_bar": 49, "last_bar": 64},
            {"system": 1, "first_bar": 65, "last_bar": 82},
        ],
        "works_row_id": "beethoven-sym5-mvt1-984073-p3",
    },
    {
        "id": "brahms1-breitkopf",
        "page_tag": "p2",
        "title": "Brahms 1 mvt 1, Breitkopf 317803 (scan, SHATTERING plate) "
                 "— pdf page index 1 (printed page 2)",
        "kind": "scan",
        "pdf": LIB / "editions/brahms/symphony-1-op68/"
                     "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
        "record": LIB / "_shared-records/brahms1-breitkopf-mvt1-whole-20260923.record.json",
        "xml": ROOT / "benchmarks/acceptance/out/brahms1-breitkopf/brahms1-breitkopf.musicxml",
        "pdf_page_index": 1,
        "dpi": 600,
        "systems": [
            {"system": 0, "first_bar": 8, "last_bar": 14},
            {"system": 1, "first_bar": 15, "last_bar": 22},
        ],
        "works_row_id": "brahms-sym1-mvt1-317803-p2",
    },
    {
        "id": "beethoven5-engraved",
        "page_tag": "p0",
        "title": "Beethoven 5 mvt 1 bars 1-24, Verovio render, 18 parts "
                 "(engraved, exact page truth) — pdf page index 0",
        "kind": "engraved",
        "pdf": None,   # the print is the pre-rendered fixture PNG below, not re-rendered
        "record": None,
        "xml": ROOT / "benchmarks/acceptance/out/beethoven5-engraved/beethoven5-engraved.musicxml",
        "print_png": ROOT / "benchmarks/omr-staged-engraved-2026-09/out/fixture/"
                            "beethoven-sym5-mvt1-m1-24-p1.png",
        "pdf_page_index": 0,
        "dpi": 300,
        "systems": [
            {"system": 0, "first_bar": 1, "last_bar": 7},
        ],
        "works_row_id": None,
    },
]

CSS = """
:root{color-scheme:light}
body{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:#f6f5f2;color:#1a1a1a}
header{position:sticky;top:0;background:#fffdf8;border-bottom:2px solid #d8d2c4;
       padding:14px 22px;z-index:9}
h1{margin:0 0 4px;font-size:17px}
.sub{color:#5d5648;font-size:12.5px;line-height:1.5}
main{padding:18px 22px 120px;max-width:2100px}
section{background:#fff;border:1px solid #ddd7c9;border-radius:6px;margin:0 0 26px;
        overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.05)}
.head{display:flex;gap:18px;align-items:baseline;flex-wrap:wrap;
      padding:10px 14px;background:#f3efe4;border-bottom:1px solid #ddd7c9}
.head b{font-size:15px}
.pane{padding:10px 14px}
.lbl{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:#8a8272;
     margin:2px 0 6px}
.scan img{width:100%;border:1px solid #e4ded0;background:#fff}
.ours{overflow-x:auto;background:#fff;border:1px solid #e4ded0}
.ours svg{max-width:100%;height:auto;display:block}
.names{color:#6a6254;font-size:12.5px;margin-top:6px}
.msg{background:#fff8e6;border-left:3px solid #d9a441;padding:7px 11px;
      font-size:12.5px;margin:8px 0}
.msg.bad{background:#fdecec;border-left-color:#c0504d}
code{background:#f1ede2;padding:1px 4px;border-radius:3px;font-size:12px}
footer{padding:12px 22px;color:#8a8272;font-size:12px}
"""


def part_list(xml_text: str):
    root = ET.fromstring(xml_text)
    return [(sp.get("id"), sp.findtext("part-name") or sp.get("id"))
            for sp in root.findall(".//part-list/score-part")]


def build_doc(doc: dict) -> Path:
    xml_text = doc["xml"].read_text()
    parts = part_list(xml_text)  # [(id, name), ...] in score order

    if doc["kind"] == "scan":
        record = load_record(doc["record"])
        bands = SBS.system_bands(record)
        provenance = record.get("provenance") or {}
        page_img = preprocessing.render_page(doc["pdf"], doc["pdf_page_index"], dpi=doc["dpi"])
        commit_line = (f"record commit <code>{provenance.get('commit')}</code>, "
                       f"dirty=<code>{provenance.get('dirty')}</code>")
    else:
        bands = {}
        page_img = None
        commit_line = "no record — the print is the pre-rendered page-truth fixture PNG"

    parts_html = [
        '<meta charset="utf-8">',
        f"<style>{CSS}</style>",
        f"<header><h1>{html.escape(doc['title'])}</h1>",
        f"<div class='sub'>Built {TODAY} for Sean's own cleanup count "
        f"(ROADMAP.md 1.4, CLAUDE.md Sec.6a) — {commit_line}. "
        f"Fill <code>counts/{doc['id']}-{doc['page_tag']}-SEAN-{TODAY}.csv</code> "
        f"per <a href='../counts/HOW-TO-COUNT.md'>HOW-TO-COUNT.md</a>, "
        f"categories in <a href='../CATEGORIES.md'>CATEGORIES.md</a>.</div></header><main>",
    ]

    crops_dir = OUT_DIR / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)

    for sysdef in doc["systems"]:
        sysi = sysdef["system"]
        lo, hi = sysdef["first_bar"], sysdef["last_bar"]
        parts_html.append("<section>")
        parts_html.append(
            f"<div class='head'><b>System {sysi}</b>"
            f"<span>printed bars {lo}–{hi} ({hi - lo + 1} bars)</span></div>")
        parts_html.append("<div class='pane'>")

        # ── the print ────────────────────────────────────────────────
        parts_html.append("<div class='lbl'>the print"
                          + (f" &middot; {doc['dpi']} dpi, native (not downscaled)"
                             if doc["kind"] == "scan" else " &middot; page-truth render, "
                             f"{doc['dpi']} dpi, native") + "</div><div class='scan'>")
        if doc["kind"] == "scan":
            band = bands.get((doc["pdf_page_index"], sysi))
            if band is None:
                parts_html.append(
                    "<div class='msg bad'>no crop: the record carries no page-pixel "
                    "band for this system.</div>")
            else:
                name = f"{doc['id']}-p{doc['pdf_page_index']}-s{sysi}.png"
                px, size = SBS.crop_system(page_img.rgb, band, crops_dir / name)
                b64 = base64.b64encode((crops_dir / name).read_bytes()).decode()
                parts_html.append(
                    f"<a href='data:image/png;base64,{b64}' target='_blank' "
                    f"title='open full size ({size[0]}x{size[1]}px)'>"
                    f"<img src='data:image/png;base64,{b64}'></a>")
        else:
            b64 = base64.b64encode(doc["print_png"].read_bytes()).decode()
            parts_html.append(
                f"<a href='data:image/png;base64,{b64}' target='_blank' "
                f"title='open full size'><img src='data:image/png;base64,{b64}'></a>")
        parts_html.append("</div>")

        # ── ours ─────────────────────────────────────────────────────
        parts_html.append("<div class='lbl'>our output, the same bars</div><div class='ours'>")
        wanted = {pid: (lo, hi) for pid, _name in parts}
        try:
            import verovio
            tk = verovio.toolkit()
            tk.setOptions({"xmlIdSeed": 1})
            sliced = SBS.slice_measures(xml_text, wanted)
            n_bars = hi - lo + 1
            page_width = max(3200, n_bars * 260)
            svg = SBS.render_svg(tk, sliced, page_width)
            if not svg:
                raise RuntimeError("verovio returned no SVG")
            parts_html.append(svg)
        except Exception as exc:  # noqa: BLE001
            parts_html.append(
                f"<div class='msg bad'>Verovio could not render this slice: "
                f"{html.escape(f'{type(exc).__name__}: {exc}')} — falling back to the "
                f"MusicXML measures for bars {lo}-{hi} is in "
                f"<code>{doc['xml'].relative_to(ROOT)}</code>; do not fabricate a render.</div>")
        parts_html.append("</div>")

        names = ", ".join(f"{name}" for _pid, name in parts)
        parts_html.append(
            f"<div class='names'>staves, top to bottom (our file's own names): "
            f"{html.escape(names)} &mdash; bars {lo}–{hi}</div>")
        parts_html.append("</div></section>")

    parts_html.append("</main><footer>"
                      f"Generated by <code>benchmarks/omr-cleanup-count-2026-09/"
                      f"build_count_sidebyside.py</code>, {TODAY}. "
                      "Self-contained: the crops/SVG are embedded, not linked "
                      "(root .gitignore excludes benchmarks/**/crops/).</footer>")

    out_path = OUT_DIR / f"count-{doc['id']}-{doc['page_tag']}-{TODAY}.html"
    out_path.write_text("\n".join(parts_html))
    return out_path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for doc in DOCS:
        out_path = build_doc(doc)
        print(f"wrote {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
