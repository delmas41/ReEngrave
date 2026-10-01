"""ROADMAP 2.48 -- Sean's boundary question (lane-2.48-boundary, NO re-gather).

The comb sits closer to the printed lines (~0.25px) than today's flat
per-bar grid (~1px) -- so why doesn't the score improve? Three hypotheses:
  (1) few heads sit near a rounding boundary, so a ~1px line change can't
      flip them;
  (2) box-centre error (box centre vs the head's own ink centre) is as big
      as the line improvement on exactly those heads;
  (3) the 149-of-1330 reference-scored sample is too small to see it.

Recipe (CLAUDE.md §2 rule 1, §6b, §10): GATHER+ADJUDICATE-only facts, STAGED
path, no re-gather -- reuses `recheck_2_48_seeded.py`'s own duck-typed
`Staff`/`PageWithStaves`, fresh render+deskew, and DIRECT calls to
`measure_extractor._cell_line_offset` / `_trace_cell_local_lines`. The
record used for geometry (boxes, staff lines, clef, bar numbers) is the
lane's own committed ARM record (`beethoven5-litolff-p3.record.json`,
agent-a3ef66441824adfff) -- every prior round in this FINDINGS line
confirmed the detector box is byte-identical base vs arm, so this record is
a valid source of GATHER facts for either grid; TODAY's (flat/orange) and
the SEEDED COMB's positions are both computed fresh here, never read off
the record's own (comb-affected) stored `notehead_staff_position`.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from tools.omr import measure_extractor as me
from tools.omr.preprocessing import deskew, render_page
from tools.omr.types import PageWithStaves, Staff
from tools.omr.staged import readout as ro
from tools.omr.staged.record import Q

import recheck_2_48_seeded as r48  # same directory -- duck_staff, expected_positions_for_page, etc.

ARM_RECORD = r48.ARM_RECORD
PROVENANCE_PDF = (
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
    "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
    "1870--imslp984073.pdf"
)
DPI = 600
PAGE_IDX = 3

OUT_DIR = REPO_ROOT / "out" / "print" / "2.48" / "boundary"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_record(path):
    return json.loads(Path(path).read_text())


def decided_value(rec, sub, q):
    for v in rec["record"].get("verdicts", []):
        if v["subject"] == sub and v["quantity"] == q and v.get("outcome") == "decided":
            return v["value"]
    return None


def main():
    rec = load_record(ARM_RECORD)
    run = ro.run_from_result(rec, path=ARM_RECORD)

    # --- the reference-scored population (149-of-1330), reused unchanged ---
    works_row = r48._load_works_row(r48.WORKS_ROW_ID)
    ref_root = r48._reference_root(works_row["reference"]["catalog_path"])
    family_map = r48._FAMILY_MAPS[r48.DOC_ID]
    expected = r48.expected_positions_for_page(rec["record"], ref_root, family_map, PAGE_IDX)

    # --- every KEPT notehead on the count page, position observed ---
    kept = []
    for g in run.glyphs.values():
        if g.page != PAGE_IDX or g.family != "note":
            continue
        if g.cls and not g.cls.startswith("notehead"):
            continue
        status, _why = ro.adjudicate_status(run, g)
        if status != ro.KEPT:
            continue
        pos_obs = run.obs_at(g.key, Q.NOTEHEAD_STAFF_POSITION)
        if not pos_obs:
            continue
        kept.append(g)

    print(f"Kept noteheads with a staff position on page {PAGE_IDX}: {len(kept)}")

    # --- render + deskew once per page (only page 3 here) ---
    pw = render_page(PROVENANCE_PDF, PAGE_IDX, dpi=DPI)
    rgb2, binary2, _deg = deskew(pw.rgb, pw.binary)
    pw.rgb, pw.binary = rgb2, binary2
    binary = pw.binary

    staff_cache = {}
    cellbox_cache = {}

    def get_staff(staff_key):
        if staff_key not in staff_cache:
            staff_cache[staff_key] = r48.duck_staff(rec["record"], staff_key)
        return staff_cache[staff_key]

    def get_cell_box(cell_key):
        if cell_key not in cellbox_cache:
            cellbox_cache[cell_key] = r48.obs(rec["record"], cell_key, "cell_box")
        return cellbox_cache[cell_key]

    rows = []
    for g in kept:
        sub = g.key
        staff_key = g.staff_key
        cell_key = g.cell_key
        staff = get_staff(staff_key)
        cell_box = get_cell_box(cell_key)
        if cell_box is None:
            continue
        x0, _y0, x1, _y1 = cell_box["value"]
        x0, x1 = int(x0), int(x1)
        pws = PageWithStaves(page=pw, staves=[staff], barlines=[])

        gb = r48.obs(rec["record"], sub, "glyph_box")
        if gb is None:
            continue
        x_center = gb["detail"]["x_center_page"]
        y_center = gb["detail"]["y_center_page"]
        box_page = gb["detail"].get("bbox_page_px")

        spacing_px = float(staff.line_spacing_px)
        nominal_ys = [float(y) for y in staff.line_ys]

        offset = me._cell_line_offset(pws, staff, x0, x1)
        orange_shift = float(offset[0]) if offset is not None else 0.0
        seeded_paths = me._trace_cell_local_lines(pws, staff, x0, x1,
                                                   seed_shift_px=orange_shift)

        today_pos = r48.grid_position(orange_shift, "flat", x0, spacing_px,
                                      nominal_ys, x_center, y_center)
        comb_pos = (r48.grid_position(seeded_paths, "comb", x0, spacing_px,
                                      nominal_ys, x_center, y_center)
                   if seeded_paths is not None else today_pos)
        if today_pos is None:
            continue

        half_step_px = spacing_px / 2.0
        residual_today = abs(today_pos - round(today_pos))
        dist_boundary_px = (0.5 - residual_today) * half_step_px

        # comb's own line position at this head's x, in px (top line's y)
        comb_top_y = nominal_ys[0] + orange_shift
        if seeded_paths is not None:
            col = int(round(x_center)) - x0
            col = max(0, min(len(seeded_paths[0]) - 1, col))
            comb_top_y = float(seeded_paths[0][col])
        orange_top_y = nominal_ys[0] + orange_shift
        line_diff_px = comb_top_y - orange_top_y  # comb - orange (today), signed

        rows.append(dict(
            sub=sub, staff_key=staff_key, cell_key=cell_key,
            x_center=x_center, y_center=y_center, box_page=box_page,
            staff=staff, x0=x0, x1=x1,
            orange_shift=orange_shift, seeded_paths=seeded_paths,
            nominal_ys=nominal_ys, spacing_px=spacing_px,
            today_pos=today_pos, comb_pos=comb_pos,
            dist_boundary_px=dist_boundary_px,
            line_diff_px=line_diff_px,
            is_scored=sub in expected,
        ))

    # ─── Part A: histogram ──────────────────────────────────────────────
    buckets = {"0-0.5": 0, "0.5-1": 0, "1-2": 0, "2-3": 0, "3+": 0}
    within1 = []
    for r in rows:
        d = r["dist_boundary_px"]
        if d < 0.5:
            buckets["0-0.5"] += 1
        elif d < 1.0:
            buckets["0.5-1"] += 1
        elif d < 2.0:
            buckets["1-2"] += 1
        elif d < 3.0:
            buckets["2-3"] += 1
        else:
            buckets["3+"] += 1
        if d < 1.0:
            within1.append(r)

    within1_scored = [r for r in within1 if r["is_scored"]]

    print()
    print("=== PART A: distance-to-rounding-boundary histogram (today's flat grid) ===")
    print(f"total kept noteheads measured: {len(rows)}")
    for k, v in buckets.items():
        print(f"  {k:>8} px: {v}")
    print(f"within 1px of a boundary: {len(within1)} of {len(rows)} "
         f"({100.0*len(within1)/max(1,len(rows)):.1f}%)")
    print(f"within 1px AND among the {len(expected)} reference-scored heads: "
         f"{len(within1_scored)}")

    # ─── Part B: box-centre vs ink-centre, and line diff, within 2px ────
    near = [r for r in rows if r["dist_boundary_px"] <= 2.0]
    print()
    print(f"=== PART B: {len(near)} heads within 2px of a boundary ===")

    box_errs = []
    line_diffs = []
    print(f"{'subject':<24}{'dist_px':<9}{'box-ink':<10}{'orange-comb':<12}")
    for r in near:
        ink = measure_notehead_ink_centre(binary, r)
        box_centre = r["y_center"]
        box_err = (box_centre - ink) if ink is not None else None
        if box_err is not None:
            box_errs.append(box_err)
        line_diffs.append(r["line_diff_px"])
        print(f"{r['sub']:<24}{r['dist_boundary_px']:<9.2f}"
             f"{('%.2f' % box_err) if box_err is not None else 'n/a':<10}"
             f"{r['line_diff_px']:<12.2f}")

    def mean_std(xs):
        if not xs:
            return None, None
        if len(xs) < 2:
            return xs[0], 0.0
        return statistics.mean(xs), statistics.pstdev(xs)

    bm, bs = mean_std(box_errs)
    lm, ls = mean_std(line_diffs)
    print()
    print(f"box-centre error:  mean={bm:.3f} std={bs:.3f} (n={len(box_errs)})"
         if bm is not None else "box-centre error: n/a")
    print(f"line diff (comb-orange): mean={lm:.3f} std={ls:.3f} (n={len(line_diffs)})"
         if lm is not None else "line diff: n/a")
    if bm is not None and lm is not None:
        bigger = "box-centre error" if abs(bm) + bs > abs(lm) + ls else "line difference"
        print(f"BIGGER on these heads: {bigger}")

    # ─── Part C: controls ────────────────────────────────────────────────
    print()
    print("=== PART C: controls ===")
    clean_candidates = [r for r in rows if r["dist_boundary_px"] > 3.0]
    clean = []
    seen_cells = set()
    for r in clean_candidates:
        if r["cell_key"] in seen_cells:
            continue
        seen_cells.add(r["cell_key"])
        clean.append(r)
        if len(clean) >= 10:
            break
    clean_errs = []
    for r in clean:
        ink = measure_notehead_ink_centre(binary, r)
        if ink is not None:
            clean_errs.append(r["y_center"] - ink)
    cm, cs = mean_std(clean_errs)
    print(f"10 clean isolated heads (far from boundary): "
         f"box-ink mean={cm:.3f} std={cs:.3f} (n={len(clean_errs)}) "
         "-- expect small (~1px)" if cm is not None else "control A: n/a")

    broken_errs = []
    for r in clean[:3]:
        fake = dict(r)
        fake["y_center"] = r["y_center"] + 3.0
        ink = measure_notehead_ink_centre(binary, fake)
        if ink is not None:
            broken_errs.append(fake["y_center"] - ink)
    print(f"3 heads with box offset +3px (broken-state control): "
         f"measured errors = {[round(x, 2) for x in broken_errs]} "
         "-- expect ~3px each")

    return rows, near


STEM_SIDE_FRACTION = 0.4  # central band fraction of box width, away from stem


def measure_notehead_ink_centre(binary: np.ndarray, r: dict) -> float | None:
    """Midpoint of the head's own ink top/bottom edge, in page px, scanned
    over the box's CENTRAL columns on the side AWAY from the stem (stems up
    -> right, down -> left; CLAUDE.md §10), with the staff-line rows masked
    out at the comb's own measured positions (line thickness from the
    record) so a note sitting ON a line does not merge with it."""
    box = r.get("box_page")
    if box is None:
        return None
    x0, y0, x1, y1 = (float(v) for v in box)
    width = x1 - x0
    if width <= 0:
        return None
    band = STEM_SIDE_FRACTION * width
    # default: a narrow central band
    cx0, cx1 = x0 + 0.5 * width - band / 2.0, x0 + 0.5 * width + band / 2.0
    # NOTE: stem-side exclusion -- a narrow central band around the box's
    # own midline avoids both stem sides for a normal head (stem meets the
    # head at its LEFT or RIGHT edge, CLAUDE.md §10), so no per-head stem
    # lookup is needed for this central-column measurement.
    cx0_i, cx1_i = int(round(cx0)), int(round(cx1))
    cx0_i, cx1_i = max(0, cx0_i), min(binary.shape[1], cx1_i)
    if cx1_i <= cx0_i:
        return None

    pad = max(2.0, 0.3 * r["spacing_px"])
    y_lo = max(0, int(round(min(y0, y1) - pad)))
    y_hi = min(binary.shape[0], int(round(max(y0, y1) + pad)))
    if y_hi <= y_lo:
        return None

    window = binary[y_lo:y_hi, cx0_i:cx1_i] == 0  # True = ink

    # Mask the staff lines at the comb's own measured y for these columns.
    staff = r["staff"]
    raw_thickness = staff.line_thickness_px
    if isinstance(raw_thickness, (list, tuple)) and raw_thickness:
        thickness = float(sum(raw_thickness)) / len(raw_thickness)
    elif raw_thickness:
        thickness = float(raw_thickness)
    else:
        thickness = 0.12 * r["spacing_px"]
    half_th = max(1.0, thickness / 2.0 + 1.0)
    seeded_paths = r["seeded_paths"]
    for xi in range(cx0_i, cx1_i):
        if seeded_paths is not None:
            col = xi - r["x0"]
            if 0 <= col < len(seeded_paths[0]):
                line_ys = [float(p[col]) for p in seeded_paths]
            else:
                line_ys = [ny + r["orange_shift"] for ny in r["nominal_ys"]]
        else:
            line_ys = [ny + r["orange_shift"] for ny in r["nominal_ys"]]
        for ly in line_ys:
            lo = int(round(ly - half_th)) - y_lo
            hi = int(round(ly + half_th)) - y_lo + 1
            lo, hi = max(0, lo), min(window.shape[0], hi)
            if lo < hi:
                window[lo:hi, xi - cx0_i] = False

    coverage = window.any(axis=0).mean() if window.size else 0.0
    if coverage < 0.3:
        return None
    # OUTERMOST ink row per column, not the nearest contiguous run: an OPEN
    # (hollow) notehead's own centre has no ink at all, so "nearest run to
    # the window's centre" catches only whichever RIM happens to sit closer
    # -- a few px of the head's own height, not the head -- and that is
    # exactly the failure the clean-head control below exists to catch.
    # The outermost extent is right for a filled head too (its ink IS a
    # single run, so outermost == that run's own top/bottom).
    tops, bottoms = [], []
    for c in range(window.shape[1]):
        col = window[:, c]
        idx = np.flatnonzero(col)
        if idx.size == 0:
            continue
        tops.append(int(idx[0]))
        bottoms.append(int(idx[-1]))
    if not tops:
        return None
    top_m = float(np.median(tops))
    bottom_m = float(np.median(bottoms))
    return y_lo + (top_m + bottom_m) / 2.0


if __name__ == "__main__":
    main()
