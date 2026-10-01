"""2.48 PINNED-comb: one crop of ONE Litolff p3 staff across the WHOLE
system (ROADMAP 2.48, Sean's design #3). Orange (today's per-bar grid,
`_cell_line_offset` per cell) vs the pinned model drawn end to end, pins
marked with a tick, verified against real black-ink pixel rows at 3 CLEAN
columns (never by eye) -- rule 7 ("a control must be able to fail"). NO
re-gather: reuses the duck-typed-record recipe `recheck_2_48_seeded.py`
already uses (production functions called directly on a fresh
render+deskew of the committed arm record's own stored geometry).

Staff chosen: `staff/3/0/8` -- the bar-49 system every earlier 2.48 crop in
this benchmark has already examined (FINDINGS.md, 2026-10-01), so this
crop's own verification lands on ground already measured a different way.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.omr import measure_extractor as me
from tools.omr.preprocessing import deskew, render_page
from tools.omr.types import PageWithStaves

from recheck_2_48_seeded import ARM_RECORD, duck_staff, load_record, obs

OUT_DIR = REPO_ROOT / "out/print/2.48/pinned"
OUT_DIR.mkdir(parents=True, exist_ok=True)

PDF = (
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
    "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
    "1870--imslp984073.pdf"
)
DPI = 600
STAFF_KEY = "staff/3/0/8"
PAGE_IDX = 3


def ink_row_centres(binary, x0, x1, band_lo, band_hi, min_cov=0.6):
    width = max(1, x1 - x0)
    row_ink = (binary[band_lo:band_hi, x0:x1] == 0).sum(axis=1)
    hit = row_ink >= min_cov * width
    centres = []
    i = 0
    while i < len(hit):
        if hit[i]:
            j = i
            while j < len(hit) and hit[j]:
                j += 1
            centres.append(band_lo + (i + j - 1) / 2.0)
            i = j
        else:
            i += 1
    return centres


def pick_clean_columns(binary, x0, x1, band_lo, band_hi, n=3, width=15):
    """The `n` column windows of least total ink in the row band, spread
    across the system (not clustered), scored by actual ink -- never by
    eye."""
    candidates = []
    for x in range(x0, x1 - width, 10):
        total = int((binary[band_lo:band_hi, x:x + width] == 0).sum())
        candidates.append((total, x))
    candidates.sort()
    picked = []
    min_gap = (x1 - x0) // (n * 2)
    for total, x in candidates:
        if all(abs(x - p) > min_gap for p in picked):
            picked.append(x)
        if len(picked) >= n:
            break
    return sorted(picked)


def main():
    rec = load_record(ARM_RECORD)
    staff = duck_staff(rec, STAFF_KEY)
    page = render_page(PDF, PAGE_IDX, dpi=DPI)
    rgb2, binary2, deg = deskew(page.rgb, page.binary)
    page.rgb, page.binary = rgb2, binary2
    pws = PageWithStaves(page=page, staves=[staff], barlines=[])

    sys_x0, sys_x1 = staff.x_start, staff.x_end
    nominal_ys = [float(y) for y in staff.line_ys]

    pinned = me._pinned_system_shifts(pws, staff, sys_x0, sys_x1)
    assert pinned is not None, "expected >=2 measurable pins on this staff"

    # Orange: per-cell `_cell_line_offset`, read for every cell on this
    # staff, drawn as a step function across the system (production's own
    # per-bar grid, never re-walked).
    cell_keys = sorted(
        {o["subject"] for o in rec["observations"]
         if o["quantity"] == "cell_box" and o["subject"].startswith(f"cell/{PAGE_IDX}/0/8/")},
        key=lambda s: int(s.split("/")[-1]))
    orange_segments = []
    for ck in cell_keys:
        box = obs(rec, ck, "cell_box")["value"]
        cx0, cx1 = int(box[0]), int(box[2])
        offset = me._cell_line_offset(pws, staff, cx0, cx1)
        shift = float(offset[0]) if offset is not None else 0.0
        orange_segments.append((cx0, cx1, shift))

    # Pin x positions, same formula `_pinned_system_shifts` uses.
    n_pins = me.PINNED_COMB_N_INTERIOR_PINS + 2
    pin_xs = [sys_x0 + (sys_x1 - sys_x0) * i / (n_pins - 1) for i in range(n_pins)]

    # ── crop, whole system ───────────────────────────────────────────────
    pad = 40
    cy0 = int(min(staff.line_ys) - pad)
    cy1 = int(max(staff.line_ys) + pad)
    cx0, cx1 = sys_x0 - 5, sys_x1 + 5
    scale = 0.5  # the system is wide (>2000px); shrink so the whole thing fits one image
    crop = page.rgb[cy0:cy1, cx0:cx1].copy()
    new_w, new_h = int(crop.shape[1] * scale), int(crop.shape[0] * scale)
    crop_small = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_AREA)
    top_margin = 70
    legend = np.full((top_margin, crop_small.shape[1], 3), 255, dtype=np.uint8)
    crop_out = np.vstack([legend, crop_small])

    def to_xy(px, py):
        return (int(round((px - cx0) * scale)),
               int(round((py - cy0) * scale)) + top_margin)

    # orange: a step function, one horizontal segment per cell
    for cx0_, cx1_, shift in orange_segments:
        for ny in staff.line_ys:
            y = ny + shift
            xa, ya = to_xy(cx0_, y)
            xb, yb = to_xy(cx1_, y)
            cv2.line(crop_out, (xa, ya), (xb, yb), (0, 140, 255), 1)

    # pinned model: production's own array, drawn continuously
    for ny in nominal_ys:
        pts = [to_xy(sys_x0 + i, ny + float(s)) for i, s in enumerate(pinned)]
        for (xa, ya), (xb, yb) in zip(pts[:-1], pts[1:]):
            cv2.line(crop_out, (xa, ya), (xb, yb), (160, 0, 200), 1)

    # pin ticks
    for px in pin_xs:
        tx, _ = to_xy(px, nominal_ys[0])
        cv2.line(crop_out, (tx, top_margin), (tx, top_margin + 10), (0, 0, 0), 2)

    y_txt = 16
    cv2.putText(crop_out, f"{STAFF_KEY}  page {PAGE_IDX}  whole system", (8, y_txt),
               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    y_txt += 18
    cv2.line(crop_out, (8, y_txt), (28, y_txt), (0, 140, 255), 2)
    cv2.putText(crop_out, "orange = today's per-cell grid", (32, y_txt + 4),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    y_txt += 18
    cv2.line(crop_out, (8, y_txt), (28, y_txt), (160, 0, 200), 2)
    cv2.putText(crop_out, "purple = pinned model (ticks = pins)", (32, y_txt + 4),
               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    out_path = OUT_DIR / f"{STAFF_KEY.replace('/', '_')}_whole_system.png"
    cv2.imwrite(str(out_path), crop_out)

    # ── pixel-row frame check at 3 clean columns (not by eye) ──────────
    band_lo = int(min(staff.line_ys) - 10)
    band_hi = int(max(staff.line_ys) + 10)
    clean_xs = pick_clean_columns(page.binary, sys_x0, sys_x1, band_lo, band_hi, n=3)
    print("crop:", out_path)
    print("pins at page-x:", [round(p, 1) for p in pin_xs])
    def shift_at(px):
        idx = max(0, min(pinned.shape[0] - 1, int(round(px)) - sys_x0))
        return float(pinned[idx])
    print("pinned shift at pins:", [round(shift_at(p), 2) for p in pin_xs])
    for cx in clean_xs:
        centres = ink_row_centres(page.binary, cx, cx + 15, band_lo, band_hi)
        col = cx - sys_x0
        orange_shift = next(s for (a, b, s) in orange_segments if a <= cx < b)
        orange_rows = [y + orange_shift for y in nominal_ys]
        pinned_rows = [y + float(pinned[col]) for y in nominal_ys]
        print(f"[x={cx}] real ink-row centres: {[round(c, 1) for c in centres]}")
        print(f"         orange predicts:      {[round(y, 1) for y in orange_rows]}")
        print(f"         pinned predicts:      {[round(y, 1) for y in pinned_rows]}")
        orange_hits = sum(1 for r in orange_rows if any(abs(r - c) <= 2.0 for c in centres))
        pinned_hits = sum(1 for r in pinned_rows if any(abs(r - c) <= 2.0 for c in centres))
        print(f"         orange hits {orange_hits}/5, pinned hits {pinned_hits}/5 (within 2px)")

    # Broken-state control: a deliberately wrong +5px offset must NOT hit --
    # the control can fail (rule 7).
    cx = clean_xs[0]
    col = cx - sys_x0
    broken_rows = [y + float(pinned[col]) + 5.0 for y in nominal_ys]
    centres = ink_row_centres(page.binary, cx, cx + 15, band_lo, band_hi)
    broken_hits = sum(1 for r in broken_rows if any(abs(r - c) <= 2.0 for c in centres))
    print(f"broken +5px control at x={cx}: hits {broken_hits}/5 (expect << 5)")


if __name__ == "__main__":
    main()
