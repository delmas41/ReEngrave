"""ROADMAP 2.50 -- a contact sheet of hollow heads for Sean, box centre vs
hole centre. NO new measurement: every value drawn comes straight off the
record's own rows (`Q.GLYPH_BOX`'s `bbox_page_px`/`x_center_page`/
`y_center_page`, `Q.STAFF_LINES`, `Q.HOLLOW_HEAD_CENTRE`); this script only
crops, scales and draws.

Per tile (300x300 at NATIVE=100, SCALE=3 -- the same scale as
`out/print/2.48/recipe/clean_heads_sheet.png`):
  - red box + red cross: the detector's own box and its centre
    (`bbox_page_px`, `(x_center_page, y_center_page)`)
  - magenta cross: `Q.HOLLOW_HEAD_CENTRE`'s own hole centroid, converted
    from the glyph's own canonical cell frame to page pixels via that
    SAME glyph's box_canon -> box_page affine (no second measurement)
  - green: the REAL 5 staff lines only (`Q.STAFF_LINES`), never extended
    past the staff
  - blue ticks (right edge): every line-or-space STEP within the crop,
    interpolated from the same 5 real lines (half their own spacing)
  - label: subject id, box-rounded vs hole-rounded staff position where
    they differ

Before writing the PNG, verifies by PIXEL ROW (not by eye) that the drawn
green line rows land on real ink, for 3 tiles, and prints the per-line
ink-coverage it found.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import cv2

from tools.omr.preprocessing import render_page
from tools.omr.staged import record_io
from tools.omr.staged.record import Q

RECORD_PATH = (REPO_ROOT / "benchmarks/acceptance/quick/out/beethoven5-litolff/"
              "beethoven5-litolff-p3.record.json")
PDF_PATH = (REPO_ROOT / "library/editions/beethoven/symphony-5-op67/"
           "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--"
           "imslp984073.pdf")
PAGE_INDEX = 3   # the Litolff count page (pdf index 3, CLAUDE.md sec.6a)
DPI = 600

OUT_PATH = REPO_ROOT / "out" / "print" / "2.50" / "hollow_head_centre_sheet.png"

NATIVE = 100
SCALE = 3
TILE_IMG = NATIVE * SCALE
TEXT_H = 50
TILE_W, TILE_H = TILE_IMG, TILE_IMG + TEXT_H
COLS, ROWS = 5, 3
N_TILES = COLS * ROWS
PAD = 6
LEGEND_H = 46

RED = (60, 60, 230)      # BGR
GREEN = (60, 200, 60)
BLUE = (230, 140, 60)
MAGENTA = (210, 60, 210)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)


def _cell_of(glyph_subject: str) -> str:
    parts = glyph_subject.split("/")
    return "cell/" + "/".join(parts[1:5])


def _staff_of(glyph_subject: str) -> str:
    parts = glyph_subject.split("/")
    return "staff/" + "/".join(parts[1:4])


def load_candidates():
    rec = record_io.load_record(str(RECORD_PATH))["record"]
    obs = rec["observations"]

    box_by_subject = {}
    for o in obs:
        if o["quantity"] == Q.GLYPH_BOX:
            det = o.get("detail") or {}
            bp = det.get("bbox_page_px")
            if bp is None:
                continue
            _, cx, cy, w, h = o["value"]
            box_by_subject[o["subject"]] = {
                "box_canon": (cx, cy, cx + w, cy + h),
                "box_page": tuple(float(v) for v in bp),
                "cx_page": float(det["x_center_page"]),
                "cy_page": float(det["y_center_page"]),
            }

    staff_lines_page = {}
    for o in obs:
        if o["quantity"] == Q.STAFF_LINES:
            staff_lines_page[o["subject"]] = [float(v) for v in o["value"]]

    pos_by_subject = {}
    for o in obs:
        if o["quantity"] == Q.NOTEHEAD_STAFF_POSITION:
            pos_by_subject[o["subject"]] = (o.get("detail") or {}).get("rounded")

    half_step_by_cell = {}
    for o in obs:
        if o["quantity"] == Q.CELL_STAFF_SPACE:
            det = o.get("detail") or {}
            if "half_step" in det:
                half_step_by_cell[o["subject"]] = float(det["half_step"])

    candidates = []
    changed_first = []
    for o in obs:
        if o["quantity"] != Q.HOLLOW_HEAD_CENTRE:
            continue
        sub = o["subject"]
        # ⚠️ CLAUDE.md sec.6a's own count page is PDF index 3 -- the record
        # also carries pages 1-2 (needed for the meter/key carry into the
        # count page, sec.6b), but this sheet renders ONE page image
        # (`PAGE_INDEX`), so it is restricted to glyphs filed on that same
        # page -- otherwise the drawn box/lines land on the wrong raster.
        if sub.split("/")[1] != str(PAGE_INDEX):
            continue
        box = box_by_subject.get(sub)
        staff_key = _staff_of(sub)
        lines = staff_lines_page.get(staff_key)
        if box is None or lines is None:
            continue
        hole_cx_canon, hole_cy_canon = o["value"]
        bx0, by0, bx1, by1 = box["box_canon"]
        pbx0, pby0, pbx1, pby1 = box["box_page"]
        sx = (pbx1 - pbx0) / (bx1 - bx0) if bx1 != bx0 else 1.0
        sy = (pby1 - pby0) / (by1 - by0) if by1 != by0 else 1.0
        hole_cx_page = pbx0 + (hole_cx_canon - bx0) * sx
        hole_cy_page = pby0 + (hole_cy_canon - by0) * sy

        half_step = half_step_by_cell.get(_cell_of(sub))
        rounded_box = pos_by_subject.get(sub)
        rounded_hole = None
        if half_step and rounded_box is not None:
            delta_canon = hole_cy_canon - (by0 + by1) / 2.0
            rounded_hole = int(round(rounded_box + delta_canon / half_step))

        entry = {
            "sub": sub,
            "box_page": box["box_page"],
            "box_centre_page": (box["cx_page"], box["cy_page"]),
            "hole_centre_page": (hole_cx_page, hole_cy_page),
            "staff_lines_page": lines,
            "rounded_box": rounded_box,
            "rounded_hole": rounded_hole,
        }
        candidates.append(entry)
        if rounded_hole is not None and rounded_hole != rounded_box:
            changed_first.append(entry)

    # Sean asked to include any whose rounded position changes -- put those
    # first, then fill the rest of the 15 with the remaining candidates.
    changed_keys = {e["sub"] for e in changed_first}
    rest = [e for e in candidates if e["sub"] not in changed_keys]
    selection = (changed_first + rest)[:N_TILES]
    return selection


def draw_tile(page_rgb, entry):
    bx0, by0, bx1, by1 = entry["box_page"]
    cx, cy = entry["box_centre_page"]
    hx, hy = entry["hole_centre_page"]
    lines = entry["staff_lines_page"]
    spacing = (lines[-1] - lines[0]) / (len(lines) - 1) if len(lines) > 1 else 40.0
    half_step = spacing / 2.0

    wx0 = int(round(cx)) - NATIVE // 2
    wy0 = int(round(cy)) - NATIVE // 2
    wx1, wy1 = wx0 + NATIVE, wy0 + NATIVE

    canvas = np.full((NATIVE, NATIVE, 3), 255, dtype=np.uint8)
    px0, py0 = max(0, wx0), max(0, wy0)
    px1, py1 = min(page_rgb.shape[1], wx1), min(page_rgb.shape[0], wy1)
    if px1 > px0 and py1 > py0:
        canvas[py0 - wy0:py1 - wy0, px0 - wx0:px1 - wx0] = page_rgb[py0:py1, px0:px1]
    big = cv2.resize(canvas, (TILE_IMG, TILE_IMG), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return int(round((px - wx0) * SCALE)), int(round((py - wy0) * SCALE))

    overlay = big.copy()
    drawn_lines = []
    for y in lines:   # ⚠️ the REAL 5 lines only -- never extended
        if y < wy0 - 2 or y > wy1 + 2:
            continue
        _, by = to_big(wx0, y)
        cv2.line(overlay, (0, by), (TILE_IMG, by), GREEN, 1)
        drawn_lines.append(y)
    big = cv2.addWeighted(overlay, 0.45, big, 0.55, 0)

    # blue step ticks: every half-step within the crop, from the same grid
    import math
    k_lo = int(math.floor((wy0 - lines[0]) / half_step)) - 1
    k_hi = int(math.ceil((wy1 - lines[0]) / half_step)) + 1
    for k in range(k_lo, k_hi + 1):
        y = lines[0] + k * half_step
        if y < wy0 or y > wy1:
            continue
        _, by = to_big(wx0, y)
        cv2.line(big, (TILE_IMG - 14, by), (TILE_IMG - 1, by), BLUE, 2)

    bx0b, by0b = to_big(bx0, by0)
    bx1b, by1b = to_big(bx1, by1)
    cv2.rectangle(big, (bx0b, by0b), (bx1b, by1b), RED, max(1, SCALE // 3))
    ccx, ccy = to_big(cx, cy)
    r = 6
    cv2.line(big, (ccx - r, ccy), (ccx + r, ccy), RED, 2)
    cv2.line(big, (ccx, ccy - r), (ccx, ccy + r), RED, 2)

    hcx, hcy = to_big(hx, hy)
    cv2.line(big, (hcx - r, hcy - r), (hcx + r, hcy + r), MAGENTA, 2)
    cv2.line(big, (hcx - r, hcy + r), (hcx + r, hcy - r), MAGENTA, 2)

    tile = np.full((TILE_H, TILE_W, 3), 255, dtype=np.uint8)
    tile[:TILE_IMG, :, :] = big
    label1 = entry["sub"]
    rb, rh = entry["rounded_box"], entry["rounded_hole"]
    label2 = f"box_pos={rb}  hole_pos={rh}" + ("  CHANGED" if rh != rb else "")
    cv2.putText(tile, label1, (4, TILE_IMG + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLACK, 1, cv2.LINE_AA)
    cv2.putText(tile, label2, (4, TILE_IMG + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.38, BLACK, 1, cv2.LINE_AA)
    return tile, drawn_lines, (wx0, wy0, wx1, wy1)


def verify_green_lines_on_ink(binary_page, drawn_lines, window, cx, label):
    wx0, wy0, wx1, wy1 = window
    x_lo = max(0, int(round(cx)) - 20)
    x_hi = min(binary_page.shape[1], int(round(cx)) + 20)
    print(f"  pixel-row check for {label}:")
    all_ok = True
    for y in drawn_lines:
        y_lo = max(0, int(round(y)) - 1)
        y_hi = min(binary_page.shape[0], int(round(y)) + 2)
        strip = binary_page[y_lo:y_hi, x_lo:x_hi] == 0
        coverage = float(strip.any(axis=0).mean())
        ok = coverage >= 0.5
        all_ok = all_ok and ok
        print(f"    y={y:7.2f} ink-column-coverage(+/-1px)={coverage:.2f} "
             f"{'OK' if ok else 'MISS'}")
    return all_ok


def main():
    selection = load_candidates()
    pw = render_page(str(PDF_PATH), PAGE_INDEX, dpi=DPI)

    tiles, verify_targets = [], []
    for entry in selection:
        tile, drawn_lines, window = draw_tile(pw.rgb, entry)
        tiles.append(tile)
        verify_targets.append((entry["sub"], drawn_lines, window,
                               entry["box_centre_page"][0]))

    sheet_w = COLS * TILE_W + (COLS + 1) * PAD
    sheet_h = LEGEND_H + ROWS * TILE_H + (ROWS + 1) * PAD
    sheet = np.full((sheet_h, sheet_w, 3), 255, dtype=np.uint8)
    cv2.putText(sheet, "red = detector box/centre", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 2, cv2.LINE_AA)
    cv2.putText(sheet, "magenta = hole centre", (310, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, MAGENTA, 2, cv2.LINE_AA)
    cv2.putText(sheet, "green = real staff lines", (560, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, GREEN, 2, cv2.LINE_AA)
    cv2.putText(sheet, "blue = half-step ticks", (820, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, BLUE, 2, cv2.LINE_AA)
    cv2.putText(sheet, "ROADMAP 2.50 -- Litolff p3, 600dpi, hollow-head hole centre vs box centre",
               (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.42, BLACK, 1, cv2.LINE_AA)

    for i, tile in enumerate(tiles):
        r, c = divmod(i, COLS)
        y = LEGEND_H + PAD + r * (TILE_H + PAD)
        x = PAD + c * (TILE_W + PAD)
        sheet[y:y + TILE_H, x:x + TILE_W] = tile

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), sheet)
    print(f"wrote {OUT_PATH} ({len(tiles)} tiles)")

    print()
    print("=== pixel-row verification of drawn green lines (3 tiles) ===")
    picks = [0, len(verify_targets) // 2, len(verify_targets) - 1]
    all_pass = True
    for i in picks:
        sub, drawn_lines, window, cx = verify_targets[i]
        ok = verify_green_lines_on_ink(pw.binary, drawn_lines, window, cx, sub)
        all_pass = all_pass and ok
    print(f"ALL 3 CHECKED TILES {'PASS' if all_pass else 'DO NOT ALL PASS'} "
         f"(every drawn staff-line row >=50% ink-covered within +/-1px)")


if __name__ == "__main__":
    main()
