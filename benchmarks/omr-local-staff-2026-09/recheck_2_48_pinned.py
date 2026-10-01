"""2.48 PINNED-comb small real check (NO re-gather, Sean's "no batteries").

Reuses `recheck_2_48_seeded.py`'s own recipe and subject list verbatim (the
15 traced heads + 10 control heads) and adds the 2 heads still right->wrong
under the SEEDED comb (`crop_2_48_broken.py`'s `SUBJECTS`:
`glyph/3/0/0/2/4`, `glyph/3/1/0/6/0`) -- 27 heads total. Four candidate
grids are scored against the reference position (via the staff's own
decided clef), using the SAME pairing `gather_only_judge.score_doc` uses:

  - TODAY   = orange's own flat per-cell grid (`_cell_line_offset`).
  - OLD COMB    = the withdrawn, UNSEEDED per-cell walk (seed=0).
  - SEEDED COMB = the per-cell walk seeded from orange (lane-2.48-seeded,
    today's course before this lane).
  - PINNED COMB = this lane's design #3: one smooth per-(staff, system)
    model pinned at both system ends and 3 interior points, linearly
    interpolated between, falling back to SEEDED COMB where fewer than 2
    pins survive.

Also reports, per staff touched on the count page, the max ABSOLUTE
deviation of the seeded comb and the pinned model from a straight line
across the system -- the "how much it changes" number Sean asked for
(DECISIONS.md, 2026-10-01: "Currently I feel like the comb changes too
much... pinned at the ends and a few points in between?").

GATHER+ADJUDICATE-only facts throughout (CLAUDE.md §6b): clef, printed bar
number and measure partition are all ADJUDICATE verdicts already in the
record; nothing here reads EVALUATE/EXPORT.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.omr import measure_extractor as me
from tools.omr.acceptance_quick import _FAMILY_MAPS, _load_works_row, _reference_root
from tools.omr.preprocessing import deskew, render_page
from tools.omr.types import PageWithStaves

from recheck_2_48_seeded import (
    ARM_RECORD, DOC_ID, TRACED_SUBJECTS, WORKS_ROW_ID,
    cell_key_of, duck_staff, expected_positions_for_page, grid_position,
    load_record, obs, page_index_of, staff_key_of,
)

BROKEN_SUBJECTS = ["glyph/3/0/0/2/4", "glyph/3/1/0/6/0"]

PDF = (
    "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
    "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
    "1870--imslp984073.pdf"
)
DPI = 600


def max_deviation_from_straight(shifts: np.ndarray) -> float:
    """The max absolute departure of a per-column shift array from the
    STRAIGHT line through its own two endpoints -- "how much it changes"
    across the system, independent of a constant overall offset."""
    n = shifts.shape[0]
    if n < 2:
        return 0.0
    endpoints_line = np.linspace(shifts[0], shifts[-1], n)
    return float(np.max(np.abs(shifts - endpoints_line)))


def main():
    rec = load_record(ARM_RECORD)
    works_row = _load_works_row(WORKS_ROW_ID)
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    family_map = _FAMILY_MAPS[DOC_ID]

    expected = expected_positions_for_page(rec, ref_root, family_map, 3)
    control_pool = sorted(s for s in expected if s not in TRACED_SUBJECTS)
    seen_cells = set()
    controls = []
    for s in control_pool:
        ck = cell_key_of(s)
        if ck in seen_cells:
            continue
        seen_cells.add(ck)
        controls.append(s)
        if len(controls) >= 10:
            break

    # BROKEN_SUBJECTS is a SUBSET of TRACED_SUBJECTS (both already-broken
    # heads were among the 15 originally traced) -- de-duplicated here so
    # each subject is measured once; its row's `group` is still reported
    # as "broken" for those two (see the group logic below).
    subjects = list(dict.fromkeys(TRACED_SUBJECTS + controls + BROKEN_SUBJECTS))

    pages, staff_pinned_cache, staff_deviation = {}, {}, {}
    rows = []
    for sub in subjects:
        page_idx = page_index_of(sub)
        if page_idx not in pages:
            pw = render_page(PDF, page_idx, dpi=DPI)
            rgb2, binary2, _deg = deskew(pw.rgb, pw.binary)
            pw.rgb, pw.binary = rgb2, binary2
            pages[page_idx] = pw
        page = pages[page_idx]

        staff_key = staff_key_of(sub)
        cell_key = cell_key_of(sub)
        staff = duck_staff(rec, staff_key)
        pws = PageWithStaves(page=page, staves=[staff], barlines=[])

        cell_box = obs(rec, cell_key, "cell_box")
        if cell_box is None:
            continue
        x0, _y0, x1, _y1 = cell_box["value"]
        x0, x1 = int(x0), int(x1)

        gb = obs(rec, sub, "glyph_box")
        if gb is None:
            continue
        x_center = gb["detail"]["x_center_page"]
        y_center = gb["detail"]["y_center_page"]

        spacing_px = float(staff.line_spacing_px)
        nominal_ys = [float(y) for y in staff.line_ys]

        offset = me._cell_line_offset(pws, staff, x0, x1)
        orange_shift = offset[0] if offset is not None else None

        old_comb = me._trace_cell_local_lines(pws, staff, x0, x1, seed_shift_px=0.0)
        seed = float(orange_shift) if orange_shift is not None else 0.0
        seeded_comb = me._trace_cell_local_lines(pws, staff, x0, x1, seed_shift_px=seed)

        # Pinned model: one per (staff, SYSTEM) -- cached by staff_key so
        # every head on the same staff reuses the same computed array
        # instead of re-measuring its pins per head.
        if staff_key not in staff_pinned_cache:
            sys_x0, sys_x1 = staff.x_start, staff.x_end
            pinned_arr = me._pinned_system_shifts(pws, staff, sys_x0, sys_x1)
            staff_pinned_cache[staff_key] = (sys_x0, pinned_arr)
            seeded_full = me._trace_cell_local_lines(pws, staff, sys_x0, sys_x1,
                                                      seed_shift_px=0.0)
            seeded_dev = (max_deviation_from_straight(seeded_full[0] - nominal_ys[0])
                         if seeded_full is not None else None)
            pinned_dev = (max_deviation_from_straight(pinned_arr)
                         if pinned_arr is not None else None)
            staff_deviation[staff_key] = (seeded_dev, pinned_dev)
        sys_x0, pinned_arr = staff_pinned_cache[staff_key]

        pinned_cell = None
        if pinned_arr is not None:
            lo_c, hi_c = x0, x1
            start, end = lo_c - sys_x0, hi_c - sys_x0
            if 0 <= start and end <= pinned_arr.shape[0]:
                cell_shift = pinned_arr[start:end]
                pinned_cell = [np.full(hi_c - lo_c, float(y), dtype=float) + cell_shift
                              for y in staff.line_ys]
        if pinned_cell is None:
            pinned_cell = seeded_comb  # <2 pins survived: today's per-bar grid

        today_pos = grid_position(orange_shift, "flat", x0, spacing_px, nominal_ys,
                                   x_center, y_center)
        old_pos = (grid_position(old_comb, "comb", x0, spacing_px, nominal_ys,
                                  x_center, y_center)
                  if old_comb is not None else today_pos)
        seeded_pos = (grid_position(seeded_comb, "comb", x0, spacing_px, nominal_ys,
                                     x_center, y_center)
                     if seeded_comb is not None else today_pos)
        pinned_pos = (grid_position(pinned_cell, "comb", x0, spacing_px, nominal_ys,
                                     x_center, y_center)
                     if pinned_cell is not None else today_pos)

        exp = expected.get(sub)
        rows.append(dict(
            sub=sub,
            group=("broken" if sub in BROKEN_SUBJECTS
                   else "control" if sub not in TRACED_SUBJECTS else "traced"),
            today=today_pos, seeded=seeded_pos, pinned=pinned_pos,
            expected=exp,
            today_right=(exp is not None and today_pos is not None
                        and round(today_pos) == exp),
            seeded_right=(exp is not None and seeded_pos is not None
                         and round(seeded_pos) == exp),
            pinned_right=(exp is not None and pinned_pos is not None
                         and round(pinned_pos) == exp),
        ))

    header = (f"{'subject':<24}{'group':<9}{'today':<9}{'seeded':<9}"
             f"{'pinned':<9}{'expected':<10}{'t_ok':<6}{'se_ok':<7}{'pi_ok':<6}")
    print(header)
    for r in rows:
        def f(v):
            return "None" if v is None else f"{v:.2f}"
        print(f"{r['sub']:<24}{r['group']:<9}{f(r['today']):<9}{f(r['seeded']):<9}"
             f"{f(r['pinned']):<9}{str(r['expected']):<10}"
             f"{str(r['today_right']):<6}{str(r['seeded_right']):<7}"
             f"{str(r['pinned_right']):<6}")

    def tally(group):
        rtw_seeded = sum(1 for r in group if r["today_right"] and not r["seeded_right"])
        wtr_seeded = sum(1 for r in group if not r["today_right"] and r["seeded_right"])
        rtw_pinned = sum(1 for r in group if r["today_right"] and not r["pinned_right"])
        wtr_pinned = sum(1 for r in group if not r["today_right"] and r["pinned_right"])
        return rtw_seeded, wtr_seeded, rtw_pinned, wtr_pinned

    traced = [r for r in rows if r["group"] == "traced"]
    ctrl = [r for r in rows if r["group"] == "control"]
    broken = [r for r in rows if r["group"] == "broken"]
    print()
    for name, grp in (("TRACED", traced), ("CONTROL", ctrl), ("BROKEN(2)", broken)):
        if not grp:
            continue
        rtw_s, wtr_s, rtw_p, wtr_p = tally(grp)
        print(f"{name} ({len(grp)}): seeded vs today  right->wrong={rtw_s} "
             f"wrong->right={wtr_s}   | pinned vs today  "
             f"right->wrong={rtw_p} wrong->right={wtr_p}")

    print()
    print("Per-staff max deviation from a straight line across the system (px):")
    print(f"{'staff':<16}{'seeded_dev':<12}{'pinned_dev':<12}")
    for sk in sorted(staff_deviation):
        sdev, pdev = staff_deviation[sk]
        def fd(v):
            return "None" if v is None else f"{v:.2f}"
        print(f"{sk:<16}{fd(sdev):<12}{fd(pdev):<12}")


if __name__ == "__main__":
    main()
