"""LOOK AT THE INK. Renders the page exactly as the pipeline did and crops the
bar each suspect stands in, with a staff-line ruler drawn on it.

⚠️ This repo's own record is that counting never settled a question of this
shape and a single crop repeatedly did. Everything else in this directory only
says WHERE TO POINT THIS.

The render is `preprocessing.render_page` at the gather's own DPI, so the page
frame is the one `Q.GLYPH_BOX.detail.bbox_page_px` is filed in -- no rescaling,
no second convention. A mismatch would move every box and look like a reading
fault, which is the `Q.ONSET_COLUMN` frame error one family over.

What is drawn:
  * the five staff lines of THIS staff, from `Q.STAFF_LINES` (thin, grey)
  * a tick at staff step 5.5 -- where an engraver MUST hang a whole rest (blue)
  * the suspect's own detection box (red)
  * every other detection box in the bar (green)

    python3 .../crops.py --cache cache.json --trace trace.json --out-dir D \
        [--only P1:45] [--controls]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

PDF = ("library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")


def _page_image(pdf, page, dpi):
    from tools.omr.preprocessing import render_page
    pi = render_page(pdf, page, dpi=dpi)
    # ⚠️ `rgb` where it exists: the BINARY image is what the detector saw, but
    # a human adjudicating ink wants the grey the binariser threw away -- the
    # whole question here is whether a mark is a filled bar or a filled oval,
    # and binarisation is exactly the step that can turn one into the other.
    for attr in ("rgb", "binary"):
        a = getattr(pi, attr, None)
        if a is not None:
            return a
    raise SystemExit("render_page gave no image array -- schema changed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--trace", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pdf", default=str(ROOT / PDF))
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--only")
    ap.add_argument("--quarters-only", action="store_true")
    ap.add_argument("--pad-spaces", type=float, default=6.0)
    ap.add_argument("--target-px", type=float, default=280.0)
    a = ap.parse_args()

    import numpy as np
    from PIL import Image, ImageDraw

    cache = json.load(open(a.cache))
    boxes, lines, spacing, cells = {}, {}, {}, {}
    for o in cache["observations"]:
        q, s = o["quantity"], o["subject"]
        if q == "glyph_box":
            pb = (o.get("detail") or {}).get("bbox_page_px")
            if pb:
                boxes[s] = pb
        elif q == "staff_lines":
            lines[s] = o["value"]
        elif q == "staff_spacing":
            spacing[s] = o["value"]
        elif q == "cell_box":
            cells[s] = o["value"]

    rows = json.load(open(a.trace))
    if a.quarters_only:
        rows = [r for r in rows if r.get("lone_quarter_in_2_4")]
    if a.only:
        pid, m = a.only.split(":")
        rows = [r for r in rows if r["part"] == pid and r["measure"] == int(m)]
    rows = [r for r in rows if r.get("subject")]
    if not rows:
        print("NO ROWS TO CROP -- dead instrument", file=sys.stderr)
        return 2

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    by_page = {}
    for r in rows:
        by_page.setdefault(r["where"]["page"], []).append(r)

    made = 0
    for page, group in sorted(by_page.items()):
        img = _page_image(a.pdf, page, a.dpi)
        arr = np.asarray(img)
        if arr.ndim == 2:
            base = Image.fromarray(arr).convert("RGB")
        else:
            base = Image.fromarray(arr).convert("RGB")
        for r in group:
            w = r["where"]
            skey = "staff/%d/%d/%d" % (page, w["system"], w["staff"])
            ly, sp = lines.get(skey), spacing.get(skey)
            if not ly or not sp:
                continue
            pad = a.pad_spaces * sp
            # the BAR: every detection filed in this cell, unioned, or the
            # suspect's own box where the cell holds only it
            pre = "glyph/%d/%d/%d/%d/" % (page, w["system"], w["staff"], w["cell"])
            here = {s: b for s, b in boxes.items() if s.startswith(pre)}
            bb = boxes[r["subject"]]
            xs = [bb[0], bb[2]] + [v for b in here.values() for v in (b[0], b[2])]
            x0, x1 = min(xs) - pad, max(xs) + pad
            y0, y1 = min(ly) - pad, max(ly) + pad
            crop = base.crop((int(x0), int(y0), int(x1), int(y1)))
            scale = max(1, int(round(a.target_px / max(1.0, (y1 - y0)))))
            crop = crop.resize((crop.width * scale, crop.height * scale),
                               Image.NEAREST)
            d = ImageDraw.Draw(crop)

            def X(v):
                return (v - x0) * scale

            def Y(v):
                return (v - y0) * scale

            for y in ly:
                d.line([(0, Y(y)), (crop.width, Y(y))], fill=(120, 170, 255),
                       width=1)
            # step 5.5 -- where a whole rest hangs. bottom line is step 0.
            rest_y = max(ly) - 5.5 * (sp / 2.0)
            d.line([(0, Y(rest_y)), (crop.width, Y(rest_y))],
                   fill=(0, 120, 0), width=1)
            for s, b in here.items():
                if s == r["subject"]:
                    continue
                d.rectangle([X(b[0]), Y(b[1]), X(b[2]), Y(b[3])],
                            outline=(0, 200, 0), width=1)
            d.rectangle([X(bb[0]), Y(bb[1]), X(bb[2]), Y(bb[3])],
                        outline=(255, 0, 0), width=2)
            name = (f"{r['part']}-m{r['measure']}-p{page}s{w['system']}"
                    f"st{w['staff']}c{w['cell']}-{r['exported']}.png")
            crop.save(out / name)
            made += 1
            print(f"{name}  h={r.get('height_spaces')} asp={r.get('aspect')} "
                  f"step={r.get('staff_step')} conf={round(r['conf'], 3)} "
                  f"cls={r['cls']} glyphs_in_bar={len(here)}")
    print(f"\n{made} crops -> {out}")
    return 0 if made else 2


if __name__ == "__main__":
    raise SystemExit(main())
