"""One print check for the SEEDED comb -- glyph/3/0/8/0/3 (Litolff p3, bar 49,
staff/3/0/8, the busy cell the one-head trace found never committing).

Draws the PRODUCTION functions' own byte-exact output -- `_cell_line_offset`
("orange") and `_trace_cell_local_lines` seeded from it ("seeded comb",
2026-10-01 fix) -- never a re-walked illustration (the manager's correction
of the FIRST 2026-10-01 crops, FINDINGS.md). A pixel-row frame control
(counts of ink per row, not "by eye") says which grid actually sits on the
printed lines.
"""
import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr import measure_extractor as me
from frame import render_page_matching_gather  # lane-2.48-recipe
from tools.omr.types import PageWithStaves

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recheck_2_48_seeded import ARM_RECORD, duck_staff, load_record, obs

OUT_DIR = REPO_ROOT / "out/print/2.48/seeded"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SUB = "glyph/3/0/8/0/3"
STAFF_KEY = "staff/3/0/8"
CELL_KEY = "cell/3/0/8/0"
PDF = (
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
    "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
    "1870--imslp984073.pdf"
)
DPI = 600


def main():
    rec = load_record(ARM_RECORD)
    page = render_page_matching_gather(PDF, 3, dpi=DPI)

    staff = duck_staff(rec, STAFF_KEY)
    pws = PageWithStaves(page=page, staves=[staff], barlines=[])

    cell_box = obs(rec, CELL_KEY, "cell_box")["value"]
    x0, _y0, x1, _y1 = (int(v) for v in cell_box)

    gb = obs(rec, SUB, "glyph_box")
    x_center = gb["detail"]["x_center_page"]
    y_center = gb["detail"]["y_center_page"]

    offset = me._cell_line_offset(pws, staff, x0, x1)
    orange_shift = offset[0] if offset is not None else 0
    print("orange (_cell_line_offset):", offset)

    seeded_paths = me._trace_cell_local_lines(
        pws, staff, x0, x1, seed_shift_px=float(orange_shift))
    print("seeded comb committed a move anywhere in the cell:",
         bool(seeded_paths is not None and
              np.ptp(np.array([p[0] for p in seeded_paths])
                     - np.array(staff.line_ys)) > 0.01))

    # ── crop ──────────────────────────────────────────────────────────────
    pad = 40
    cy0, cy1 = min(staff.line_ys) - pad, max(staff.line_ys) + pad
    cx0, cx1 = x0 - 20, x1 + 20
    crop = page.rgb[cy0:cy1, cx0:cx1].copy()
    scale = 4
    crop_big = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_NEAREST)

    def to_crop_xy(px, py):
        return int(round((px - cx0) * scale)), int(round((py - cy0) * scale))

    # orange: one rigid shift, drawn as 5 horizontal lines across the cell's
    # own x-range (ORANGE, BGR).
    for ny in staff.line_ys:
        y = ny + orange_shift
        x_a, y_a = to_crop_xy(x0, y)
        x_b, y_b = to_crop_xy(x1, y)
        cv2.line(crop_big, (x_a, y_a), (x_b, y_b), (0, 140, 255), 1)

    # seeded comb: the production array itself, column by column (GREEN).
    if seeded_paths is not None:
        for path in seeded_paths:
            pts = [to_crop_xy(x0 + i, float(y)) for i, y in enumerate(path)]
            for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
                cv2.line(crop_big, (xa, ya), (xb, yb), (0, 200, 0), 1)

    # the subject: a corner bracket on the exact head, not a margin tick.
    hx, hy = to_crop_xy(x_center, y_center)
    bracket = 18
    cv2.line(crop_big, (hx - bracket, hy), (hx - 4, hy), (255, 0, 255), 2)
    cv2.line(crop_big, (hx, hy - bracket), (hx, hy - 4), (255, 0, 255), 2)
    cv2.putText(crop_big, SUB, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
               (255, 0, 255), 1)

    out_path = OUT_DIR / "staff8_bar49_head1_seeded.png"
    cv2.imwrite(str(out_path), crop_big)
    print("wrote", out_path)

    # ── pixel-row frame control (not by eye) ────────────────────────────
    # Count ink per row in a clean vertical strip near the head but off its
    # own ink (CLEAU.md: "a control must be able to fail" -- also run a
    # deliberately-wrong +5px offset and confirm it reads LESS ink).
    strip_x0, strip_x1 = int(x_center) + 30, int(x_center) + 45
    band_lo = min(staff.line_ys) - 10
    band_hi = max(staff.line_ys) + 10
    row_ink = (page.binary[band_lo:band_hi, strip_x0:strip_x1] == 0).sum(axis=1)
    peaks = [band_lo + i for i, v in enumerate(row_ink) if v >= (strip_x1 - strip_x0) * 0.6]
    print(f"strip x=[{strip_x0},{strip_x1}) real ink-row peaks (>=60% covered):", peaks)
    print("orange predicts rows:", [y + orange_shift for y in staff.line_ys])
    if seeded_paths is not None:
        col = strip_x0 - x0
        col = max(0, min(len(seeded_paths[0]) - 1, col))
        print("seeded comb predicts rows at this x:",
             [round(float(p[col]), 1) for p in seeded_paths])

    broken = [y + orange_shift + 5 for y in staff.line_ys]
    broken_rows_hit = sum(1 for y in broken if band_lo <= int(round(y)) < band_hi
                          and row_ink[int(round(y)) - band_lo] >= (strip_x1 - strip_x0) * 0.6)
    real_rows_hit = sum(1 for y in [yy + orange_shift for yy in staff.line_ys]
                        if band_lo <= int(round(y)) < band_hi
                        and row_ink[int(round(y)) - band_lo] >= (strip_x1 - strip_x0) * 0.6)
    print(f"control: orange's own rows hit {real_rows_hit}/5 strips; "
         f"a deliberately broken +5px offset hits {broken_rows_hit}/5 -- "
         f"{'CAN FAIL (control is live)' if broken_rows_hit < real_rows_hit else 'DID NOT FAIL -- suspect'}")


if __name__ == "__main__":
    main()
