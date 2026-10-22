# 2.194 -- one shared ink map: the cause, measured (read-only; plan in docs/plan-2026-10-22-shared-ink-map.md)

Path: STAGED. Measured on the frozen page sample (8 pages per plate, `benchmarks/lane-report/sample.json`) from the 20261020-night
slices (`library/_shared-records/lane-report-slices-20261020-night/`), the whole Litolff record streamed once for byte shares. No
gather was run; no code under `tools/` changed. Scripts here: `census_functions.py` (static), `census_quantities.py`,
`census_verdicts.py`, `disagreements.py` (record), `crops.py` (18 crops, my look, `out/print/2.194-ink-map/`). Results in `results/`.

## Cause (rule 3), in plain words
Every reader measures the ink itself, from the raster, with its own cut-offs, and files its own quantity. The record then holds
several readings of ONE stroke (a stem, a beam, a head's hole, a ledger rung) that were never compared, and the adjudicators settle
their disagreement case by case. Where I could pair two readers of the same ink on the record they disagree on a third to a half of
the cells; on the 18 crops I looked at, the disagreement was usually one reader plainly wrong (a flag boxed as a beam, a stem the
"reach" ruler did not see) or a box that was never a head at all (a dot, a stroke), where the two readers were measuring different ink
under one wrong box -- an OWNERSHIP question asked as a measurement.

## 1. How many functions measure ink (static, `census_functions.py`)
- 205 functions read the raster or an ink helper directly (strict rule: names a raster AND a pixel op, or an ink helper), of 3,325
  functions in 155 modules; 75 of them in `gather.py`. A looser rule (names ink/run/column/px/stroke and uses numpy/cv2/slicing)
  gives 450 -- the "~500" in the ROADMAP row is this loose count.
- 787 module-level measured cut-off constants (`*_SPACES`, `*_PX`, `*_MIN`, `*_RATIO`, ...) in 44 files.
- 36 independent binarisation sites (`threshold 180`, `< 128`, `> 127` ...): the ink/paper line is drawn by hand in 36 places.
- "Where are the staff lines at this x" is implemented at least 10 times: `_local_staff_lines`, `line_rows_across_stem`,
  `line_band_beside`, `_hook_line_rows`, `local_line_thickness`, `header_ink.refine_staff_lines_in_cell`,
  `staff_detector.measure_line_geometry`, `meter_object._line_thickness`, `staff_line_removal.remove_staff_lines_from_cell`,
  `line_detection._column_stroke_bands`; 113 ink-touching functions name staff lines.
- The same stroke is read by these distinct quantities (frozen sample, Litolff rows): a stem by `stem` (cv_lines, 4,409),
  `head_stem_reach` (2,225), `stem_tip_ink` (1,313), `notehead_ink.stem_bridge`, `stem_slash` (4,409), `beam_stem_join` (3,326),
  `beam_stem_levels` (4,409) -- seven readers; a beam by `beam_stroke` from TWO readers (cv_lines and detector, 2,278),
  `beam_stroke_ink` (2,271), `beam_stem_levels`, `stem_tip_ink`; a head's fill by `notehead_ink` (interior window), the 2.148 slit
  (`head_fill_first`), the 2.159 located box, `notehead_recentre.fill`, `stacked_head_fit`, `head_oval`, `head_line_cut`; a ledger
  rung by `glyph_ladder` (detector), `ledger_rung_ink` (8,273), `ledger_ink_under` (3,865), `ledger_owner_density`,
  `far_head_owner_ledger`; an arc by `arc_box` (detector), `arc_ink_shape`, `system_arc`.
- `_ink_components` (connected components of the erased cell) is asked by 5 gather readers (memoised since 2.191).

## 2. How often two readers of one stroke disagree (`disagreements.py`, frozen sample)
| pair (same ink, two code paths) | Litolff | Brahms |
|---|---|---|
| beams in a cell: CV strokes vs detector beam boxes (cells with a reading) | 2,012 cells: agree 9%, both none 51%, presence disagrees 31% (detector only 21%, CV only 10%), count disagrees 9% | 1,640 cells: agree 5%, both none 31%, presence disagrees 55% (detector only 52%, CV only 3%), count 9% |
| head fill: detector class vs the ink window (`head_is_open`) | 303 of 5,147 heads (5.9%), all "detector black, ink hollow" | 77 of 5,687 (1.4%) |
| stem: finder found a stem, the reach ruler sees < 1 sp | 87 of 2,225 (3.9%) | 259 of 2,887 (9.0%) |
| ledger rungs: detector ladder vs CV rung ink, presence | 761 of 2,209 (34%) | 1,025 of 2,726 (38%) |
| arcs: detector arc boxes not inside any traced system arc | 424 of 1,403 (30%) | 2,644 of 4,630 (57%) |
| accidentals (2.190 FINDINGS, same sample): shape reader vs detector winner | switch 30 / agree 40 / unclear 7 of 80 | switch 85 / agree 134 / unclear 58 of 321 |
The readers' own words for it: `beam_stem_join:ambiguous` 4,210 / 1,828, `stem_tip_ink:ambiguous` 2,721 / 1,827 abstentions;
`stem_direction:stems_disagree` 796 / 350, `beam_discounted_uncertain` 423 / 2,072, `dot_role_ambiguous` 119 / 504 whole-movement
(overnight summary). Limits: `cv_beams`/`yolo_beams` are per CELL (the duration detail counts the cell's rows), so "presence
disagrees" is a cell whose beams one reader saw and the other did not; `head_stem_reach` exists only for heads with a finder stem, so
the opposite disagreement (reach sees a stem the finder refused) is not measurable here -- 2.167 measured it on tiles (33 of 40
no-stem real notes had a stem the finder refused).

## 3. The crop look (18 tiles, `out/print/2.194-ink-map/sheet.png`, key.json; MY look, not Sean's -- rule 7)
Beams (6): the CV reader right 4 (tiles 10-12 are Brahms eighths whose FLAG the detector boxed as a beam; tile 2's beams are plainly
there), the detector right 1 (tile 3, CV found no stroke under visible beams), unclear 1. Head fill (4): the ink right 2 (tiles 4-5,
Litolff halves boxed black -- 2.148's case), 2 moot (tiles 13-14: the "head" is a stem sliver and an augmentation dot). Stems (4):
the finder right 3 (6, 7, 16: a stem is plainly on the head; the reach ruler read 0.03-0.6 sp), 1 moot (15, a dot boxed as a head).
Ledgers (4): I cannot call them without a ruler; they are the right tiles for Sean. Unexplained remainder: 1 beam + 4 ledger tiles.
Lesson: 5 of 18 disagreements were about a box that is not a head -- the two readers measured different ink under one wrong box.
Ownership of the ink comes before any measurement of it.

## 4. Which guard rules exist to settle reader disagreement (fires on the frozen sample, Litolff / Brahms)
Of the refusal reasons in `notehead_is_not_a_notehead` and `rest_is_not_a_rest`, these say "two readers / two boxes disagree about
this ink": `stacked_head_duplicate` 253 / 53, `notehead_is_a_duplicate_box` 120 / 30, `rest_is_a_duplicate_box` 60 / 241,
`rest_has_a_stem` 58 / 13, `rest_stroke_into_a_head` 29 / 41, `rest_is_a_barline` 40 / 19, `tremolo_slash_crosses_stem` 43 / 47,
`is_a_rest_twin` 12 / 21, `is_a_beam_piece` 13 / 3, `head_cut_piece` 10 / 7, `on_a_rest` 2 / 7, `is_a_rest_shape` 7 / 0,
`is_an_arc_tail` 1 / 3, `rest_is_a_slashed_stem` 1 / 0; in `duration`: `beam_discounted_uncertain` 180 / 614 (narrowed),
`stem_tip_reads_no_beam` 88 / 534, `beams_ambiguous` 53 / 33, `head_fill_from_ink` 53 / 63, `hooks_counted` 14 / 41,
`open_head_flag_contradiction` 9 / 4, `flags_disagree` 0 / 1, `tip_readers_disagree` 1 / 0, `whole_class_filled_or_stemmed` 8 / 6,
`whole_class_on_a_stem` 6 / 36; plus 2.186's `one_ink_merged` (same-cell family merge) and the 2.172 view merge `production_stronger`.
Shape rules (`too_narrow` 100 / 914, `clipped_fragment` 192 / 169), ownership (`belongs_to_a_nearer_staff`), and the convention
claims (`claimed_by:*` 30 / 91) are NOT reader disagreement and stay.

## 5. Where the record's size comes from (`census_verdicts.py`; whole Litolff record streamed)
Litolff 20261020-night, 1,269 MB: verdicts 1,118 MB (88%), observations 92 MB (7%), pools 38 MB (3%), abstentions 21 MB (2%).
Inside the verdicts: the `basis` list is 64% (Litolff) / 77% (Brahms) of the bytes, `considered` 10-11%; `duration` verdicts are
70-80% of verdict bytes, `arc_kind` 23% on Brahms. A duration verdict cites 560 rows on average (median 177, max 4,600); within one
cell the heads' basis lists repeat each other x2.5 (Litolff) / x3.8 (Brahms); over the sample every observation row is cited ~31 /
~75 times. The ink MEASUREMENT rows (notehead_ink, ledger_rung_ink, stem, beam*, ink, pieces, ...) are about 30 of 1,269 MB.
So a stroke map will not shrink the record by itself; a verdict that cites a few stroke ids instead of every row of its cell will.

## 6. What is already a stroke map, in part
`Q.CELL_INK_PIECES` (one row per cell, the head/rest/flag-sized pieces with page boxes), `Q.INK` (per-cell component summary),
`Q.VERTICAL_RUN` (every stem candidate; research flag, OFF), `Q.CLAIMED_AREA` (2.177/2.181: owner, unit `area`, boxes_inside with
measured ink shares; `unit: ink` planned, never filed), `Q.SYSTEM_ARC` (a traced stroke with pieces and coverage). None carries a
stroke's own measurements (length, angle, thickness, local staff rows) and none is read by the stem, beam, head-fill or ledger readers.
