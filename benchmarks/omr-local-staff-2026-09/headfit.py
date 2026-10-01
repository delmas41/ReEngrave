"""ROADMAP 2.48 -- near-boundary head fit by ideal-head ink coverage
(lane-2.48-headfit, NO re-gather, GATHER+ADJUDICATE only, STAGED path).

Sean's design (DECISIONS 2026-10-01, queued behind the boundary-distance
check): snapping a box to a line/space IS the rounding decision, so it
cannot be its own evidence. Instead, for a head within ~2px of a rounding
boundary ONLY, place an IDEAL head (2.39's standard size, `geometry.
standard_head_box`) at EACH of the two candidate staff-position steps
either side of the boundary, at the head's own x, with its vertical centre
exactly on that candidate's line/space y from TODAY'S per-bar grid
(`measure_extractor._cell_line_offset` -- the comb is a separate,
not-yet-merged mechanism, deliberately not used here). Score each
candidate by the fraction of its ideal box that is inked, with the
STAFF-LINE rows (today's real lines, not a candidate's hypothetical
position) masked out identically for both candidates -- a line-note's
own line ink is expected there and is not evidence either way.

MARGIN RULE, stated here BEFORE any result in this file was looked at:
decide for the candidate with the higher coverage only when (a) it beats
the other candidate's coverage by >= MARGIN (0.15, i.e. 15 points of box
area) AND (b) its own coverage is >= MIN_WINNER (0.30). Otherwise ABSTAIN
and keep today's reading, counted.

Reuses `boundary_measure.py`'s own row-building (calling its `main()`
directly for the dist-to-boundary-labelled population) and
`recheck_2_48_seeded.py`'s duck-typed-record recipe for the 3 merged-blob
subjects, which are not necessarily in `boundary_measure`'s KEPT-only
population.
"""
from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.omr import measure_extractor as me  # noqa: E402
from frame import render_page_matching_gather  # noqa: E402 -- lane-2.48-recipe
from tools.omr.staged.geometry import standard_head_box  # noqa: E402
from tools.omr.types import PageWithStaves  # noqa: E402

import boundary_measure as bm  # noqa: E402
import recheck_2_48_seeded as r48  # noqa: E402

MARGIN = 0.15
MIN_WINNER = 0.30

# 3 documented merged two-head blobs on Litolff p3 (not necessarily in
# boundary_measure's KEPT-only population) -- Sean's own example plus two
# more from this tree's prior FINDINGS:
#   glyph/3/0/0/2/9  -- boundary_measure's own crop D: detector box covers
#                        only the upper portion of a visibly larger blob.
#   glyph/3/0/9/2/6  -- omr-notehead-width-2026-09 FINDINGS 20d crop 2,
#                        "merged blob".
#   glyph/3/1/2/9/2  -- omr-notehead-precision-2026-09 FINDINGS, round 3's
#                        own unresolved "may be one merged mark or two real
#                        heads a small interval apart under one over-tall
#                        box" cluster (cell/3/1/2/9).
MERGED_SUBJECTS = ["glyph/3/0/0/2/9", "glyph/3/0/9/2/6", "glyph/3/1/2/9/2"]


# ─── shared geometry helpers ────────────────────────────────────────────

def line_thickness_px(staff, spacing_px):
    raw = staff.line_thickness_px
    if isinstance(raw, (list, tuple)) and raw:
        return float(sum(raw)) / len(raw)
    if raw:
        return float(raw)
    return 0.12 * spacing_px


def box_ink_coverage(binary, x0, x1, y0, y1, mask_line_ys, half_th):
    """Fraction of ink in the box, with rows at `mask_line_ys` (+/-
    `half_th`) excluded from both the numerator and the denominator --
    real staff-line ink is neither evidence for nor against a candidate."""
    xi0, xi1 = int(round(x0)), int(round(x1))
    yi0, yi1 = int(round(y0)), int(round(y1))
    xi0, yi0 = max(0, xi0), max(0, yi0)
    xi1 = min(binary.shape[1], xi1)
    yi1 = min(binary.shape[0], yi1)
    if xi1 <= xi0 or yi1 <= yi0:
        return None
    window = binary[yi0:yi1, xi0:xi1] == 0  # True = ink
    row_mask = np.ones(window.shape[0], dtype=bool)
    for ly in mask_line_ys:
        lo = int(round(ly - half_th)) - yi0
        hi = int(round(ly + half_th)) - yi0 + 1
        lo, hi = max(0, lo), min(window.shape[0], hi)
        if lo < hi:
            row_mask[lo:hi] = False
    masked = window[row_mask, :]
    if masked.size == 0:
        return None
    return float(masked.mean())


