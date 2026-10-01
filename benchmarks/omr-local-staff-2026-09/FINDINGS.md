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
