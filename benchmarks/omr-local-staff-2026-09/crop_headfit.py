"""3 crops for the headfit CONTROL FAILURE (lane-2.48-headfit, NO re-gather).

Draws BOTH candidate ideal-head boxes (`geometry.standard_head_box`) at
today's per-bar grid, the real staff lines (orange), the detector's own
box (red), and prints each candidate's ink-coverage score -- the same
numbers `headfit.py` computed -- so the overlap this lane's CONTROL (a)
measured is visible, not just tabulated.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.omr.preprocessing import deskew, render_page  # noqa: E402
from tools.omr.staged.geometry import standard_head_box  # noqa: E402

import boundary_measure as bm  # noqa: E402
import headfit as hf  # noqa: E402

OUT_DIR = REPO_ROOT / "out" / "print" / "2.48" / "headfit"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (subject, label) -- one clean-control near-tie, one merged-blob control
# that unexpectedly decided, one more clean-control miss.
SUBJECTS = [
    ("glyph/3/0/0/5/12", "control_a_near_tie"),
    ("glyph/3/0/9/2/6", "control_d_merged_decided"),
    ("glyph/3/0/0/0/15", "control_a_miss"),
]


def crop_one(row, binary, rgb, label, is_merged=False):
    if is_merged:
        lower, upper = hf.true_candidates(row["today_pos"])
    else:
        lower, upper = hf.true_candidates(row["today_pos"])
    top_y = row["nominal_ys"][0] + row["orange_shift"]
    half_step = row["spacing_px"] / 2.0
    true_lines = [row["nominal_ys"][i] + row["orange_shift"] for i in range(5)]
    thickness = hf.line_thickness_px(row["staff"], row["spacing_px"])
    half_th = max(1.0, thickness / 2.0 + 1.0)

    boxes = {}
    scores = {}
    for cand in (lower, upper):
        cy = top_y + cand * half_step
        x0, x1, y0, y1 = standard_head_box(row["x_center"], cy, row["spacing_px"])
        boxes[cand] = (x0, x1, y0, y1)
        scores[cand] = hf.box_ink_coverage(binary, x0, x1, y0, y1, true_lines, half_th)
    step, diff, wscore = hf.decide(scores)

    bbox = row["box_page"]
    pad = 40
    all_ys = list(true_lines)
    for (x0, x1, y0, y1) in boxes.values():
        all_ys.extend([y0, y1])
    if bbox:
        all_ys.extend([bbox[1], bbox[3]])
    cy0 = int(min(all_ys) - pad)
    cy1 = int(max(all_ys) + pad)
    cx0 = int(row["x0"]) - 15
    cx1 = int(row["x1"]) + 15 if row.get("x1") else int(row["x_center"]) + 60
    crop = rgb[cy0:cy1, cx0:cx1].copy()
    scale = max(3, int(round(640 / max(1, crop.shape[1]))) + 1)
    crop_big = cv2.resize(crop, (crop.shape[1] * scale, crop.shape[0] * scale),
                          interpolation=cv2.INTER_NEAREST)
    top_margin = 140
    legend = np.full((top_margin, crop_big.shape[1], 3), 255, dtype=np.uint8)
    crop_big = np.vstack([legend, crop_big])

    def to_xy(px, py):
        return (int(round((px - cx0) * scale)),
               int(round((py - cy0) * scale)) + top_margin)

    for ly in true_lines:
        xa, ya = to_xy(cx0, ly)
        xb, yb = to_xy(cx1, ly)
        cv2.line(crop_big, (xa, ya), (xb, yb), (0, 140, 255), 1)

    colors = {lower: (0, 200, 0), upper: (255, 0, 0)}  # green=lower, blue=upper
    for cand, (x0, x1, y0, y1) in boxes.items():
        pa = to_xy(x0, y0)
        pb = to_xy(x1, y1)
        cv2.rectangle(crop_big, pa, pb, colors[cand], 2)

    if bbox:
        ra, rb = to_xy(bbox[0], bbox[1]), to_xy(bbox[2], bbox[3])
        cv2.rectangle(crop_big, ra, rb, (0, 0, 255), 1)

    y_txt = 18
    cv2.putText(crop_big, f"{row['sub']}  ({label})", (8, y_txt),
               cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    y_txt += 18
    cv2.putText(crop_big,
               f"lower={lower} score={scores[lower]}  upper={upper} score={scores[upper]}",
               (8, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    y_txt += 16
    cv2.putText(crop_big, f"decide={step}  diff={diff}  margin=0.15 min_winner=0.30",
               (8, y_txt), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    y_txt += 18
    for color, lbl in (((0, 140, 255), "orange = today's real staff lines"),
                      ((0, 200, 0), f"green = lower candidate ({lower}) ideal head"),
                      ((255, 0, 0), f"blue = upper candidate ({upper}) ideal head"),
                      ((0, 0, 255), "red = detector's own box")):
        cv2.line(crop_big, (8, y_txt), (28, y_txt), color, 2)
        cv2.putText(crop_big, lbl, (32, y_txt + 4), cv2.FONT_HERSHEY_SIMPLEX,
                   0.34, (0, 0, 0), 1)
        y_txt += 15

    out_path = OUT_DIR / f"{row['sub'].replace('/', '_')}_{label}.png"
    cv2.imwrite(str(out_path), crop_big)
    print(f"wrote {out_path}  lower={lower}:{scores[lower]} upper={upper}:{scores[upper]} "
         f"decide={step}")
    return out_path


def main():
    all_rows, near = bm.main()
    by_sub = {r["sub"]: r for r in all_rows}

    pw = render_page(bm.PROVENANCE_PDF, bm.PAGE_IDX, dpi=bm.DPI)
    rgb2, binary2, _deg = deskew(pw.rgb, pw.binary)
    pw.rgb, pw.binary = rgb2, binary2

    full = bm.load_record(bm.ARM_RECORD)
    inner = full["record"]

    for sub, label in SUBJECTS:
        row = by_sub.get(sub)
        is_merged = False
        if row is None:
            row = hf.build_row_generic(inner, pw, sub)
            is_merged = True
            if row is None:
                print(f"SKIP {sub}: not found")
                continue
        crop_one(row, pw.binary, pw.rgb, label, is_merged=is_merged)


if __name__ == "__main__":
    main()
