"""lane-2.48-recipe (2026-10-01) -- a contact sheet of the SAME 15 clean
heads `frame_check.py` measured, for Sean and the manager to look at by
eye. NO new measurements: the frame comes from
`frame.render_page_matching_gather` (the one place this directory's
scripts get a page), the 15-head selection and dy values come straight
from `frame_check.notehead_check` (not recomputed), and the drawn
geometry (box, staff lines, step positions) comes straight off the
record's own stored values via `boundary_measure.py`'s own rows. This
script only crops, scales and draws -- it files no new row, computes no
new statistic.

Per tile (300x300, native ~100x100px crop at the head's own x/y, scaled
x3 nearest-neighbour so individual pixels are visible):
  - red, 1px at native scale: the detector's stored box (`box_page`)
  - red cross: the box's own centre (same (x0+x1)/2,(y0+y1)/2 frame_check
    used for dx/dy)
  - green, partial alpha: the five staff lines at today's per-cell shift
    (`nominal_ys[i] + orange_shift`), extended at the SAME spacing beyond
    the real 5 whenever the crop window reaches that far (this IS the
    ledger-line extension, not a separate mechanism -- the same formula
    that places the real lines also places a ledger line at |k|>4)
  - blue ticks, right edge: every line-or-space STEP (half-step increments
    of the same grid), not just the 5 real lines
  - label: subject id, today's recorded position (`today_pos`), and
    frame_check's own dy for that head

Legend strip at top names the three colours. Before writing the PNG, this
script verifies by PIXEL ROW (not by eye) that the drawn green line rows
land on real ink for 3 tiles, and prints the per-line ink-coverage numbers
it found.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import cv2

import boundary_measure as bm
import frame_check as fc
from frame import render_page_matching_gather

OUT_PATH = REPO_ROOT / "out" / "print" / "2.48" / "recipe" / "clean_heads_sheet.png"

NATIVE = 100       # native-px crop window (square) around the head
SCALE = 3          # nearest-neighbour upscale
TILE_IMG = NATIVE * SCALE          # 300
TEXT_H = 50                        # label band under each tile, at tile scale
TILE_W, TILE_H = TILE_IMG, TILE_IMG + TEXT_H
COLS, ROWS = 5, 3
PAD = 6
LEGEND_H = 46

RED = (60, 60, 230)     # BGR
GREEN = (60, 200, 60)
BLUE = (230, 140, 60)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)


def line_y(top_y, half_step, k):
    return top_y + k * half_step


def draw_tile(rgb_page, binary_page, row, dy):
    sub = row["sub"]
    box = row["box_page"]
    x0, y0, x1, y1 = (float(v) for v in box)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    spacing_px = row["spacing_px"]
    half_step = spacing_px / 2.0
    top_y = row["nominal_ys"][0] + row["orange_shift"]
    today_pos = row["today_pos"]

    wx0 = int(round(cx)) - NATIVE // 2
    wy0 = int(round(cy)) - NATIVE // 2
    wx1, wy1 = wx0 + NATIVE, wy0 + NATIVE

    # crop (clamped to the page, padded with paper/white if it runs off)
    canvas = np.full((NATIVE, NATIVE, 3), 255, dtype=np.uint8)
    px0, py0 = max(0, wx0), max(0, wy0)
    px1, py1 = min(rgb_page.shape[1], wx1), min(rgb_page.shape[0], wy1)
    if px1 > px0 and py1 > py0:
        canvas[py0 - wy0:py1 - wy0, px0 - wx0:px1 - wx0] = rgb_page[py0:py1, px0:px1]

    big = cv2.resize(canvas, (TILE_IMG, TILE_IMG), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return int(round((px - wx0) * SCALE)), int(round((py - wy0) * SCALE))

    overlay = big.copy()

    # --- green staff/ledger lines, same grid formula at every k in view ---
    k_lo = int(np.floor((wy0 - top_y) / half_step)) - 1
    k_hi = int(np.ceil((wy1 - top_y) / half_step)) + 1
    drawn_lines = []  # (k, y_native) for the verification step
    for k in range(k_lo, k_hi + 1):
        if k % 2 != 0:
            continue  # lines only on even steps; odd steps are spaces (blue ticks only)
        y = line_y(top_y, half_step, k)
        if y < wy0 - 2 or y > wy1 + 2:
            continue
        _, by = to_big(wx0, y)
        cv2.line(overlay, (0, by), (TILE_IMG, by), GREEN, 1)
        drawn_lines.append((k, y))
    big = cv2.addWeighted(overlay, 0.45, big, 0.55, 0)

    # --- blue step ruler on the right edge: every integer k (line+space) ---
    for k in range(k_lo, k_hi + 1):
        y = line_y(top_y, half_step, k)
        if y < wy0 or y > wy1:
            continue
        _, by = to_big(wx0, y)
        cv2.line(big, (TILE_IMG - 14, by), (TILE_IMG - 1, by), BLUE, 2)

    # --- red detector box + centre cross, native 1px line ---
    bx0, by0 = to_big(x0, y0)
    bx1, by1 = to_big(x1, y1)
    cv2.rectangle(big, (bx0, by0), (bx1, by1), RED, max(1, SCALE // 3))
    ccx, ccy = to_big(cx, cy)
    r = 6
    cv2.line(big, (ccx - r, ccy), (ccx + r, ccy), RED, 2)
    cv2.line(big, (ccx, ccy - r), (ccx, ccy + r), RED, 2)

    # --- label band ---
    tile = np.full((TILE_H, TILE_W, 3), 255, dtype=np.uint8)
    tile[:TILE_IMG, :, :] = big
    label1 = sub
    label2 = f"pos={today_pos:+.2f}  dy={dy:+.2f}" if dy is not None else f"pos={today_pos:+.2f}  dy=n/a"
    cv2.putText(tile, label1, (4, TILE_IMG + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLACK, 1, cv2.LINE_AA)
    cv2.putText(tile, label2, (4, TILE_IMG + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLACK, 1, cv2.LINE_AA)
    return tile, drawn_lines, (wx0, wy0, wx1, wy1), cx


def verify_green_lines_on_ink(binary_page, row, drawn_lines, cx, label):
    """Pixel-row check (not by eye): for each on-staff green line (the real
    5, k in 0..8), sample a strip of columns around the head's own x and
    report the fraction of ink rows within +/-1px of the drawn y."""
    x_lo = max(0, int(round(cx)) - 20)
    x_hi = min(binary_page.shape[1], int(round(cx)) + 20)
    print(f"  pixel-row check for {label}:")
    all_ok = True
    for k, y in drawn_lines:
        if not (0 <= k <= 8):
            continue  # only the real 5 lines are expected to sit on ink here
        y_lo = max(0, int(round(y)) - 1)
        y_hi = min(binary_page.shape[0], int(round(y)) + 2)
        strip = binary_page[y_lo:y_hi, x_lo:x_hi] == 0  # True = ink
        coverage = float(strip.any(axis=0).mean())  # fraction of columns with ink in the +/-1px band
        ok = coverage >= 0.5
        all_ok = all_ok and ok
        print(f"    k={k:>2} y={y:7.2f} ink-column-coverage(+/-1px)={coverage:.2f} "
             f"{'OK' if ok else 'MISS'}")
    return all_ok


def main():
    rec = bm.load_record(bm.ARM_RECORD)["record"]
    pw = render_page_matching_gather(bm.PROVENANCE_PDF, bm.PAGE_IDX, dpi=bm.DPI)
    all_rows, _near = bm.main()
    row_by_sub = {r["sub"]: r for r in all_rows}

    # the SAME 15-head selection + dy frame_check.py already computed
    results = fc.notehead_check(pw.binary, all_rows)  # [(sub, dx, dy), ...]
    dy_by_sub = {sub: dy for sub, _dx, dy in results}

    tiles = []
    verify_targets = []
    for sub, _dx, dy in results:
        row = row_by_sub.get(sub)
        if row is None or row.get("box_page") is None:
            continue
        tile, drawn_lines, window, cx = draw_tile(pw.rgb, pw.binary, row, dy)
        tiles.append(tile)
        verify_targets.append((sub, drawn_lines, cx))

    # --- legend strip ---
    sheet_w = COLS * TILE_W + (COLS + 1) * PAD
    sheet_h = LEGEND_H + ROWS * TILE_H + (ROWS + 1) * PAD
    sheet = np.full((sheet_h, sheet_w, 3), 255, dtype=np.uint8)
    cv2.putText(sheet, "red = detector box", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 2, cv2.LINE_AA)
    cv2.putText(sheet, "green = staff lines from the record", (220, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2, cv2.LINE_AA)
    cv2.putText(sheet, "blue ticks = line/space steps", (560, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLUE, 2, cv2.LINE_AA)
    cv2.putText(sheet, "lane-2.48-recipe 2026-10-01 -- Litolff p3, 600dpi, same 15 heads as frame_check.py",
               (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.42, BLACK, 1, cv2.LINE_AA)

    for i, tile in enumerate(tiles):
        r, c = divmod(i, COLS)
        y = LEGEND_H + PAD + r * (TILE_H + PAD)
        x = PAD + c * (TILE_W + PAD)
        sheet[y:y + TILE_H, x:x + TILE_W] = tile

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), sheet)
    print(f"wrote {OUT_PATH} ({len(tiles)} tiles)")

    # --- verification: 3 tiles, by pixel row, not by eye ---
    print()
    print("=== pixel-row verification of drawn green lines (3 tiles) ===")
    picks = [0, len(verify_targets) // 2, len(verify_targets) - 1]
    all_pass = True
    for i in picks:
        sub, drawn_lines, cx = verify_targets[i]
        ok = verify_green_lines_on_ink(pw.binary, row_by_sub[sub], drawn_lines, cx, sub)
        all_pass = all_pass and ok
    print(f"ALL 3 CHECKED TILES {'PASS' if all_pass else 'DO NOT ALL PASS'} "
         f"(every real staff-line row >=50% ink-covered within +/-1px)")


if __name__ == "__main__":
    main()
