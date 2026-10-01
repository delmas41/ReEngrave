# Measure against the staff LOCALLY — ROADMAP 2.48

CLAUDE.md §10 (2026-09-30, Sean): "anything that uses geometry compared to
the staff needs to be measuring locally instead of globally on the staff."
This lane builds the audit the roadmap item asks for, then one local
staff-line model, wired into ONE consumer (`gather_notehead_positions`) as
the brief directed. Every other consumer is listed, not touched.

## Part 1 -- the audit

`gather._cell_grid(cell)` reads `cell.staff_line_ys_canonical`: five ideal
rows, ONE FLAT GRID for the whole measure cell. That grid is already a
*per-cell* value (not the raw staff-wide `Staff.line_ys`) when
`_cell_line_offset` succeeds -- a single rigid shift for the whole cell,
picked by sliding the comb to the best-scoring position -- but it falls back
SILENTLY to the staff-wide `Staff.line_ys`, copied unchanged into the
cell, whenever `_cell_line_offset` declines: a cell narrower than
`CELL_LINE_MIN_WIDTH_SPACES` (4 staff spaces), a shift under the
`CELL_LINE_MIN_SHIFT_SPACES` (0.05 sp) noise floor, or fewer than
`CELL_LINE_MIN_ROWS_COVERED` (4 of 5) rows clearing `CELL_LINE_MIN_ROW_COVERAGE`
(45%) ink coverage. That silent fallback is exactly what CLAUDE.md §10 and
the 2026-09-30 DECISIONS line ("the green staff lines are not lined up")
measured: at Litolff p3 bar 55 the cell grid equals the staff-wide lines,
~2.5 px off the print, and at Sean's confirmed D6 (`glyph/3/0/0/2/9`) the
flat grid answers -5.56 (E6, wrong) against -5.42 (D6, right) off the
PRINTED lines at the head's own x.

| consumer | file:function | reads today | local? |
|---|---|---|---|
| notehead staff position | gather.py:gather_notehead_positions | _cell_grid(c) | YES, as of this lane -- tries gather._local_cell_grid_at(c, page_x) at the head's own x first, falls back to _cell_grid(c) (recorded: local_staff_lines detail) |
| in-bar accidental position | gather.py:gather_accidental_positions | _cell_grid(c) | no |
| clef glyph position on its staff | gather.py:gather_clef | _cell_grid(by_key.get(...)) at the staff's first cell | no |
| key-signature run position | gather.py:gather_key_signature | per-cell grid (header cell) | no |
| meter digit / meter-at-bar position | gather.py:gather_meter, gather_meter_at_bars, gather_meter_ocr_at_bars | per-cell canonical staff_line_ys_canonical window split (line_ys[2]) | no |
| cross-staff ownership: band distance, ladder, ledger-rung ink, ledger-owner density | gather.py:gather_ownership_evidence (_observe_ledger_owner_density, _observe_ledger_rung_ink, _band_distance_spaces, the ladder term) | st.line_ys directly -- the STAFF-WIDE page-pixel lines off pws.staves, built once into a geom dict at the top of gather_ownership_evidence, not even the per-cell flat grid | no -- this is the least-local consumer in the pipeline, and CLAUDE.md §10's own ledger rules ("the ledger lines are authoritative", "there is no such thing as a far note with no ledger line") are adjudicated on this exact reading |
| wedge/hairpin anchor position | gather.py:gather_wedge_boxes / _notehead_boxes_for_cell | per-cell grid | no |
| standard head box sizing from spacing | geometry.standard_head_box (reads Q.CELL_STAFF_SPACE, itself from _cell_grid) | per-cell grid, one scalar per cell | no |
| notehead ink / recentre / stacked-head fit | gather.py:gather_notehead_ink, gather_notehead_recentre, gather_stacked_head_fit | per-cell grid | no |
| CV line reader (gather_cv_lines) | gather.py:gather_cv_lines | per-cell grid, twice | no |
| ledger ink reader | gather.py:gather_ledger_ink | per-cell grid | no |

Fallback counts on the two count pages: not re-gathered for this lane
(Sean, 2026-09-29: microscopic tests, not pricing runs -- a page re-gather is
a pricing run and this lane's proof is unit tests plus the one reproduced
number below). The DECISIONS-line measurement already gives one concrete
instance (Litolff p3 bar 55, flat grid == staff-wide, ~2.5 px off) and
2.44c's own FINDINGS §13 record the staff wandering 447-454 px (7 px, ~5%
spacing change) across staff/3/0/0's own system -- i.e. within ONE staff, let
alone one cell, well past the rigid-shift mechanism's single-number model.

## Part 2 -- the local model, and the one consumer

Design, in two lines. `measure_extractor._trace_cell_local_lines`
follows each of the staff's 5 printed lines across the CELL's own x-band,
reusing `header_ink.trace_staff_line` (the same column-by-column tracer
staff-line erasure already runs) with its search window widened to
`CELL_LINE_MAX_SHIFT_SPACES` (0.75 sp) -- its own default (0.35 sp) could not
follow the ramp this model exists to read, proven by the first run of this
lane's own synthetic ramp test. `gather._local_cell_grid_at(cell, page_x)`
reads the traced path at one column, converts it to the cell's canonical
frame (the same transform every other canonical quantity already uses:
(page_y - bbox_y0) * upscale_factor), and returns (top_y, half_step) --
the exact tuple _cell_grid returns, so a caller that gets one back cannot
tell which model answered except by the records kept alongside it.

