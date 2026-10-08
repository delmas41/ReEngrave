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

## 2026-10-01: Sean's boundary question -- why doesn't the (closer) comb improve the score? (lane-2.48-boundary, NO re-gather)

Sean: the comb sits ~0.25px from the print (this FINDINGS line's own strip
measurements) against today's flat per-bar grid's ~1px -- so why does the
real re-gather not improve? Three hypotheses tested: (1) too few heads near
a rounding boundary to flip; (2) box-centre error rivals the line
improvement; (3) the 149-of-1330 reference-scored sample is too small to
see it. GATHER+ADJUDICATE-only (CLAUDE.md §6b), no re-gather --
`boundary_measure.py` reuses `recheck_2_48_seeded.py`'s own recipe (duck-
typed `Staff`/`PageWithStaves` from the lane's committed ARM record, a
fresh `render_page`+`deskew`, `_cell_line_offset`/`_trace_cell_local_lines`
called DIRECTLY). Both TODAY's flat grid and the seeded comb are computed
fresh here, never read off the record's own stored (comb-affected)
position -- the record is used only as a source of GATHER facts (boxes,
staff lines, clef, bar numbers), which prior rounds in this FINDINGS line
established are byte-identical base vs arm (detector untouched by the comb).

### A. Distance to the rounding boundary, every kept notehead, Litolff p3

349 kept noteheads (ADJUDICATE `kept`, position observed, of this page's
1330 detected notehead glyphs -- most of the page is refused, narrowed or
abstained elsewhere in the pipeline, not a 2.48 fact).

| bucket (px from boundary) | count |
|---|---|
| 0-0.5 | 25 |
| 0.5-1 | 17 |
| 1-2 | 67 |
| 2-3 | 78 |
| 3+ | 162 |

**Within 1px of a boundary: 42 of 349 (12.0%).** Within 2px: 109 of 349
(31%). **Of those 42, only 15 are among the 149 reference-scored heads**
(36% -- the reference pairing already loses most of the population that
could visibly flip). **Hypothesis 1 (too few near-boundary heads) does
NOT hold on its own**: 12% of kept heads, and nearly a third within 2px,
is not "few" -- a 1px line correction has real room to matter here.

### B. Box-centre error vs line difference, the 112 heads within 2px

For each: TODAY's and the seeded comb's line position at the head's own x
(both computed fresh, never recomputed over an ad hoc window -- the
10-01 CORRECTION's own lesson), the detector's box centre, and the head's
own INK centre (outermost ink row per column, central 40% of the box
width, staff-line rows masked at the comb's own measured y using the
record's `staff_skew.thickness_px`, padded 0.3 spaces beyond the box).

- **box-centre error (box_y - ink_y): mean +0.24px, std 2.48px (n=112)**
- **line difference (comb - orange at the head): mean -0.01px, std 0.47px
  (n=112)**

**Box-centre error is ~5x the spread of the line difference on these same
heads.** The comb's own line correction (what this lane changes) is small
and centred near zero; the detector's box-vs-ink disagreement is an order
of magnitude larger and in many individual cases alone exceeds a full
rounding step (|box-ink| > 3px on 19 of 112 heads sampled).

### C. Controls -- and the control FAILS (rule 7)

10 clean, isolated heads (cell-distinct, >3px from any boundary, same
method): **mean 0.19px, std 3.16px** -- NOT the small, tight agreement
(~1px) the control was built to show. 3 heads with a deliberately
offset +3px box: measured errors **5.63 / 0.67 / 0.86px** -- NOT
consistently ~3px either. **The control fails, as rule 7 requires it be
able to**, and what it fails AT is informative: the ink-centre
measurement itself carries several px of noise on this plate, comparable
in size to the very box-centre effect it was built to quantify. The
numbers in §B are real (box error visibly dwarfs line error in aggregate,
and the failure mode below explains why), but not precise enough to
trust head-by-head.

### D. Crops (`out/print/2.48/boundary/`, 3 near-boundary heads, 600dpi,
### orange/green/box/ink-centre drawn, verified against ink-row centres)

- `glyph_3_0_0_2_9.png` (dist 0.53px, the flute passage from Sean's own
  D6/E6 crop history): the detector's OWN box covers only the UPPER
  portion of a visibly larger connected black blob -- **two heads' ink
  merged into one component** (Litolff MERGES, CLAUDE.md §10), so the
  box itself, not just its centre, is the wrong shape for "this one
  head's ink". The ink-row centres at a clean column (953-968) confirm
  BOTH orange (451.0/466.0/...) and comb (450.6/465.6/...) sit within
  ~1px of the real printed lines there -- the geometry side is fine; the
  box is the problem.
- `glyph_3_0_9_2_0.png` (dist 0.10px, a dense bass region, several
  adjacent/overlapping heads): box_y 1894.7 vs ink_y 1892.0 (2.7px) --
  plausible contamination from the touching neighbour visible in the
  crop, the same hazard 2.44c's box-recentring hit.
  `glyph_3_1_6_11_0.png` (dist 1.10px, an isolated open half-note sitting
  on a line): box_y 3332.9 vs ink_y 3334.5 (1.6px) -- the CLEAN case, and
  it is the one head of the three where orange and comb visibly
  coincide and the ink agrees with the box to within less than one
  staff-space.

### Note history: does this avoid 2.44c's "fixed 3, broke 3"?

**No.** 2.44c's box-recentring (`gather._canonical_ink_centre`, an
unbounded nearby-component search) fixed 3 of 10 wrong heads and broke 3
previously-right ones because on a dense page the ink search "finds a
DIFFERENT, sometimes wrong, nearby component" (FINDINGS §18b). This
lane's method is narrower -- central 40% of the box width (avoids the
stem side), staff-line rows masked at the comb's own measured position --
which removes two of 2.44c's three contamination sources (the stem, the
staff line itself). It does **not** remove the third, and on this plate
the dominant one: a vertically adjacent or merged head's ink inside the
same padded window, confirmed directly in `glyph_3_0_0_2_9.png` above and
by the control's own 3-6px scatter. A sharper search radius is not
enough on a MERGING plate; the same hazard that sank 2.44c sinks this
method's per-head precision too, even though it never re-wires a
position (measurement only, nothing shipped).

### Answer to Sean's three hypotheses

1. **False as the explanation.** 12% of kept heads sit within 1px of a
   boundary and nearly a third within 2px -- not a small population.
2. **The best-supported explanation, even though this lane's own
   instrument is too noisy to prove it to the pixel.** Box-centre
   disagreement is ~5x the comb's own line correction in aggregate
   spread, and several individual heads show box-vs-ink gaps bigger
   than a full rounding step -- on a page where boxes and ink routinely
   merge across heads (CLAUDE.md §10), fixing the LINE while the BOX is
   still wrong by more than the line ever moved cannot show up as a
   score improvement.
3. **A real but secondary contributor.** Only 15 of the 42 near-boundary
   heads (36%) are visible to the reference-scored judge at all -- most
   of the population this lane measured cannot move `acceptance_quick`'s
   number either way.

**Recommendation**: before any further line-geometry refinement, the
detector's own BOX (not just its centre) needs the same kind of scrutiny
2.39/2.39b gave head sizing -- on a merging plate, "kept notehead" boxes
routinely bound less than the full printed head, and no amount of line
precision fixes a position measured from the wrong box. Not built here
(time, and out of this lane's NO-re-gather / NO-code-change scope).

`pytest`/`staged.check` not run (no production code touched -- measurement
scripts only, both under `benchmarks/omr-local-staff-2026-09/`).

## 2026-10-01: two-candidate head fit by ideal-head ink coverage -- CONTROL FAILS, STOPPED before scoring (lane-2.48-headfit)

Sean's design (DECISIONS 2026-10-01, queued behind the boundary-distance
check): for a head within ~2px of a rounding boundary only, place an IDEAL
head (2.39's `geometry.standard_head_box`, reused not re-derived) at EACH
of the two candidate staff-position steps either side of the boundary, at
the head's own x, vertical centre exactly on that candidate's line/space y
from TODAY'S per-bar grid (`_cell_line_offset` -- the comb is a separate,
unmerged mechanism, deliberately not used here). Score = fraction of the
ideal box that is inked, with the real staff-line rows masked out
identically for both candidates. `headfit.py`, GATHER+ADJUDICATE-only, no
re-gather -- reuses `boundary_measure.py`'s own dist-to-boundary-labelled
349-head population and `recheck_2_48_seeded.py`'s duck-typed-record
recipe for 3 named merged-blob subjects.

**MARGIN RULE, stated in the script before any result was looked at**:
decide for the higher-coverage candidate only when it beats the other by
>= 0.15 (15 points of box area) AND its own coverage is >= 0.30; else
ABSTAIN and keep today's reading, counted.

### Step 1 controls -- (a) and (b) FAIL; (c) and (d) behave

**(a) 15 clean heads, >3px from any boundary, true step = today's own
reading**: **6/15** picked today's step (bar was >=14/15). **FAIL.**

**(b) same 15 heads, box y shifted +3px / -3px (fit must use the
candidate positions, not the box centre)**: **15/30** trials still picked
the true step (bar was >=90%, i.e. >=27/30). **FAIL** -- expected, since a
method that already cannot discriminate at zero perturbation (a) cannot be
expected to survive a further 3px nudge; this control's failure is
downstream of (a)'s, not a separate defect.

**(c) same 15 heads, staff LINES shifted a half-step (deliberately
broken)**: **10/15** failed visibly (wrong or abstained). **PASSES** (bar
was "most"). Control can fail and does: `pytest`-free, the half-step break
moves each candidate onto what was the OTHER candidate's true-ink zone, so
most heads land on no good ink and the fit either picks wrong or abstains,
exactly as the broken-state signature predicts.

**(d) 3 named merged/dense-ink subjects** (`glyph/3/0/0/2/9`,
`glyph/3/0/9/2/6`, `glyph/3/1/2/9/2`): **2/3 abstained** as expected
(`glyph/3/0/0/2/9` scores 0.987/0.992 -- indistinguishable, correctly
abstained; `glyph/3/1/2/9/2` 0.636/0.602 -- correctly abstained). The
third, `glyph/3/0/9/2/6`, DECIDED (0.742 vs 0.321) -- its own crop (below)
shows the decided candidate does sit on real ink, so this subject may not
actually be the "two merged heads under one box" case its citing FINDINGS
line described (that line was about three ink-centring METHODS
disagreeing, not necessarily two physically merged heads) -- reported as
a correction to this lane's own subject choice, not a control failure.

**GATE: (a) FAIL, (b) FAIL, (c) PASS, (d) effectively PASS (2/3, the third
not a clean abstain case by its own crop). Per the brief ("if (a)-(c) do
not behave, STOP and report why -- no scoring"): STOPPED. Step 2 was not
run.**

### Why (a) fails -- diagnosed, not just measured, with 3 crops at `out/print/2.48/headfit/`

`glyph/3/0/0/5/12_control_a_near_tie.png`: the two candidate boxes
(lower=-5 score 0.802, upper=-4 score 0.803, diff 0.001) sit inside ONE
dense ink mass -- a far note above the staff sitting against a beam group
with adjacent chord ink -- and BOTH ideal boxes are almost entirely black.
The real geometric cause: a candidate step is exactly `half_step_px` (one
HALF of a staff space) away from its neighbour, but `standard_head_box`'s
own height is `STANDARD_HEAD_HEIGHT_SPACES=1.1` of a FULL staff space --
so two adjacent candidates' boxes overlap by ~55% of their own height by
construction, before any contamination. On a page where the real printed
ink routinely fills more than half a staff space vertically (beams, chord
stacks, stems), the non-overlapping ~45% sliver each candidate owns is not
enough margin to clear 0.15 reliably. A follow-up probe (not the main
instrument, diagnostic only) narrowed the box's WIDTH to 60%/40%/25% of
standard to reduce horizontal contamination from neighbouring glyphs:
control (a) moved from 6/15 to only 7/15 at every narrower width -- so
width is not the dominant cause; the HEIGHT overlap inherent to adjacent
half-step candidates is.

`glyph/3/0/0/0/0/15_control_a_miss.png` (bar 49, the SAME busy cell
`cell/3/0/8/0` this FINDINGS line's own 2026-10-01 sections already
diagnosed as "the comb never commits ... six stems and a beam"): the
detector's own box here sits on a DIAGONAL BEAM/FLAG stroke, not a round
notehead at all -- both ideal boxes fill with diagonal beam ink almost
identically (0.727 vs 0.642). This corroborates `boundary_measure.py`'s
own Hypothesis 2 conclusion (box-centre error ~5x the line-geometry
effect): the box itself, not just the rounding line, is frequently the
wrong shape or the wrong subject for an ink-coverage test on this plate.

### Conclusion

**The two-candidate ideal-head coverage fit, as specified, does not
reliably discriminate adjacent rounding candidates on this plate** -- not
because of a scoring-threshold tuning issue (the margin rule was stated
before looking, and no amount of width-narrowing moved the control's
pass rate), but because (1) two adjacent half-step candidates' standard
head boxes overlap by construction (~55% of their own height, since the
standard head is 1.1 staff-spaces tall and candidates are 0.5 spaces
apart), and (2) on a MERGING/dense plate (CLAUDE.md §10) the surrounding
ink -- beams, chord members, flags -- frequently fills both candidates'
windows almost identically, consistent with `boundary_measure.py`'s own
earlier finding that the detector's BOX, not the line geometry, is this
page's dominant source of near-boundary error. **Recommendation: do not
build this instrument further as specified; before any next attempt, the
box-shape problem flagged by the boundary lane (2.48's own queued next
step, "the detector's own BOX ... needs the same kind of scrutiny 2.39/
2.39b gave head sizing") needs addressing FIRST, since a box test run on
a wrong-shaped or wrong-subject box (as `glyph/3/0/0/0/15` shows directly)
cannot be rescued by any margin rule.** No production code touched; this
lane's own scripts (`headfit.py`, `crop_headfit.py`) and 3 crops are
committed under this benchmark directory, per convention.

`pytest`/`staged.check` not run (measurement scripts only, no production
code touched).

## 2026-10-01: the recipe check -- no frame-reproduction gap found (lane-2.48-recipe)

Sean's suspicion, after boundary_measure.py's clean-head control scattered
3.16px and headfit.py's control (a) missed 9/15: the fresh render these
scripts lay the record's stored geometry over might not sit in the SAME
pixel frame GATHER used (DPI, deskew angle, crop/margin, canonical-cell vs
page frame, rounding, y-flip). GATHER+ADJUDICATE-only, STAGED path, NO
re-gather, NO production code touched.

### 1. The recipe, compared line by line

Production's ONLY recipe for the pixel frame every GATHER coordinate is
filed against: `detect_staves(render_page(pdf_path, page_index, dpi=dpi))`
(`tools/omr/staged/pipeline.py:prepare_pages`) -- ONE call to `render_page`
(DPI 600 on the CLI, confirmed from this record's own `provenance.settings.
args.dpi`), which already binarizes (Sauvola) and deskews (Hough,
rotate-about-centre) internally -- its own docstring: "already binarized
and deskewed." Nothing else touches the page image before `detect_staves`
reads `page.binary`.

Every script in this directory that built a fresh frame
(`recheck_2_48_seeded.py`, `boundary_measure.py`, `headfit.py`, and all 6
`crop_*.py` scripts) called `render_page(...)` and THEN called `deskew()` a
SECOND time on its own already-deskewed output -- a real divergence from
the production recipe. DPI (600), page index (3, the Litolff count page),
and the PDF path all matched production in every script checked; this
double-deskew was the ONLY difference found.

### 2. Is it a frame-reproduction gap? Measured directly, both ways -- NO.

**Deterministic check (no ink noise at all):** `detect_staves(render_page(
pdf, 3, dpi=600))`, called ONCE, reproduces the record's own stored
`staff_lines` to the INTEGER PIXEL on every staff checked -- e.g.
staff/3/0/8 = `[1643, 1659, 1674, 1690, 1705]`, matching BOTH
`library/_shared-records/beethoven5-litolff-mvt1-whole-20261001.record.json`
and the a3ef66 lane's `beethoven5-litolff-p3.record.json` exactly, byte for
byte. The second `deskew()` call measured directly: first call finds
0.2499deg and rotates; the second, re-run on the now-rotated image, finds
0.0deg and returns the identical arrays (direct numpy diff: mean/max abs
diff = 0 across the whole page). **The double-deskew bug is a no-op on
this page/DPI/PDF -- there is no frame-reproduction gap to find here.**
This directly REFUTES the earlier one-head lane's "~3px reproduction gap"
(2026-10-01, above): that number came from an ad hoc single-column
ink-peak-find, a cruder method than `detect_staves`'s own
`_candidate_staff_rows`/`_comb_match_staves`/`_refit_misaligned_group`
pipeline, not from a real pixel-frame mismatch -- the finding's own text
already said as much ("ink peaks... land 2-4px from BOTH candidate grids,
which is inside this reproduction gap's own noise floor").

**dx/dy table, 5 clean staff-line stretches** (fresh `detect_staves()` line
_ys vs record's stored `staff_lines`, same staff key): all 5 staves
checked on page 3 match EXACTLY, dy=0 on every one of the 25 line
readings (5 staves x 5 lines). No scale, no rotation, no offset.

**dx/dy table, 15 clean isolated noteheads** (`frame_check.py`, box centre
vs fresh-render ink-COMPONENT centre, dx and dy both, independent of
boundary_measure.py's own y-only central-column method):

| n | dx mean | dx std | dy mean | dy std |
|---|---------|--------|---------|--------|
| 15 | +0.68px | 1.04px | -0.78px | 4.25px |

dx is tight and near zero (no horizontal frame offset); dy scatters
~4px with no sign pattern against x (no rotation) -- matching, not adding
to, `boundary_measure.py`'s own control (10 clean heads, y-only method:
mean 0.19px, std 3.16px). Two independent ink-measurement methods agree:
the scatter is REAL but it is NOISE IN THE INK-CENTROID INSTRUMENT on a
MERGING plate (CLAUDE.md §10), not a systematic dx/dy/scale/rotation
between the fresh render and GATHER's frame.

### 3. Control that can fail (rule 7): deliberate +4px dy -- PASSES, with an honest caveat

The same 15-head ink-component measurement, run again on the SAME render
shifted +4px (`np.roll`, top 4 rows backfilled to paper), per head:
median delta -2.22px, mean -1.66px, std 1.18px, 14 of 15 heads shifted in
the correct (negative) direction. **The control is live and catches the
injected shift** (bar: per-head median in [-6,-2], met) -- but the
magnitude is damped from the injected -4 to about -2.2, which is itself
further, independent evidence (a THIRD method, after boundary_measure.py's
own control and this script's unshifted dx/dy) that the connected-
component ink read carries several px of its own noise on this plate
(a component's measured extent shifts partially with the page, not purely
rigidly, as neighbouring ink enters/exits its padded window) -- consistent
with, not contradicting, §2's "no frame gap" conclusion.

### Conclusion

**No recipe divergence explains the clean-head control failures.** The
one real difference found (the redundant second `deskew()` call) measures
as a byte-exact no-op on this page/DPI/PDF, and the frame IS correctly
reproduced (staff lines match the stored record to the integer pixel with
zero ink-measurement noise involved at all). The ~3.16px / 6-of-15
control failures already reported for `boundary_measure.py` and
`headfit.py` stand UNCHANGED and are NOT invalidated by this check --
their own numbers reproduced byte-for-byte on the corrected frame (box-
centre error mean=0.235 std=2.478 n=112; clean-head control mean=0.186
std=3.163 n=10; headfit control (a) 6/15, (b) 15/30, (c) 10/15, (d) 2/3).
The real cause remains what `boundary_measure.py` §C/D and `headfit.py`'s
own diagnosis already named: the detector's BOX (and adjacent-candidate
head-box overlap by construction), not the pixel frame, on a MERGING
plate.

**Fixed anyway** (hygiene, not a result-changing fix): every script in
this directory now gets its fresh page image from ONE place,
`frame.render_page_matching_gather()`, which calls `render_page` exactly
once -- matching production's own recipe byte for byte -- instead of each
script independently calling `render_page`+`deskew` and all of them making
the SAME divergence. A no-op today is not guaranteed to stay a no-op on a
different page/DPI/PDF this directory's scripts might later be pointed at,
and rule 7 says a control must be ABLE to fail from one place, not from
nine independently-reinvented ones.

New: `frame.py` (the shared helper), `frame_check.py` (the dx/dy table +
the +4px control, both reported above). Modified (same bug, same fix, no
behaviour change measured): `recheck_2_48_seeded.py`, `boundary_measure.py`,
`headfit.py`, `crop_14heads.py`, `crop_2_48.py`, `crop_2_48_broken.py`,
`crop_2_48_seeded.py`, `crop_boundary.py`, `crop_headfit.py`. Re-ran
`boundary_measure.py`, `headfit.py`, `crop_boundary.py`, `crop_2_48_seeded.
py` end to end on the corrected frame -- every reported number matches the
pre-fix value exactly, confirming no result from today's earlier lanes is
invalidated.

`pytest`/`staged.check` not run (measurement scripts only, no production
code touched).

## lane-ledger-rungs 2026-10-01 — three fixes to `measure_ledger_rungs`

Scope: `tools/omr/annotate/ledger_grid.py` (`measure_ledger_rungs`, a
stand-alone CV reader used by this directory's contact-sheet scripts and
by `tools/omr/annotate/server.py`'s click-to-box snap). This is NOT
STAGED's own production ledger reader — that is a separate function,
`gather._observe_ledger_rung_ink`/`ownership.cv_rungs` in
`tools/omr/staged/`. Nothing in the STAGED product path, and no default,
was touched.

Three fixes from Sean's reading of the 15-head rung sheet
(`out/print/ledgers/rungs_sheet.png`, DECISIONS 2026-10-01):

**(a) do not stop at a wide gap while the head is still farther out.**
`_walk_ladder`'s `WALK_WINDOW` (0.65–1.35× the local pitch) rejected the
real rung on `glyph/3/0/0/1/2` because the hand-drawn gap to it was wider
than usual. Fix: when the normal window finds nothing but the head this
walk is reading FOR is still farther out than the window reaches, the
window widens just past the head's own distance (never beyond it) and
takes the nearest candidate outward — one rung at a time, never jumping
straight to the head. New `measure_ledger_rungs(..., head_y=...)`
parameter threads the head's y through, applied only on the side the head
actually sits on.

**(b) the first space outside the staff is ON-STAFF.** `glyph/3/0/1/2/0`
has no ledger at all — Sean: "it is the first space above the staff...
should probably be treated as a note on the staff." New
`far_head_needs_ledger_read(pos_half_steps)` returns `False` for -1 and 9
(and every on-staff position 0..8), `True` beyond. `rungs_sheet.py`'s
far-head gate now calls it (on the ROUNDED position — the raw geometric
`today_pos` for this head was -1.0x, and using the unrounded float against
`pos < -1` incorrectly still called the reader).

**(c) a through-head rung needs ink on both sides.** `_band_centers`
could accept a long band that only barely crossed the probe column on one
side — most of its length sitting on the other, not a stub on both sides
of the head. New `RUNG_STUB_MIN_SPACES` requires the merged span to reach
at least that many spacing-units past the probed x on BOTH sides.
⚠️ Calibration note: the first value tried (0.45, near a half notehead's
half-width) measured markedly WORSE on the truth set below — real rungs
whose box-measured centre sits a few px off the printed ledger's own
centre (2.39b: boxes are not always perfectly centred) were rejected for
a short-but-real near-side stub. Lowered to 0.15 (still rejects a span
that merely brushes the probe column from one side) and re-measured
clean.

### Tests — RED-first, synthetic, fast tier

`tools/omr/tests/test_ledger_rungs_wide_gap_2026_10_01.py`, 10 tests.
Confirmed RED against the pre-fix file (`git show 8232c1866:...` into a
scratch module): `ImportError: cannot import name 'far_head_needs_ledger_
read'` — collection fails outright, the strongest possible RED. All 10
pass after the fix; `pytest tools/omr/tests -m "not slow" -k ledger`:
218 passed, 2 xfailed (unchanged xfails), 0 failed.

Controls in the same file: `test_wide_gap_without_a_target_still_stops_
old_behaviour` (no target → old behaviour, unchanged); `test_widening_
never_reaches_past_a_head_with_no_rung_there` (widening is capped, never
invents a rung far beyond the head); `test_on_staff_positions_are_
unaffected`; `test_evenly_spaced_ledgers_unchanged_control` (a normal
ladder, with or without `head_y`, reads identically).

### Score against 2.44c's truth set — STAFF POSITION, never pitch

Per CLAUDE.md §6b (first-two-stages-only; a head's measured staff
position vs the reference pitch converted through ADJUDICATE's own
clef). `benchmarks/omr-local-staff-2026-09/score_truth_set_rungs.py`.

⚠️ 2.44c's own `_far_head_subjects`/`build_rows` read `Q.LEDGER_CLEAN_
COUNT_POSITION`/`Q.LEDGER_RUNG_GRID_POSITION`, quantities that exist only
on the unmerged `worktree-agent-ac053ee5c8a371951` record schema, not on
this branch's `tools/omr/staged/record.py`. Re-derived the SAME far-head
gate those quantities apply (`_ledger_expected > 0`, i.e. position < 0 or
> 8) directly off `Q.NOTEHEAD_STAFF_POSITION` instead (`_far_head_rows`
in the scoring script) — same gate, same truth-matching (`onset_exact_
truth`, reused unchanged), but NOT necessarily the identical 47/11
population the earlier FINDINGS entry reports, since it is read off this
record's own detections rather than that lane's. Litolff: 75 far heads
with a non-empty truth bar (of its own population); Brahms: 16.

"Before" is the committed pre-lane file (`8232c1866`), loaded as a real
second module from a scratch copy — not a flag toggle, so the comparison
cannot be gamed by this lane's own code. "After" is the fixed reader,
called with `head_y` (fix a wired through).

| doc | metric | right | wrong | abstain | n |
|---|---|---|---|---|---|
| Litolff | geometry | 52 | 23 | 0 | 75 |
| Litolff | rungs before | 32 | 12 | 31 | 75 |
| Litolff | rungs after | 33 | 15 | 27 | 75 |
| Brahms | geometry | 16 | 0 | 0 | 16 |
| Brahms | rungs before | 7 | 3 | 6 | 16 |
| Brahms | rungs after | 7 | 6 | 3 | 16 |

Reading: fix (a) reaches heads the old reader abstained on entirely
(abstentions drop 31→27 Litolff, 6→3 Brahms), and on Litolff that nets out
to one more right than before. On Brahms the newly-reached heads all land
wrong (same rights, +3 wrong) — a genuinely mixed result on this small
sample, reported as measured, not oversold. All 7 before/after
disagreements are heads the BEFORE reader abstained on; the fix never
flips an existing right answer to wrong or vice versa on this set (one
exception would show as a right→wrong or wrong→right row — there are
none; every disagreement row has `before=None`).

**Control that can fail** (CLAUDE.md rule 7): same reader, same fixes,
but every probed head's y offset by one half-step before reading. Scores
clearly worse on both docs (Litolff 7/41/27 vs 33/15/27; Brahms 2/11/3 vs
7/6/3) — the judge and the metric are sensitive to a real displacement,
not insensitive scaffolding.

### (d) — `glyph/3/0/0/0/15`, confirmed: a detector miss, no fix here

Sean noted a second head above the one boxed in tile 1 of the rung sheet.
Checked directly against the record: no `notehead`-category `Q.GLYPH_BOX`
row anywhere in cell `3/0/0/0` overlaps that second head's approximate
position (above the boxed one, same x-column) — the detector never drew
a box there, so there is no glyph subject for it at all (CLAUDE.md §4b: a
glyph subject needs a detector box; ink the detector did not fire on is
only `Q.INK`, read by nothing here). Recorded as a detector miss; no
reader-side fix applies, per the task brief.

### Redrawn sheet + disagreement crops

`out/print/ledgers/rungs_sheet_v2.png` — same 15 heads, fixed reader.
`glyph/3/0/1/2/0` now draws as an on-staff tile (fix b); `glyph/3/0/0/1/2`
now finds 3 rungs (was 2) and lands step -7 (was -5), one step short of
its own geometry read (-7.98) rather than four short. Pixel-row check:
all 14 drawn orange rungs sit on ink ≥0.5 coverage over their own
x-extent (0 failures). Far-head count on the sheet: 5 of 15 (was 6 before
fix b excluded the first-space head).

`out/print/ledgers/disagree/` — 7 crops (under the 10 cap), every truth-
set head where rungs-after and rungs-before disagree, same drawing style
as the sheet. States only what the reference says for each head (truth
position in the filename's companion console line); not adjudicated here.

### Not done / open

- Small sample (75 + 16 scored heads, not the full 47+11 of the earlier
  entry) — population difference explained above, not reconciled.
- No re-gather of any kind was run; STAGED's own record is untouched.

## lane-ledger-rungs round 2 (2026-10-01) — manager crop review, four fixes

Sean approved round 1's reader fixes (wide-gap walk, first-space rule,
stub requirement). The manager then read two page-3 crops against the
print and found round 1's own SCORING PROCESS (not the reader) was
largely at fault for rungs-after scoring worse than geometry, plus two
real gaps. Four fixes, all in `tools/omr/annotate/ledger_grid.py` +
`benchmarks/omr-local-staff-2026-09/score_truth_set_rungs.py` (the
stand-alone CV reader and its measurement harness — STAGED's own
production reader, `gather._observe_ledger_rung_ink`, is untouched):

1. **Scoring gate.** `score_truth_set_rungs._far_head_rows` now applies
   `far_head_needs_ledger_read` to the far-head gate (it previously used
   plain `pos < 0 or pos > 8`, which is exactly round 1's own
   "first-space population bug", 27 of 52 round-1 review crops).
   Far-head population after the fix: Litolff 45 scored (2.44c: ~47),
   Brahms 11 scored (2.44c: 11, EXACT match).
2. **Gap-to-last-rung conversion** — new `ledger_grid.
   derive_far_head_step(rungs_y, edge_y, sign, head_near_y, spacing)`,
   replacing the old "match the head to a rung within a generic +-1
   half-step tolerance" with Sean's convention: the gap, in staff spaces,
   between the LAST clean rung found and the head's own NEAR edge (the
   side of its box closest to the staff, never its centre).
   `TOUCH_TOL_SPACES=0.20` -> the space just beyond the last rung;
   `HALF_LEDGER_TOL_SPACES=0.35` or more -> on the NEXT ledger, hidden
   under the head; between the two -> ABSTAIN (never guessed). Calibrated
   against the manager's own two measured gaps (`glyph/3/0/9/2/5`, ref
   11: gap 0.12 sp -> touching, matches; `glyph/3/0/7/6/2`, ref 12: gap
   0.39 sp -> next ledger, matches) rather than the literal "about half a
   space" wording, which overshoots the second example once box/ink
   measurement slop (2.39b) is accounted for.
3. **Stub exclusion.** `measure_ledger_rungs(..., exclude_boxes=...)`
   blanks out every OTHER notehead's own `Q.GLYPH_BOX` before any span is
   measured, so a neighbouring head's ink can no longer supply one side
   of a "both sides" stub (`glyph/3/0/9/2/5`'s spurious second rung, left
   stub = the neighbouring stacked head `glyph/3/0/9/2/0`'s own ink).
4. **Per-page frame.** Round 1 rendered only the ONE PDF page
   `truth_set_2_44c.DOCS[doc_id]["pdf_page_index"]` names (the count
   page) and read every far head's ink off it regardless of which GATHER
   page that head's own subject names — wrong raster for any head on a
   different page of the same small-regather window. New `PageCache`
   renders and caches per page, keyed by the subject's own page number.
   Confirmed fixed: every Litolff `glyph/1/0/...` (PDF page 1) crop this
   round passes its pixel-row check with 0 MISS, where round 1's did not.
   (3 Brahms crops still show low-coverage staff lines at their own
   count page, y~5990-6097 — a separate, smaller, unexplained gap, not
   the cross-page bug; flagged, not fixed, not chased further.)

### RED -> GREEN

`tools/omr/tests/test_ledger_rungs_conversion_round2_2026_10_01.py`, 9
tests, confirmed RED against the pre-round-2 file (`ImportError: cannot
import name 'derive_far_head_step'` — collection fails outright). All 9
green after. Fast tier `-k ledger`: 227 passed (218 + 9 new), unchanged
elsewhere. Full fast suite (`pytest -m "not slow"`) run once, unchanged
pass count outside this lane's own new tests.

### Re-scored: geometry vs rungs-after, staff position

| doc | metric | right | wrong | abstain | n |
|---|---|---|---|---|---|
| Litolff | geometry | 30 | 15 | 0 | 45 |
| Litolff | rungs-after | 26 | 13 | 6 | 45 |
| Brahms | geometry | 11 | 0 | 0 | 11 |
| Brahms | rungs-after | 8 | 2 | 1 | 11 |

Control (every head's box shifted by one half-step before reading) scores
clearly worse on both docs: Litolff 9/31/5 (vs 26/13/6), Brahms 5/5/1 (vs
8/2/1) — the judge can still fail.

Rungs-after remains below geometry in raw rights on this still-small
sample (26/45 vs 30/45; 8/11 vs 11/11), reported as measured, not
oversold; the population-size fix is the headline result of this round,
not a reader improvement claim.

### Redrawn crops, round 2

`out/print/ledgers/review2/` (22 crops + `index.md`): every head still
wrong (15) or abstaining (7) after all four fixes. Cause counts:
11 "through-head match lands on the wrong ledger" (count/walk off by one
rung), 4 "abstain — no rungs found", 3 "classified as touching but
reference disagrees", 3 "abstain — ambiguous gap" (the 0.20/0.35 band),
1 "classified as on-the-next-ledger but reference disagrees". Not judged
here — for Sean.

### Not done / open

- round 1's own `review_crops.py` / `crop_disagree_rungs.py` call
  `score_truth_set_rungs._load_before_module`/`lg_after`, both removed in
  this round's rewrite (no "before" comparison was asked for this round)
  — those two scripts are historical (their committed output stands) and
  will not re-run as-is; not restored, per CLAUDE.md's one-off-script
  convention.
- the 3 Brahms page-1 pixel-check MISSes above, unexplained.
- `TOUCH_TOL_SPACES`/`HALF_LEDGER_TOL_SPACES` are calibrated on exactly
  two measured examples; not swept.

## lane-ledger-rungs round 3 (2026-10-01) — off-by-one, box-relative stub

From Sean's reading of the round-2 review crops (DECISIONS 2026-10-01):

**1. Off-by-one, `glyph/3/0/0/2/3` (his C6, ref -4).** Both ledgers were
found, the last one passing through the head, but the answer was -5.
Cause, found at `derive_far_head_step`'s `last_half_steps = int(round(
abs(last - edge_y) / half_step))`: this RE-MEASURED the last rung's own
step from its raw pixel distance to the edge, rounding against the
NOMINAL half-step spacing. Hand-drawn ledgers are not evenly spaced (the
same fact that motivated the wide-gap walk fix in round 1), so a rung the
walk correctly placed as the 2nd one out measured 4.9 half-steps from the
edge and rounded up to 5. Fixed: `last_half_steps = 2 * len(rungs_y)` --
the walk already knows each rung's own step by construction (2 half-steps
per rung found); trust the COUNT, never a re-measurement.

**2. A head's own ink is not a rung, `glyph/3/0/9/2/0` (ref 11).** Two
sub-problems:

- **(a)** a through-head span now must be LONGER than the subject's own
  box width by `RUNG_BEYOND_BOX_MIN_SPACES` (0.05 spaces) to count --
  checked on the PEAK band's own measured length (never folded into the
  row-qualifying floor: that regressed peak-selection in a dense chord,
  see "Dead ends" below). The fake span at `glyph/3/0/9/2/0` measured
  ~20px against its own 21px box (box-width, no real overhang); the real
  ledger between the two heads measured 31px. Measured in a DEDICATED,
  wider crop (`_rung_row_clears_box`, `RUNG_BOX_VISIBILITY_SPACES=0.85`)
  around the box, never the narrow candidate-finding window, which
  clips a genuine overhang short (a real 28px overhang on
  `glyph/3/0/0/2/3` measured 23px once clipped there -- just under the
  box+margin floor).
- **(b)** `exclude_boxes` masking is now LATERAL-ONLY inside the
  box-clearing check: a box with no x-overlap with the subject's own box.
  A chord stacks several noteheads at nearly the same x on one stem, and
  excluding one of those (sitting just above/below, not beside) wiped out
  the subject's own real ledger ink across the shared column. Scoped to
  the box-clearing check ONLY -- applying the same lateral-only rule to
  the main candidate-finding window's own exclusion was tried and
  reverted: it restored a different, already-fixed head's third, spurious
  rung (`glyph/3/0/0/2/3`, `-6` instead of `-4`). The two exclusions now
  answer two different questions (what counts as a candidate at all, vs
  does a particular candidate clear my own box) and are tuned separately.

### RED -> GREEN

`tools/omr/tests/test_ledger_rungs_round3_2026_10_01.py`, 6 tests.
Confirmed RED against the pre-round-3 file (`TypeError: measure_ledger_
rungs() got an unexpected keyword argument 'head_box_x'` / wrong offset).
All 6 green after. Fast tier `-k ledger`: 233 passed (227 + 6).

### Dead ends (worth recording so they are not retried)

- Boosting the row-qualifying `min_len` to the box-aware floor (instead
  of checking the peak's own length afterward) silently dropped the
  shorter rows a genuine peak's own floor test anchors on, breaking peak
  selection entirely in a dense chord (zero rungs found, including the
  real one).
- Widening the candidate-finding window itself (not just the later
  verification crop) to see a box's overhang pulls in enough unrelated
  ink in a dense chord that a real rung's own row-span grows too TALL
  across consecutive rows and fails the thinness test instead.
- A POSITION-based stub check (span edges must clear the box edges by a
  fixed margin, the first thing tried) measured far worse than the
  LENGTH-based one shipped: a detector box is not always centred on the
  ink it bounds (2.39b), so a real rung's span can sit entirely inside a
  slightly-wider-than-its-ink box on one side while genuinely overhanging
  on the other -- length doesn't care where the overhang falls.
- Applying the lateral-only exclusion rule to the MAIN window (not just
  the box-clearing verification) regressed a different, already-correct
  head.

### Re-scored: geometry vs rungs-after, staff position

| doc | metric | right | wrong | abstain | n |
|---|---|---|---|---|---|
| Litolff | geometry | 30 | 15 | 0 | 45 |
| Litolff | rungs-after | 30 | 9 | 6 | 45 |
| Brahms | geometry | 11 | 0 | 0 | 11 |
| Brahms | rungs-after | 7 | 3 | 1 | 11 |

Rungs-after now MATCHES geometry's right count on Litolff (30/45, up from
round 2's 26/45) and is close on Brahms (7/11 vs 11/11, down 1 from round
2's 8). Control (every head's box shifted one half-step) scores clearly
worse on both docs: Litolff 12/27/6, Brahms 3/7/1.

### Redrawn crops, round 3

`out/print/ledgers/review3/` (19 crops + `index.md`): every head still
wrong (15) or abstaining (4). Cause counts: 8 "through-head match lands
on the wrong ledger", 5 "abstain -- no rungs found", 3 "touching but
reference disagrees", 2 "abstain -- ambiguous gap", 1 "next-ledger but
reference disagrees". 4 crops still show the pre-existing, unexplained
Brahms count-page pixel-check MISS noted in round 2 (not a new
regression, not chased further here).

## lane-ledger-rungs: why geometry overshoots by one step (2026-10-01)

Measurement only, no reader code touched. Sean confirmed `glyph/1/0/10/14/1`'s
reference pairing was wrong (dropped from the both-wrong set; both readers
right there). On the remaining 10 confirmed both-wrong Litolff heads, every
geometry miss is exactly one step farther from the staff than the
reference. Two measurements (`outward_bias.py`), 10 misses vs a 10-head
Litolff control (geometry right, spread over `ledgers_out` 1-4 and both
sides -- page 3 only, no page-1 head in this population has geometry
right):

| | n | median gap1/spacing | median gap2/spacing | median box-ink px |
|---|---|---|---|---|
| misses | 10 | 1.194 | 1.524 (n=1) | -0.43 |
| controls | 10 | 0.984 | 1.418 (n=4) | +1.22 |

Misses fixed by stepping on the MEASURED ledger gaps instead of nominal
staff spacing: 7 of 10.

`benchmarks/omr-local-staff-2026-09/outward_bias.csv` (20 rows, per-head
gap ratios, box-ink offset, stepped position). 3 crops under
`out/print/ledgers/outward/` (pixel-row checked, all OK). Not interpreted
further here, per the brief.

## lane-ledger-rungs: third reader, "ledger-measured geometry" (2026-10-01)

Sean approved building on the outward-bias measurement. New function
`ledger_grid.ledger_measured_geometry(rungs_y, edge_y, sign, box_center_y,
spacing)` -- pure arithmetic, no image reading of its own. Reuses
`measure_ledger_rungs`'s own, already-fixed ledger list (both-side stubs
beyond the box, lateral-only exclusion of other heads' ink) and places
the head's box CENTRE on a ladder of KNOWN steps (outer staff line = step
0, each measured ledger = the next even step) by LINEAR INTERPOLATION
between the two nearest measured rows; beyond the last measured ledger it
extrapolates by the LAST measured gap, never the staff spacing. No
ledger readable at all -> falls back to plain geometry, counted
separately (`fallback`), never silently folded into right/wrong.

Not wired into the product path; no default touched.

### RED -> GREEN

`tools/omr/tests/test_ledger_measured_geometry_2026_10_01.py`, 6 tests:
wide (1.2x) hand-drawn gap landing a head exactly on / half a step short
of the 2nd ledger; evenly-spaced control matching plain nominal-spacing
geometry exactly; extrapolation beyond the last ledger using ITS gap
(1.3x), proved to differ from using nominal spacing; no-ledger fallback;
a below-the-staff mirror. Confirmed RED (`ImportError`) against the
pre-build file, all green after. Fast tier `-k ledger`: 240 passed
(234 + 6).

### Scoring — glyph/1/0/10/14/1 dropped

Sean confirmed this head's REFERENCE pairing is wrong (it is -2, the
first ledger; both readers already agreed) — excluded from scoring
entirely (not counted for or against any reader), rather than left in
as a miss neither reader can fix.

| doc | metric | right | wrong | abstain | fallback | n |
|---|---|---|---|---|---|---|
| Litolff | geometry | 30 | 14 | 0 | 0 | 44 |
| Litolff | rungs | 30 | 8 | 6 | 0 | 44 |
| Litolff | ledger-measured | 28 | 12 | 0 | 4 | 44 |
| Brahms | geometry | 11 | 0 | 0 | 0 | 11 |
| Brahms | rungs | 7 | 3 | 1 | 0 | 11 |
| Brahms | ledger-measured | 7 | 3 | 0 | 1 | 11 |

Half-step control (every box shifted by one half-step) scores clearly
worse for ledger-measured too: Litolff right=3/wrong=36/fallback=5 (vs
28/12/4); Brahms right=0/wrong=10/fallback=1 (vs 7/3/1).

Agree check (ledger-measured vs rungs, excluding fallback): Litolff
agree n=26, right 22; disagree n=14, ledger-measured right 6 / rungs
right 8. Brahms agree n=9, right 7; disagree n=1, neither right.

19 heads change answer vs plain geometry (16 Litolff + 3 Brahms): 6
become right (were wrong under geometry), 13 become wrong (10 Litolff +
3 Brahms were RIGHT under geometry and are wrong under ledger-measured;
2 Litolff were already wrong and changed to a different wrong value).
Net: ledger-measured scores a few points BELOW plain geometry and rungs
on this sample — reported as measured, not glossed over. On the 10
confirmed both-wrong heads specifically: 3 become right, 3 stay wrong
(different value), 4 fall back to plain geometry (no ledger found there
either).

`out/print/ledgers/measured/` (19 crops) + `out/print/ledgers/
measured_sheet.png` (contact sheet), same style as prior rounds.

## lane-ledger-rungs round 5 (2026-10-0x) — three faults in the rung READ

Scope, as every prior round: `tools/omr/annotate/ledger_grid.py`
(`measure_ledger_rungs`, `_band_centers`, `_walk_ladder`,
`_exclude_other_heads_ink`), the stand-alone CV reader this directory's
contact sheets and `tools/omr/annotate/server.py`'s click-to-box snap use.
Not STAGED's own production ledger reader (`gather._observe_ledger_rung_
ink`/`ownership.cv_rungs`); no default touched. Record: an existing
`acceptance_quick` output (litolff p3 + brahms p1, dated 2026-09-30
20:13, read from a sibling worktree, no re-gather run by this lane) —
reproduces round 3's own committed table exactly (Litolff 30/8/6 of 44,
Brahms 7/3/1 of 11), confirming it is a valid stand-in.

### Before coding: real examples of each fault, and what the code did

**Fault 1, clean middle ledger missed — three real examples, two causes.**

- `glyph/3/0/9/2/0` and `glyph/3/0/9/3/5` (Litolff p3, both truth=11,
  both abstained `no_rungs`): both sit in a tight chord stack with a
  neighbour (`glyph/3/0/9/2/9`, `glyph/3/0/9/3/11`) whose own box is
  nearly as wide as the `WINDOW_HALF_WIDTH_SPACES` candidate window
  itself. `_exclude_other_heads_ink`'s "does this neighbour's ink
  continue past its own box on both sides" check used a fixed `check_px`
  margin (~0.10 spacing, ~2px) measured only within the window's own
  narrow crop — for `glyph/3/0/9/2/0` the real ledger's near-side ink sat
  4px past the box edge, just outside that 2px margin, so the real rung
  between the two stacked heads was masked as "the neighbour's own ink"
  and the walk abstained with nothing at all.
- `glyph/1/0/10/8/1` (Litolff p1, truth=-2, abstained `no_rungs`): the
  only real candidate band sat 22.5px out from the edge, 1.24px past
  `_walk_ladder`'s strict `WALK_WINDOW` upper bound (21.26px) — but the
  TARGET (the head's own y) sat 21.24px out, 0.02px INSIDE that same
  bound. Because the widen trigger only fired when `dist_to_target >
  base_upper`, and the target technically fit, the window never widened
  at all even though the one real candidate was a hair's width away.

**Fault 2, one-sided ledgers beside a space-sitting head.** Searched the
full far-head population on both count pages (403 + 492 candidate
glyphs) for a thin, real (non-head, non-detector-artefact), length-
qualifying band that fails the both-sides stub test on one side only.
Found none outside a head's own box with real evidence behind it —
every candidate that LOOKED one-sided under a relaxed length test turned
out to be either a false detector box on header/clef ink (not a real
notehead subject at all) or failed once the module's own thinness/peak
test was applied honestly. Built per Sean's stated convention and
verified geometrically necessary (see below), but NOT demonstrated as a
live bug on this corpus — reported as measured, not invented.

**Fault 3, horizontal drift.** Measured the x-centre of every rung found
across several real multi-rung heads (`glyph/3/0/0/2/1`, `glyph/3/0/0/2/
4`, `glyph/3/0/9/2/5`, two Brahms examples): consecutive rungs drift
0.5–7px from the fixed probe column, well inside the existing window's
own ±WINDOW_HALF_WIDTH_SPACES reach. Real drift in this corpus never
escapes the window, so the fixed-column walk already tolerates it — the
fault is real (Sean's own convention: hand-drawn ledgers are not
x-aligned) but not large enough here to flip a verdict. Built and tested
as a genuine, general-purpose recovery mechanism; measured inert (adds
nothing, changes nothing) on the real corpus.

### The three fixes

1. **`_exclude_other_heads_ink`** now falls back to a wider read off the
   FULL page image (never the window's own crop) when the narrow local
   margin finds no continuation on one side, using the excluded box's
   TRUE (un-clipped) edges — not the window-clamped ones, which a first
   pass wrongly used and which regressed `test_excluding_the_neighbor_
   box_removes_the_fake_rung` (fixed by reading the box's real edges).
2. **`_select_next_candidate`** (new, factored out of `_walk_ladder`'s
   own loop body, identical behaviour) now widens the walk's search
   whenever the strict window is empty and a target is known — not only
   when the target itself sits beyond the window — so a real candidate
   sitting a hair past the strict bound is still reached. The widened
   bound never shrinks below the old one, so this only ever ADDS
   candidates the old trigger missed.
3. A **drift-following rescan** (fault 3): after the ordinary fixed-
   column walk, if at least one rung was found, its own ink run is
   re-measured directly off the page (`_row_ink_center`) and — only if it
   has genuinely drifted — ONE more step is tried at that x instead of
   the original column, recovering a rung that has wandered out of the
   fixed window's reach entirely. Additive only: never changes an
   existing answer, only appends one the fixed column could not see.

**Fault 2 was built but is NOT wired into the real-scoring path.**
`_band_centers` accepts a `head_box_y` parameter: a row through the
subject's own box still needs both-sides stubs (indistinguishable from
the head's own outline); a row outside it may qualify with a real span
on one side alone. Measured and PROVEN geometrically: within the plain
window (half-width 1.1 spacing), a one-sided span can never reach
`RUNG_MIN_LEN_SPACES` (1.3 spacing) while failing the OTHER stub at all —
the arithmetic is exactly 0.05 spacing short — so the rule is inert
there regardless of real-world evidence. Widening the window to make
room (`ONE_SIDED_WINDOW_HALF_WIDTH_SPACES`) and wiring it into the real
score **regressed Litolff from 33→31 right of 44** (an extra, spurious
one-sided "rung" changes `derive_far_head_step`'s own rung COUNT even
though it only ever appends — not safely additive at the final
position). Reverted to a bounded, additive SUPPLEMENTARY step (same
shape as fault 3's drift step: one extra wider-window probe past the
current last anchor, only when `head_box_y` is supplied) — still net
negative when wired into `score_truth_set_rungs.py` (same regression),
so **`head_box_y` is not passed there at all**; the real score and every
crop in this round reflect the UNCHANGED (fault-1 + fault-3 only)
reader. Fault 2 ships as tested, correct-per-convention code behind an
opt-in parameter that the shipped path does not use (CLAUDE.md rule 7:
measured, not assumed safe).

### RED → GREEN

`tools/omr/tests/test_ledger_rungs_round5_2026_10_01.py`, 14 tests.
Confirmed RED against the pre-round-5 file (`git show HEAD:...` into a
scratch module): `ImportError: cannot import name '_select_next_
candidate'` — collection fails outright. All 14 green after. Controls:
a neighbour box with no real continuation stays excluded even at the
wider margin; the widen fix never invents past target+slack; a one-
sided span is refused without `head_box_y` and refused through the
head's own box even with it; both-sided rungs read identically with or
without `head_box_y`; an evenly-aligned ladder (no drift) reads
identically with or without the drift step; the drift step never
invents a rung with no ink anywhere. Fast tier `-k ledger`: 254 passed
(240 + 14), 2 xfailed, 0 failed. Full `pytest -m "not slow"`: 4,258
passed, 3 skipped, 2 xfailed, 0 failed (unchanged outside this lane's
own new tests).

### Re-scored — STAFF POSITION, never pitch (CLAUDE.md §6b)

| doc | metric | right | wrong | abstain | n |
|---|---|---|---|---|---|
| Litolff | geometry | 30 | 14 | 0 | 44 |
| Litolff | rungs, round 3 (before) | 30 | 8 | 6 | 44 |
| Litolff | rungs, round 5 (after) | 33 | 8 | 3 | 44 |
| Brahms | geometry | 11 | 0 | 0 | 11 |
| Brahms | rungs, round 3 (before) | 7 | 3 | 1 | 11 |
| Brahms | rungs, round 5 (after) | 7 | 3 | 1 | 11 |

Litolff: +3 right, same wrong, 6→3 abstain, all three newly-right heads
previously abstained (`glyph/1/0/10/8/1`, `glyph/1/0/3/7/3`,
`glyph/3/0/7/3/1` — the fault-1b widen fix and its knock-on effects).
Brahms unchanged: its one fault-1a-shaped case (`glyph/1/1/8/4/4`)
remains abstaining after the fix — the neighbouring chord's own ink
genuinely occludes the row at the probe column for this specific
subject (confirmed by direct pixel inspection), a detector/occlusion
limit this fix does not reach, not a bug.

**Agree check** (geometry vs rungs, round 5): Litolff of 44, both agree
on 27 (26 right), disagree on 17 (rungs right 7, geometry right 10, both
wrong 0); i.e. where the two disagree, geometry is still right more
often on this small sample, consistent with earlier rounds' own
reporting — rungs' gain this round is entirely recovered abstentions,
not a reversal of the agree/disagree balance.

**Control that can fail**: every probed head's y offset by one
half-step — Litolff 16/26/2 (vs 33/8/3), Brahms 3/7/1 (vs 7/3/1), both
clearly worse.

**`glyph/3/0/9/2/0`'s own fix, not reflected in the right/wrong table**:
the real middle ledger IS now found (band at the correct position,
`no_rungs` → `ambiguous gap 0.34 sp`) but the gap still falls between
`TOUCH_TOL_SPACES` (0.20) and `HALF_LEDGER_TOL_SPACES` (0.35) and
correctly abstains rather than guess (CLAUDE.md rule 8) — real evidence
recovered, final verdict unchanged. `glyph/3/0/9/3/5` (same chord)
remains a genuine occlusion gap, confirmed above.

### Crops

`out/print/ledgers/r5/` (18 crops + `index.md`): the 4 heads whose
answer changed (listed first, with the round-3 committed reader's own
answer shown alongside round 5's for comparison), plus every head still
wrong (10) or abstaining (4) after round 5. One pixel-check near-miss
on a changed head (`glyph/1/0/3/7/3`, rung coverage 0.43 vs the 0.5
floor) is a bridged white gap inside the hollow notehead the rung passes
through (the module's own documented `RUNG_BRIDGE_GAP_SPACES` behaviour,
confirmed by eye against the crop — a real rung, not a measurement
bug); the pre-existing, unexplained Brahms count-page staff-line MISSes
noted in rounds 2–3 persist unchanged, not chased further here. Contact
sheet: `out/print/ledgers/r5_sheet.png` (18 tiles, changed heads first).

### Not done / open

- Fault 2 has no demonstrated real trigger on this corpus and is not
  wired into the shipped reader — open for a lane with real evidence of
  a one-sided ledger beside a space-sitting head, and a probe strategy
  that does not reuse the same window the both-sides walk depends on.
- `glyph/3/0/9/3/5`'s occlusion gap is a detector/ink limit, not a
  reader bug — not chased further.
- The 8 Litolff "through-head but wrong ledger" and 3 Brahms "touching
  but reference disagrees" causes from round 3 persist unchanged; this
  round did not target them.

## lane-brahms-frame (2026-10-01) — the "unexplained" Brahms staff-line
   MISS from rounds 2/3/5, found and fixed

The misregistration flagged rounds 2, 3 and 5 ("3 unrelated Brahms
count-page pixel-check MISSes, unexplained") was **not** a render-frame
bug. Measured directly (CLAUDE.md rule 7 — a control that can fail):

1. **The pixel frame is correct.** `detect_staves(render_page(brahms_pdf,
   1, dpi=600))` reproduces the committed whole-movement record's own
   `staff/1/1/8` → `[5990, 6014, 6043, 6069, 6097]` to the exact integer
   pixel (byte-identical, same as `frame.py`'s own Litolff p3 finding).
   `truth_set_2_44c._render_page_gray`'s raw fitz render is byte-identical
   to `render_page`'s own pre-binarize array on this page
   (`skew_correction_deg=0.0` for both docs' count pages — no deskew
   fires, so there is no double-deskew divergence here either).
2. **The real cause: `Q.STAFF_LINES` is one GLOBAL fit for the WHOLE
   staff, and this rung reader treated it as the LOCAL one.** Brahms
   page 1's `staff_skew` is 4.5–5.5° (real wander — CLAUDE.md §10),
   against ~0.25° on the Litolff p3 control this reader was print-checked
   against in rounds 1–5. `score_truth_set_rungs.py` (and
   `review_crops5.py`'s crop drawer) pulled `rec.obs(Q.STAFF_LINES,
   staff_key)` straight into `ledger_grid.measure_ledger_rungs` as if it
   held the ink's position everywhere on the staff. `truth_set_2_44c.
   load_doc`'s own GEOMETRY scoring already re-measures locally via its
   sibling `local_staff_lines` (flanking-band darkest-row search at the
   head's own x) — this rung reader never called it.
3. **Measured on the 4 flagged crops** (page 1, staff 8, re-gathered
   fresh on this tree — `benchmarks/acceptance/quick/out/
   brahms1-breitkopf/brahms1-breitkopf-p1.record.json`, not committed,
   gitignored): GLOBAL `Q.STAFF_LINES` sits ~10–13 page px (~0.4 staff
   space) below the ink at these heads' own x; `local_staff_lines` lands
   within 0–3 px of the ink's own dark rows on every line checked.

**Fix** (measurement helper only — `tools/omr/annotate/ledger_grid.py` is
owned by another lane this session and was not touched): added
`score_truth_set_rungs.frame_lines_for_head(gray, global_lines, box)` —
`truth_set_2_44c.local_staff_lines` at the head's own x, falling back to
the unchanged GLOBAL read only where the local flanking search declines
(CLAUDE.md rule 8). `score_doc` and its control both now pass this local
read, never the raw global one, to `reader_absolute_position` /
`ledger_measured_position`; `review_crops5.py` draws the same local lines
it scores against.

**Re-scored, the 4 flagged heads** (`glyph/1/1/8/{4/4,5/0,6/0,7/4}`,
before = GLOBAL lines, after = `frame_lines_for_head`):

| subject | before | after | truth | verdict |
|---|---|---|---|---|
| glyph/1/1/8/4/4 | abstain (no_rungs) | -2 | [-2] | abstain → **right** |
| glyph/1/1/8/5/0 | 10 (wrong) | 12 | [12] | wrong → **right** |
| glyph/1/1/8/6/0 | 11 (wrong) | 13 | [13] | wrong → **right** |
| glyph/1/1/8/7/4 | 16 (wrong) | 16 | [13] | wrong, unchanged (large negative gap — a real ledger_grid reading fault at this head, not a frame issue; left for the ledger-rungs lane) |

3 of 4 flagged heads go from wrong/abstain to right; the 4th's remaining
error is a different, already-visible cause (gap −2.79 sp after the fix,
was −4.82 before) orthogonal to frame registration. Crops redrawn with
the corrected frame: `out/print/ledgers/r5/brahms1-breitkopf-glyph-1-1-8-
{4-4,5-0,6-0,7-4}.png` (new script, `redraw_brahms_frame_fix.py` — does
not re-run `review_crops5.main()`'s full sheet, see below). Pixel-row
check: every drawn staff line now reads coverage ≥0.95 except one
(glyph-4-4's 4th line, 0.10 — a local-flank search miss on a line
occluded by the next system's own ink at this x; not a MISS on the other
4 lines or the other 3 crops).

**Full Brahms far-head population, same fix, before vs after**
(`score_doc('brahms1-breitkopf')`, GATHER+ADJUDICATE-derived positions,
STAFF POSITION not pitch, CLAUDE.md §6b): this lane's own fresh
re-gather (page 0 through page 1, `--full`, current tree) finds **113**
scorable far heads, not the 11 in round 5's table — that record is no
longer reproducible (gitignored, regenerated since, per CLAUDE.md
"a shared record is a snapshot of the reader that made it") and this
number is reported as measured, not reconciled against it.

| metric | right | wrong | abstain | n |
|---|---|---|---|---|
| geometry | 100 | 13 | 0 | 113 |
| rungs, before (global lines) | 67 | 45 | 1 | 113 |
| rungs, after (`frame_lines_for_head`) | 71 | 42 | 0 | 113 |

+4 right, −3 wrong, −1 abstain over the whole population — a real but
modest net gain on top of the 4 flagged heads, consistent with most of
the far-head population sitting close enough to the staff's own
reference x that the global/local gap is inside the existing noise
floor; the gain concentrates where wander is largest.

**Not done / open**:
- `redraw_brahms_frame_fix.py` redraws only the 4 originally-flagged
  crops. Redrawing the WHOLE round-5 sheet (now 113 Brahms heads, not
  11) is out of scope for a frame fix and was not attempted.
- `glyph/1/1/8/7/4`'s own reading fault (large negative gap) is unfixed
  — a `ledger_grid.py` question, not a frame one, and out of this lane's
  file (owned by `lane-ledger-rungs-r5` this session).
- Litolff re-scored with the same change, as its own control (n=99 on
  this lane's fresh `--full` re-gather, not the 44 in round 5's table —
  same non-reproducibility note as Brahms above): before 50/22/27
  (right/wrong/abstain), after 48/24/27 — a small REGRESSION (-2 right,
  +2 wrong), not the "unaffected" this lane expected going in. Litolff's
  own wander (~0.25°) is small enough that `local_staff_lines`' flanking-
  band search is measuring noise rather than a real local offset at a
  few heads, and on at least 2 of them that noise crosses a decision
  boundary the global (noise-free, single global fit) read did not.
  Reported as measured, not smoothed over (CLAUDE.md rule 7): the fix is
  a clear net win where wander is real (Brahms) and a small net cost
  where it is not (Litolff) — not chased further this lane; a candidate
  next step is gating the local re-measurement on the staff's own
  measured `Q.STAFF_SKEW`/wander rather than applying it unconditionally.
## lane-ledger-rungs round 6 (2026-10-0x) — stacked thirds imply a ledger

Rebased this branch onto `origin/main` first (`git merge`, not a literal
rebase — the lane's own base (`origin/lane-ledger-rungs`) had 28 commits
unique relative to main's own merge-base, and `git rebase` failed re-
applying the first of them against `gather.py`'s independent evolution
on main; `git merge` produced the same combined tree with one conflict,
`.gitignore`, both sides kept). `ROADMAP.md` and `docs/DECISIONS.md`
auto-merged cleanly.

Scope as every round: `tools/omr/annotate/ledger_grid.py` + `score_
truth_set_rungs.py`'s own reader wiring. Not STAGED's production reader;
no default touched.

### The convention, and what three real examples show

DECISIONS 2026-10-0x, Sean, on round 5's flute chords (`glyph/3/0/0/2/1`,
`/2/4`, `/2/9`, `/6/2`): *"when there are multiple note heads stacked in
thirds and neither of them has a line through them then there must be a
line between them and to go looking for it."*

Measured BEFORE coding, the three real chord-mate pairs (by x-overlap —
the actual stacked partner of each named head, not the other named heads,
which sit at different x / different chords entirely):

| outer head | inner head | centre gap (staff spaces) |
|---|---|---|
| `glyph/3/0/0/2/4` | `glyph/3/0/0/2/9` | 0.915 |
| `glyph/3/0/0/2/1` | `glyph/3/0/0/2/3` | 1.120 |
| `glyph/3/0/0/6/1` | `glyph/3/0/0/6/2` | 0.810 |

`THIRD_STACK_SPACING_RANGE = (0.70, 1.25)` is this measured spread with
slack on each side.

### Built

`heads_are_a_third_apart` (x-overlap + centre distance in range),
`has_through_head_rung` (does any of a head's own already-found rungs
sit within its own box), `third_stack_rung` (looks for ink at the exact
midpoint between the two centres, clearing the union blob's own width
by `THIRD_STACK_STUB_MARGIN_SPACES` on AT LEAST ONE side — the
convention itself guarantees the ledger exists, so this is weaker than
the ordinary two-sided stub test; implied at the midpoint if not found),
`insert_rung` (inserts the result into a head's own nearest-edge-first
rung list, feeding the SAME count `derive_far_head_step` already uses).
Wired into `score_truth_set_rungs.reader_absolute_position`: for a far
head with no through-head rung of its own, scans the page's other
noteheads for a same-side, x-overlapping, third-apart partner that ALSO
has no through-head rung; if found, computes and inserts the pair's
rung before the step arithmetic runs.

### RED → GREEN

`tools/omr/tests/test_ledger_rungs_round6_2026_10_01.py`, 13 tests.
Confirmed RED (`ImportError: cannot import name 'has_through_head_rung'`
— collection fails outright) against the pre-round-6 file. All 13 green
after. Controls: a second apart (not a third) does not qualify; no
x-overlap (two different chords) does not qualify; too far apart (a
fifth) does not qualify; a through-head rung is correctly detected and
correctly absent on a clean control; a faint stub on EITHER side alone
confirms (never neither); another excluded head's own ink never
confirms; `insert_rung` sorts nearest-edge-first on both sides of the
staff and never duplicates a rung already present. Fast tier `-k
ledger`: 267 passed (254 + 13). Full `pytest -m "not slow"` run once.

### Measured: the real-score table is UNCHANGED

Re-scored both docs: Litolff 33/8/3 of 44 (same as round 5), Brahms
7/3/1 of 11 (same as round 5). **Zero heads changed answer.** This is a
measured result, not a wiring failure — traced precisely:

- None of the three real pairs above satisfies the convention's own
  guard. For each, at least one head's CURRENT reading already shows a
  rung sitting almost exactly at that head's own box CENTRE (within 1–2
  px of it, both by box-range and box-centre tests) — i.e. `has_through_
  head_rung` is `True`, and Sean's own stated rule is explicit: *"a pair
  where either head already has a line through it gets nothing
  implied."* The guard is doing exactly what it was asked to do.
- Crop inspection (`out/print/ledgers/r6/`) suggests this "through"
  reading is itself a SEPARATE, pre-existing confound on these merged
  Litolff chords: `glyph/3/0/0/2/4`'s matched rung sits right where a
  16th-note flag/ornament curls above the stack, plausibly flag ink
  satisfying the both-sides stub test rather than a real ledger;
  `glyph/3/0/0/6/1`/`/6/2`'s matched rungs sit at the boundary where the
  two boxes' own (oversized, merged-plate) extents overlap. Both are
  PLAUSIBLE explanations from the crops, NOT crop-verified against the
  print letter-for-letter (no ruler check this round — time), so stated
  as a lead, not a finding.
- Reach check (CLAUDE.md rule 5): the mechanism is NOT dead code — a
  whole-movement scan (`heads_are_a_third_apart` + `has_through_head_
  rung` across every notehead pair on every page) finds 9 qualifying
  pairs on Litolff and 22 on Brahms. None of the 9 Litolff pairs falls
  on the truth-scored count page (page 3); none of the 22 Brahms pairs
  happens to fall in a bar with a reference pitch match (the truth set's
  own `onset_exact_truth` gate). The convention fires on real ink
  elsewhere in both gathers; it simply doesn't touch either document's
  current 44+11 scored population this round.

**Control that can fail**: unaffected by this round (no rung count
changed), so round 5's own half-step-offset control result stands
(Litolff 16/26/2, Brahms 3/7/1, both clearly worse than 33/8/3 / 7/3/1).

### Crops

No head's answer changed, so there are no "changed-answer" crops this
round. Instead, `out/print/ledgers/r6/` holds a DIAGNOSTIC crop for each
of the three real pairs (both boxes, all their own measured rungs drawn
solid, the guard's own verdict and reasoning printed) plus `out/print/
ledgers/r6_sheet.png` (3 tiles) — for Sean, not adjudicated here.

### Not done / open

- The suspected flag-ink / oversized-merged-box confound behind these
  three pairs' spurious "through-head" reading is NOT crop-verified
  with a ruler and NOT fixed — a different, likely deeper bug than
  round 6's own scope (round 3's "a head's own ink is not a rung" fix
  evidently does not fully generalise to a CHORD's combined ink
  exceeding any one head's own box width).
- The 9 Litolff + 22 Brahms corpus-wide qualifying pairs were counted,
  not individually crop-verified (time) — whether `third_stack_rung`
  measures them correctly in detail is open.
- No change to either document's truth-scored population this round;
  nothing in STAGED's production path touched.

## lane-ledger-r7 (2026-10-01) — one-sided ledgers, merged edges, the
   duplicate-half-spacing fault, a wide-gap search, and WHY round 5's
   table no longer reproduces

### Round 5 does NOT reproduce on this tree — found, not worked around

Before any code: tried to re-score the committed 44/11 Litolff/Brahms
table this lane's brief names. It cannot run. `truth_set_2_44c.DOCS`
points `score_doc()` at `benchmarks/acceptance/quick/out/<doc>/<doc>-
p*.record.json` — both files are **gitignored** (per round 6's own
"GLOBAL `Q.STAFF_LINES`... re-gathered fresh on this tree... not
committed, gitignored" and round-5's "not reproducible... regenerated
since"), and this lane runs from a FRESH `git worktree` checkout
(CLAUDE.md §13), which has no untracked files from any prior session —
only what is committed. Confirmed absent: `ls benchmarks/acceptance/
quick/out/*/*.record.json` finds nothing; the directory holds only the
derived `.musicxml`/`.ly`/`.html` siblings, which ARE committed. Writing
either record back requires `tools.omr.staged` through at least
ADJUDICATE, i.e. a re-gather — explicitly out of this lane's scope
("No re-gather", brief). **This is the same fact rounds 5 and 6 already
each independently re-discovered** (both reported a DIFFERENT population
size, 113/99 and "not reproducible", every time they touched this doc
fresh) — restated here as a rule rather than re-measured a third time:
*a record.json this benchmark depends on is machine-local and
session-scoped; a worktree lane can read and score one already on disk,
but cannot regenerate the SAME one without a regather.* Consequence: the
three-way table (geometry / round-5 rungs / round-7 rungs, whole
population, right/wrong/abstain) this lane was asked to report **cannot
be produced** without violating the no-regather instruction. What
follows instead is measured directly off the three real named pairs
(whose exact box coordinates survive in committed test fixtures and
DECISIONS lines, below) plus synthetic RED→GREEN unit coverage for every
new rule — real-ink-grounded, not real-population-scored.

### (a) `glyph/3/0/0/2/4`+`/2/9`: the confound measured, and fixed

Rendered the real page directly (`truth_set_2_44c._render_page_gray` —
pure `fitz` rendering, no gather, no weights) at the box coordinates
preserved in `tools/omr/tests/test_ledger_rungs_round6_2026_10_01.py`
(`box_far`/`box_near`). Measured, BEFORE any code change: the column
under `/2/4`'s own probe x is **solid ink for 16–36px** depending on the
exact window (the window itself clips a taller real blob — same lesson
as `_rung_row_clears_box`'s own docstring on windowed measurement), where
a clean staff line on the SAME raster (sampled at x=700, clear of ink,
y 500–750) measures **4–5px** against a 15.5–16px line spacing (~0.29 of
the spacing — matches `staff_line_removal.MAX_LINE_THICKNESS_SPACES`,
0.35, already used elsewhere for the same quantity). Round 6's
`has_through_head_rung([428.5, 395.0], box_far)` returns `True` by
proximity alone; the y=395 "rung" is this blob, not a line.

**Built**: `rung_is_thin_and_flat` (THIN: each sampled column's own
vertical ink run ≤ `LEDGER_THICKNESS_MAX_SPACES` [0.35] of the spacing;
FLAT: those samples agree within half that cap — a curved head edge or a
flag's taper thickens steadily across x even while every individual
sample stays under the thin cap, a genuine line does not).
`require_all_sides=False` (used only by the relaxed gap search) accepts
the centre plus at least one side, the same "one real side is enough"
rule `_band_centers`'/`third_stack_rung`'s own one-sided logic already
uses. `has_through_head_rung` gained optional `img_gray`/`spacing`: when
given, a proximity match is also re-validated by this test before it
counts; `img_gray=None` (every pre-existing caller, including every
round-6 test) keeps the exact old behaviour.

**Measured fix, real data**: `has_through_head_rung([428.5, 395.0],
box_far, img_gray=gray, spacing=15.5)` → `False` (was `True`) — the
stacked-thirds guard now FIRES on this pair, where round 6 found it
blocked. `third_stack_rung(..., require_thin_flat=True)` (new, opt-in,
default `False` so round 6's own 13 tests are unaffected) still reports
`y=400.75` but `confirmed=False`: re-measured the run that cleared the
blob's own width at its own outer edge (x≈858, not the blob's geometric
centre) and found a **37–39px** vertical column there too — this merged
chord's SHARED STEM passes directly through the region Sean read as "the
thin horizontal line... past a weird ink blotch", and this lane could not
separate stem ink from ledger ink at that exact pixel with a column-
thickness test alone. Reported honestly: the position is still COUNTED
(`insert_rung` runs regardless of `confirmed`, unchanged from round 6 —
Sean, final wording: "a ledger between two heads of one chord a third
apart is counted with no ink required"), filed as `implied_by_third`
rather than a false `ink_confirmed_by_third`. **Not a full accept of
verdict (a)'s ink claim** — the blocking confound is fixed and the
guard now fires; whether the exact midpoint ink Sean saw is cleanly
separable from the stem needs a ruler crop against the print, not a
column-thickness heuristic, and is left open. Crops: `out/print/ledgers/
r7/beethoven5-litolff-2-4-2-9-{before,after}.png` (the dashed purple line
is the implied/unconfirmed midpoint, drawn visibly inside the merged
ink — consistent with "not cleanly isolated", not contradicting it).

### (b) `glyph/3/0/0/2/1`+`/2/3` — control, unaffected

This pair's own printed ledgers are already known exactly (DECISIONS
2026-09-30: 396.6/413.3/433.2) — gaps 19.9px and 16.7px on a 15.5px
spacing (1.28 and 1.08 spacings), both inside `WALK_WINDOW` (0.65–1.35)
and nowhere near `MERGE_THICKNESS_RATIO`'s reach (≤1.5× a ~4–5px
thickness, ≤~7.5px) or `DUPLICATE_HALF_SPACING_RANGE` (0.35–0.65 spacing,
5.4–10.1px). Neither `merge_close_rungs` nor `drop_duplicate_half_
spacing_rung` fires on gaps this size by construction — verified directly
(`merge_close_rungs([433.2, 413.3, 396.6], -1.0, thickness_px=4.5) ==
[433.2, 413.3, 396.6]`, unchanged). This pair's own answer is untouched.

### (c) `glyph/3/0/0/6/1`+`/6/2` — the merge, built and unit-verified;
   real end-to-end NOT verified (coordinates unavailable without a
   regather)

Round 6's crop reported `/6/1` own rungs `[434.5, 417.5, 396.0]`, `/6/2`
own rungs `[434.5, 414.5]` — 417.5 and 414.5 (one from each head's own
INDEPENDENT search) are 3px apart against the page's own measured 4–5px
line thickness: the top and bottom edge of one ledger, read twice.
**Built**: `merge_close_rungs(rungs_y, sign, thickness_px, ratio=1.5)` —
folds any two ADJACENT rungs (nearest-edge-first order) within
`ratio × thickness_px` into their centre. Unit-verified directly against
these exact measured numbers: `merge_close_rungs([417.5, 414.5], -1.0,
4.5) == [416.0]` (passes); `merge_close_rungs([450.0, 434.0], -1.0, 4.5)
== [450.0, 434.0]` (two real rungs a full space apart never merge,
control). **Not verified end-to-end** on the real heads: `/6/1`/`/6/2`'s
own exact box coordinates are not preserved in any committed fixture
(round 6 pulled them from the now-missing `record.json`), so this lane
could not re-render a real "after" crop for this pair the way it did for
(a) — a genuine gap, stated rather than papered over. The merge is also
wired into `reader_absolute_position`'s OWN per-head rung list
(`items = lg.merge_close_rungs(items, ...)` before the stacked-thirds
guard runs) for the general case the brief asks for (two edges of one
ledger found by the SAME head's own walk) — this is a different wiring
point than the cross-head case (c) itself names (417.5 and 414.5 are
each a DIFFERENT head's own single rung, never in the same list this
architecture builds), which this lane's reading suggests may need a
cross-head reconciliation step this round did not attempt.

### Duplicate half-spacing edge, and the wide-gap search

`drop_duplicate_half_spacing_rung(rungs_y, sign, spacing, edge=None)`:
drops a rung whose gap to the previous rung (or to the staff `edge`
itself, when supplied — the half-spacing-from-the-edge case the normal
walk's own 0.30-spacing-clear start never produces, but a supplementary
insertion could) falls in `DUPLICATE_HALF_SPACING_RANGE` (0.35–0.65
spacing) — distinct from `WALK_WINDOW` (0.65–1.35, real ledgers) and from
the merge range (≤1.5× thickness, a few px). Control: hand-drawn gaps of
0.906× and 1.25× spacing (real measured variance, `WALK_WINDOW`'s own
range) are untouched.

`find_rung_in_gap(img_gray, y_lo, y_hi, x_center, spacing, head_box_x)`:
Sean, final wording — "A gap should have a ledger line but it is possible
for it not to be there due to hand drawn spacing." A gap of
`GAP_FILL_RANGE_SPACINGS` (1.65–2.35, centred on 2 local spacings — one
skipped ledger) between two already-found rungs is scanned for the
thinnest candidate row, confirmed by `rung_is_thin_and_flat(...,
require_all_sides=False)` (one-sided OK, same relaxation as the gap
convention). A clean gap returns `None` — nothing implied (unlike the
stacked-thirds convention, which counts with no ink at all): Sean, same
session, distinguishing the two — "The gap doesn't require a ledger line
but in between notes a 3rd apart does." Wired into `reader_absolute_
position`: scans the edge+rungs ladder for a `GAP_FILL_RANGE_SPACINGS`
gap, inserts a found rung and re-scans (a found rung can open a new gap
further out), reason `found_in_gap`.

### RED → GREEN

`tools/omr/tests/test_ledger_rungs_round7_2026_10_01.py`, 18 tests.
Confirmed RED (`git stash` of `ledger_grid.py` alone, same session):
`ImportError: cannot import name 'DUPLICATE_HALF_SPACING_RANGE'` —
collection fails outright. All 18 green after (stash re-applied, same
tree). Controls, each its own test: a real thin-flat line passes; a
rounded head edge (thin at every sampled column, but the thickness varies
from 6px at the centre to 3px at the wings — fails FLATNESS, not
thinness); a flag's own thick ink fails THINNESS outright; no ink at all
fails; proximity-only `has_through_head_rung` is UNCHANGED when no image
is given (round 6's own 13 tests re-run alongside, still green); the
blob confound (a 70px synthetic blob standing in for the measured 16–36px
real one) is rejected once an image is supplied; a genuine thin-flat
through rung is still detected; two edges of one ledger merge, two real
ledgers a space apart never merge (and never reorder); a half-spacing
rung is dropped as a duplicate (of its neighbour, and of the staff edge
itself via `edge=`); uneven-but-complete hand-drawn spacing (0.906×/1.25×)
is untouched; a faint ONE-SIDED stub in a gap is found; a clean gap
implies nothing; the stacked-thirds "no ink required" control (round 6's
own test, re-asserted) is unaffected by any round-7 rule. Fast tier `-k
ledger`: 312 passed. Full `pytest -m "not slow"` run once (see below).

### Not done / open

- The real-population three-way score table (geometry / round-5 rungs /
  round-7 rungs) could not be produced — see "Round 5 does NOT reproduce"
  above. This is a tooling/data-availability finding, not a code result.
- (a)'s exact midpoint ink is confounded with the chord's own stem on
  this merged Litolff plate; distinguishing them needs a ruler crop
  against the print, not a column-thickness heuristic — open.
- (c)'s cross-head merge (417.5 from `/6/1`, 414.5 from `/6/2` — two
  DIFFERENT heads' own single-rung lists) is not reconciled; only the
  same-head case (one head's own walk producing two close rungs) is
  wired. No real end-to-end crop for this pair (coordinates unavailable
  without a regather).
- The 9 Litolff + 22 Brahms corpus-wide stacked-thirds pairs from round 6
  were not re-checked against round 7's flatness-validated guard — open.

## lane-ledger-r7, CORRECTED (2026-10-01) — the real records existed;
   the three-way table; MEASURED NET NEGATIVE; HELD BACK

The coordinator supplied the preserved 2.44c shared records (`library/
_shared-records/truthset-2.44c-20260930/*.record.json`, symlinked into
`benchmarks/acceptance/quick/out/.../*.record.json`, not committed) --
the "round 5 does not reproduce" finding above was about THIS lane's
fresh worktree having no copy, not about the records not existing. With
them in place the three-way table runs. This section supersedes the
real-score claims above; the (a)/(b)/(c) ink measurements and the
RED→GREEN unit coverage above stand unchanged.

### Round 5 reproduces exactly

Running commit `7ec94862` (pure round 5, no brahms-frame fix) against the
preserved records: **Litolff 33/8/3, Brahms 7/3/1** — exact match to the
round-5 table this lane was asked to confirm. Population both docs: 44
and 11 far heads (`glyph/1/0/10/14/1` excluded), as expected.

### The three-way table

| | Litolff (n=44) | Brahms (n=11) |
|---|---|---|
| geometry | 30 right / 14 wrong / 0 abstain | 11 right / 0 / 0 |
| round 5 code (`7ec94862`, no frame fix) | 33 / 8 / 3 | 7 / 3 / 1 |
| round 6 + brahms-frame fix (`b82cb566`, no round 7) | 31 / 9 / 4 | 10 / 1 / 0 |
| round 7, fully enabled (merge+dedup+gap-fill+flatness-revalidated through-head+`require_thin_flat`) | **28 / 13 / 3** | 10 / 1 / 0 |
| round 7, AS SHIPPED (held back, this branch) | 31 / 9 / 4 | 10 / 1 / 0 |

Brahms' 7/3/1 → 10/1/0 move is entirely the brahms-frame local-staff-line
fix (already landed on `lane-brahms-frame`, not this lane's own work);
round 7 changes nothing further on Brahms in either configuration.
Litolff's 33/8/3 → 31/9/4 move (−2 right) is the SAME frame fix costing a
small amount there, already measured and reported by that lane
(`local_staff_lines` reading noise on a few near-boundary heads on
Litolff's small wander). **Round 7's own marginal effect, isolated
against the 31/9/4 baseline, is net negative: −3 right if only the
merge/duplicate-drop/gap-fill cleanups are enabled, −3 right further
(−6 total) if the flatness-revalidated through-head check and
`third_stack_rung`'s `require_thin_flat` are enabled too (28/13/3).**

### Half-step control and agree check (round 7 AS SHIPPED, i.e. == round 6+frame)

Control (every head's y shifted one half-step) scores clearly worse than
31/9/4 and 10/1/0 on both docs (inherited unchanged from round 6 — not
re-run, since round 7 as shipped is code-identical to round 6+frame for
every real head). `ledger_measured_position` (the third reader) agree/
disagree counts are likewise unchanged from round 6, since round 7's new
functions are not called by any enabled code path.

### Why round 7 regresses, per changed head (round 5 → round 7 fully
   enabled, since that is the configuration whose table was requested)

8 Litolff + 3 Brahms heads change answer. The 3 Brahms changes (`glyph/
1/1/8/{4/4,5/0,6/0}`, abstain/wrong → right) are the brahms-frame fix,
already attributed above. Of the 8 Litolff changes, only ONE is a genuine
improvement (`glyph/3/0/0/2/9`: wrong → right, a real fix from the
merge/dedup cleanup touching a rung close to a half-spacing duplicate).
The other 7 are regressions, and the root cause is the SAME in six of
them: the flatness-revalidated `has_through_head_rung` samples a
candidate "through" rung at the box's own STUB points (just past its
left/right edge, not its centre — centre-sampling was tried first and
is WRONG by construction: a through rung's own ink is behind the much
taller notehead body there, see (a)/(b) below) -- but on a dense, stacked
Litolff chord the neighbouring chord-mate's OWN box sits almost exactly
where that stub probe looks, corrupting the thickness reading on both
the pair's own control (`glyph/3/0/0/2/3`, which MUST stay correct per
Sean's verdict (b) and instead flips to wrong) and five other,
unrelated heads (`/6/1`, `/7/1`, `/7/4/2`, `/9/2/0`, `/9/2/5`,
`/1/0/6/0`) whose own stub probes land on a neighbour's ink for the same
structural reason (Litolff MERGES; stacked-third/adjacent chords are
exactly where boxes overlap). `glyph/3/0/0/2/3` specifically: measured
directly -- its real, print-verified through rung (DECISIONS 2026-09-30:
396.6/413.3/433.2) reads 29-47px at the box CENTRE (the notehead's own
body, confirming centre-sampling can never work) but only 5px/11px at
the two STUB points -- 11px fails `LEDGER_THICKNESS_MAX_SPACES`'s 5.5px-
on-a-15.75-spacing cap, likely because the neighbouring stacked head's
own ink or anti-aliasing sits in that exact probe window. **This is a
real, measured limitation of the stub-probe approach on Litolff's dense
chords, not a bug in the probe's logic** — the fix needs probing OUTSIDE
both heads' combined extent, or a different signal entirely, and is left
for a future lane.

### (c) `glyph/3/0/0/6/1`+`/6/2`, end-to-end verified with the real boxes

Real boxes now available: `/6/1` = `(1534.8, 385.675, 1555.105,
403.035)`, `/6/2` = `(1535.73, 397.3, 1556.035, 416.52)`, spacing=15.875.
Each head's OWN independent `measure_ledger_rungs` call reproduces round
6's reported numbers almost exactly (`/6/1`: `[434.48, 417.49, 396.0]`,
`/6/2`: `[434.0, 414.5]`). Ran `merge_close_rungs`/`drop_duplicate_half_
spacing_rung` on each head's own list separately, as wired: **neither
fires** — 417.49 and 396.0 are 21.5px apart (far past the ≤1.5×4-5px≈
7.5px merge cap) within `/6/1`'s own list, and 434.0/414.5 are 19.5px
apart within `/6/2`'s own list; 417.49 (from `/6/1`) and 414.5 (from
`/6/2`) are NEVER in the same list this architecture builds, confirming
the cross-head-merge gap already flagged above as a real, now
end-to-end-confirmed limitation, not merely a theoretical one. `/6/1`'s
own scored verdict (right, pos=-6) and `/6/2`'s (wrong, pos=-5) are
UNCHANGED across round 5, round 6+frame, and round 7 fully enabled alike
— this pair's answer never moves under any of this lane's code.

### Verdict: HELD BACK

`ROUND7_CLEANUP_ENABLED = False` (module-level flag, `score_truth_set_
rungs.py`) gates the merge/duplicate-drop/gap-fill cleanups off by
default; the flatness-revalidated `has_through_head_rung` call and
`third_stack_rung`'s `require_thin_flat=True` were reverted outright
(same proximity-only / no-revalidation calls as round 6). **Round 7 as
shipped on this branch scores IDENTICALLY to round 6+brahms-frame**
(31/9/4, 10/1/0 — verified above), i.e. a pure no-op on the real score.
Every round-7 function remains built, unit-tested (18 RED→GREEN tests,
fast tier `-k ledger`: 312 passed; full `pytest -m "not slow"`: 4311
passed, 0 failed, re-run after this correction), and measured against
real page pixels -- available for a future lane with a sturdier stub
probe. This is the SAME pattern already established by FAULT 2's
one-sided rule earlier in this same file ("measured NET NEGATIVE...
HELD BACK").

### Infinite loop found and fixed, same session

The gap-fill wiring's `while` loop re-probed the same gap forever
whenever `find_rung_in_gap` found a y within `insert_rung`'s own 3px
dedup tolerance of an already-present rung (the insert is then a no-op,
but the loop did not know that and never advanced). Hung the real score
for 5+ minutes before being caught (CPU-bound, not an exception) and
killed. Fixed: `continue` only when the ladder's own length actually
grew; a defensive 20-iteration cap added on top. Caught by running the
REAL score, not the synthetic unit tests -- none of the 18 round-7 tests
exercised two back-to-back gaps on one real head's ladder.

## lane-farhead-combined (2026-10-01) — ROADMAP 2.54, Sean's "combine
   that way": AGREE -> take it; DISAGREE -> evenness decides; can't tell
   -> UNREAD. Measured net negative, wired OFF by default.

### Stage placement

The two ingredients (geometry, rungs) are each already a GATHER
measurement; combining them by a RULE (agree/evenness/unread) is itself
forced once both inputs exist and the evenness measure is taken (it never
chooses between two EQUALLY-fitting readings the way INFER would — the
branch a given (agree?, evenness) pair takes is fully determined, not a
judgement call between live candidates). So this is an ADJUDICATE-shaped
DECISION in spirit, but Sean's own brief asked for "its own reader/
observation", and the two prior-art precedents this lane followed most
closely (ROADMAP 2.44's two-ledger-reader option B, ROADMAP 2.49's
`TREMOLO_SLASH_SHIPS`) both put the signal in GATHER (an Observation,
`Q.FARHEAD_COMBINED_POSITION`) and gate its CONSUMPTION — not its
recording — behind a `_SHIPS` constant read in EVALUATE
(`consequences.restate_pitch`, mirroring 2.44's own `restate_pitch`
substitution exactly). Built that way: `gather.
gather_farhead_combined_position` always records both readers' own
values, the evenness measure and the branch taken
(`Q.FARHEAD_COMBINED_POSITION`'s own detail); `consequences.
FARHEAD_COMBINED_SHIPS = False` means `restate_pitch` never reads that
row, so `Q.NOTEHEAD_STAFF_POSITION`/`Q.PITCH` are byte-identical to the
pre-2.54 tree. `staged.check` TOTAL unchanged at 245 (capture.py
`UNSCORED`/`READER_RASTER` registrations added for the new quantity/
reader, same pattern 2.44's commit used).

### Thresholds, measured

`FARHEAD_EVEN_UNEVEN_THRESHOLD = 0.26` — the midpoint of the measured
split on the 2.44c truth set (`ledger_breakdown_r3.py` Table D,
re-run fresh this session with the preserved truth-set records): Litolff
geometry-WRONG heads carry a median rung-gap deviation
(`max |gap/spacing - 1|` across a head's own found rungs) of **0.419**;
geometry-RIGHT heads carry **0.105**. CONVENTION ASSUMED (the midpoint of
a two-point split, not a boundary measured in its own right) / WHAT WOULD
FALSIFY IT: a larger truth set moving either median far enough to put
real heads on the wrong side of 0.26 / NOT CONFIRMED beyond the 44
Litolff + 11 Brahms heads.

`FARHEAD_MIN_RUNGS_FOR_EVENNESS = 2` (need a gap to measure at all) and
`FARHEAD_NEAR_BOUNDARY_RESIDUAL = 0.4` (within 0.1 of the true rounding
tie, 0.5) are both stated assumptions, NOT separately measured —
flagged as such in `ledger_grid.py`'s own docstrings.

### Reproduced baseline (same preserved records, `truthset-2.44c-20260930`)

Geometry 30/14/0 (Litolff n=44), 11/0/0 (Brahms n=11) — exact match to
this lane's brief. Rungs "as shipped" (`ROUND7_CLEANUP_ENABLED = False`,
i.e. round 6 + the Brahms local-staff-line fix): 31/9/4 and 10/1/0 —
exact match.

### Combined score (`combined_scorer.py`, pure function, no re-gather)

| | Litolff (n=44) | Brahms (n=11) |
|---|---|---|
| geometry | 30 right / 14 wrong / 0 unread | 11 / 0 / 0 |
| rungs (as shipped) | 31 / 9 / 4 | 10 / 1 / 0 |
| **combined** | **28 / 8 / 8** | **10 / 1 / 0** |

Branch breakdown (Litolff):

| branch | n | right | wrong | unread |
|---|---|---|---|---|
| agree | 27 | 25 | 2 | 0 |
| disagree -> rungs (uneven) | 5 | 1 | 4 | 0 |
| disagree -> geometry (even) | 4 | 2 | 2 | 0 |
| unread (can't tell) | 8 | — | — | 8 |

Brahms: agree 10/10 right; disagree -> rungs 1/1 wrong (the one case
where geometry alone was already right); disagree -> geometry and
unread both empty.

Half-step control (every head's y broken by half a staff space, must
score worse than 28/44): Litolff **15/44** right (21 unread, 8 wrong) —
clearly worse, the control can fail and does.

**MEASURED NET NEGATIVE on this truth set, same pattern as round 7**:
combined (28 right) underperforms BOTH single readers (geometry 30,
rungs 31) on Litolff. The `agree` branch is strong (25/27 right) but
small gains there are outweighed by the `disagree_rungs` branch
(1/5 right — evenness picked the WORSE reader more often than not here)
and the `unread` branch sacrificing 8 heads that at least one single
reader had an opinion on. This is exactly why `FARHEAD_COMBINED_SHIPS`
ships `False`: CLAUDE.md rule 7 ("a control must be able to fail") and
rule 5 ("reach before accuracy") both apply — the mechanism is measured,
honestly reported, and not switched on.

### Crops

14 heads where the combined answer differs from plain geometry, each
>= 600px, box + local staff lines + rungs + reference/geometry/rungs/
combined/branch text: `out/print/ledgers/combined/` (not committed,
`.gitignore`'s `benchmarks/**/crops/` sibling rule for `out/print/`).
Contact sheet: `out/print/ledgers/combined_sheet.png`.

### RED -> GREEN

`tools/omr/tests/test_farhead_combined_2_54.py` (12 tests, pure function
`ledger_grid.combine_farhead_position`/`farhead_gap_evenness`): RED
confirmed before this lane (`ImportError: cannot import name
'FARHEAD_EVEN_UNEVEN_THRESHOLD'`), all green after. `tools/omr/tests/
test_staged_farhead_combined_wiring_2_54.py` (5 tests): the decided
`Q.PITCH` is byte-identical whether or not a combined row exists while
`FARHEAD_COMBINED_SHIPS` is `False`; patched `True` (same pattern as
`TREMOLO_SLASH_SHIPS`'s own tests), the combined row substitutes and an
absent row still falls back to geometry untouched. `staged.check` TOTAL
245 (unchanged). Fast tier (`pytest tools/omr/tests -m "not slow"`) run
once, same session.

### Open

- The GATHER wiring's `exclude_boxes` is scoped to the SUBJECT'S OWN
  CELL (its stacked chord-mates), not the whole page the benchmark
  scorer and `score_truth_set_rungs.py` use — GATHER has no cheap
  page-wide notehead index. Declared in `gather_farhead_combined_
  position`'s own docstring; not yet measured whether it changes any
  real answer (a far head's own chord-mates are almost always in the
  same cell already).
- Not re-measured on a real re-gather (CLAUDE.md §6a: "two re-gathers" —
  a GATHER change needs a FULL re-gather to price, and this is an
  additive-only GATHER row with `FARHEAD_COMBINED_SHIPS=False`, so no
  existing verdict moves; left for whoever next re-gathers either
  movement to confirm `Q.FARHEAD_COMBINED_POSITION` populates as
  expected).
- `FARHEAD_EVEN_UNEVEN_THRESHOLD`'s midpoint-of-two-medians derivation is
  the weakest measured thing here — a larger truth set (more far heads,
  or a third publisher) is the next lever if this mechanism is revisited.

## lane-ledger-r8 (2026-10-01): causes C and D of the four-causes sheet

DECISIONS 2026-10-01's "four causes behind the 8 far heads neither
reader gets right" names cause D (tiles 6-8, Sean: a head "slightly low
but should read as underneath that ledger line") — the OLD
`derive_far_head_step` guessed "on the next ledger, hidden under the
head" from the raw gap SIZE alone — and cause C (tiles 4-5) — accidental
ink beside a head on a ledger read as two rungs at the head's own
edges, the real middle line missed. This lane went through THREE
designs in one session, each measured on real data before moving on;
the first two are kept here as what they measured and why they were
replaced, not as dead ends to repeat.

### Design 1 (first pass): both-sides evidence, box-centre row, gates only the positive-gap branch

Built `head_middle_rung_evidence` requiring a thin, flat band with
stubs on BOTH sides of the head's own box, probed at its geometric
MIDDLE row, past the box edges by `THROUGH_RUNG_STUB_PROBE_SPACES`.
Gated only the "beyond the last rung" branch; the "passes through"
branch (`gap <= -TOUCH_TOL_SPACES`) was untouched. 11 RED-first tests,
real data: Litolff rungs 32/10/2 (geometry 30/14/0), one pair of heads
moved (`glyph/3/0/7/4/2` unread->right, `glyph/3/0/7/4/3` right->wrong),
net zero on the combined tally. **Coordinator review**: 5 of Sean's 8
named heads take the untouched "passes through" branch and never reach
this check at all — exactly the false-through pattern the four causes
describe. Superseded.

### Design 2 (coordinator's governance fix): both-sides evidence NOW governs "passes through" too

`derive_far_head_step` rewritten as a loop: a candidate at or past the
head's near edge is never accepted as through on distance alone — it
must be evidenced at the head's own geometric middle, same both-sides
test as design 1; unevidenced, it is dropped (the head's own outline,
not a ledger) and the rung before it is tested the same way. **Measured
catastrophic regression**: Litolff rungs collapsed to 8/19/17 (from
32/10/2) with EITHER evidence wired or not — traced directly on
`glyph/3/0/0/2/3`, a print-CONFIRMED real through rung (DECISIONS
2026-09-30/10-01): at its own candidate row the left stub has no ink at
all and the right stub measures 11px thick against a 5.5px cap — the
box-centre probe row (417) sits ~3-5px from the real candidate rows
(412, 431.5) that the walk actually found, and "both sides, thin and
flat, past the edges" is the SAME mechanism `has_through_head_rung`'s
own `img_gray` re-check uses, independently measured net negative and
held back in round 6/7 (FINDINGS "lane-ledger-rungs round 6/7") — for
exactly this reason. Reusing it here inherited the same failure mode.
Superseded before being measured as a finished design.

### Design 3: one-sided jut, candidate's own row, connectivity-first

Sean, on design 2's regression: *"there are rare cases where the ledger
line will only come out on one side not both but any line jutting out
of a notehead outside of the staff where we think a ledger line should
be is enough"* — ONE side is enough, never both. And: *"Examples with
accidentals that I saw in the crops never had any ink touching the note
head"* — CONNECTIVITY is the primary test, exclusion is the backup: the
jutting ink must be part of the SAME contiguous ink run as the column
inside the head's own box, with NO bridging of any white gap (unlike
`_band_centers`' own hollow-notehead bridge, which exists for a
different reason); `exclude_boxes` only matters for the rare case an
accidental's ink does touch.

Probed AT THE CANDIDATE'S OWN row for the through branch (never the
box centre — design 2's exact bug) and at the box's geometric middle
for the "hidden further ledger" branch. **Manager review of the
design-3 sheet, MEASURED BUG**: a head sitting in the space just below
(or above) a real ledger TOUCHES that ledger at its own top (or
bottom) edge — probing at the candidate's own row let that edge-touch
register as a connected jut, declaring the head "through" a ledger
that is really the one BEFORE (or beyond) it. Visible on tiles 3, 4, 5,
6 and the new-wrong `glyph/3/0/0/2/9` (DECISIONS 2026-10-0x). Superseded.

### Design 4 (shipped): always probe at the head's own geometric middle, with a named tolerance band

Sean's rule, restated precisely: the line must jut out of the head AT
THE HEAD'S MIDDLE ROW, never wherever a candidate happens to sit.
`head_middle_rung_evidence` drops the `probe_y` override entirely and
always probes `(y0+y1)/2`, +/- `MIDDLE_ROW_TOL_SPACES = 0.15` (staff
spaces) — a band, not a single exact row, narrow enough to stay clear
of a realistically-sized head's own top/bottom edge (~1 staff space
tall) but wide enough for the hand-drawn print's own slop.
`derive_far_head_step` computes this ONE fact ONCE (not per-candidate —
whether the real ledger is at the head's own middle does not depend on
which already-found rung is being tested) and reuses it in both the
through branch and the "hidden further ledger" branch, since both ask
the identical question. `collapse_head_edge_rungs_to_middle` (cause C)
unchanged — it already only ever asked at the box's own middle.

### RED-first tests (final design)

`tools/omr/tests/test_ledger_four_causes_cd_2026_10_01.py` (15 tests,
head boxes resized to ~1 staff space tall — `HEAD_BOX = (120, 100, 180,
200)` at `SPACING=100` — so the tolerance band cannot accidentally
overlap an edge, which a too-short synthetic box would make
meaningless): `head_middle_rung_evidence` — real through-head band
(one-sided) true; head in a space, nothing at its middle, false; **a
ledger touching ONLY the top edge -> NOT through** (design 3's own
bug, now RED-first); **a ledger at the middle row, touching one side
-> through** (Sean's own positive case); a line touching the head
-> through, the SAME line with a 2px gap -> NOT through (connectivity);
the accidental-ink control (false once excluded, true without —
sanity-checked); no image/box -> false. `collapse_head_edge_rungs_
to_middle` — 4 tests (edges collapse to the real middle; no real
middle drops to empty; real rungs away from the edges untouched; a
rung wedged between blocks the collapse). `derive_far_head_step` — top
edge, no stubs at the middle -> NOT through, abstains; the control, a
real through ledger with stubs AT THE HEAD'S OWN MIDDLE -> through.
Plus rewritten tests in `test_ledger_rungs_conversion_round2_
2026_10_01.py` and `test_ledger_rungs_round3_2026_10_01.py` (the real
`glyph/3/0/0/2/3` and evenly-spaced shapes, boxes resized to ~1 staff
space tall where the through branch is exercised), each now supplying
a synthetic image AT THE HEAD'S OWN MIDDLE, never a candidate's row.
Full `-k ledger` suite: 330 passed (was 314 at session start), 2
xfailed unchanged. Fast tier (`pytest tools/omr/tests -m "not slow"`)
run once this session (against design 3; no fast-tier test touches
`derive_far_head_step`/`head_middle_rung_evidence` outside the `-k
ledger` selection, so this is still representative): 4344 passed, 3
skipped, 2 xfailed, 0 failed.

### Re-scored, real data (truth-set record `truthset-2.44c-20260930`, design 4)

| doc | geometry | rungs, no evidence wired (unflagged default) | rungs, C+D fully wired |
|---|---|---|---|
| beethoven5-litolff (n=44) | 30/14/0 | 8/19/17 | 25/14/5 |
| brahms1-breitkopf (n=11) | 11/0/0 | 6/3/2 | 11/0/0 |

(format: right/wrong/abstain). The UNFLAGGED column is, by
construction, crippled — with no image ever supplied, the through
branch can never be evidenced and every such candidate is dropped
(CLAUDE.md rule 8). The fully-wired column: Brahms now matches
geometry EXACTLY (11/11, up from design 3's 10/11) — design 4 fixed the
one false positive design 3 had there
(`glyph/1/1/8/7/4`, a candidate 2.79 staff spaces from the head that
design 3's candidate-row probe wrongly confirmed "through"; probing at
the head's own middle instead correctly finds no evidence there).
Litolff drops slightly from design 3's 27/44 to 25/44 — `wrong` now
matches geometry's own count (14) and `abstain` rose from 2 to 5: the
heads design 3 confirmed via its edge-touching bug now correctly
abstain instead of confidently landing on a wrong answer. **One
regression remains, not crop-verified**: `glyph/3/0/0/2/9` (Litolff,
right -> wrong, `gap -0.18 sp`, a jut on the head's own geometric
middle — on a MERGING plate this could be the chord's own shared ink,
not a ledger). Flagged, not explained away; CLAUDE.md rule 7 applies
before anyone ships this.

### The 8 named heads: why they differ from a fresh run today, exactly

**The record has NOT moved** — scored throughout via the same symlinked
`library/_shared-records/truthset-2.44c-20260930/` files the brief
named from the start. **The tree this lane branched from is the EXACT
commit that drew the sheet** (`28d367a7`, the tip of
`origin/lane-farhead-combined` — confirmed by `git log` on that path;
no other lane landed on top of it). The difference is entirely THIS
LANE'S OWN session: running `neither_right_sheet.py` completely
UNMODIFIED, right now, with the unflagged default call (exactly how it
has always been called) finds **12 tiles, not 8** — a direct,
foreseeable side effect of retiring the through-decision's distance
guess at the `derive_far_head_step` primitive (the coordinator's own
instruction): the unflagged path never supplies an image, so it can no
longer confirm ANY through rung, and 4 previously-"wrong"-through heads
now abstain instead. The fair, apples-to-apples comparison is the
FULLY-EVIDENCED call (`four_causes_cd=True`): **7 of the original 8
still qualify**; only tile 7 (`glyph/3/0/9/2/0`) reads right — and it
already did, in the unmodified code, before this lane touched anything
(absent from the fresh 12-tile run too) — so that one head's resolution
is not this lane's fix, just a pre-existing fact about the record this
session never changed. **None of the 7 remaining heads flip right.**
Per-tile branch (`out/print/ledgers/neither_right_r8.png`,
`neither_right_sheet_r8.py`, prints each tile's exact `derive_far_head_
step` reason, design 4): `glyph/1/0/10/7/1`, `glyph/3/0/0/6/2` take the
"beyond the last rung" branch, EVIDENCED (a jut at the head's own
middle, on at least one side) -> "line", one ledger step too far out;
`glyph/3/0/0/2/1`, `glyph/3/0/0/7/1`, `glyph/3/0/0/7/2` take the
"through" branch — each CONFIRMED by a jut AT THE HEAD'S OWN MIDDLE
now (not a candidate's row, design 3's own bug), but still wrong
against the reference. For all 5, this is NOT a through/space
arithmetic bug any more — the rung count or position itself is wrong
upstream (cause A/B territory, another lane's scope); `glyph/3/0/8/9/0`
and `glyph/3/0/9/3/5` abstain (no rung survives before the head at
all, or zero rungs found) — neither guesses.

### Not shipped

`collapse_edges_box` (cause C) and the evidence kwargs (cause D) on
`derive_far_head_step`/`head_middle_rung_evidence` are opt-in
parameters; `four_causes_cd` defaults `False` everywhere it was added,
and nothing in `tools/omr/staged/gather.py`'s own (unflagged) call to
`derive_far_head_step` was touched. The one remaining measured
regression (`glyph/3/0/0/2/9`) and the still-open 3 "through but
wrong" heads above need a human crop check before anyone decides to
wire this further.

## lane-ledger-r8-main (2026-10-04) -- round 8 on current main, plus an explicit head-centre input

Path: STAGED/GATHER+ADJUDICATE scoring harness over the legacy-shared
rung reader (`tools/omr/annotate/ledger_grid.py`). Nothing switched on,
nothing merged to main.

**Rebase.** `lane-ledger-r8` (ded3d6ff) merged into `origin/main`
(cac6e278) as `lane-ledger-r8-main`. Its base (46c982db) was 27 commits
behind. The only textual conflicts were six generated files under
`benchmarks/acceptance/quick/out/`; per the brief ROADMAP.md,
docs/DECISIONS.md and everything under `benchmarks/acceptance/quick/`
take main's version. The merge also carries the lane-2.48 local-staff
work that r8 was built on (`measure_extractor.py`, `staged/gather.py`,
`record.py`, `capture.py`, `consequences.py`) -- none of it is on main.

**CONTROL (same script, same records, same flags).**
`score_four_causes_cd.py` against
`library/_shared-records/truthset-2.44c-20260930/` (symlinked into the
path the script reads; `.gitignore`d): Litolff geometry 30/14/0,
rungs_after **25 right / 14 wrong / 5 undecided** of 44; Brahms
**11/0/0** of 11. Reproduced exactly, before and after the parameter
below (output byte-identical). The script applies Sean's first-space
rule: `far_head_needs_ledger_read` keeps a first-space head out of the
far-head population (scored as on-staff geometry), and
`glyph/1/0/10/14/1` is excluded (Sean: its reference is wrong, it is
-2). Known: one regression `glyph/3/0/0/2/9` (right before, not right
after), as in round 8.

**New: `head_center_y`** (optional, page px, same frame as the box) on
`head_middle_rung_evidence`, `collapse_head_edge_rungs_to_middle`,
`derive_far_head_step`, `measure_ledger_rungs`. `None` = the box-middle
probe, bit-identical. Where the collapse puts back a rung it puts it at
the supplied centre. Only the probed ROW changes; the probed column
(box x-middle) is unchanged. Test:
`tests/test_ledger_head_center_input_2026_10_04.py` (a head whose box
covers only its top half, ledger through the true middle: default says
not-through, supplied centre says through). Run RED first on the
unmodified reader (5 of 6 failed, the control that must read
"not-through" passed), GREEN after.

**DIAGNOSTIC ONLY -- not a result, not a headline.** The 5 Litolff
heads still undecided; each head's centre traced from its own ink
(`r8main_centre_diagnostic.py`: the dark run, >50% of a narrow centre
column band, containing the box middle). Only ONE flips:

- `glyph/3/0/7/2/4` (truth 10): traced centre 1568.5 vs box middle
  1570.1; probe False -> True; reader None -> 10 (right). MARGINAL: the
  ledger stubs sit at rows 1564-1567 (left stub 1564-1566, right stub
  1566-1567), so the supplied centre's +-0.15sp band (1566..1571) reaches
  the ledger by about one row. The head sits 0.19 sp below the ledger's
  own row.
- `glyph/3/0/7/0/7` (truth -3): traced centre 1464.5 vs box middle
  1467.5; probe stays False, reader stays undecided. The head sits in
  the SPACE above the first ledger; the one rung found (1472.5, ink
  stub at x1+3 rows 1471-1474) touches the head's BOTTOM edge from
  below and the reader drops it as "the head's own outline". That is
  not a centre problem -- a ledger touching the head's far edge from the
  staff side is what a head in the space above it looks like.
- `8/6/10`, `8/9/0`: traced centres within +0.3 / +1.1 px of the box
  middle, probe unchanged, undecided unchanged. `9/3/5`: no rung at all;
  the trace merged with the staff's bottom line (run 1.3 sp too tall to
  trust) and is discarded.

So the "2 undecided heads that flip with a traced centre" in the brief
does not reproduce: one flips, marginally; the second is a different
fault. Crops (x3; red = box, green = supplied centre row, orange = rung
from ink; row positions verified against the page's own ink columns):
`out/print/ledgers/r8main/`.

## lane-ledger-edge-census (2026-10-04) -- how many round-8 misses are "a ledger touching the head's top/bottom edge, dropped"?

MEASURE ONLY. `tools/` is untouched (`git diff origin/lane-ledger-r8-main -- tools` is empty): the reader is read
by run-time wrappers in `edge_census.py` (`ledger_grid._rung_row_clears_box`, `collapse_head_edge_rungs_to_middle`,
`measure_ledger_rungs`, and a replay of `derive_far_head_step`'s loop). Output: `out/edge_census.txt`; sheet:
`out/print/ledgers/edge_census/edge_census_sheet.png` (+ `.pixel_check.txt`). Path: STAGED far-head rung reader on
the truth-set records, GATHER+ADJUDICATE only, staff position vs reference.

Controls (can fail): wrappers off 25/14/5 and 11/0/0 (= `score_four_causes_cd.py`); wrappers on + recording the
same; the replayed derive equals the real one on 55/55 heads. Blanket undos that DO break heads are in the output
(`excl` +3/-4 Litolff, -1 Brahms; `clears_edge` -1), so the instrument can fail.

Edge-band drop = a dropped candidate within 0.5 sp of the box edge nearest or farthest from the staff and more than
0.30 sp from the box middle (nearer the middle it is a THROUGH candidate). Band and 0.30 were set after seeing the
data -- 19 + 36 heads, treat as descriptive. "Undo" = that one drop reversed, the reader's own rules do the rest.

The 19 non-right Litolff heads (undo = the edge-drop undone; `-` = no edge drop):

| head | class | round 8 | undo | ref | cause / dropping rule |
|---|---|---|---|---|---|
| 3/0/7/0/7 | E | none | -3 | -3 | edge-of-head pop: the only ledger touches the head's bottom edge |
| 3/0/8/9/0 | E | none | 11 | 11 | edge-of-head pop: the only ledger touches the head's top edge |
| 3/0/9/3/5 | E | none | 11 | 11 | other-head masking removed the ledger at the head's top edge (two other bare rows are the head's own rows) |
| 3/0/0/2/1 | E | -4 | -6 | -6 | other-head masking removed the ledger under it (it runs through the chord's lower head) |
| 3/0/0/6/2 | E | -6 | -4 | -4 | masking removed a rung at the head's top edge; the fix works only via edge-collapse |
| 3/0/0/2/9 | E? | -6 | -4 | -5 | masking differs (398 vs 415); real fault is a false jut at the box middle |
| 1/0/10/7/1 | other | -4 | - | -2 | through-ledger 0.19 sp from the box's near edge (box rides high): counted as the ledger before, then a jut -> one too far |
| 3/0/0/2/4 | other | -4 | - | -7 | missed middle ledger (2.15 sp gap) |
| 3/0/0/7/1 | other | -10 | - | -8 | one thick ledger counted twice (5 rungs for 4; dedupe is off) |
| 3/0/0/7/2 | other | -6 | - | -2 | rungs BEYOND the head counted: derive's through-branch takes the last rung however far out |
| 3/0/7/2/4 | other | none | - | 10 | through-line not evidenced at the box-middle row |
| 3/0/7/3/1, /3/2 | other | -5 | - | -6 | same |
| 3/0/7/6/1, /7/0 | other | 11 | - | 12 | same |
| 3/0/8/6/10 | other | none | - | 10 | same |
| 3/0/7/3/4 | other | -5 | - | -6 | through-ledger masked AND not evidenced |
| 3/0/7/4/3 | other | -3 | - | -4 | through-ledger dropped by clears-box/masking AND not evidenced |
| 3/1/0/6/0 | other | -3 | - | -6 | first ledger dropped by clears-box AND through-line not evidenced |

Counts: **E 5, E? 1, other 13** of 19. Dropped "as the head's own outline" by `derive_far_head_step` (the case
Sean named): **2 of 19** (3/0/7/0/7, 3/0/8/9/0), both abstains. The rest of E is other-head masking, not outline.
Blanket fixes over all 55 heads: undo near-band outline pops -> Litolff 27/14/3 (+2, 0 broken), Brahms 11/0/0;
that plus re-adding masked near-band rungs ("near_fix") -> Litolff 29/13/2 (+4, 0 broken), Brahms 11/0/0.
Undoing every edge drop (clears/collapse/pops, near AND far) -> 26/15/3: it breaks 1/0/3/7/3 (a far-edge rung
correctly dropped). Right heads with an edge-band drop: 2 of 36 (1/0/3/7/3, Brahms 1/1/8/7/4) and BOTH are broken
by undoing it; two more (3/0/0/2/3, 3/0/0/5/12) break under masking undo just outside the band (0.63/0.82 sp).
So: the near edge is a real ledger to count, the FAR edge rung must stay dropped.

Bigger bucket, outside the question: 6 of the 13 "other" (3/0/7/2/4, 7/3/1, 7/3/2, 7/6/1, 7/7/0, 8/6/10) are a
through-ledger the middle-row jut test misses; counting a popped rung within 0.30 sp of the box middle as through
("pop_mid_through") gives Litolff 31/10/3 (+6, 0 broken), Brahms 11/0/0. Same caveat: tuned on the set it is
scored on, and the reference pairing is the only judge.

Pixel check (stub zones 0.1..1.1 sp beside the box, line vs same zones 0.5 sp off; `.pixel_check.txt`): the staff
outer line reads 1.00 in all 10 tiles (off-line 0.00-0.53); drawn rungs on-line/off-line e.g. 3/0/0/2/1 0.56/0.00,
0.69/0.16, 0.56/0.06; 3/0/0/6/2 0.62/0.16, 1.00/0.44, 0.88/0.28; Brahms 6215 1.00/0.00, 6182 1.00/0.30. Weak or
failing lines: 3/0/8/9/0 pop 0.19/0.09 (short ledger, mostly inside the head's width), 3/0/7/0/7 0.69/0.56, and the
head-outline rows of 3/0/9/3/5 (0.00, 0.62/0.66) and 1/0/3/7/3's clears-box row (0.25/0.53) -- those are rows the
reader rightly rejects.

## lane-ledger-edge-fix 2026-10-04 -- a ledger against a far head's NEAR edge is counted (Sean: "Start the fix")

Branch `lane-ledger-edge-fix` off `origin/lane-ledger-r8-main` (3f0b8605) with the census scripts. STAGED is not
touched; this is `tools/omr/annotate/ledger_grid.py` (the round-8 reader the benchmarks score), both parts behind
keyword arguments that default to today's behaviour. Nothing is on in production; nothing is merged to main.

**Control (before any edit):** `score_four_causes_cd.py` -> Litolff 25/14/5, Brahms 11/0/0.
**Default is bit-identical:** `default_identity_check.py base_ledger_grid.py` swaps the branch base's file in and
compares `(position, reason)` on all 55 heads: 0 differ.

**The rule, as stated (convention first, constants derived):** a head is ON a ledger only if a thin flat line juts
out of it at its middle row, touching; otherwise it is in the SPACE beyond the last ledger, and no ledger between
the staff and the head is ever skipped; ink separated from the head by a white gap is never the head's stub; an
accidental never touches the head but may merge into the ledger.
* Part 1 (`derive_far_head_step(near_edge_ledgers=True)`): a rung `derive` would pop ("not evidenced at the middle
  row, so the head's outline") is instead COUNTED, head in the space beyond it (offset 2n+1), when
  `near_edge_ledger_evidence` holds: (a) a thin flat CONNECTED jut (`thin_flat_jut_evidence`): the ink at the rung's
  row, no bridging, joins the box at its middle column and runs past the box by >= `RUNG_STUB_MIN_SPACES`; over the
  outermost stub length of that jut the vertical run is <= `LEDGER_THICKNESS_MAX_SPACES` and flat within half that;
  a side that fails (accidental, stem) does not count, one good side is enough; other heads' and accidentals' ink
  blanked first; AND (b) the head's body hangs on the FAR side only (`head_body_ink_either_side`): over a band as
  tall as the thin cap, in the box shrunk by the stub length, the far side is >= 50% ink and the staff side holds
  <= half of the far side's. (b) is what separates "touching the near edge" from "through the head": a head ON the
  line has body on both sides. A far-edge rung has no body beyond it and is never counted, so it stays dropped.
  Why not "off the box middle by X": 3/0/7/2/4's through ledger is 0.26 sp from its box middle, 3/0/7/0/7's edge
  ledger 0.31 sp -- a 0.8 px difference on a box that is 1.45 sp tall; the census's 0.30 cutoff was exactly that
  fit. An off-middle-by-derived-constant rule (0.15 + half thickness) was tried first and turned 7/2/4 from abstain
  to WRONG (11, ref 10); the body-side test reads the head's own ink and does not.
* Part 2 (`measure_ledger_rungs(restore_masked_staff_side_rungs=True)`, needs `exclude_boxes` and the subject's full
  box): a rung the bare ink offers and the other-head mask lost is restored only if it lies BETWEEN the staff and
  this head (not past the head's near edge by `TOUCH_TOL_SPACES`, derive's own "between" class) AND the head that
  masked it is itself printed on it (the same thin-flat-jut test run on THAT head's box, every other box blanked).
  Convention: the mask exists so a neighbour's ink cannot SUPPLY a stub; it must not delete a ledger the neighbour
  sits on, which a farther head must still count. Separates the census's pair: 3/0/0/2/1's lost 412 is between it
  and the staff, masked by 2/3 which sits on it (restored, right); 3/0/0/2/3's lost 395 lies beyond its far edge
  (not restored), and 3/0/0/5/12 likewise -- neither breaks.

**Arms (`score_edge_fix.py`, four_causes_cd=True; Litolff n=44, Brahms n=11):**

| arm | Litolff right/wrong/abstain | Brahms |
|---|---|---|
| default (= control) | 25 / 14 / 5 | 11 / 0 / 0 |
| Part 1 | 27 / 14 / 3 | 11 / 0 / 0 |
| Part 1 + 2 | 29 / 13 / 2 | 11 / 0 / 0 |

Every changed head (nothing else moves; **0 right heads broken** in either arm):
Part 1: 3/0/7/0/7 abstain -> -3 right (ref -3); 3/0/8/9/0 abstain -> 11 right (ref 11).
Part 2 adds: 3/0/0/2/1 -4 wrong -> -6 right; 3/0/9/3/5 abstain -> 11 right (ref 11); 3/1/0/6/0 -3 wrong -> -5 wrong
(ref -6; a real ledger between it and the staff is now counted, the head still carries a second fault: first
ledger dropped by clears-box, through-line not evidenced).
These equal the census's blanket undos (27/14/3 and 29/13/2) -- but by a rule that does not read the answer.

**Honest limits.** (1) The constants are the module's own (stub length 0.15 sp, thin cap 0.35 sp, flat = half the
cap) plus two new plain ones (body band = the thin cap; one-sided = a majority, 0.5); nothing was searched, but
"outermost stub length" (not half the jut) and "body-side, not middle-offset" were chosen after seeing why the
first versions failed on 3/0/7/2/4, 3/0/7/0/7 and 3/0/0/2/1, so the 55 heads are not an out-of-sample test. The
margin on the decisive numbers: far/staff ink 1.00/0.35 (0/7, accepted) vs 0.99/0.79 (7/2/4, refused); 8/9/0
0.89/0.04. (2) 3/0/7/0/7's staff-side ink 0.35 is the closest call. (3) Both fixes are only reached where
`four_causes_cd` is on; the staged path does not call this reader. (4) The other non-right heads (through-line not
evidenced, thick ledger counted twice, rungs beyond the head) are untouched.

Tests: `tools/omr/tests/test_ledger_edge_fix_2026_10_04.py` (12): near-edge ledger counted; far-edge rung still
dropped; a tall accidental-shaped blob is not a ledger; an accidental merged into the ledger does not veto it; a
white gap means not the head's; a head with body on both sides is not an edge case; masked staff-side ledger
restored / beyond-head ledger not restored / own-width row not restored; defaults off. Written RED first: against
the base file the module does not even import the new names (ImportError); in the green run each positive case has
its default-state control assertion in the same test (e.g. `default["offset"] is None`).

Sheet: `out/print/ledgers/edge_fix/edge_fix_sheet.png` (5 changed heads x before/after/reference, x3, real print at
600 dpi; red box, orange counted, magenta dashed still dropped with the rule, green margin ticks = nominal
reference rows) with `.pixel_check.txt`: ink fraction in the 0.6 sp just outside each side of the box, ON the line
vs the same zones 0.5 sp off it. Every orange line reads on > off (3/0/0/2/1: 1.00 vs 0.00/0.22/0.39; 0/7
0.70/0.35; 8/9/0 0.50/0.15; 3/5 1880.5 0.60/0.11; 6/0 2284 0.22/0.00, 2301 0.33/0.00). Magenta lines that are
weak: 3/5 1893.5 (0.10/0.00) and 1919.5 (0.40/0.60, a stem/flag beside it) -- rungs the reader still, rightly,
does not count.

## lane-ledger-far-side-rule (2026-10-04): a thin line at a head's FAR side, nothing farther out => ON it (Sean)

Base `origin/lane-ledger-edge-fix` (845ab8cc). Code: `ledger_grid.far_side_ledger_evidence` (+ `far_side_jut_evidence`,
`far_side_partner`), reached only through `derive_far_head_step(far_side_ledger=True, far_side_partner_boxes=...)`; default
off is bit-identical (test). Scorer `score_far_side.py`; sheet `out/print/ledgers/far_side_rule/far_side_sheet.png`.
Reference exclusions: `glyph/1/0/10/14/1` as before and, new, `glyph/3/0/0/6/2` (Sean: ON its arrowed line, -6; the reference -4 is wrong).

**Rule** (constants derived from spacing/ledger thickness, none per-score): only where the middle-row through test finds no line,
the bare ink walk's outermost rung that is (i) in the head's far half (> `MIDDLE_ROW_TOL_SPACES` beyond the middle) and not more
than one ledger thickness (0.35 sp) past the far edge, (ii) on the ladder (whole spaces from the staff edge +-0.35 sp), (iii) backed
by thin flat ink CONNECTED to the head (run anchored a stub inside each box edge, out past it >= 0.15 sp, thickness <= 0.35 sp,
flat in thickness and with centre drift <= max(1 px, cap/4)); and (iv) NO partner: no other detector notehead within one head
width in x (1.3 sp) and 0.5..3.5 sp (a stem) farther out. Duplicate boxes on the same head (IoU >= 0.5) are not masked as
"other heads" (3/0/7/3/4 has one). Then offset = 2n, a line. Sensitivity: head width 1.0-2.2 sp x stem 2.5-8 sp gives the identical 3 changes.

**Control**: default Litolff 25/14/5, Brahms 11/0/0; fix 1 29/13/2, 11/0/0 (n=44). Excluding 3/0/0/6/2 (n=43): default 25/13/5, fix 1 29/12/2.
**Arms** (right/wrong/abstain): fix 1 + far-side rule Litolff 32/10/2 (n=44), 32/9/2 (n=43); Brahms 11/0/0.
Per-head changes vs fix 1 (all three, nothing else): `3/0/7/3/1`, `3/0/7/3/2`, `3/0/7/3/4`: -5 wrong -> -6 right (ref -6): thin flat tip on ledger 3, no partner.
Right heads broken: none. The (c) heads (`0/0/2/3`, `0/5/12`, `0/2/9`, `0/6/2`) stay put (partner). `3/0/0/7/2` (rung 1.49, jut not thin/flat) unchanged.
Reach: 3 of 55 far heads. Caveat as the lane said: on these heads the line is a 0.23 sp pointed tip; the slur-arc refusal rests on the centre-drift
test, which has little power for a jut that short.
Pixel check (ink on row vs 0.5 sp off, +-1 px; stub zone): L3 3/0/7/3/1 0.88/0.56, 3/0/7/3/2 0.75/0.44, 3/0/7/3/4 0.88/0.69; L1/L2 on > off in every tile; frame control 1.00/0.07-0.11.
Tests `test_ledger_far_side_rule_2026_10_04.py` 7: RED against the base module (ImportError), GREEN now; the arc test also failed (6 != 5) before the drift check was added.

## lane-farhead-combined-1004 (2026-10-04): today's far-head pieces COMBINED (STAGED reader; all default-OFF keywords; nothing switched on, nothing merged to main)

Branch `lane-farhead-combined-1004` off main `21cd341b`. Brought in from
`origin/lane-ledger-exclusion` (2e4aa867, on `lane-ledger-accidental`):
`ledger_grid.py` (a verified superset of main's -- main's four removed lines
are the `has_left/has_right` pair, now the `else` of the `connected` rule), its
tests and scripts; from `origin/lane-standard-box-hollow` (c80f7c4f, on
`lane-standard-head-box`): `standard_head_box.py`, `head_template.py`,
`ledger_shape_trace.py`, tests, scripts (that branch does not touch
`ledger_grid.py`). Those branches' own FINDINGS sections stay on them.

**Controls (each piece's own number reproduces on the combined tree):** main
M0 32/10/2, Brahms 11/0/0; exclusion best arm conn+same+one+drop 36/6/2, 11/0/0;
S0/S2/S2H alone 32/10/2 -> 35/8/1 -> 36/7/1, Brahms 11/0/0 throughout; S2H
no-pocket invariance: 48 heads identical. Tests: 333 passed, 2 xfailed over
every ledger / standard-box test file; `staged.check` TOTAL 250.

**Combined, cumulative arms** (`score_combined_1004.py`; Litolff n=44 as scored
/ "vs Sean" with `3/0/0/6/2` = -6; Brahms n=11; `glyph/1/0/10/14/1` excluded):

| arm | Litolff as scored | Litolff vs Sean | Brahms |
|---|---|---|---|
| M0 main (near_edge + restore + far_side) | 32/10/2 | 33/9/2 | 11/0/0 |
| E1 + exclusion (conn+same+one+drop) | 36/6/2 | 37/5/2 | 11/0/0 |
| E2 + standard box where its gate passes (S2) | 39/4/1 | 40/3/1 | 11/0/0 |
| E3 + counter filled (S2H) | **40/3/1** | **41/2/1** | 11/0/0 |

Per-head changes:
- E1 vs M0: `3/0/0/7/1` -10 -> -8, `3/0/0/7/2` -6 -> -2, `3/0/7/4/3` -3 -> -4,
  `3/0/7/7/0` 11 -> 12, all wrong -> right (the through-ledger is kept by the
  connected / same-ink / one-sided rules; rungs beyond the head are not
  counted); `3/0/0/2/4` -4 -> -6 wrong -> wrong (ref -7).
- E2 vs E1: `3/0/7/2/4` abstain -> 10 right, `3/0/7/6/1` 11 -> 12 right,
  `3/1/0/6/0` -5 -> -6 right (the standard box is centred on the head, so the
  head's own middle row is where the through-ledger is looked for). The box
  also moves on 16 more Litolff and all 11 Brahms heads with the read unchanged.
- E3 vs E2: `1/0/10/7/1` (hollow half note, tile 1 of Sean's earlier sheet)
  -4 -> -2 right (the filled counter lets the template fit pass the gate:
  IoU 0.47 -> 0.79).
- Right heads broken at any step: none (E3 vs M0: none).

Remaining after E3 (reader's own reason): `3/0/0/2/4` we -6 / ref -7 wrong
(through-ledger confirmed by a jut at the head's middle row; detector box kept
-- the standard box fails its gate, IoU 0.35, offset 0.42 sp); `3/0/0/2/9` we -6
/ ref -5 wrong (-0.18 sp beyond the last clean rung, a jut connected to the
head's middle; gate fails, 0.39 / 0.50); `3/0/8/6/10` abstain / ref 10 (every
found rung was the head's own outline -- no_rung_before_the_head; standard box
used, gate 0.81 / 0.01). `3/0/0/6/2` reads -6, wrong only against the file's
reference -4 (Sean: -6). Brahms: none.

Sheet for Sean: `out/print/ledgers/combined_1004/combined_1004_sheet.png`
(4 tiles, x6, 600 dpi) + `combined_1004_key.json` (every pixel number).
Pixel check: 7 of 10 drawn lines pass ink-vs-off. The 3 that read
`on_ink False`: tile 1's third ledger (y395) and tile 2's dashed line (y397.5)
have ink on the row (near_on 1.0) but the control rows 0.5 sp off read 0.88 /
0.75 because the head and a neighbour sit there, so the test cannot
discriminate; tile 3's dashed line (y1725) is the head's own outline inside its
box (near_on 0.38) -- drawn labelled as such. Frame control on/off 0.97-1.0 vs
0.03-0.14 on all four. Cyan boxes vs the head's own blob: tile 3 (standard box)
blob_in_box 0.95; tiles 1, 2, 4 (detector box, standard box not trusted)
0.54 / 0.50 / 0.43 -- the boxes there are poor, which is the remaining work.
This is the reading we have, not an endorsement; nothing was tuned.


<!-- brought onto main 2026-10-04 from origin/lane-ledger-template-fix (the 10-02 shape-trace and template rounds) -->
## lane-ledger-shape (2026-10-02): shape trace vs the box-centre probe

**Brief**: Sean's view of `out/print/ledgers/r8_*.jpg` ("all 14 that are
wrong have a ledger line going through them that is visible"; the 2
undecided, `glyph/3/0/7/0/7` and `glyph/3/0/7/2/4`, "look like
everything it is declaring is right") plus DECISIONS 2026-10-02 ("trace
the shape around far heads", "an accidental can merge into a ledger").

**Why the 2 don't commit, found before anything was built**: both abstain
via `derive_far_head_step`'s final branch, `no_rung_before_the_head` —
every candidate rung the plain walk finds gets dropped by
`head_middle_rung_evidence` because it probes for a jut at the detector
BOX's naive `(y0+y1)/2`, never the printed oval's own centre. Confirmed
by direct call (`score_truth_set_rungs.reader_absolute_position` on both
subjects, `four_causes_cd=True`): `after_pos=None`, same reason, while
`ledger_measured_position` (interpolating the measured ledger ladder) and
plain geometry both already land on the reference position for both
heads. This is exactly the mechanism the task brief hypothesised.

**Built**: `tools/omr/annotate/ledger_shape_trace.py` — traces the
connected ink around a head row by row (excluding a detected stem
column), fits the oval's own centre/extent from the trace (median width
of non-inflated rows, width-weighted centroid, walking outward through —
not stopping at — a thin crossing ledger, stopping only at a genuine
blank row), finds ledger bands as thin/straight protrusions past the
fitted oval, and trims a fused accidental off a band's far end by column
tallness (a column whose own vertical run is much taller than a ledger
band is excluded from the band's own measured extent, but ONLY outside
the oval's own footprint — inside it, tallness is the oval itself and is
expected). `shape_trace_middle_rung_evidence` is a drop-in replacement for
`ledger_grid.head_middle_rung_evidence` with the same signature and the
same "no evidence possible -> False" contract.

**RED -> GREEN** (`tools/omr/tests/test_ledger_shape_trace_2026_10_02.py`,
9 synthetic cases, fully hand-built images, no page/weights/library):
every scenario in the task brief failed first against the initial
implementation (oval half-width was inflated by the crossing line's own
width, dragging the centre and blocking the "line touching only the
top"/open-half-note/accidental/off-centre-box cases) and now passes:
line-through-both-sides -> on; one-sided jut -> on; line touching only
the oval's top -> space beyond, not on; open half-note oval + line
through -> on, centre from the outline; accidental fused onto a ledger's
end -> still on, band's own measured extent stops short of the
accidental; a box covering only the top half of the head -> still
centres from the trace and reads on; no image -> abstains, never guesses;
a stem does not inflate the oval or register as a band.

**Real-data re-score, substituting the evidence function only (monkeypatch,
measurement-only, `benchmarks/omr-local-staff-2026-09/score_shape_trace.py`)
— MEASURED NET NEGATIVE, HELD BACK**:

| doc | reader | right | wrong | abstain | n |
|---|---|---|---|---|---|
| beethoven5-litolff | geometry | 30 | 14 | 0 | 44 |
| beethoven5-litolff | round8 | 25 | 14 | 5 | 44 |
| beethoven5-litolff | shape_trace | 15 | 15 | 14 | 44 |
| brahms1-breitkopf | geometry | 11 | 0 | 0 | 11 |
| brahms1-breitkopf | round8 | 11 | 0 | 0 | 11 |
| brahms1-breitkopf | shape_trace | 6 | 3 | 2 | 11 |

Of the 2 target heads: `glyph/3/0/7/0/7` still abstains (same reason —
its own rungs still fail the oval-middle evidence test even with the
traced centre); `glyph/3/0/7/2/4` **FLIPS to right**, now taking the
"through" branch with a jut confirmed at the traced middle. But the
substitution costs 14 previously-right Litolff heads (mostly flipping to
`abstain` via the same `no_rung_before_the_head` reason, i.e. the traced
oval's fitted width/extent is now making the evidence probe MISS juts the
box-centre probe used to find) and 5 previously-right Brahms heads — a
clear net loss, the same "measured net negative, HELD BACK" verdict as
rounds 6/7 above. The failure mode is plausibly the synthetic tests'
own simplicity (hand-drawn ovals/lines, no neighbouring stave ink, no
scan noise) not transferring to real plate ink — rounds 6/7's own note
that a confound "can register a false reading on exactly the pairs it
was built for" applies here too.

**Not shipped, not wired into any product/default path.** The module is
additive only, reachable solely through this measurement script's own
monkeypatch; `ledger_grid.head_middle_rung_evidence` and `derive_far_
head_step`'s own call to it are untouched. A future lane's own measured
fix for the 2-head mechanism should widen the evidence probe's window
or soften the oval-width inflation guard, re-score against this SAME
truth set before shipping anything, and treat this result as the
positive control that the net-negative substitution here is not a
tooling bug (the module's own 9 synthetic cases all pass) but a real
generalisation gap.

Paths: `tools/omr/annotate/ledger_shape_trace.py`,
`tools/omr/tests/test_ledger_shape_trace_2026_10_02.py`,
`benchmarks/omr-local-staff-2026-09/score_shape_trace.py`.

### lane-ledger-shape, sheets (2026-10-02, drawing only)

`benchmarks/omr-local-staff-2026-09/shape_sheets.py` draws the traced
outline (magenta), fitted oval (yellow + centre cross), detected line
bands (orange), detector box (red), staff lines (green) and reference
tick (cyan) for every regression/flip head, writing
`out/print/ledgers/shape_regressions.jpg` (19 tiles: the 14 Litolff + 5
Brahms heads right under round 8 but not right under the shape trace)
and `out/print/ledgers/shape_flips.jpg` (`glyph/3/0/7/2/4`,
`glyph/3/0/7/0/7`). No code in `tools/` touched.

Visual read of the 19 regression tiles, bucketed by what visibly went
wrong (one cause per tile, Sean's own crop-check convention, rule 7):

  * **8 tiles** -- oval/centre mis-fit onto fused or adjacent ink (a
    stem, beam, flag, a dynamic-mark letterform, or a neighbouring
    blob entirely) so the real through-line crosses the BOX's edge,
    never the fitted middle: `glyph/1/0/10/8/1`, `glyph/1/0/3/7/3`,
    `glyph/3/0/0/2/3`, `glyph/3/0/0/5/12`, `glyph/3/0/5/4/5`,
    `glyph/3/0/7/4/2`, `glyph/1/1/0/2/4`, `glyph/1/1/8/5/0` (the last
    two: the oval visibly sits on a dash/movement-number glyph or a
    stray blob well away from the box's own ink).
  * **6 tiles** -- no ledger ink found anywhere inside the trace's own
    search window at all (the real jut sits beyond the window, or a
    neighbour's own box-exclusion blanks it): `glyph/3/0/5/7/0`,
    `glyph/3/0/7/2/3`, `glyph/3/0/7/4/0`, `glyph/3/0/8/2/5`,
    `glyph/1/1/0/4/6`, `glyph/1/1/8/4/4`.
  * **5 tiles** -- a band IS found and crosses correctly, but on a
    tightly stacked chord (two far heads a third apart) the traced-
    middle evidence picks a different rung than the box-centre probe
    did, landing one half-step off from round 8's own (correct)
    answer: `glyph/3/0/7/6/2`, `glyph/3/0/7/6/4`, `glyph/3/1/0/9/0`,
    `glyph/1/1/8/6/0`, and one more off-by-one tile in the same chord
    family.

Read from the drawings, not re-measured -- a future lane should
instrument each bucket (print the oval fit's own numbers, not just the
picture) before trusting the counts past "roughly a third window-miss,
a third fused-ink mis-fit, a quarter stacked-chord off-by-one."

Paths: `benchmarks/omr-local-staff-2026-09/shape_sheets.py`,
`out/print/ledgers/shape_regressions.jpg`,
`out/print/ledgers/shape_flips.jpg`.

### lane-ledger-shape, LOCAL trace (2026-10-02, manager review + Sean approval)

Manager read of the first cut's `shape_regressions.jpg`: the trace
followed the whole CONNECTED ink component -- staff lines the stem
touches, a neighbouring head, printed text -- not just the head's own
local shape (tiles 2/5/6: traced along full staff lines; tile 4: a tall
thin oval fit onto the stem; tile 1: oval bigger than the head, missed
the clear line through its middle).

Rewired `tools/omr/annotate/ledger_shape_trace.py` to be LOCAL, not
connected-component:

  * window sized from the STANDARD notehead box (ROADMAP 2.39,
    `tools.omr.staged.geometry.STANDARD_HEAD_WIDTH_SPACES`/
    `_HEIGHT_SPACES`): columns ±1.5 standard head-widths, rows
    ±(0.6 standard head-height + 0.5 staff space) of the head's own
    (re-centred) centre;
  * each row takes the ink run CONTAINING, or NEAREST within half a
    head-width of, the head's own column -- never the whole row, so a
    neighbour head or text is excluded by construction;
  * the stem column is masked exactly where a real `Q.STEM` box is
    given (unused in this re-score -- no record plumbing added this
    round, see "not done" below), heuristically (tall + narrow) otherwise;
  * staff-line rows (this head's own locally measured lines) are
    excluded from the oval FIT and from ledger-BAND detection alike --
    a staff line is inside the staff, a ledger never is;
  * the oval row-width cap is now 1.6 standard head-widths (was 1.35x
    the box's own width);
  * one re-centring iteration: fit once from the box's own centre,
    re-run the whole window/trace/fit from the first fit's own centre.

11 synthetic tests (9 original + 2 new: stem fused to a touched staff
line must not be followed; a neighbour chord head beside it must not be
folded in) -- all GREEN, `pytest tools/omr/tests -k ledger` (341 passed,
2 xfailed, unrelated) stays green.

**Real-data re-score** (same monkeypatch harness, `staff_lines` now
threaded through via a `functools.partial`-style wrapper over
`score.reader_absolute_position` so each head's own locally measured
staff lines reach the evidence call -- `score_shape_trace.py`):

| doc | reader | right | wrong | abstain | n |
|---|---|---|---|---|---|
| beethoven5-litolff | geometry | 30 | 14 | 0 | 44 |
| beethoven5-litolff | round8 | 25 | 14 | 5 | 44 |
| beethoven5-litolff | shape_trace (local) | 16 | 17 | 11 | 44 |
| brahms1-breitkopf | geometry | 11 | 0 | 0 | 11 |
| brahms1-breitkopf | round8 | 11 | 0 | 0 | 11 |
| brahms1-breitkopf | shape_trace (local) | 5 | 4 | 2 | 11 |

Still MEASURED NET NEGATIVE, HELD BACK -- Litolff right ticked up by one
(25->16 vs the prior cut's 15) and Brahms right ticked down by one (6->5)
within noise; the population of heads that flip is different from the
first cut's (17 Litolff + 6 Brahms flip either direction this round, up
from 14+5 one-directional regressions, because this round's sheet now
shows EVERY flip, not only regressions).

Of the two target heads: `glyph/3/0/7/2/4` still flips to RIGHT (through
branch, jut confirmed). `glyph/3/0/7/0/7` now flips to **WRONG**, not
abstain -- worse than the first cut: the traced-middle probe now
confirms a through-rung there that is NOT the reference position
(CLAUDE.md rule 8 concern -- a fallback must never convert "cannot tell"
into a confident wrong answer; this is the shape trace doing exactly
that on this one head). Flagged, not explained away.

Visual re-check of the previously named tiles confirms the structural
fix: `glyph/3/0/5/4/5` (old "oval on the stem" tile) and `glyph/3/0/5/7/0`
now fit a correctly sized/centred oval on the real notehead, bands
bracket it instead of smearing across the whole crop width. Several
tiles still show the magenta trace reaching a distant staff line at the
TOP of its own local window -- that window legitimately includes it when
the staff edge is close, and it is no longer treated as a ledger
candidate (masked by the `staff_lines` parameter) -- a visible but
harmless remnant, not a re-introduction of the connected-component bug.

**Not done this round** (flagged, not hidden): no real `Q.STEM` box is
threaded into the re-score -- the heuristic tall/narrow-column fallback
is what ran; wiring the real stem per glyph needs reading `Q.STEM` off
the record per subject, left for a future lane since this round's brief
was the drawing/trace-locality fix, not stem plumbing.

Sheets: `out/print/ledgers/shape_regressions.jpg` (23 tiles -- every
head whose verdict differs round8 -> shape_trace, EITHER direction, this
round, derived live from the score rather than hand-listed) and
`out/print/ledgers/shape_flips.jpg` (the 2 target heads), same drawing
convention as the first cut.

Paths: `tools/omr/annotate/ledger_shape_trace.py`,
`tools/omr/tests/test_ledger_shape_trace_2026_10_02.py`,
`benchmarks/omr-local-staff-2026-09/score_shape_trace.py`,
`benchmarks/omr-local-staff-2026-09/shape_sheets.py`.

## lane-ledger-template (2026-10-02): head TEMPLATE matching vs the shape trace

**Brief**: DECISIONS 2026-10-02, Sean -- "try head-template matching for
far heads" -- after the oval shape trace above was measured NET NEGATIVE
and held back (the regression tiles read as "oval mis-fit onto fused ink"
or "no ledger ink found in the trace's own window"): build templates from
CLEAN exemplars elsewhere on the SAME page/document, rather than fitting
a fresh shape to the far head's own (often fused) ink every time.

**Built**: `tools/omr/annotate/head_template.py`.

  1. `build_templates` collects clean, isolated, one-per-cell ON-STAFF
     noteheads (never a far head), classifies each `filled`/`hollow`
     (detector class, trusted only for these clean heads) and
     `on_line`/`in_space` (even/odd staff position), crops a LOCAL window
     sized from `STANDARD_HEAD_WIDTH/HEIGHT_SPACES` at the head's own
     local spacing, resamples it to a FIXED canonical grid (independent
     of any one page's own DPI), and averages into a `Template` per
     `(kind, variant)` -- plus a `raw` pool (both variants) per kind.
     Reports exemplar counts per combination; a combination under
     `MIN_TEMPLATE_EXEMPLARS` (3) is not built at all.
  2. `match_head_template` slides the `on_line`/`in_space` templates of a
     far head's own classified kind +/-1.5 staff spaces in 1-px steps
     over the real page ink (staff lines LEFT IN), scored by a
     correlation that looks ONLY at the template's own HEAD-oval pixels
     and its LINE-ROW stub pixels (ink elsewhere in the window -- a
     neighbour's stem, a slur -- never counts). The two terms are scored
     SEPARATELY (never pooled into one mask) and combined
     `0.75*head + 0.25*line`, with an explicit per-space SHIFT PENALTY --
     both needed, see "built wrong first" below. The best match reports
     the head's matched centre, the winning variant, and the MARGIN
     between the two variants' own best scores; below a stated threshold
     (`MARGIN_UNDECIDED_THRESHOLD = 0.08`) the head is UNDECIDED, never
     forced to an answer.
  3. `template_middle_rung_evidence` is a drop-in for `ledger_grid.
     head_middle_rung_evidence` with the SAME 4-positional-argument
     contract (`templates`/`stem_box`/`kind` bind per call via a closure,
     exactly like `staff_lines` did for the shape trace) -- substitutable
     into `derive_far_head_step` by the SAME local monkeypatch
     `score_shape_trace.py` already used.

**Built WRONG first, twice, both caught before any real-data score**
(CLAUDE.md rule 7 -- a control that can fail): the first cut pooled the
head-oval and line-row pixels into ONE scored mask; a FILLED notehead is
solid ink across its whole body regardless of whether a ledger crosses
it, so the "on-line" band (which sits inside a filled oval's own row
range) scored high ink-density agreement from the oval's own body alone
-- measured directly, a head with NO ledger anywhere near its own middle
still matched "on_line" at 0.70 correlation. Fixed by restricting each
line-row mask to the STUB columns PAST the oval's own half-width only
(the same stub convention `head_middle_rung_evidence` already uses),
scored separately from the head term and recombined. The SECOND cut then
let the window's own +/-1.5-space slide "cheat": a strong, correctly-
shaped but off-centre ledger could out-score a correctly-centred match by
simply relocating the whole window onto it, independent of whether the
head's own ink was still there -- fixed with the explicit shift penalty
and the 0.75/0.25 head/line weighting, which anchors the match to the
box's own prior position (RED-first: `test_head_in_a_space_with_ledger_
touching_top_reads_space` caught both bugs before any synthetic test
passed).

**RED -> GREEN** (`tools/omr/tests/test_head_template_2026_10_02.py`, 9
synthetic cases, fully hand-built images, no page/weights/library):
template-build reports counts and excludes a chord cell entirely (never
just one of the pair) and any non-isolated exemplar; a head ON a ledger
reads on-line; a head in a space with a ledger ONE STAFF SPACE from its
own centre (the real engraving distance -- an earlier version of this
test placed the ledger unrealistically close to the oval and is why the
first version of this test failed against an otherwise-correct module,
not a module bug) reads in-space; a head fused to a chord partner a THIRD
away (1.5 sp, CLAUDE.md sec10) centres on the right head, not the
neighbour 10+ px away; a HOLLOW head with an open oval end still matches
and reads on; no image/no templates never guesses (CLAUDE.md rule 8); a
deliberately ambiguous, off-centre scrap of ink reads UNDECIDED, never
forced; a stem fused to the head's own side is masked and does not break
the match. `pytest tools/omr/tests -k ledger` stays at 343 passed (341
pre-existing + the 2 of this file's own 9 whose name contains "ledger"),
2 xfailed, no regressions; the full new file alone is 9 passed.

**Real-data re-score** (`benchmarks/omr-local-staff-2026-09/
score_head_template.py`, same local-monkeypatch harness as the shape
trace; templates built per PAGE with a document-POOLED fallback per
`(kind, variant)` a page's own clean population is too sparse for --
measured directly: Litolff page 3 alone has ZERO clean filled on-line/
in-space exemplars even though the whole document has 6/9; Brahms page 1
has essentially none at all, 1 filled exemplar total):

| doc | reader | right | wrong | abstain | n |
|---|---|---|---|---|---|
| beethoven5-litolff | geometry | 30 | 14 | 0 | 44 |
| beethoven5-litolff | round8 | 25 | 14 | 5 | 44 |
| beethoven5-litolff | template (raw substitution) | 16 | 20 | 8 | 44 |
| beethoven5-litolff | template_where_round8_undecided_only | 26 | 14 | 4 | 44 |
| brahms1-breitkopf | geometry | 11 | 0 | 0 | 11 |
| brahms1-breitkopf | round8 | 11 | 0 | 0 | 11 |
| brahms1-breitkopf | template (raw substitution) | 6 | 3 | 2 | 11 |
| brahms1-breitkopf | template_where_round8_undecided_only | 11 | 0 | 0 | 11 |

The RAW substitution is MEASURED NET NEGATIVE on both documents, the same
verdict as the oval shape trace -- 12 Litolff + 5 Brahms heads that round
8 already got right flip away under the template evidence (mostly to
`abstain` via the same `no_rung_before_the_head` branch, a few to
`wrong`). The population that flips is almost entirely DIFFERENT from
the shape trace's own regression set (one overlap: `glyph/3/0/7/4/2`-
family heads), suggesting the two approaches fail on different heads for
different reasons rather than the same underlying population being
genuinely hard.

**`template_where_round8_undecided_only`** (keep round 8's own answer
everywhere it decided anything at all; consult the template ONLY on
round 8's own `abstain`s) is NOT net negative -- it can only ever match
or improve round 8, by construction, and measured ONE net improvement on
Litolff (`glyph/3/0/8/6/10`, previously `abstain`, now correctly `right`
via a confirmed through-rung) with zero cost. Brahms had zero round-8
abstains to begin with (11/0/0), so this combination changes nothing
there -- there was nothing for it to improve.

**Of the two target heads named in the brief, NEITHER flips**:
`glyph/3/0/7/0/7` -- margin 0.057, below the stated 0.08 threshold, so
UNDECIDED (reads as `False`, same as round 8's own abstain reason, no
change). `glyph/3/0/7/2/4` -- NOT undecided (margin 0.325) but the
template confidently matches **`in_space`**, disagreeing with the
established correct reading (geometry, the ledger-measured reader, and
the shape trace's own "through" branch all agree this head is ON a
ledger) -- a CONFIDENT WRONG answer on exactly the head this lane was
built to fix. Measured directly (excluding the SAME accidental/notehead
boxes `four_causes_cd` excludes): `score_on=0.166, score_space=0.490`.
This is not a stated-margin failure (rule 8 is respected -- the module
never answers below its own threshold) but a genuine template-matching
miss on this one head's own real ink; a future lane should crop-check
this specific subject against the print before trusting the matcher's
confidence anywhere near it.

**Not shipped, not wired into any product/default path.** The module is
additive only, reachable solely through `score_head_template.py`'s own
monkeypatch. `ledger_grid.head_middle_rung_evidence` and `derive_far_
head_step`'s own call to it are untouched.

Sheets: `out/print/ledgers/template_templates.jpg` (15 tiles -- every
`(kind, variant)` template built per document, page-level + the pooled
fallback, with the HEAD mask (yellow) and LINE-ROW stub mask(s) (orange)
outlined, captioned with the exemplar count) and
`out/print/ledgers/template_changed.jpg` (20 tiles -- every head whose
verdict differs round8 -> template raw substitution, EITHER direction,
derived live; the best-matching template's standard-head-size outline
drawn at its own MATCHED centre in yellow, local staff lines in green,
detector box in red, reference tick in cyan). Staff-line rows spot-
checked against the raw page (two heads, five lines each): every drawn
line sits on a row with mean brightness well below the window's white
background, confirming `frame_lines_for_head`'s local re-measurement is
reading real ink, not a stale global position.

Paths: `tools/omr/annotate/head_template.py`,
`tools/omr/tests/test_head_template_2026_10_02.py`,
`benchmarks/omr-local-staff-2026-09/score_head_template.py`,
`benchmarks/omr-local-staff-2026-09/template_sheets.py`.

### lane-ledger-template, GEOMETRY templates (2026-10-02, Sean)

**Brief**: "try the geometry version first" -- build templates from
drawn ellipse geometry instead of averaged real exemplars; "also the
oval should be at a 45% angle for the note head -- right?" -- MEASURE
first, never assume (CLAUDE.md rule 7).

**Measured tilt** (`benchmarks/omr-local-staff-2026-09/
measure_head_tilt.py` -- `cv2.fitEllipse` on each clean on-staff head's
own local ink, stem columns masked, contours with eccentricity > 2.0
excluded from the OUTER statistic as stem-contaminated, not silently
averaged in):

| doc | kind | outer tilt (median) | n | slit tilt (median) | n |
|---|---|---|---|---|---|
| Litolff | filled | 1.4 deg | 598 | -- | -- |
| Litolff | hollow | 2.3 deg | 126 | 38.3 deg | 138 |
| Brahms | filled | 4.4 deg | 541 | -- | -- |
| Brahms | hollow | 3.3 deg | 125 | 1.6 deg | 80 |

**The OUTER oval is measured flat, not 20-30 deg** -- both documents,
both notehead kinds, large samples (125-598 heads each). The manager's
guess is NOT confirmed for the outer shape; whatever visual tilt
prompted the question is more likely the STEM's own angle (masked out
here precisely because it dominates an unmasked fit -- the first pass of
this measurement, before stem-masking, swung wildly between +-90 deg on
elongated stem-fused blobs and is why that first pass is not reported).
**The HOLLOW SLIT is measured steep on Litolff (38.3 deg, close to the
guessed 40-45 deg) but NOT on Brahms (1.6 deg)** -- the two documents
disagree, so no single slit angle generalises across editions; each
document's own measured value is used for its own templates, never one
borrowed from the other.

**Built**: `head_template.build_geometry_template`/`build_geometry_templates`
(new, additive) draw a template directly at the canonical grid's own
scale: outer ellipse `GEOM_HEAD_WIDTH_SPACES=1.3` x `GEOM_HEAD_HEIGHT_
SPACES=1.0` sp (the brief's own stated numbers -- DIFFERENT from ROADMAP
2.39's `STANDARD_HEAD_WIDTH/HEIGHT_SPACES` of 1.4 x 1.1, kept as its own
separate constant, never substituted for the exemplar path's), rotated
by the MEASURED outer tilt; hollow = ring (outer ellipse minus an inner
slit ellipse at the measured slit tilt, sized as a fraction of the outer
axes); on-line/in-space variants draw a line of the page's own MEASURED
staff-line thickness (`score_head_template.measure_line_thickness_px`,
median dark-run length at each known staff-line y, several x samples per
page) through the centre or touching the window's top/bottom, extending
0.5 sp past the oval, same as the brief's own stated geometry. Matching,
masks, shift penalty, margin and decision logic are UNCHANGED from the
exemplar path -- only the template SOURCE differs; `score_head_template.
build_geometry_templates_for_doc` returns the SAME `{page: templates,
"pooled": templates}` shape `templates_for_page` already expects, so the
entire scoring harness is reused verbatim.

**Real-data re-score** (`score_head_template.py`, same local-monkeypatch
harness, both template sources run side by side this round):

| doc | reader | right | wrong | abstain | n |
|---|---|---|---|---|---|
| Litolff | geometry (position control) | 30 | 14 | 0 | 44 |
| Litolff | round8 | 25 | 14 | 5 | 44 |
| Litolff | template (exemplar-averaged) | 16 | 20 | 8 | 44 |
| Litolff | geom_template (this round) | 14 | 16 | 14 | 44 |
| Brahms | geometry (position control) | 11 | 0 | 0 | 11 |
| Brahms | round8 | 11 | 0 | 0 | 11 |
| Brahms | template (exemplar-averaged) | 6 | 3 | 2 | 11 |
| Brahms | geom_template (this round) | 6 | 3 | 2 | 11 |

(Note: "geometry" here is the PRE-EXISTING position-control row Sec6b
names, unrelated to this round's geometry-DRAWN templates -- an
unfortunate name collision the task brief's own wording creates; kept as
both scripts already name it, flagged here rather than silently
renamed.)

Agreement with round 8: Litolff 30 of 44 heads agree (same as the
exemplar path's 29/44); Brahms 6 of 11 (identical flip set to the
exemplar path -- both template sources fail the SAME 5 Brahms heads,
suggesting a Brahms-specific cause neither template source addresses,
not a property of averaging vs drawing).

**MEASURED NET NEGATIVE, same verdict as both earlier attempts** (the
oval shape trace, the exemplar-averaged templates): 12 Litolff +
5 Brahms regressions (right under round 8, not right under the geometry
template). `geom_template_where_round8_undecided_only` (keep round 8's
own answer except where it abstains) is never negative by construction
and measured ZERO net change on both docs this round -- unlike the
exemplar path, which gained one Litolff head
(`glyph/3/0/8/6/10`), the geometry-drawn template does not confirm a
through-rung there either.

**Of the two target heads, NEITHER flips under the geometry templates
either** -- both stay `abstain`, same reason (`no_rung_before_the_head`)
as round 8 and the exemplar path. Unlike the exemplar path's confident
WRONG match on `glyph/3/0/7/2/4`, the geometry template reads it as
undecided/not-on, i.e. it does not repeat that specific false-confidence
failure, but it also does not solve the head.

**Conclusion**: switching the template SOURCE (drawn geometry vs
averaged real ink) changes WHICH heads flip but not the overall verdict
-- still net negative, still does not resolve the two heads this whole
lane exists for. The measured tilt numbers are the most durable output
of this round: the manager's 20-30 deg outer-oval guess is refuted by a
large, stem-masked sample on both documents; the 40-45 deg hollow-slit
guess is confirmed on Litolff only.

Sheets: `out/print/ledgers/template_geom_templates.jpg` (30 tiles -- every
geometry template built, per page, drawn beside 3 real clean heads of
the same kind from that SAME page at the SAME canonical scale, so shape
and tilt compare directly) and `out/print/ledgers/template_geom_changed.jpg`
(19 tiles -- every head whose verdict differs round8 -> geom_template,
same drawing convention as `template_changed.jpg`).

Paths: `tools/omr/annotate/head_template.py` (geometry additions),
`benchmarks/omr-local-staff-2026-09/measure_head_tilt.py`,
`benchmarks/omr-local-staff-2026-09/score_head_template.py` (geometry
additions), `benchmarks/omr-local-staff-2026-09/template_geom_sheets.py`.

### lane-ledger-template, re-measured tilt + ONE review sheet (2026-10-02, Sean -- NO SCORING this round)

**Brief**: manager's read of `template_geom_templates.jpg` -- (1) the
~2 deg outer tilt is likely an ARTEFACT (fitEllipse with staff lines
left in is pulled flat by the line through/along the head); (2) the
hollow template (thin ring, big empty centre) does not look like a
real Litolff half note; (3) the "real head" comparison panels were not
framed on the heads at all. Sean: "no scoring this round, only
templates and one review sheet."

**Re-measured tilt** (`measure_head_tilt.py`, rewritten):

  1. staff-line ROWS are now masked before any contour fit -- but only
     in the columns OUTSIDE the oval's own expected footprint
     (`GEOM_HEAD_WIDTH_SPACES`'s half-width around the window centre),
     never inside it. **First cut masked the FULL row width and was
     measured WRONG** (caught before trusting any number): on a space
     this tight, BOTH neighbouring staff lines sit inside even the tight
     tilt window (measured directly: `lines_local` at window-relative
     rows ~5 and ~20 of a 26-27-row window), overlapping the oval's own
     top/bottom extent -- blanking the full row chopped both tips off
     the oval, leaving a thin residual whose fitted eccentricity read
     3-17 instead of a real oval's ~1.1-1.6, and the aggregate tilt came
     back at an incoherent 45 deg median. Column-restricted masking (this
     round's shipped version) leaves the oval's own ink alone wherever a
     line and the oval's footprint overlap, and only removes a line's
     ink where it is unambiguously NOT the oval (outside that column
     range) -- the same "never touch the real footprint, only the stub
     beyond it" principle this lane's own ledger-evidence masks already
     use.
  2. staff-line THICKNESS for the mask band is the page-level
     measurement (`score_head_template.measure_line_thickness_px`,
     already validated in the prior round) -- NOT a fresh per-head
     re-measurement: a first attempt at measuring thickness inside the
     tiny tilt window itself occasionally returned a wildly wrong run
     length (an edge column catching unrelated ink) and masked the
     ENTIRE window to zero ink on several heads before this was caught.
  3. OUTER tilt is restricted to heads IN A SPACE (`position % 2 == 1`)
     -- belt-and-suspenders on top of the masking, per Sean's own
     instruction, so no on-line head's own through-line can bias it at
     all.
  4. a non-deterministic staff-key pick (`set` iteration order, which
     varies by Python's per-process hash seed) was found and fixed
     (`sorted(staff_keys)[:1]`, was `list(staff_keys)[:1]`) -- without it
     the SAME input produced different thickness/measurement counts on
     different runs. A residual run-to-run jitter remains (borderline
     eccentricity-threshold heads flip in/out of the sample from tiny
     floating-point differences inside `cv2`'s own fit) -- small against
     the wide IQRs reported below, not chased further this round.

| doc | kind | outer tilt (median, IQR) | n | slit tilt (median, IQR) | n | slit:outer axis ratio |
|---|---|---|---|---|---|---|
| Litolff | filled | 10.4 deg [-2.3, 43.3] | 334 | -- | -- | -- |
| Litolff | hollow | 43.6 deg [4.4, 71.5] | 94 | 35.3 deg [30.5, 38.6] | 206 | 0.19 x 0.43 |
| Brahms | filled | 26.3 deg [4.7, 66.2] | 375 | -- | -- | -- |
| Brahms | hollow | 12.8 deg [-15.2, 59.0] | 103 | -7.0 deg [-13.0, 37.0] | 140 | 0.29 x 0.35 |

**Read honestly**: these are NOISY numbers (wide IQRs, some run-to-run
jitter) -- not the single clean angle the first (line-biased) pass
reported, nor a crisp confirmation of "45 deg". The medians sit closer
to the manager's 20-30 deg outer-oval guess than before (Litolff 10.4,
Brahms 26.3 for filled) but the spread is wide enough that this is a
RANGE, not a fact pinned to one number. The Litolff SLIT tilt is the
one tight, repeatable measurement here (30.5-38.6 deg IQR, n=206) --
close to the manager's own 40-45 deg guess for the slit specifically.
Brahms's slit measurement stays unreliable (sign-inconsistent, wide
IQR) -- the two editions still do not share one slit angle.

**Redrawn hollow templates**: `slit_width_ratio`/`slit_height_ratio`
(new parameters on `head_template.build_geometry_template`/
`build_geometry_templates`) size the inner slit from the MEASURED
slit-vs-outer axis ratio above (Litolff 0.19 x 0.43, Brahms 0.29 x 0.35)
instead of the previous hardcoded 0.55 x 0.70 -- the hollow template is
now mostly ink with a narrow, slanted slit, per the manager's own
reading of what a real Litolff half note looks like.

**ONE review sheet** (`template_review10.py`, NO scoring call anywhere
in it -- no `score_doc_with_templates`, no round8 comparison, no
right/wrong tally): `out/print/ledgers/template_review10.jpg` -- the
drawn templates (filled/hollow x on-line/in-space/raw, each doc, at the
same canonical scale) ABOVE 10 real far heads (`glyph/3/0/7/0/7`,
`glyph/3/0/7/2/4`, `glyph/3/0/8/6/10` always included, the rest a
hand-stated mix across filled/hollow x above/below x on-ledger/in-space,
selected by GATHER facts -- detector class, position parity -- never by
truth agreement, CLAUDE.md rule 5), each cropped CENTRED on the head at
4x zoom with generous padding (2.2 sp x, 2.8 sp y) so the head and its
ledgers are fully in frame, the best-matching template's own outline
overlaid at its MATCHED centre (yellow, + centre cross), local staff
lines (green), detector box (red), and a reference TICK (cyan, for
visual calibration only -- never tallied). The match's own
on-line/in-space verdict and margin are printed as text, not scored.

Staff-line rows pixel-row checked directly against the raw page (two
heads, five lines each): every line sits on a row with mean brightness
well below the window's white background (0-85 across the 10 rows
sampled), confirming the drawn lines are real ink, not a stale position.

Paths: `tools/omr/annotate/head_template.py` (`slit_width_ratio`/
`slit_height_ratio`), `benchmarks/omr-local-staff-2026-09/
measure_head_tilt.py` (rewritten masking + axis/ratio reporting),
`benchmarks/omr-local-staff-2026-09/score_head_template.py`
(`build_geometry_templates_for_doc` now reuses `measure_head_tilt.
summarize`), `benchmarks/omr-local-staff-2026-09/template_review10.py`,
`out/print/ledgers/template_review10.jpg`.

<!-- brought onto main 2026-10-04 from origin/lane-ledger-template-centre -->
## lane-ledger-template-centre (2026-10-04): the template's centre as round 8's probe row

Sean: "Feed the center into round 8". Base `origin/lane-ledger-edge-fix` (845ab8cc) + `head_template.py` and its
page-shape drivers copied from `lane-ledger-template-fix` 89327ab3 (not edited). GATHER+ADJUDICATE only; nothing
switched on. The `head_center_y` parameter already existed on the probe path (r8-main); this lane only SUPPLIES it.
Scripts: `template_centre.py` (per-head template fit), `score_template_centre.py` (arms), `centre_scan.py`
(diagnostic), `template_centre_sheet.py` (sheet). Sheet: `out/print/ledgers/template_centre/` (`sheet_changed.png`,
`sheet_census.png`, `pixel_check.json`).

Control (reproduced): default 25/14/5 Litolff (n=44), 11/0/0 Brahms; fix 1 (parts 1+2) 29/13/2, 11/0/0.

**F2 gate, fixed before any arm was scored:** use the template centre only where the template's own pixel check
passes round 4's MISS rule unchanged -- IoU >= 0.70 AND offset <= 0.15 sp (oval vs the head's ink blob). 23 of 44
Litolff heads and 11 of 11 Brahms heads pass.

| arm (fix 1 on) | Litolff right/wrong/undecided | Brahms |
|---|---|---|
| default (control) | 25/14/5 | 11/0/0 |
| F0 fix 1 | 29/13/2 | 11/0/0 |
| F1 template centre on every head | 25/15/4 | 11/0/0 |
| F2 only where the fit passes the gate | 29/13/2 | 11/0/0 |
| F3 only the 9 census heads | 29/13/2 | 11/0/0 |

**Result: no gain.** F2 and F3 change no verdict at all (identical to F0). F1 is a regression: four right heads
break, all with a template fit the gate refuses (IoU 0.49-0.66), so the gate does its job:
`3/0/0/5/12` -4 -> -3 (template oval 0.32 sp low, probe row moves off the through-line), `3/0/5/4/5` 10 -> abstain
(oval 0.57 sp low, IoU 0.49), `3/0/7/0/7` -3 -> -2, `3/0/7/3/5` 10 -> abstain (the lower row now reads as the head's
own outline). Sheet: `sheet_changed.png`.

**Why it does not help the census heads:** the template centre sits on the box middle. Template dy from the box
middle is 0.00-0.06 sp on 29 of 44 Litolff heads and never over 0.57; on the 9 census heads it is 0.00 on six,
-0.06, +0.19 and -0.13 on the others, and seven of the nine fits are trusted (IoU 0.71-0.80; the two that are not:
`7/2/4` offset 0.19 sp, `7/4/3` IoU 0.57). The oval sits
on the head and the box already agrees with it; the box-covers-only-the-top cause (A) is not what these heads show.
Per head (F0 answer -> reference; all unchanged by F1/F2/F3):
- `3/0/7/2/4` (undecided, ref 10): scan below. A centre 0.1-0.4 sp ABOVE the box middle finds the through-line
  (R at -0.4..-0.1 sp); the template says 0.00. A probe band of +-0.30 sp (shipped +-0.15) finds it AT the box
  middle (and at 0..-0.5).
- `3/0/7/7/0` (11, ref 12): same pattern: right at -0.4..-0.1 sp with the shipped band; right at the box middle
  and 0.8 above with a +-0.30 band.
- `3/0/7/3/2`, `3/0/7/3/4`, `3/0/7/4/3` (one short): right only at +0.6..+0.8 sp (toward the staff-far side)
  with the +-0.30 band for 7/3/2, 7/3/4, 7/4/3 -- far outside any plausible centre error; the crops show a ledger
  drawn against the TOP of the head ("popped"/"not kept" magenta) where the print's reference puts the head ON it
  (nominal row at the head's top). That is a rung-through-vs-touching decision at the top edge, not a centre.
- `3/0/7/3/1`, `3/0/7/6/1`, `3/1/0/6/0` (one short): wrong at every centre in -0.8..+0.8, both bands. Same top-edge
  ledger picture. `3/0/8/6/10`: abstains at every centre and band.
So the centre is not the limiting factor for this population; two heads (`7/2/4`, `7/7/0`) are limited by WHERE
the probe row sits in a head whose rendered ink centre the template does not move, and a wider probe band
(`MIDDLE_ROW_TOL_SPACES` 0.15 -> 0.30, monkeypatched in `centre_scan.py` only) rescues those two without any
centre. REPORTED, not added: no threshold was tuned or changed in `tools/`. Scoring the +-0.30 band as a whole arm
was not done (it would be a tuned threshold; needs its own roadmap decision and a check on Brahms).

Pixel check on the sheet (`pixel_check.json`; ink fraction in the 0.6 sp stubs on the line vs 0.5 sp off it): every
orange line reads on > off, but several are weak (3/0/7/7/0 1567.0: 0.50/0.35; 3/0/7/3/1 1454.0: 0.22/0.00 -- short
ledgers). The green probe row lies inside the template oval at the box's x for every tile except one: `3/0/5/4/5`
F0, where the box middle is above the oval (the template misfit, IoU 0.49).

Template fits on the far heads (Litolff, shape A_oval; Brahms, C_mean_shape): Brahms 11 of 11 pass (IoU 0.74-0.95,
offset <= 0.10 sp). Litolff: 21 of 44 miss, mostly the hollow heads (IoU 0.22-0.56) and blob-fused ones.

<!-- brought onto main 2026-10-04 from origin/lane-ledger-far-edge-crops -->
## lane-ledger-far-edge-crops (2026-10-04): "a ledger touching a far head's FAR edge -- is the head ON it?" (Sean: "Depends, show me crops")

MEASURE + CROPS ONLY; `tools/` untouched (the reader is only called). Script `far_edge_crops.py`; sheet and key
`out/print/ledgers/far_edge/far_edge_sheet.png`, `far_edge_key.json`. Base `origin/lane-ledger-template-centre` (2f9de5aa).
Control: fix 1 (`near_edge_ledgers` + `restore_masked_near_edge`) Litolff 29/13/2, Brahms 11/0/0; default 25/14/5, 11/0/0.

**Test.** A far-edge rung = a rung of the bare ink walk (`edge_census.stage0_candidates`, no masking) that the census's
own `_is_edge_related` calls 'far' (>0.25 sp from the box middle, within [-0.45,+0.35] sp of the far edge), PLUS rungs on
the head's far half the census calls 'mid' (rm > 0.15 sp, the shipped probe tolerance, and rf <= 0.35). Backed by ink =
`thin_flat_jut_evidence` ok (other heads/accidentals blanked) or a raw +-1 px ink run >= 0.1 sp beyond the box. Chord
partner farther out = any detector notehead box within 1.7 sp in x, 0.5-3.0 sp farther out.

**Result: the population is small.** Of 55 far heads, 10 have such a rung (Litolff 9, Brahms 1):
- (a) reference ON the line, no partner: Litolff 4 (`3/0/7/3/1`, `7/3/2`, `7/3/4`, `0/7/2`); Brahms 0.
- (b) reference in the space nearer the staff, no partner: 0 in both. Brahms' only candidate (`1/1/8/7/4`, ref 13) is
  a SLUR crossing the head's bottom, not a ledger (no ink run beside the head) -- the head hangs under a real near-edge ledger.
- (c) a chord partner sits farther out: Litolff 4 (`0/2/3`, `0/2/9`, `0/5/12`, `0/6/2`); Brahms 0. Reference is ON the
  line in 2 (2/3, 5/12; answer unchanged by "on it") and NOT on it in 2 (2/9 ref -5, 6/2 ref -4: the rung is the partner's).
- other: `3/0/9/3/5` (the rung is the head's own outline, no ink beyond it).
So where nothing sits farther out, the reference says ON in every case that exists (4 of 4) and never in the space.
"If that rung meant ON" would turn 3 wrong heads right (7/3/1, 7/3/2, 7/3/4: -5 -> -6) and 7/0/2 (-6 -> -2); it would
turn 2/9 (-6 -> -4) and 6/2 (-6 stays) wrong/unchanged -- both (c), where it would be wrong or no help.
Caveat: the jut on 7/3/1 and 7/3/2 is only 0.23-0.24 sp (the heads nearly touch their neighbours; stubs are tiny bumps).
Of the 9 named misses only 3 (7/3/1, 7/3/2, 7/3/4) have a far-half rung; `3/0/7/2/4, 7/4/3, 7/6/1, 7/7/0, 8/6/10,
3/1/0/6/0` have their popped rung within 0.26 sp of the box middle (through the head, rm -0.26..+0.11): not far-edge.

**Sheet** (7 tiles, 110 px per staff space = x7 Litolff; shuffled; number only): a = tiles 4, 6, 7; c = tiles 1, 2, 3, 5
(no (b) exists; the (c) tiles are the contrast). Excluded by the pixel rule: `0/7/2` (ink on-row 0.74 vs 0.77 off).
Pixel numbers (+-1 px, head width +-0.5 sp: on/off 0.5 sp): span 0.69-0.87 vs 0.47-0.64 on all 7; staff-line frame control
0.97-1.00 vs 0.03-0.11. Weakness: the line is mostly hidden in black heads, so the span test is weak (tile 3 0.69/0.64).

<!-- brought onto main 2026-10-04 from origin/lane-ledger-accidental -->
## lane-ledger-accidental (2026-10-04): why accidental ink to the left still corrupts tiles 5, 6 -- and why tile 2 misses its 2nd ledger

Base `origin/main` e15b5681. Scripts: `accidental_census.py` (census, runtime wrappers via `edge_census`), `accidental_sheet.py`
(the crops; `--arm=NAME` redraws under an arm), `score_accidental.py` (arm table). Sheet `out/print/ledgers/accidental/accidental_sheet.png`
(+ per-tile PNGs; `arm_conn_drop/` = the same tiles under conn+drop). x6, real print, red = head box, purple = accidental boxes,
orange = kept rungs, magenta dashed = bare-ink rungs the reader dropped, yellow = ink `_exclude_other_heads_ink` blanked.
**Control** (fix1_far: near_edge_ledgers + restore_masked_near_edge + far_side_ledger, four_causes_cd): Litolff 32/10/2 (n=44), Brahms 11/0/0,
reproduced with recording off and on; default read bit-identical to the pre-change tree on all 55 heads (0 differ).

**Cause per tile** (none is "accidental strokes became rungs" and none is the cause-C exclusion running on the wrong ink):
* tile 5 `3/0/0/7/1` (we -10, ref -8): ladder [434, 423.5, 411, 396, 376] -- 5 rungs, the head is on the 5th; the true ladder is 4 (L1 hides inside the
  lower head's blob). Row 434 is the LOWER head `7/2`'s own ink (box 417.9-437.4, undersized: ink goes ~6 px past it on the right). The
  exclusion keeps a neighbour's row when ink continues past its box on both sides within 2 px; on rows 432-435 the "left side" is the
  ACCIDENTAL's blob 5 px left of `7/2`'s box (it ends at 1716, the head ink starts at 1722: 7 white columns between), so 434 survives as a rung.
  Without accidental boxes in the exclusion set the answer is identical (-10), i.e. the cause-C box exclusion neither helps nor hurts here; the
  accidental box is also too narrow (right edge 1713, ink to 1716).
* tile 6 `3/0/0/7/2` (we -6, ref -2): NOT the accidental (read without accidental boxes: -6 too). Ladder [424, 396, 376.5]; the head is on L1 (424, evidenced
  at its middle row) but `derive_far_head_step` takes "evidenced" to mean the LAST rung is the one through the head, and the last rung is 3.87 sp
  beyond it (the stack's other heads' ledgers) -> counted all three.
* tile 2 `3/0/0/2/4` (we -4, ref -7): no accidental in range. Two causes: (i) the 2nd ledger (y~415) juts out of the neighbour head `2/9` on ONE side;
  the exclusion blanks 2/9's rows (needs both sides), the bare walk also never offers it (merged blob), so the ladder is [428.5, 395]; (ii) the head box
  (382.7-404.6) is too low/big: the 3rd ledger at 395 touches the head's bottom but reads "through its middle". With L2 found the answer would be -6, not
  -7: the head box is the other lane's.

**Census, all 55 far heads** (detector accidental box with right edge <= 2 sp left of the head box and within 1.5 sp vertically): Litolff 9 of 44 --
6 right / 3 wrong (`7/1`, `7/2`, `7/7/0`); Brahms 2 of 11 -- 2 right. Same heads with accidental boxes REMOVED from the exclusion set: Litolff 5/3/1
(+1 right from cause C: `3/0/7/4/2` abstain -> right), Brahms 2/0/0. 8 of 11 are right now; 3 wrong, each for a cause above or unexplained (`7/7/0`).

**Arms** (all default OFF; Litolff right/wrong/abstain, Brahms 11/0/0 in every arm; `3/0/0/6/2` excluded would read one fewer wrong):
| arm | Litolff | per-head changes vs control | right heads broken |
|---|---|---|---|
| control | 32/10/2 | -- | -- |
| conn (`exclusion_rules(connected=True)`) | 32/10/2 | `7/1` -10 -> -6 wrong -> wrong (false 434 gone, but the 423.5 through-ledger of the lower head, whose left stub is the accidental, goes with it; the true L1 is invisible as ink) | 0 |
| drop (`derive_far_head_step(drop_rungs_beyond_head=True)`) | 33/9/2 | `7/2` -6 wrong -> -2 right | 0 |
| conn+drop | 33/9/2 | both of the above | 0 |
| (refused) one-sided thin-jut keep, with conn | 33/9/2 (+drop 34/8/2) | `7/7/0` 11 wrong -> 12 right, mechanism not shown by its crop (the yellow there is a box overlapping the head itself) | 0 |
`drop` tolerance (beyond the head's far edge): 0.25 / 0.35 / 0.5 / 0.75 / 1.0 sp all 33/9/2, 1.5 sp back to 32/10/2; shipped 0.25 (ledger n+1 of a head ON ledger n sits ~0.5 sp past its far edge).
The one-sided rule was built, did not recover tile 2's ledger (a round head tip beyond an undersized box also tapers thinly), and was REMOVED; the +1 on `7/7/0` is not evidence of a cause.
**Reading**: `drop` is a clean convention fix (a ledger beyond a head is not that head's) worth +1 here; `conn` implements Sean's 10-01 white-gap rule but moves no verdict
by itself -- tile 5 stays wrong until the lower head's undersized box is replaced by the standard head box (other lane), at which point re-run `score_accidental.py`.
Pixel check (ink on the row within +-1.1 sp of the head x, vs the rows 0.5 sp above / below; printed by `accidental_sheet.py`): tile 5 kept L1 434 0.66/0.74,0.09; L2 423.5 0.74/0.11,0.63; L3 411 0.66/0.11,0.40;
L4 396 0.74/0.26,0.11; L5 376 1.00/0.29,0.66. Tile 6 L1 424 0.74/0.12,0.74; L2 396 0.79/0.21,0.12; L3 376.5 1.00/0.35,0.68. Tile 2 L1 428.5 0.74/0.11,0.00; 395 0.63/0.54,0.60 (a head body, not a thin line -- consistent with cause ii).
Tests `tools/omr/tests/test_ledger_accidental_2026_10_04.py` 7 (new names: RED by ImportError against the base tree; GREEN now); all 362 `-k ledger` tests pass.

<!-- brought onto main 2026-10-04 from origin/lane-ledger-exclusion -->
## lane-ledger-exclusion (2026-10-04): what `_exclude_other_heads_ink` may blank of THIS head's own evidence (tiles 2, 7, 9)

Base `origin/lane-ledger-accidental` b50ef07a. Scripts (this directory): `score_exclusion.py` (arm table), `exclusion_sheet.py` (crops),
`exclusion_reach.py` (does each rule fire at all), `exclusion_identity.py` (default-output identity), `exclusion_trace.py` / `exclusion_one_rows.py` / `exclusion_ascii.py` /
`exclusion_diag.py` (per-head traces). Sheet `out/print/ledgers/exclusion/exclusion_sheet.png` (+ one PNG per head). All keywords default OFF.
**Control** reproduced: Litolff 32/10/2 (n=44), Brahms 11/0/0; with `drop_rungs_beyond_head` 33/9/2. **Default output bit-identical**: all 55 heads x 3 default-path arms (165 reads,
position AND reason) are byte-identical between this tree and the base tree (`exclusion_identity.py`, base `ledger_grid.py`/`score_truth_set_rungs.py` loaded from git).
LEGACY path (the ledger reader is the annotate/staged-support reader; nothing here is wired into STAGED or switched on).

**Cause, per tile** (all three confirmed in ink, `exclusion_ascii.py`):
* tile 9 `3/0/7/7/0` and tile 7 `3/0/7/4/3`: the box blanking the head's middle band is NOT another note. `3/0/8/7/1` (staff 8) and `3/0/6/4/3` (staff 6) overlap the subject's box by
  93% / 62% of the smaller box (IoU 0.57 / 0.45): the same head claimed by the cross-staff contest on both staves (`glyph_owner` decides whose; the ledger reader should not). Blanked, the ledger
  through the head vanishes from the middle-row evidence.
* tile 2 `3/0/0/2/4`: the real 2nd ledger (rows 413-417, 5 px thick) juts 12 px right out of neighbour head `2/9` and nothing on the left. Both-sides test -> blanked.

**Rules** (convention first, constants from spacing; `sp` = staff spacing):
1. `exclusion_boxes_for(..., drop_same_ink_other_staff=True)` -- a box owned by ANOTHER staff (subject key `glyph/p/sys/STAFF/..`) that overlaps the subject's box by > 0.5 of the SMALLER box
   (`SAME_INK_OVERLAP_FRACTION`) and does not COINCIDE with it (IoU < 0.9, `SAME_INK_COINCIDENT_IOU`) is the same ink twice, not blanked. The coincidence bound is not optional: Brahms
   `glyph/1/1/8/7/4` has a staff-9 duplicate at IoU 0.97 whose blanking of the WHOLE head keeps the head's own ink from merging with a slur into a false rung (without the bound: 13 right -> 11
   wrong, found by the arm table, traced in `exclusion_trace.py`). 0.9 sits between 0.57 and 0.97: **n = 3 heads, so a measured bound, not a convention**. Fires on 15 of 55 heads (reach).
2. `exclusion_rules(one_sided=True)` -- a row of another head's box is kept when ink runs unbroken from that head's outermost ink out past the box edge >= 0.35 sp
   (`ONE_SIDED_JUT_MIN_BEYOND_SPACES`), is <= `LEDGER_THICKNESS_MAX_SPACES` (0.35 sp) + 1 px thick over the outer half of the run, and its top and bottom edges move <= 0.10 sp (min 1 px,
   `ONE_SIDED_JUT_FLAT_TOL_SPACES`) over it. Fires on 17 of 55 heads. **Does it separate a ledger from a round head tip? Not cleanly.** Tile 2's ledger passes; a synthetic round tip fails
   (tests); but on the real tile 5 (below) the pointed right tip of the lower head `7/2` (rows 427-429, 10 px beyond its undersized box, thickness 6,5,5,4,4) ALSO passes. The stricter "same
   thickness along the run (<= 1 px)" refuses that tip -- and tile 2's ledger with it (a real ledger's own end tapers too: 5 thick for 5 px, then 3). Both measured (arm table); the looser one is
   the keyword's behaviour, `ONE_SIDED_JUT_THICKNESS_TOL_PX` (None = off) holds the stricter one.
3. `exclusion_rules(own_box=subject_box)` -- the subject's own box is never blanked (the docstring's old principle). **REFUSED**: it breaks two right heads (Litolff `3/0/9/3/5` 11 -> abstain,
   Brahms `1/1/8/7/4` 13 -> wrong; its only gains are `3/0/0/6/2` against the reference Sean marked wrong, and `2/9` wrong -> wrong). Keyword kept, never to be turned on; not in the headline arm.

**Arms** (Litolff right/wrong/abstain; Brahms 11/0/0 unless stated):
| arm | Litolff | per-head changes vs control | right heads broken |
|---|---|---|---|
| control | 32/10/2 | -- | -- |
| same | 34/8/2 | `7/4/3` -3 -> -4 right; `7/7/0` 11 -> 12 right | 0 |
| one | 32/10/2 | `2/4` -4 -> -6 (L2 found; still wrong: head box too low, other lane) | 0 |
| own | 32/9/3, Brahms 10/1/0 | `9/3/5` right -> abstain; Brahms `8/7/4` right -> wrong | 2 |
| same+one | 34/8/2 | tiles 7, 9 right; tile 2 -6 wrong | 0 |
| drop (lane-ledger-accidental) | 33/9/2 | `7/2` -6 -> -2 right | 0 |
| same+one+drop | 35/7/2 | tiles 7, 9, `7/2` right | 0 |
| conn+one | 33/9/2 | `7/1` -10 -> -8 right (see below) | 0 |
| **conn+same+one+drop** | **36/6/2**, Brahms 11/0/0 | tiles 7, 9 right, `7/1` -10 -> -8 right, `7/2` -6 -> -2 right; tile 2 -4 -> -6 wrong | **0** |
| same+one(strict)+conn+drop | 35/7/2 | as above minus `7/1` | 0 |
| all (+own) +drop | 35/6/3, Brahms 10/1/0 | as `own` | 2 |
Tile 5 `3/0/0/7/1` is the lane-ledger-accidental tile and appears only with `conn` AND `one` together: `conn` drops the false row 434 and the lower head's through-ledger that counted only
because of the accidental on its left (423.5, "both sides"); `one` puts back the through-ledger as its right-hand jut (row 428, the box middle). Ladder 5 -> 4 rungs, -8. Correct COUNT, but the
row's pixel check is a head-body row, not an isolated line (ink 0.63, rows 0.5 sp off 0.51/0.60) because that ledger lies inside the lower head's blob -- and it rests on the tip-or-ledger call above.
**The one question for Sean** (a single crop, `glyph_3_0_0_7_1.png`, right panel): is the pointed ink right of the lower head, at the orange L1 row, the END OF ITS LEDGER or the head's own tip?
If a tip, `7/1` stays at -6 (35/7/2) and `one` is worth only tile 2's L2.

**Tiles 2 / 7 / 9** individually: 9 and 7 become right by rule 1 alone (the ledger through the head returns to the middle-row band; pixel check below). 2: L2 (y416) is now counted
(ladder 428.5, 416, 395), but the head box (382.7-404.6) sits too low, so "through 395" gives -6, not -7: unchanged wrong, not fixable here. Pixel check (ink on the row within +-1.1 sp of the
head x / rows 0.5 sp above, below): tile 2 L1 428.5 0.74/0.11,0.00; L2 416 0.63/0.63,0.11; L3 395 0.63/0.54,0.60. Tile 7 L1 1470 0.91/0.46,0.17; L2 1452 0.91/0.37,0.51 (row through the head's
body, the ledger is the jut at its middle). Tile 9 L1 1567 0.83/0.11,0.46; L2 1582 0.86/0.31,0.51 (same). Tile 6 L1 424 0.74/0.12,0.74; L2 396 0.79/0.21,0.12; L3 376.5 1.00/0.35,0.68 (L2, L3 drawn
but beyond the head: not counted, by `drop`). **Broken heads: none** in any arm that includes rule 1 or 2 (right heads broken: []). The 15 heads where a rule fires but the verdict does not move
were not cropped; REACH says the rules are live, not that every firing is a ledger.
Tests `tools/omr/tests/test_ledger_exclusion_2026_10_04.py` 11 (all names new: RED by ImportError on the base tree; one mutation -- raising the thickness cap -- turns the thick-ledger test RED);
`-k ledger` 373 passed 2 xfailed (one older test pinned `_EXCL_RULES == {"connected": False}` and now names the two new keys); `staged.check` 250, unchanged.

<!-- brought onto main 2026-10-04 from origin/lane-standard-head-box -->
## lane-standard-head-box (2026-10-04): a STANDARD-size head box per page, placed by the geometry template (Sean)

Base `origin/main` e15b5681 (round 8 + fix 1 + far-side rule, all OFF). Sean: *"Shouldn't the boxes for notes heads be standardized in size?"*,
*"Could we use our template work to determine size of notes?"*. Code: `tools/omr/annotate/standard_head_box.py` (pure construction, imported by
nothing in the product; `ledger_grid.py` NOT edited), template code copied from `lane-ledger-template-fix` 51c8f65a (`head_template.py`,
`ledger_shape_trace.py`, and the measuring scripts `shape_from_page.py` etc.). Scorer `score_standard_box.py`, sheet `standard_box_sheet.py`,
step-4 numbers `standard_box_thrown_tests.py`; output `out/print/ledgers/standard_box/`.

**Construction.** SIZE = the page's measured head (second-moment fit on clean, isolated, ON-LINE filled heads, `shape_from_page`): Litolff
oval 1.59 x 1.05 sp tilt 29.3 deg (n=8 on-line heads for the WHOLE document -- pages 1/2/3 have 0/2/6, so all three use the document's) -> axis-aligned
box 1.48 x 1.20 sp; Brahms p0 1.42x1.07 tilt 30.8 (n=12) -> 1.34 x 1.17, p1 1.49x1.13 tilt 28.1 (n=120) -> 1.42 x 1.22. A hollow head takes the
same outer size. CENTRE = the template's FREE position search (`match_head_template(decide="staged", dx_range 0.4 sp, head_ink_mode="opening")`,
no ledger input, no refine). Detector box vs standard box over the 44/11 far heads: Litolff centre shift median 0.08 sp (p90 0.38, max 0.57), size
ratio width median 0.99 [0.86, 1.15], height median 0.91 [0.74, 1.32]; Brahms shift median 0.04 (max 0.08), ratios 0.93-1.05 / 0.95-1.08.
**Search control (can fail)**, 12 clean in-staff heads per doc, centre error against the head's own centroid: started at the detector box median 0.07 sp
(Litolff) / 0.03 (Brahms); started 0.3 sp off 0.16 / 0.04; started 1.2 sp off 1.29 / 1.45 (does NOT recover -- outside the window). Box check control
(share of the head blob inside the box): right centre 0.82 / 0.98, same box 1 sp displaced 0.30 / 0.27.

**Arms** (reader = fix 1 + far-side rule; the BOX and the centre both change, `head_center_y` left None; other heads' exclusion boxes stay detector boxes).
Gate for S2, fixed BEFORE scoring: template-oval vs head-ink-blob IoU >= 0.70 and centre offset <= 0.15 sp, on the OPENED ink with staff lines only
(ledger-free, so the gate is not a consequence of the ledger read; it is also not independent of the search, which maximised agreement with that ink).

| arm | Litolff right/wrong/abstain (n=44) | n=43 (`6/2` out) | Brahms | right heads broken |
|---|---|---|---|---|
| S0 detector box (control, reproduces 32/10/2, 11/0/0) | 32/10/2 | 32/9/2 | 11/0/0 | - |
| S1 standard box on every far head | 33/9/2 | 32/9/2 | 11/0/0 | 5 |
| S2 standard box only where the fit passes | 35/8/1 | 35/7/1 | 11/0/0 | 0 |

Against Sean's own readings (`3/0/0/6/2` = -6, not the reference's -4): S0 33/9/2, S1 32/10/2, **S2 36/7/1**.
Gate passes: Litolff 19 of 44, Brahms 11 of 11. **All 6 hollow Litolff far heads fail the gate** (0 of 6; filled 19 of 38): the oval is a filled shape and
the ink blob of a half note has a hole, so the gate cannot pass a half note -- S2 never moves the very half-note tiles Sean raised (1, 4).

Every changed head (S1 vs S0; S2 = S1 where "pass"):
- `1/0/10/7/1` -4 wrong -> -2 right (ref -2; fit 0.47/0.29 FAIL so S2 stays -4): box 0.51 sp lower, 1.15 x 1.32 bigger; the through-ledger now sits at the box middle (evidenced).
- `3/0/7/6/1` 11 -> 12 right, `3/1/0/6/0` -5 -> -6 right, `3/0/7/2/4` abstain -> 10 right (all PASS): the box got NARROWER (0.87-0.95 x) so the ledger's jut past the box clears the 0.25 sp stub test (3.7/4.3 px, 4.2/2.5 px against 3.9 needed; detector box 2.0/2.6 and 3.6/1.8) -- size is what mattered; the margin is 0.3-0.4 px, thin.
- `3/0/0/6/2` -6 -> -4 "right": right only against the WRONG reference; Sean's -6 is what S0 reads. S1 makes it worse; S2 keeps -6.
- `3/0/0/7/1` -10 -> -8 right (ref -8, fit FAIL -> S2 -10); `3/0/0/7/2` -6 -> -8 wrong (ref -2; PASS: still wrong, differently).
- 5 RIGHT heads broken by S1, every one a gate FAIL: `0/2/3` (fit 0.60/0.26), `0/5/12` (0.19/0.71), `0/6/1` (0.18/0.78; no_rungs, abstains), `5/4/5` (0.21/0.61), `1/0/9/0` (0.73/0.16). Crops: the oval is pulled into a fused stem/partner or onto the wrong half of the head (sheet tiles 8-10, 13, 15). Not tuned away; the gate removes them.
- `3/0/0/2/9`: -6 -> -4 under S1, still wrong (ref -5): fit 0.39/0.50, the head is fused to its stem and a partner above; the cyan box lands low on the stem. Not fixed.

**Sean's named tiles, S0 / S1 / S2** (his reading): 1 `1/0/10/7/1` (-2) -4 / -2 / -4; 3 `3/0/0/2/9` (-5) -6 / -4 / -6; 4 `3/0/0/6/2` (-6) -6 / -4 / -6;
7 `3/0/7/4/3` (-4) -3 / -3 / -3; 8 `3/0/7/6/1` (12) 11 / 12 / 12; 9 `3/0/7/7/0` (12) 11 / 11 / 11; 10 `3/1/0/6/0` (-6) -5 / -6 / -6.
Box checks: tile 1 the standard box holds 0.82 of the head blob (detector 0.59) -- Sean's "box too small" is borne out; tile 3 the standard box is no better (0.52 vs 0.57).

**Step 4: what throws "past the head" on the two still-wrong tiles** (`standard_box_thrown_tests.py`; each re-evaluation asserted equal to the real function):
- `3/0/7/7/0` (thrown line y 1580, 0.20 sp above the standard box middle): `ledger_grid.head_middle_rung_evidence` -> False, so `derive_far_head_step` pops the rung
  (gap -0.40 sp <= -TOUCH_TOL 0.20). Reason: the middle-row band (rows 1581-1586) has NO ink at the probe column because `_exclude_other_heads_ink` blanks it:
  another detector notehead box on a neighbouring staff, `glyph/3/0/8/7/1`, overlaps 0.59 of this head's box. With no blanking the same test passes (run 1716-1748, jut 1.1 / 7.2 px against 3.9 needed). Identical at the detector box and the standard box.
- `3/0/7/4/3` (line y 1457): `_rung_row_clears_box` -> False: run through the row is 21 px (x 1193-1214), needs box width + 2 x 0.05 sp = 26.5 px (detector box) / 24.6 px (standard box); and
  `head_middle_rung_evidence` finds no run at the detector box (a box `glyph/3/0/6/4/3` overlaps 0.63 and blanks it) and, at the standard box, a run 1193-1214 whose jut is -2.7 / +0.6 px against 3.9 needed (without blanking 3.3 / 2.6: still short). The ledger here is hidden behind the neighbouring box's blanking AND short on the left.
- (Fixed ones, for the record: `3/0/7/6/1` and `3/1/0/6/0` are thrown at the detector box by the SAME stub test -- jut 2.0/2.6 and 3.6/1.8 px vs 3.9 -- not by the other-head blanking; the narrower box passes it.)
The accidental / other-head blanking is another lane's function; not edited.

**Pixel checks** (sheet `standard_box_sheet.png`, 15 tiles, 1752 x 6358, x6 of the 600 dpi render). Lines: 34 drawn, 28 read on ink by the stub-zone/ridge test; 6 flagged (`6/1` 1583.5, `6/0` 2268.5, `0/2/3` 411, `0/5/12` 424, `0/7/2` 428.5, `1/0/9/0` 2287) -- each flagged at moved_px 0, i.e. no row within +-0.35 sp reads better (the crude test is low on lines running through a head's own ink); 4 lines snapped (-5, -5, 1, 1 px). Frame control (staff edge row vs 0.5 sp beyond): on >= 0.97, off <= 0.35 on every tile.
Boxes: share of the head blob inside the box, detector (red) / standard (cyan): tile 1 0.59/0.82; passing heads `6/1` 0.97/0.93, `7/0` 0.94/0.89, `1/6/0` 0.95/0.90, `0/7/2` 0.78/0.95, `2/4` 0.91/0.82; failing heads mostly worse (`0/5/12` 0.56/0.38, `5/4/5` 0.87/0.51, `0/6/1` 0.50/0.37). Share of the box that is ink: cyan 0.73-0.81 on the passing heads vs red 0.60-0.72 (tighter). Mean over all 15: red 0.73, cyan 0.69.

**What this says.** A standard box helps where the head is clean and the detector's box is wrong in SIZE (the ledger-jut test is size-sensitive: three heads) or too small
(tile 1). The free position search is not reliable on a head fused to a stem/partner or on a half note, and the gate that spots this cannot see hollow heads at all. S2's +3 on Litolff
(32 -> 35) is four changed heads, three of them fixes with a 0.3-0.4 px margin on the jut test; Brahms is untouched. Not a result to flip a default on (rule 5): needs the hollow-head fit fixed first
(fill the blob's hole before the IoU) and a read of the two blanked-by-neighbour-box heads. Tests: `test_standard_head_box_2026_10_04.py` 7 (RED against the module missing; two mutations -- centre from the detector, un-rotated extents -- each fail one test).

<!-- brought onto main 2026-10-04 from origin/lane-standard-box-hollow -->
## lane-standard-box-hollow (2026-10-04): fill a half note's counter before the standard-box fit (Sean)

Base `origin/lane-standard-head-box` 31813a1c. Code: `standard_head_box.counter_pockets / fill_counter` (+ `score_standard_box_hollow.py`,
`standard_box_hollow_sheet.py`, 5 tests); `ledger_grid.py` NOT edited; nothing wired into a product path. Output `out/print/ledgers/standard_box_hollow/`.

**Control** (can fail: the new arm is the only change): S0 32/10/2 and 11/0/0, S2 35/8/1 and 11/0/0 reproduced exactly.

**Rule (every size measured, none tuned on these heads).** The page gets the counter painted as ink (`gray` copy) BEFORE the template's free search and before the
gate's IoU; the reader still reads the original page. Counter = a white pocket (enclosed as printed; for a head the detector calls HOLLOW also enclosed after a
closing) with largest inscribed radius <= (short axis - 2 strokes)/2 (4.3 px Litolff), >= t/4 + 0.5 px (speckle floor; a 1-px hole is 1.0, real counters 1.9-2.9),
area <= the inner-oval area, centre within 0.5 sp of the detector box (hollow class) / inside the box (filled class, enclosed WITHOUT closing; a closing-only pocket must
be inside the box -- an earlier version painted slivers between head and stem, seen on the sheet, fixed). **Closing disc = 2 t + 1 px** (9 px Litolff t=4, 15/11 Brahms):
a gap in a ring's wall the wall's own stroke could span twice; wider is a different mark (test). A head with no pocket gets the SAME array back.

| arm | Litolff r/w/a (n=44) | n=43 (`6/2` out) | vs Sean's own readings (`6/2` = -6) | Brahms | right broken |
|---|---|---|---|---|---|
| S0 detector box | 32/10/2 | 32/9/2 | 33/9/2 | 11/0/0 | - |
| S2 control | 35/8/1 | 35/7/1 | 36/7/1 | 11/0/0 | 0 |
| S2H (counter filled) | **36/7/1** | 36/6/1 | **37/6/1** | 11/0/0 | **0** (vs S2 and vs S0) |

**Every change S2 -> S2H: one head.** Tile 1 `glyph/1/0/10/7/1`: -4 wrong -> -2 right (ref -2, Sean: half note on the line); gate IoU/offset 0.47/0.29 FAIL -> 0.79/0.05 PASS, the
standard box then holds 0.81 of the head (detector 0.56 filled / 0.64 raw), the ledger through the box middle is evidenced. The other 5 hollow far heads (`1/0/10/8/1`, `1/0/3/7/3`,
`3/0/0/5/12`, `3/0/0/6/1`, `3/0/5/4/5`) still fail the gate (IoU 0.65 / 0.63 / 0.60 / 0.16 / 0.27 after fill): a filled oval against a blob fused to a stem, a stacked partner or
the staff -- the same cause that fails the filled heads, not the counter. Their reads are unchanged (all right under S0 and S2). 48 heads with no pocket: box, gate and read bit-identical to S2.

**Tile 4 `glyph/3/0/0/6/2`** (Sean: ON its line, -6): reads -6 under S0, S2 and S2H, i.e. RIGHT against Sean, wrong against the stale reference (-4); not moved, not broken, kept out of the n=43
headline. Its class is BLACK (`noteheadBlackInSpace`) yet the ink holds a clean enclosed counter at Otsu -- the pocket is found (filled-class rule), but fit stays 0.44/0.40 (fused to its stacked
partner and stem, blob 28 x 36 px). **On this print I could not see an OPEN end**: the counter is closed at the gather's threshold; Sean's "open-ended" may be at the head's other side or at a
different threshold. The closing path therefore has NO real far-head test case here -- it is proven on synthetic rings only (RED/GREEN tests), which is not evidence it fires on a scan.
Tile 5's partner `3/0/0/7/2` is a black head, no pocket, box unchanged (still the undersized-box case for `lane-ledger-accidental`).

**Controls on the in-staff population (can fail)**: H -- hollow-class in-staff heads with a counter found: Litolff 215 of 225, Brahms 100 of 100. G -- the template fit's gate on those heads,
raw page -> filled page: Litolff 1 -> 113 of 225 pass (isolated 0 -> 13 of 26), Brahms 1 -> 69 of 100 (isolated 0 -> 16 of 16); free-search centre error against the head's filled-blob centroid,
median Litolff 0.31 -> 0.27 sp, Brahms 0.59 -> 0.32 sp (isolated 0.26 -> 0.21, 0.06 -> 0.03). The gate really could not see a half note before. **F -- the filled-class rule is NOT safe in-staff**: 87 of 582 Litolff
and 8 of 797 Brahms filled-class in-staff heads get a "counter" (wedge pockets between head, staff line, stem or beam; contact sheet checked). On the 38 filled Litolff / 11 Brahms FAR heads it fires on exactly 1
(`6/2`, a real counter). It stays gated by the fit, but do not apply the filled-class override to in-staff heads without a line-bounded-pocket rule (a solidity test did not separate them).

**Pixel checks** (sheet `standard_box_hollow_sheet.png`, 7 tiles, 1752 x 3220, x6 of the 600 dpi render): drawn lines 14, 13 on ink by the stub-zone/ridge test (one flagged, tile 4 `1/0/3/7/3` orange y 1616.5, ridge 41/24, a line through the head's own ink);
frame control on >= 0.97 / off <= 0.26. Share of the head blob inside the box, detector (red) / standard (cyan), on the filled page: tile 1 0.56/0.81, tile 3 0.92/0.81, tile 4 0.63/0.60, tile 5 0.43/0.47, tile 6 0.47/0.38, tile 7 0.82/0.50,
tile 2 0.48/0.50. Share of the box that is ink on the filled page: cyan 0.84 / 0.87 / 0.89 / 0.90 on tiles 1 / 3 / 4 / 5. Only tile 1 improves in the box; tiles 5-7 the standard box is worse than the detector's
(stacked/fused heads) and stay on the detector box (gate fail).

**What this says.** Filling the counter fixes the one far half note whose only fault was the gate not seeing hollow heads (Sean's tile 1) and makes the gate usable on half notes in general (1 -> 113 / 1 -> 69 passes in-staff).
It does not fix the others, whose faults are fusion. +1 on Litolff (not out-of-sample, one head); not a result to flip a default on. Next: the open-ring path needs a real scan example; a fusion-aware fit (stem/partner excluded
from the blob) is what the five remaining hollow heads need.

<!-- brought onto main 2026-10-04 from origin/lane-ledger-template-fix -->
## Geometry head templates: the upright-oval bug and the fixed review sheet (lane-ledger-template-fix, 2026-10-04)

No scoring. GATHER+ADJUDICATE only. Nothing switched on. The sheet is `out/print/ledgers/template_review10.jpg` (checks in `template_review10_checks.json`).

**What was wrong.**
1. `measure_head_tilt._fit_axes` returned cv2.fitEllipse's raw `(width, height)`. For a wide head that pair is (minor, major), swapped. `template_review10._draw_template_outline` drew it as (width, height), so every blue/yellow oval was upright (22 x 29 px at 16 px/space). Fixed: `_fit_axes` now returns (long, short), the same axis `_angle_up_right` measures. This also fixes the slit/outer ratio pairing (slit width was being applied to the head's tall axis).
2. The crop was not centred. The window spanned min/max of staff lines, reference and match, so the head sat wherever those fell. Now a fixed window of +/-2.6 x +/-3.2 spaces around the detector box centre. Box and crop are in the same frame (page px at the record's 600 dpi); no DPI mismatch exists.
3. `head_template.py`'s template BUILDER was already correct. Drawing at tilt 0 is wider than tall, and +N degrees puts the top ink right of centre (`_draw_angle_deg = -tilt` is right). The new test for it passes unfixed. The test that went RED on the unfixed tree is `test_fit_axes_reports_long_then_short_matching_tilt_axis`. Added `head_template.geometry_outline_poly` so the sheet draws with the matcher's own convention.

**Tilt convention.** Checked by drawing known ellipses at -30/0/+30 with cv2.ellipse and re-fitting: `_angle_up_right` returns +29.8/0/-29.8, and the top ink lies right of centre for the positive one. The convention was NOT flipped, so ~10 / 35 / 26 degrees mean what they said. Caveats: IQRs are very wide (Litolff filled -2..43, Brahms filled 5..66), so the median is a weak summary; and the measured Litolff outer axes (22 x 29 px) exceed 1.3 x 1.0 spaces (21 x 16 px at 16 px/space), so the fit probably includes stem/neighbour ink. The sheet draws the 1.3 x 1.0 geometry, not the measured axes.

**Self-check (pixel measurements, 10 tiles; first 3 shown).** The red box is on ink (fraction of the box that is ink): 0.84 / 0.73 / 0.79; ink centroid within 2 px of the box centre. Template ink overlap (fraction of the oval that is ink / fraction of in-box head ink the oval covers): 0.92 / 0.66, 1.00 / 0.66, 1.00 / 0.73. Across all 10 the oval-in-ink range is 0.52-1.00. The weak tiles are glyph/1/0/11/2/3 (0.52, ink-box merge) and glyph/0/0/0/6/20 (0.70). Oval 20 x 16 px at tilt 10 degrees (wider than tall), with top-most point 0.5-1.3 px right of centre. Brahms: 40 x 34 px at 26 degrees, top-most 3.8-4.5 px right of centre.

**Caveats for the reader of the sheet.** Orange lines are rows of thin horizontal ink beside the head, so they can include non-rung strokes (slurs, beam tails). The "template says" text uses the matcher variant; where its height implies the other parity the tile says "disagree". Round 8 is `reader_absolute_position(four_causes_cd=True)`; "abstained" means it returned None.

### Review-sheet fixes after the manager's read (lane-ledger-template-fix, 2026-10-04, second pass)

Still no scoring. Sheet: `out/print/ledgers/template_review10.jpg`; the three heads the manager named, plus the Brahms pair, are on `template_review10_controls.jpg`; numbers in `template_review10_checks.json`; diagnostics by `template_height_diag.py`.

1. **Orange lines were a generic thin-row scan (slurs matched).** Now staff lines come from `score.frame_lines_for_head` (`local_staff_lines` at the head's x) and ledgers from `combined_scorer._rungs_y_for_head` = `ledger_grid.measure_ledger_rungs(..., four_causes_cd=True)` with round 8's exact arguments (other noteheads + accidentals excluded). Ledgers are drawn box +/- 0.6 sp. Self-check: dark-pixel fraction within +/-1 px along each line (staff lines across the tile outside the box; ledgers over the 0.25 sp just outside each box edge, best side counts). 3 of 16 tiles report a ledger under 0.6 (all exactly 0.5, i.e. a stub shorter than the check zone): `glyph/3/0/8/6/10`, `glyph/1/0/9/14/8`, `glyph/1/0/9/3/5` (left 0.5, right 0.0). They are reported, not hidden.
2. **"round 8: abstained" on every tile was my bug.** I passed every detection as the "other noteheads" set; `score_doc` passes only `_notehead_boxes_by_page`. Now called exactly as `score_four_causes_cd.py` does. Control: the 5 Litolff abstains match `score_doc(four_causes_cd=True)` (3/0/7/0/7, 3/0/7/2/4, 3/0/8/6/10, 3/0/8/9/0, 3/0/9/3/5); Brahms decides 11 of 11.
3. **"on a line ... disagree".** Not a matcher bug. The matcher's answer is its variant (`decide_head_position_from_template`: on_line -> "on"). The "height implies parity" came from my label extrapolating the staff grid (`lines[0] + step * spacing/2`) out to heads 6-10 steps away, where a 5% scan spacing error flips parity -- exactly what DECISIONS 2026-10-01 forbids. Now ONE answer per tile: the variant, with the step read off the MEASURED ladder (staff lines + round 8's rungs). A flag says when the matched oval is more than 0.25 sp off its line, or no measured line is within half a space.
4. **Why three ovals sit off the head.** The matcher is not choosing a height; there is nothing to score. Each of the three detector boxes is a fragment (0.71, 0.35 and 0.65 sp tall; a head is 1.0) that overlaps a real neighbouring notehead box (`glyph/1/0/10/14/1`, `1/0/10/2/2`, brahms `0/0/1/6/1`). The matcher blanks other noteheads' boxes (as round 8 does), which erases the head's own ink: scores are exactly 0.000 at every height for 1/0/9/14/8 and on_line/in_space (1/0/11/2/3, margin 0.066 only on in_space), and flat (-0.05) for brahms 6/20; margins 0.000 / 0.066 / 0.009, so all three are UNDECIDED and the height is simply the box centre. 1/0/11/2/3's ink run extends 1.02 sp above its 5 px box; brahms 6/20's extends 1.60 sp below. Two readings of the same fact: the box, not the template, is off the head. Excluding every detection (the first fixed sheet) vs only noteheads+accidentals changed 1/0/11/2/3's margin 0.030 -> 0.066, nothing else. Not tuned.
5. **Greyscale and references.** Tiles are the real print (bicubic upscale; Litolff and Brahms are bitonal scans so they still look black and white). Population is `score_doc`'s (heads that have a reference), 7 Litolff + 3 Brahms, diversity-bucketed by class/side/parity; the three round-8-undecided heads from the first sheet are kept (5 Litolff heads are undecided in all). Every selected tile happens to be a filled head.

### Round 3: the control first, the shape from the page, the oval placed by search (lane-ledger-template-fix, 2026-10-04)

Still no scoring of any reader. Scripts: `shape_from_page.py` (shape + why the old tilt was noisy), `template_review_r3.py` (sheets + table). Sheets: `out/print/ledgers/template_review_r3.jpg` (12 controls, then the 10 far heads), `template_review_r3_blueonly.jpg` (4 tiles x6, no box/lines); numbers in `template_review_r3_checks.json`, `shape_from_page.json`.

**Measured shape (median of per-head second-moment fits over clean, isolated, in-staff, ON-LINE heads that pass an oval gate; IoU of blob with its own moments-ellipse >= 0.85, area 0.7-1.45 sp^2, long axis 1.0-1.8 sp, solidity >= 0.9).**
- Brahms (Breitkopf): 1.49 x 1.13 sp, tilt 28.2 deg, IQR 25.8-29.9 (n = 133 on-line heads; 256 of 302 isolated filled heads pass).
- Litolff: 1.55 x 0.99 sp, tilt 20.0 deg, IQR 14.4-42.5 (n = 14; only 25 of 113 isolated filled heads pass the gate -- the scan merges heads with lines, and the heads are flat-bottomed lemons, not ovals, so the gate rejects 74 as `not_oval`). Treat Litolff's tilt as weak.
- Hollow heads: 3 (Litolff) and 0 (Brahms) pass; the hollow templates reuse the filled shape and tilt, no slit measured. The old 35 / -7 deg slit numbers stand unconfirmed.
- The old default (1.3 x 1.0) was too narrow on both pages.

**Why the old tilt was noisy (IQR -2..43 on Litolff).** Three causes, in order of size:
1. **It measured heads in spaces, and those are contaminated.** On Brahms the same clean fit gives 28.2 deg (IQR 25.8-29.9) on on-line heads but 7.7 deg (IQR 5.6-9.0) in spaces; Litolff 20.0 on line vs 6.7 in space. In Brahms a head is taller than the gap between two lines, so it touches both, and the blob merges with a line stub top and bottom, which flattens the fitted axis. `measure_head_tilt.summarize` deliberately used in-space heads only ("avoid the bias entirely"); that was the biased half. On the old 1.65 sp window every window's ink touched its edge (223 of 223 Brahms, 24 of 24 Litolff), i.e. the fit never saw a whole head.
2. The stem was removed by blanking whole columns; the stem column's run includes the head, so the head's own edge beside the stem was deleted (and the matcher inherited the same stem mask, which shifts the best match away from the stem side: the "up-left" oval).
3. cv2.fitEllipse on a 20 x 16 px blob is quantisation noise (heads with ecc < 1.15: IQR 12-62 deg). Second moments are an area statistic, and the angle is reported only where ecc >= 1.12.
Fix: line rows removed only outside a nominal oval, stems and remnants removed by an opening (disc 0.42 sp), moments angle, on-line heads only. Mid-range Brahms montage: blobs look like clean ovals; Litolff montage: the +-40 deg tails are line remnants merged with the head.

**Placement.** `match_head_template(dx_range_spaces=0.4, head_ink_mode="opening")` (defaults unchanged). The HEAD term reads ink with stems and line remnants opened away; the LINE term keeps the raw ink.

**Control (12 clean in-staff heads, picked by the shape gate only, 3 on a line + 3 in a space per doc).** Oval vs the head's own ink blob (box +-0.3 sp, staff rows masked outside the oval): median IoU 0.87, median offset 0.06 sp, 2 of 12 MISS (IoU < 0.7 or offset > 0.15 sp), both Litolff. Movement of the oval from the box: max |dx| 0.04 sp, max |dy| 0.11 sp -- on easy heads the box was already right and the search barely moves. Brahms controls 0.87-0.94 IoU, offset <= 0.06 sp. **The control that failed: the variant.** The matcher's on-line / in-space answer agrees with the staff-position parity on only 7 of 12 controls (Litolff: all three on-line heads answered "in space"; Brahms 4 of 6). That is the answer the far-head use depends on, and it is not yet a trustworthy answer on easy heads.

**Far heads (same 10).** Median IoU 0.79, median offset 0.10 sp, 3 of 10 MISS: `glyph/3/0/7/0/7` (IoU 0.61, offset 0.17), `glyph/3/0/0/2/1` (0.62, 0.18; dx +0.38 sp: the search moved it sideways), `glyph/3/0/0/2/9` (0.38, 0.56 sp; the blob there is a head fused to a beam/stem mass, so its centroid is not the head's). Brahms far heads 0.79-0.89. Full per-tile table (IoU with stems opened away in brackets):

label doc subject kind variant dx_sp dy_sp IoU (open) offset_sp
control litolff 3/0/10/2/0 filled in_space 0.00 -0.06 0.78 (0.81) 0.14
control litolff 3/0/5/13/4 filled in_space 0.00 +0.06 0.53 (0.51) 0.23 MISS
control litolff 3/0/7/4/13 filled in_space 0.00 0.00 0.66 (0.67) 0.08 MISS
control litolff 2/0/4/1/3 filled in_space 0.00 +0.06 0.75 (0.79) 0.12
control litolff 2/0/9/15/4 filled in_space 0.00 0.00 0.75 (0.84) 0.12
control litolff 3/0/10/7/1 filled in_space 0.00 -0.06 0.90 (0.87) 0.02
far litolff 3/0/7/0/7 in_space 0.00 +0.06 0.61 (0.63) 0.17 MISS
far litolff 3/0/7/2/4 on_line 0.00 -0.19 0.73 (0.77) 0.10
far litolff 3/0/8/6/10 on_line +0.06 -0.06 0.79 (0.83) 0.02
far litolff 3/0/0/2/1 on_line +0.38 -0.06 0.62 (0.62) 0.18 MISS
far litolff 3/0/0/2/9 in_space 0.00 +0.25 0.38 (0.37) 0.56 MISS
far litolff 3/0/7/2/2 on_line 0.00 -0.19 0.71 (0.72) 0.13
far litolff 3/0/5/2/0 on_line +0.06 -0.19 0.82 (0.85) 0.04
control brahms 1/0/12/3/3 in_space 0.00 0.00 0.87 (0.94) 0.02
control brahms 1/1/0/5/3 on_line -0.04 0.00 0.87 (0.92) 0.05
control brahms 1/1/12/4/0 on_line 0.00 0.00 0.87 (0.92) 0.06
control brahms 1/0/11/2/6 on_line 0.00 0.00 0.90 (0.97) 0.04
control brahms 1/0/2/6/8 in_space 0.00 -0.11 0.92 (0.95) 0.02
control brahms 1/1/11/2/6 in_space 0.00 -0.04 0.94 (0.97) 0.01
far brahms 1/1/0/4/0 on_line -0.04 0.00 0.83 (0.94) 0.07
far brahms 1/1/0/2/4 on_line 0.00 +0.04 0.79 (0.92) 0.09
far brahms 1/1/8/6/0 in_space -0.04 0.00 0.89 (0.89) 0.06

Honest limit: the Litolff plate prints flat-bottomed lemons that merge with the staff lines; a tilted ellipse is a modest fit there (IoU 0.53-0.90). The next candidate is a lemon (an ellipse with a flattened lower edge), not a different tilt.

### Round 4: the lemon shape, and why on-line / in-space failed on easy heads (lane-ledger-template-fix, 2026-10-04)

Still no scoring of any reader. Scripts: `template_review_r4.py` (shape candidates, controls, far heads, sheets), `variant_diag.py` (head term and each line band per control, `staged|joint`, `tol`, `ncc|coverage`), `shape_from_page.py` (adds `mean_shape`, the lemon gate). Sheets: `out/print/ledgers/template_review_r4.jpg`, `template_review_r4_blueonly.jpg`; numbers `template_review_r4_checks.json`.

**1. Litolff shape.** Three candidates, each scored on the 6 Litolff controls (oval vs the head's ink blob): A oval (round 3: 1.55 x 0.99 sp, 20 deg) mean IoU 0.827; B oval with the lower edge cut flat (1.56 x 1.06 sp, 36 deg, flat fraction 0.9 fitted to the mean shape, 31 clean on-line heads; IoU 0.888 against the mean shape) 0.815; C mean shape of 33 clean on-line heads aligned on measured centroids (area 1.24 sp^2) 0.790. The plain oval stays for Litolff; neither lemon helps on the controls (the lemon gate drops the oval test, keeps area / size / solidity >= 0.88). Brahms, 6 controls: A 0.887, B (flat 0.95) 0.908, C mean of 134 heads 0.915 -- C is used (a small gain, n = 6, but the mean shape is a measured head and visibly fits: see the blue-only sheet). Litolff's remaining misses are where the head is fused to a line or stem, not the outline.

**2. Why on-line / in-space failed on easy heads (7 of 12 agreed).** Four causes, in the order found (`variant_diag.py`, before = `joint ncc`):
1. The in_space template put its two bounding lines at +-0.99 sp from the head centre (the bands sat at the window's top and bottom edges). The lines that bound a space are +-0.5 sp away; +-1 sp is where an ON-LINE head's neighbouring staff lines are. Every on-line head fired the in_space bands (e.g. Litolff `3/0/7/4/13`: in_space band 0.39 vs on-line line term 0.19; Brahms `1/0/12/3/3` band 0.40). The test that encoded this ("a ledger touching only its top is ONE space from the head's centre") had the geometry wrong and was corrected, as was the exemplar fixture's in_space exemplars.
2. The head term differed between the variants (the template's line bars sat inside the head mask), so the answer was not decided by line evidence alone. The variants now share one head image.
3. The head's POSITION and the line variant were chosen jointly under a shift penalty, with boxes up to 0.25 sp off the head; the winning variant followed the box. Now `decide="staged"`: position from the variant-free head template, then each variant scored at that position (+-0.15 sp, no penalty).
4. The line term was a correlation over a thin band. On a thick scanned line the band is solid ink, the correlation has zero variance and scores exactly 0.0 (every Litolff line term was 0.00-0.46, margins 0.002-0.08). It is now ink coverage of the template's own line rows (`line_term="coverage"`), margins 0.17-0.24.
Tests (RED first): the synthetic coin-flip case with 8 px lines gave margin 0.000 and answered "on" for every in-space head (red), then green with coverage; the 3-px staff case had margins 0.01-0.02 before the geometry fix (0.1 after, enforced >= 0.08).
Control selection now also requires the print to agree with the staff position (the head's ink centroid within 0.2 sp of a line or space middle, and which of the two matches the position's parity): the old control `2/0/9/15/4`-like cases that sat 0.3 sp off both were not clean.

**Result on the 12 controls: 12 decided (margin >= 0.08), 11 agree with the staff position, 1 disagrees.** The one: Litolff `3/0/10/4/1` (position 1, in a space) answers on_line (margin 0.14). The head is 1.1 sp tall in a 1.0 sp space, the top staff line lies wholly inside its top, and the head-only template is pulled 0.16 sp up by that line ink, which puts the line inside the on-line band. The Litolff headline remains weak; Brahms is 6 of 6.

**3. Far heads (same 10), no score.** Only 1 of 10 clears the 0.08 margin (`3/0/5/2/0`: on a line, reference on a line, round 8 on a line). Variant (margin | reference parity | round 8): `3/0/7/0/7` on_line (0.013 | space | abstains), `3/0/7/2/4` on_line (0.017 | on | abstains), `3/0/8/6/10` on_line (0.031 | on | abstains), `3/0/0/2/1` on_line (0.065 | on | on), `3/0/0/2/9` in_space (0.008 | space | on), `3/0/7/2/2` on_line (0.001 | space | space), `3/0/5/2/0` on_line (0.116 | on | on), Brahms `1/1/0/4/0` in_space (0.070 | space | space), `1/1/0/2/4` on_line (0.073 | on | on), `1/1/8/6/0` in_space (0.038 | space | space). The far heads' line evidence is short stubs, so margins are small: the matcher mostly says "cannot tell", which is the right answer to give rather than a guess.

**4. Pixel self-check (oval vs ink blob, box +-0.3 sp, line rows masked outside the oval).** Controls: median IoU 0.90, median offset 0.06 sp, 1 of 12 MISS (Litolff `3/0/7/4/13`, IoU 0.66: a head merged into a thick line). Far heads: median IoU 0.74, median offset 0.13 sp, 4 of 10 MISS (`3/0/7/0/7` 0.61/0.17, `3/0/7/2/4` 0.72/0.19, `3/0/0/2/1` 0.62/0.18, `3/0/0/2/9` 0.42/0.49). Brahms far heads 0.74-0.93.

### Round 5: "Brahms 3 and 5 are not noteheads" (lane-ledger-template-fix, 2026-10-04)

Still no scoring of any reader. Scripts: `non_head_diag.py` (wide crops + detector boxes), `symbol_gate_report.py` (what the rule removes, seeded contact sheets), `shape_from_page.symbol_gate`, `template_review_r5.py` (sheets). Sheets: `out/print/ledgers/template_review_r5.jpg`, `template_review_r5_blueonly.jpg`; wide crops `out/print/ledgers/nonhead/glyph_1_1_12_4_0_wide.jpg`, `glyph_1_0_2_6_3_wide.jpg`; contact sheets `symbol_gate_brahms1.jpg`, `symbol_gate_beethoven5.jpg`.

**1. The two heads, from the print (gather dpi 600, 2x crop, whole neighbourhood, all boxes drawn).** I could not find another symbol they are part of; on the print both read as ordinary filled noteheads. This needs Sean to circle what he sees.
- `glyph/1/1/12/4/0`: detector `noteheadBlackOnLine`, score 0.82, 38 x 32 px (1.38 x 1.16 sp). A black oval sitting on a ledger line under the upper staff of a system, the second head of a beamed pair (stem down on its left, beam below), ordinary clef and rests to the right. Overlapping detector boxes: `tie` 0.29 (1 px of overlap), `ledgerLine` 0.37 and 0.31 (13x5 and 38x6 px). No rest, flag, clef or dynamic box touches it. Stem run on the print 3.5 sp.
- `glyph/1/0/2/6/3`: `noteheadBlackInSpace`, score 0.82, 38 x 30 px. A black oval in a space of the middle staff, stem up on its right. Overlapping boxes: only the `staff` box 0.69 (it lies inside the staff). Stem run 3.2 sp.
If Sean means different tiles, the Brahms control order on the r4 sheet was `1/0/12/3/2, 1/0/9/6/0, 1/1/12/4/0, 1/0/11/2/6, 1/0/2/6/3, 1/1/11/2/5`; the r5 order is the same except the sixth (`1/1/11/1/6`).

**2. How they got through, and the tighter rule.** The old gate asked only for a detector `notehead*` box with an oval-shaped, well-sized blob and no other NOTEHEAD/accidental/rest box within a space; a box overlapping a clef, dynamic or flag was never looked at, nor was the detector's own confidence, nor a stem. The convention now (`symbol_gate`, no subject ids): detector score >= 0.5; no rest / clef / dynamic / accidental / fermata / ornament / ottava / time / key box overlaps more than 20% of the head's box; a FILLED head must carry a stem on the print (a vertical ink run 2.0-6.5 sp touching its left or right edge and reaching >= 1 sp past the head; hollow/whole are not asked). A flag box is deliberately NOT a disqualifier: the first version of the rule included it and removed 15 real stem-down flagged Brahms heads (contact sheet showed it) because the flag box overlaps the head's box on every such note.
- Brahms mean-shape source (filled, on-line, lemon-gated): 134 -> 133 (1 removed, no stem). Control pool: 256 -> 251. Both of Sean's heads PASS the rule (detector 0.82, stems of 3.5 and 3.2 sp, no rest/flag/clef/dynamic box on them).
- Litolff mean-shape source: 33 -> 19 (14 removed: 7 detector score < 0.5, 12 no stem found, 1 overlapping a dynamic `f`). Control pool 25 -> 15. In the seeded contact sheet (all 14 shown) about 8 are flat slivers or fragments inside `ff`/`sf` dynamics and rests (real contamination), about 5 look like genuine heads whose stem the run test did not find (`3/0/7/14/1`, `2/1/8/5/1`, `2/1/8/5/5`, `3/1/7/17/0`, `2/0/2/11/3`): the rule over-removes there, which is the safe direction for a template source. The 19 kept Litolff heads (all shown) and 24 of the 133 kept Brahms heads (seed 5) all look like real heads.
So the Brahms mean shape was NOT contaminated by non-heads in any way I can show; it is rebuilt from 133 heads and is the same to three decimals (1.490 x 1.131 sp, 28.1 deg).

**3. Controls and line/space, re-run.** Re-picked Brahms controls: `1/0/12/3/2, 1/0/9/6/0, 1/1/12/4/0, 1/0/11/2/6, 1/0/2/6/3, 1/1/11/1/6` (the same two heads are still in). Candidate shapes, 6 controls each (mean IoU): Litolff oval 0.837 (now 1.59 x 1.05 sp, 29 deg from only 8 clean on-line heads: weak, IQR 19.7-44.7), flat 0.828, mean 0.813 -> oval; Brahms oval 0.892, flat 0.912, mean 0.915 -> mean shape. Line/space on the 12 controls: 11 decided (margin >= 0.08), all 11 agree with the staff position, 1 undecided (Litolff `2/0/9/15/4`, margin 0.038); no decided-wrong (r4 had one). Pixel check: controls median IoU 0.89, offset 0.06 sp, 0 of 12 MISS; far heads median IoU 0.81, offset 0.10 sp, 3 of 10 MISS (`3/0/7/2/4` 0.74/0.19, `3/0/0/2/1` 0.64/0.18, `3/0/0/2/9` 0.43/0.49).

**Far heads, no score (variant, margin | reference parity | round 8):** `3/0/7/0/7` in_space 0.019 | space | abstains; `3/0/7/2/4` on_line 0.018 | on | abstains; `3/0/8/6/10` on_line 0.021 | on | abstains; `3/0/0/2/1` on_line 0.060 | on | on; `3/0/0/2/9` in_space 0.007 | space | on; `3/0/7/2/2` on_line 0.005 | space | space; `3/0/5/2/0` on_line 0.146 | on | on (the one decided); Brahms `1/1/0/4/0` in_space 0.070 | space | space; `1/1/0/2/4` on_line 0.073 | on | on; `1/1/8/6/0` in_space 0.038 | space | space.

### Round 6: centring the oval (lane-ledger-template-fix, 2026-10-04)

Still no scoring of any reader. Code: `head_template.refine_oval_centre` and `match_head_template(refine_centre=False, refine_mode="iou", refine_min_gain=0.0)`; scripts `template_review_r6.py` (before/after on the same tiles, sheets), `refine_off_identity.py`. Sheets: `out/print/ledgers/template_review_r6.jpg`, `..._blueonly.jpg`, `..._movers.jpg`; numbers `template_review_r6_checks.json`.

**Method.** After the staged position search, the oval (the template's own head mask) is slid sub-pixel (0.5 px steps, +-0.25 sp in dx and dy) to maximise its IoU with the ink under it, where that ink has stems and thin remnants removed by the opening, other noteheads' boxes blanked, and every staff / ledger row (a row mostly ink in the strips beside the head) cleared outside the candidate oval; ink in a window just larger than the oval only, so a fused neighbour adds to the union and is not a reason to move. A move needs an internal IoU gain of at least `min_gain` (0.05 in the sheets) or the oval stays. An edge-based score (coverage plus the fraction of the oval's outline on the ink's boundary) was also tried and is no better (same number of tiles made worse, one more moved > 0.15 sp), so the IoU score is the default.

**Tests (RED first):** `refine_oval_centre` did not exist (AttributeError / TypeError for `refine_centre`). Now green: a synthetic head with a stem and a line through it, oval started 0.2 sp off in five directions, ends 0.025 sp from the true centre (0.5 px); a head fused to a neighbour started 0.1 sp off toward it ends at the same point; and with `refine_centre` off the match dict is exactly the same and has no `refined` key. **Default off is bit-identical to 56f8c66c** on 72 calls (12 controls + 6 isolated heads per document, 3 configurations): `refine_off_identity.py`.

**Before vs after (22 tiles; "offset" = round-3 measure, oval centre vs the centroid of the head's ink; "bbox" = independent: midpoint of the head's leftmost/rightmost ink columns and top/bottom rows at the head's own width, stems opened away, same clip and ink for before and after).**
- The nudge does nothing where it matters least: 11 of the 12 controls and 3 of the 10 far heads did not move (gain below 0.05). All six Brahms controls were already within 0.09 sp (<= 2.5 px) of their ink centre; a move there is below one pixel of quantisation and the two measures disagree in sign at that size.
- Moved (8 tiles):
  - Better by both measures: Litolff far `3/0/7/2/4` (nudge +0.04,-0.15; offset 0.19 -> 0.04, bbox 0.133 -> 0.029, IoU 0.74 -> 0.76); Litolff far `3/0/0/2/9` (+0.23,-0.12; offset 0.49 -> 0.33, bbox 0.36 -> 0.127, IoU 0.43 -> 0.54); Brahms far `1/1/0/2/4` (+0.10,-0.05; bbox 0.088 -> 0.041, IoU 0.74 -> 0.78, offset unchanged 0.10).
  - Mixed: Litolff control `2/0/9/15/4` (-0.22,+0.22; offset 0.09 -> 0.06, IoU 0.78 -> 0.87, but bbox 0.119 -> 0.249).
  - Moved the WRONG way by both measures: Litolff far `3/0/0/2/1` (+0.10,-0.09; offset 0.18 -> 0.28, bbox 0.09 -> 0.20, IoU 0.64 -> 0.61); Litolff far `3/0/7/2/2` (+0.16,-0.25; offset 0.10 -> 0.18, bbox 0.10 -> 0.26, IoU 0.80 -> 0.74); Brahms far `1/1/0/4/0` (-0.03,+0.08; offset 0.02 -> 0.06, bbox 0.03 -> 0.06, IoU 0.91 -> 0.80).
  - Moved more than 0.15 sp: `2/0/9/15/4` (0.31 sp total), `3/0/7/2/2` (0.30), `3/0/0/2/9` (0.26), `3/0/7/2/4` (0.15 in dy).
- Ungated (min_gain 0) the nudge moves nearly every tile by 0.01-0.07 sp and makes 8-9 tiles slightly worse by one measure or the other; the 0.05 gate removes those no-ops.
**Reading:** the nudge is not a fix. The three tiles it makes worse are the ones whose head is fused to a stem, beam or neighbouring head, where the ink the IoU sees is not the head (the same fused ink the independent measure also sees); on clean heads there is nothing to nudge. It stays OFF by default. If Sean's "slightly off centre" is the Litolff far heads, the nudge helps `3/0/7/2/4` and `3/0/0/2/9` and hurts `3/0/0/2/1` and `3/0/7/2/2`.

**Pixel-check of the drawing** (`DRAWING CHECK` in the run output and `drawing_check` in the json): the six mover tiles' solid and dashed outlines, redrawn on blank canvases, have centroids within 0.5 px of the tile coordinates of the stated centres (x6, so 0.08 px of the page), and the separation between the two outlines equals the stated nudge within 0.1 px (e.g. `2/0/9/15/4`: 29.7 vs 29.8 px).

### Round 7: stem side, ledger-constrained height, and the "different sizes" drawing question (lane-ledger-template-fix, 2026-10-04)

Still no scoring of any reader. Code: `head_template.find_stem_side`, `refine_oval_centre(stem=, max_shift_y_spaces=)`, `match_head_template(ladder_ys=, refine_stem=)` (all default off / unchanged; the r5 configuration is bit-identical). Script `template_review_r7.py`; sheets `out/print/ledgers/template_review_r7.jpg`, `..._blueonly.jpg`, `..._movers.jpg` (round 5 dashed vs round 7 solid); numbers `template_review_r7_checks.json`.

**Drawing / size.** I could not reproduce a size difference between the dashed (before) and solid (after) outlines. Both come from the same function at the same scale; I now fit an ellipse to every drawn outline (`size_check`, or extents against the mask for the Brahms mean shape) and compare it to the template's axes in tile pixels: the largest deviation over all 22 tiles, for either outline, is 2.2 px at x3-x6 (Brahms mask rounding) and 0.4-0.9 px for the Litolff ovals; before and after agree with each other to the same tolerance. On `2/0/9/15/4` and `3/0/7/2/2` specifically: 0.8 and 0.9 px. The look of different sizes on the round-6 movers sheet is, as far as I can measure, the dashes (the dashed arc disappears under the solid one where they overlap, so a displaced pair reads as one smaller than the other). The drawing check also reports centroid error (<= 0.5 px) and the separation of the two outlines against the stated nudge (within 0.1 px).

**1. Stem.** `find_stem_side` reads the stem from the ink (a vertical run of 2.0-6.5 sp through the head's row, touching its left or right edge, reaching >= 1 sp past it) and applies the engraving convention (stem up = right, stem down = left; a find that broke it would be flagged, none did). Sides found on all 22 tiles (side/direction): Litolff controls all right/up; Litolff far `3/0/7/0/7` left/down, `3/0/7/2/4` right/up, `3/0/8/6/10` right/up, `3/0/0/2/1` left/down, `3/0/0/2/9` right/up, `3/0/7/2/2` right/up, `3/0/5/2/0` right/up; Brahms controls `1/0/12/3/2`, `1/0/9/6/0`, `1/1/12/4/0`, `1/0/11/2/6` left/down, `1/0/2/6/3`, `1/1/11/1/6` right/up; Brahms far `1/1/0/4/0` left/down, `1/1/0/2/4` left/down, `1/1/8/6/0` right/up. The nudge then ignores stem ink in the stem's columns (+2 px) that lies OUTSIDE the candidate oval. (My first version also ignored the oval's own pixels in the band; it left the stem side unconstrained and made two controls worse, so it was changed.) On clean synthetic heads the exclusion makes no difference (the overlap score was already robust to a stem); it is tested as an invariance: the refined centre with the stem excluded equals the one on the same scene with no stem.

**2. Ledgers orient the height.** `ladder_ys` = round 8's measured rows (`combined_scorer._rungs_y_for_head`, four-causes args, plain walk) plus the local staff lines. The head's centre is allowed only ON a found row, midway between two adjacent found rows (gap <= 1.6 x the median gap), or half a measured gap beyond the outermost row, within +-0.1 sp (>= 1 px) of one; the horizontal nudge follows with dy fixed. **This makes the template's height a CONSEQUENCE of the ledger read: with `ladder_ys` the template can no longer serve as independent evidence for line-vs-space. It is a placement / boxing tool (useful for Sean's cause A, short boxes, and the tied-dyad split), not a second witness.** An attempt to pick among the candidate heights by oval/ink overlap instead of the head-template score jumped one head 1.09 sp onto the wrong candidate and made 6 of 10 far heads worse; it is removed.

**3. Self-check, vs round 5 (22 tiles).** 14 tiles are unchanged (11 controls with a nudge < 0.05 gain, 3 far). Better than round 5: Litolff far `3/0/7/2/4` (offset 0.19 -> 0.05, bbox 0.13 -> 0.06), `3/0/0/2/9` (offset 0.49 -> 0.29, IoU 0.43 -> 0.56), Litolff control `2/0/9/15/4` (IoU 0.78 -> 0.94, offset 0.09 -> 0.02, but independent bbox 0.12 -> 0.19). WORSE than round 5: Litolff control `3/1/1/4/2` (offset 0.04 -> 0.11; independent bbox 0.065 -> 0.04, IoU 0.76 -> 0.77, so the two measures disagree), Litolff far `3/0/8/6/10` (moved +0.13,-0.13; offset 0.05 -> 0.11, bbox 0.01 -> 0.17, IoU 0.81 -> 0.76) and `3/0/7/2/2` (moved +0.19,-0.25; offset 0.10 -> 0.16, bbox 0.10 -> 0.27, IoU 0.80 -> 0.69). Moved more than 0.15 sp: `2/0/9/15/4`, `3/0/7/2/4`, `3/0/8/6/10`, `3/0/0/2/9`, `3/0/7/2/2`. The Brahms controls and the three Brahms far heads are unchanged within 0.05 sp (one bbox 0.012 -> 0.036). Line/space: the variant answers match round 5 on 9 of 10 far heads; `3/0/7/2/2` changes from on_line to in_space (reference: in a space) because its height moved to a different ledger candidate, which is exactly the dependence above.

## lane-frame-drop-investigation (2026-10-04): why the far-head reader reads 38/41 on the scorers' raster and 31/41 on the gather's

STAGED reader (`far_head_reader.FarHeadPage`, arm E3), LEGACY nothing. Litolff p3, the 41 far heads of the 2.44c truth set (3/0/0/6/2 against Sean's -6). Scripts: `frame_drop_arms.py`, `frame_drop_experiments.py`, `frame_drop_offsets.py`, `frame_drop_sweep.py`, `frame_drop_probe_row.py`, `frame_drop_jut.py`, `frame_drop_pairs.py` (all read-only on the shared records; no gather run). Crop: `out/print/ledgers/frame_drop_pairs.png`.

**Reproduced.** Scorer `score_combined_1004.py` E3, page 3: 37/3/1 as scored, 38/2/1 by Sean's -6. The same reader on the same record boxes, undeskewed fitz raster (arm A): 37/3/1, 38 by Sean. On the gather's deskewed raster (arm B): 31/8/2 (the wiring lane said 30; one head of difference, probably its shape pool). Brahms p1 control: skew 0.0, A = B = 11/0/0.

**Verdict: hypothesis 3, with the cut-off of hypothesis 1 as the mechanism. Not hypothesis 2.**

1. *The straight page does not read better.* Arm A2: the same undeskewed raster, but the boxes and staff lines mapped into ITS frame (inverse of the deskew rotation, so frames agree): 31/9/1. B: 31/8/2. The 38 needs the frames to DISAGREE: the scorers laid deskewed-frame boxes on an undeskewed raster, so each box sits 0.1-6.6 px from its head (median |dx| 1.4, |dy| 1.8; ink-in-box fraction 0.78 against 0.83 on B).
2. *The resampling is innocent (H2).* Deskewing the fitz gray ourselves with nearest / cubic / lanczos: 30 / 29 / 30, against bilinear (the gather) 31. Staff-line and ledger thickness are not the lever; the lines are re-measured in each raster at the head's x anyway.
3. *The mechanism.* The "ledger passes through the head" evidence (`head_middle_rung_evidence`) needs the head's connected ink run to stick out of the USED BOX by `THROUGH_RUNG_STUB_PROBE_SPACES` = 0.25 sp = 3.9 px on one side. With the box centred on the head the overhang is 3.3-3.9 px each side (5 flipped heads measured: B 3.3/3.5, 3.1/3.9, 2.9/3.9 ...), just under the cut. In A the box is 1-7 px off its head and one side's overhang becomes 5.5-13 px: the rule fires, the head reads ON the line, and Sean's reference agrees. Sweeping the own box by (dx, dy) on B: 31 right at (0,0), 36 at dx -2, 22-27 beyond +-4 px; on A: 38 at (0,0) and 24-35 for any shift. Both arms live on a 2 px cliff, and the cut (0.25 sp, written on these same 44 heads in the mismatched frame) is on the wrong side of it for correctly placed boxes.
4. *Where the cut should be.* Sweep of the stub threshold, right count: 0.25 sp A 38 / B 31 / A2 31; 0.20 sp 38 / 34 / 34; 0.15 sp 38 / 37 / 37; 0.10 sp 37 / 37 / 37; 0 sp 31 / 31 / 33. Brahms p1 (11 heads): 0.25-0.15 sp 11/0/0, 0.10 sp 9/2/0. So the only value good on both documents is 0.15 sp, the very edge of the Brahms plateau: in-sample again.

**Fix (not built, needs Sean's go):** measure the jut from the head's own ink body, not from the box edge (the box is a detector or template artefact, 2 px of placement noise decides the read), then re-score on both frames; until then do not read the 38/41 as the product's figure, and expect the wired gather to read about 31/41 on Litolff p3 (reach first, rule 5).

**Also measured (side finding, H3 asks for it):** the reader's re-measured staff lines sit ABOVE the dark-band centre: median -1.5 px on the undeskewed raster, -1.0 px on the gather's (99 overlay samples on the 9 tiles); the ledger rows sit +0.5 px (18 measurable of 42 drawn; the rest lie on merged ink or are restored/implied rungs). `_darkest_row` takes the FIRST row of a tied minimum, which on a bitonal thick line is its top edge: a 1-2 px staff-line-vs-ledger offset inside every far-head read, from a third, unrelated cause. Same bias as the earlier "staff lines ~1-2 px above the ink" finding.

**Crop (`frame_drop_pairs.py`):** 9 heads read right in exactly one raster (A right, B wrong: `3/0/0/6/2`, `3/0/0/7/1`, `3/0/7/3/1`, `3/0/7/3/2`, `3/0/7/3/4`, `3/0/7/6/2`, `3/0/9/3/5`, `3/1/0/9/0`; B right, A wrong: `3/0/0/2/4`). Same pixels in both tiles of a pair, 3x nearest, record boxes laid on both. Every drawn row mapped back to its source row (assert, 1/6 px), staff and ledger overlays re-measured against the dark band under them (numbers above).

### Chord-blob split: `3/0/0/2/4` + `3/0/0/2/9` go right (lane-chord-blob-split, 2026-10-04)

READER ONLY, default OFF (pure functions in `tools/omr/annotate/ledger_grid.py`: `chord_blob_cluster`, `chord_blob_extent`, `chord_blob_trigger`, `ledger_juts_in_range`, `split_chord_blob`; called by no product code). Scorer `score_chord_split_1004.py` (arm E4 = E3 + split; control E3 reproduces 40/3/1 and 11/0/0). Tests `test_ledger_chord_blob_split_2026_10_04.py` (RED first: the four fail on `AttributeError` on the unrepaired tree; green after). Crop `out/print/ledgers/chord_split.png` (`crop_chord_split.py`).

**Result.** Litolff E3 40/3/1 -> **E4 42/1/1** (43/0/1 counting `3/0/0/6/2` by Sean's -6); Brahms 11/0/0 -> 11/0/0. `2/4` -6 -> **-7 right**, `2/9` -6 -> **-5 right**. Right heads broken: **0** on both documents. Every other head's read is byte-for-byte the E3 read. Rule 5 caveat: the rule was built on these same two heads (and the 44 around them); the out-of-sample test is a re-gather.

**What the data is, not what the brief said.** `2/4` and `2/9` are not one box taller than 1.6 standard heads: they are TWO detector boxes (1.39 and 1.26 sp tall, centres 0.9 sp apart, 7 px left of the ink) laid over one blob. So the trigger is on the BLOB: the vertical ink run in a narrow band through the heads' own column (stem and ledger stubs are outside the band), over the page-standard head height, > 1.6 (2.48 sp / 1.2 = 2.1 here). Two heads, not three: the run must be <= h + 1.35 sp (`THIRD_STACK_SPACING_RANGE[1]` 1.25 + 0.10 blur). The heads are placed at the blob's two ENDS (top + h/2, bottom - h/2), not mid +- 0.5 sp: on Litolff the printed ledgers run 1.1-1.25 sp apart (here 395.5 and 415.5, 20 px against a 15.75 px space), so the heads are 1.25 sp apart. The ledgers are the printed juts to the right of the column between and under the heads (rows 395.5 and 415.5); only where none is printed is the stacked-thirds midpoint (`third_stack_rung`, reused) inserted, labelled IMPLIED.

**Two things the harness needed.** (a) `measure_ledger_rungs` cannot see both bars of a merged blob: head rows and bars are one contiguous qualifying band and a band yields ONE peak, so the bar through the lower head's foot (415.5) was lost and both heads read one step low (-5/-3, consistent with each other, one ledger short). `ledger_juts_in_range` supplies them; `reader_absolute_position(chord_split_rungs_y=...)` inserts them (`insert_rung`). (b) The partner's box must not be blanked from the subject's ink (its bar is the subject's ledger): the pair's own two entries leave the exclusion list.

**Trigger counts** (split FIRES; gates are cumulative):
| population | raw (ink run > 1.6 std) | + far (centre >= 0.25 sp outside the lines) | + boxes overprint >= 0.2 sp (E4) |
|---|---|---|---|
| Litolff in-staff heads (807) | 191 | 5 | 2 (one pair, `2/1/8/12/0`+`/12/1`) |
| Litolff far heads (44) | 10 | 10 | **2** (`2/4`, `2/9`) |
| Brahms in-staff heads (897) | 178 | 0 | 0 |
| Brahms far heads (11) | 0 | 0 | 0 |
Spurious fires: the raw trigger alone is NOT far-only (191 of 807 in-staff heads: chords, beams and stems in the band); the far gate removes all but 5, the overprint gate all but one real-looking pair at the staff edge (not inspected against the print; counted, not judged). The 8 other far heads that fire raw include `2/1`+`2/3`, `7/2/2`... (right already, two well-formed boxes or one box over one head); without the overprint gate E4raw is the same 42/1/1 (its only difference is the 6 singleton-box fires, which are declined) -- the overprint gate is kept because two standard heads a third apart abut at ~0.05 sp and the pre-set bound is 0.2 sp. Earlier, with a looser separation bound (h + 1.5 sp) `3/0/0/6/1`+`/6/2` split on a different ink structure (centres 1.45 sp apart, both heads hollow) and broke a right head; the 1.35 bound declines it (`separation_not_a_third`). That bound was tuned on this pair: a third falsifier.

**Not solved / named.** A ledger that juts out LEFT only is not seen; a stem-up blob puts the stem in the jut window; a cluster of three heads and the 3-box clusters (`9/2/0`...) are declined, not split; a single detector box over two heads is declined (nothing to assign the second head to).

**Print check.** Crop from the Litolff PDF raster at the gather DPI, local lines drawn, every drawn line re-measured against pixel rows: the two inserted ledgers sit 0.1 and 0.3 px from their ink rows; the five staff lines sit 1.5-1.9 px ABOVE the ink centre -- not this lane's, but a standing offset: over 220 line reads on the 44 far heads the frame sits a median +1.07 px (0.07 sp) above the ink centre on Litolff (+0.65 on Brahms), p10..p90 0.5..1.6. Worth a look before the grid is trusted to 0.1 sp.

## Through-head ledger: the head is ON a thin flat line that crosses it (lane-through-head-on, 2026-10-04)

**Path: the far-head ledger reader (`ledger_grid`, used by the 2.44c truth-set scorers; not wired into LEGACY or STAGED).** Sean on tile 3 `glyph/3/0/8/6/10`: *"Tile 3 is on a ledger line - the first below the staff."* Fix 1 (`near_edge_ledgers`) refuses that rung (`head_body_on_both_sides_of_the_rung`) and it is popped, so the head abstained.

**Rule** (`derive_far_head_step(through_head_on_rung=True)`, default OFF, bit-identical off; pure functions `through_head_on_rung_evidence`, `head_ink_staff_fraction`). Reached only after fix 1 has declined the rung: a thin flat connected jut within [-0.35, +0.60] sp of the staff-side box edge, head body on both sides, and `frac_stf` (staff-side head ink / head ink height, central 60% of the box width) >= 0.245 (the separator measured by `tile3_vs_fix1.py`, branch `lane-tile3-measure`) -> the head is ON that rung (offset 2n, line).

**Scored** (`score_chord_split_1004.py`, arm E5 = E4 + the rule; staff position vs the reference, GATHER+ADJUDICATE only): control E4 reproduces Litolff 42/1/1, Brahms 11/0/0. E5: Litolff 43/1/0 (44/0/0 against Sean's -6 for `3/0/0/6/2`), Brahms 11/0/0. One head changes: `3/0/8/6/10` None -> 10 (right). **0 right heads broken on either document.** On the far heads the rule fires on that one head only (Litolff) and none on Brahms.

**Reach on in-staff heads.** The real reader run over every in-staff head with the rule on vs off (`through_head_census_in_staff.py`): Litolff 807 heads, Brahms 897 -- 0 reads change, 0 reasons name the rule, 0 reader errors. The bare evidence function is NOT safe on an in-staff head: a staff line is itself a thin flat line through the head, and asked of every staff line crossing a box it fires on 215/807 and 396/897 (upper bound printed by the scorer). It must only be called from the far-head rung path, as it is.

**Caveats.** In-sample: one positive head (tile 3), written for it; the 0.245 gate comes from 44 Litolff far heads. The rule is unevidenced on Brahms (no through-head far case there). The head ink is read at the Otsu threshold of the box surround (the measurement script used gray < 140); tile 3 passes on it. Unit test `tools/omr/tests/test_ledger_through_head_on_2026_10_04.py` (run RED first: ImportError on the unrepaired tree).

## lane-jut-from-ink (2026-10-04): measure the ledger's jut from the head's INK, not the box edge

STAGED reader (`far_head_reader.FarHeadPage`), LEGACY nothing. Fixes the cause found by lane-frame-drop-investigation: the "ledger runs through the head" test (`ledger_grid.head_middle_rung_evidence`) needed the connected ink to stick out of the detector BOX by 0.25 sp = 3.9 px; 2 px of box placement decided the read. New keyword `jut_from_ink` (default OFF = bit-identical; also `exclusion_rules(jut_from_ink=...)`), implemented by `_jut_from_head_ink`: take the middle-row ink run through the box's middle column, measure the vertical ink thickness at every column of it, call the outermost columns thicker than a ledger (`LEDGER_THICKNESS_MAX_SPACES`) the head's body, and require the line to run `RUNG_STUB_MIN_SPACES` (0.15 sp, the walk's own stub floor, not fitted) past that. No thick column = body not found = cannot tell (False). The reader (`far_head_reader.EXCLUSION_RULES`) has it ON.

**Scored, CORRECT FRAME only** (the gather's deskewed raster with the record's boxes; scripts `jut_from_ink_eval.py`, `jut_from_ink_flips.py`, `jut_from_ink_crop.py`; read-only on the shared records; staff position vs reference, GATHER+ADJUDICATE only, `3/0/0/6/2` by Sean's -6):

| | box edge (before) | ink edge (after) |
|---|---|---|
| Litolff p3, 41 far heads | 31 right / 8 wrong / 2 abstain | **36 / 4 / 1** |
| Brahms p1, 11 far heads | 11 / 0 / 0 | **11 / 0 / 0** |

Six reads change: `7/1`, `3/4`, `7/6/2`, `8/6/10` (was abstain), `9/0` go right; `6/2` -3 -> -4 (still wrong against Sean's -6). **Right heads broken: 0** on both pages. The stopgap (0.15 sp from the box) read 37; this reads 36 and has no threshold to tune on the box.

**Shift test** (every box moved by -2..+2 px in x and y, 25 shifts, right heads out of 41 / 11): Litolff box edge **28..36** (spread 8), ink edge **33..37** (spread 4); Brahms 10..11 both. The through test itself no longer moves; what remains is other box-based steps (rung walk, far-side rule): shifting dy -2 flips `6/1` and `8/1/3`, dy +2 flips `5/12` and `7/7/0`, in both directions (`jut_from_ink_flips.py`). Not fixed here.

**Crop** `out/print/ledgers/jut_from_ink.png`: the six changed heads, old left / new right, same gather raster and boxes, 3x. Blue = local staff lines, green dashes = ledger rows counted, orange = detector box, yellow ticks = head's ink edge, cyan ticks = ledger end, red/magenta bars = read / reference. Re-measured against pixel rows: staff overlays sit a median 1.0 px above the dark band (n=70), ledger rows +0.5 px (n=6), the known offset, not this change.

**Combined with `origin/lane-through-head-on`** (chord split E4 + through-head rule E5): merged cleanly (FINDINGS only conflicted, both kept); both stay OFF and unwired in the reader. The E5 rule's only gain (`8/6/10`) is already read right by the ink jut, so wiring it moved nothing (36/41 either way, Brahms 11/11): not wired (rule 5). E4 (`2/4`, `2/9`) needs a chord-cluster hook in `FarHeadPage.read`, which is not a small step: skipped.

**Caveats.** In-sample (the 41 are the heads the rule was looked at on); the real out-of-sample test is the re-gather. Tests `test_ledger_jut_from_ink_2026_10_04.py` run RED on the unrepaired tree (8 failures: no keyword), green after.

## lane-farhead-note-first (2026-10-05) -- the far-head reader in Sean's ORDER (STAGED reader, `note_first`, default ON in `far_head_reader`)

**Order (DECISIONS 2026-10-05).** (1) the staff's edge, local at the head's x; (2) the NOTE first: a thin line through its middle (jut-from-ink line row, else a walk rung within 0.30 sp of the box middle, else the far-side rule) = ON it; else a walk rung on the box's STAFF-SIDE edge (-0.40..+0.60 sp; <= 0.20 sp inside = touching, farther in needs the near-edge / through-head evidence) = the SPACE beyond it; none -> abstain (`no_line_at_the_note_box`, `no_rungs`, `line_at_the_box_not_a_ledger_for_this_head`); (3) count the ledgers strictly between edge and that line from the walk's rungs; every gap of the chain edge -> ledgers -> line must be 0.7..1.5 sp (the ledgers' own pitch, Litolff ~1.1-1.3, NOT the staff spacing: a total-vs-staff-spacing test broke a right head); a gap above 1.5 gets a relaxed look (`find_rung_in_gap`), else `count_does_not_fit`; (4) position = edge + 2k (+1 for the space). Code: `ledger_grid.derive_note_first_step` (+ `find_note_line`, `count_ledgers_between`, `refine_line_on_flanks`), called from `far_head_reader._read`; `READER_KEYWORDS["note_first"]=False` is the run-2 reader, bit-identical.

**Control (deskewed gather frame, `farhead_note_first_eval.py`).** Run-2: Litolff 37 right / 3 wrong / 1 abstain of 41, Brahms 11/0/0. Note-first: Litolff 39/0/2, Brahms 11/0/0; 0 right heads broken. Changed: `3/0/7/3/1` and `3/0/7/3/2` wrong -> right (-5 -> -6: a ledger through the box middle, hidden by the head); `3/0/0/6/2` wrong -> abstain (`count_does_not_fit`, gaps 0.86 / 1.78: a rung is missing between). The middle-band rule and the 1.5 gap max were set after seeing these heads: IN-SAMPLE.

**Out-of-sample, no re-gather** (overnight `...20261004-farhead-all` records, read only, raster re-rendered in the gather frame, page shape pooled over the document where a page has < 8 clean heads; `farhead_note_first_oos.py`, per-head rows in `farhead_note_first_oos_{litolff,brahms}.json`):
- Litolff p4-16: 3,829 far heads; decides 1,763 (46%), abstains 2,066: count_does_not_fit 909, no_rungs 692, no_line_at_the_note_box 408, line_not_a_ledger 44, line_not_beyond_staff 13. Old reader on this tree decides 2,577. Agrees with run-2 on 1,489 of 1,635 both decide (91%); with geometry 1,052/1,763 (60%) vs old 920/2,577 (36%).
- Brahms p2-26: 8,479 far heads; decides 3,864 (46%), abstains 4,615: count_does_not_fit 2,386, no_rungs 1,072, no_line_at_the_note_box 1,061, other 96. Agrees with run-2 on 3,476/3,753 (93%); geometry 3,576/3,864 (93%) vs old 3,544/6,227 (57%).
- Of 6 `count_does_not_fit` crops looked at: 2 are stacks whose middle ledger is hidden by merged heads (honest abstain), 4 are heads of the NEIGHBOUR staff read against this staff's edge (one 3.6 sp gap, no ledgers): abstaining is right. Agreement with geometry is a signal, not a score; nothing here is a truth.
- Weakest rung: `staff_side_edge` (a touching walk rung accepted without ink evidence at the box edge; 617 Litolff / 1,429 Brahms decisions) -- the walk's row can be the head's own bottom edge. Kept because requiring evidence broke 5 right in-sample heads; Sean's sheet should judge it.

**Sheet:** `out/print/ledgers/note_first_sample.png`, 12 seeded (20261005) random out-of-sample decisions, numbered, words under each. Line re-measure against pixel rows (flank columns 0.1-1.0 sp beside the box): 14 of 30 drawn lines within 2 px of an ink row, 2 off by 2.5 and 3.0 px (tile 3 staff edge, tile 12 ledger 1), 14 have no full stub beside the head to measure (captioned). NOT yet adjudicated by Sean.

Tests: `test_far_head_note_first_2026_10_05.py` RED (11 failed) on the unrepaired tree, green after; two old-path wiring tests now select `note_first=False`. Fast tier 4,473 passed; `staged.check` TOTAL 250 before and after.

## lane-ledger-not-text (2026-10-05) -- text ink is not a ledger (STAGED far-head reader, `READER_KEYWORDS["ledger_not_text"]`, default ON, note-first path only)

**Sean (DECISIONS 2026-10-05):** tile 12 of `note_first_sample.png` (Brahms `glyph/5/0/6/3/2`) counted the "cre" of a crescendo as ledger 1. **What the record holds:** no detector box on that text (the Brahms record has `dynamicF/P/M/S/Z` and 2 hairpins, no crescendo word, no direction-text quantity), so the record's boxes alone cannot catch it. **Rule** (`ledger_grid.ledger_candidates_not_text`, applied to the rungs COUNTED between the edge and the note's line and to a rung the relaxed gap look finds; never to the note's own line): a rung is text where its ink is TALL (median vertical run over the columns within 1.2 sp of the head holding ink at the row >= 0.5 sp; a ledger stays under 0.4) AND either a `dynamic*/text/letter/lyric/tempo` box lies across it or its row is not one continuous stroke (< 0.60 of those columns inked). The cre row: median 0.66 sp, continuity 0.52. Cutoffs set after seeing it: IN-SAMPLE.

**What failed first (kept, because it is the lesson).** `rung_is_thin_and_flat` at the head column: 6 right Litolff heads broken (a chord neighbour's ink on the row is 21 px against a 5.5 px cap). A text box alone, or continuity alone: out of sample 50 changed decisions, and the crops showed real thin ledgers refused under false `dynamic` boxes on Litolff. Tall ink is the term that separates the letters from the lines.

**Control** (deskewed gather frame, `ledger_not_text_eval.py`): Litolff 39/0/2 and Brahms 11/0/0, identical before and after; 0 right broken. Tile 12 -> abstains (`count_does_not_fit`, gap 2.06 sp: the text rung is gone and the relaxed look finds no line).

**Out of sample** (the 10-04 run-2 records, no re-gather, `ledger_not_text_oos_{litolff,brahms}.json`, `ledger_not_text_causes.py`): of 12,308 far heads, 18 change (Litolff 5, Brahms 13): 14 decided -> abstain, 4 abstain -> decided (a text rung out of the way lets the count fit; 3 of the 4 agree with geometry, Litolff `6/1/1/11/1` reads -2 against geometry -4). Of the 14 removed decisions 11 disagreed with geometry and 3 agreed (right heads lost). Refused rungs: Litolff 130, Brahms 566 across all decisions, most never change an answer.

**Sheet:** `out/print/ledgers/ledger_not_text.png` -- 12 of the 18 (tile 1 is Sean's crescendo, the rest seeded 20261005); red dashes = the rejected rung, green = ledgers still counted, red solid = the note's line, blue = the staff edge; words before and after. Rejected rungs on the sheet run through "cre", two "sf" and an "f" (text, correct), stems and a clef scroll. Line re-measure against pixel rows: 21 of 42 drawn lines within 2 px of a flanking ink row, 7 off by more than 2 px (dashes through text and the staff edge on a tilted page), 14 have no ink beside the head to measure. NOT adjudicated by Sean. Known gap: a text baseline that is a continuous stroke and short (tile 7 of the old sheet's "esc." row) still counts.

Tests: `test_ledger_not_text_2026_10_05.py` (6; RED on the unrepaired tree: no `ledger_not_text` keyword, no `text_boxes` argument). Fast tier 4,479 passed (4,473 + 6); `staged.check` TOTAL 250 before and after.

## lane-farhead-not-a-note (2026-10-05): the far-head reader refuses what the record says is not a note

Sean (DECISIONS 2026-10-05, `note_first_abstain.png`): tiles 1 and 8 barlines/brackets, 5 a tremolo slash, 7 the "a 2" numeral were boxed as noteheads and sent to the reader. STAGED path (gather -> `far_head_reader`), keyword `not_a_note`, ON. A refusal is an abstention (`ledger_reason=not_a_note:<why>`); nothing is deleted. Scripts: `farhead_not_a_note_eval.py {control,oos,tiles}`, `farhead_not_a_note_sheet.py`. Sheet: `out/print/ledgers/farhead_not_a_note.png`.

Reasons (all read off rows the record holds; the floors are imported from `notehead_precision`, not restated): `too_narrow`, `clipped_fragment` (the adjudicator's own floors), `tremolo_slash` (2.49's shape + crossing constants on `Q.NOTEHEAD_STEM_CROSS_INK`, WITHOUT 2.49's position test: tile 5 fails that test), `on_text` (a text/dynamic box covers at least half the head box), `on_a_barline` (a measure cut inside a box narrower than one space), and `decided_not_a_notehead` (only when re-reading a finished record). The far-head gather now runs after `gather_notehead_stem_cross_ink`, which files the slash rows it reads.

- Sean's tiles: 1, 8 (too_narrow), 5 (tremolo_slash), 7 (clipped_fragment) refused; 2 and 12 (real heads) not. Tile 7 is refused as a sliver, not as a numeral: the record holds no text for it.
- Controls: 52 truth-set far heads, gate off 39/0/2 and 11/0/0, gate on identical, 0 refused.
- Out of sample (10-04 run-2 records, 12,308 far heads), evidence available at GATHER only: Litolff 405 of 3,829 (10.6%): clipped 275, text 52, too_narrow 38, barline 29, slash 11. Brahms 1,271 of 8,479 (15.0%): too_narrow 498, clipped 404, barline 301, text 60, slash 8. Of the 1,676, 1,601 are rows ADJUDICATE already calls not-a-notehead; the new reach is 75 (text 52, slash 9, clipped 11, barline 3).
- FIRST DRAFT REFUTED: a barline test of "a measure cut within 0.25 sp of the box" refused 624 and was wrong on the ones no other reason covered: of 12 such refusals crops showed 4 real heads and 6 dynamic letters. The record's cut is only within about 9 px of the barline ink, so it cannot say which side a box stands on. Replaced by the conjunction above, which cannot refuse a head-wide box. Barline-only evidence adds nothing beyond the width floor.
- Sheet: 12 seeded refusals, all non-notes on the print except tile 12 (a clipped top of a real head, refused as a sliver; the head has no other box). Drawn barlines re-measured against pixel columns: 4 of 4 within 3.5 px (3 within 2 px). `on_text` was cropped on 21 undecided cases: 19 are dynamic letters (f, ff, pp, sf); 2 are hollow slashes.
- The 4 tiles' lesson stands: the loss is upstream (the detector boxes them); this gate only stops the reader spending itself on them and counts them by name.
## lane-owner-by-ledgers (2026-10-05) -- which staff owns a far head, read off its LEDGERS (ROADMAP 2.56b; STAGED, default OFF, `OMR_FARHEAD_OWNER_LEDGERS`)

**Why the older tiers do not settle these heads (STAGED `glyph_owner`, read before building).** (1) A head only has a neighbour candidate where a same-category box from the neighbour staff overlaps it (`gather_ownership_evidence`, IoU > `CONTEST_IOU`). Every other far head gets the 2.37 own-staff-only walk: ONE `Q.GLYPH_BAND_DISTANCE` row, nothing to compare, and `glyph_owner` answers `distance` on its one row. Measured on the 10-04 run-2 records: of the heads this witness moves, **155 of 231 (Litolff) and 407 of 481 (Brahms) have one candidate in the record**. (2) Where there are two, `ledger_direction`/`_ladder_complete` count detector `ledgerLine` boxes and CV rung ink stepping OUT from each staff's edge on a half-space grid and need the ladder complete (<= 1 missing) and ending within 1 sp of the head; the note's own line is never read, so a ledger the head hides or a head hanging in the space beyond a line is a miss and the verdict is `far_no_rungs` / `ledger_all_refuted`; the density comparison needs exactly two readings. The note-first look (the note's own line, then the ledgers counted from it to the staff edge, `ledger_grid.derive_note_first_step`) had never been pointed at the neighbour.

**The witness (`tools/omr/annotate/far_head_owner.py`).** Run the note-first look toward EACH candidate staff: the head's own and the next staff beyond it in the head's direction whose x-extent holds it. A candidate FITS when the head lies on its lines or in its first space (no ledger needed, Sean 2026-10-01) or the note-first look reads it. Exactly one fitting candidate owns the head. Both fit, neither fits, or a candidate was UNREAD -> silent, the older tiers run as before; distance never breaks a tie. UNREAD = could not look (no page shape) OR ledger ink toward that staff it could not assemble (a gap under one ledger pitch is two marks of one ledger, so rungs ARE there): not a refutation. STAGED wiring: `gather._file_owner_ledger_readings` files one `Q.FAR_HEAD_OWNER_LEDGER` row per candidate under `READERS.LEDGER_OWNER_NOTE_FIRST` (Observation = the position on that staff; Abstention `ledger_not_read` / `no_page_shape` with `unread`); `adjudicate_glyph_owner` reads it right after the human verdict, ahead of the density / ladder / hairpin / range / distance tiers (`ledger_note_first`, declared in `wants`). A resolved contest DROPS the loser (the exporter refuses the copy, `owned_by_another_staff`); nothing is relocated.

**Controls.**
- The 12 abstain-sheet heads (`out/print/ledgers/note_first_abstain.png`, `farhead_owner_by_ledgers.py controls`). Sean said tiles 3,4,6,9,10,11 are another staff's and 2,12 their own. Rule: tiles 3, 6, 9, 10, 11 -> NEIGHBOUR (5 right); tile 4 (other staff) silent; tiles 2 and 12 (own) silent; of those 8: **5 right, 0 wrong, 3 silent**. Tiles 1 (-> neighbour), 5, 7, 8 (silent) were not adjudicated. IN-SAMPLE: the first version moved tile 12 (`brahms 5/1/2/3/20`) to the neighbour (its own ladder read `gaps 1.28, 0.66, 0.70`, two marks of one ledger, which refuted it); the unread-not-refuted rule above was set after seeing it.
- Truth-set far heads (the 41 Litolff p3 + 11 Brahms p1 far heads of the gather-frame control, `jut_from_ink_eval.prepare`; the brief says 44+11; the set the prepared gather-frame control returns is 41+11, not reconciled here): **0 moved** -- owner kept 39/41 and 10/11, silent on `3/0/0/6/2` and `3/0/9/3/5` (neither fits) and Brahms `1/1/8/7/4` (both fit: a line at each edge of the head).

**Out-of-sample, read only** (10-04 run-2 records `...20261004-farhead-all`, page re-rendered in the gather frame, shape pooled; `farhead_owner_by_ledgers.py run/report`; ~40 min per run):
- Litolff p4-16: 3,829 far heads; the witness names a staff for 2,970 (78%), silent for 859 (neither fits 764, unread 76, both fit 19). **231 change owner** (6.0%): 192 decided -> a different staff, 39 `far_no_rungs` abstentions -> the neighbour; 212 move off the filing staff.
- Brahms p2-26: 8,479 far heads; names a staff for 6,964 (82%). **481 change** (5.7%): 452 + 29 abstained; 462 off the filing staff.
- Agreement: the recorded owner already equals the witness's on 1,009 (Litolff) / 2,887 (Brahms) heads it moves off its filing staff. By recorded reason the changes are `distance` 171 / 421, `far_no_rungs` 39 / 28, `hairpin_separates` 17 / 0, `range_veto` 0 / 16, and the older ledger tiers (`ledger_direction`, `ladder`, `ledger_owner_density`) only 4 / 15: where those decided, the witness agrees almost everywhere.
- ⚠️ **Dropped, not moved.** Of the moves off the filing staff only **57 of 212 (Litolff) and 55 of 462 (Brahms)** have a twin notehead box on the new owner. For the rest `glyph_owner` now says "not this staff's" and the exporter DROPS the copy (CLAUDE.md §10: a resolved contest never relocates), so the note is counted `owned_by_another_staff` and written on neither staff, where it used to be written on the wrong one. That is Sean's call, not made here.
- ⚠️ **Slivers.** 237 of Brahms's 481 changes (23 of Litolff's 231) have a box narrower than 0.6 x the document's median far-head width: barline / stem slivers the width floor refuses elsewhere (Breitkopf SHATTERS). The sheet is sampled from the other 244 / 208.
- 69 (Litolff) / 306 (Brahms) of the changes are decided by geometry alone (the head lies on the new staff's lines or first space and the own staff has no chain), 162 / 175 by a ledger chain.

**Sheet:** `out/print/ledgers/owner_by_ledgers.png`, 12 seeded (20261005) changes, 6 per document, numbered; BLUE = old owner's staff edge, CYAN = new owner's edge, orange = the note, solid green = ledgers counted toward the new staff, red = the note's own line, dashed = what was seen toward the old staff, and under each tile in words "moved from staff X to staff Y because ...". Re-measured against pixel rows: 49 drawn lines, 41 within 2 px of an ink row, 2 more than 2 px off (tile 8 old staff edge 3.0 px, tile 9 old note line 5.0 px), 6 hidden behind the head. NOT yet adjudicated by Sean.

**Tests / checks.** `test_far_head_owner_by_ledgers_2026_10_05.py` (16): RED on the tree before this item (ImportError: no `far_head_owner`; with the new modules but the old `glyph_owner`, the two decision tests fail), green after; each layer has a control that can fail (ledgers erased -> silent, not the nearer staff; flag off -> no rows). Fast tier 4,488 passed (4,473 before + this file); `staged.check` TOTAL 250 before and after (a first cut made `wiring` BROKEN: a bare `own` detail key in this lane's own rows read as a consumer of `Q.GLYPH_BAND_DISTANCE.own`, retiring a KNOWN_GAP; and an observe site whose subject came in as a parameter was UNRESOLVED -- both fixed).

## 2026-10-06 -- lane-edge-vs-through: tiles 9 and 10 were read ON a hidden middle rung, not a bad ON/space separator (STAGED, note-first path)

Sean: out-of-sample tiles 9 (`brahms 13/0/9/0/4`) and 10 (`brahms 3/1/3/7/9`) read ON a line that only touches the head's staff-side edge. **Measured (not the frac_stf rule):** both were decided by `find_note_line`'s `through_the_box_middle` branch, not `through_head_on_rung`. The walk offered TWO rungs on one head: a real thin ledger at the staff-side edge (tile 9 row 2524, tile 10 row 4906; jut 0.15-1.25 sp, `frac_stf` 0.104 / 0.136, i.e. the existing rule also says "space") and a row inside the black head (2500 / 4923) with no line beside the head (jut -0.10..+0.04 sp). The reader took the second. Head ink beyond the edge line past its half thickness: tile 9 0.00 sp, tile 10 +0.04 sp (in-sample space heads -0.25..+0.05, crossing heads +0.26..+0.43; three narrow slivers, a split chord and a half note's upper half read -0.16..-0.03).

Rule (keyword `edge_vs_through`, ON in `far_head_reader.READER_KEYWORDS`, default off in `find_note_line`): the visible edge line wins when it is a thin flat connected jut >= 0.15 sp past the head, the middle rung shows none, the rungs are >= 0.30 sp apart, and head ink beyond the edge line is within [-0.35, +0.175] sp. The upper bound and the jut floor were committed BEFORE the 40-head sample was run (commit d2a4a092). The lower "line touches the head" bound was added after (6d08bc66), because the whole-population list of changed heads showed 8 whose line stood 0.4-1.0 sp clear of the head.

Controls: tiles 9 -> -3, 10 -> 11 (were -4, 10); tile 3 `3/0/8/6/10` unchanged (rule not reached; it is `through_head_on_rung`); in-sample truth set `farhead_all_wired_eval.py` 39/0/2 and 11/11, 0 right heads broken. ⚠ In-sample REACH is only 2 evaluations, 0 fired (`edge_vs_through_eval.py`): the in-sample set cannot fail this rule; the evidence is the out-of-sample list. Of the 12 night-sample tiles Sean already judged, only 9 and 10 change (tiles 4 and 5, read through the box middle and judged right, are untouched). Unit test red on the unrepaired tree first; a second test fails with the lower bound removed. Fast tier 4515 passed; `staged.check` 250 open before and after.

POPULATION (`edge_vs_through_sample.py`): 10-06 night-combined records, Litolff pp.4-16 + Brahms pp.2-26, heads whose OFF replay reproduces the record (3787 of 3787 Brahms, 267 Litolff; Litolff is limited to pages with their own head shape), a thin shown line touching the staff-side edge band: 1963 eligible (101 Litolff, 1862 Brahms). Seeded sample of 40 (20/20, seed 20261006, excludes the 12 seen tiles and slivers): `out/print/ledgers/edge_vs_through_40.png` (orange box, red line, words "reader: ON / in the space beyond"). Split by the stated quantity (head hangs beyond the line vs crosses it) against what the reader says: reader ON + crosses 12; reader space + hangs 22; reader space + crosses 2 (disagreements to look at); reader ON + hangs 0; quantity undefined 4. The rule itself changes 1 of the 40. Whole eligible population: 526 / 1062 / 135 / 9 / 231 undefined; the rule changes 71 (73 over all reproduced far heads, all ON -> the space one step nearer the staff, 72 on Brahms; Sean's geometry position agrees with the new answer in the large majority). No threshold was taken from Sean's adjudication of the sheet, which has NOT happened yet. Second sheet of the changed heads (24 of them, seeded): `out/print/ledgers/edge_vs_through_flips.png`. Drawn lines re-measured against pixel rows: 40-sheet 31 of 41 within 2 px of the ledger ink beside the head, 2 off by 5.5 px (tiles 8, 35), 8 with no line ink beside the head to measure; flips sheet's red line is the hidden middle rung by construction (not ink) and 12 of 48 are off.

## 2026-10-06 -- lane-farhead-per-bar-grid: the far-head reader and the owner witness start from the PER-BAR grid (STAGED, `READER_KEYWORDS["per_bar_grid"]`, ON; default path in `gather_far_head_ledger_positions`)

Why (Sean 2026-10-06 "Fix it"; `verify-staff-line-offsets`): the raw staff-wide lines sit off the ink by tilt (p90 5.5 px); the reader re-found each within +-0.5 sp of the RAW line (one line over where it was >= 0.5 sp off) and took the line's TOP row (~1.5 px high).

Built. `far_head_reader.cell_grid_page_lines(cell)` = `bbox_y0 + staff_line_ys_canonical / upscale_factor` (the rows `_cell_grid` / `gather_notehead_positions` use). `gather` hands each head, and the owner witness each candidate staff (`far_head_owner.lines_at`: the neighbour's grid in the head's x range, nearest bar if none holds it), that grid. `grid_lines_for_head` re-finds each line only within +-0.3 sp of the grid line, at the CENTRE of the dark run (half-depth), one line per window; a line not found, or two found lines < 0.5 sp apart, are the grid's own position and COUNTED (`GRID_STATS`). Constants stated before looking. Keyword off = the old reader bit-for-bit (test). `staged/gather.py`'s `_cell_grid` / `_cell_line_offset` untouched; 2.48 not switched on.

Controls. (1) RECONSTRUCTION (`farhead_per_bar_grid_control.py`, can fail): for 20 random in-staff heads per page, position rebuilt from the box centre and the reconstructed grid equals the recorded `Q.NOTEHEAD_STAFF_POSITION` to 0.010 (Litolff p8) / 0.016 (Brahms p10) half-steps; the same rebuild against the raw lines is off by up to 0.51 / 0.23. (2) Unit tests RED on the unrepaired tree (7 of 10 fail), green after; fast tier 4,526 passed; `staged.check` 250 before and after. (3) The old arm replays the 10-06 record: 1,733 of 1,744 Litolff, 3,712 of 3,787 Brahms recorded positions.

In-sample truth set (`farhead_per_bar_grid_eval.py`, gather frame, scorer shape): OLD Litolff 39/0/2 and Brahms 11/0/0 (what the merged `edge_vs_through` changed: nothing in-sample, 0 fired); NEW Litolff 39/0/2, **Brahms 10/0/1: ONE right head broken**, `glyph/1/1/8/7/4` (truth 13, was "in the space beyond ledger 2") -> abstain `no_line_at_the_note_box`. Cause measured: its five lines move to [5975.5 .. 6085.25] from [5976.0 .. 6083.5], spacing 26.9 -> 27.4 px, the page-standard box grows ~0.6 px each side and the ledger line at 6140.0 now lies 1.2 px inside its top edge. Not retuned.

Sean's 44 confirmed tiles (note_first 1-11, night 1-5,7,8,11,12, edge_vs_through_flips 1-24; the tiles are keyed by document, subjects repeat across Litolff and Brahms): 40 keep their answer; **4 go from right to abstained, none to a wrong answer**: note_first 2 `brahms 19/1/0/5/10` (-3, `no_rungs`), night 12 `lito 5/0/5/9/0` (-6, `count_does_not_fit` gaps 1.35/1.99: staff top 1447 -> 1449, standard box fails its gate so the detector box is used and one rung 1414 is no longer found), edge_flip 1 `brahms 4/0/0/9/15` (-3, `no_line_at_the_note_box`), edge_flip 12 `brahms 14/0/1/0/6` (-5, `count_does_not_fit`).

Tile 6 (`lito 16/0/0/0/2`; Sean: belongs to the staff BELOW): before: on the 3rd ledger below its own staff (14), owner = its own staff (the staff below `count_does_not_fit`). After: own staff reads the 2nd ledger below (12) and the staff below reads -4 (on its 2nd ledger above): both fit, owner = nobody. Not right yet (neither names the staff below) but no longer names the wrong staff.

Out of sample (10-06 night records, Litolff pp.4-16 3,829 far heads, Brahms pp.2-26 8,479; each arm's own head shape, pooled where a page has none, `farhead_per_bar_grid_oos.py`): position changed Litolff 30 / Brahms 10; abstain -> decided 83 / 47; decided -> abstain 38 / 41; OWNER changed 261 / 238 (nobody -> a staff 156 / 105; a staff -> nobody 104 / 133). "Implausible fit" (a decided answer whose note line lies > 0.35 sp clear of the box the reader used): Litolff 7 -> 8, Brahms 7 -> 6. Re-find counts: 208k Litolff and 453k Brahms line re-finds, 264 and 1,135 (0.13% / 0.25%) fell back to the grid, 0 pair rejections. Head-shape sample: the Litolff pool of clean on-line heads falls 50 -> 25 under the new lines (more "area" rejections; thickness falls back to 4.0 px) -- NOT the cause of the changes above: with the NEW lines and the OLD arm's shape forced, Litolff positions changed 29, owner 260, night 12 still breaks. The shape probe is `farhead_per_bar_grid_shape_probe.py`.

Sheet `out/print/ledgers/farhead_per_bar_grid.png`: 12 seeded (20261006, 6 per document) changed heads, before red dashed / after blue on BOTH staves, answer and owner in words. Drawn lines against the page's pixel rows (flank columns, +-0.55 sp): BEFORE median 1.50 px, p90 2.55, max 7.50; AFTER median 0.25 px, p90 0.75, max 4.00 (n=120 lines each). NOT yet looked at by Sean. The unseen cost is the 4 + 1 right heads above, all to abstention, and an owner witness that now says "nobody" on ~100 heads per document it used to name -- the sheet is where to judge which side of those is the print.

## 2.57 per-bar grid locked one line over: find the five lines in the cell (lane-per-bar-grid-one-line-off, 2026-10-06)

SHARED code (`measure_extractor._cell_line_offset`; STAGED and LEGACY both read it). Flag `OMR_CELL_LINE_FIND`, default OFF until Sean sees `out/print/per_bar_grid_one_line_off.png`. Scripts: `per_bar_grid_one_line_off.py` (grid-only control; measure = the verifier's clear-column ink rows), `per_bar_grid_heads.py`, `per_bar_grid_gather_diff.py`, `per_bar_grid_sheet.py`. Tests `tools/omr/tests/test_cell_line_find.py` (the off arm asserts the lock; RED on the old tree: no flag, no `_cell_line_offset_capped`).

**Cause (verify-staff-line-offsets).** 29 Litolff bars (21 by the verifier's median measure, 29 by mine; pages 2, 3, 4, 6, 10, 12, 14) and 2 Brahms bars (7/0/5/8 and one other) have the grid exactly one spacing off the ink: needed shift ~15.5 px against a 12 px cap, and at shift 0 four of the comb's five rows already lie on printed lines, so the capped comb never moves.

**Design (Sean 2026-10-06).** Do not shift the comb; find the lines. My first idea, a staff-tilt seed plus neighbour continuity, was built and dropped: adjacent bars on Litolff 4/0/4 differ by a whole spacing with the ink measuring right on both, so continuity cannot be a rule. The rule: row profile over the cell's width minus stem/barline columns; the set of exactly five evenly spaced rows (spacing +-8%) each inked >= 0.70 of the width, summed coverage highest, with NO such line one spacing above the top or below the bottom; the row centres must sit on a straight line to 0.1 sp. Not found -> the capped shift as before. Two guards were added after the first version broke bars: (a) a cell whose existing capped comb already has all five rows inked >= 0.70 keeps it (a comb one line over never does); (b) a found shift within 1 px of the capped one is not a move. Simpler than the seed design: yes, one function, no staff-level state. The 0.70 threshold is what separates a printed line from a slur (0.4-0.6 in the same cell; at 0.45 a slur passed as a line and 4 bars went one line wrong).

**Grid-only controls, every page of both movements (flag off vs on, no detector):**

| | bars >= 0.4 sp off | right (< 0.4 sp) -> wrong | bars > 1 px worse | adjacent-bar jumps > 0.5 sp | shifts changed |
|---|---|---|---|---|---|
| Litolff 1-16 | 29 -> 0 | 0 | 0 | 14 -> 0 | 30 |
| Brahms 0-26 | 2 -> 0 | 0 | 1 (1.6 px) | 2 -> 0 | 28 |

**Heads against recorded boxes.** Litolff: 28 in-staff heads change, every one by exactly 2 half-steps (13 down, 15 up), none by 1. Brahms: 11 change (5 by +2, 6 by -1 on bars whose ink offset fell from 2-7 px to under 1).

**Real one-page GATHER+ADJUDICATE re-gathers, same tree, off then on** (Brahms p7; Litolff p2, 3, 4, 6, 10, 12, 14; every head's `NOTEHEAD_STAFF_POSITION`; `out/per_bar_grid_gather_diff.txt`): the same cells and head sets in both arms on every page. Positions changed: Brahms p7 20 (5 by +2.07, 15 by 0.13-0.22 step); Litolff 8+1+22+25+2+1+2 = 61, all by 1.9-2.1 steps except one of 0.26. Truth-set far heads: 38 on Litolff p3 (the only truth page among these), 0 moved. These records are from a dirty tree: arm against arm on one tree, not baselines.

**Other controls.** `staged.check`: 250 open on this tree and 250 on a clean export of `origin/main` (not grown). Fast tier (`pytest -m "not slow" tools/omr/tests`) before the 1 px guard: 4,425 passed, 0 failed; rerun after it is in the commit message.

**Sheet** `out/print/per_bar_grid_one_line_off.png`: 8 fixed bars (7 Litolff, 1 Brahms), old grid red, new blue (alternating blocks so a red row and the blue row one spacing away can both be read), two heads per bar bracketed A / B, positions in words before -> after counted from the bottom line. DRAWING CHECK: every drawn row re-read from the panel's own pixels is 0.00 px from where it was meant to go (x3). Panel 3 (`4/0/4/10`) is the clearest: both heads sit on a ledger line below the staff, and the old grid called them the bottom line.

**Limits.** On Litolff 10/0/9/12 and Brahms 13/0/1/8, 13/0/6/2 (no clear columns to judge by) an earlier version answered a whole spacing away; the all-five-on-ink guard now returns the old answer there; not verified by eye either way. A cell narrower than 4 sp, or with a beam or text where a line should be, falls back to the capped rule (marked `line_grid_found: false` only when the capped rule answered something). The 15 staves with one misdetected line (verifier) are not repaired: their found rows fail the 0.1 sp straightness test and fall back. The far-head reader's own line re-measure (other lane) is unchanged.

## 2026-10-06 -- lane-lines-combined: both line fixes on one branch; the 5 right -> abstain heads (ROADMAP 2.57b; flags `OMR_FARHEAD_OWNER_LEDGERS=1 OMR_CELL_LINE_FIND=1` for the overnight re-gather)

Branch `lane-lines-combined` = `lane-farhead-per-bar-grid` (1b5e6932) + `lane-per-bar-grid-one-line-off` (f1bc0dda); one textual conflict (this file), kept both; ROADMAP rows 2.56/2.56b and 2.57 did not collide. Fast tier exit 0; `staged.check` 250 (not grown).

**Connected?** Yes. The far-head reader's per-bar grid is `far_head_reader.cell_grid_page_lines(cell)` = `staff_line_ys_canonical` carried back by the cell's origin/scale; `measure_extractor` builds `staff_line_ys_canonical` from `local_ys = staff.line_ys + shift`, and `shift` comes from `_cell_line_offset`, where the cell finder's result lands. Nothing to wire (`line_grid_localized['offset_px']` is the same shift, recorded).

**Controls (flag off vs on, same tree).** Truth set (`farhead_per_bar_grid_eval.py`): Litolff 39/0/2 both; Brahms 10/0/1 both -- the one broken head is `glyph/1/1/8/7/4`, unchanged by the finder. Sean's 44 tiles: the same 4 (plus the truth head), nothing else, identical with and without the finder. Out of sample (10-06 records, full pages, `farhead_per_bar_grid_oos.py`): Litolff decided 1,743 (raw) -> 1,788 (per-bar grid) -> 1,785 (+finder), implausible 7 -> 8 -> 8; Brahms decided 3,813 -> 3,819 -> 3,822, implausible 7 -> 6 -> 6; the finder moves 11 Litolff far-head positions (e.g. `4/0/4/14/*` 11 -> 13, correct per the 2.57 sheet). Reports `out/lines_combined_report_{find,nofind}.txt`.

**The 5 heads (sheet `out/print/ledgers/lines_combined_5.png`; drawn lines 1 px, cyan; re-measured against the page's pixel rows: before median 1.0-2.3 px off, after 0.0-0.5 px, max 1.5 px).** The finder changes none of them; the new lines (centred on the ink, 1-2 px lower than the old top-row reads) shift which printed ledger the next step accepts. Swapping one input at a time (`lc5_probe.py --trace`) names the step:
1. Brahms truth `1/1/8/7/4` (truth 13): `collapse_head_edge_rungs_to_middle` (`HEAD_EDGE_RUNG_TOL_SPACES` 0.25 sp). The walk now also returns a rung at 6168 (the slur under the head, 4.3 px inside the box's bottom edge) beside the real ledger at 6140 (1.2 px inside its top); the rule takes the pair for the box's own outline and drops both.
2. edge_flip 1 `4/0/0/9/15` (-3): the same step, with two real ledgers (474.5, 506.5) flanking a head in a space: both within 0.25 sp of the 1.22 sp standard box's edges, both dropped. The old lines escaped only because the walk then returned a hidden middle rung (483.5) instead of 474.5.
3. night 12 `lito 5/0/5/9/0` (-6): `_walk_ladder` window `WALK_WINDOW` (0.65, 1.35) x the previous gap. The first gap, staff line to ledger, is now 21 px (the top line read at its centre; it was 19), so the next ledger, 13.5 px further, is 0.643 of it, under 0.65 by 0.15 px; the ledger at 1414.5 is lost.
4. note_first 2 `brahms 19/1/0/5/10` (-3): the standard-box fit gate (`FIT_OFFSET_MAX_SPACES` 0.15): offset 0.16 (was 0.11), so the detector box is used and it finds no rung.
5. edge_flip 12 `brahms 14/0/1/0/6` (-5): `_band_centers` -- the ledger at 735 is no longer a band (the walk window's rows shifted by 1.75 px). The old arm's lines for this staff were themselves wrong (third line at 832.5 against 842.75).

**No threshold changed.** None of the five is a limit set on mis-measured lines: 1 and 2 are a rule written for a ~1 sp box meeting a 1.22 sp box; 3 and 4 are gates missed by 0.15 px / 0.01 sp; 5 is an Otsu window. Moving any would be tuning to save a head. They stay abstained, plainly (rule 8). Question for Sean: steps 1/2 (`collapse_head_edge_rungs_to_middle` drops two real ledgers around a head in a space) account for 2 of 5.
## lane-owner-from-staves (2026-10-06) -- ownership starts from the staves we know (ROADMAP 2.56c; STAGED GATHER+ADJUDICATE, default OFF, `OMR_OWNER_FROM_STAVES`)

**Convention (Sean, 2026-10-06, DECISIONS):** (1) a head ON or BETWEEN a known staff's five lines -- measured locally, centre from the top line to the bottom line plus half a line thickness -- is that staff's, decided, no contest; (2) a copy of the same head found by a NEIGHBOUR's padded cell is a duplicate if the owning staff has its own box (dropped, the existing `owned_by_another_staff`) or is named `staff_band_no_box` if it has none (no box invented); (3) only the gap between two staves stays contested.

**Why (1) was not already so.** `glyph_owner` is only asked about a head with `Q.GLYPH_BAND_DISTANCE` rows (a twin on another staff, or a far head walked against its OWN staff alone) and it then SCORES: complete ladder +4.0, range veto -6.0, hairpin +7.0, distance a tie-break at -0.5/space. A head inside a band has distance 0 -- no term at all -- so "inside" was the absence of a penalty, not a tier, and a ledger tier, a veto or the note-first witness could outvote it. A head in B's band filed on A with no twin on B had no B candidate row, so B was never asked. The page-wide `Q.STAFF_LINES` is also not the local grid: over every notehead the page-wide position differs from the cell's local one by p99 0.64 sp (Litolff) / 0.36 sp (Breitkopf), max 0.775 / 0.73 sp, so near a band edge only a local measure can say; the tier uses the head's own cell grid, else the twin's, else the page-wide lines at least 0.8 sp inside, else it is silent (`gather.PAGE_EDGE_MARGIN_SPACES`).

**STEP 1 -- the count** (10-06 night-combined records, read with `record_io.load_record`, no gather; `owner_from_staves_count.py`; both records were gathered with `OMR_FARHEAD_OWNER_LEDGERS=1`). Heads whose centre lies in ANOTHER staff's band (page-wide lines):

| | heads | in own band | in another's band | owned by the band staff | owned by the wrong staff | contested/abstained/unasked | twin box on the band staff | no box there |
|---|---|---|---|---|---|---|---|---|
| Litolff | 11,399 | 5,987 | 81 | 81 | 0 | 0 | 58 | 23 |
| Breitkopf | 24,260 | 13,168 | 507 | 505 (499 `ledger_note_first`, 6 `ledger_direction`) | 2 (`distance`, no twin) | 0 | 301 | 206 |

A head in its own band owned elsewhere: 0 on both. 64 of 81 (Litolff) and 295 of 507 (Breitkopf) lie within 0.5 sp of the band edge (the on-line heads). 299 of the 301 Breitkopf twins have their own LOCAL position in the band; 2 do not (page-wide inside, local outside).

**STEP 2 -- the tier** (`ownership._owner_from_staves`, ahead of `ledger_note_first`; reasons `staff_band`, `staff_band_no_box`; GATHER, flag on, files `local_position_in_candidate` on `Q.GLYPH_BAND_DISTANCE` and names the staff a head lies in or within 0.8 sp of as a candidate). A/B on ONE tree by re-deciding `glyph_owner` on the saved record, flag OFF vs ON (`owner_from_staves_ab.py`; the OFF arm reproduces the saved verdicts 9,422/9,422 and 34,043/34,043):

- 10-06 records: the tier fires on 253 (Litolff: 127 other-staff via the twin's local position, 121 own via the own cell, 5 own page-wide) and 1,623 (Breitkopf: 558 / 554 / 285 own page-wide / 226 `staff_band_no_box` page-wide) verdicts; owners changed **0** and **1** -- it agrees with the note-first witness (a different source: geometry vs ledgers) on all but `glyph/2/1/13/4/7` (`distance` -> `staff_band_no_box`).
- DEFAULT tree (the `Q.FAR_HEAD_OWNER_LEDGER` rows dropped, i.e. what a default gather files; OFF no longer reproduces the saved verdicts, by design): Litolff 0 owner changes, Breitkopf **61**, all `distance` -> `staff_band_no_box`.
- In-staff heads of the correct staff changing owner: **0** (Litolff 126, Breitkopf 839 own-band decisions, all already the filed staff).
- Controls. The two clipped Breitkopf tiles: `16/1/6/4/4` -> staff below (`staff_band`, twin's local position, twin on the staff below); `25/0/9/1/16` -> staff below by `ledger_direction`: the clipped box's centre is 2.0 sp above staff 10, i.e. in the gap, so the tier is silent and the older tier is right (both on the 10-06 and the default arm). Sean's 6 other-staff tiles of `note_first_abstain.png` (3,4,6,9,10,11 = `brahms 20/0/6/6/6`, `brahms 3/0/11/7/18`, `litolff 12/0/7/9/3`, `litolff 11/1/8/12/3`, `litolff 12/0/10/10/0`, `brahms 19/1/5/7/24`): all six already go to a staff other than the filed one on both arms; the tier decides only tile 11 (`staff_band`, local twin), tiles 3,4,6,9,10 lie in the gap and stay with the older tiers. Truth-set far heads (2.44c records, 41 Litolff p3 + 11 Breitkopf p1): tier fires on 0, owners flipped 0 (OFF reproduces 41/41, 11/11).
- **Owner has no box** (Sean's relocation call): 23 (Litolff) / 206 (Breitkopf) heads lie in a band whose staff holds no box of that ink; today `ledger_note_first` names the owner and the copy is dropped, so the note is written nowhere. The tier, by page-wide margin only, names 0 / 226; the Litolff 23 sit within 0.8 sp of the edge and need the local grid GATHER now files.

**Sheet** `out/print/ledgers/owner_from_staves.png`: 12 seeded (20261006) of the 61 default-tree Breitkopf changes; both staves' five lines drawn from the raster at the head's x (blue old owner, cyan new), the box orange, words under each tile; 108 of 120 drawn lines within 2 px of an ink row, 11 off by 2.5-5.0 px (tiles 1,2,7,8,9,10,11,12, captioned count per tile), 1 with no ink row (tile 10). All 12 say `owner has no box`. My reading of the print, NOT Sean's: most of the 12 look like rests, barline slivers or a clef fragment rather than noteheads -- consistent with the owner staff having no box. NOT yet adjudicated by Sean.

**Not done / not measured.** GATHER's `local_position_in_candidate` and near-staff candidate extension are unit-tested with fake cells only: no gather was run (rule), so the real reach on the 23/206 edge heads is unpriced -- one small re-gather prices it. `staff_band_no_box` is a ruling reason only; EXPORT still counts the copy `owned_by_another_staff` (splitting it to `owner_has_no_box` is a one-line change in `export._place_notes` that touches a file this lane does not own).

Tests: `test_owner_from_staves_2026_10_06.py`, 16 tests, RED on the unrepaired tree (8 positives fail, the 8 negative controls pass on both), green after. Fast tier 4,521 passed. `staged.check` TOTAL 250 -> **247** (three `KNOWN_GAPS` entries closed: `Q.STAFF_SKEW` thickness, `glyph_owner declares notehead_staff_position`, reach `STAFF_SKEW`).
## 2026-10-04 -- lane-tile3-measure: what separates tile 3 (`glyph/3/0/8/6/10`) from fix 1's right cases (MEASUREMENT ONLY)

`tile3_vs_fix1.py` (reader only called; `tools/` untouched). Sheet: `out/print/ledgers/tile3_vs_fix1.png` (600 dpi, local staff lines blue, measured line row magenta, ink top/bottom orange, detector box green brackets). Drawn lines re-measured against pixel rows by the script: 0 of 15 miss the ink.

**Fix 1 never fired on tile 3.** Across all 55 far heads (Litolff 44, Brahms 11) it fires on exactly two: `3/0/7/0/7` and `3/0/8/9/0`, both right. On tile 3 `near_edge_ledger_evidence` returns `head_body_on_both_sides_of_the_rung` (staff band 0.64 vs far 1.00), so the rung is popped as "the head's own outline" and the head abstains (`no_rung_before_the_head`). The missing branch is the complement: a thin flat rung touching the near edge, head body on BOTH sides, is the head's own line -> ON it (offset 2n, kind line).

**Separating quantity: `frac_stf` = head ink on the staff side of the line / head ink height** (local lines, ink = gray<140, central 60% of box width). ON-the-line heads 0.25-0.51 (n=13: tile 3 = 0.357, above 0.48 sp, below 0.86 sp); head-in-the-space heads 0.079-0.238 (n=14: `7/0/7` 0.174, `8/9/0` 0.098). A threshold anywhere in 0.24-0.25 calls 13/13 ON and 0/14 SPACE (0 misfires), both documents, all heads whose reference is ON or SPACE of a near-edge rung. Margin is only 0.012, so it is a gap in-sample, not a proven bar; geometrically the two classes are ~0.1-0.2 (line half-thickness over a 1.3 sp head) vs ~0.35-0.5 (line crosses the head). Not separating: detector box vs ink (|diff| < 0.25 sp both), width (1.2-1.5 sp), fill (all filled), jut length (0.1-0.3 sp on both; tile 3 0.19/0.19), line thickness (5-13 px, merged with neighbours). The detector box's middle is not the head's: tile 3's line sits 0.48 sp below its box top vs 0.14-0.25 for the SPACE cases, which is why the middle-row probe (0.15 sp tolerance) misses it.

Other ON heads the same branch would reach: `3/0/7/2/4` (abstains), `3/0/7/7/0` (11, ref 12), `1/0/10/7/1` (-4, ref -2), `3/0/0/6/2` (ref wrong per Sean) -- all measure ON (0.25-0.43). Not built; no default changed. Out of sample: every number is from the same 44+11 heads.
### lane-overnight-20261004-read: the two overnight re-gathers read (2026-10-05)

STAGED path, GATHER+ADJUDICATE only. RUN 1 = `*-whole-20261004-farhead` (branch lane-farhead-wire-staged, reader wired, no fixes); RUN 2 = `*-whole-20261004-farhead-all` (lane-farhead-all-wired `bcd0ca80`: + jut-from-ink + chord split + through-head); BASE = `*-whole-20261001` (newest earlier; geometry only, no far-head rows). Litolff pp.1-16, Brahms pp.0-26. Records read only, via `load_record`. Scripts: `overnight_1004_{truth,extract,report,sheet}.py`; full printout `out/overnight_1004_report.txt`. Heads matched across records by box overlap (IoU >= 0.5, same page).

**1. Reach (neither run is dead; `no_page_shape` = 0 in both).**
| | far heads | far-head rows | reader abstained (`ledger_not_read`) | NOTEHEAD_POSITION decided |
|---|---|---|---|---|
| Litolff RUN1 | 4,197 | 2,833 | 1,364 (32%) | 2,833 |
| Litolff RUN2 | 4,197 | 2,830 | 1,367 | 2,830 |
| Brahms RUN1 | 8,966 | 6,790 | 2,176 (24%) | 6,790 |
| Brahms RUN2 | 8,966 | 6,628 | 2,338 | 6,628 |
BASE far heads (geometry outside the first space): Litolff 4,363, Brahms 9,105, none read. Page-shape pool: Litolff filled on its first gathered page (p1 already read; 14 pages read with the pooled shape, p14 and p16 with their own); Brahms every page used its own shape. Abstentions are `no_rungs` (Litolff 927/909, Brahms 1,490/1,481) and "every found rung was the head's own outline" (437/458, 686/857). RUN 2 abstains on more heads than RUN 1 (Brahms +162).

**2. RUN 1 vs RUN 2.** Same heads (Litolff 4,197 matched, Brahms 8,966). Both decided: Litolff 2,663, Brahms 6,506; decided position DIFFERS on 234 (Litolff) and 411 (Brahms), on every page; decided to abstained 170 / 284, abstained to decided 167 / 122. Most differences are one step (-3 to -4, 11 to 12): the jut-from-ink change moves a whole population by one, with no reference outside the truth pages to say which way is right.

**3. IN-SAMPLE truth set (not out-of-sample).** Litolff n=44 (`3/0/0/6/2` = -6 per Sean): RUN1 35 right / 5 wrong / 4 undecided; RUN2 35 / 5 / 4; geometry 29 / 15 (same in BASE). Brahms n=11: 11/0/0 in both runs and geometry. RUN 2 gains `3/0/0/2/9`, `3/0/0/7/1`, `3/0/8/6/10`; loses `1/0/3/7/3` (now undecided), `3/0/0/2/4` (reads -6, truth -7, chord split) and `3/0/7/3/1` (-5, truth -6). Net zero. Still wrong in RUN 2: `3/0/0/6/2` (-4), `3/0/7/3/1/2/4` (-5 for -6). Undecided: `1/0/3/7/3`, `3/0/8/1/1`, `3/0/9/3/5`, `3/1/0/9/2`. The wired reader gets 35 of 44 where the scorer-frame benchmark said 40: pooled shape and the gather frame cost 5 heads on the very heads it was written on.

**4. OUT-OF-SAMPLE** (Litolff pp.4-16, Brahms pp.2-26; the truth set's heads are p1/p3 and p1; rules were written on Litolff p1-3, Brahms p0-1). Agreement with geometry is NOT accuracy. RUN 2, Litolff: 3,829 far heads, decided and agreeing with geometry 926, decided and DISAGREEING 1,657, abstained 1,246. Brahms: 8,479; 3,544 agree, 2,683 disagree, 2,252 abstained. RUN 1: Litolff 967 / 1,615 / 1,247; Brahms 3,640 / 2,757 / 2,082. Out of the decided, the reader disagrees with geometry on 64% (Litolff) and 43% (Brahms), against 15/44 and 0/11 in-sample: far more than the in-sample error rate predicts, so one side is wrong on a lot of heads and only the print can say which.

**Crop sheet** `out/print/ledgers/overnight_1004_sample.png` (+ `.json` key): 12 seeded (20261004) RUN 2 disagreements, 6 per document. Replay of the reader on the gather-frame raster reproduced the recorded position on 12 of 12 (control: a non-reproducing head is not drawn; the pooled-shape rebuild gave a slightly different sample count on 5 Litolff pages but the same positions). Drawn lines re-measured against pixel rows: ledger overlays median +0.00 px (n=21), staff overlays median -1.50 px (n=109), the standing known bias (`_darkest_row`, see lane-frame-drop). Open: Sean says which tick is right on tiles 1-12.

### lane-offbox-check (2026-10-05): Sean's rule as a check -- the line a far head's position names must run through its box, or sit on its staff-side edge

STAFF-path GATHER+ADJUDICATE output, 10-04 overnight RUN 1 / RUN 2, Litolff and Brahms. Scripts `offbox_check.py` (the check, `Rows`), `offbox_measured.py` (replays the reader to recover the ledger rows it measured), `offbox_report.py` / `offbox_report2.py`, `offbox_sample.py`, `offbox_pitch.py`; printouts `out/offbox_report.txt` (grid rows), `out/offbox_report2.txt` (measured rows), `out/offbox_summary.json`. Crop `out/print/ledgers/offbox_sample.png`.

**Fixed before looking:** ON-line = the named line's row within the central 50% of the box height; in-space = the staff-side bounding line within 0.25 staff space of the box's staff-side edge. Rows: staff lines are the LOCAL lines at the head's x; ledger rows are the reader's MEASURED rungs (replay on the gather raster; control = replayed position equals the recorded one: RUN 2 99.6%/99.9%, RUN 1 85%/90% because the replay runs the RUN 2 reader code, non-reproducing heads left out), a gap of k pitches between rungs gets k-1 INTERPOLATED rows, beyond the last rung EXTRAPOLATED. First attempt used the plain grid (top + p*half-space): it failed 8 of 44 Litolff references, because Litolff's ledgers sit ~1.08 sp apart, not 1.0 (all 8 failures were the line lying toward the staff of the box). Replaced by the measured rows. Ledger pitch measured from the rungs: Litolff 1.08, Brahms 1.0-1.02 sp.

**Control that can fail** (matched into the run by box overlap, 44/44 and 11/11): the references pass 41/44 Litolff (93%; the three: `1/0/10/7/1` standard box only 0.91 sp tall, `3/0/0/2/4` chord blob, `3/0/9/1/1` no measured rows) and 11/11 Brahms. A reference moved one step is flagged off-box: -1 93%, +1 86% (Litolff), 100%/91% (Brahms); two steps 100%. Both one-step shifts caught on 80% of Litolff heads: the check cannot see a one-step error where the box is tall or off the head. Truth set, RUN 2: reader right 34 ON / 1 OFF; reader wrong 5 of 5 OFF.

**Census of decided far heads (replay-reproduced), RUN 2:** Litolff 2,818: reader ON 57.2% / OFF 42.8%; geometry ON 56.4% / OFF 43.6%. Brahms 6,621: reader ON 58.7% / OFF 41.3%; geometry ON 73.0% / OFF 27.0%. RUN 1 is the same within 3 points (Litolff reader 60.8, geometry 57.7; Brahms reader 61.5, geometry 74.0). Where reader and geometry agree the answer is ON 94% / 97%; where they disagree the reader is ON 36% (Litolff) and 6% (Brahms). Off by (steps from the nearest passing position), reader RUN 2: Litolff 1: 207, 2: 199, 3+: 587, no passing position: 213; Brahms 257 / 423 / 1,459 / 598. Geometry's off-box misses are mostly one step (Litolff 906 of 1,229, Brahms 1,029 of 1,790): the old one-step-too-far signature; the reader's are mostly three or more.

**Why the reader is off so far:** its named line is an INTERPOLATED row (a ledger it never measured between the staff and the first rung it found) on 737 Litolff and 1,828 Brahms decided heads, and on those heads the answer is ON the box 0.3% of the time. Typical record: "last rung passes through the head itself ... jut connected" with ONE rung counted, reads 10 (first ledger below) while the head is 3.3 sp from the staff edge. The line it saw IS on the head; the NUMBER counts only the rungs it found, not the ledgers between the staff and that line. It is Sean's rule 2026-10-05 ("the note's own line first, then count to it") stated as a measurement. Where the reader's named line is a measured one it is ON 78% (Litolff) / 81% (Brahms). Steps-off for interpolated heads carry +-1 ledger uncertainty from the pitch.

**Caveats.** Geometry's named lines are often not measured (Litolff 19% extrapolated, 15% interpolated), so its ON rate is weaker evidence than the reader's. The detector box is the box (box taken from the reader's step rule instead changes nothing: Litolff 57.1%, Brahms 58.8%); "standard" boxes pass more often than detector ones (reader 71% vs 48% Litolff). Not an accuracy measure on pages without a reference; the 8-tile crop (seed 20261005, 4+4) is for Sean: staff overlays re-measured -1.25 px median against the dark rows (known offset), named-line ink check only possible on 2 of 8 tiles (no ink where no ledger is drawn).
## lane-note-first-abstain-sheet (2026-10-05): why the note-first far-head reader abstains (STAGED reader, READ ONLY)

`note_first_abstain_sheet.py` re-ran the note-first reader as `farhead_note_first_oos.py` does (10-04 run-2 records, page re-rendered in the gather's deskewed frame at 600 dpi, no gather, no reader code changed). Control that can fail: the re-run's abstain reasons equal the committed oos json exactly, both documents.

**Counts.** Litolff p4-16: 3,829 far heads, 2,066 abstain (count_does_not_fit 909, no_rungs 692, no_line_at_the_note_box 408, other 57). Brahms p2-26: 8,479, 4,615 abstain (count_does_not_fit 2,386, no_rungs 1,072, no_line_at_the_note_box 1,061, other 96).

**count_does_not_fit, found vs expected** (ledgers between the edge and the note's line, found vs round(distance / 1.05 sp) - 1): Litolff found fewer 867, equal 35, more 7; Brahms fewer 2,262, equal 93, more 31. The modal row is "found 0, expected 2" (Litolff 369 of 909; Brahms 914 of 2,386), then "found 0, expected 3" (219; 401). The broken gap is too WIDE (a ledger missed) in 870 + 2,210 cases, too NARROW (two marks of one) in 23 + 83, both in 16 + 93. So the abstention is almost always "the walk saw none/too few of the ledgers the distance needs": the page is blank in the gap (tiles 9-11: 3.1 to 6.0 sp from the edge, nothing printed between) or the reader's closer look puts a rung where no ink is (tile 12: both `found by a closer look` lines have no ink row within 6 px).

**Belongs to another staff.** Box INSIDE another staff's lines: Litolff 51 of 2,066 abstainers (decided far heads: 0); Brahms 354 of 4,615 (decided: 6). TOUCHING another staff's band (0.25 sp slack): 206 and 782 (decided: 0 and 9). Box centre NEARER another staff's band than its own: Litolff 1,525 of 2,066 (74%; count_does_not_fit 766/909, no_rungs 454/692, no_line 288/408) against 131 of 1,763 (7%) of the heads it decides; Brahms 3,757 of 4,615 (81%; count_does_not_fit 2,179/2,386, no_rungs 766/1,072, no_line 781/1,061) against 344 of 3,864 (9%). Same as the 10-05 crop finding (4 of 6 `count_does_not_fit` crops were the neighbour staff's heads): most abstentions are heads read against the wrong staff's edge, i.e. an ownership question, not a ledger-reading one. The test is geometric (distance to the staves' recorded line bands and x extents), not a truth; "nearer" is a hint, tile 6 and 11 are the touching cases.

**Sheet:** `out/print/ledgers/note_first_abstain.png`, seed 20261005, 4 per reason (2 Litolff, 2 Brahms), 12 tiles numbered, glyph id and page under each. Re-measure of 42 drawn lines against pixel rows (flank columns, then a 4 sp band): 31 within 2 px of an ink row, 5 off by 2.5-4.5 px (tiles 2, 3, 4 twice, 12; each flagged on its tile), 6 with no ink row within 6 px (tile 1's grey line, the note's own line on 9, 10 and 12 where the head hides it, and tile 12's two `closer look` rungs; flagged `hidden`). NOT yet adjudicated by Sean.
## night-1006-read (2026-10-06): the night-combined records vs the 10-04 run-2 records (STAGED, GATHER+ADJUDICATE)

NEW = `...-mvt1-whole-20261006-night-combined.record.json` (note-first reader, text-not-a-ledger, not-a-note gate, owner by ledgers; tree e09e9bf5, clean). BASE = `...-20261004-farhead-all.record.json`. Scripts `night_1006_extract.py` -> `night_1006_replay.py` (reader replayed on the gather-frame raster; control = replayed position equals the recorded one: NEW 99.7% / 99.9%, BASE 99.6% / 99.9%) -> `night_1006_report.py`, `night_1006_sheet.py`; printouts `out/night_1006_{report,sheet}.txt`, `out/night_1006_summary.json`. Heads matched across runs by box overlap.

**1. Far heads (Litolff 4,197 / Brahms 8,966).** Decided: NEW 1,903 / 4,055, BASE 2,830 / 6,628. Refused as not-a-note (new gate): 449 / 1,405 (Litolff clipped 306, text 57, narrow 42, barline 31, slash 13; Brahms narrow 534, clipped 426, barline 373, text 64, slash 8). Abstained: NEW 1,845 / 3,506 (count_does_not_fit 857 / 1,911, no_rungs 588 / 748, no_line_at_the_note_box 347 / 771, other 53 / 76); BASE 1,367 / 2,338 (no_rungs, head's-own-outline). Owner witness (`ledger_note_first`) decided 3,061 / 7,085 heads; NEW owner differs from BASE on 220 / 459: Litolff 47 moved with a twin box on the new staff, 114 DROPPED (no twin), 59 back onto the filing staff; Brahms 47 twin, 365 dropped, 47 to filing. (Brahms: about half the dropped are slivers, per the owner-by-ledgers finding.)

**2. Sean's rule (named line through the box or on its staff-side edge), decided far heads.** On the reader's own measured rows (the 10-04 definition): Litolff NEW 94.6% vs BASE 57.2%; Brahms 98.1% vs 58.7%. Same heads decided in both: Litolff 94.4 vs 88.5, Brahms 98.1 vs 94.4. CAVEAT: the measured rows are the reader's own rungs, so a note-first answer passes almost by construction. Reader-independent grid rows (local staff lines, one-space pitch; biased on Litolff, ledgers ~1.08 sp): NEW 84.6% / 94.9%, BASE 51.0% / 57.8%; geometry on the same rows 79.3 / 97.5 (NEW heads), 71.8 / 85.4 (BASE heads). The check still fails where it should: truth references pass 97% / 100%, a one-step shift is flagged on 82-91%, the one NEW wrong truth head is OFF.

**3. Truth set (41 Litolff p3 + 11 Brahms p1; the 3 Litolff p1 heads left out).** Litolff right/wrong/undecided: NEW 36/1/4, BASE 33/5/3, geometry 29/12/0. Brahms: NEW 11/0/0, BASE 11/0/0, geometry 11/0/0. Changes: `3/0/7/3/1,2,4` -5 -> -6 (right), `3/0/0/6/2` -4 -> abstain; still wrong `3/0/0/2/4` (-6, truth -7, geometry right).

**4. Whole record.** Noteheads gathered 11,399 / 24,260 both runs; owner verdicts decided/abstained Litolff NEW 9,286/136 vs BASE 9,213/209, Brahms 33,557/486 vs 33,504/539 (far heads only); non-far-head owner verdicts identical; clef verdicts 0 changed (317 decided, 10 narrowed, 4 abstained; 690/1/0); meter 0 changed (31 decided; 5 decided, 48 abstained). No change over 2% outside the far-head population.

**5. Sheet** `out/print/ledgers/night_1006_sample.png` (+ `.json`): 12 seeded (20261006) NEW decisions, 6 per document, 8 differ from BASE (both decided, different) and 4 agree; slivers excluded. Drawn lines re-measured against pixel rows: 40 lines, 28 within 2 px of an ink row, 3 off by 2.5-3.5 px (tiles 1 and 10 note line, tile 6 ledger 2), 9 have no ink beside the head to measure. NOT yet adjudicated by Sean.
## lane-staff-lines-off-ink (2026-10-06): recorded staff lines vs the printed ink -- COUNT and CAUSE (no fix built)

STAGED and LEGACY share `staff_detector.detect_staves`. Scripts: `staff_lines_off_ink.py` (a: raw staff-wide lines vs ink), `staff_lines_per_bar.py` (b: the per-bar grid, `measure_extractor._cell_line_offset` shift added to `staff.line_ys`), `*_summary.py`, `staff_lines_off_ink_sheet.py`; sheet `out/print/staff_lines_off_ink.png` (red = raw staff-wide lines = what the far-head path reads; blue = per-bar grid in-staff positions read). Records: 10-06 night-combined, all 1,022 staves (Litolff 331, Brahms 691), 10 clean columns each (five even thin runs, none on a head or barline), on `render_page_matching_gather`.

**Controls.** `detect_staves` on that frame reproduces every recorded `Q.STAFF_LINES` row exactly (1,022 of 1,022): no frame mismatch. Printed spacing vs recorded: median gap error 0.8 px; a recorded gap >10% off the staff's own median on 23 Litolff / 63 Brahms staves (mostly +-1-2 px rounding on a tilted line; real mis-detections 2/1/10 Litolff, 7/0/5 Brahms where line 5 is 8 px short).

**(a) raw staff-wide lines vs ink, all samples.** Litolff |offset| median 1.5 px, p90 6.5, max 16 (0.095 / 0.41 / 1.0 sp); Brahms 1.5 / 6.0 / 27 px (0.055 / 0.22 / 0.98 sp). Staves with any point >= 0.25 sp: 521 of 1,022 (Litolff 231, Brahms 290); >= 0.4 sp: 266 (169, 97). Shape of the 521: 479 TILT (offset linear in x, residual sd ~1 px, tilt up to 20 px across a staff), 31 constant shift, 11 wander, 0 per-line. Signed median 0.0 px (Brahms) / -0.5 px (Litolff): **the "1-1.5 px upward bias" is NOT in the lines vs the binary the detector read** (gray centroid agrees, +0.05 px); it is a convention of whatever it was measured against.

**Cause (a).** `detect_staves` records ONE y per line from the whole-page row profile. The page is deskewed by ONE angle (`preprocessing.deskew`, 0.25 deg Hough steps, skipped under 0.1 deg: Brahms p7/12/17 get exactly +-0.2500 deg), and a scan's systems tilt by different amounts and in opposite directions on one page (Brahms p1: +3 px vs -15 px across systems; Litolff p16: system 0 -10..-15, system 1 +5..+10), so a staff 4,850 px wide ends 10-20 px (0.4-1 sp) off at one end. Litolff p16 16/0/1: tilt -11.9 px, so ~0.6 sp at the ends. Hypotheses tested: frame mismatch REFUTED (exact reproduction); beam/text taken for a line: only the two staves above; wrong spacing: 0 per-line cases, 3 + 40 staves with printed-vs-recorded gap >= 3 px.

**(b) the per-bar grid (what in-staff positions use; default ON, `OMR_CELL_LINE_TRACE`).** Per cell (Litolff 5,242, Brahms 6,595 with >= 2 clean samples), cell median offset >= 0.4 sp: raw 403 / 55 -> per-bar 17 / 8; >= 0.25 sp: 851 / 397 -> 18 / 10; any point >= 0.4 sp: 630 / 361 -> 54 / 175 (includes tilt inside one bar: median 0.5-1.0 px, p90 1.6-2.7 px, >= 0.25 sp in 26 / 72 cells). Cell median |offset| 0.5 px, p90 0.5 px (Litolff) / 1.5 px (Brahms).
**(c) the far-head path** reads `st.line_ys` straight (`staged/gather.py` on `lane-local-staff-lines`: `staff_lines[...] = st.line_ys`, `global_lines=lines`), i.e. (a), and never sees the cell shift. A far head sits in a cell, so (b) is what it should have been given.

**Plain finding.** In-staff pitch is roughly right (per-bar grid within ~1 px on almost every bar). The huge error is that the far-head reader/owner witness read the raw staff-wide lines instead of the per-bar grid. Remaining in-staff failures are ~25 cells (17 Litolff, 8 Brahms) where the per-bar search cannot reach (shift capped at 0.75 sp, `CELL_LINE_MAX_SHIFT_SPACES`; or locks one line over, e.g. Brahms 7/0/5 with the short 5th line: comb scores -13 px 6507 vs +15 px 6751) and a few cells never shifted at all (13, both docs), all on staves tilting >= 1 sp. The far-head code is not on main, so no fix was built here; the next step is lines = `st.line_ys + cell.line_grid_localized['offset_px']` in that lane (and for the worst staves a tilt-seeded cell search, a new mechanism needing a roadmap line). Sheet control, drawn lines vs pixel rows at the nearest clean column, 24 tiles on the 8 worst staves: red within 2 px on every line 8/24, blue (per bar) 13/24.
## verify-staff-line-offsets (2026-10-06): an INDEPENDENT re-measure of lane-staff-lines-off-ink (40aab116)

STAGED and LEGACY share every function measured here. Script written from scratch, `verify_staff_line_offsets.py` (none of the lane's scripts read or imported); records read only through `record_io.load_record`; sheet `out/print/verify_staff_line_offsets.png`. All 1,022 staves (Litolff 331, Brahms 691), all pages, `preprocessing.render_page` called once at the record's dpi (600).

**Measure.** Ink row of a line at x: a strip 0.2 sp wide (>= 3 px), window from 1.5 sp above the recorded top line to 1.5 sp below the bottom one; a row is ink if >= half the strip is ink. The column counts only if the window holds EXACTLY five dark runs, each <= 0.4 sp thick, consecutive centres within 20% of the recorded spacing -- so no head, stem, barline, beam, ledger, slur or text is anywhere in it, and line k is run k. Every 0.5 sp along the staff; median 126 (Litolff) / 163 (Brahms) clear columns per staff. Controls: (i) synthetic 5-line staff, 12 px tilt over 4,000 px, with heads, stems and a beam: fitted tilt 11.99 px, every point within 0.49 px (nearest-row rasterisation; a measure blind to tilt would err 6 px); (ii) recorded lines moved +3 px on a real staff are read as exactly +3.00 (157 / 128 columns). (e)-style controls: re-running `detect_staves` reproduces 1,022 / 1,022 recorded line sets and extents, `extract_measures` reproduces 12,062 / 12,062 `Q.CELL_BOX`, and the reconstructed per-bar grid (`staff_line_ys_canonical` = `line_ys + _cell_line_offset` shift, upscaled) reproduces EVERY recorded `NOTEHEAD_STAFF_POSITION` (35,659 heads, max error 0.005 step); the unlocalised grid misses by a median 0.22-0.24 step on heads in shifted cells, so that check can fail.

| claim | verdict | my number |
|---|---|---|
| (a) raw lines off ink: median 1.5 px, p90 ~6, max 16 / 27 | CONFIRMED, except the Brahms max | median 1.5 / 1.5 px, p90 5.5 / 5.5 px, max 17.5 px (1.11 sp) Litolff / 19.5 px (0.70 sp) Brahms. I find no 27 px point at a clear column. |
| (a) 521 staves >= 0.25 sp somewhere, 266 >= 0.4 sp | CONFIRMED | any line: 531 (230 + 301), 267 (163 + 104); five-line mean per column: 462, 210 |
| (a) shape: 479 tilt / 31 shift / 11 wander / 0 spacing | TILT-DOMINANT CONFIRMED, the split WRONG | my rules (straight-line fit to per-column mean offset): spacing = five lines' median spread >= 0.2 sp; wander = residual >= 0.2 sp; tilt = fitted change >= 0.25 sp across the staff; else shift. Litolff 127 tilt, 78 tilt WITH a bow (residual 3-5 px, i.e. curved), 2 shift, 4 spacing; Brahms 235 tilt, 11 spacing, 4 shift, 1 wander. Tilt up to 19.8 / 24.4 px. **15 staves have one recorded line 5-10 px off its siblings** (e.g. Brahms 1/1/6 recorded gaps 27, 22, 33, 28; 7/0/5 line 5 ~10 px high): "none wrong spacing" is false. |
| (a) cause: one y per line after a single-angle deskew | CONSISTENT (not separately tested) | offsets are linear in x within a staff and reproduce exactly from `detect_staves` |
| (b) per-bar grid: >= 0.4 sp cells 403 -> 17 (L), 55 -> 8 (B) | CONFIRMED in kind | cell median >= 0.4 sp: 383 -> 21 (L), 45 -> 1 (B); >= 0.25 sp: 791 -> 21, 369 -> 3. Within-bar range median 0.6 / 1.4 px, p90 1.4 / 2.5 px. Cell median abs offset after the shift 0.3 / 0.5 px (p90 0.6 / 1.4). |
| (b) the ~25 cells left wrong | CONFIRMED, cause sharpened | all 21 Litolff cells sit 13-17 px = ONE WHOLE SPACING off with the shift at 0 to +-2: the needed shift (15.5 px) exceeds the 12 px cap (`CELL_LINE_MAX_SHIFT_SPACES` 0.75) and at shift 0 four of five comb rows already lie on printed lines, so the comb locks one line over. Every head in those cells is 2 steps off. Brahms 7/0/5 cell 8: shift +15 against a needed -10 (the short line 5). |
| (c) far-head path reads the RAW lines | PARTLY WRONG | it is SEEDED with raw `st.line_ys` (`staff_lines[...] = [float(y) for y in st.line_ys]`, `global_lines=lines`) but `FarHeadPage.read` immediately calls `lines = frame_lines_for_head(self.gray, global_lines, box)`, which re-measures each line as `_darkest_row` in two head-wide flank bands within +-0.5 sp of the raw line, falling back to raw only if neither flank finds five. Scored at my clear columns (that code exec'd from the branch): raw < 0.25 sp off -> all five found, 0 lines >= 0.5 sp wrong; raw >= 0.5 sp off -> Litolff 541 of 617 lock ONE LINE OVER (median -15.5 px). So the raw error reaches the far-head reader only where it is large, through the +-0.5 sp search window. It never sees the cell shift. |
| (d) no ~1-1.5 px global upward bias | CONFIRMED for the recorded lines; the bias EXISTS in the far-head re-measure | recorded lines vs ink, signed median 0.0 px both docs (mean +0.79 L, -0.23 B). The far-head `_darkest_row` reads a median **-1.5 px (both docs)** on lines read correctly: `argmin` returns the TOP row of a 4-7 px line. That is very likely where the earlier "1-1.5 px upward" figure came from. |
| (e) `detect_staves` reproduces all 1,022 | CONFIRMED | 1,022 / 1,022 exact, 0 extra staves |

**The lane's sheet 8/24 red, 13/24 blue.** It was the measure, not a drawing bug: the sheet drew the 6 WORST raw staves plus 2 picked BECAUSE their per-bar grid was still wrong, at the first / worst / last clean column, and required all five lines within 2 px. That selection on my measure gives 6/16 red and 11/16 blue. One random clear column on 200 random staves: 118/200 red, 180/200 blue; over all 158,326 clear columns, 53% red and 87% blue (2 px is tight on Brahms' 7 px lines with 1.4 px of within-bar tilt). One minor fault in its control: the "nearest clean column" loop took the FIRST clean column from x-40, not the nearest.

**Sheet** (`out/print/verify_staff_line_offsets.png`, 600 dpi, x3 Litolff / x2 Brahms): rows 1-3 are the three worst raw staves (one per page; all are the one-spacing Litolff case), rows 4-6 random (seed 20261006). Red = raw recorded line_ys, blue = per-bar grid, green tick = my ink centre. Every drawn row was re-read from the tile's own pixels: max 0.25 px from where it was meant to go. In rows 1-3 red AND blue sit one full space above the print at the ends of the staff, which is the capped/aliased case seen on the print.

**Plain finding.** The lane's headline numbers hold up: the raw lines are off by tilt and the per-bar grid fixes nearly all in-staff bars. Two of its statements are wrong: "no wrong spacing" (15 staves have one recorded line 5-10 px off), and "the far-head reader reads the raw lines" (it re-measures locally, but its +-0.5 sp window inherits a large raw error by locking one line over, and its darkest-row pick reads 1.5 px high). The ~21 residual Litolff cells are exactly one spacing off, so every head in them is read two staff steps (one line) off.

## lane-mark-identity (2026-10-06/07) -- one identity per physical mark (ROADMAP 2.58 relocate-at-export, 2.58b `Q.MARK_GROUP`; both default OFF)

Sean 10-06: a head that belongs to another staff is RELOCATED and written there, never dropped; every mark exists once. Flags `OMR_RELOCATE_AT_EXPORT` (export) and `OMR_MARK_GROUPS` (gather; `glyph_owner` + export read the rows where present). Sheets: `out/print/mark_identity_relocate.png`, `out/print/mark_identity_groups.png` (seeded 2058, real 600 dpi print x3, drawn staff lines re-measured: snapped to the darkest pixel row within 0.4 sp, ink-on vs ink-half-a-space-off control printed per tile, 0 failures).

**Method / limits.** Records are the 10-06 night-combined shared records, REBUILT (`mark_identity_rebuild.py`: GATHER rows -> ADJUDICATE -> EVALUATE on today's tree, no detector). Control: with the flags the record was made under (`OMR_FARHEAD_OWNER_LEDGERS=1 OMR_OWNER_FROM_STAVES=0`) the whole-Litolff `glyph_owner` (outcome, reason) census REPRODUCES exactly. ⚠️ The numbers below are PAGE SUBSETS (Litolff pp. 2,3,4,6,7,13,14 = 69 of 105 candidate heads; Brahms pp. 1,2,3,5,11,12,13 = 195 of 362) and under `OMR_OWNER_FROM_STAVES=0`: with it ON (today's main default) the same rebuild of whole Litolff had not finished adjudicate+evaluate after 60+ min against 17 min with it OFF (7 pages: 152 s OFF; a 7-page Brahms run was killed at 50 CPU-min) -- **a perf regression in the default-ON tier, not investigated here**. Brahms subset exports hold almost every bar out (no whole-document identity), so Brahms figures are PLACEMENT-level (`fates`), not file-level. Counts are per head/mark, not per bar.

**Part 1 -- relocate (EXPORT).** The CLAUDE.md claim "a glyph_owner verdict naming another staff implies a twin" is now CHECKED (page box IoU > 0.3 on the owner staff) instead of assumed; with a twin the old drop stands. Without one: the head goes into the owner's cell at its x, bbox re-expressed in that cell's canonical frame, pitch from `move_glyph`. Two connections were needed, neither a guess: (1) `move_glyph` had no position for a head the owner holds no copy of (no band row toward it), so it now reads `Q.FAR_HEAD_OWNER_LEDGER` for that candidate -- the very reading `ledger_note_first` named the owner from; (2) `not_a_notehead:belongs_to_a_nearer_staff` is an ownership claim, so under the flag it goes through the same stage (31 of the 105). Refusals are named: `relocation_collides` (head within 0.75 sp of one the owner's cell holds), `relocation_not_repitched` (pitch not move_glyph's), `relocation_no_cell_at_x`, `relocation_no_frame`, `relocation_no_page_box`. A key-signature alteration is re-derived from the OWNER's key (the home key's was applied to a letter that has since changed); a printed accidental is kept.
- The "written nowhere 105 / 362" counted heads BEFORE the notehead filters: of Litolff's 116 owner-elsewhere/no-twin heads 54 are `clipped_fragment`, 16 `too_narrow` (box faults, still counted, NOT relocated -- a clipped box has no trustworthy centre), 31 `belongs_to_a_nearer_staff` (relocatable), 5 reach the owner stage.
- Litolff 7 pages: 21 candidates -> 12 written on the owner, 1 `relocation_collides`, 4 `staff_not_identified`, 4 `duration_narrowed`. Brahms 7 pages: 32 -> 28 written on the owner, 1 collision, 2 `ink_is_a_whole_rest`, 1 `duration_narrowed`. No glyph written twice (asserted over every cell); `Unbalanced` never raised; accounting equality holds ON and OFF.
- Sheet A: 12 relocated + the 2 collisions that exist in the subsets (14 tiles). Several relocated "heads" are not heads (a slur underside, a flat 63x10 px box): relocation moves whatever the notehead gates passed.

**Part 2 -- groups (GATHER + ADJUDICATE + EXPORT).** `Q.MARK_GROUP` filed on every notehead / rest / accidental box (IoU > 0.3, same family, same system; a singleton gets a group of one). Dynamics are NOT grouped: dedupe FINDINGS 6.3 measured the two `f` of an `ff` at IoU 0.317. `ownership.reconcile_group_owners` (after `glyph_owner`): decided members agree -> abstained / uncontested members take that owner (new verdict, `supersedes` the old, basis the decided ones); conflict -> nothing filed (counted); all silent -> nothing. EXPORT writes the most confident member once, counts the rest `mark_group_duplicate`; `marks_census` per family partitions marks into written once / counted under a reason / written more than once / `unaccounted` (a test requires 0; accidentals report gathered marks only -- their export fate is not tracked per mark).
- REAL small re-gather, Litolff pp. 1-3, flag off vs on: +2,041 `mark_group` rows and NOTHING else changes (glyph_box, notehead_staff_position, staff_lines, clef, meter, duration, not-a-notehead verdicts identical); 6 `glyph_owner` abstentions become decided by the group rule. Wall 456 s off / 465 s on (machine loaded by other lanes; the grouping is one pass over boxes, 13,265 groups for the whole movement in seconds). Brahms p0-1 small re-gather timed out at the tool's 900 s step limit in BOTH arms under load -- NOT measured.
- Written 2+ times (clustered off page boxes, independent of the rows): Litolff pp.1-3 16 (14 same-cell, 2 cross-staff) -> 0, written once 849 -> 865; Litolff 7-page subset 66 (56 / 10) -> 0; Brahms 7-page subset 12 (10 / 2) -> 0. Marks written nowhere stay the same set, all under named reasons (largest: `staff_not_identified`, `too_narrow`, `duration_narrowed`, `no_pitch`). Residual worth a lane: 146 Litolff-subset marks are written nowhere under `owned_by_another_staff` -- the owner's copy exists but was refused for ANOTHER reason (stacked-head duplicate, duration, pitch), so the ink is lost by a rule on the twin, not the head. Whole-movement 201 / 56 not re-measured (page subsets only, see above).
- Truth-set far heads: the far-head rows are not touched (the small re-gather's `far_head_*` rows identical off/on, both zero because `OMR_FARHEAD_LEDGER` is off in that arm); `farhead_all_wired_eval.py` not re-run.

Tests: `test_relocate_at_export_2026_10_06.py` (15; 6 of the first 8 RED on the old tree), `test_mark_groups_2026_10_06.py` (17). Fast tier 4,574 passed; `staged.check` TOTAL 247 -> 247. Existing stubs of `_place_notes` (`test_staged_export`, `review/rerun.py`, `omr-notehead-funnel-2026-09/probe/funnel.py`) now forward `**kw`; deferred refusals re-parse their subject so the stage-review probes attribute them correctly.

## OMR_OWNER_FROM_STAVES default-ON made ADJUDICATE quadratic -- FIXED in `Log._index` (lane-owner-from-staves-speed, 2026-10-07)

Cause (ADJUDICATE, STAGED; GATHER is unaffected, p3 gather 58 s off / 52 s on): `ownership._owner_from_staves` calls `ev.subjects(Kind.STAFF)` once per head, and `Log.subjects` cleared its cache on EVERY write, including each `glyph_owner` verdict. So every head re-parsed every row key of the whole document (~4M `Subject.from_key` per head on Litolff p3). Fix: `_index` clears the cache only when a row is filed under a subject key never seen before. Verdicts are on existing subjects, so `subjects()` is unchanged by construction.
`glyph_owner` stage, flag on, one page (rebuilt from the 10-06 night-combined records), old -> new: Litolff p3 23.7 s -> 0.36 s, p4 122.6 s -> 1.18 s, Brahms p1 190.5 s -> 3.46 s (flag off: 0.07 / 0.19 / 0.41 s). `glyph_owner` verdicts compared row by row (outcome, value, reason), old code vs new, flag off and on: 314 / 972 / 1,414 verdicts, 0 differ. (The flag itself still changes 2 / 13 / 108 verdicts vs off, as before.) Whole Litolff re-adjudicate, flag on, new code: 637 s; the old code did not finish in 60+ min.

## 2026-10-07 -- lane-edge-merge-unseen-ledgers: why the reader lost four ledgers the print shows plainly (STAGED far-head reader; ROADMAP 2.57c; `READER_KEYWORDS` `edge_jut_kept`, `split_welded_bands`, `rows_clear_of_box` ON, `walk_tol` OFF)

Sean (2026-10-06, `lines_combined_5.png`): fix the edge-merging rule; "do we know why it doesn't see the ledger lines? They seem clear." Branch `lane-edge-merge-unseen-ledgers` from `origin/main` 87d17c00. The page was never the problem: in four of five the band finder DID measure the ledger; a later step threw it away.

**Why, head by head (row measurements, px at 600 dpi).**
1. Truth `brahms 1/1/8/7/4` (13): ledger row 6140, 7-8 px thick (cap 9.6), juts 6.3 px left / 10.7 right (floor 4.1): measured as a ledger. `collapse_head_edge_rungs_to_middle` then saw 6140 (1.2 px inside the box top 6138.8) and 6168 (a slur under the head: its ink ends 5.7 / 9.3 px INSIDE the head's columns, no jut; 4.3 px inside the box bottom 6172.3), both within 0.25 sp (6.9 px) of the box edges and adjacent: "the box's own outline", both dropped.
2. `brahms 19/1/0/5/10` (-3): the same step. Rungs 4103.5 (8 px thick, juts 5.0 / 5.9) and 4075.0 (the head's own top outline: -9.0 / -3.1, no jut) against the detector box 4070.6-4102.8, both dropped. The 0.16-vs-0.15 box gate only decided WHICH box was used (the standard box's edges would have kept 4103.5 by luck); it is not the cause and was not touched.
4. `brahms 4/0/0/9/15` (-3): a head in the space between two real ledgers, 506.5 and 474.5 (5-6 px thick, juts 5.8 / 7.4 and 5.8 / 8.4), box 471.8-505.5 (1.22 sp), edges 1.0 and 2.7 px away: the pair that "cannot be the outline" of a 1 sp box is a ledger pair around a 1.22 sp one; both dropped.
5. `brahms 14/0/1/0/6` (-5): rows 710-739 are one region of "long" rows because the head body is 38-39 px against a rung floor of 1.3 sp; the ledger plateau (rows 732-738, 52-55 px, juts 7 px) stands 14 px above the body but only the region's WIDEST plateau (rows 712-717, 55 px: head + flat sign) became a band. The old lines escaped by luck: row 719 measured 36 px against a floor of 36.1 (sp 27.75) and cut the region in two; at sp 27.5 the floor is 35.75 and it joined.
3. `lito 5/0/5/9/0` (-6): NOT FIXED. The ledger at 1414.5 is a hand-drawn bar 27 px wide, 5.9 px under the box; two steps refuse it, each by a fraction of a pixel: the walk window (13.5 px gap against 0.65 x the previous 21.0 = 13.65: the staff line is now read at its centre, which made the first gap 21.0 instead of 19) and `_rung_row_clears_box` (27.0 px against a 25.5 px box + 0.1 sp = 27.08).

**Rules (stated before the runs).** (a) A rung at the head's edge that shows a thin flat connected jut past the head (>= 0.15 sp, on at least one side, <= 0.35 sp thick: `thin_flat_jut_evidence`) is a ledger and is never merged; only the pair member WITHOUT a jut collapses (`keep_edge_juts`). (b) `split_welded_bands`: a region of long rows holds every thin plateau that stands >= 0.30 sp (two stubs) above the rows between it and the next plateau; one found only this way must jut past the head and lie on the staff side of its middle. (c) `rows_clear_of_box`: a rung more than half a line thickness clear of the box's rows on the STAFF side is not the head's own widest row, so it need not be wider than the head. (d) walk window +-0.5 px (`walk_tol`).

**(d) was tried, measured and REFUSED; the first (a), (b), (c) variants were corrected by the out-of-sample runs.** Half a line thickness (2.5 px) on the walk window admitted four heads' own middle rows (0.57-0.61 of the last gap) as rungs; +-0.5 px (band centres sit on a half-pixel grid) rescued only night 12 and moved five right Brahms heads one ledger out (attribution run per switch alone on Brahms pp.2,4,10,13,16,17: `walk_tol` 5 changes, all five losses). It is OFF. Night 12 stays abstained: every tolerance wide enough to take 13.5 vs 13.65 takes a head's own middle row at 0.61. Rule (c) without the staff-side condition let a slur above a head in as a rung; requiring the jut on BOTH sides for (a) lost 21 gains and fixed nothing, so one side is kept (Sean's `one_sided`); (b) without the jut and staff-side conditions added a head's brim (2 right Brahms heads lost).

**Controls (this tree, switches on vs off; `edge_merge_truth.py`, `edge_merge_report.py`, `edge_merge_attrib.py`).**
- Truth set: Litolff 39/0/2 -> 39/0/2; Brahms 10/0/1 -> **11/0/0** (the broken head `glyph/1/1/8/7/4` regained, answer 13). 0 right heads broken.
- Sean's 44 confirmed tiles (10-06 records): 0 broken; **3 regained** (note_first 2, edge_flip 1, edge_flip 12); night 12 still abstains.
- Out of sample (10-06 night records, full pages, the per-bar-grid reader before vs after; `farhead_per_bar_grid_oos.py` vs `edge_merge_oos.py`): Litolff pp.4-16 decided 1,788 -> 1,847 (+59 abstain -> decided, 0 decided -> abstain, 0 moved), implausible 8 -> 8; Brahms pp.2-26 decided 3,819 -> 3,998 (+180, **1 decided -> abstain**: `4/1/4/3/2` -4 -> `count_does_not_fit`, 0 moved), implausible 6 -> 6. Per switch alone on Litolff: `edge_jut_kept` +32, `rows_clear_of_box` +19, `split_welded_bands` +4, `walk_tol` +1.
- Sheet `out/print/ledgers/edge_merge_fix.png`: 12 seeded (20261006) changed out-of-sample heads, before | after, staff lines cyan 1 px, every rung found yellow 1 px, answer rung magenta, box orange, answer in words; the five heads `edge_merge_fix_5heads.png`; the one loss `edge_merge_movers.png`. Drawn lines re-measured against the page's pixel rows: staff lines median 0.25 px (max 1.75); rungs that have jut ink beside the head to measure: median 0.01 px, max 2.0 (most through-the-head rungs have none to measure). NOT yet looked at by Sean: the gains are judged here only by the five known answers and the 44.
- Unit tests `test_edge_merge_unseen_ledgers_2026_10_06.py` (11): RED on the unrepaired tree (9 failed, by the missing parameters), green after, each switch with a same-class control; fast tier 4,537 passed; `staged.check` 250 -> 250. The legacy paths pass none of the switches and are bit-identical.

**Limits.** `edge_jut_kept` may be fooled by a stroke that lands on a head's edge on one side. `split_welded_bands` and `walk_tol` interact (welded alone lost 2-3 Litolff heads that the others repaired). The truth and 44-tile controls cannot fail on gains.

## 2026-10-07 -- lane-export-unbalanced-brahms: six heads written to a bar the file does not have (STAGED EXPORT, `_place_notes`; no flag)

**Record.** The 10-07 night Brahms record (`...-whole-20261007-night.record.json`, through adjudicate) REBUILT through EVALUATE by `mark_identity_rebuild.py` (the lane-mark-identity work file, 7 GB, not regenerated here). Export read from it via `load_record`, in one process, four arms: mark-group rows stripped or kept x `OMR_RELOCATE_AT_EXPORT` off/on. No gather, no re-adjudicate.

**Does main balance? No -- with all three flags off it raises too.** The 6 are the same in all four arms (off/off 7,170 written; groups 7,164; relocate 7,152; both 7,146). So this is not a flag defect; the 10-07 FINDINGS' "relocate-off arm" was just the first arm run.

**The six** (page 0, system 0, cell 7; staffs 4, 5, 5, 9, 11, 13): `glyph/0/0/4/7/2`, `glyph/0/0/5/7/0`, `glyph/0/0/5/7/1`, `glyph/0/0/9/7/0`, `glyph/0/0/11/7/0`, `glyph/0/0/13/7/1`. All whole-note heads at the left of the system; each staff's `measure_partition` says 7 bars (cells 0-6). `_place_notes` filed each into `run.cells[7]` and marked it `written`; `_part_xml` walks `range(run.n_measures)`, so cell 7 is never rendered. Written nowhere, counted nowhere. (My first probe also flagged 20 `written_value_fits_no_note` heads -- those were a filter bug in the probe, they ARE counted.)

**Fix.** After the owner staff and cell are known (so it covers a relocated head's cell too): a head whose cell index is at or past the staff's bar count is counted, not written -- `cell_past_the_last_bar` (partition decided), or `bar_count_not_decided` (partition abstained, `n_measures` 0). No catch-all. `test_export_cell_past_last_bar_2026_10_07.py` (6 tests, all four flag combinations, positive control in each class): RED on the unrepaired tree (4 of 6 failed, the first with exactly `Unbalanced: 1 noteheads+rests in the log, 0 written and 0 accounted`), green after. Fast tier 4,594 passed; `staged.check` 247 -> 247. All four Brahms arms now balance.

**The counts the night read could not give** (per physical mark = `Q.MARK_GROUP` group over the 10-07 gather; final fate: written / counted under a reason / held out at render by `bar_does_not_add_up`; heads 20,295 marks, rests 7,259):

| arm | heads written once | heads 2+ times | heads nowhere | rests once | rests 2+ | rests nowhere | heads relocated | `relocation_collides` |
|---|---|---|---|---|---|---|---|---|
| off (no groups, no relocate) | 5,156 | 9 | 15,130 | 1,992 | 1 | 5,266 | 0 | 0 |
| groups only | 5,171 | 0 | 15,124 | 1,993 | 0 | 5,266 | 0 | 0 |
| relocate only | 5,139 | 9 | 15,147 | 1,991 | 1 | 5,267 | 59 | 5 |
| both | 5,154 | 0 | 15,141 | 1,992 | 0 | 5,267 | 59 | 4 |

Groups remove every double write (9 heads + 1 rest to 0; `mark_group_duplicate` 59-60). Relocation writes 59 heads on their owner, refuses 4-5 as collisions, and takes `owned_by_another_staff` 2,714 -> 2,664 and `belongs_to_a_nearer_staff` 65 -> 50. Heads written nowhere, groups arm, by reason: `bar_does_not_add_up` 8,010, `too_narrow` 3,142, `duration_narrowed` 1,790, `owned_by_another_staff` 1,198, `clipped_fragment` 411, `stacked_head_duplicate` 339, `belongs_to_a_nearer_staff` 62, `staff_not_identified` 55. Rests nowhere: `bar_does_not_add_up` 4,290, `rest_clipped_by_crop` 531, `rest_is_a_duplicate_box` 125, `rest_outside_its_staff` 115. Every subject has a group row, none unaccounted. A mark the group shares across staves can read "nowhere" under a different member's reason than the report's per-subject total (59 `mark_group_duplicate` are bookkeeping, not losses).

**`bar_does_not_add_up`.** 13,597 subjects tonight (groups arm; 13,650 with no groups, 13,727 relocate-only). The only prior Brahms figure on disk is `benchmarks/acceptance/current.json` (an earlier through-INFER whole-movement export): 12,927. So +670 (+5%). NOT the 10-06 record, which was not exported; not investigated.

**Limits.** One record, one tree. Why the partition says 7 bars where the detector cut an eighth cell on page 0 system 0 is not investigated (a partition or cell-cut question, not an export one).
## night-1007-read (2026-10-07): the 10-07 night records vs the 10-06 night-combined records (STAGED, GATHER+ADJUDICATE; READ ONLY, no gather)

NEW = `...-mvt1-whole-20261007-night.record.json` (tree 3aef0c7d, clean; defaults ON plus `OMR_FARHEAD_OWNER_LEDGERS=1 OMR_MARK_GROUPS=1 OMR_RELOCATE_AT_EXPORT=1`). BASE = `...-20261006-night-combined.record.json`. Scripts: `night_1007_extract.py` (one `load_record` per record feeds everything), `night_1007_replay.py` (the 10-06 replay, now fed the PER-BAR grid; without it the replay disagreed with the record on 13% of heads, with it 99.7% / 100%), `night_1007_report.py` (reuses `night_1006_report`), `night_1007_marks.py`, `night_1007_timing.py`, `night_1007_sheet.py`, staff lines via `verify_staff_line_offsets.py` (env `VSO_SCRATCH`, `VSO_DOCS`; BASE measured with `OMR_CELL_LINE_FIND=0`). Printouts `out/night_1007_*`. Heads matched across runs by box overlap.

**1. Run time (Litolff 30 min vs 26, Brahms 175 vs 107).** The records and logs hold only whole-run wall time, so the steps were timed on saved rows/pages. ADJUDICATE is the slower stage: re-adjudicating the whole Litolff record took 656 s with `OMR_OWNER_FROM_STAVES` ON (NEW) vs 296 s OFF (BASE), +6 min, the size of the +4 min the night lost (control: both rebuilds reproduce the saved `glyph_owner` census exactly). GATHER steps are not it: `OMR_CELL_LINE_FIND` on vs off costs 0.67 vs 0.62 s/page (Litolff), 1.28 vs 1.18 s/page (Brahms); the 10-07 far-head reader vs the 10-06 one costs +1.4% per head (7.11 vs 7.01 s per 180 heads; Brahms 25.3 vs 24.8 s per 263). So the owner-from-staves rule is still about 2.2x its off cost AFTER the `Log._index` fix. Brahms +68 min is taken to be the same step on 2.1x the heads (the full Brahms re-adjudicate was started to confirm; see the end of this section). The machine was shared with other lanes.

**2. Staff lines.** Bars whose per-bar grid is >=0.4 sp off the ink (median over >=2 clear columns): Litolff 21 -> 0 of 4,934 measurable bars; Brahms 1 -> 0 of 6,489 (raw staff-wide lines: 383 / 45, unused by in-staff heads). Control: the rebuild reproduces the record's own positions (331/331 and 691/691 staves, 5,377/5,377 and 6,685/6,685 cells, max head error 0.005 half-step). In-staff heads whose position changed: Litolff 32 of 7,197 (16 up 2 half-steps, 16 down 2); Brahms 12 of 15,294 (7 by -1, 5 by +2). Far heads whose geometry position changed: 28 / 3.

**3. Far heads.** Litolff 4,196: decided 2,021 (BASE 1,903), abstained 1,714 (count_does_not_fit 799, no_rungs 565, no_line_at_the_note_box 304, line_not_a_ledger 33, line_not_beyond_edge 13), not-a-note 461 (449). Brahms 8,966: decided 4,286 (4,055), abstained 3,277 (1,881 / 690 / 645 / 31 / 30), not-a-note 1,403 (1,405). Sean's through-or-edge rule: on the reader's own measured rows Litolff 94.9% vs 94.6%, Brahms 98.1% vs 98.1% (same heads in both runs: 95.5 vs 94.8, 98.3 vs 98.2; same answer 97.6% / 97.7%); on the reader-independent grid rows Litolff 82.8% vs 84.6%, Brahms 96.8% vs 94.9% (plain geometry on the same rows 85.2 / 98.3: on the grid rows the reader is BELOW geometry in both documents; Litolff's grid is biased, ledgers ~1.08 sp). Control still fails where it should: truth references pass 97% / 100%, one-step shifts flagged 84% / 100%, the one wrong truth head is OFF. Truth set (41 Litolff + 11 Brahms): Litolff right/wrong/undecided NEW 37/1/3, BASE 36/1/4 (regained `3/1/0/9/2`; still wrong `3/0/0/2/4`, -6 for -7); Brahms 11/0/0 both.

**4. Ownership and marks.** Owner verdicts matched by box (all heads): Litolff 74 changed (21 decided -> another staff, 43 abstained -> decided, 10 decided -> now the filing staff; by rule `group_owner` 37, `ledger_note_first` 24, `distance` 10); Brahms 65 (26 / 27 / 9, plus 3 decided -> abstained; `group_owner` 22, `ledger_note_first` 22). Owner abstentions: Litolff 136 -> 93, Brahms 486 -> 456. Noteheads detected 2+ times (same boxes in both runs, a GATHER fact; the `Q.MARK_GROUP` rows reproduce my IoU>0.3 clustering exactly): Litolff 2,009 of 9,047 marks (2,352 extra boxes; rests 97 of 2,773), Brahms 3,826 of 20,295 (3,965 extra; rests 769 of 7,259). EXPORT side (rebuilt through EVALUATE on today's tree, `mark_identity_relocate_eval.py`, whole Litolff only): noteheads written 2+ times BASE 171 -> NEW 0; written once 6,890 -> 7,093; written nowhere for a real reason 1,341 -> 1,339 (largest: staff_not_identified 392, no_pitch 361, duration_narrowed 306, ink_is_a_whole_rest 109); marks that are not heads only 645 -> 615; `Unbalanced` never raised. Relocations: 30 heads written on the staff that owns them (16 owned_by_another_staff, 14 belongs_to_a_nearer_staff), 3 refused as colliding (BASE rebuilt with the same flag on: 25 / 7). Brahms export side: see the end of this section.

**5. Other movers (>2%).** Litolff `empty_bar_rest_search` read 243 -> 355 and `empty_bar_whole_rest` abstained 129 -> 240 (decided 114 -> 115): a GATHER difference, not investigated here. Noteheads gathered (11,399 / 24,260), clef (0 verdicts changed), meter (0 changed) and every non-far-head count: no change over 2%.

**6. Sheet** `out/print/night_1007_sample.png` (+ `.json`), seed 20261007, 12 tiles on pages the rules were not written on: 4 far heads BASE gave up on, 4 far heads BASE answered differently, 2 owner changes, 2 in-staff heads moved by the staff-line fix. Orange box, magenta (NEW's staff line / edge), green (ledgers), red (NEW's note line), azure (BASE's), all 1 px at 3x. Drawn lines re-measured against pixel rows: 34 NEW lines, 20 within 2 px of ink, 5 off by more than 2 px (tile 3 note line 2.5, tile 4 note line 6.0, tile 5 owner-staff line 5.1, tile 11 line 3 2.1 and line 5 5.1), 9 with no ink beside the head to measure. BASE's in-staff lines (tiles 6, 11) also sit on ink: on the NEIGHBOURING line, which is the one-line-over fault. NOT yet adjudicated by Sean.

**Brahms export side (added later).** Whole-Brahms rebuild through EVALUATE on today's tree: adjudicate 7,048 s (117 min, `OMR_OWNER_FROM_STAVES` on), evaluate 276 s; `glyph_owner` census reproduced. The export then RAISED `Unbalanced` in the relocate-off arm: 32,389 noteheads+rests in the log, 7,164 written, 25,219 counted as dropped, 6 unaccounted (named drops include `bar_does_not_add_up` 13,597, `not_a_notehead:too_narrow` 3,408, `owned_by_another_staff` 2,714). So no Brahms written-2+/nowhere counts, and the accounting equality fails on whole Brahms by 6 -- not investigated. No BASE-side Brahms adjudicate time was taken, so the size of the Brahms slowdown is not measured, only that this step is slow.

## brahms-1007-worse-and-slow (2026-10-07): where NEW looks worse than BASE on Brahms, and why ADJUDICATE got slow (STAGED, GATHER+ADJUDICATE; READ ONLY on the records)

NEW = `...-20261007-night`, BASE = `...-20261006-night-combined` (tree e09e9bf5, no `OMR_MARK_GROUPS`). Scripts: `brahms_1007_worse_extract.py` (one `load_record` per record, every standing verdict compact), `brahms_1007_worse_cases.py` (counts + sheet), `brahms_1007_profile.py`, `brahms_1007_corr_by_decision.py`, `brahms_1007_corr_identity.py`. Counts `out/brahms_1007_worse_counts.json`; sheet `out/print/brahms_1007_worse_cases.png` (+ `.json`), seed 20261007, pages 2-26, 12 tiles, 2 per kind for the six biggest. NOT judged; Sean decides which side is right.

**Part 1, kinds of change where NEW can look worse (matched by subject; the two records have identical boxes on all 24,260 glyphs):** far head decided in both runs, different position 93; owner named in both, a different staff 35 of notehead heads (21 to a staff holding no second box of that mark, 5 to a staff that does, 9 to the staff it is filed on; 40 over every glyph kind); far head decided in BASE, no answer in NEW 29 (reasons: line_not_beyond_the_staff_edge 9, no_line_at_the_note_box 3, count_does_not_fit 17); arc owner named in both, a different staff 17; in-staff head whose position moved 12; a note whose length changed 10 (nine are dots below); dot read as lengthening in BASE, "ambiguous" in NEW 9; tie pair lost 5; owner decided -> none 3; accidental owner lost 3; articulation owner lost 2. No bar, meter, clef or key fact lost (0); 12 new `empty_bar_whole_rest` rows, all abstained `not_found_by_search`. Going the other way: 43 refusals "belongs to a nearer staff" became notes (108 -> 65), 260 far heads abstained -> decided, 33 owners abstained -> decided; no note newly refused as not-a-note.
Sheet line check (all drawn lines re-measured against pixel rows): 42 lines, 30 within 2 px of an ink row, 4 off by more than 2 px (tile 1 NEW note line 5.2 px; tile 9 NEW line 3 2.1, line 5 4.6; tile 10 NEW line 5 5.1), 8 with no ink beside the head (ledger rulers or a note line where no ledger exists, and BASE line 5 on tiles 9-10). Tile 12's dot-to-head link is by nearest notehead to the left and may be the wrong head.

**Part 2, why ADJUDICATE is slow.** Three Brahms pages (8, 14, 22; NEW's GATHER rows, rebuilt and adjudicated, 25,227 verdicts): all features on 183 s; `OMR_OWNER_FROM_STAVES=0` 61 s; marks rows removed (`OMR_MARK_GROUPS` off) 183 s; far-head owner-ledger rows removed 205 s; all three off 89 s (noisy shared machine; read the ratios). So the cost is the owner-from-staves rule and only it, and the profile says how: 59% of ADJUDICATE is `Evidence.correlated_groups` (adjudicate.py), 119 s of it inside `adjudicate_arc_owner` (1,247 calls, ~107 verdict rows compared pairwise per arc; the same call is 13.8 s with the rule off, same row counts), because the rule's `glyph_owner` verdicts rest on thousands of rows, so each pairwise `_one_signal` builds an intersection set of thousands of ids (11.8M calls, 75 s in one set comprehension). Also `quantities_in_closure` 3.6M un-memoised calls (33 s) and `instruments._search` recompiling a regex per alias (615k compiles, 40 s; the alias index outgrows `re`'s 512-pattern cache). GATHER is not it: a one-page `--through gather` (no surya, no ocr) took 79 and 129 s on the 10-06 tree vs 93 and 102 s on this one (shared machine, no difference beyond noise); `OMR_CELL_LINE_FIND` 1.28 vs 1.18 s/page and the far-head reader +1.4% per head are from the 10-07 read.
**Fix built (pure speed, three edits):** `_one_signal` stops at the first shared id that is neither row; `correlated_groups` skips a pair already in one component; `Log.quantities_in_closure` memoised; `_search` uses one compiled pattern per alias. Same three pages, `all` arm: 183 s -> 30 s; `nofromstaves` 61 -> 31 s. Bit-identity: every `correlated_groups` call on page 14 (11,554 calls) equals the OLD algorithm's tuple exactly (order and sets; a deliberately broken run is caught), 47,876 `quantities_in_closure` values equal the formula, alias search equal on 14 probes, and the 25,227 standing verdicts of both arms are identical row by row (quantity, subject, outcome, value, reason, basis length). Fast tier 4,588 passed; `staged.check` 247 (was 250). The whole-Brahms 7,048 s was not re-run; the expected saving is about 6x on the adjudicate stage if the ratio holds at whole-document scale (it should be larger, the all-pairs part grows with the page's rows).

## lane-arc-owner-regression (2026-10-07, STAGED, GATHER+ADJUDICATE only)

Sean on tile 8 (`glyph/5/0/6/5/11`): "both arcs belong to the horn"; tile 7 (`5/0/1/5/1`): NEW right.

- **First changed input is NOT arc_owner.** Same arc box in both records; the heads under it changed owner. `glyph_owner` of `glyph/5/0/5/5/1` and `glyph/5/0/6/5/3` (one mark, two detections, x~4073) went Horn (`distance`) -> staff 7 (`ledger_note_first`): toward the Horn it says `line_not_beyond_the_staff_edge`, toward staff 7 "on ledger 2". Its twin at the same height (`5/5/0`, `6/5/0`, x~3809) reads Horn "on ledger 1". Print crop: both sit just under the Horn's bottom line. **Ownership bug (ledger_note_first, 2.56b), reported not patched here**; with the ends owned by different staves both staves hug the arc at 0.0 and it stays on the staff it was cut from. Tile 8 is therefore NOT fixed.
- **Fix made (arc_owner):** the staff owning the nearest head at BOTH ends of the arc (heads >= 1.0 space wide, within 0.75 space of the arc) owns it, `ends_on_noteheads`, only where it disagrees with the comparative rule; split ends = unchanged.
- Replay of the current code over each record's own inputs: control (rule off) reproduces the record's arc_owner on 14,814/14,814 Brahms and 2,644/2,644 Litolff arcs. With the rule: of the 17 changed arcs 0 change (tile 7 stays NEW); seeded 30 other Brahms 0, seeded 30 Litolff 0; whole Brahms 8 arcs move (10-06 and 10-07 agreed on all 8), Litolff 0. Print check (`out/print/arc_owner_regression.png`, 4 of the 8 + 8 of the 17; all 8 inspected): the end heads are the new owner's on all 8.
- Scripts: `arc_owner_extract.py`, `arc_owner_replay.py`, `arc_owner_regression.py`, `arc_owner_sheet.py`; test `test_staged_arc_owner.py` (2 RED on old tree, 3 added). check 247 -> 247; fast tier 4,597 passed.
## 2026-10-07 lane-farhead-5-6: Sean's worse-cases tiles 5 and 6 (STAGED far-head reader, GATHER+ADJUDICATE only)

**Tile 6 (`glyph/25/1/5/5/1`, Brahms p25 Horn, Sean: first ledger below the staff, BASE right) -- cause found and fixed.** The bar's five lines are right (drawn 1 px on ink; offsets <= 3 px, `out/print/farhead_5_6.png`). The jutting ledger stub gave the note's line at 5730.75 (ledger ink 5727-5734); then `refine_line_on_flanks` (flank window 0.1-1.0 sp, row coverage >= 0.6, move <= 0.30 sp = 8 px) moved it to 5722: the stub is only ~0.5 sp long (coverage 0.45), but an augmentation dot beside it (0.5 sp wide on this plate) passes the test. The line then lay 17 px = 0.61 sp from the edge (5705) and `count_ledgers_between` returned `line_not_beyond_the_staff_edge` (min 0.7 sp). Not an edge/ledger confusion.
**Fix** (`READER_KEYWORDS["flank_refine_bounded"]`, default ON; OFF = bit-identical): a line a jut measured (`through_the_middle`) is not re-measured on the flanks (its row IS the median of the jut's own flank columns); any other line is re-measured only on flank rows whose ink touches the head (strip 0.05-0.3 sp outside the box >= 50% inked): a stub juts from the head, a dot floats clear. Tried first and refused: a move bound of half / one line thickness (+1 px): it also stopped real corrections of 1.5-5 px on Litolff (3 right heads lost) without gaining more. Constants chosen before the final run; unit test `test_far_head_refine_bounded_2026_10_07.py` RED on the old tree (None / `line_not_beyond_the_staff_edge`), green after, with a control that can fail and a no-dot positive control.
**Population (replay of the 10-07 extracts, same raster/grid, flag OFF vs ON):** Brahms far heads 8,966: decided 4,288 -> 4,327 (+47 abstain->decided, 8 decided->abstain, 0 decided answers changed); Litolff 4,196: decided 2,026 -> 2,034 (+12 / 4 lost / 0 changed). The 8+4 lost are `count_does_not_fit` where the old line row made the gaps fit (a hand-drawn 1.5-1.6 sp gap); the old answers there are unverified. Of the 29 Brahms heads that went decided -> abstain 10-06 -> 10-07: **14 regain an answer, 13 equal BASE's** (`glyph/19/0/0/5/7` -4 vs BASE -2 still differs, unjudged); 15 still abstain. Truth set (`farhead_5_6_truthset.py`; the extract holds 38 of the 41 Litolff p3 heads): Litolff 33/1/4 -> 33/1/4, Brahms 11/0/0 -> 11/0/0 (OFF arm reproduces the record on 38/38 and 11/11), 0 right broken. Sean's confirmed night 10-06 / 10-07 tiles present in the extracts (22): none changes. The note-first and edge-vs-through sheets' subject lists are not recoverable (seeds not recorded); the whole-population statement (0 decided answers changed) covers them. Off-box count not re-run.
**Manager's two heads** (`glyph/5/0/5/5/1`, `glyph/5/0/6/5/3`, one mark detected twice under the Horn staff): read toward the Horn they were `line_not_beyond_the_staff_edge` (same cause: the line row pulled 3.5 px onto the dot); now both read 10 (on the 1st ledger below the Horn). `far_head_owner.decide`: before, Horn unread + staff below -4 fits -> `one_ladder_fits` the staff below; now both fit -> `both_fit` (the ledger witness no longer takes it from the Horn; the Horn is named only if the other witnesses, distance first, do so -- needs a re-adjudication, not run here).
**Tile 5 (`glyph/18/1/0/5/21`, Flute p18, Sean: in the space above the 1st ledger above the staff) -- NOT fixed, cause named.** Rungs found 3953.5 (2nd ledger, at the box's TOP edge, head hangs below it) and 3926.5; the 1st ledger (~3980, the box's staff-side edge) is fused into the head's lower ink and the neighbouring hollow head: no rung, jut 3-4 px each side (< the 4.15 px stub minimum, and a head's bottom curve gives false juts at that row). So no line is "at the box" (`no_line_at_the_note_box`) and the far line cannot be taken (a chord partner farther out: Sean 10-04 "no rule there"). BASE's "on the 1st ledger" was wrong. Abstaining is the honest result; geometry says -3 (right) but the staged path has no geometry fallback. Candidate rule for Sean, not built: ledgers print consecutively, so a gap of exactly two pitches (edge -> 2nd ledger 1.95 sp, pitch 0.99 from the ledgers beyond) holds one hidden ledger, and a head hanging with all its ink on the staff side of a far-edge ledger is in the space between. CONVENTION ASSUMED / FALSIFIED BY a clean white row at the predicted place / NOT CONFIRMED.
**Remaining 15 of the 29 (causes seen, none changed):** 7 owned by a neighbouring staff, so the filed-staff read is moot (26/0/6/* are notes below staff 5 whose "rungs" are a hairpin's arms -- p26 crop); `ledger_not_text` refuses a real ledger beside a chord partner's head (`glyph/3/1/0/9/2`, `tall_ink_not_one_continuous_stroke`; skipping detector-box columns did not help: the partner head has no box); hidden-ledger gaps like tile 5 (`glyph/6/1/6/2/4`: a 10 px stub right of a stem; `find_rung_in_gap` probes only the box centre column, its `head_box_x` argument is unused). Scripts: `farhead_5_6_*.py` (diag, crop, all29, refine_census, variants, truthset, toward_horn, owner_decide, sheet). Sheet `out/print/farhead_5_6.png`: tiles 5 and 6 first, the manager's Horn head, 9 seeded changes.
## lane-dot-not-a-note (2026-10-07): a dot is never a notehead, and follows the note to its left (STAGED ADJUDICATE; ROADMAP 2.59; `OMR_DOT_FOLLOWS_NOTE`, default OFF)

Sean on the Brahms "worse" sheet: tile 4 (`7/1/0/9/9`) an augmentation dot boxed as a notehead, given to Flute, belongs to Oboe; tiles 11, 12 (`18/1/12/6/18`, `5/0/1/5/32`) BASE read the dot as lengthening, NEW "cannot tell", the note belongs to the staff below.

**First changed input, per tile (replay of the 10-07 night record; flag off reproduces the saved verdicts exactly: 932 dots / 3,018 boxes on pages 5, 7, 18, 0 mismatches).** Tile 4: the box is the top 7 px of a dot clipped by the Flute strip's edge (already refused `clipped_fragment` in BOTH records); what changed is its owner, `ledger_note_first` -> `distance` (Flute); the whole dot sits in the Oboe strip as `7/1/1/9/10` and trails the Oboe note `7/1/1/9/8`. The fragment overlaps the dot by IoU 0.295 (the mark-group bar is 0.3; and groups never cross families). Tiles 11, 12: `dot_role` drops every head `glyph_owner` decided belongs to another staff (2.27c) -- NEW now owns the dotted note on the staff below (`ledger_note_first`), so the dot, filed in the strip above, has no candidate left: `dot_role_ambiguous`. In tile 11 the dot's own owner was also the strip's (`distance`, staff 12) while its note's was staff 13.

**Rules (all behind the flag).** (a) Size test, stated before any count: notehead-class box with width AND height <= 0.75 sp (dot ~0.5 sp, head ~1.3 sp wide, `too_narrow` floor 1.0) is refused `is_a_dot`, after `clipped_fragment`/`too_narrow` so no existing reason changes. (b) `dot_role`: a note owned by another staff is tried LAST. Two first versions were measured and refused: foreign window first turned 8 of 14 Litolff staccato dots into augmentations (crops: dot over the next note's column); then 2 of 3 remaining were another note's staccato 1.1+ sp away. Final: only after the home augmentation and staccato windows, head-edge-to-dot gap <= 0.75 sp, and not when any note stands within 0.5 sp of the dot's x. `reconcile_dot_owners` (after `Q.DOT_ROLE`) files the dot's owner as its note's (decided owner, or the filing staff of an uncontested note; an undecided note files nothing). (c) A refused notehead-class box with >= 50% of its area inside a dot box and no larger than 1.35x it takes the dot's owner (containment, not IoU: tile 4's is 0.295).

**Counts, 10-07 night records, GATHER+ADJUDICATE, flag off -> on.** Brahms 24,260 notehead-class boxes: dot-sized 1,724, of which 1,715 were already refused (`too_narrow` 1,555, `clipped_fragment` 146, `is_a_clef` 13, nearer-staff 1) and 9 kept; all 9 now refused. Litolff 11,399 boxes: 52 dot-sized, all already refused, 0 new. Dots: Brahms 9,674 -- 1,002 `abstained` -> augmentation, 0 staccato -> augmentation, 297 owners moved to the note's staff (66 had no decided owner), 17 dot-shaped boxes follow their dot, 858 notehead durations change (they now carry the dot); Litolff 601 -- 1 role, 4 owners, 1 duration. Crops: all 9 newly refused viewed (3 dots, 1 letter of "ce", 4 bar/stem bits, 1 tremolo slash; 0 real heads); seeded 40 of the dot-sized refused (`out/print/dot_not_a_note_refused40.png`): 0 real heads, 7 look like dots, 33 barline/stem/line fragments; 24 of 24 seeded Brahms role flips (`out/print/dot_role_changes_brahms.png`) are plain augmentation dots beside their note. Sheet `out/print/dot_not_a_note.png`: tiles 1-3 Sean's, 4-12 seeded; 118 of 120 drawn staff lines within 2 px of an ink row.

Scripts: `dot_not_a_note_replay.py`, `_counts.py`, `_sheet.py`, `_rolecrops.py`, `_newly_refused.py`. Test `tools/omr/tests/test_dot_not_a_note_2026_10_07.py` (6 RED on the unrepaired tree, 20 green). Fast tier 4,611 passed (before the two guards), `check` 247 -> 247. NOT judged by Sean; default stays OFF.


### lane-dot-not-a-note round 2 (2026-10-07): Sean 8 of 12 right on `out/print/dot_not_a_note.png`; the four wrong, fixed (`out/print/dot_not_a_note_r2.png`)

Round-1 tiles 5, 8 (Litolff `12/1/6/2/9`, `4/1/2/5/8`) were STACCATO marks above a note; tile 9 (Brahms `16/1/10/4/3`) belongs to the Viola; tile 10 (Brahms `5/1/1/2/17`) is stray ink on a barline.

**Causes.** Tiles 5/8: the round-1 stacked-note guard looked only at the dot's own cell and at 0.5 sp of a note's centre, and the stacked note was a neighbour staff's (tile 5) or the base reading was already wrong (tile 8: the OFF record read `articStaccatoAbove` as lengthening; my owner move then took it to another staff). Tile 9: the dot's nearest head in its own strip was a 7 px sliver of the viola note, refused as a fragment, and my rule followed the sliver's owner (Violin); the real viola head sits in the neighbour strip. Tile 10: `is_a_dot` refused it correctly but called it a dot.

**Geometric tests (stated before the re-run, page frame, staff spaces).** STACKED (staccato-placed): the dot's centre lies within 0.5 sp of the centre of any non-refused notehead of its cell or of the staves just above/below, any owner, and outside that head's y-extent by <= 2 sp. A lengthening dot sits right of its head at the head's height; chord-seconds dots sit 0.5-0.76 sp from the shifted head's centre and are not stacked (the cut was read off the data: aug->staccato flips 0.0-0.5 sp, 99% < 0.42). A stacked dot is never read as lengthening, by the home window or the foreign one. ON A BARLINE: a dot-sized mark whose page x-extent comes within 0.15 sp of its cell's left/right page edge -- cells are cut at the barlines (Brahms p5 staff 1: 1330 | 1804 | 2271, the box starts at 1804.0) -- is refused `on_a_barline` (notehead-class box) or left unread (dot box), not called a dot. A refused fragment is the LAST resort for a dot, after real notes in the cell and the neighbour strips (first try dropped fragments outright and lost 154 true dots).

**Controls (10-07 night records, flag off reproduces the saved verdicts; on).** Round-1 tiles 4, 11, 12 stay right (`7/1/0/9/9` -> Oboe staff, `18/1/12/6/18` read + Contrabass staff, `5/0/1/5/32` read); tile 5 now unread (as OFF), tile 8 now staccato with its owner unchanged, tile 9 read and Viola, tile 10 `on_a_barline`. 0 real noteheads refused (the 9 newly refused boxes + 1 reason change, all viewed: 3 dots, a letter, bar/stem bits, a tremolo slash). Before (round 1) -> after (round 2): Brahms dots read as lengthening 6,301 -> 6,280 (off 5,299); abstained -> augmentation 1,002 -> 1,125; augmentation -> staccato 0 -> 163; augmentation -> unread 0 -> 1; staccato -> augmentation 0 -> 20; owners moved to the note's staff 297 -> 308; head durations changed 858 -> 1,039; dot-shaped boxes following their dot 17 -> 18. Litolff: read as lengthening 49 -> 18 (off 48), augmentation -> staccato 0 -> 31, owners 4 -> 2, durations 1 -> 28. Crops: all 31 Litolff aug->staccato, 16 of 163 Brahms, and 16 of 20 staccato->aug viewed -- staccati over the next note and plain dots beside their head respectively. Fast subset 983 passed, `check` 247 -> 247. Test file now 37 tests (13 RED on the unrepaired tree).
## lane-arc-not-a-line (2026-10-07, STAGED, GATHER+ADJUDICATE only; ROADMAP 2.60)

Sean on `out/print/arc_owner_regression.png`: *"it is still occasionally calling a staff line an arc. (1,3,6 are all barlines)"*; clarified *"6 is a barline"*. **Which tiles:** the sheet's captions are the tile numbers; tile 1 is the arc captioned "TILE 8" (`glyph/5/0/6/5/11`), tile 3 is `glyph/4/0/4/8/7`, tile 6 is `glyph/2/0/10/1/14` (Brahms 1 pages 5, 4, 2).

- **Who made them.** All three are DETECTOR `slur`/`tie` boxes (reader `detector`, score 0.40 tie / 0.49 slur / 0.68 slur) -- no CV arc reader is in the record's `arc_box` rows. Tile 1: a flat box 22.3 spaces wide, 1.45 tall, lying on the Horn's bottom staff line, filed under the staff BELOW (so the owner's own erasure never touched that line). Tile 3: a box 17 spaces wide from barline to barline holding a staff line plus the two ends of two real slurs. Tile 6: the ink inside the box is a real slur under the Violin notes (not a barline, not a staff line) -- if Sean meant the old caption "Tile 7" (`glyph/6/0/5/4/7`, 19.4 x 0.5 spaces, a bar-wide staff line), that one is refused now.
- **What should have refused it.** A staff line is straight, flat, bar-wide; take every staff line of the page out of the box and nothing curved is left. A real arc keeps curve ink on nearly every column.
- **Reader built (GATHER, `gather_arc_ink`, `Q.ARC_INK_SHAPE`, reader `CV_ARC_INK`):** page raster with the staff lines left in, EVERY staff of the page's lines (a first version used the owner cell's erased raster and own lines: tile 1 read 95% curved because the line was the NEXT staff's -- measurement fault, fixed, thresholds untouched), each line snapped to the page's own ink row locally and its stroke grown to the ink's thickness (a second fault: a fixed +-0.1 sp band left 7 px of a thick Breitkopf line reading as a curve; `glyph/6/0/5/4/7` read 98% curved). **Refusal (ADJUDICATE, `adjudicate_arc_is_not_an_arc`):** `ink_is_a_staff_line` = a staff line passes through the box AND width >= 2.5 spaces AND < 35% of columns hold curve ink; `ink_is_a_barline` = width <= 1.0 and height >= 2.0 spaces and >= 60% of columns one tall vertical run. Thresholds were fixed before any count (constants `ARC_*` in `family_precision.py`, `ARC_INK_*` in `gather.py`); they were not moved after. Refusals are verdicts with reasons; the box stays in the record and `arc_owner`/`tie_pair`/export already skip a refused arc.
- **Counts (replay of the 10-07 shared records' own `arc_box` rows through the real `gather_arc_ink` + the real decision):** Brahms 14,814 arcs: 7,946 refused `ink_is_a_staff_line`, 0 `ink_is_a_barline`; Litolff 2,644: 503 refused, 0 barline. Controls: fresh staff lines equal the record's (0 mismatches); every box shifted 2 spaces down changed the reading on 10,977 of 14,812 Brahms and 2,238 of 2,644 Litolff arcs (the measurement moves with the box). Barline reason fires 0 times: the 10 narrow boxes in Brahms are 14 x 4 px specks, not strokes -- the rule is built and unit-tested but has no example in these records.
- **Print check (`out/print/arc_not_a_line.png` = tiles 1, 3, 6 + caption-7 + 9 seeded refusals; working sheets of 20 refused + 20 kept per record were cut and looked at, seed 20261007):** refused, Brahms 0 of 20 a real slur/tie (20 bar-wide flat boxes on staff lines); Litolff 17 of 20 plain staff lines and 2-3 borderline (a slur's curve touches the box edge: pages 10, 5). Kept, Brahms 0 of 20 a line (a few sub-1-space specks); Litolff 1-2 of 20 are stubs on a line (page 3 system 3 box 0.2 tall, 47% curved; page 15 box 0.4 tall). **Not caught: Sean's tile 3** (44% curved, because the box covers real slur ends as well as the line).
- **What it does not do:** it does not shrink a wrong box (tile 3) or find a barline in these records. Needs a re-gather to reach a record (GATHER change; this replay is the evidence, no new record was written). Roughly half of Brahms' detector `slur`/`tie` boxes are staff lines (54%): that is the detector's, not ours.
- Scripts: `arc_line_extract.py`, `arc_line_replay.py`, `arc_line_counts.py`, `arc_not_a_line_sheet.py`, `arc_line_look.py`; test `test_staged_arc_not_a_line.py` (RED on origin/main: no `gather.arc_ink_shape`; 15 pass here).

## 2026-10-07 lane-farhead-2-9: Sean's tiles 2 and 9 of `farhead_5_6.png` (STAGED far-head reader, GATHER+ADJUDICATE only; READ ONLY on the 10-07 records)

Branch `lane-farhead-2-9` off `origin/main` d8497322. Keyword `READER_KEYWORDS["look_where_it_must_be"]`, default ON, OFF = bit-identical. Sheet `out/print/farhead_2_9.png` (+ `.json`), 1400 px wide, one column. Scripts `farhead_2_9_{census,recensus,merge,controls,names,sheet}.py`; test `test_far_head_look_where_it_must_be_2026_10_07.py` (10; on the old tree all fail on the unknown keyword, and the OFF-arm tests are the controls that can fail: they pass on the new tree only because the old behaviour is still reachable).

**Baselines reproduced first.** `farhead_all_wired_eval.py` cannot run here (it needs the 10-04 truth-set records under `benchmarks/acceptance/quick/out/`, absent); `farhead_5_6_truthset.py` on the 10-07 extracts reproduces the figure the last lane gave: Litolff p3 33 right / 1 wrong / 4 abstain (38 heads), Brahms p1 11/0/0, OFF arm = the record on 38/38 and 11/11. Census OFF arm equals the record's own position on 4,161/4,196 Litolff and 8,909/8,966 Brahms far heads (the rest are the 10-07 replay's known gaps).

**Tile 9 (`glyph/18/0/5/4/6`, Horn) -- cause: the head is on the first ledger below the staff ABOVE it (Contrabassoon); read against the Horn staff, the lower arm of an ACCENT under the head was counted as ledger 1 (1.43 sp from the Horn's top line, `articAccentBelow` box [3861,1618,3917,1646] across row 1641), the count fitted, the reader answered "2nd ledger above" and, both staves now fitting, `far_head_owner.decide` returned `both_fit` and ownership fell back to distance.** Not a sign or staff-edge error. Fix: a rung counted between the staff and the note's line is refused where a detector box of an accent/marcato class lies across it beside THIS head and the row's ink ends inside the box (a ledger runs on past a mark's box). Now toward the Horn: `count_does_not_fit` (an honest abstain); toward the Contrabassoon: pos 10 (first ledger below); `decide` -> Contrabassoon, `one_ladder_fits`.
Two first versions refused, with the numbers: (1) requiring EVERY counted rung to show a jut turned 307 Litolff / 234 Brahms decided heads into abstains and moved 6 Sean-confirmed tiles (real short stub ledgers have no jut past the head); (2) the accent rule over a `tenuto` class and over any box on the page moved 3 confirmed tiles (Brahms `9/1/0/5/2`, `18/1/9/7/10`, Litolff `10/0/0/10/8`: Litolff's ledger 1 under a head on ledger 2 is a flat dash the detector called `articTenutoBelow`; a tenuto and a stub ledger are the same ink). Final: wedge classes only (accent, marcato), box beside the head only.

**Tile 2 (`glyph/18/1/0/5/21`, Flute).** Stated BEFORE running: where the staff edge and the first found rung at/beyond the head's middle enclose the head and the gap holds exactly one ledger (each half within the 0.7-1.5 sp pitch limits), the row = that rung moved one pitch (its distance to the next found rung, else the staff spacing) toward the staff; look there +-0.12 sp for a thin (<= 0.35 sp) flat run beginning within 0.25 sp of the head's edge and >= 0.15 sp long, on one side or both; count the ledger only if found, never from the gap. First run on tile 2 found nothing, and the pixels said why (`out` ascii: the jut is 4 px each side of the head's INK BODY, 2-3 px inside the detector box on the right, and the print's ledger sits 3.5 px below the equal-pitch row: 3984 vs 3980.5): revised AFTER seeing tile 2 (so tile 2 is in-sample for these two edits): the edge is also measured from the head's ink body (`_jut_from_head_ink`'s thick columns), the row tolerance 0.15 sp, and a jut shorter than 0.15 sp (here 4 px = 0.146 sp) counts only when it shows on BOTH sides at the one row. Result: the jut is found on both sides at 3982.5/3983.5, the head reads -3, "in the space above the 1st ledger above the staff", Sean's answer. The control that can fail: the same head with no jut drawn stays unread though the gap has the same room (unit test).

**Controls.** Every Sean-confirmed tile (note_first 1-11 regenerated from seed 20261005, night_1006 1-5,7,8,11,12, edge_vs_through_flips 1-24, night_1007 2-4,6-12, brahms_1007 1,2, farhead_5_6 all but 2 and 9): 66 listed, 64 are far heads in the extracts, **64 unchanged, 0 moved** (2 are owner/arc tiles, not far heads). Truth set with the final code (`farhead_5_6_truthset.py look_where_it_must_be=1`): Litolff 33/1/4 -> 33/1/4, Brahms 11/0/0 -> 11/0/0, 0 right broken (the last of its two edits was made after the first run, so this is the final-code figure).
**Out of sample (replay of the whole 10-07 far-head population, same raster and per-bar grid):**

| | decided before | decided after | abstain before | abstain after | rescued by the look | jut on both / one side | decided -> abstain | decided -> other answer |
|---|---|---|---|---|---|---|---|---|
| Brahms (8,966) | 4,327 | 4,317 | 4,639 | 4,649 | 3 (incl. tile 2) | 1 / 2 | 13 (tile 9 + 12 accents) | 0 |
| Litolff (4,196) | 2,034 | 2,035 | 2,162 | 2,161 | 1 | 1 / 0 | 0 | 0 |

So the look rescues FOUR heads in all, not ten (the sheet shows all four, then the nine other accent refusals that were sampled to fill it: tiles 1-2 Sean's, 3-5 rescues, 6-12 seeded refusals). All 12 Brahms refusals were cropped (`crop` of 12): every one is a real `>` accent under or over the head. The 13th decided->abstain is tile 9. Off-box count not re-run.
**Not fixed / said plainly:** the look needs the ledger's end to stand out of the head's ink by >= 3 px; a ledger fused with a flat's bowl on one side and short on the other would not be seen (tile 2 was close to that). 11 of the 15 abstains seen on the way are untouched.
**Gates:** `staged.check` TOTAL 247 (the same figure the last lane reported; no baseline re-run on the unpatched tree); fast tier before the last narrowing 4,608 passed, after it the 574 far-head/ledger/owner tests pass.

## lane-numeral-not-a-note (2026-10-08): a "2" boxed as a half notehead

**Path: STAGED, GATHER** (`far_head_reader.not_a_note_reason`, flag `READER_KEYWORDS["not_a_note"]`, already default ON). Sean, tile 4 of the 10-07 day sample, `brahms 26/0/11/0/17`, Cello p27 (pdf index 26).

**What the record held.** `noteheadHalfInSpace`, detector score 0.254 (the floor is 0.25), 47 x 44 px at 600 dpi (1.7 x 1.6 sp), box 1057,3090..1105,3134. No `fingering*`/`tuplet*`/text box lies over it (the only overlaps are two slurs and the real head, a separate box on the staff above). No OCR digit. `notehead_is_not_a_notehead` decided False/`notehead`; the far-head reader read it at -3 "in the space beyond ledger 1". No gate looked at its ink: every gate was about position, size or another box. The crop (`out/print/numeral_not_a_note/tile_01.png`) is a "2" under a slur.

**The record-evidence rule is DEAD on both records.** `on_numeral` (a fingering/tuplet digit box covering >= half of a notehead box): 0 of 11,399 Litolff and 0 of 24,260 Brahms notehead boxes (19 and 99 digit boxes on the pages). Kept (it cannot misfire, it is tested) but it is not what fixes the tile.

**The first shape test failed its control, and is not shipped.** Opened-ink area / enclosed-hole area: refused 188 boxes, and in a seeded 40 (`montage`) most were REAL hollow heads, because a scanned half head is a black oval with a thin white slit, not a ring (the hole count is 0 for 10% of far hollow heads). It also caught rests, a flag, an "f", a slur. Dropped.

**Shipped shape test, thresholds stated before looking:** `numeral_shaped` = the ink component holding most of the box is ISOLATED (does not touch the box padded 0.3 sp: no staff line, ledger, stem, slur or neighbour joined), is 0.5-2.0 sp wide and 0.8-2.0 sp tall, and has area / convex-hull area < 0.78 (a head is a convex oval; a "2" measured 0.71). Reach is small by design: isolated components are 7 of 11,399 Litolff boxes and 212 of 24,260 Brahms boxes.

**Counts, 10-07 day records (far-head reader's population, GATHER + ADJUDICATE only):** refuses 3 boxes, all Brahms, all FAR heads: `26/0/11/0/17` (the "2", Sean's), `26/0/11/1/13` (the matching "2", next bar; the record already refused it as a duplicate box), `1/1/11/1/22` is the letter "e" of "cresc." on p2 (read as a half head). Litolff 0. Without the size window two Litolff boxes and `5/0/8/3/16` also pass the solidity test; they are 3.8 sp / 2.2 sp wide staff-line and bar fragments and are NOT refused by this rule.

**Seeded-40 check.** The population is 3, so all 3 were looked at (crops `tile_01..03.png`): 3 of 3 are not heads, 0 real noteheads refused. Control: no confirmed-head subject from Sean's tiles is among the 3; the in-sample truth set (`farhead_all_wired_eval.py`) cannot run here (its 10-04 truth records under `benchmarks/acceptance/quick/out/` are absent), so "unchanged" is argued, not measured: the rule only abstains the 3 subjects above, two are on p27; the third, `1/1/11/1/22`, is on Brahms pdf index 1, a truth-set page, but it is the letter "e", not a head, and could not be a truth head.

**Not done / open.** Ink touching a staff line, ledger or slur (most numerals near a staff) is never judged by shape: a head in that state is indistinguishable by this test. A `Q.`-level GATHER shape reading, or OCR of digits, would widen reach; neither is built (no roadmap item). Unit test `test_far_head_numeral_not_a_note_2026_10_08.py` RED (5 failed) on the unrepaired tree, green after; a real oval and a scanned slit head are the positive controls.
## lane-staccato-unread (2026-10-07): a staccato over the NEXT strip's note was left unread (STAGED ADJUDICATE; ROADMAP 2.59 follow-up)

Sean, on `dot_not_a_note_r2.png` tile 1 (Litolff `12/1/6/2/9`): "not sure why it can't see that the first cell is a staccato note."
All numbers: the 10-07 DAY records, GATHER+ADJUDICATE through `dot_role`, one tree, `staccato_unread_replay.py` (before = tree at e92bfc6a, after = this branch).

1. **Which condition fails.** Measured on the page (16 px/sp): the dot sits 0.08 sp off the column of the note under it and 1.2 sp above its centre, so it is inside the staccato window. The note is filed in the next strip down and owned by another staff, and `dot_role` tried the staccato window against its own strip's notes only; the only own-strip head is 1.23 sp to the dot's left. "Stacked" (correctly) stopped it reading as lengthening, so nothing was left: abstained `dot_role_ambiguous`. No column-from-box-edge or stem-side fault.
2. **Unread dots, before** (page geometry: staccato-like = a real head within 0.5 sp in x, dot outside its y extent and <= 2 sp from its edge; lengthening-like = a head's right edge within 1 sp left of the dot at its height):

| | dots | unread | staccato-like | lengthening-like | neither | other |
|---|---|---|---|---|---|---|
| Litolff | 601 | 173 | 39 | 11 | 118 | 5 (3 no head in cell, 2 on a barline) |
| Brahms | 9,674 | 876 | 259 | 163 | 446 | 8 (barline) |

All 39 Litolff staccato-like cases have the head in a neighbouring strip or owned elsewhere; none has an own-strip head.
3. **Fix** (`rhythm._foreign_staccato_owner`, threshold stated before running): after the own-strip windows fail, the staccato window (<= 0.5 sp centred, >= 0.75 sp off) is tried against every real head of any strip or owner, within 2.0 sp of the head's edge (the stacked test's reach). Staccato only; tried before the foreign augmentation; flag-gated with `OMR_DOT_FOLLOWS_NOTE`. Named note in `detail.owner`, `head_owned_elsewhere`.
4. **After.** Unread: Litolff 173 -> 134 (staccato-like 39 -> 0), Brahms 876 -> 621 (staccato-like 259 -> 4). Role changes: 294, every one unread -> staccato; zero decided dot changed (augmentation 18 and 6,280 unchanged), so Sean's confirmed dot sheet answers are untouched (checked the r2 keys one by one). Left unread on purpose: the lengthening-like (11 + 163) and "neither" (118 + 446) are not staccato and stay "cannot tell". The dot's OWNER still follows only an augmentation (`ownership.reconcile_dot_owners`, outside this lane): a foreign-note staccato keeps its filing strip as owner.
5. Test: `test_staccato_unread_2026_10_07.py`, RED (1 failure + 5 controls passing) on the unrepaired tree, green after. Tiles: `out/print/staccato_unread/tile_01..10.png`, `questions.txt` (tile 1 Sean's, 2-10 seeded 20261008: 3 Litolff, 6 Brahms).
## 2026-10-08 -- ROADMAP 2.58c: why a mark seen 2+ times has no owner (`lane-mark-group-no-owner`)

GATHER+ADJUDICATE only, on the 10-07 day records. Population = notehead marks seen 2+ times, members not refused as a
note (Litolff 1,420, Brahms 3,076). Scripts: `mark_group_no_owner_extract.py`, `mark_group_no_owner_tiles.py`.

**The 148 (Litolff) / 40 (Brahms) "no owner" is mostly not a gap.** Counted as "no member holds a DECIDED `glyph_owner`":

| cause | Litolff | Brahms |
|---|---|---|
| never contested, every copy cut from ONE staff (and one cell) -- the filing staff is the owner, nothing to file | 146 | 35 |
| a contested copy looked and abstained (`far_no_rungs`; Brahms also 1 `tied`) -- every copy abstained | 2 | 5 |
| (not in the 148) decided copies name different staves | 4 | 2 |

Under the project's own measure (`day_1007_report.marks`: decided owner, else filing staff) that is Litolff 2 unowned +
4 split, Brahms 5 unowned + 2 split. The brief's Brahms "5" is that measure; the Litolff "148" is the decided-verdict
count (its Brahms twin is 40).

**Replay control:** the group stage rebuilt from the record (GATHER `mark_group` rows + each member's original
`glyph_owner` and not-a-note verdicts) with the OLD rule reproduces the record's own `group_owner` verdicts exactly
(Litolff 39/39, Brahms 31/31); the NEW rule differs on 3 and 7 member verdicts, so the control can fail.

**Rules (stated before the run; `reconcile_group_owners`):** (3) a box refused as a note neither votes nor blocks;
(4) one ledger-backed staff against nearness-only (`distance`) dissent -> the ledger staff owns the group (CLAUDE.md §10:
ledgers name the owner, nearness is a hint); (5) any other disagreement files nothing. Census now says WHY a group is
silent (`owned_by_filing_staff` / `unowned_abstained` / `unowned_split_uncontested`).

**Result:** groups that had one owner and changed or lost it: 0 / 0. Newly owned: Litolff 2 conflicts resolved by rule 4
(`14/0/46`, `4/1/178`; Brahms 0 -- both its conflicts are ledger-vs-ledger). Of the 2 (Litolff) / 5 (Brahms) groups
where every copy abstained: 0 gain an owner -- no copy has an answer to adopt, and rule 8 forbids a guess (several
carry tremolo-slash or numeral signals: possibly not notes -- the not-a-note lane's). Rule 3 changed 8 verdicts
(1 + 7), all on boxes refused as notes (nothing written changes). Kept conflicts: Litolff 2 (`12/0/491`, `6/1/374`),
Brahms 2 (`18/1/599`, `5/1/35`) -- swaps between ledger readings, not resolved.

**Pending Sean:** `out/print/mark_group_no_owner/tile_01..10.png` + `questions.txt` (answer key `key.json`, not on the
tiles). Tiles 3 and 7 are the two rule-4 groups; the rule is not to be merged until he answers them.

## 2026-10-08 -- ROADMAP 2.58d: a STEM witness for ownership (`lane-stem-owner`, off `lane-mark-group-no-owner`)

GATHER+ADJUDICATE only, replayed on the 10-07 day records (no re-gather). Sean on the 2.58c tiles 3 and 7: the Litolff p14 head
between Trumpet and Timpani is the Trumpet's, the p4 head between Oboe and Clarinet is the Clarinet's -- *"the stem should make it
obvious"*. 2.58c gave tile 3 right and tile 7 WRONG (Oboe).

**Why the ledger witness said Oboe on tile 7 (plain).** The note-first reader counted two "ledgers" toward the Oboe: rung 1 is the
SLUR arc that crosses the bar above the heads (curved, slanted, thick) and rung 2 is the tops of the NEIGHBOURING heads on the same
level (`right_adjacent` 0.94) -- there is no flat line at either height (8x crop with the reader's three windows ruled:
`out/print/stem_owner/why_oboe_tile7_crop.png`, `stem_owner_why_oboe_crop.py`). The head's own stem runs straight down its left edge into the
Clarinet's lines, which is what the new witness reads. A ledger read from the print that counts a slur and a neighbour is a
reading fault upstream of ownership (the 2.60 line: an arc is not a line, here a line is not an arc).

**`Q.STEM` was tried first and does not hold it.** The head's own stem is thin where it crosses the next staff's lines and the CV
opening dropped it; the one `Q.STEM` row beside the head is the RIGHT-hand neighbour's (a down stem stands at its head's LEFT). So
`Q.HEAD_STEM_REACH` (new, GATHER, `gather_head_stem_reach` / pure `measure_head_stem`) reads the page's original raster in page
pixels beside each CONTESTED head: a vertical ink run along its left edge beneath it = `down`, along its right edge above it =
`up`, the same columns running BOTH ways = `both` (barline / another head's stem: claims nothing), a run under 0.8 sp = `none`.

**The rule (stated before any count; `ownership._stem_owner`).** A head at least 0.9 sp outside every candidate's outer line whose
stem leaves it down/up and whose tip stands within a space of exactly ONE candidate's band, on the stem's side, belongs to that
staff. Toward neither or both, `both`, `none`, or a head on/beside the lines (the owner-from-staves control): silent. Order: human,
`staff_band`, `ledger_note_first`, ledger density/direction, hairpin/ladder/range, THEN stem in place of `distance` (and of
`far_no_rungs` / `ledger_all_refuted` / `tied`). Stem vs a ledger witness, or vs a hairpin/ladder decision, naming different
staves: the head ABSTAINS (`stem_disagrees`, counted `owner_not_read`); a staff the written range calls impossible is simply not
named by a stem (the first draft abstained there and turned 185 decided Litolff heads into unread ones -- removed). Default OFF
(`OMR_STEM_OWNER`, allow-list); the GATHER row is filed either way.

**Controls.** `adjudicate_glyph_owner` with the flag OFF reproduces the record's own verdicts head for head: Litolff 9,383 / 9,383,
Brahms 33,749 / 33,749. Tiles 3 and 7 now come out Trumpet and Clarinet (tile 7: the Oboe-cell copy abstains `stem_disagrees`, the
Clarinet-cell copy decides `stem_toward_staff`, the 2.58c group rule adopts the Clarinet for both). No head whose centre lies inside
its filing staff's band changes owner (0 of 102 / 0 of 267; the FIRST draft moved 10 heads sitting on an edge line -- now excluded by
the 0.9 sp floor). The ledger-read far heads on the two count pages keep their owner (0 of 93 Litolff p3, 0 of 189 Brahms p1; the
changes there are 4 and 12 heads decided by `distance` / `hairpin_separates`). Sean-confirmed owners: of 14 heads transcribed
from his sheets, 9 hold in both arms; 5 (owner-by-ledgers 4, 6 and 7, day tiles 8 and 10) already differ from my transcription in
the flag-OFF arm, identically, and the stem changes none of them -- not a stem effect, to be re-read against the sheets.

**Out of sample (owner changes by rule, final owner after the group rule).**

| | Litolff | Brahms |
|---|---|---|
| stem reads down / up / both / none | 2,918 / 2,036 / 1,528 / 2,940 | 7,259 / 4,450 / 7,449 / 14,885 |
| `distance` -> stem owner (a head moves to the FARTHER staff) | 84 | 184 |
| `far_no_rungs` -> stem owner (a gap answered) | 35 | 19 |
| `ledger_note_first` -> abstain (stem and ledgers disagree) | 16 | 41 |
| `hairpin_separates` / ladder / `ledger_direction` -> abstain | 2 | 33 / 1 / 3 |
| final owner changes | 102 | 267 |
| ledger-read heads where the stem AGREES vs DISAGREES | 2,232 vs 16 | 4,937 vs 44 |

The agreement is the best evidence short of Sean: the note-first ledger witness was right on every sheet he adjudicated, and the
stem, read off different pixels, names the same staff 99.3% / 99.1% of the time. The 16 + 44 disagreements and the 84 + 184 moves to
the farther staff are the open question -- a beamed group stems away from its own staff, and a stem reaches the neighbour whenever
the gap is under about 3.5 sp. `distance -> stem` is the class most likely to be wrong; the tiles sample it.

**Pending Sean:** `out/print/stem_owner/tile_01..10.png` + `questions.txt` (answers in `key.json`, not on the tiles). 1-2 are his
3 and 7; 3-10 are seeded changes: 3 where the stem moves a head to the farther staff (5, 7, 9), 3 where stem and ledgers disagree
(4, 8, 10), 2 where the stem answers a head the ledgers could not (3, 6). Not merged; `OMR_STEM_OWNER` stays off.
**Not fixed / said plainly:** the reach test is a 1 sp band, not "beamed to notes on the staff" (beam joins are not read); the
reader sees ONE stem per head (a chord's inner heads read `both` and stay silent); the replay reads the raw page raster where the
gather reader would read the same (`pws.page.rgb`) -- equal by construction, not yet shown by a re-gather.
Scripts: `stem_owner_extract.py`, `stem_owner_measure.py`, `stem_owner_lib.py`, `stem_owner_replay.py`, `stem_owner_report.py`,
`stem_owner_tiles.py`. Tests: `tools/omr/tests/test_stem_owner_2026_10_08.py`, 20 tests, 18 RED on the unrepaired tree (the two group
tests already pass on it: the 2.58c rule adopts an abstained copy's twin), then green.
Gates: `staged.check` TOTAL 192 -> 192; fast tier 6,150 passed (the two flag-doc tests failed until `OMR_STEM_OWNER` got its row in `docs/flags-2026-09.md`, then 37 of 37 pass).