def fit_scores(row, binary, lower, upper, place_top_y):
    """Score both integer candidates `lower`/`upper` against the ideal
    head box, placed at `place_top_y + cand*half_step`, head's own x.
    Masking always uses TODAY's real lines (never a candidate's
    hypothesis, never a broken grid) -- the physical staff doesn't move
    just because this instrument is testing a broken one."""
    half_step = row["spacing_px"] / 2.0
    true_lines = [row["nominal_ys"][i] + row["orange_shift"] for i in range(5)]
    thickness = line_thickness_px(row["staff"], row["spacing_px"])
    half_th = max(1.0, thickness / 2.0 + 1.0)
    scores = {}
    for cand in (lower, upper):
        cy = place_top_y + cand * half_step
        x0, x1, y0, y1 = standard_head_box(row["x_center"], cy, row["spacing_px"])
        scores[cand] = box_ink_coverage(binary, x0, x1, y0, y1, true_lines, half_th)
    return scores


def decide(scores):
    """Returns (decided_step_or_None, diff, winner_score). Margin rule
    stated at the top of this file, applied verbatim here."""
    vals = {k: v for k, v in scores.items() if v is not None}
    if len(vals) < 2:
        return None, None, None
    (c1, s1), (c2, s2) = sorted(vals.items())
    diff = abs(s1 - s2)
    winner, winner_score = (c1, s1) if s1 >= s2 else (c2, s2)
    if diff >= MARGIN and winner_score >= MIN_WINNER:
        return winner, diff, winner_score
    return None, diff, winner_score


def true_candidates(pos):
    lower = math.floor(pos)
    upper = lower + 1
    return lower, upper


def build_row_generic(inner, pw, sub):
    """Same row shape boundary_measure.py's own rows use, built directly
    for an arbitrary subject (not restricted to its KEPT-only filter)."""
    staff_key = r48.staff_key_of(sub)
    cell_key = r48.cell_key_of(sub)
    staff = r48.duck_staff(inner, staff_key)
    cell_box = r48.obs(inner, cell_key, "cell_box")
    if cell_box is None:
        return None
    x0, _y0, x1, _y1 = cell_box["value"]
    x0, x1 = int(x0), int(x1)
    gb = r48.obs(inner, sub, "glyph_box")
    if gb is None:
        return None
    x_center = gb["detail"]["x_center_page"]
    y_center = gb["detail"]["y_center_page"]
    box_page = gb["detail"].get("bbox_page_px")
    spacing_px = float(staff.line_spacing_px)
    nominal_ys = [float(y) for y in staff.line_ys]
    pws = PageWithStaves(page=pw, staves=[staff], barlines=[])
    offset = me._cell_line_offset(pws, staff, x0, x1)
    orange_shift = float(offset[0]) if offset is not None else 0.0
    half_step = spacing_px / 2.0
    top_y = nominal_ys[0] + orange_shift
    today_pos = (y_center - top_y) / half_step
    return dict(sub=sub, staff=staff, x0=x0, x1=x1, x_center=x_center,
                y_center=y_center, box_page=box_page, spacing_px=spacing_px,
                nominal_ys=nominal_ys, orange_shift=orange_shift,
                today_pos=today_pos, cell_key=cell_key)


def mean_std(xs):
    if not xs:
        return None, None
    if len(xs) < 2:
        return xs[0], 0.0
    return statistics.mean(xs), statistics.pstdev(xs)