Abstention, never a silent fallback further than today. ALL FIVE LINES
OR NOTHING (measure_line_geometry's own policy): a cell too narrow, too
faint, or with the flag off has no local model at all, and the glyph loop
falls back to _cell_grid(c) -- exactly today's behaviour, not a new,
further fallback -- and records which grid answered
(Q.NOTEHEAD_STAFF_POSITION.local_staff_lines, True/False). This is
recorded on EVERY row, not just the ones that disagree, so a later consumer
or a crop can always ask.

Consumer wired: gather.gather_notehead_positions only, as the brief
directed. Every other consumer in the table above is a next step, in the
priority Sean's own convention writing implies:

1. Cross-staff ownership (gather_ownership_evidence's geom dict) -- the
   LEAST local reading in the pipeline today (raw Staff.line_ys, not even
   the per-cell flat grid), and CLAUDE.md §10's ledger rules are adjudicated
   directly on it.
2. Accidental / clef / key-signature / meter positions -- same _cell_grid
   mechanism as the notehead reader, so the same wiring pattern applies with
   no new design.
3. Standard head box sizing, CV line reader, notehead ink/recentre/stacked
   fit -- lower priority: these size or re-locate an already-placed box
   rather than naming a staff position directly.

## Proof

tools/omr/tests/test_local_staff_lines.py, 9 tests, RED->GREEN (the first
run of test_two_ends_of_one_cell_read_different_lines failed red -- the
default search window undershot the ramp by half; fixed by widening it, see
above):

- a synthetic tilted staff: the two ends of ONE cell read different local
  lines (14 px ramp recovered at both ends within 2 px), a flat staff traces
  to the nominal row everywhere (control), and no staff ink under a band
  abstains (a control that can fail).
- _build_measure_cell stores the model on the cell and the flag disables
  it cleanly.
- _local_cell_grid_at reproduces Sean's own number exactly: printed
  lines at x=902 (450.5/466.5/481.5/497.5/513.5), box centre 407.8 ->
  top_y=450.5, half_step=7.875 -> position -5.42 (D6), matching
  DECISIONS 2026-09-30 to two decimal places.
- gather_notehead_positions prefers the local grid over a deliberately
  wrong flat grid on a fake cell, and tags the row local_staff_lines=True.

## REAL RESULT (manager-directed small re-gather, 2026-10-01): NOT MERGE-READY -- a net regression

Per the manager's review of `61cf3844`, the microscopic-test-only proof above
was superseded by an actual run: `python3 -m tools.omr.acceptance_quick
--doc beethoven5-litolff` and `--doc brahms1-breitkopf`, base = `origin/main`
`8f1b2228` in its own worktree, arm = this branch at `86d0bf68`
(`--weights auto`, `OMR_DIRECTION_TEXT_SCAN_GATE=1`; `--full` for the
EVALUATE-stage pitch needed to score against the reference).

**Cell-level fallback counts, count page only** (`measure_extractor.
extract_measures` run directly against the rendered page): Litolff p3
320/320 cells traced locally, 0 fell back to a measured flat grid, 0 fell
back further. Brahms p1 202/202, same. **Not many fall back** -- the model
answers almost every cell on its own.

**Head-level abstentions** (`ABSTAIN.GRID_NOT_LOCALIZED`, the whole
GATHER+ADJUDICATE small re-gather, pages 1-3 / 0-1): Litolff 6 of 1330
notehead glyphs (0.45%), Brahms 0 of 1502. Small, not a concern on its own.

**GATHER+ADJUDICATE readout diff** (`tools.omr.staged.readout diff --force
--arm code`, base vs arm, Litolff p3): 1065 differences. `notehead_staff_
position` changed on 1058 of 1330 noteheads (almost every one, since the
local model answered almost every cell) -- changes are mostly sub-0.5-space
fractional shifts, but 7 of them cross a rounding boundary far enough to
flip an `accidental_owner` ADJUDICATE verdict.

**2.44c reference-backed truth set, adapted** (`truth_set_2_44c.py` copied
from branch `worktree-agent-ac053ee5c8a371951` into this directory; its own
`_far_head_subjects` depends on the UNMERGED 2.44 ledger-reader quantities
(`Q.LEDGER_CLEAN_COUNT_POSITION`/`Q.LEDGER_RUNG_GRID_POSITION`), absent on
this tree -- confirmed by `AttributeError` running it unmodified, so "far"
was reclassified geometrically here (position outside the 5-line staff,
strictly WIDER than the ledger gate) in a small adapter script, scoring
EVERY notehead, far and in-staff, base vs arm, onset-exact against the
reference, reusing `onset_exact_truth` unchanged):

| doc | bucket | base (right/wrong/unscored) | arm (right/wrong/unscored) |
|---|---|---|---|
| Litolff p3 | far | 121 / 42 / 350 | 84 / 54 / 342 |
| Litolff p3 | in-staff | 289 / 16 / 512 | 234 / 96 / 514 |
| Brahms p1 | far | 16 / 0 / 589 | 11 / 2 / 531 |
| Brahms p1 | in-staff | 114 / 0 / 783 | 88 / 29 / 841 |

**Every head whose verdict changed, base to arm, head by head** (646 lines,
not reproduced in full here -- in `/tmp/score_2_48_v2.out` this session,
not committed): Litolff **103 right -> wrong, 11 wrong/unscored -> right**;
Brahms **31 right -> wrong, 0 -> right**. Combined: **134 regressions
against 11 improvements.**

**This fails the manager's own keep criterion** ("wrong->right with no
right->wrong, or a net gain verified head by head") outright -- it is a
clear net loss, not a close call. Two sampled regressions (`glyph/1/0/7/12/1`
D5->E5 at pos 1.66->1.28; `glyph/1/0/7/15/0` G5->F5 at pos -1.26->-0.41)
both cross a rounding boundary by a small, locally-measured shift -- **not
crop-verified against the print**, so which reading is actually right on
the page is not established here, only that the local model disagrees with
the reference encoding more often than the flat grid does on this page.

**Suspected cause, not confirmed**: `_cell_line_offset`'s rigid comb-slide
is a single whole-cell vote over all five lines together (robust to one
line's ink being contaminated by a nearby notehead); `trace_staff_line`
traces each line INDEPENDENTLY, column by column, with no cross-line
coherence check, and this lane widened its search window to 0.75 spaces
(from its own 0.35 sp default) specifically so it could follow a real tilt
-- the same widening may let it lock onto nearby glyph ink (a stem, a
ledger, a beam) at a given column instead of the true staff line, exactly
where notes are densest. NOT diagnosed further this lane (time); the next
step is crop-verifying a handful of the 134 regressions against the print
before any narrower search window or a coherence check is tried.

**Recommendation: do not merge.** The model and its tests stand (Sean's own
D6 number is reproduced exactly, and the synthetic controls hold), but the
accuracy claim does not -- CLAUDE.md rule 7 applies ("a convincing number is
not evidence about its cause"): the mechanism measures something, but not
yet the right thing on real ink.

## staged.check

`pytest -m "not slow" tools/omr/tests`: 4,190 passed, 0 failed.
`python3 -m tools.omr.staged.check`: TOTAL **245** (confirmed against
`8f1b2228` directly), no new flag, no new unread detail key.

## Not verified

- The two sampled regressions above are NOT crop-verified against the
  print -- which reading (local or flat) is actually right is not
  established, only that the local model disagrees with the reference MORE
  on this page.
- The suspected cause (independent per-line tracing vs the rigid comb's
  cross-line coherence) is a hypothesis, not confirmed by a targeted test.
- `/tmp/score_2_48_v2.out`'s full 646-line per-head listing is not
  committed to the tree (ran from a scratch location); the counts above are
  read directly from it and are reproducible by re-running the adapter
  script against the same two record pairs.

## REBUILD 2026-10-01: Sean's own design -- the comb walked along the ink, replacing the independent per-line trace

Sean's instruction, verbatim: *"As it works currently a straight line is
aligned with the 5 staff lines. Once the straight lines are laid out, can
it be measured against the ink, and where they begin to differ the straight
line starts to change direction to match what the ink is doing?"*

Built as specified in `measure_extractor._walk_comb_shift` /
`_trace_cell_local_lines` (same signature, same callers -- `gather.py`
needed NO changes this round): the comb starts at the staff's own rigid,
already-measured `line_ys` (shift 0). Walked along x in quarter-space steps
(`CELL_LINE_WALK_STEP_SPACES`). At each step every one of the 5 lines is
checked in a NARROW window (+-0.25 space) around where the comb CURRENTLY
predicts it (an ink-weighted centroid, `_measure_ink_centroid`) -- not the
withdrawn design's widened 0.35+ space search. The comb updates as ONE
SHAPE: the median candidate shift across whichever lines found clean ink,
outliers beyond 1px dropped, and the comb only moves where >=3 of 5 still
agree (Sean's own floor); fewer agree and it HOLDS its last course exactly.
Per-step change is capped and the whole course is smoothed with a running
median. 14 unit tests, including two built specifically to prove the new
rules: an outlier line's own 6px displacement never moves the comb (follows
the other 4), and a blob covering 4 of 5 lines' windows holds the comb
exactly rather than drifting toward it. Sean's D6 reproduction and the
flat-staff control are unchanged.

**Real test, same proof as the withdrawn attempt** (`acceptance_quick
--full`, base = `origin/main` `8f1b2228` in its own worktree, arm = this
branch `f21e8d71`):

| doc | bucket | base (right/wrong/unscored) | arm (right/wrong/unscored) |
|---|---|---|---|
| Litolff p3 | far | 121 / 42 / 350 | 102 / 60 / 365 |
| Litolff p3 | in-staff | 289 / 16 / 512 | 246 / 60 / 497 |
| Brahms p1 | far | 16 / 0 / 589 | 15 / 2 / 596 |
| Brahms p1 | in-staff | 114 / 0 / 783 | 97 / 16 / 776 |

**Per-head changes**: Litolff 66 right->wrong, 4 wrong->right; Brahms 18
right->wrong, 0 wrong->right. **Combined: 84 regressions against 4
improvements.** Better than the withdrawn independent-trace design (134/11)
-- roughly 37% fewer regressions -- but **still a clear net loss, failing
the "right->wrong ~0" bar** this rebuild was asked to clear.
GATHER+ADJUDICATE readout diff: 847 differences (was 1065), 844 of 1330
notehead positions changed on Litolff (was 1058).

**Crops, 8 of them** (`benchmarks/omr-local-staff-2026-09/out/print/`,
drawn at 600 dpi: orange = the base's flat per-staff comb, green = the new
walked comb, red = the head's own detector box), 4 heads the base got
wrong and 4 the WITHDRAWN independent-trace design broke:

- `base_wrong_1.png`, `base_wrong_2.png`: the new comb sits a small,
  plausible distance below the flat comb and tracks it closely -- ordinary,
  unremarkable corrections.
- `base_wrong_3_now_fixed.png`, `base_wrong_4_now_fixed.png`: the head sits
  right at a line/space boundary; the new comb's small offset is exactly
  what flips its pitch to match the reference (both are among the 4
  wrong->right head-by-head above).
- `prev_attempt_regression_1.png`..`_3.png`: green and orange are nearly
  identical here -- the withdrawn design's own failure on these heads does
  NOT reproduce with the new comb.
- **`prev_attempt_regression_4_still_wrong.png`: the new comb is VISIBLY,
  CONFIRMED WRONG** -- it diverges from the true printed lines by close to
  a full staff space over a short stretch, exactly where three noteheads
  sit close together as a dense chord cluster. This is the SAME x-region
  (`glyph/1/0/8/0/5`, `/0/6`, `/0/7`, page x~912-988) driving 3 of the 66
  Litolff regressions, and it is now CROP-CONFIRMED, not merely suspected:
  dense chord ink in the narrow +-0.25-space search window produces enough
  agreeing "ink" across >=3 lines to satisfy the update rule even though
  that ink is the CHORD's, not the staff's -- the per-step cap slows the
  drift but does not stop it from accumulating across many steps through a
  wide dense region.

**Recommendation: still do not merge.** The specific failure mode asked
about last time (one outlier line dragging the comb) is fixed and proved
fixed by a dedicated test; the mechanism is visibly better-behaved in
ordinary ink. But a NEW, confirmed failure mode replaces it: sustained
dense ink (a chord cluster, not a single stray mark) can still walk the
comb away from the true lines, because the >=3-of-5 agreement rule cannot
tell "3 lines agreeing on the true staff" from "3 lines agreeing on the
same wrong ink" -- CLAUDE.md rule 7 again: the mechanism measures
something, and this time it is visibly closer, but still not reliably the
right thing on real ink. Next step, not attempted here (time): bound the
comb's TOTAL drift against the page's own globally-measured spacing/skew
(e.g. refuse an update that would move the comb further from the staff's
own `_cell_line_offset` baseline than the measured wander ever reaches,
~0.5 spaces), rather than only capping the PER-STEP change.

`pytest -m "not slow"` 4,190 passed (unaffected). `staged.check` TOTAL 245,
unchanged. No new flag.

## 2026-10-01 continued: bias diagnosis, then Sean's two fixes (centre not edge; clean columns only)

**Bias diagnosis, before adding a drift bound** (manager-directed, a control
that can fail): of the 84 right->wrong heads, direction was NOT one-sided
-- 52 moved UP, 31 DOWN, 1 unchanged (62%/37%, a lean, not a dominant bias).
Magnitude split the population instead: 55 of 84 carried a >3px excursion
(up to -11.18px, past a full staff LINE on some staves -- aliasing), while
the other 29 clustered around a small, real but modest mean (-0.28px).
**Conclusion: the dominant fault was aliasing/drift, not a uniform
systematic offset** -- so the total-drift bound (`CELL_LINE_WALK_MAX_TOTAL_
SPACES`, 0.3 spaces) was added first, as planned.

**Drift bound alone, real re-gather**: Litolff 65 right->wrong / 4
wrong->right, Brahms 18/0 -- combined **83/4**, barely moved from 84/4.
Confirms the bound alone does not fix the underlying measurement.

**Sean, reviewing the comb-walk's own crops**: *"The green is much closer
to the ink but it moves every time it runs into a symbol that crosses the
staff and when the ink collects at a bar line ... The green line is on the
ink but towards the TOP of the ink."* Two fixes, as specified:

1. **Centre, not edge.** `_measure_line_run_mid` replaces the withdrawn
   ink-weighted centroid: walks outward from the ink nearest the search
   window's centre to that run's own top/bottom edge and uses the
   midpoint. Proven directly (`TestCentreNotEdge`): the midpoint survives a
   window whose own centre sits near the run's bottom edge, where the old
   centroid would have been pulled off-centre.
2. **Clean columns only.** A column contributes only where its run's
   thickness is within `CELL_LINE_WALK_CLEAN_THICKNESS_MULT` (1.6x) of the
   staff's own measured line thickness; barline columns (ink across
   `CELL_LINE_WALK_BARLINE_FRAC` of the whole staff span) and their own
   +-2px neighbours are excluded outright. The comb now COMMITS a move only
   after `CELL_LINE_WALK_MIN_CONSISTENT_RUN` (3) consecutive clean,
   mutually-agreeing steps -- a single accepted column can no longer move
   it. Proven directly (`TestBarlinesAndConsistencyRun`): a barline column
   is detected and excluded; a single clean, agreeing step alone cannot
   move the comb.

**Real re-gather with both fixes (and the drift bound)**: Litolff 59
right->wrong / 4 wrong->right, Brahms 18/0 -- combined **77/4**. Modest
improvement over the drift-bound-alone number (83->77, ~7%), far short of
the "right->wrong ~0" bar. **The specific bias Sean caught ("towards the
top") is fixed by design and proven fixed by a direct test, but it was not
the dominant cause of the 84 regressions** -- consistent with the earlier
direction histogram (a 62/37 lean, not an overwhelming one-sided bias).

**Strips for Sean** (`out/print/strips/`, 600 dpi, orange=base flat comb,
green=new comb, grey tick=held step, green tick=committed update):
- `litolff_p3_staff3_0_0_flutes_seg{0,1}.png` (his own confirmed chords'
  staff): **max separation 0.00px across the whole system** -- the comb
  never moves here at all under the new, stricter gates (a control that
  passes, but also a sign the fixes may now be more conservative than
  needed on an ordinary staff).
- `litolff_p1_staff1_0_8_dense_chord_seg{0,1}.png` + one 4x zoom inset: the
  worst-case staff from the regression list. Max separation dropped from
  the earlier ~11px aliasing to **3.78px**, and the zoom shows WHY: the
  divergence sits immediately after a barline, where a printed CLEF's own
  dense ink crosses all 5 lines right at the edge of the barline-exclusion
  margin -- bounded and far more plausible than before, but still a real,
  visible disagreement with the print, not a clean match.

**Recommendation: still not merged.** Both of Sean's specific faults are
fixed and proven fixed in isolation; the real-page number moved in the
right direction but only modestly (84->77 of ~1300-1500 heads per page).
Not chased further this round (time): why the clean-column/consistency-run
gates still admit enough contaminated steps to drive 77 regressions is
unexplained -- the next diagnostic step, not attempted here, is a
head-by-head crop review of the 77 (not just the one worst staff) to see
whether a SECOND, different fault is still at work, or whether the
remaining regressions are genuinely close calls where the comb's answer
and the reference disagree for reasons outside this mechanism (e.g. a
detector box itself slightly mis-placed).

`pytest tools/omr/tests/test_local_staff_lines.py` 19 passed;
`test_cell_line_localization.py` + `test_staged_pipeline.py` 47 passed
(not the full fast tier this round, time). `staged.check` TOTAL 245,
unchanged. No new flag.

## 2026-10-01 continued: is the 77 actually the comb? A/A control + per-head attribution

**A/A control** (CLAUDE.md §6b non-determinism check): base tree (`8f1b2228`)
gathered twice, separate worktrees, same command, scored against the same
truth set. **0 right->wrong / 0 wrong->right on both docs.** This pipeline
is byte-deterministic for this exact command/weights/env; the 77 is not run
noise.

**Per-head attribution, all 77 right->wrong (+ the 4 wrong->right)**: for
each, compared the detector's own `Q.GLYPH_BOX` (base vs arm -- **identical
on all 81**, zero box differences anywhere) and recomputed the comb's shift
at that exact head's x (base's own staff lines, arm's code).

- **38 of 77** right->wrong (and 3 of 4 wrong->right) have `|shift| < 0.1
  step` -- the comb barely moved this head at all, yet its scored pitch
  still flipped. Box identical, geometry near-identical: **these flips are
  NOT the comb's doing.** Not chased further this round (time), but the
  likely mechanism is a cascade through ADJUDICATE/EVALUATE (chord/event
  grouping, voicing, or stack-rank assignment) triggered by a DIFFERENT
  head's position change elsewhere in the same bar, not by this head's own
  measurement.
- **39 of 77** right->wrong (and 1 of 4 wrong->right) have `|shift| >= 0.1
  step` with an identical box -- attributable to the comb.

**The comb's real, attributable effect: 39 right->wrong vs 1 wrong->right.**
Smaller in absolute count than the raw 77/4, but the same decisive
direction -- still a clear net regression, not close to the "right->wrong
~0" bar. The other ~41 flips in the raw count are a confirmed SEPARATE
fault (unchanged box, unmoved comb, flipped verdict) and should not be
charged to this mechanism or used to judge it further; they are a distinct
open question for whoever investigates ADJUDICATE/EVALUATE's own
sensitivity next.

**Recommendation unchanged: do not merge.** The comb's own measured effect
(39/1) is now isolated from an unrelated ~41-flip artefact the raw A/B was
conflating it with.

## CORRECTION 2026-10-01: the "39/1 attributable" claim was wrong -- a bug in the attribution script, not a cascade

Re-investigating the manager's judge question (did `Q.NOTEHEAD_STAFF_
POSITION`'s rounding actually change for the 38 "cascade" heads) found the
root cause: `attribution_2_48.py` recomputed the comb's shift by calling
`_walk_comb_shift` fresh over an AD HOC +-150px window around each head,
starting its own walk at `shift=0` from THAT window's x0 -- a different
starting point than the real gather used (the cell's own x0). The walk's
hold/commit history depends on where it starts, so this recomputation does
not reproduce the production value and is not evidence about anything.

**Corrected check**: read `Q.NOTEHEAD_STAFF_POSITION`'s own STORED value
directly from both the base and arm records (no recomputation at all) for
all 81 subjects (77 right->wrong + 4 wrong->right). **All 81 have an
identical detector box AND a genuinely changed rounded position.** Zero
are a judge/cascade artifact; the earlier "38 of 77 are not the comb's
doing" finding does not hold -- it was this script's own bug.

**The comb's real, attributable effect is the full 77 right->wrong vs 4
wrong->right** (box always identical, so it is purely the comb's
geometric effect on the position, never a detector difference) --
matching the raw score exactly. No fix to `truth_set_2_44c.py` is needed;
there is no re-pairing bug to find, because there is no cascade.
Recommendation unchanged: do not merge. The compensating-bias and 12-head
trace questions this (now withdrawn) finding prompted do not need
answering on this premise.

## 2026-10-01: GATHER+ADJUDICATE-only judge (Sean: "just the first 2 stages")

New judge (`gather_only_judge.py`): no `Q.PITCH`, no `restate_pitch`, no
export. Pairs OUR notehead sequence (detector box x,y order within a bar)
against the REFERENCE's (onset ascending, stack descending) by INDEX, never
by an estimated position. Bar number = `Q.PRINTED_BAR_NUMBER` (ADJUDICATE)
+ cell index. Family = staff ordinal -> `_FAMILY_MAPS`' P-number (stated
assumption: condensed layout, one staff per family, fixed all piece).
Reused the existing GATHER+ADJUDICATE rows inside the `--full` records
(EVALUATE/INFER/EXPORT only ADD verdicts, never mutate them) rather than
re-gathering.

**Litolff**: base 150 right/131 wrong/1039 unscored; arm 137/144/1039 --
**14 right->wrong / 1 wrong->right**. **Brahms**: 53/3/1446 both arms, 0
changed (same severe under-scoring as the full-pipeline judge). Of the
earlier 77 full-pipeline right->wrong heads, 10 are STILL a flip under
this independent judge -- the rest fall outside this judge's (much
smaller) scored population, not because they stopped flipping.

**No other first-two-stage verdict changed**: `readout diff` shows only
`notehead_staff_position` (844 of 1330) and `accidental_owner` (1 of 139)
differ; clef (87/87 matched, 0 changes) and glyph_owner/event grouping are
untouched.

**Conclusion for Sean**: the worsening is visible already at GATHER, under
a judge whose pairing cannot itself be moved by the comb -- it is in the
measurement, not a later stage. Recommendation unchanged: do not merge.

## 2026-10-01: compensating-bias measurement (Sean's hypothesis)

GATHER+ADJUDICATE only (`compensating_bias.py`). "Clean" = no chord-mate
within 1.5 spaces, no overlapping box, ink fraction in [0.12, 0.85] within
the detector's own box. Litolff 251 qualified, Brahms 100.

| | Litolff mean / std (px) | Brahms mean / std (px) |
|---|---|---|
| line bias (base grid - ink centre) | -0.94 / 3.45 (n=226) | +1.02 / 5.93 (n=231) |
| line bias (comb - ink centre) | -0.25 / 1.06 (n=83) | +0.01 / 0.28 (n=14) |
| head bias (box centre - head ink centre) | +0.43 / 3.04 (n=251) | +0.51 / 4.53 (n=100) |
| &nbsp;&nbsp;open / filled heads | +0.14 / +0.64 | -0.02 / +0.95 |
| &nbsp;&nbsp;on-line / in-space | +0.04 / +0.76 | +0.92 / +0.27 |

**Do the two errors cancel today? No, not reliably.** Cancellation needs
line bias and head bias to share SIGN and SIZE (error = head_bias -
line_bias). On Litolff the signs are OPPOSITE (line -0.94, head +0.43) --
the two errors ADD (~1.4px), they do not cancel. On Brahms the signs
happen to MATCH (line +1.02, head +0.51) -- partial cancellation there,
by coincidence, not by any structural relationship. Every number above
also carries a standard deviation several times its own mean (n in the
hundreds, so the means are measured, not noise, but the underlying spread
is large and real) -- there is no clean, page-independent compensating
relationship to find. The comb's own line bias is small on both pages
(-0.25, +0.01px) -- it is reading closer to true ink centre than the base
grid is, as designed.

**Per the manager's own conditional (build a corrected-judge arm only if
line and head bias share sign and size): that condition is not met**
(opposite signs on the page this mechanism was built against), so the
"comb lines + head ink centre" / "base lines + head ink centre" arms were
not built or scored this round.

4 crops at `out/print/bias/` (base grid=orange, comb=green where it did
not decline, head centre=magenta cross, detector box=red).

## 2026-10-01: trace the 14 right->wrong / 1 wrong->right stage by stage (Sean's directive)

Per-head trace of all 15 subjects from the GATHER+ADJUDICATE-only judge
(`gather_only_judge.py`, Litolff count page), read STRAIGHT off two fresh
re-gathers (base = `origin/main` `fd396df0` in a throwaway worktree, arm =
this branch, both `acceptance_quick --doc beethoven5-litolff`, default
GATHER+ADJUDICATE only, no recomputation of either grid -- `Q.NOTEHEAD_
STAFF_POSITION`'s own stored value, `Q.CELL_STAFF_SPACE`'s own stored
half-step, `glyph_box`/`event`/`clef`/`printed_bar_number` verdicts as
filed). Script: `trace_14_heads.py`. All 15 reproduced the a3ef66 lane's
own arm record's shift to several decimal places on independent re-gather
(same-code determinism, corroborating the already-recorded A/A control of
0/0 on both docs).

**Per-head table** (shift = arm pos - base pos, in staff-spaces; dist =
pos - 4, roughly staff-centre-relative; +/- large = outside the staff):

| subject | bar | clef | chord | dist(base) | shift | base->arm verdict |
|---|---|---|---|---|---|---|
| glyph/1/0/7/1/1 | 4+1 | treble | no | 4.52 | -0.035 | right->wrong |
| glyph/1/0/8/1/6 | 4+1 | treble | no | 4.46 | +0.064 | wrong->right |
| glyph/2/0/2/4/1 | 17+4 | treble | yes | 6.42 | +0.320 | right->wrong |
| glyph/2/0/3/0/5 | 17+0 | bass | yes | -6.20 | +1.024 | right->wrong |
| glyph/2/0/3/0/7 | 17+0 | bass | yes | -6.22 | +1.024 | right->wrong |
| glyph/2/0/3/3/2 | 17+3 | bass | yes | 3.04 | +0.764 | right->wrong |
| glyph/2/0/7/0/4 | 17+0 | treble | no | -3.18 | +0.760 | right->wrong |
| glyph/2/0/7/10/3 | 17+10 | treble | no | 3.48 | +0.028 | right->wrong |
| glyph/2/0/7/2/2 | 17+2 | treble | no | -2.78 | +0.620 | right->wrong |
| glyph/3/0/0/2/4 | 49+2 | treble | yes | -11.40 | -0.135 | right->wrong |
| glyph/3/0/8/0/3 | 49+0 | treble | no | 0.06 | +0.780 | right->wrong |
| glyph/3/0/8/0/4 | 49+0 | treble | no | 2.08 | +0.780 | right->wrong |
| glyph/3/0/8/0/5 | 49+0 | treble | no | 3.10 | +0.780 | right->wrong |
| glyph/3/0/8/0/8 | 49+0 | treble | no | 3.02 | +0.780 | right->wrong |
| glyph/3/1/0/6/0 | 65+6 | treble | no | -10.50 | -0.028 | right->wrong |

Detector box identical base vs arm on all 15 (zero exceptions, as the
09-30/10-01 attribution rounds already found for the full 81) -- every
flip here is purely the comb's geometric answer, never a detector
difference.

**Classification.** Two clean groups by `|shift|`, not a continuum:

- **5 of 15 (`|shift| < 0.15` sp): rounding-boundary flips.** The head's
  staff position sits almost exactly on a `.5` cusp in BOTH grids (base
  residuals 0.46-0.50); a few hundredths of a space from the comb's
  slightly different line reading tips the `round()` the other way. This
  group contains the ONE wrong->right head (`glyph/1/0/8/1/6`, +0.064) --
  it and its right->wrong neighbour at the same bar (`glyph/1/0/7/1/1`,
  -0.035) sit on ADJACENT staves of the same bar, both near-boundary,
  flipping in opposite directions. Not a mechanism fault so much as
  irreducible sensitivity where the true position is near a half-step.

- **10 of 15 (`|shift| >= 0.3` sp, up to a full space): DOMINANT CAUSE --
  a per-cell/per-chord disagreement between the flat grid and the comb
  that moves every head in that cell the SAME way.** All 10 are
  right->wrong and, notably, all 10 shifts are the SAME SIGN (positive)
  -- not a symmetric spread. Four of the ten are the SAME cell
  (`cell/3/0/8/0`, bar 49) sharing the identical shift (+0.780 sp) to
  three decimal places -- one comb decision, charged four times. Two more
  are one bass chord (`cell/2/0/3/0`, bar 17, glyphs 5+7) sharing +1.024.
  The other four (`cell/2/0/2/4`, `cell/2/0/3/3`, `cell/2/0/7/0`,
  `cell/2/0/7/2`) are each their own cell. **So the 10 heads are really
  only 6 independent comb decisions**, 4 of which land on more than one
  head because the comb's answer is a per-CELL (or per-chord-column)
  quantity, not a per-glyph one.

**Print check on the dominant cause** (`crop_14heads.py`, 3 crops at
`out/print/2.48/`, orange=base flat grid, green=an independently re-walked
comb for illustration [NOT the byte-exact production value -- the
10-01 CORRECTION already established that recomputing the walk over an ad
hoc window does not reproduce the production start-at-x0 history; the
legend prints the actual stored base/arm positions instead], red=the
flagged head's own box, bracketed):

- `dominant_cause_staff8_bar49_head1.png` (`glyph/3/0/8/0/3`, first head
  in the shared cell): near the box the orange and green lines sit close
  together; by the right edge of the same crop window they have visibly
  separated by close to half a line's gap. **The page's staff genuinely
  tilts/wanders across this cell's width** (consistent with the measured
  ~5% spacing drift on Litolff p3, CLAUDE.md §10) -- the flat grid and a
  locally-aware reading do not agree over one cell's span, which is
  exactly what ROADMAP 2.48 set out to fix. The crop does NOT show an
  obvious misread (no ink is mistaken for a line near the box).
- `dominant_cause_staff8_bar49_head4.png` (`glyph/3/0/8/0/8`, the last
  head in the same cell, further right): the SAME divergence is clearly
  visible right at this head -- green sits above orange by close to half
  a space here, more than at the first head. Confirms the drift is
  real and grows across the cell, but the box itself sits in the same
  space relative to EITHER nearby line pair in this crop -- the crop does
  not, by itself, show which grid is the one a musician would read off
  the print; it shows that the two mechanisms genuinely disagree about
  where the lines are by the time they reach this head.
- `dominant_cause_bass_chord_bar17.png` (`glyph/2/0/3/0/5`, bass clef):
  the flagged head is a **ledger note sitting well above the staff's top
  line**, with a visible ledger stroke through it -- a far note, the
  hardest case per CLAUDE.md §10. Orange/green again fan apart left to
  right across the system. For a far note, any per-space measurement
  difference between the two grids is used TWICE over (it is doubled by
  the glyph's own distance from the staff before it is extrapolated), so
  the same tilt that cost ~0.78 sp inside the staff costs ~1.02 sp here --
  the amplification-by-distance CLAUDE.md names, confirmed visually.

**Conclusion for Sean**: the dominant cause is not 10 independent note
errors -- it is 6 independent per-cell disagreements between the flat
grid and the comb over a REAL, visible staff tilt, amplified by distance
from the staff for the one far head. The comb is not hallucinating ink;
it is answering a geometric question (where do the lines actually run)
differently from the flat grid, and on this page's cells, every one of
those 6 disagreements points the SAME direction -- there is no sign
cancellation to appeal to.

**Comb + head-ink-centre, scored on these same 15 heads: not built,
for a measured reason, not skipped.** The already-recorded compensating-
bias measurement (immediately above) found the head-centring bias is
+0.43 px (std 3.04) against a measured half-step of 50 canonical px
(`Q.CELL_STAFF_SPACE` on every cell above) -- under 1% of one staff space,
two orders of magnitude below the 0.3-1.0 sp dominant-cause shifts traced
here. A sub-pixel box-vs-ink correction cannot move a whole-space grid
disagreement; building the combined arm and scoring it against these 15
heads would reach the a-priori-determined answer (no change) at the cost
of a full re-gather, which rule 5 (reach before accuracy) counsels against
once the magnitudes are this far apart. If a future lane disputes the
50-canonical-px half-step on this page, that premise should be re-measured
first.

**A/A control**: the previously recorded 0 right->wrong / 0 wrong->right
A/A (separate worktrees, same code) stands; this session's independent
re-gather of the base and arm (fresh worktree, `fd396df0`) reproduced the
a3ef66 lane's own arm shifts to several decimal places on every one of
the 15 heads, which is the same determinism claim made a second,
independent way.

STILL NOT MERGED -- this trace explains the mechanism (a real, tilt-driven
per-cell disagreement, one-directional on this page) but does not change
the keep/drop verdict: the comb's own measured effect is still a net
regression under every judge tried so far.

## 2026-10-01: one-head frame-control re-check -- the prior crops' transform, not the staff, was wrong

Manager flagged that the two 2026-10-01 trace crops (`dominant_cause_staff8_
bar49_head1.png`, `dominant_cause_bass_chord_bar17.png`) drew both grids
~10px off the real printed lines, and that the green line in those crops
was explicitly an "illustration" re-walked over an ad hoc window, never the
byte-exact production comb (stated in `crop_14heads.py`'s own docstring and
the prior section above). Per CLAUDE.md rule 7 ("a control must be able to
fail") this re-check rebuilt the frame control and both grids from scratch
for ONE head, `glyph/3/0/8/0/3` (staff/3/0/8, bar 49, treble, head1 of the
4-head shared cell), with no re-gather: BASE from the committed
`library/_shared-records/beethoven5-litolff-mvt1-whole-20261001.record.json`
(commit `342ec6244`, confirmed NOT an ancestor of 2.48's `81f8c94d7` --
clean, no comb code), ARM from the a3ef66 lane's own
`benchmarks/acceptance/quick/out/.../beethoven5-litolff-p3.record.json`
(the comb branch). The two line-finding functions
(`measure_extractor._cell_line_offset`, `._trace_cell_local_lines`) were
called DIRECTLY on a freshly rendered+deskewed page (duck-typed `Staff`/
`PageWithStaves` stand-ins built from the record's own stored
`staff_lines`/`staff_spacing`/`staff_skew.thickness_px`) -- re-running only
the line finders, not a gather.

**Frame control, run first:** stored `staff_lines` for staff/3/0/8
([1643, 1659, 1674, 1690, 1705], page px) checked against real ink-row
peaks at a CLEAN x inside the staff's own measured extent (`staff_extent`
[345, 2610]) -- NOT outside it, which is what produced a bogus -6px
"failure" on the first attempt (the first clean-x window, 140-60px left of
the cell, fell before the staff's own extent even started and measured
nothing real). Corrected: measured peaks [1646, 1662, 1677, 1693, 1709],
average delta +3.2px from stored. **Broken-state control**: offsetting the
same stored lines by +5px and comparing ink density under the true vs
broken position (53 vs 400) correctly shows the broken offset failing --
the control can fail and does when it should.

So: a genuine ~3px reproduction gap exists between a fresh `render_page`+
`deskew` call and whatever pixel alignment the original gather's own
render produced (this run's `deskew()` found 0.000deg to correct; the
record's own `staff_skew` observation reads 5.0, a different-named
quantity, not directly comparable) -- small (~0.2 staff-space), well under
the dominant 0.78sp shift being explained, but real, and it means today's
independent ink re-measurement cannot discriminate BASE (4.06) from ARM
(4.84) by eye or by a crude single-column peak-find: ink peaks measured on
either side of the head (avoiding the notehead's own ink) land 2-4px from
BOTH candidate grids, which is inside this reproduction gap's own noise
floor. **This supersedes the "crop does not show which grid is right"
conclusion only insofar as pixel-level discrimination was never the
answer here** -- the mechanism below is.

**Where the 0.78sp actually comes from (confirmed, not inferred):**
`_cell_line_offset` (BASE, pre-existing, NOT part of 2.48) searches the
WHOLE cell `[343,636)` for one rigid shift maximizing ink coverage under
all 5 lines at once, and finds `+6px` (`offset_spaces: 0.387`, `rows_
covered: 5`, `min_row_coverage: 0.98`) -- in canonical half-steps,
`6/7.75 = 0.774`, matching the recorded shift (+0.780) to three
decimals. `_trace_cell_local_lines` (ARM, the 2.48 comb), called on this
SAME cell's own `[343,636)` x-range exactly as `_build_measure_cell`
calls it, measures **`+0.00px` shift at every single column in the
cell** -- it never moves at all here, so it reports the raw, un-localized
`staff.line_ys` unchanged, which is where the ARM's 4.84 comes from.
**This is not the comb finding a tilt the flat grid missed -- it is the
comb finding NOTHING (never getting 3-of-5 lines to agree for the
`CELL_LINE_WALK_MIN_CONSISTENT_RUN` consecutive steps `_walk_comb_shift`'s
own docstring requires to commit) in a cell this busy** (the cell's own
`ink` observation: 12 components, 6 stems, 2 beam strokes, several
noteheads) **and silently holding its starting value, which is read
downstream as a decided answer with no abstain.** A positive control
confirms the walk function itself is live in this harness: run
continuously across the WHOLE staff (`[345,2610)`, one shape, as
production always calls it per-cell but never across a cell boundary) it
commits to real nonzero shifts elsewhere on the same staff (up to +4.58px,
and +1.24px by the time it reaches this cell's own x-range) -- **meaning
`_trace_cell_local_lines`'s PER-CELL restart (seeded to shift=0 at each
cell's own left edge, per its `_build_measure_cell` call site) throws away
whatever momentum the comb built on cleaner columns earlier in the staff,
right before a busy cell where it most needs that momentum to find
anything.** Even with full-staff momentum the comb only reaches +1.24px
here, well short of the rigid localizer's independently cross-validated
+6px (98% row coverage) -- so even its best-case behaviour UNDER-corrects
this cell, the opposite of "the comb caught a tilt the flat grid missed."

**Conclusion, correcting the 2026-10-01 trace section above for this one
head:** the "dominant cause" is not a real staff tilt visible to the
naked eye in a correctly-transformed crop (it cannot be, cleanly, given
this reproduction's own ~3px noise floor) -- it is that the comb's
"held, never committed" null answer is indistinguishable, downstream,
from a confident zero-shift reading, and the per-cell restart denies it
the one piece of evidence (upstream momentum) that might have let it
reach closer to the rigid localizer's answer. The other 5 of the 6
independent per-cell disagreements in the prior trace were NOT
individually re-examined this round (small-check scope); the mechanism
found here -- restart-at-cell-boundary discarding momentum, feeding a
silent "never committed" zero into a decided position -- is a plausible
candidate for some or all of them and is worth checking before any next
attempt at the comb, but is not re-verified across all 6 here.

One crop, production-exact grids (not a re-walked illustration -- the
green line here reproduces the recorded 4.84 to the stored value, the
orange reproduces 4.06), magenta crosses for the independent ink
cross-check: `out/print/2.48/onehead/staff8_bar49_head1.png`. The bass
chord head (`glyph/2/0/3/0/5`) was not re-traced this round (time-boxed,
Sean: no batteries).

STILL NOT MERGED.

## 2026-10-01: the comb SEEDED from orange -- fixes the busy-cell cluster, no new regressions

Sean's design (DECISIONS 2026-10-01): *"let's use the current process to
start where the comb starts -- so the green line should take a cue from the
orange lines so it can't get lost and then it should tilt with the ink as it
does."* `_walk_comb_shift` (and `_trace_cell_local_lines`,
`_build_measure_cell`) now take `seed_shift_px`: the comb starts at this
cell's own `_cell_line_offset` ("orange") shift when that reader measured
one, 0 (today's unseeded course) when it abstained for this cell -- never
invented. The total-drift bound (`CELL_LINE_WALK_MAX_TOTAL_SPACES`) is now
measured FROM THE SEED, not from a raw zero, so a seeded cell can still
tilt the same 0.3 spaces further from where it started.

**Unit tests, RED->GREEN** (`tools/omr/tests/test_local_staff_lines.py`,
class `TestCombSeededFromOrange`): (a) a cell solid with ink top-to-bottom
(no clean line anywhere -- the real bar-49 shape) that never commits: FAILS
on the pre-fix code (`seed_shift_px` doesn't exist; confirmed RED by
swapping in the parent commit's `measure_extractor.py` and re-running --
3/3 new tests fail) and PASSES after, holding the SEED (6px) instead of 0;
(b) a clean tilted staff still bends with the real ink from a seed that
matches neither end; (c) `_build_measure_cell`'s own wiring stores a local
grid at orange's shift when the comb never commits, not at the raw lines.
Full fast suite: `pytest tools/omr/tests -m "not slow" -q` -- 4190 passed,
3 skipped, 2 xfailed, 0 failed.

**Small real check, NO re-gather** (`recheck_2_48_seeded.py`, reusing the
one-head lane's recipe -- duck-typed `Staff`/`PageWithStaves` from the
committed arm record's own `staff_lines`/`staff_spacing`/`staff_skew`, a
fresh `render_page`+`deskew`, `_cell_line_offset`/`_trace_cell_local_lines`
called DIRECTLY, no gather): the 15 heads `trace_14_heads.py` traced plus
10 control heads on the same page (Litolff p3), TODAY (orange/flat grid) vs
OLD unseeded comb vs SEEDED comb, against the reference position via the
staff's decided clef. 5 of 15 traced + 6 of 10 controls paired against the
reference (the rest "unscored" -- box-count-vs-truth-count mismatch in that
bar, same as the real judge). Of the 5 scored traced heads: the 4 bar-49
heads (`glyph/3/0/8/0/3,0/4,0/5,0/8`) that the OLD comb got wrong
(never-committed, held at the raw lines) are now RIGHT under the seeded
comb, matching TODAY exactly (4.07->4.10, 6.09->6.12, 7.11->7.27,
7.03->7.10, all still rounding the same way). The other 2 scored traced
heads (`glyph/3/0/0/2/4`, `glyph/3/1/0/6/0`) are UNCHANGED by seeding --
these are the already-documented "comb commits to a real but
disagreeing tilt" cases (the prior trace section's dominant cause, a
different failure mode seeding does not touch) and were wrong under the old
comb too. **All 10 control heads unchanged** (today/old/seeded identical).
No new right->wrong anywhere in the 25.

**Crop + pixel-row frame check** (`crop_2_48_seeded.py`,
`out/print/2.48/seeded/staff8_bar49_head1_seeded.png`): draws PRODUCTION's
own byte-exact arrays (orange's rigid shift, the seeded comb's path), never
a re-walked illustration. A clean vertical strip near the head (off its own
ink) measured real ink-row peaks directly: orange's predicted rows
([1649, 1665, 1680, 1696, 1711]) land inside the real peaks 5/5; the seeded
comb's rows at that x (1648.7 .. 1710.7, confirming it never moved off the
seed in this cell) land in the same 5/5. A deliberately broken +5px offset
control correctly fails (0/5 peaks hit) -- the control can fail (rule 7).

**Full count-page re-gather** (step 4, since the small check was clean): a
clean `origin/main` worktree (0719f18d, confirmed zero `_trace_cell_local_lines`/
`_walk_comb_shift` in `measure_extractor.py` -- pure today/orange-only
production) as BASE vs this branch as ARM, both
`python3 -m tools.omr.acceptance_quick --doc beethoven5-litolff`
(GATHER+ADJUDICATE only, default mode), then `--against` for the
GATHER+ADJUDICATE readout diff. Per-family GATHER/ADJUDICATE status counts
(kept/refused/narrowed/abstained/given_away/undecided for every family) are
IDENTICAL between base and arm -- expected, since seeding touches no GATHER
quantity. 600 of 1330 `notehead_staff_position` values changed at the raw
float (comb now active on some cells that previously fell back to the flat
grid; most deltas are sub-0.2, i.e. sub-pixel). Scored against the
reference (same pairing as `gather_only_judge.py`, 149 of 1330 noteheads on
this page pair cleanly): **right->wrong=2, wrong->right=0** -- the SAME 2
heads (`glyph/3/0/0/2/4`, `glyph/3/1/0/6/0`) the small check already found,
not new, and not fixed by seeding (a different, already-documented failure
mode: the comb commits to a real ink tilt that disagrees with the correct
flat grid, amplified by the heads' own distance from a clean reference
column). **No new regression at full-page scale beyond the small check's
own two.**

**Conclusion**: seeding fixes exactly the mechanism it targeted (a busy
cell's comb silently holding a wrong raw-lines default instead of orange's
measured shift) and introduces zero new regressions, at both the 25-head
small-check scale and the full count-page scale. It does NOT fix the
separate, already-documented "comb finds a real but wrong tilt" failure
mode (2/149 here) -- that remains open and is a different mechanism from
this lane's own scope. Given CLAUDE.md's "N must go down" bar is about
derived-check findings, not this page's note-level score, and this script
is NOT a new derived check (rule 9) -- it is this lane's own iteration
tool, kept in the benchmark directory per convention.

STILL NOT MERGED -- the net effect at the scored population here is a pure
improvement (4 wrong->right against the old comb, 0 new wrong), but the
2/149 pre-existing regression (unrelated to this fix) means the comb as a
whole has not yet cleared the keep bar from the original A/B
(`score_2_48.py`'s right->wrong~0 target). Next: crop-check the 2 remaining
heads (`glyph/3/0/0/2/4`, `glyph/3/1/0/6/0`) the way the earlier trace did
for the bar-49 cluster, to see whether the SAME seeding idea (or a
different one) can close them too.

## 2026-10-01: PINNED per-system comb (Sean's design #3) -- fixes the seeded comb's last 2 right->wrong, 0 new regressions on the scored heads

Sean, on the seeded comb's own crops (both remaining right->wrong heads are
rounding-boundary coin-flips, 0.13 and 0.03 of a step apart, DECISIONS.md
2026-10-01): *"Currently I feel like the comb changes too much. Can it be
more gradual? Like pinned at the ends and a few points in between a
system?"* STAGED/shared (`tools/omr/measure_extractor.py`, read by both
readers per CLAUDE.md §3): replaces the per-CELL seeded walk with one
smooth model per (staff, SYSTEM) -- `_pinned_system_shifts` pins the
five-line comb's shift at BOTH system ends and `PINNED_COMB_N_INTERIOR_PINS`
= 3 points evenly spaced between (5 pins total, a small FIXED count rather
than a per-space density, so a short system is not starved and a long one
does not accumulate an unbounded number of commit decisions), measures each
pin as a robust MEDIAN over the existing clean-column test
(`_measure_line_run_mid`, reused unchanged) in a window of
`PINNED_COMB_WINDOW_HALF_SPACES` = 1.5 staff spaces either side, then
interpolates LINEARLY between surviving pins (`np.interp`) -- no new degree
of freedom beyond the single per-pin shift the per-cell walk already used.
A pin that cannot be measured (fewer than `CELL_LINE_WALK_MIN_LINES_AGREE`
= 3 of 5 lines agreeing anywhere in its window) is DROPPED, never
defaulted (rule 8); fewer than `PINNED_COMB_MIN_PINS` = 2 surviving pins and
the whole staff keeps TODAY's per-cell seeded walk, byte-identical to the
lane-2.48-seeded course. Wired into `_build_measure_cell` behind the SAME
existing code path (`local_line_paths_px`, no new flag, rule 9):
`extract_measures` computes the pinned array ONCE per (staff, system) over
the system's own full x-span (`xb[0][0]`..`xb[-1][1]`) and passes it down;
`_build_measure_cell` prefers it, slicing the cell's own x-band out of the
precomputed array, and only falls back to the per-cell seeded walk when the
caller passed none or the staff's own model came back `None`.

**Unit tests, RED->GREEN** (`tools/omr/tests/test_local_staff_lines.py`,
class `TestPinnedSystemComb`, 4 tests, confirmed RED on `lane-2.48-seeded`
`62116487` by swapping in that commit's `measure_extractor.py` and
re-running -- `AttributeError: _pinned_system_shifts` on all 4, since the
function does not exist there at all): (a) a flat clean staff with one busy
bar BETWEEN two pins (foreign "ghost" lines at the staff's own thickness,
so they pass the clean-run test and could legitimately mislead a walk,
unlike a solid ink block which the clean-thickness gate simply declines) --
the pinned model reads the true (0) shift straight through the busy bar
because it never measures inside one, while the per-cell seeded walk,
seeded with the TRUE local shift (the fairest seed it could be given), is
still pulled toward the foreign lines (>2px, vs <1px for the pinned model);
(b) the same fixture scored the other way -- the seeded walk lands within
1.5px of the foreign lines' own offset (it "bends toward" them) while the
pinned model stays within 1px of the true, flat position; (c) control: a
flat clean staff with no busy ink reads 0 everywhere under the pinned
model too; (d) 4 of 5 pins blotted with unreadable solid ink (only the
system's own right end stays clean) -- `_pinned_system_shifts` returns
`None` (rule 8), and `_build_measure_cell(..., pinned_shifts=None)` still
produces a local trace via today's per-cell seeded walk, unaffected. Full
fast suite: `pytest tools/omr/tests -m "not slow" -q` -- 4190 passed, 3
skipped, 2 xfailed, 0 failed (IDENTICAL to the seeded lane's own count --
`test_local_staff_lines.py` is already in the slow tier via its
pre-existing `"synthetic.pdf"` path match, so the 4 new tests run under a
direct file invocation: `pytest tools/omr/tests/test_local_staff_lines.py`
-- 26 passed, up from 22).

**Small real check, NO re-gather** (`recheck_2_48_pinned.py`, reusing
`recheck_2_48_seeded.py`'s own recipe and subject list verbatim): the 15
traced heads + 10 controls + the 2 heads still right->wrong under the
seeded comb (`crop_2_48_broken.py`'s own `SUBJECTS` -- both of which turn
out to already be members of the 15 traced, so 25 UNIQUE heads total, not
27) against TODAY / SEEDED COMB / PINNED COMB, same reference pairing as
`gather_only_judge.score_doc`. Of the 23 heads with a reference pairing
(13 traced + 10 control, excluding the 2 broken): **right->wrong=0,
wrong->right=0 for the pinned model against today, identical to the
seeded comb's own 0/0 on the same 23** -- no new regression anywhere
scored. On the 2 previously-broken heads: **the pinned model matches
TODAY exactly where the seeded comb did not**
(`glyph/3/0/0/2/4`: today -7.40, seeded -7.52 [wrong, rounds -8], pinned
-7.40 [right]; `glyph/3/1/0/6/0`: today -6.49, seeded -6.52 [wrong, rounds
-7], pinned -6.48 [right]) -- the pinned model fixes BOTH of the seeded
comb's own remaining regressions, net 0 right->wrong / 0 wrong->right
against today over all 25 scored/unscored heads together, where the
seeded comb was 0/0 on the 23 scored and 2/0 wrong on the 2 broken.

**Open question, not yet resolved**: per-staff max deviation of each
model from a straight line through its own two system-endpoint values (the
"how much it changes" number Sean asked for) --

| staff | seeded (px) | pinned (px) |
|---|---|---|
| staff/1/0/7 | 3.89 | 3.36 |
| staff/1/0/8 | 4.54 | 3.88 |
| staff/2/0/2 | 3.57 | **9.07** |
| staff/2/0/3 | 3.89 | **8.64** |
| staff/2/0/7 | 3.59 | **9.34** |
| staff/3/0/0 | 3.92 | 3.87 |
| staff/3/0/1 | 4.86 | 5.16 |
| staff/3/0/10 | 4.33 | 3.64 |
| staff/3/0/2 | 4.83 | 5.06 |
| staff/3/0/8 | 4.40 | 3.91 |
| staff/3/1/0 | 4.39 | 3.32 |

On 8 of 11 staves the pinned model is AS gradual as or more gradual than
the seeded comb (exactly the design's own goal). On 3 (staff/2/0/2,
staff/2/0/3, staff/2/0/7 -- the SAME system that carries the already-
documented "comb commits to a real but disagreeing tilt" cluster from the
2026-10-01 trace section above, `glyph/2/0/3/0/5` etc.), the pinned
model's own deviation is more than double the seeded comb's. None of
these 3 staves' traced heads have a reference pairing in this check
(`expected=None` for all 7), so this is NOT a measured regression -- it is
an open question about whether the pins are finding a genuinely larger
printed tilt on this system (plausible: this is the same system the
seeded comb's own unfixed failure mode lives on) or aliasing onto nearby
ink in a denser orchestral system, and it should be crop-checked before
this model is trusted on that system specifically. Not resolved this
session (time-boxed).

**Crop + pixel-row frame check**
(`crop_2_48_pinned_system.py`,
`out/print/2.48/pinned/staff_3_0_8_whole_system.png`): the WHOLE system
for `staff/3/0/8` (the bar-49 system every earlier 2.48 crop in this
benchmark has examined), orange (today's per-cell grid, drawn as its own
step function) vs the pinned model (drawn continuously, pins ticked) full
width. Verified against real ink-row centres at 3 clean columns picked by
actual ink count (x=1745, 2155, 2565), never by eye: **both orange and the
pinned model land all 5 lines within 2px of the real ink 5/5 times at
every one of the 3 columns.** A deliberately broken +5px offset control at
the same first column correctly hits 0/5 -- the control can fail (rule 7).

STILL NOT MERGED. Next: crop-check the 3 flagged staves' own pins before
trusting the pinned model there; then the overnight full re-gather
(`THROUGH=adjudicate`) if the small-check numbers hold.

## 2026-10-01: PINNED comb step 4 (full count-page re-gather) -- CORRECTS the small check's optimism: net right->wrong=8 / wrong->right=5 at full scale

Per rule 4 (one objective) and rule 7 (a control must be able to fail),
ran the full count-page re-gather the small check's own result cleared
the bar for. **Base vs arm on ONE tree** (CLAUDE.md §6b): `lane-2.48-
seeded`'s own `measure_extractor.py` (`62116487`) was swapped into THIS
worktree and gathered fresh (`acceptance_quick --doc beethoven5-litolff
--out-root .../out_base_2_48`, Litolff p0-p3, GATHER+ADJUDICATE only) as
BASE, THEN the pinned branch's own code was restored and gathered fresh
the same way as ARM (`--against <base record>`, `--out-root
.../out_arm_2_48_pinned`) -- never an older record from a concurrent
worktree, which CLAUDE.md §6b already warns no longer reproduces today's
tree. Scored with `score_2_48_pinned.py` (the `gather_only_judge.py`
judge, same pairing as `recheck_2_48_seeded.py`/`recheck_2_48_pinned.py`:
detector box order within a bar against the reference's onset-descending
order, scored at GATHER+ADJUDICATE position only, never Q.PITCH/export):

```
base (lane-2.48-seeded, this tree): {'unscored': 1039, 'wrong': 136, 'right': 145}
arm  (lane-2.48-pinned):            {'unscored': 1039, 'wrong': 139, 'right': 142}
changed: 13  right->wrong: 8  wrong->right: 5
```

**This CORRECTS the small check's conclusion above.** The small check (23
scored heads out of 25) found 0/0 and a clean fix of the 2 known-broken
heads; the full page (281 scored heads) finds a NET REGRESSION of 3
(8 right->wrong against 5 wrong->right) -- the small 25-head sample
simply did not include 5 of the 8 new right->wrong heads
(`glyph/2/0/0/5/5`, `glyph/3/0/4/12/3`, `glyph/3/0/4/13/6`,
`glyph/3/0/8/1/0`, `glyph/3/0/8/1/3`) at all. Two of those five
(`glyph/3/0/8/1/0`, `/1/3`) sit on the SAME staff and the CELL
IMMEDIATELY AFTER the bar-49 cluster the seeded comb already fixed
(`cell/3/0/8/0`) -- consistent with the pinned model's own per-system
reach: fixing one cell's disagreement by interpolating from distant pins
can shift a NEIGHBOURING cell that was fine under the per-cell walk.
`glyph/3/0/8/0/5` itself (part of the original bar-49 cluster, matched
TODAY in the small check against the 09-30 `ARM_RECORD` snapshot) flips
right->wrong in this fresh pairing -- the two checks used records from
different snapshots (the small check's reference pairing came from a
09-30 seeded record, this one from a fresh 10-01 gather of both base and
arm on today's tree) and do not reconcile exactly, which is itself the
project's own standing warning: "a shared record is a snapshot of the
reader that made it."

**Verdict: the pinned model is NOT a clean win at full scale.** It
reliably fixes the 2 originally-flagged heads and a few more the small
check's narrow sample happened to miss, but the per-system reach that
makes it "more gradual" also lets one system's measured tilt move cells
the per-cell walk had gotten right by holding locally. STILL NOT MERGED.
Next: crop-check the 5 NEW right->wrong heads above (same recipe as
`crop_2_48_pinned_system.py`) before any further iteration on pin count,
window width, or a per-cell "prefer whichever of {pinned, seeded} is
closer to this cell's own `_cell_line_offset`" tie-break.
