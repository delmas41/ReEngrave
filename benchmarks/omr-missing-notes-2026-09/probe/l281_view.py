#!/usr/bin/env python3
"""l281_view: draw Sean's truth boxes over a cell (or a page rectangle) of the print, to
LOOK at what `l281_truth.py` derives. Diagnostic only; nothing here is evidence about the
reader. The render is `preprocessing.render_page`, the one the gather and the labeling
session share (hand_truth.score_crops docstring).

    python3 l281_view.py --cell s0-st3-m5 --out crop.png [--pdf PDF] [--cache p0.npy]
    python3 l281_view.py --rect x0,y0,x1,y1 --out crop.png
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_truth import Truth  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
       "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
COLORS = {"stem": (0, 120, 255), "notehead": (0, 170, 0), "beam": (255, 0, 255),
          "flag": (255, 0, 0), "augmentation_dot": (0, 200, 200), "tremolo": (200, 100, 0),
          "ledger_line": (150, 150, 150), "slur": (120, 120, 0), "tie": (120, 120, 0)}


def page_rgb(pdf, cache):
    if cache and Path(cache).exists():
        return np.load(cache)
    from tools.omr.preprocessing import render_page
    img = render_page(pdf, 0, dpi=600).rgb
    if cache:
        np.save(cache, img)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cell")
    ap.add_argument("--rect")
    ap.add_argument("--pdf", default=PDF)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=int, default=60)
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--no-boxes", action="store_true")
    ap.add_argument("--bracket", default=None, help="x0,y0,x1,y1 page px: a yellow corner bracket on the subject")
    a = ap.parse_args()
    T = Truth()
    img = page_rgb(a.pdf, a.cache)
    if a.cell:
        c = [c for c in T.page.cells if c.id == a.cell][0]
        x0, y0, x1, y1 = [int(v) for v in c.rect]
    else:
        x0, y0, x1, y1 = [int(float(v)) for v in a.rect.split(",")]
    P = a.pad
    ox, oy = max(0, x0 - P), max(0, y0 - P)
    crop = img[oy:y1 + P, ox:x1 + P].copy()
    if not a.no_boxes:
        for it in T.items:
            r = it.rect
            if r[2] < ox or r[0] > x1 + P or r[3] < oy or r[1] > y1 + P:
                continue
            fam = "stem" if it.cls == "stem" else it.family
            col = COLORS.get(fam)
            if col is None:
                continue
            cv2.rectangle(crop, (int(r[0] - ox), int(r[1] - oy)), (int(r[2] - ox), int(r[3] - oy)), col, 2)
    if a.bracket:
        bx0, by0, bx1, by1 = [float(v) for v in a.bracket.split(",")]
        bx0, bx1, by0, by1 = int(bx0 - ox), int(bx1 - ox), int(by0 - oy), int(by1 - oy)
        for (x, y, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
            cv2.line(crop, (x, y), (x + dx * 14, y), (230, 190, 0), 4)
            cv2.line(crop, (x, y), (x, y + dy * 14), (230, 190, 0), 4)
    if a.scale != 1.0:
        crop = cv2.resize(crop, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
    cv2.imwrite(a.out, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    print("wrote", a.out, crop.shape)


if __name__ == "__main__":
    main()
