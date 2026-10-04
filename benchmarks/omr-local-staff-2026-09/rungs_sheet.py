"""lane-ledger-sheet (2026-10-01) -- a second contact sheet, the SAME 15
heads `frame_check.py`/`clean_heads_sheet.py` used, for Sean and the
manager to look at.

Sean (DECISIONS 2026-10-01): "We need to treat ledger lines entirely
different from the staff lines... It can only be an ink read for the
lines." `clean_heads_sheet.py`'s green line draws the real 5 staff lines
AND extends them past the staff at the SAME flat spacing -- that extension
IS the extrapolation Sean ruled out. This script removes it for every head
OUTSIDE the staff (`today_pos` < 0 or > 8, i.e. off the real 5 lines) and
replaces it with `measure_ledger_rungs`'s (tools/omr/annotate/ledger_grid.py)
own ink read of that head's PRINTED ledgers, at the head's own x. Heads
INSIDE the staff are drawn exactly as `clean_heads_sheet.draw_tile` drew
them (reused unchanged) -- no ledger work applies there.

This script computes NO new staff-line geometry and no new box or
position: it reuses `boundary_measure.py`'s own rows (box, staff, spacing,
orange_shift, today_pos) and `frame_check.notehead_check`'s same 15-head
selection and dy, unchanged. The only new numbers it introduces:

  (1) the x-extent (left/right stub) of each rung `measure_ledger_rungs`
      found -- that function returns only a y per rung; the extent is
      read here, off the SAME already-thresholded ink, for drawing and
      for the pixel-row check below;
  (2) the "rungs" read, derived from those rungs by Sean's clean-count
      convention (DECISIONS 2026-09-30): count the CLEAN ledgers (no head
      on them) walking out from the staff edge, then call it a LINE (the
      head sits on/hides a rung) or a SPACE (the head sits beyond the
      last clean rung, no rung there) from the head's own y relative to
      that last clean rung.

Sean and the manager judge whether the resulting step is RIGHT -- this
script only draws it and checks, by pixel row, that every orange rung it
drew really sits on ink over its own x-extent. A reader crash or an empty
read is reported as "NO RUNGS", never invented (CLAUDE.md rule 8).
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import cv2

import boundary_measure as bm
import frame_check as fc
import clean_heads_sheet as chs
from frame import render_page_matching_gather
from tools.omr.annotate import ledger_grid as lg

# lane-ledger-rungs (2026-10-01): v2, drawn with the wide-gap/on-staff/
# stub fixes (DECISIONS 2026-10-01 a/b/c) applied to the SAME reader --
# the original rungs_sheet.png stays committed as the before-fix sheet.
OUT_PATH = REPO_ROOT / "out" / "print" / "ledgers" / "rungs_sheet_v2.png"

# --- reuse clean_heads_sheet's own layout/scale constants exactly ---
NATIVE = chs.NATIVE
SCALE = chs.SCALE
TILE_IMG = chs.TILE_IMG
TILE_W, TILE_H = chs.TILE_W, chs.TILE_H
COLS, ROWS = chs.COLS, chs.ROWS
PAD = chs.PAD
LEGEND_H = chs.LEGEND_H + 18  # one extra legend line for orange/marks

RED = chs.RED
GREEN = chs.GREEN
BLUE = chs.BLUE
WHITE = chs.WHITE
BLACK = chs.BLACK
ORANGE = (30, 140, 255)  # BGR -- distinct from the existing red/green/blue

# A head within this many position-units (half-steps) of a rung's own
# measured position is read as sitting ON that rung (the rung is hidden
# under the head) -- half of one full space, i.e. the usual line/space
# rounding window used everywhere else in this lane.
OCCUPIED_TOL_UNITS = 1.0


def _merge_runs(mask: np.ndarray, bridge: int) -> list[list[int]]:
    """Contiguous True runs in `mask`, merging gaps of False no wider than
    `bridge` -- the SAME bridging rule `ledger_grid._band_centers` uses for
    a rung broken by a hollow head's white counter."""
    runs: list[list[int]] = []
    n = len(mask)
    i = 0
    while i < n:
        if mask[i]:
            j = i
            while j < n and mask[j]:
                j += 1
            if runs and i - runs[-1][1] <= bridge:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    return runs