def main():
    # ─── reuse boundary_measure's own dist-to-boundary-labelled rows ────
    all_rows, near = bm.main()
    print("\n" + "=" * 70)
    print("ROADMAP 2.48 headfit -- two-candidate ideal-head ink-coverage fit")
    print(f"MARGIN={MARGIN}  MIN_WINNER={MIN_WINNER} (stated before results)")
    print("=" * 70)

    pw = render_page_matching_gather(bm.PROVENANCE_PDF, bm.PAGE_IDX, dpi=bm.DPI)
    binary = pw.binary

    # ─── Step 1(a)/(b)/(c): 15 clean heads, far from any boundary ───────
    clean_candidates = [r for r in all_rows if r["dist_boundary_px"] > 3.0]
    clean, seen_cells = [], set()
    for r in clean_candidates:
        if r["cell_key"] in seen_cells:
            continue
        seen_cells.add(r["cell_key"])
        clean.append(r)
        if len(clean) >= 15:
            break
    print(f"\n--- CONTROL (a): {len(clean)} clean heads (>3px from boundary) ---")

    a_ok = 0
    true_steps = {}
    for r in clean:
        lower, upper = true_candidates(r["today_pos"])
        true_step = int(round(r["today_pos"]))
        true_steps[r["sub"]] = true_step
        top_y = r["nominal_ys"][0] + r["orange_shift"]
        scores = fit_scores(r, binary, lower, upper, top_y)
        step, diff, wscore = decide(scores)
        ok = (step == true_step)
        a_ok += int(ok)
        print(f"  {r['sub']:<22} true_step={true_step:>3} fit={step} "
             f"diff={diff if diff is None else round(diff,3)} "
             f"scores={{{lower}: {None if scores[lower] is None else round(scores[lower],3)}, "
             f"{upper}: {None if scores[upper] is None else round(scores[upper],3)}}} "
             f"{'OK' if ok else 'MISS'}")
    print(f"CONTROL (a) result: {a_ok}/{len(clean)} picked today's step "
         f"(bar: >=14/15)")

    print(f"\n--- CONTROL (b): same heads, box y shifted +3px / -3px ---")
    b_trials, b_ok = 0, 0
    for r in clean:
        true_step = true_steps[r["sub"]]
        top_y = r["nominal_ys"][0] + r["orange_shift"]
        half_step = r["spacing_px"] / 2.0
        for shift in (+3.0, -3.0):
            pos_shifted = (r["y_center"] + shift - top_y) / half_step
            lower, upper = true_candidates(pos_shifted)
            scores = fit_scores(r, binary, lower, upper, top_y)
            step, diff, wscore = decide(scores)
            b_trials += 1
            ok = (step == true_step)
            b_ok += int(ok)
            print(f"  {r['sub']:<22} shift={shift:+.0f}px bracket=({lower},{upper}) "
                 f"fit={step} true={true_step} {'OK' if ok else 'MISS'}")
    print(f"CONTROL (b) result: {b_ok}/{b_trials} still picked the true step "
         f"under a +/-3px box-y perturbation")

    print(f"\n--- CONTROL (c): same heads, STAFF LINES shifted a half-step "
         f"(deliberately broken) ---")
    c_trials, c_wrong_or_abstain = 0, 0
    for r in clean:
        true_step = true_steps[r["sub"]]
        lower, upper = true_candidates(r["today_pos"])
        top_y = r["nominal_ys"][0] + r["orange_shift"]
        half_step = r["spacing_px"] / 2.0
        broken_top_y = top_y + half_step
        scores = fit_scores(r, binary, lower, upper, broken_top_y)
        step, diff, wscore = decide(scores)
        c_trials += 1
        failed = (step != true_step)  # wrong OR abstained both count as "fails visibly"
        c_wrong_or_abstain += int(failed)
        print(f"  {r['sub']:<22} true_step={true_step:>3} fit_under_break={step} "
             f"{'FAILS (as expected)' if failed else 'still right (unexpected)'}")
    print(f"CONTROL (c) result: {c_wrong_or_abstain}/{c_trials} failed visibly "
         f"(wrong or abstained) under the broken grid (bar: most)")

    print(f"\n--- CONTROL (d): 3 merged two-head blobs -- must abstain ---")
    full = bm.load_record(bm.ARM_RECORD)
    inner = full["record"]
    d_abstained = 0
    for sub in MERGED_SUBJECTS:
        row = build_row_generic(inner, pw, sub)
        if row is None:
            print(f"  {sub:<22} -- subject not found in record, skipped")
            continue
        lower, upper = true_candidates(row["today_pos"])
        top_y = row["nominal_ys"][0] + row["orange_shift"]
        scores = fit_scores(row, binary, lower, upper, top_y)
        step, diff, wscore = decide(scores)
        abstained = step is None
        d_abstained += int(abstained)
        print(f"  {sub:<22} today_pos={row['today_pos']:.3f} bracket=({lower},{upper}) "
             f"scores={{{lower}: {None if scores[lower] is None else round(scores[lower],3)}, "
             f"{upper}: {None if scores[upper] is None else round(scores[upper],3)}}} "
             f"fit={step} {'ABSTAINED (expected)' if abstained else 'DECIDED (unexpected)'}")
    print(f"CONTROL (d) result: {d_abstained}/{len(MERGED_SUBJECTS)} abstained")

    # ─── gate: stop here (no scoring) unless all of (a)-(c) behave ─────
    a_pass = a_ok >= 14
    b_pass = b_ok >= int(0.9 * b_trials)
    c_pass = c_wrong_or_abstain >= int(0.5 * c_trials)
    print(f"\n--- GATE: (a) {'PASS' if a_pass else 'FAIL'}  "
         f"(b) {'PASS' if b_pass else 'FAIL'}  (c) {'PASS' if c_pass else 'FAIL'} ---")
    if not (a_pass and b_pass and c_pass):
        print("CONTROL DID NOT PASS -- STOPPING, no Step 2 scoring run.")
        return

    # ─── Step 2: the 42 within-1px / 109 within-2px population ─────────
    print("\n" + "=" * 70)
    print("STEP 2: scoring on the 42-within-1px / 109-within-2px population")
    print("=" * 70)

    works_row = r48._load_works_row(r48.WORKS_ROW_ID)
    ref_root = r48._reference_root(works_row["reference"]["catalog_path"])
    family_map = r48._FAMILY_MAPS[r48.DOC_ID]
    expected = r48.expected_positions_for_page(inner, ref_root, family_map, bm.PAGE_IDX)

    within1 = [r for r in all_rows if r["dist_boundary_px"] < 1.0]
    within2 = near  # bm.main()'s own <=2px set, already 109

    def run_population(pop, label):
        decided_n, abstained_n = 0, 0
        today_right, today_wrong = 0, 0
        fit_right, fit_wrong = 0, 0
        scored_rows = []
        for r in pop:
            lower, upper = true_candidates(r["today_pos"])
            top_y = r["nominal_ys"][0] + r["orange_shift"]
            scores = fit_scores(r, binary, lower, upper, top_y)
            step, diff, wscore = decide(scores)
            if step is None:
                abstained_n += 1
                fit_step = int(round(r["today_pos"]))  # abstain -> keep today's
            else:
                decided_n += 1
                fit_step = step
            if r["is_scored"]:
                exp = expected.get(r["sub"])
                if exp is None:
                    continue
                today_step = int(round(r["today_pos"]))
                scored_rows.append((r["sub"], today_step, fit_step, exp, step is not None))
                if today_step == exp:
                    today_right += 1
                else:
                    today_wrong += 1
                if fit_step == exp:
                    fit_right += 1
                else:
                    fit_wrong += 1
        print(f"\n{label}: n={len(pop)}  decided={decided_n}  abstained={abstained_n}")
        print(f"  reference-scored subset: n={len(scored_rows)}")
        print(f"  TODAY  right={today_right} wrong={today_wrong}")
        print(f"  FIT    right={fit_right} wrong={fit_wrong}")
        for sub, t, f, e, was_decided in scored_rows:
            flag = "DECIDED" if was_decided else "abstained->today"
            print(f"    {sub:<22} today={t:>3} fit={f:>3} expected={e:>3} ({flag}) "
                 f"{'today_right' if t==e else 'today_WRONG'} "
                 f"{'fit_right' if f==e else 'fit_WRONG'}")
        return dict(n=len(pop), decided=decided_n, abstained=abstained_n,
                   scored=len(scored_rows), today_right=today_right,
                   today_wrong=today_wrong, fit_right=fit_right, fit_wrong=fit_wrong)

    res1 = run_population(within1, "WITHIN 1px (42)")
    res2 = run_population(within2, "WITHIN 2px (109)")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"within1: {res1}")
    print(f"within2: {res2}")


if __name__ == "__main__":
    main()
