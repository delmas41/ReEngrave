"""2.48 seeded-comb small real check (NO re-gather, Sean's "no batteries").

Reuses the one-head lane's own recipe (FINDINGS.md 2026-10-01: duck-typed
`Staff`/`PageWithStaves` built from a committed record's own stored
`staff_lines`/`staff_spacing`/`staff_skew.thickness_px`, a fresh
`render_page`+`deskew`, then calling `_cell_line_offset` and
`_trace_cell_local_lines` DIRECTLY -- never a gather) and generalises it
from one head to the 15 traced heads (14 right->wrong + 1 wrong->right,
`trace_14_heads.py`'s own `SUBJECTS`) plus ~10 control heads on the same
page that today already reads right, to check the comb SEEDED from
`_cell_line_offset` ("orange") against:

  - TODAY  = orange's own flat per-cell grid (what production emits when
    `_cell_line_offset` measures a shift; the raw unlocalized lines when it
    abstains) -- i.e. the pipeline exactly as it stands before 2.48 ever
    touched it.
  - OLD COMB  = `_trace_cell_local_lines(..., seed_shift_px=0.0)` -- the
    withdrawn, unseeded 2.48 comb.
  - SEEDED COMB = `_trace_cell_local_lines(..., seed_shift_px=orange)` --
    this lane's fix.

against the reference pitch (via the staff's own decided clef), using
EXACTLY the pairing `gather_only_judge.score_doc` uses (box x,y order
within the bar vs. the truth's onset-descending-pitch order) so the
right/wrong verdict here is comparable to that judge's own numbers.
GATHER+ADJUDICATE-only facts throughout (CLAUDE.md §6b): clef, printed
bar number and measure partition are all ADJUDICATE verdicts already in
the record; nothing here reads EVALUATE/EXPORT.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.omr import measure_extractor as me
from tools.omr.acceptance_quick import _FAMILY_MAPS, _load_works_row, _reference_root, _union_bars
from tools.omr.pitch_resolver import _CLEF_ANCHORS, diatonic_index
from tools.omr.preprocessing import deskew, render_page
from tools.omr.types import PageWithStaves, Staff

ARM_RECORD = (
    "/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/"
    "agent-a3ef66441824adfff/benchmarks/acceptance/quick/out/"
    "beethoven5-litolff/beethoven5-litolff-p3.record.json"
)
WORKS_ROW_ID = "beethoven-sym5-mvt1-984073-p3"
DOC_ID = "beethoven5-litolff"

# The 15 heads trace_14_heads.py traced (14 right->wrong + 1 wrong->right,
# base = orange/flat grid, arm = the withdrawn unseeded comb).
TRACED_SUBJECTS = [
    "glyph/1/0/7/1/1",
    "glyph/1/0/8/1/6",
    "glyph/2/0/2/4/1",
    "glyph/2/0/3/0/5",
    "glyph/2/0/3/0/7",
    "glyph/2/0/3/3/2",
    "glyph/2/0/7/0/4",
    "glyph/2/0/7/10/3",
    "glyph/2/0/7/2/2",
    "glyph/3/0/0/2/4",
    "glyph/3/0/8/0/3",
    "glyph/3/0/8/0/4",
    "glyph/3/0/8/0/5",
    "glyph/3/0/8/0/8",
    "glyph/3/1/0/6/0",
]

_LETTER_ORDER = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


def pitch_height(p):
    return p[1] * 7 + _LETTER_ORDER.get(p[0], 0)


def parse_ref_pitch(s):
    if not s:
        return None
    step, rest, i = s[0], s[1:], 0
    if i < len(rest) and rest[i] in "+-":
        i += 1
        if i < len(rest) and rest[i].isdigit():
            i += 1
    try:
        return step, int(rest[i:])
    except ValueError:
        return None


def truth_onset_groups(ref_bars, bar):
    by_onset = {}
    for ev in ref_bars.get(str(bar), ()):
        if ev.pitch is None:
            continue
        p = parse_ref_pitch(ev.pitch)
        if p is not None:
            by_onset.setdefault(ev.onset, []).append(p)
    return [by_onset[k] for k in sorted(by_onset)]


def load_record(path):
    return json.loads(Path(path).read_text())["record"]


def decided(rec, sub, q):
    for v in rec.get("verdicts", []):
        if v["subject"] == sub and v["quantity"] == q and v.get("outcome") == "decided":
            return v["value"]
    return None


def obs(rec, sub, q):
    rows = [o for o in rec["observations"] if o["subject"] == sub and o["quantity"] == q]
    return rows[-1] if rows else None


def staff_key_of(sub):
    p = sub.split("/")
    return f"staff/{p[1]}/{p[2]}/{p[3]}"


def cell_key_of(sub):
    p = sub.split("/")
    return f"cell/{p[1]}/{p[2]}/{p[3]}/{p[4]}"


def system_key_of(sub):
    p = sub.split("/")
    return f"system/{p[1]}/{p[2]}"


def page_index_of(sub):
    return int(sub.split("/")[1])


def position_from_pitch(letter, octave, clef):
    anchor = _CLEF_ANCHORS.get(clef)
    if anchor is None:
        return None
    return diatonic_index(*anchor) - diatonic_index(letter, octave)


def expected_positions_for_page(rec, ref_root, family_map, page_idx):
    """subject -> expected diatonic position, for every notehead on `page_idx`
    -- same pairing `gather_only_judge.score_doc` uses (box x,y order within
    the bar against the truth's onset-descending flat order)."""
    family_by_pnum = {int(ids[0][1:]): fam for fam, (ids, _r) in family_map.items()}
    out = {}
    staff_keys = sorted({
        o["subject"] for o in rec["observations"]
        if o["quantity"] == "staff_lines" and o["subject"].split("/")[1] == str(page_idx)
    })
    for staff_key in staff_keys:
        p = staff_key.split("/")
        page_i, system, staff = int(p[1]), int(p[2]), int(p[3])
        ordinal = decided(rec, staff_key, "staff_ordinal")
        if ordinal is None or (ordinal + 1) not in family_by_pnum:
            continue
        family = family_by_pnum[ordinal + 1]
        clef = decided(rec, staff_key, "clef")
        measure_partition = decided(rec, staff_key, "measure_partition")
        system_key = f"system/{page_i}/{system}"
        printed_bar = decided(rec, system_key, "printed_bar_number")
        if measure_partition is None or clef is None or printed_bar is None:
            continue
        ref_ids = family_map[family][1]
        ref_bars = _union_bars(ref_ids, ref_root)
        for cell in range(measure_partition):
            prefix = f"glyph/{page_i}/{system}/{staff}/{cell}/"
            dets = [o for o in rec["observations"]
                   if o["quantity"] == "glyph_box" and o["subject"].startswith(prefix)
                   and o["value"] and str(o["value"][0]).startswith("notehead")]
            if not dets:
                continue
            dets_sorted = sorted(dets, key=lambda o: (
                o["detail"]["bbox_page_px"][0], o["detail"]["bbox_page_px"][1]))
            bar = printed_bar + cell
            groups = truth_onset_groups(ref_bars, bar)
            flat = []
            for g in groups:
                flat.extend(sorted(g, key=pitch_height, reverse=True))
            if len(flat) != len(dets_sorted):
                continue
            for o, truth in zip(dets_sorted, flat):
                exp = position_from_pitch(truth[0], truth[1], clef)
                if exp is not None:
                    out[o["subject"]] = exp
    return out


def duck_staff(rec, staff_key):
    page_idx, system, staff_ord = (int(x) for x in staff_key.split("/")[1:])
    lines = obs(rec, staff_key, "staff_lines")
    spacing = obs(rec, staff_key, "staff_spacing")
    extent = obs(rec, staff_key, "staff_extent")
    skew = obs(rec, staff_key, "staff_skew")
    thickness = (skew.get("detail", {}).get("thickness_px") if skew else None)
    return Staff(
        page_index=page_idx, staff_index=staff_ord,
        line_ys=[int(y) for y in lines["value"]],
        x_start=int(extent["value"][0]), x_end=int(extent["value"][1]),
        system_index=system,
        line_thickness_px=thickness,
        nominal_line_spacing_px=float(spacing["value"]) if spacing else None,
    )


def render_cached(pdf_path, dpi, cache):
    key = (pdf_path, dpi)
    if key not in cache:
        page_idx_cache = {}
        cache[key] = page_idx_cache
    return cache[key]


def grid_position(paths_or_shift, kind, x0, spacing_px, nominal_ys, page_x, y_center):
    """Returns pos_float for one of the three candidate grids.

    `kind` is "flat" (paths_or_shift is a scalar px shift, or None to mean
    the raw, un-localized nominal grid) or "comb" (paths_or_shift is the
    [path_0..path_4] list `_trace_cell_local_lines` returns)."""
    if kind == "flat":
        shift = 0.0 if paths_or_shift is None else float(paths_or_shift)
        top_y = nominal_ys[0] + shift
        half_step = spacing_px / 2.0
    else:
        paths = paths_or_shift
        col = int(round(page_x)) - int(x0)
        col = max(0, min(len(paths[0]) - 1, col))
        ys = [float(p[col]) for p in paths]
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        top_y = ys[0]
        half_step = (sum(gaps) / len(gaps)) / 2.0
    if half_step <= 0:
        return None
    return (y_center - top_y) / half_step


def main():
    rec = load_record(ARM_RECORD)
    provenance_pdf = (
        "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/"
        "symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-"
        "1870--imslp984073.pdf"
    )
    dpi = 600
    works_row = _load_works_row(WORKS_ROW_ID)
    ref_root = _reference_root(works_row["reference"]["catalog_path"])
    family_map = _FAMILY_MAPS[DOC_ID]

    # Control heads: every notehead on page 3 scored by the SAME pairing,
    # minus the 15 already traced, sampled across different staves/bars.
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

    subjects = TRACED_SUBJECTS + controls

    pages = {}
    rows = []
    for sub in subjects:
        page_idx = page_index_of(sub)
        if page_idx not in pages:
            pw = render_page(provenance_pdf, page_idx, dpi=dpi)
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

        today_pos = grid_position(orange_shift, "flat", x0, spacing_px, nominal_ys,
                                   x_center, y_center)
        old_pos = (grid_position(old_comb, "comb", x0, spacing_px, nominal_ys,
                                  x_center, y_center)
                  if old_comb is not None else today_pos)
        seeded_pos = (grid_position(seeded_comb, "comb", x0, spacing_px, nominal_ys,
                                     x_center, y_center)
                     if seeded_comb is not None else today_pos)

        exp = expected.get(sub)
        rows.append(dict(
            sub=sub, is_control=sub not in TRACED_SUBJECTS,
            orange_shift_px=orange_shift,
            today=round(today_pos, 2) if today_pos is not None else None,
            old_comb=round(old_pos, 2) if old_pos is not None else None,
            seeded_comb=round(seeded_pos, 2) if seeded_pos is not None else None,
            expected=exp,
            today_right=(exp is not None and today_pos is not None
                        and round(today_pos) == exp),
            old_comb_right=(exp is not None and old_pos is not None
                            and round(old_pos) == exp),
            seeded_comb_right=(exp is not None and seeded_pos is not None
                               and round(seeded_pos) == exp),
        ))

    header = (f"{'subject':<24}{'ctrl':<6}{'orange_px':<11}{'today':<9}"
             f"{'old_comb':<10}{'seeded':<9}{'expected':<10}"
             f"{'t_ok':<6}{'o_ok':<6}{'s_ok':<6}")
    print(header)
    for r in rows:
        print(f"{r['sub']:<24}{str(r['is_control']):<6}"
             f"{str(r['orange_shift_px']):<11}{str(r['today']):<9}"
             f"{str(r['old_comb']):<10}{str(r['seeded_comb']):<9}"
             f"{str(r['expected']):<10}"
             f"{str(r['today_right']):<6}{str(r['old_comb_right']):<6}"
             f"{str(r['seeded_comb_right']):<6}")

    traced = [r for r in rows if not r["is_control"]]
    ctrl = [r for r in rows if r["is_control"]]

    def tally(group):
        rtw = sum(1 for r in group if r["today_right"] and not r["seeded_comb_right"])
        wtr = sum(1 for r in group if not r["today_right"] and r["seeded_comb_right"])
        old_rtw = sum(1 for r in group if r["today_right"] and not r["old_comb_right"])
        old_wtr = sum(1 for r in group if not r["today_right"] and r["old_comb_right"])
        return rtw, wtr, old_rtw, old_wtr

    t_rtw, t_wtr, t_old_rtw, t_old_wtr = tally(traced)
    c_rtw, c_wtr, c_old_rtw, c_old_wtr = tally(ctrl)
    print()
    print(f"TRACED ({len(traced)}): seeded comb vs today  right->wrong={t_rtw} "
         f"wrong->right={t_wtr}   | old (unseeded) comb vs today  "
         f"right->wrong={t_old_rtw} wrong->right={t_old_wtr}")
    print(f"CONTROL ({len(ctrl)}): seeded comb vs today  right->wrong={c_rtw} "
         f"wrong->right={c_wtr}   | old (unseeded) comb vs today  "
         f"right->wrong={c_old_rtw} wrong->right={c_old_wtr}")


if __name__ == "__main__":
    main()
