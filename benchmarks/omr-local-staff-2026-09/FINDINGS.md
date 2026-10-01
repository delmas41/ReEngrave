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

No whole-page or whole-movement re-gather was run this lane (Sean,
2026-09-29). The reference-backed truth set (truth_set_2_44c.py, branch
worktree-agent-ac053ee5c8a371951) was read for context (2.44c's own
numbers, quoted above) but NOT re-run against this change -- scoring the new
model against it is the natural next proof step and is named, not done,
consistent with "no pricing runs" as this lane's own standard.

## staged.check and the one open finding this lane could not close

pytest -m "not slow" tools/omr/tests: 4,190 passed, 0 failed (includes the new 9
tests added to this tree's own fast-tier baseline).

python3 -m tools.omr.staged.check: TOTAL 246 (was 245 on 8f1b2228,
confirmed by running check against a clean worktree at that exact commit)
-- staged.wiring rose from 67 to 68 open, status still ok (not broken). The
new entry is DETAIL Q.NOTEHEAD_STAFF_POSITION.local_staff_lines -- written
by gather_notehead_positions, read by nothing but
readout._position_words (which shows it in the stage-readout hover text,
the exact "never show a ruler built the wrong way" requirement), and
readout.py declares DERIVED_CHECK = True, so wiring.py's own fourth
exclusion (a "sibling instrument" that NAMES a quantity for display is not
a CONSUMER of it, by the same rule a test or a benchmark probe is not) does
not let that mention close the gap. Wiring it into a real DECISION-stage
consumer this round would have meant switching a second consumer (the
brief's own instruction says not to); leaving the detail off the row
entirely would have put the local/flat distinction nowhere a later reader
or crop could ask for it, which is the exact silent-fallback CLAUDE.md §10
exists to forbid. Recorded honestly in KNOWN_GAPS (wiring.py) with its own
reason, same as every other open wiring finding in this tree -- this is
the one number in this lane's proof that did not come in under the stated
ceiling, and it is reported rather than hidden.

## Not verified

- The fallback-reason COUNTS on the two count pages (how many cells decline
  to how many each reason) were not measured this lane -- doing so needs a
  re-gather, which this lane's own proof standard (microscopic tests, not
  pricing runs) defers to whoever runs the next scheduled re-gather.
- Whether the local model, wired into gather_notehead_positions, actually
  turns any of 2.44c's 16 Litolff misses right (or any of its 31 rights
  wrong) is NOT measured -- that needs scoring against truth_set_2_44c.py
  on a real record, which is a re-gather and is named as the next step, not
  done here.