def rung_extent(binary_page: np.ndarray, y: float, x_probe: float, spacing: float):
    """The left/right stub of the rung measured at `y`, read off the SAME
    ink `measure_ledger_rungs` thresholded -- that function returns only a
    y per rung; this reads its x-extent for drawing and for the pixel
    check. Returns (x_left, x_right) in page px, or None if no run of ink
    covers the probe column there (should not happen for a rung
    `measure_ledger_rungs` itself reported, but a second independent read
    must be able to fail -- CLAUDE.md rule 7)."""
    h, w = binary_page.shape
    y_i = int(round(y))
    y0, y1 = max(0, y_i - 1), min(h, y_i + 2)
    if y1 <= y0:
        return None
    x_half = int(round(2.5 * spacing))
    x0 = max(0, int(round(x_probe)) - x_half)
    x1 = min(w, int(round(x_probe)) + x_half)
    if x1 <= x0:
        return None
    window = binary_page[y0:y1, x0:x1]
    thr = lg._otsu_threshold(window)
    ink_cols = (window <= thr).any(axis=0)
    bridge = int(round(lg.RUNG_BRIDGE_GAP_SPACES * spacing))
    runs = _merge_runs(ink_cols, bridge)
    if not runs:
        return None
    probe_col = int(round(x_probe)) - x0
    containing = [r for r in runs if r[0] <= probe_col < r[1]]
    if containing:
        r = containing[0]
    else:
        r = min(runs, key=lambda r: min(abs(r[0] - probe_col), abs(r[1] - 1 - probe_col)))
    return float(x0 + r[0]), float(x0 + r[1] - 1)


def classify_far_head(row: dict, binary_page: np.ndarray):
    """Reads the ledger rungs for one far head and derives Sean's
    clean-count step. Returns (side, rung_items, rungs_step, read_kind,
    crashed). `rungs_step` is None (label "NO RUNGS") when the reader
    found nothing or crashed -- never invented."""
    staff = row["staff"]
    spacing = row["spacing_px"]
    half_step = spacing / 2.0
    nominal_ys = row["nominal_ys"]
    shift = row["orange_shift"]
    top_y = nominal_ys[0] + shift
    bottom_y = nominal_ys[-1] + shift
    cx, cy = row["x_center"], row["y_center"]
    pos = row["today_pos"]

    if pos < 0:
        side, edge_y, sign = "above", top_y, -1.0
    else:
        side, edge_y, sign = "below", bottom_y, 1.0

    line_ys_abs = [ny + shift for ny in nominal_ys]

    crashed = False
    try:
        rungs_y = lg.measure_ledger_rungs(
            binary_page, line_ys_abs, cx, head_y=cy
        ).get(side, [])
    except Exception:
        traceback.print_exc()
        rungs_y = []
        crashed = True

    rung_items = []
    for i, ry in enumerate(rungs_y, start=1):
        dist_units = sign * (ry - edge_y) / half_step
        extent = rung_extent(binary_page, ry, cx, spacing)
        rung_items.append(dict(idx=i, y=float(ry), dist_units=dist_units,
                                extent=extent, occupied=False))

    if not rung_items:
        return side, rung_items, None, None, crashed

    head_dist_units = sign * (cy - edge_y) / half_step
    occ_idx = None
    for it in rung_items:
        if abs(it["dist_units"] - head_dist_units) <= OCCUPIED_TOL_UNITS:
            occ_idx = it["idx"]
            break

    if occ_idx is not None:
        for it in rung_items:
            it["occupied"] = (it["idx"] == occ_idx)
        rungs_step = sign * 2 * occ_idx
        read_kind = "line"
    else:
        clean_before = sum(1 for it in rung_items if it["dist_units"] < head_dist_units)
        rungs_step = sign * (2 * clean_before + 1)
        read_kind = "space"

    return side, rung_items, rungs_step, read_kind, crashed


