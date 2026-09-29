"""ROADMAP 2.18 -- print crops of the top class (A: narrowed ONLY by strokes on
the FAR side of the head's own read stem) for Sean.

Reads the saved p1 record ONCE (`record_io.load_record`), `beams_mechanism.py`'s
output (which heads are class A, which strokes are which) and
`price_stem_side.py`'s output (the verdict before and after 2.18). Style after
`benchmarks/omr-owner-domain-2026-09/crop_losers_2_6b.py`: the FILED staff is a
shaded, labelled BAND with its lines drawn thick, the subject head is
bracketed thick red, a staff-space ruler runs down the left edge.

Overlays (all from the record, mapped canonical -> page by a least-squares fit
of the cell's own glyph boxes against their `bbox_page_px`):
  GREEN  the head's own read stem(s)
  BLUE   a stroke on the stem side (kept by 2.18)
  RED X  a stroke on the FAR side (dropped by 2.18)

⚠️ FRAME CONTROL FIRST, AND IT CAN FAIL: the filed staff's own `Q.STAFF_LINES`
must be darker than a half-space off them on the render, or the crop is
REFUSED (`crop_contested._frame_ok`'s precedent).

    python3 benchmarks/omr-missing-notes-2026-09/probe/crop_stem_side.py \\
        <record.json> <mech.json> <price.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

OUT_DIR = HERE.parent / "out" / "print"
DPI = 600

#: Chosen by hand from class A of the 104 heads EXPORT counts as
#: `duration_narrowed` -- spread over both systems and both stem directions,
#: and INCLUDING the two whose 2.18 reading my eye says is WRONG (a flag the
#: detector did not box, so the note falls to a quarter): a crop set that only
#: shows the wins is not evidence.
SUBJECTS = [
    "glyph/1/0/0/4/11", "glyph/1/0/3/4/2", "glyph/1/0/10/0/9",
    "glyph/1/1/3/1/27", "glyph/1/1/8/0/11", "glyph/1/1/9/3/1",
    "glyph/1/1/3/3/2", "glyph/1/1/8/0/9",
]


def _frame_ok(arr, line_ys, spacing, *, margin=8.0):
    a = arr if arr.ndim == 2 else arr.mean(axis=2)
    h, w = a.shape
    x0, x1 = int(w * 0.15), int(w * 0.85)
    on, off = [], []
    half = max(1, int(round(spacing / 2.0)))
    for y in line_ys:
        y = int(round(y))
        if not (half < y < h - half):
            continue
        on.append(a[y, x0:x1].mean())
        off.append((a[y - half, x0:x1].mean() + a[y + half, x0:x1].mean()) / 2)
    if not on:
        return False, 0.0
    c = float(sum(off) / len(off) - sum(on) / len(on))
    return c >= margin, c


def _beats(v):
    if v is None:
        return "?"
    if v.get("outcome") != "decided":
        return v.get("outcome")
    return (v.get("value") or {}).get("beats")


def main() -> int:
    import fitz
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    from tools.omr.staged.record import Kind, Q, READERS, Subject
    from tools.omr.staged.record_io import load_record

    rec_path, mech_path, price_path = sys.argv[1:4]
    doc = load_record(rec_path)
    rec = doc["record"]
    mech = {h["subject"]: h for h in json.loads(Path(mech_path).read_text())}
    price = json.loads(Path(price_path).read_text())
    after = {c["subject"]: c["after"] for c in price["on"]["changed"]}
    before = {v["subject"]: v for v in rec["verdicts"]
              if v["quantity"] == Q.DURATION}
    pdf = doc["provenance"]["settings"]["args"]["pdf"]

    by_cell, lines_of, spacing_of = {}, {}, {}
    for o in rec["observations"]:
        sub = Subject.from_key(o["subject"])
        if o["quantity"] == Q.STAFF_LINES and sub.kind is Kind.STAFF:
            lines_of[o["subject"]] = [float(y) for y in o["value"]]
        elif o["quantity"] == Q.STAFF_SPACING and sub.kind is Kind.STAFF:
            spacing_of[o["subject"]] = float(o["value"])
        c = sub.at(Kind.CELL)
        if c is not None:
            by_cell.setdefault(c.to_key(), []).append(o)

    def fit(ck):
        xs, ys = [], []
        for o in by_cell[ck]:
            d = o.get("detail") or {}
            if o["quantity"] == Q.GLYPH_BOX and "bbox_page_px" in d:
                _, x, y, w, h = o["value"]
                px0, py0, px1, py1 = d["bbox_page_px"]
                xs += [(x, px0), (x + w, px1)]
                ys += [(y, py0), (y + h, py1)]
        ax = np.polyfit([a for a, _ in xs], [b for _, b in xs], 1)
        ay = np.polyfit([a for a, _ in ys], [b for _, b in ys], 1)
        return lambda x, y: (ax[0] * x + ax[1], ay[0] * y + ay[1])

    pm = fitz.open(pdf)[1].get_pixmap(dpi=DPI)
    page = (Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
            if pm.n >= 3 else
            Image.frombytes("L", (pm.width, pm.height), pm.samples)
            .convert("RGB"))
    arr = np.asarray(page.convert("L"), dtype=float)
    font = ImageFont.load_default(size=20)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest, refused = [], []

    for n, s in enumerate(SUBJECTS, 1):
        h = mech[s]
        sub = Subject.from_key(s)
        staff = sub.at(Kind.STAFF).to_key()
        ck = sub.at(Kind.CELL).to_key()
        lines = lines_of[staff]
        sp = spacing_of.get(staff, 27.0)
        ok, contrast = _frame_ok(arr, lines, sp)
        if not ok:
            refused.append({"subject": s, "why": f"FRAME CONTROL {contrast:.1f}"})
            continue
        P = fit(ck)
        box = [o for o in by_cell[ck] if o["subject"] == s
               and o["quantity"] == Q.GLYPH_BOX][0]
        px0, py0, px1, py1 = box["detail"]["bbox_page_px"]
        ys = [py0, py1] + lines
        cx0 = int(max(0, px0 - 9 * sp))
        cx1 = int(min(page.width, px1 + 9 * sp))
        cy0 = int(max(0, min(ys) - 5 * sp))
        cy1 = int(min(page.height, max(ys) + 5 * sp))
        Z = 3
        crop = page.crop((cx0, cy0, cx1, cy1)).resize(
            ((cx1 - cx0) * Z, (cy1 - cy0) * Z), Image.LANCZOS)
        T = lambda x, y: ((x - cx0) * Z, (y - cy0) * Z)

        overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        big = ImageFont.load_default(size=max(30, int(sp * Z * 0.8)))
        rgb = (0, 170, 60)
        top, bot = T(0, min(lines))[1], T(0, max(lines))[1]
        od.rectangle([0, top, crop.width, bot], fill=rgb + (50,))
        for ly in lines:
            y = T(0, ly)[1]
            od.line([(0, y), (crop.width, y)], fill=rgb + (200,), width=4)
        label = f"{staff} (FILED staff)"
        tw = od.textlength(label, font=big)
        ty = top + (bot - top) / 2 - big.size / 2
        od.rectangle([30, ty - 4, 30 + tw + 12, ty + big.size + 6],
                     fill=(255, 255, 255, 220), outline=rgb + (255,), width=4)
        od.text((36, ty), label, fill=rgb + (255,), font=big)
        crop = Image.alpha_composite(crop.convert("RGBA"), overlay).convert("RGB")
        dr = ImageDraw.Draw(crop)

        # the head's own stems (GREEN) -- recovered from the cell's STEM rows
        # that overlap its canonical box, the same test `_stem_joined` uses
        hx, hy, hw, hh = h["head_box"]
        for o in by_cell[ck]:
            if o["quantity"] != Q.STEM or o["reader"] != READERS.CV_LINES:
                continue
            x, y, w, hgt = [float(t) for t in o["value"]]
            if x <= hx + hw and x + w >= hx and y <= hy + hh and y + hgt >= hy:
                a, b = T(*P(x, y)), T(*P(x + w, y + hgt))
                dr.rectangle([a, b], outline=(0, 160, 0), width=5)
        for f in h["strokes"]:
            x, y, w, hgt = f["box"]
            a, b = T(*P(x, y)), T(*P(x + w, y + hgt))
            if f["label"] == "wrong_side":
                dr.line([a, b], fill=(230, 0, 0), width=5)
                dr.line([(a[0], b[1]), (b[0], a[1])], fill=(230, 0, 0), width=5)
            else:
                dr.rectangle([a, b], outline=(0, 60, 230), width=4)

        bx0, by0 = T(px0, py0)
        bx1, by1 = T(px1, py1)
        arm = max(14, int((bx1 - bx0) * 0.5))
        for (ax_, ay_, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1),
                                   (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            dr.line([(ax_ - dx * 6, ay_ - dy * 6),
                     (ax_ + dx * arm, ay_ - dy * 6)], fill=(220, 0, 0), width=8)
            dr.line([(ax_ - dx * 6, ay_ - dy * 6),
                     (ax_ - dx * 6, ay_ + dy * arm)], fill=(220, 0, 0), width=8)
        step, y, k = sp * Z, T(0, min(lines))[1], 0
        while y < crop.height:
            dr.line([(2, y), (16 if k % 5 else 26, y)], fill=(0, 90, 200),
                    width=2)
            y += step
            k += 1

        b_ = before.get(s) or {}
        a_ = after.get(s)
        name = f"beams-2.18-{n:02d}.png"
        title = [
            (f"#{n:02d}  {s}  {h['head']}  stem {h['stem_direction']} "
             f"(read off its own stem)", (0, 0, 0)),
            (f"before 2.18: {b_.get('outcome')} {b_.get('reason')} levels "
             f"{h['certain']}..{h['possible']}   after 2.18: "
             f"{_beats(a_)} beats ({(a_ or {}).get('reason')})",
             (80, 0, 120)),
            ("GREEN box = its own read stem   BLUE = stroke on its stem side "
             "(kept)   RED X = stroke on the FAR side (dropped)",
             (0, 0, 0)),
            ("Q: printed value of the bracketed note? Is any RED-X stroke "
             "this note's beam?", (0, 0, 0)),
        ]
        band = 22 * (len(title) + 1)
        out = Image.new("RGB", (crop.width, crop.height + band), "white")
        out.paste(crop, (0, band))
        cd = ImageDraw.Draw(out)
        for i, (text, color) in enumerate(title):
            cd.text((6, 4 + i * 22), text, fill=color, font=font)
        out.save(OUT_DIR / name)
        manifest.append({
            "n": n, "file": name, "subject": s, "class": h["class"],
            "head": h["head"], "stem_direction": h["stem_direction"],
            "levels_before": [h["certain"], h["possible"]],
            "export_before": h["export_refusal"],
            "after_2_18": a_, "frame_contrast": round(contrast, 2),
            "page_box": [round(c, 1) for c in (px0, py0, px1, py1)],
            "strokes": [{k: f[k] for k in ("label", "certain", "reader",
                                            "dy_spaces")} for f in h["strokes"]],
            "question": ("printed value of the bracketed note; is any RED-X "
                         "(far-side) stroke this note's beam"),
            "VERDICT_none_yet": None,
        })
        print("wrote", name)
    (OUT_DIR / "beams-2.18-manifest.json").write_text(json.dumps({
        "roadmap_item": "2.18",
        "record": ("scratch base.record.json -- Breitkopf 317803 pdf p1, "
                   "gathered on 6309396a, dirty False, --no-surya --no-ocr "
                   "--no-roster; not committed (~24 MB), reproducible in ~85 s"),
        "dpi": DPI, "crops": manifest, "refused": refused}, indent=2))
    for r in refused:
        print("REFUSED", r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