def draw_tile_far(rgb_page, binary_page, row, dy, rung_items, rungs_step, read_kind, side):
    """Same crop/scale/red-box recipe as `clean_heads_sheet.draw_tile`, but
    the green staff-line draw stops at the real 5 lines (no extension) and
    the ledger rungs `classify_far_head` measured are drawn in orange at
    their own measured y AND x-extent, with a filled/hollow mark."""
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

    canvas = np.full((NATIVE, NATIVE, 3), 255, dtype=np.uint8)
    px0, py0 = max(0, wx0), max(0, wy0)
    px1, py1 = min(rgb_page.shape[1], wx1), min(rgb_page.shape[0], wy1)
    if px1 > px0 and py1 > py0:
        canvas[py0 - wy0:py1 - wy0, px0 - wx0:px1 - wx0] = rgb_page[py0:py1, px0:px1]

    big = cv2.resize(canvas, (TILE_IMG, TILE_IMG), interpolation=cv2.INTER_NEAREST)

    def to_big(px, py):
        return int(round((px - wx0) * SCALE)), int(round((py - wy0) * SCALE))

    # --- green: the REAL 5 staff lines only (k=0,2,4,6,8), never extended ---
    overlay = big.copy()
    for k in range(0, 9, 2):
        y = top_y + k * half_step
        if y < wy0 - 2 or y > wy1 + 2:
            continue
        _, by = to_big(wx0, y)
        cv2.line(overlay, (0, by), (TILE_IMG, by), GREEN, 1)
    big = cv2.addWeighted(overlay, 0.45, big, 0.55, 0)

    # --- blue step ruler: within the staff only (k=0..8), same reason ---
    for k in range(0, 9):
        y = top_y + k * half_step
        if y < wy0 or y > wy1:
            continue
        _, by = to_big(wx0, y)
        cv2.line(big, (TILE_IMG - 14, by), (TILE_IMG - 1, by), BLUE, 2)

    # --- orange: each measured ledger rung, at its own y and x-extent ---
    for it in rung_items:
        ry = it["y"]
        if ry < wy0 - 2 or ry > wy1 + 2:
            continue
        _, by = to_big(wx0, ry)
        if it["extent"] is not None:
            ex0, ex1 = it["extent"]
        else:
            ex0, ex1 = cx - 0.5 * spacing_px, cx + 0.5 * spacing_px
        bx0, _ = to_big(ex0, ry)
        bx1, _ = to_big(ex1, ry)
        bx0, bx1 = max(0, min(bx0, bx1)), min(TILE_IMG, max(bx0, bx1))
        cv2.line(big, (bx0, by), (bx1, by), ORANGE, max(1, SCALE // 2))
        # filled (clean, no head) vs hollow (a head sits on it) mark,
        # centred on the probed x (the head's own x)
        mx, _ = to_big(cx, ry)
        r = 5
        if it["occupied"]:
            cv2.circle(big, (mx, by), r, ORANGE, 1)       # hollow
        else:
            cv2.circle(big, (mx, by), r, ORANGE, -1)      # filled

    # --- red detector box + centre cross, same as before ---
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
    label1 = row["sub"]
    if rungs_step is None:
        label2 = f"geom {today_pos:+.2f} / NO RUNGS"
    else:
        label2 = f"geom {today_pos:+.2f} / rungs {rungs_step:+.0f} ({read_kind})"
    label3 = f"dy={dy:+.2f}" if dy is not None else "dy=n/a"
    cv2.putText(tile, label1, (4, TILE_IMG + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.36, BLACK, 1, cv2.LINE_AA)
    cv2.putText(tile, label2, (4, TILE_IMG + 31), cv2.FONT_HERSHEY_SIMPLEX, 0.36, BLACK, 1, cv2.LINE_AA)
    cv2.putText(tile, label3, (4, TILE_IMG + 46), cv2.FONT_HERSHEY_SIMPLEX, 0.36, BLACK, 1, cv2.LINE_AA)
    return tile


def verify_rung_on_ink(binary_page, sub, it):
    """Pixel-row check (not by eye): does this ONE drawn orange rung sit on
    real ink over its own x-extent, at its own measured y? Coverage is the
    fraction of extent columns with ink within +/-1px of the drawn y --
    same test `clean_heads_sheet.verify_green_lines_on_ink` runs for the
    green lines, applied here to every orange rung this script drew."""
    extent = it["extent"]
    if extent is None:
        return sub, it["idx"], None, False  # no extent measured -- cannot check, reported separately
    x0, x1 = extent
    x0_i, x1_i = int(round(x0)), int(round(x1)) + 1
    x0_i, x1_i = max(0, x0_i), min(binary_page.shape[1], x1_i)
    if x1_i <= x0_i:
        return sub, it["idx"], None, False
    y = it["y"]
    y_lo = max(0, int(round(y)) - 1)
    y_hi = min(binary_page.shape[0], int(round(y)) + 2)
    strip = binary_page[y_lo:y_hi, x0_i:x1_i] == 0  # True = ink
    coverage = float(strip.any(axis=0).mean())
    return sub, it["idx"], coverage, coverage >= 0.5


def main():
    rec = bm.load_record(bm.ARM_RECORD)["record"]
    pw = render_page_matching_gather(bm.PROVENANCE_PDF, bm.PAGE_IDX, dpi=bm.DPI)
    all_rows, _near = bm.main()
    row_by_sub = {r["sub"]: r for r in all_rows}

    # the SAME 15-head selection + dy frame_check.py already computed
    results = fc.notehead_check(pw.binary, all_rows)

    tiles = []
    far_count = 0
    far_with_rungs = 0
    far_no_rungs = []
    far_crashed = []
    all_pixel_checks = []  # (sub, idx, coverage, ok)

    for sub, _dx, dy in results:
        row = row_by_sub.get(sub)
        if row is None or row.get("box_page") is None:
            continue
        pos = row["today_pos"]
        # DECISIONS 2026-10-01 (b): the first space just outside the
        # staff (-1 or 9) is ON-STAFF, no ledger read -- `lg.far_head_
        # needs_ledger_read` is the one place that line is drawn. `pos`
        # is the raw geometric measurement (e.g. -1.02); the half-step
        # SLOT it names is its rounding, the same convention every other
        # consumer of `today_pos` in this lane already uses.
        is_far = lg.far_head_needs_ledger_read(int(round(pos)))
        if not is_far:
            tile, _drawn_lines, _window, _cx = chs.draw_tile(pw.rgb, pw.binary, row, dy)
            tiles.append(tile)
            continue

        far_count += 1
        side, rung_items, rungs_step, read_kind, crashed = classify_far_head(row, pw.binary)
        if crashed:
            far_crashed.append(sub)
        if rungs_step is None:
            far_no_rungs.append(sub)
        else:
            far_with_rungs += 1
        for it in rung_items:
            s, idx, coverage, ok = verify_rung_on_ink(pw.binary, sub, it)
            all_pixel_checks.append((s, idx, coverage, ok))

        tile = draw_tile_far(pw.rgb, pw.binary, row, dy, rung_items, rungs_step, read_kind, side)
        tiles.append(tile)

    # --- legend strip (one extra line vs clean_heads_sheet.py) ---
    sheet_w = COLS * TILE_W + (COLS + 1) * PAD
    sheet_h = LEGEND_H + ROWS * TILE_H + (ROWS + 1) * PAD
    sheet = np.full((sheet_h, sheet_w, 3), 255, dtype=np.uint8)
    cv2.putText(sheet, "red = detector box", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, RED, 2, cv2.LINE_AA)
    cv2.putText(sheet, "green = staff lines (real 5 only, never extended)",
               (220, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.46, GREEN, 2, cv2.LINE_AA)
    cv2.putText(sheet, "orange = measured ledger rung (filled=clean, hollow=head on it)",
               (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.44, ORANGE, 2, cv2.LINE_AA)
    cv2.putText(sheet,
               "lane-ledger-rungs v2 2026-10-01 -- wide-gap / first-space / stub fixes "
               "applied; same 15 heads as rungs_sheet.png",
               (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.40, BLACK, 1, cv2.LINE_AA)

    for i, tile in enumerate(tiles):
        r, c = divmod(i, COLS)
        y = LEGEND_H + PAD + r * (TILE_H + PAD)
        x = PAD + c * (TILE_W + PAD)
        sheet[y:y + TILE_H, x:x + TILE_W] = tile

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT_PATH), sheet)
    print(f"wrote {OUT_PATH} ({len(tiles)} tiles, {far_count} far heads of 15)")

    # --- report: every drawn orange rung, by pixel row, not by eye ---
    print()
    print(f"=== pixel-row check of ALL {len(all_pixel_checks)} drawn orange rungs "
         f"({far_count} far heads, {far_with_rungs} with rungs found) ===")
    failures = []
    no_extent = []
    for sub, idx, coverage, ok in all_pixel_checks:
        if coverage is None:
            no_extent.append((sub, idx))
            print(f"  {sub:<24} rung#{idx} NO EXTENT MEASURED -- cannot check")
            continue
        print(f"  {sub:<24} rung#{idx} coverage={coverage:.2f} {'OK' if ok else 'MISS'}")
        if not ok:
            failures.append((sub, idx, coverage))

    print()
    if failures:
        print(f"PIXEL CHECK: {len(failures)} of {len(all_pixel_checks)} drawn rungs "
             f"do NOT sit on ink >=0.5 coverage:")
        for sub, idx, coverage in failures:
            print(f"    {sub} rung#{idx} coverage={coverage:.2f}")
    else:
        print(f"PIXEL CHECK: ALL {len(all_pixel_checks)} drawn orange rungs sit on ink "
             f">=0.5 coverage over their own x-extent" +
             (f" ({len(no_extent)} had no extent to check)" if no_extent else ""))

    print()
    print(f"far heads: {far_count} of 15; rungs found for {far_with_rungs}; "
         f"NO RUNGS for {len(far_no_rungs)} ({far_no_rungs}); "
         f"reader crashed for {len(far_crashed)} ({far_crashed})")


if __name__ == "__main__":
    main()
