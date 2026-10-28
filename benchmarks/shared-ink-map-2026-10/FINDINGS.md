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

# 2.195 -- step 1: the `Q.STROKE` producer (OFF flag `OMR_STROKE_MAP`, nothing reads it)

Path: STAGED GATHER. Built: `tools/omr/staged/stroke_map.py` (pure; run analysis on the staff-erased cell reduced to 16 px a space; `LocalStaff.lines_at(x)`),
`gather.gather_stroke_map` (after `gather_system_arcs`, before every ink reader), `Q.STROKE` / `READERS.CV_STROKE`, reach / wiring / capture entries,
`docs/flags-2026-09.md` row, `tools/omr/tests/test_stroke_map_2_195.py` (12 tests; controls: a broken kernel loses the stem, a wrong staff reference
moves the steps, a flipped angle sign fails). Scripts here: `stroke_parity.py` (coverage), `parity_live.py` (re-run the map on the sample pages without a
gather, to sweep a constant), `stroke_crops.py`, `byte_control.py`. Results in `results/2.195/`. Frozen sample, both plates, one gather per arm.

## Cause / lesson (rule 3)
The plan expected the shared map to reproduce the finders' populations at >= 99%. It does for stems (100% / 99.95%) and, counting ink of ANY kind, for CV beams
(100% / 100%). Everywhere else the misses are not the map failing to see ink; they are old rows with no ink of their kind under them, which is the plan's own
lesson (ownership before measurement) showing up as a coverage number. I looked at 44 crops (Litolff 36, Brahms 8; my look, rule 7): 

- **detector beam boxes (79% / 75% covered)**: of the 293 / 835 misses, 36 / 79 sit on EMPTY paper (8 of 8 crops: a wide box across a bar with only a head or a rest in it),
  187 / 564 on a vertical stroke (a stem or flag boxed as a beam: the 2.194 finding again), 55 / 130 on a blob. The map is right in every crop I looked at.
- **CV beam rows (92% / 98%)**: all 62 / 10 misses are rows laid on a head-and-stem blob or a lone stem (tiles: a "beam" box on a black head); with any stroke kind counted, 100% / 100%.
- **ledger rungs (84% / 89%)**: the rung passes BEHIND its head, so what is left of it is two stubs shorter than the 1 sp horizontal opening, fused to the head's blob (or cut at the
  cell edge); the map has the ink as one blob, not a rung. This is a real limit of run analysis and is step 7's question (a rung read at the ledger steps, not found by length).
- **system arcs (77% / 80% as horizontal+curve strokes; 89% / 93% counting any stroke)**: an arc is cut at barlines, thinning to a hair at its tips and broken by stems and heads it
  passes; the strokes are there where the ink is thick and absent for the last tapered tenth of a space. Parameter sweeps (cover threshold 96 -> 40, area floor 0.05 -> 0.01, curve
  thickness 0.5 -> 0.7 sp) moved arcs by < 3 points and nothing else, so they are not a tuning bug.
**Process lesson:** a coverage target stated against old readers' rows measures the old readers as much as the map; the useful number is the miss list by the kind of stroke under the miss
(`*_miss_is_*` in `results/2.195/`), which is what step 3 / 4 / 5 consume. The >= 99% bar is met for stems only; I did not tune the map toward the old rows (that would be
agreement with our own reading, rule 5).

## 1. Coverage parity (`stroke_parity.py`; rows from the gathered ON records; box-level, kind-compatible)
| existing quantity | Litolff covered | Brahms covered | any stroke kind |
|---|---|---|---|
| `Q.STEM` (cv_lines), vertical strokes, >= 80% of the height | 4236 / 4236 = 100.0% | 4293 / 4295 = 99.95% | |
| `Q.BEAM_STROKE` cv_lines, horizontal/curve, >= 50% of the width | 732 / 794 = 92.2% | 399 / 409 = 97.6% | 100% / 100% |
| `Q.BEAM_STROKE` detector | 1097 / 1390 = 78.9% | 2524 / 3359 = 75.1% | 82.4% / 77.4% |
| ledger rungs present (`Q.LEDGER_RUNG_INK` true) | 296 / 354 = 83.6% | 1424 / 1596 = 89.2% | 85.9% / 89.5% |
| `Q.SYSTEM_ARC` (every cell of its staff; horizontal/curve) | 583 / 755 = 77.2% | 1090 / 1358 = 80.3% | 89.3% / 93.3% |
Misses by the kind of stroke that holds the box's ink: CV beam: vertical 31 / 4, blob 31 / 6. Detector beam: vertical 187 / 564, blob 55 / 130, none 36 / 79, horizontal (partial) 14 / 57, curve 1 / 5.
Controls: (a) the live re-run (`parity_live.py`) reproduces the gathered record exactly (47,780 strokes, same parity); (b) `--shuffle` (every cell's strokes drawn from another cell) gives stems 7.4%,
beams 7-8%, rungs 0%, arcs 0.9% -- the measure can fail; (c) the unit tests above.

## 2. Bytes and seconds
Records written by the arms (`indent=2`): Litolff 8 pages 476.9 -> 552.8 MB (+75.9 MB, **+9.5 MB a page**; 47,780 rows, 5,973 a page); Brahms 1,415.7 -> 1,515.2 MB (+99.6 MB, **+12.4 MB a page**; 65,084 rows,
8,136 a page). A row is ~0.7 KB compact / ~1.4 KB `indent=2` (the same flat-row cost `Q.INK`'s per-component form had; in line with the plan's 20-60 rows a cell: ~18 (Litolff) / 32 (Brahms) after the 0.05 sp^2 floor,
which dropped 18 pieces on the first Litolff cell I looked at). Slimming (cap `profile_sixteenths`, `touches`, `staff_lines_*`) is the first thing step 2 should do; I kept every field the plan names.
CPU of `gather_stroke_map` alone (process time, sample pages, warm; `parity_live.py`): Litolff **5.7 s a page** (45.3 s / 8), Brahms **7.3 s a page** (58.4 s / 8). Against 2.191's gather CPU
(Litolff ~107 s a page, Brahms ~291) that is about 5% / 2.5%. Wall time of the four arms was 29 / 33 min (Litolff off / on) and ~55 / ~49 min (Brahms) on a box shared with another lane's gathers
(wall swings 2x here, 2.191), so I do not quote it.

## 3. Lane report (`lane_report --flag OMR_STROKE_MAP --from gather`; `results/2.195/lane_report.txt`)
Litolff: **NOTHING CHANGED in the exported file**; red bars 0 -> 0; judged right->wrong 0 (233 tiles). Brahms: red bars 166 -> 166, notes not written 3202 -> 3202, judged right->wrong 0 (232);
the file differs by **words -1**. That word is NOT the strokes' doing, and I say what I can and cannot show: the record-level control (`byte_control.py`, every non-stroke observation and abstention
of OFF vs ON as a multiset, ids and timings stripped) finds exactly one row in only one arm on Brahms observations -- a `direction_word` -- and on abstentions 77 `direction_word` rows (their Surya page counters
`page_n_read` 45 vs 40); Litolff: 27 `margin_label` rows (Surya tiers vs Tesseract: 14 vs 13) and 254 `direction_word` abstentions. Every other row of every other quantity is identical, which is the control; a
word read through Surya varies between two runs of UNCHANGED code (2.191 FINDINGS: 26 values on Brahms). I did NOT run a second OFF gather to show the same one-word swing with the flag off (a 50-minute Brahms
arm); so "byte-identical" is shown for the record minus Surya's words and for the file on Litolff, and is one Surya word short on Brahms. No tiles are needed for a step that changes no verdict; the report drew 2.
Nothing reads `Q.STROKE` (`check` lists it as producer-only), which is why no row can reach the file.

## 4. `check`
`python3 -m tools.omr.staged.check`: open findings **193 -> 205 (+12)**, every one the by-design producer-only entry the discipline asks for (`reach` +1: `Q.STROKE` unread; `wiring` +11: the detail keys
nothing reads), named in `reach.py` / `wiring.py` and leaving the day step 3 reads the rows. "Not up" cannot hold for a new unread quantity; nesting the fields under one key would have made it +2 and hidden the
names a consumer needs, so I did not.

## 5. One bug the full fast tier found
The first draft put `_STROKE_GLYPH_BASE` at 400,000, ON `review/human_evidence.HUMAN_GLYPH_BASE` (`test_stage_review_evidence::test_the_offset_base_cannot_collide_with_any_gather_reader`
failed in the 29-minute fast tier, 8,783 passed). Moved to 375,000. The four gathers above were made with 400,000: only the stroke subjects' last coordinate differs (400,000+i vs 375,000+i), no
coverage, byte or timing number depends on it. Nothing in a gathered record could have collided (no human box is added to a gather).

# 2.198 -- step 2: `Q.GLYPH_STROKES`, the register's `ink` branch, slimmer `Q.STROKE` rows (flag group `OMR_STROKE_MAP`, producer only)

Path: STAGED GATHER. No new flag: 2.195's `OMR_STROKE_MAP` (default OFF) is the master switch of the whole group. Built on `lane-2.195-stroke-map`, main merged in. Nothing reads any of it.
Built: `stroke_map.strokes_in_box` (+ masks kept on `CellStrokes`, never filed); `gather_glyph_strokes` (right after the map, when the box set is final): `Q.GLYPH_STROKES`, one row per detector
box of every pass, value = ordinals of the cell's strokes of which >= 0.5 of the stroke's ink lies inside the box (the register's one cut, `claims.INSIDE_SHARE_MIN`, not a new number), `shares`,
`partial` (strokes with some ink inside and less); an EMPTY list is a fact, a cell with no stroke map ABSTAINS per box (rule 8). `gather_claimed_register(stroke_cells=)` files a `unit: ink`
`Q.CLAIMED_AREA` row beside each CLEF area claim (detector clef box: its `Q.GLYPH_STROKES` strokes; located clef: strokes >= 0.5 inside the fitted area); an owner on no stroke abstains.
Meter claims and the header column get no ink claim (the column is a convention area, the meter's pieces span two cells): said, not built. `claims.covering(rows, key, box_strokes=, cell=)` gains the
`ink` branch; without `box_strokes` it reads exactly what it read. Tests `tools/omr/tests/test_glyph_strokes_2_198.py` (16; controls: a moved box loses the stroke, a box on paper is `[]`, a mark numbered
just under the base is still listed).

## Cause / lesson (rule 3): the byte cost was not the rows
2.195's +9.5 MB a page was blamed on the row size. First ON gather of this lane (Litolff pages 2,4): the file grew +10.2 MB a page although the rows were already 26% slimmer. The rows are 3.5 MB a
page; the rest sat in the `evaluation` and `inference` sections (+5.9 MB each over two pages): `Log.subjects(Kind.GLYPH)` listed each stroke (a glyph subject) and every EVALUATE rule wrote a
"skipped: cause_absent" line for it, 13,441 strokes x the rules. Fix: `Log.subjects(Kind.GLYPH)` does not list subjects numbered `STROKE_GLYPH_BASE <= g < 400,000` (record.py; a flag-off record holds none, so
nothing there changes). Process lesson: a record-size claim needs the file's per-section bytes, not the rows' bytes.

## 1. Bytes a page of the `Q.STROKE` rows (`slim_bytes.py`: the same strokes, 2.195 filing copied verbatim vs the real function; compact JSON, which is how the file is written)
Slimmed: dropped `area_sp2` (= fill x box area), `component_n_strokes` (count of rows sharing `component`), `staff_lines_left/right` (what a consumer takes from them is `end_steps_from_top` and
`staff_space_local_px`, which stay), `profile_sixteenths` on blobs (their named fields are `fill`, `hole_share`), `staff_local` unless False, `cell_n_below_floor` once per cell (first row); `ends` one flat list.
| | rows | before | after |
|---|---|---|---|
| Litolff p2 / p4 | 6,816 / 6,625 | 4.81 / 4.67 MB | 3.57 / 3.48 MB (-25.7% / -25.4%) |
| Brahms p4 / p5 | 9,560 / 9,939 | 6.71 / 7.00 MB | 4.99 / 5.22 MB (-25.7% / -25.4%) |
Per page: Litolff 4.74 -> 3.53 MB, Brahms 6.85 -> 5.10 MB. Check: the real ON Litolff record holds 13,441 stroke rows = 7.04 MB (3.52 MB a page), the live NEW figure. `Q.GLYPH_STROKES`: 5,774 rows, 1.35 MB for
two Litolff pages (0.67 MB a page). Still ~520 bytes a row; what is left is the envelope and the named fields -- pooling per cell is plan step 9. File-level numbers in section 2.

## 2. Byte-identical check (final code, main merged; PYTHONHASHSEED=0, detector cache, `--musicxml`; all arms re-gathered after the merge, one at a time)
Litolff pages 2,4 and Brahms pages 4,5, flag OFF vs ON: the MusicXML is byte-identical on both (`cmp`), and so is Litolff's coverage JSON. Record-level (`byte_control.py`): Brahms ON differs from OFF only by
rows the flag files: 9,282 `glyph_strokes` + 81 `claimed_area` (the `ink` claims) observations and 1 `claimed_area` abstention (a clef box on no stroke); 19,499 stroke rows; every other row identical.
**File bytes a page, whole record (the real measure)**: Litolff 137.40 -> 146.01 MB for 2 pages = **+4.3 MB a page** (2.195: +9.5); Brahms 373.62 -> 386.56 MB = **+6.5 MB a page** (2.195: +12.4).
`evaluation` / `inference` sections: identical to OFF (the `Log.subjects` fix); verdicts +0.17 MB on Litolff (not traced, small).
**OFF-vs-OFF control (Brahms 4,5, two gathers of the same code, flag off): 0 rows differ and the MusicXML is byte-identical.** So 2.195's one Surya/Tesseract word did NOT reappear here: it neither
shows the swing is reader noise nor that it is the flag's -- this pair of runs is clean, and the ON-vs-OFF pair is clean too. Said plainly: the question is not settled by this, only not reproduced.

## 3. Sanity count: 2.185's same-cell different-class doubles as shared stroke sets (`glyph_strokes_census.py`, Litolff pages 2,4 ON record)
199 pairs (same cell, different class, IoU >= 0.5): **167 stand on the same stroke set**, 28 overlap without being equal, 4 have an empty list. Examples: a head and a whole rest on one blob,
keyFlat/keySharp on three strokes, dynamicF/dynamicZ. Control: 10,559 same-cell different-class pairs with IoU 0 and strokes: none shares a stroke. Brahms pages 4,5: 459 pairs, **382 same stroke set**, 68 overlap not equal, 9 empty list; control 54,560 IoU-0 pairs, none shares a stroke.

## 4. `check`
`python3 -m tools.omr.staged.check`: TOTAL 203, status ok. By design: reach +1 (`Q.GLYPH_STROKES` unread), wiring +2 (`Q.GLYPH_STROKES.shares`, `Q.CLAIMED_AREA.shares`). wiring -5 stale entries removed (`area_sp2`,
`staff_lines_left` truly gone; `profile_sixteenths`, `staff_local`, `cell_n_below_floor` are still written but through a conditional dict the tool cannot see, so the drop is partly the tool's blind spot).
Fast tier (final code): 8825 passed, 0 failed (12 skipped, 2 xfailed).


# 2.202 -- step 3: a head's beams from the stroke map (flag `OMR_BEAMS_FROM_STROKES`, OFF; needs `OMR_STROKE_MAP` in the gather)

Path: STAGED ADJUDICATE. Built on `lane-2.198-glyph-strokes`, main merged in. Code and unit tests only: no gather, no `lane_report` was run (Sean's overnight re-gather was running).
Built: `tools/omr/staged/beam_strokes.py` (pure: a stroke's role from its own fields, what a detector beam box stands on, the strokes at a stem's tip); `rhythm._beams_from_strokes`
(reads `Q.STROKE` and `Q.GLYPH_STROKES` through `Evidence`, both added to `adjudicate_duration`'s `wants` and `composed_from`) called from `adjudicate_duration` right after the old beam
readers have spoken (`_kept_beams`, the side / beyond-the-tip / ink / neighbour / arc / slash / ledger filters, `_beam_levels`, `_beam_join_witness`, `_fused_double_beams`, the 2.140
stem-levels block) and BEFORE `strokes_before_hollow`, the hollow override, the flag reads, `certain_conflicts`, `beams_ambiguous`, `stem_tip_reads_no_beam`,
`beam_discounted_uncertain`, `hooks_counted` and `flag_ink_unread`; those later branches are untouched and see the stroke-map-adjusted `certain` / `possible` / `kept` / `flag_levels`.
`tests/test_staged_beams_from_strokes_2_202.py` (33 tests); `hook_beam_measure.py`; reach / wiring gap entries for `Q.STROKE`, `Q.GLYPH_STROKES` and three `Q.STROKE` detail keys
LEAVE (a decision reads them now); `check` open findings 203 -> 198.

## What it does (flag ON; a cell with no stroke map, a box with no `Q.GLYPH_STROKES` row, a head with no stem stroke in the map, a hollow head, a two-voice head: nothing changes, rule 8)
1. A DETECTOR beam box (`Q.BEAM_STROKE`, reader detector, kept by `_kept_beams`) is linked to its `Q.GLYPH_STROKES` row (the cell's `beam`-class `Q.GLYPH_BOX` with the same x,y,w,h). If no
   stroke under it is beam-shaped the box leaves the count and its level is kept as a CANDIDATE (`possible` = the old certain): the head NARROWS (`beams_ambiguous`), it does not decide.
   The reasons are named per box: `box_on_paper`, `box_on_a_stem`, `thin_or_curved_span`, `one_stem_stub`, `hook_or_stub`, `hook_on_a_beamed_stem`, `hook_on_another_stem`.
2. A box standing on a HOOK (one stem, thinner than a beam, <= 1.6 sp) that touches THIS head's stem, a stem that touches no spanning beam, is a FLAG (Sean 2026-10-22): the box leaves the
   beam count and the number of hooks at the tip is filed as the flag levels, used only where no flag box was attached and no beam level stands (`beam_evidence: "flag"`, the rows used are the hook strokes).
3. The beam-shaped strokes touching the head's own stem stroke inside the tip window (0.5 sp past the tip, 3.3 sp inward; `rhythm.BEAM_STEM_RUNS_PAST_MAX_SPACES` 2.5 + one beam) are counted,
   one per level. More than the old readers counted: a candidate only (`possible`), nothing is invented (rule 6). Fewer: the two readings disagree and the strokes cannot settle it
   (CV rows and strokes come off the same erased raster, so neither is the other's second witness): NARROWED between them (rule 8). Equal: decided as today.

## 1. The hook-vs-beam measure (`hook_beam_measure.py` on the 2.198 Litolff p2,4 ON record; `results/2.202/hook_beam_measure.json`; read-only, no gather)
Horizontal / curve strokes under the 373 detector beam boxes (395) and under the 39 detector flag boxes (15), by how many vertical strokes each touches:
| population | touches | n | length sp (min / median / p95 / max) | thickness sp (median) |
|---|---|---|---|---|
| under beam boxes | >= 2 stems | 192 | 1.0 / 5.6 / 10.3 / 17.5 | 0.63 |
| under beam boxes | 1 stem | 100 | 0.75 / 3.1 / 6.1 / 10.1 | 0.31 |
| under beam boxes | none | 103 | 0.6 / 2.3 / 6.5 / 10.9 | 0.25 |
| under flag boxes | 1 stem | 12 | 0.63 / 1.2 / 2.7 / 2.7 | 0.19 |
- **Beam thickness has a gap.** The 190 horizontal strokes touching >= 2 stems: 66 are 0.06-0.437 sp (slur / tie / hairpin remnants), 124 are 0.546-1.0 (median 0.653). The cut `BEAM_MIN_THICKNESS_SP` = 0.5 sits in the
  gap and is the engraving convention for a beam; Sean's own rule (2026-10-09, "the thickness of a beam is always more than a hairpin") says the same direction.
- **Hook length does not separate a flag from a beam stub.** The 12 one-stem strokes under flag boxes are 10 near-horizontal (0.63-1.45 sp, thickness 0.12-0.38) and two slanted curves (1.93, 2.69 sp).
  Of the 100 one-stem strokes under BEAM boxes, 32 are <= 1.6 sp, 9 are 1.6-2.4, 59 are longer. Length, thickness, sagitta and angle all overlap, so **no number on the stroke alone defines a hook**.
- **What does is the stem (structural, not a number):** a short one-stem stroke is a hook only on a stem that touches NO spanning beam; beside a spanning beam it is a partial-beam stub (Sean's
  one-stem rule makes that a candidate level, never decided). The only numbers left are the hook length cut (`HOOK_MAX_SPACES` 1.6 = the longest near-horizontal flag + 0.15, decided; up to 2.4 =
  `hook_or_stub`, narrowed, never decided; the 2.69 curve is not rescued) and the 0.5 beam thickness. Both are read off this one plate (n = 15 for the hook): CLAUDE §4 says a cut measured on our
  plates only NARROWS until another publisher confirms it, which is why the band between 1.6 and 2.4 exists and why Brahms must be measured the same way before any default (no Brahms ON record
  exists: the 2.198 Brahms ON arm was stopped for the overnight).
- **Not tuned to a target:** I did not look at which heads the rule changes before fixing the cuts, and no run of the rule on a file exists yet.

## 2. Tests (`test_staged_beams_from_strokes_2_202.py`, 33, constructed cells; every RED has a twin that must not fire)
OFF byte-identical (the same verdict value, detail, candidates with and without the stroke map in the log; flag ON without a map equals OFF). Beamed pair (decides as today). Flag misboxed as beam:
two hooks -> a SIXTEENTH flag (OFF: one beam level), one hook -> eighth flag; twins: hook on a stem that carries a spanning beam, hook longer than 2.4, hook in the near-miss band. Beam box on empty paper,
on a stem alone, on a thin slur across two stems (narrow); twin: a box on a real beam, a box with no `Q.GLYPH_STROKES` row, a CV stroke the map agrees with. Two beam levels (agree -> decided; a second
stroke no reader counted -> candidate; two strokes closer than a beam gap -> one level; the readers' two vs the map's one -> narrowed). **Controls that fail:** with `HOOK_MAX_SPACES` broken the RED flag
case stops being a flag; with `BEAM_MIN_THICKNESS_SP` broken a slur supports the box. Two bugs the tests found in my first draft: two hooks 0.35 sp apart merged into one level (real 16th hooks are ~0.7 sp
apart, the test geometry was wrong, not the rule), and a twin built with a CV row the box overlapped, which `_kept_beams` had already dropped.
Other tests run: `test_staged_duration`, `..._beam_stem_levels_2_140`, `..._beam_refused_off_the_tip_2_170`, `..._stroke_is_a_beam_2_141h`, `test_stroke_map_2_195`, `test_glyph_strokes_2_198`,
`test_staged_wiring`, `test_staged_reach`, `test_staged_check`, the four `test_flag_*` files: all pass. The full fast tier was NOT run (the box was busy).

## 3. What is NOT shown (said, not hidden)
No whole-file A/B, no byte-identity on a gathered record (the unit test is the OFF control), no Brahms stroke data, no tile. The tip window (0.5 / 3.3 sp), the 0.4 sp level separation and the stem-matching
slack (0.35 sp) are geometry taken from the stacking convention and `rhythm`'s own 2.141h number, not measured on strokes; the milestone should print each as a count of heads it touches.
Risks to look at first: (a) the downward disagreement (map counts fewer levels than the CV rows) narrows a CV-confirmed beam when the stem stroke is cut short or the beam stroke is split at a crossing;
(b) a stroke shared by two stems of a chord; (c) `Evidence.rows(Q.STROKE, SELF_AND_DESCENDANTS)` per head records ~30-100 ids in `considered` (record bytes: plan step 9's `pools`).

## 4. MILESTONE MEASUREMENT PLAN (to be run on a quiet box; NOT run now)
Prerequisite: the worktree `lane-2.202` with origin/main merged again; the overnight `summary.txt` says "done"; one lane on the box (CLAUDE §6).
```
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.202
python3 -m tools.omr.staged.lane_report --flag OMR_STROKE_MAP=1:1 --flag OMR_BEAMS_FROM_STROKES --from gather \
    --workers 2 --out out/lane-report/2.202 > out/lane-report/2.202.txt 2>&1
```
`--flag OMR_STROKE_MAP=1:1` puts the stroke map in BOTH arms (2.198 showed it changes no file: the OFF arm is main's behaviour with the map filed beside it), `--flag OMR_BEAMS_FROM_STROKES` is OFF in the first arm
and ON in the second, `--from gather` re-gathers the frozen sample's pages for both arms with the 2.189 detector cache (the flag acts in ADJUDICATE but the rows it reads exist only in a gather made with
`OMR_STROKE_MAP`; a replay of the 20261020-night record has none, and `lane_report` refuses `--from adjudicate` for a flag that needs a gather rather than print a clean zero). The report gives per plate what
changed in the exported MusicXML by kind (value, beam, flag, red bars, blue marks), judged right -> wrong against Sean's answers, and writes the 12-tile sheet and key.
Then, from the same out directory and one extra process (no new gather), for each plate count the heads by `beams_from_strokes.settled` in the ON record: `agrees` / `box_narrowed` / `box_flag` /
`stroke_candidate` / `disagree_narrowed` / (absent = the map could not speak) -- the 31% / 55% cells of plan §5 step 3 as decided / narrowed / contested counts, and per box reason
(`box_on_paper`, `box_on_a_stem`, ...). A flat table in `results/2.202/settled_counts.txt`; the mining script is written on the day (a 20-line stream over `observations` is enough).
**The 12 tiles** (blind, nothing of ours drawn, neutral orange box, key in a separate JSON; Sean answers right / wrong / what is it): about 9 are the CHANGED heads (the report draws them at random,
stratified by kind: `box_flag` heads (the hook-as-flag decision) get at least 3, `box_narrowed` 3, `stroke_candidate` / `disagree_narrowed` 3), and 3 are CONTROLS: one decided-and-unchanged beamed pair from
each plate, and the re-shown tiles (the report's seed-2188 controls are replaced by these three, same orange box): 2.170 tile 2 (`out/print/2.170-review/`, the HALF the beam rule must not turn into
a beam) and one clear beamed Litolff eighth from 2.153 tiles 4 / 14 / 16 (`out/print/2.153-review/`, Sean: "the stem clearly connects to the beam"), so a regression of the join shows. Judged right -> wrong
must be 0 over Sean's answers; the 12 tiles are Sean's to answer before any default is discussed.
The question for Sean at the milestone (plan §5 step 3, now narrowed by his 2026-10-22 ruling): when the box is a beam but the stroke is a hook on a stem with no beam, the file already writes a flag; the tile
asks "is this a flag or a beam?" on the box's ink, and the hook length cut (1.6 / 2.4 sp) is confirmed or moved on his answers.

# 2.204 -- step 4: a head's stem from the stroke map (flag `OMR_STEMS_FROM_STROKES`, OFF; needs `OMR_STROKE_MAP` in the gather)

Path: STAGED ADJUDICATE (+ a two-line GATHER gate). Built on `lane-2.202-beams-from-strokes` (`08fa1bb57`), main merged in. Code and unit tests only: no gather, no `lane_report` was run (2.202 was gathering).

## Cause (rule 3) and what it teaches
"Which vertical stroke is this head's stem" was never asked once. It is asked by seven readers (the finder `Q.STEM`, `head_stem_reach`, `stem_tip_ink`, the 2.161 bridge, `stem_slash`, `beam_stem_join`, `beam_stem_levels`), each on the raster with its own
cut-offs, and each pair got a rule written for its disagreement: the finder vs the reach ruler disagree on 3.9% / 9.0% of heads (section 2 above); `refuse_owned` took 58 / 126 real stems away because a false rest/flag box sat on them
(plan section 3); 2.167 found 33 of 40 "no stem" real notes had a stem the finder refused. Those are not three measurement faults, they are one ownership question (is this stroke a stem of THIS head?) answered by geometry in three places
and by the finder's refusals in a fourth. The stroke map already separates the vertical strokes (2.195: `Q.STEM` is covered 100% by vertical strokes), so the question is a join: the head's blob, the vertical stroke beside it, the engraving side.
Lesson: when the same ink is read by several readers, the first thing to build is the join that says which ink belongs to which mark; the cut-offs then shrink to the one the join needs (here: the bridge gap).

## Built
- `tools/omr/staged/stem_strokes.py` (pure; `reach.NOT_A_STAGE`): `head_stem(views, head_box, space, whole_head, other_heads, cell_width)` -> `StemReading` with `state` (stem / two_stems / bridged / no_stem / whole_head / wrong_side / through_head / barline / unanchored / ambiguous),
  the accepted `StemCand`s (stroke row ids, merged box, side, direction, tip end / y / staff step as the map measured it at the stroke's own x, length in sp, distance from the head) and every candidate with the reason it was refused. The rule: the stroke the head touches on the engraving side
  (up -> right, down -> left); a stem that passes the head (chord middle, a second's displaced head) takes its direction from the head its END stands in; a whole head reads no stem. The three old rules on strokes: 2.161 bridge (`bridged`, gap <= 0.35 sp, no head in the gap), 2.169
  pair (a stem each side, each ending in the head -> `two_stems`; two collinear halves cut by a beam or ledger rung -> ONE stem), 2.155 edge (a stroke at the cell edge that ends in no head, or longer than 8 sp, is a barline).
- `rhythm._head_stems` / `_bridged_from_strokes` / `_tips_from_strokes` / `_tip_obs` / `_tip_abs` / `stem_reach_equivalent` (+ `ownership._stem_owner`): the reading is set against the finder's. Agree -> the finder's own row, decided as today. Strokes find a firm stem the finder did not (`gained`) -> a stand-in
  row carrying the stroke's id. The finder's stem is a stroke the convention refuses for this head (`old_refused`: wrong side, barline) -> the strokes settle it, the finder's row is dropped. The finder's stem is not a stroke beside the head at all, or strokes touch the head and refuse every one while the
  finder attached a stem (`disagree`) -> `adjudicate_stem_direction` and `adjudicate_duration` ABSTAIN `stem_readers_disagree` with the candidates (EXPORT counts it; colour is EXPORT's). The map being SILENT about a finder stem (no vertical stroke beside the head; a stem under 1.5 sp is not a stroke) is not a
  disagreement: as today (rule 8 both ways). A vertical stroke no head touches, or touches on the wrong side, is a candidate in the detail and never a stem (rule 6). Recorded in `detail["stems_from_strokes"]` (state, settled, candidates, gained, old_refused, directions).
- The tip readers: the four accessors (`_stem_tip_flag_ink`, `_stem_tip_disputed`, `_stem_tip_unread_why`, `_no_beam_at_the_stem_tip`) read `_tips_from_strokes` instead of `Q.STEM_TIP_INK`: hook strokes at the tip of an unbeamed stem -> True (counted; hook_or_stub bracketed 1..2);
  a beam, a beam stub, or a stem that carries a beam -> `runs_on`; ANY other stroke within reach of the tip -> `occupied` (never a clean tip); nothing -> False (clean). A cell with no stroke map falls back to the GATHER rows (older records replay as before).

## Retired when ON (unreachable) / unchanged when OFF
- `head_stem_reach`: no ADJUDICATE read of `Q.HEAD_STEM_REACH` survives the flag (`_own_stem_side`, `_second_only_evidence`, `ownership._stem_owner`; `_flags_on_reach_stem` is unreachable because `reach_stem` is never true), and GATHER does not file the row (`gather_head_stem_reach` skipped when `OMR_STEMS_FROM_STROKES` and `OMR_STROKE_MAP` are both on).
- `stem_tip_ink`'s scan: `Q.STEM_TIP_INK` is not read (the four tip accessors) and GATHER does not file it (`_observe_stem_tip_ink` skipped under the same two flags). A static test counts the reads in `rhythm.py`.
- `refuse_owned`: BYPASSED, not deleted -- the stroke reading never passes through the finder's refusals, so a stem under a false rest/flag box is found. It still shapes the `Q.STEM` rows that other, not-yet-moved readers (beam join, stem value, articulation owners) consume; removing it from the finder would change all of them at once, so it waits for step 10.
- Side effect to say aloud: `_second_only_evidence`'s `stem_reach` witness (an independent ruler on the UNERASED raster) is gone; the stroke stem is already counted as `stem_box`, so a second-detector-only head has one stem witness where it had two (conservative: more refusals, no new notes).

## Tests (`tools/omr/tests/test_staged_stems_from_strokes_2_204.py`, 58, constructed cells; every RED has a twin that must not fire)
Pure: up-stem right (twin: same stroke on the left = `wrong_side`), down-stem left (twin: on the right), a stroke through the head, length / tip / staff step off the stroke, a stroke beside another head, a chord on one stem (both heads take it), a second's displaced head (twin: no head sees the stem on the
engraving side -> `wrong_side`), a stem each side = `two_stems` (twin: two same-side strokes = `ambiguous`), a stem cut by a ledger rung = ONE (twins: a gap too wide; two columns; a beam on both halves widens the gap), a barline (> 8 sp; unanchored; cell edge unless an end stands in a head), a whole note
(the stroke is shown, never made its stem), the bridge (twins: too wide a gap; a head in the gap; the wrong side). Integrated through `adjudicate.run`: OFF byte-identical with and without the map; ON without a map changes nothing; ON agrees (up, down, chord); ON gains a stem the finder refused; a stroke no head touches /
on the wrong side / by a whole head -> no stem, as OFF; ON a finder stem that is a barline to the strokes -> `stem_readers_disagree` (twin: OFF decides `up` as main); the strokes settle a finder stem on the wrong side (`old_refused`); the unison case still abstains `stems_disagree`; the owner witness's page-px tip.
Retirement: the OFF accessor reads the planted `Q.STEM_TIP_INK` row (True), the ON accessor ignores it and reads the stroke (False), ON with no map falls back to the row; ON the ruler is not a head's side; a static test on the sources. **Controls that fail:** with `engraving_side_ok` forced True the wrong-side case becomes a stem; with `STEM_MAX_SPACES` raised the barline becomes a stem.
Other tests run (serially): the 48 test files naming the stem / tip / reach quantities, `test_staged_beams_from_strokes_2_202`, `test_stroke_map_2_195`, `test_glyph_strokes_2_198`, `test_staged_wiring`, `test_staged_reach`, `test_staged_check`, the flag-doc tests: all pass (1,938 + 268). `inventory --check` green; `check` open findings 197 (was 198).
Two things the tests found in my first draft: a stem that PASSES a head took its direction from the head's side, which called a second's displaced head's stem a down-stem (now: from the head its end stands in; the displaced head sees it on the far side by design); and the test cell lacked `category: notehead` on the box row `_heads_in` filters on.

## What is NOT shown (said, not hidden)
No whole-file A/B, no record, no tile, no Brahms data. The six cuts (`BRIDGE_MAX_GAP_SPACES` 0.35 from 2.161's one-plate 0.13-0.27; `END_IN_HEAD_SLACK` 0.3; the two collinear-join cuts 0.3 / 0.6; the flush fractions 0.6 / 0.4; the 0.4 vertical-overlap share) are geometry stated before any count and NOT fitted -- the milestone must print how many heads each touches. Risks to look at first:
(a) `disagree` abstentions replace decided notes with unread bars where the finder was right and the map is wrong (a stem cut short, a head box that stops short of the chord's stem): the count and the tiles tell, right -> wrong must stay 0, but decided -> unread is a loss to count;
(b) `_heads_in` needs `category: notehead` on the box row (true on gathered records, absent on the old test helpers): without it a PASSING stem reads `unanchored`;
(c) `cell_width` is not passed (the bar-edge test is dormant in the adapter; the pure function has it): a barline at the cell edge relies on `unanchored` / the 8 sp cut;
(d) the clean-tip reading (`False`) is firmer than the GATHER shape reader's `ink_not_flag_shaped`: it feeds 2.146 ("clean tip decides no beam"); a beam stroke the map did not record as near the tip would read clean;
(e) the memo `rhythm._STEM_MEMO` holds one `Log` alive until the next decision replaces it.

## MILESTONE MEASUREMENT PLAN (to be run on a quiet box; NOT run now)
Prerequisite: `lane-2.204` with origin/main merged again; the overnight/2.202 gather finished; one lane on the box (CLAUDE section 6).
```
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.204
python3 -m tools.omr.staged.lane_report --flag OMR_STROKE_MAP=1:1 --flag OMR_STEMS_FROM_STROKES --from gather \
    --workers 2 --out out/lane-report/2.204 > out/lane-report/2.204.txt 2>&1
```
`OMR_STROKE_MAP=1:1` puts the map in BOTH arms (so the arms differ by one flag, and 2.198 showed the map alone changes no file); `OMR_STEMS_FROM_STROKES` is OFF in the first arm, ON in the second. `--from gather` is required: the flag is named in `gather.py` (it gates the two scans), so `lane_report` refuses an ADJUDICATE replay, and the OFF arm
must still file `Q.HEAD_STEM_REACH` / `Q.STEM_TIP_INK` while the ON arm must not (that is what "retired" means).
**2.202's flag (`OMR_BEAMS_FROM_STROKES`) is in NEITHER arm** for this run: 2.202 is not landed or measured, and with it in both arms the stems effect would be read through a beam change nobody has seen on a tile. This is the attribution run. A SECOND run, only if the first shows changes, repeats it with
`--flag OMR_BEAMS_FROM_STROKES=1:1` (2.202 in both arms): the two lanes share `own_stems` and both read the tip, so the stack is what would ship; report the second as a control, not a result.
The report gives, per plate, what changed in the exported MusicXML by kind (value, beam, flag, red bars, blue marks, and `stem_readers_disagree` bars), and judged right -> wrong against Sean's answers (`python3 -m tools.omr.staged.judged`). Then, from the same out directory and one extra pass (no gather), count per plate the heads by
`detail["stems_from_strokes"].settled` in the ON record -- `agrees` / `gained` / `old_refused` / `disagree` / `map_silent` / `no_stem_candidate_only` -- and by `state`; the `disagree` count by `disagree` reason; heads decided -> unread (risk a). That table is the answer to "the 87 / 259 reach disagreements named" (plan step 4) and to 2.167's 33 of 40.
**The tiles (12, blind, nothing of ours drawn, neutral orange box on the head, key in a separate JSON; Sean answers right / wrong / what is it):** about 9 are CHANGED stem decisions, drawn at random stratified by kind: `gained` 3 (a stem the finder refused now in the file), `old_refused` 2, `disagree` 3 (the head now unread, shown as "is there a stem here, which way?"), and
1 changed value or direction. 3 are CONTROLS: (1) 2.150 tile 11 re-shown and (2) 2.150b tile 20 re-shown (the "stems of quarter notes" tiles; see `docs/DECISIONS.md` 2026-10-16, the 2.150b line -- the PNGs are in the old agent worktree `/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/agent-a6fd65f56a127e4f7/out/print/2.150-review` and `.../2.150b-review` (coordinator, 2026-10-25); at milestone time copy tile 11 and tile 20 into this worktree's `out/print/` -- not copied yet), and (3) one decided-and-unchanged
beamed Litolff eighth (2.153 tile 4 / 14 / 16: "the stem clearly connects to the beam") so a regression of the join shows. Judged right -> wrong must be 0 over Sean's answers; the 12 tiles are Sean's to answer before any default is discussed.
The question for Sean at the milestone (plan step 4): "re-show those two tiles (stems of quarter notes)", plus one plain question on the bridge cut: a stem standing a hair beside the head's box on the right (up) or left (down) is that head's stem -- may it speak, or only narrow?

## 5. MILESTONE RESULT (2.202; main 78a0144fe merged; fast tier 8,962 passed; `lane_report --flag OMR_STROKE_MAP=1:1 --flag OMR_BEAMS_FROM_STROKES --from gather`; `results/2.202/`)
Cause first: the hook-as-flag path almost never fires, and the reason is upstream of it. Of the map's 122 (Litolff) / 332 (Brahms) detector beam boxes standing on a "hook", 118 / ~300 stood on a stroke leaning on a
BARLINE or a cell-height vertical, not a stem (the first draft counted any vertical; fixed with `STEM_MAX_SPACES` = 8, measured: the 4,260 verticals that coincide with a `Q.STEM` row are 1-8 sp, the unmatched pile up at 8 and 12), and
the 2.74 ink test had already dropped the rest from `kept` (fixed: pre-filter boxes are read). Process lesson: a funnel count made on the rows alone (`hook_box_funnel.py`) overstated the population 50x; the head-level reach
(verdict details) is the number.
- **Measure 1, exported file (Litolff / Brahms):** notes +2 -133 / +6 -113, beams +2 -131 ~17 / +3 -78, flags +19 -14 / +19 -29, blue marks +2 -34 / +69 -32, red bars 0->0 / 166->167, notes NOT written 2563->2694 / 3202->3311
  (about 130 and 110 notes held out: the narrowed beams leave bars the bar sum will not settle). **Measure 3, Sean's judged answers: right->wrong 0 / 0**, right->narrowed 4 / 1, wrong->right 0 / 1.
- **Control (Litolff, same flags both arms): NOTHING CHANGED**, 5029 = 5029 notes, 2563 = 2563 held out, box quiet. A replay of the OFF gather confirmed OFF reproduces its own record (0 of 8,958 differ).
- **`beams_from_strokes.settled`, first duration verdicts (Litolff 7,399 / Brahms 9,676):** map could not speak 4,518 / 5,726; agrees 2,642 / 3,716; stroke_candidate 179 / 112; disagree_narrowed 57 / 79; box_narrowed 2 / 34;
  box_narrowed+stroke_candidate 1 / 7; box_narrowed+disagree_narrowed 0 / 2. **Hook-as-flag decided at 0 heads on Litolff, 2 on Brahms.** Heads whose live duration changed: 158 / 119. Box reasons: Litolff 411 no beam- or hook-shaped stroke,
  36 on paper, 12 hook on another stem; Brahms 3,347 / 476 / 130, `thin_or_curved_span` 50, `one_stem_stub` 85, `hook_or_stub` 152.
- **Tiles `out/lane-report/2.202m-tiles/tiles/sheet.png` (key `../key.json`):** 12 = 9 changed (2 hook-as-flag -- all there are --, 4 disagree_narrowed, 3 stroke_candidate) + 3 controls (one unchanged decided beamed head, the re-shown 2.170 tile 2 and 2.153 tile 4); no two on one ink (boxes
  grown one space must not meet). 2.170 tile 2 is on page 5, outside the frozen sample, so it shows the tile, not a re-measured verdict. Question: "for each boxed note: is it an eighth, a sixteenth, a quarter, or something else -- and is the mark on its stem a flag or a beam?"
- **What the numbers say:** the big movers are not the box rule or the hook rule but the two disagreement kinds (`disagree_narrowed` narrows a note the CV rows decided; `stroke_candidate` raises `possible`). Together ~236 / 191 heads become narrowed; that is where the 130 held-out
  notes come from. Whether those narrowings are right is the tiles' question (tiles 1, 4, 10, 11 are decided-on-main-now-narrowed; 2, 5, 6 are candidates). Not landed, no default touched.

# 2.205 -- step 5, moved forward: ONE OWNER PER STROKE (flag `OMR_STROKE_OWNER`, OFF; needs `OMR_STROKE_MAP` in the gather)

Path: STAGED ADJUDICATE. Branch `lane-2.205-stroke-owner`, cut from `lane-2.204-stems-from-strokes` (2.198 + 2.202 + 2.204), main `b4a6c573d` merged. Code, unit tests and
read-only record replays only: NO gather and NO lane_report was run (2.204 was gathering). Every number below comes from a script in this directory run on the 2.202 milestone's
gathered ON records (`.claude/worktrees/lane-2.202/out/lane-report/2.202m/work/*.on.gathered.record.json`, frozen 8-page sample, OMR_STROKE_MAP on), which hold the strokes, the boxes'
`Q.GLYPH_STROKES` and main's own precision verdicts. My look is not evidence (rule 7); no crop or tile was made.

## Cause (rule 3) and what it teaches
**The stroke map measured every piece of ink, and the first two consumers read it before anything said whose it was.** `multi_claim_census.py`: of 47,780 (Litolff) / 65,084 (Brahms)
strokes, 5,167 / 10,842 lie under two or more detector boxes, 1,908 (4.0%) / 5,878 (9.0%) under boxes of two or more FAMILIES, 1,380 / 3,568 under two or more CLAIMANT families
(consumers -- beam, flag, stem boxes -- left out). The pairs that dominate: arc|beam 312 / 1,300, arc|head 198 / 796, head|ledger 201 / --, accidental|arc -- / 481, arc|rest -- / 447,
flag|head 58 / 421, dynamic|head 148 / --, head|rest 127 / 139, accidental|rest 55 / 319, arc|flag -- / 263 (top 12 per plate in `results/2.205/multi_claim.json`).
**What that means to the consumers**: of the strokes 2.202's rule gives a beam role, a CLAIMANT's box covers 369 of 1,172 (31%) / 363 of 659 (55%) `beam` strokes (head 220 / 217,
clef 74 / 90), 317 of 399 / 1,031 of 1,082 `beam_stub` (head 267 / 864), 2,086 of 2,563 (81%) / 2,379 of 2,866 (83%) `hook` (dynamic 953, head 416, rest 321 / rest 814,
accidental 618, dynamic 410) and 452 of 611 / 789 of 1,154 `hook_or_stub` (ledger 178 / 556). And 1,508 of the 4,795 / 712 of the 4,568 strokes that coincide with a finder `Q.STEM`
are under some claimant's box (mostly the head they stand beside). The 31% / 55% are, to the stroke, the plan's "CV and detector disagree about beams in 31% / 55% of cells".
**Process lesson.** A role (`beam`, `hook`, `stem`) is a shape rule, and a shape rule fires on any dark stroke of that shape. We built two shape readers (steps 3 and 4) on a
map whose strokes had no owner, and measured their cut-offs on strokes that were often a head's, a letter's or a rest's. The plan put ownership at step 5 because it is the
hardest, not because it comes later in dependency; the order of building should follow the order of reading (who owns it, then what it is).

## The design, in plain words
Once per cell, every stroke gets one owner (`stroke_owner.py`, pure; `adjudicators/stroke_owner.py`, one verdict per CELL -- a stroke is a measurement, not a subject, 2.198).
The claimants, in convention order: the register's AREA claims (clef, key signature, meter, header column -- nothing else is printed there), then noteheads and ledger lines,
accidentals, arcs and hairpins, dynamics / text / articulations / dots, rests. Stems, beams and flags are never claimants: they read what is left. A box claims the strokes
with >= half their ink inside it (`Q.GLYPH_STROKES`). Per stroke: no claimant -> unclaimed; an area -> its owner; one family whose SHAPE fits -> decided (two boxes of that
family -> merged, which box is 2.186's question); claimants none of whose shapes fit -> the claims are refused and the stroke stays the consumers'; two families that both fit ->
the stroke's own shape decides only if it CLEARLY fits one, else CONTESTED (abstained, candidates kept in claim order, counted, no consumer may use it). Never a confidence pick.
The shapes are convention sizes on the stroke's fields (`shape_fit`, the fields named in every `why`); two were MEASURED and corrected before they spoke
(`owner_shape_sizes.py`, the strokes under boxes main KEPT): a whole / half rest block is 0.76 sp tall at the median, 0.88 at p95, on both plates (the convention's 0.75 refused
455 / 170 real rests) and a filled head 1.24-1.32, so the cut is 1.0; quarter / eighth rest verticals reach 3.44 sp (Litolff p95), so the rest length cut is 2.71's measured 3.8.
Where the order acts: areas first, consumers last, and a REST may not own a stroke that touches a stroke a HEAD (an earlier tier) already owns (2.150b, 2.33c: a rest never
touches a note). A stroke only partly in a box joins that mark when it touches two strokes the mark owns and its shape fits (a sharp's crossbar that runs into the note's stem).
The consumers MASK owned and contested strokes (kind `owned` / `contested`): the ink is still there, so a tip with a slur on it is never read as a clean tip (rule 8), but it is
never a beam, a hook, a stub or a stem. 2.202's and 2.204's rules are otherwise untouched (the filter is in `rhythm._stroke_views` / `_stem_views` only).
EXPORT: `report["stroke_ownership"]` (strokes by state, owner family, boxes owning none of their ink; a partition with `unaccounted` = 0), present only when the decision ran.
OFF: the decision files nothing (`adjudicate.run` skips it), the views read no verdict, the report gains no key.

Three faults the record replay found in my first draft (each now a test): a box's PARTIAL strokes counted as evidence against it (127 / 343 heads main kept "owned nothing"
because a neighbouring ledger rung was another's); real chord heads beside their stem read as tremolo slashes (56 / 204 strokes; a slash is a line, length / thickness >= 2.5,
crossed in its middle); and the attach step had no shape test, so a stem touching both halves of an erase-split head went to the head (647 / 143 finder stems).

## What ownership does, measured without a gather
- **States** (`multi_claim.json`): Litolff decided 20,239, merged 5,187, unclaimed 18,293, refused claims 3,615, **contested 446 (0.9%)**; Brahms 31,118 / 7,380 / 22,240 / 3,678 /
  **668 (1.0%)**. Contested by pair: Litolff mark|rest 69, head|ledger 56, accidental|mark 31, head|rest 24; Brahms **accidental|rest 190** (2.192's eighth-rest bulb boxed as an
  accidental), accidental|arc 79, accidental|mark 57, arc|clef 36.
- **Finder stems that ownership gives to a mark** (the risk to 2.204): 247 of 4,795 (5.2%) / 246 of 4,568 (5.4%). Of them the header claims (key signature, clef, meter,
  header column) are 89 / 43 and right by convention; **accidental 44 / 150 and dynamic 112 / 46 are the ones to tile** (an accidental's or a letter's own vertical the finder
  took for a stem, or a real stem under a letter / accidental box: cannot tell from here).
- **The 2.202 heads** (`owner_on_2202_heads.py`; 2.202's own tip count re-taken with the mask; the box-support half is not replayed, so this predicts, it does not measure):
  `stroke_candidate` (the map counted MORE levels) resolved 44 of 179 Litolff / **97 of 112 Brahms**, stem stroke owned 7 / 3; `disagree_narrowed` (FEWER: the erase-thinned
  beams) unchanged 57 / 78 -- ownership only takes strokes away, so this is 2.202b's, as expected; hook heads 1 of 2 no longer a flag.
  **The 9 judged 2.202 tiles**: tile 2 (the sharp's crossbar) -> the accidental's, resolved; tile 5 (the head cluster) and tile 6 (head + ledger) -> the head's, resolved;
  tile 12 (slur start) -> the arc's, no longer a flag; tile 8 (slur start) STILL a flag -- that slur has no detector box, and a stroke map never names a mark nobody boxed
  (rule 6); tiles 1, 4, 10, 11 (beams thinned by the erase) unchanged -- 2.202b. So 4 of the 9 move toward Sean's answer, 0 move away; the milestone must show it.
  Litolff's 128 unchanged `stroke_candidate` heads: the head-end piece is not >= half inside any claimant's box (Litolff merges); not chased here.

## Parity with the old pair rules (plan section 3; the record's own verdicts against `box_verdict`; Litolff / Brahms)
Every head / rest / accidental box an old pair rule refused, and what ownership says about it (refused = owns none of its ink; contested = narrowed; merged = same family,
2.186's; owns = owns some of its ink; no_ink = covers no stroke it does not stand beside):
| rule | n | refused + contested | merged | owns | no_ink |
|---|---|---|---|---|---|
| rest_has_a_stem | 58 / 13 | **54 / 11** | 0 / 0 | 2 / 1 | 2 / 1 |
| rest_stroke_into_a_head | 29 / 41 | 15 / 24 | 1 / 0 | 10 / 11 | 3 / 6 |
| rest_is_a_barline | 31 / 19 | 10 / 3 | 1 / 0 | 2 / 0 | 18 / 16 |
| is_a_rest_twin | 12 / 21 | 6 / 14 | 4 / 1 | 2 / 6 | 0 / 0 |
| is_a_beam_piece | 13 / 3 | 11 / 2 | 0 / 0 | 2 / 1 | 0 / 0 |
| on_a_rest (head and accidental) | 11 / 63 | 1 / 5 | 0 / 2 | 10 / 56 | 0 / 0 |
| rest_is_a_duplicate_box, different class | 0 / 8 | 0 / 1 | 0 / 4 | 0 / 3 | 0 / 0 |
| head_cut_piece | 10 / 7 | 0 / 0 | 7 / 0 | 3 / 7 | 0 / 0 |
| tremolo_slash_crosses_stem (+ rest_is_a_slashed_stem) | 42 / 47 | 0 / 1 | 8 / 10 | 34 / 36 | 0 / 0 |
**Parity is NOT reached: 97 of 206 (47%) / 61 of 222 (27%).** Strong for the rest-vs-stem rules and the beam piece; the named differences: (1) `rest_is_a_barline` is mostly
`no_ink` -- the barline's stroke is longer than the thin rest box, so under half of it lies inside and the box covers nothing (a box-coverage limit, not a shape one);
(2) `tremolo_slash_crosses_stem` and `head_cut_piece` boxes own a head-shaped piece of their own (the slash is cut by the stem into head-sized halves; a cut piece is the same
family -- 2.186's); (3) `on_a_rest` is mostly 2.192's ACCIDENTAL on an eighth-rest bulb where no rest box covers the bulb, so nothing contests it. So the old rules are NOT
deleted or bypassed: the box verdicts are on the record (`detail.boxes`) and no precision decision reads them. Deleting a rule waits for its row to reach parity and for Sean.
**Boxes ownership refuses that main KEPT** (what switching the precision rules over would change; NOT acted on): Litolff heads 42 refused + 43 contested, rests 4 + 39;
Brahms heads 45 + 30, rests 13 + 79. These, and the contested strokes, are the tile population.

## Tests (`tools/omr/tests/test_stroke_owner_2_205.py`, 36, constructed cells; every RED has a twin that must not fire)
Pure: a sharp's crossbar at a stem tip is the sharp's (attached by the two stems it ties; twins: no sharp -> unclaimed; touching one owned stroke -> not attached); a stem
touching both halves of an erase-split head stays unclaimed; head + ledger fused piece -> the head (twins: a thin rung -> the ledger; a long thick beam -> nobody's); a slur's
start at a stem -> the arc's (twin: an arc box never owns a blob or a beam it passes); an eighth-rest bulb under an accidental box and a rest box -> CONTESTED, counted, claim
order kept (twins: one claimant decides; two boxes of one family merge); the census partitions every stroke; the pair rules as ownership (rest stroke into a head, block rest on
a stem, block rest on a head's blob, a barline under a rest box, a tremolo slash; twins: a quarter rest's own stroke, a real whole-rest block, a head beside its stem, a head at
the block height -> contested); an area claim owns whatever stands in it. Through `adjudicate.run`: OFF files no verdict and the duration equals flag-unset; the flag is an
allow-list; with 2.202 ON the sharp's crossbar is a tip beam OFF and the sharp's ON; a slur start is a 2-hook flag OFF and not ON, while real hooks with no claimant stay a
flag; a real beamed pair reads as OFF; a contested beam stroke narrows; with 2.204 ON a quarter-rest box on a stem that runs into a head leaves the stem to the stem reader
(direction `up`) and the head box owns its blob. **Controls that fail**: the claim order broken (rests before heads) -> the rest takes the stem and the direction is lost; the
consumer mask switched off -> the sharp's crossbar is a beam level again. Export: the tally partitions with `unaccounted` 0 and is absent OFF.
Also run (serially): 2.202's and 2.204's test files, `test_stroke_map_2_195`, `test_glyph_strokes_2_198`, `test_staged_adjudicate`, `test_staged_check`, `test_staged_inventory`,
`test_staged_reach`, `test_staged_wiring`, `test_flag_docs_match_predicates`: all pass. The full fast tier was NOT run (the box was busy).

## MILESTONE PLAN (to run on a quiet box; NOT run now)
Prerequisite: `lane-2.205-stroke-owner` with origin/main merged again (and 2.202b's fixes when they land, re-merged); one lane on the box. **Subset first (Sean 2026-10-25: "Don't
take too long testing if we can rule out issues quickly")**: every command below runs FIRST with `LANE_REPORT_SAMPLE=benchmarks/shared-ink-map-2026-10/results/2.205/sample_2pages.json`
(2 pages per plate: Litolff 8, 16; Brahms 0, 14 -- the pages holding the judged 2.202 tiles 1, 2, 4, 5, 6, 10, so the right->wrong control can fire). If notes not written jump,
or any judged answer goes right -> wrong, stop and find the cause on those pages; only a clean subset earns the full frozen sample (unset the variable).
```
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/lane-2.205-stroke-owner
# (a) ownership alone: the stroke map in both arms, OMR_STROKE_OWNER off -> on. Expected: NOTHING CHANGED in the file (no consumer reads it); the report's
#     stroke_ownership tally per plate (contested count) is the measure.
python3 -m tools.omr.staged.lane_report --flag OMR_STROKE_MAP=1:1 --flag OMR_STROKE_OWNER --from gather --workers 2 --out out/lane-report/2.205a > out/lane-report/2.205a.txt 2>&1
# (b) what ownership does to beams and stems: the three flags vs the same two without ownership (the consumers in BOTH arms)
python3 -m tools.omr.staged.lane_report --flag OMR_STROKE_MAP=1:1 --flag OMR_BEAMS_FROM_STROKES=1:1 --flag OMR_STEMS_FROM_STROKES=1:1 --flag OMR_STROKE_OWNER \
    --from gather --workers 2 --out out/lane-report/2.205b > out/lane-report/2.205b.txt 2>&1
```
`--from gather` because the flags it stacks on are named in `gather.py`; the ownership flag itself acts in ADJUDICATE, so (b)'s two arms differ by one ADJUDICATE flag on one gather
each. Then, from the ON records and one extra pass (no gather): `multi_claim_census.py out/lane-report/2.205b <out.json>` (states, contested pairs, finder stems owned, parity)
and `owner_on_2202_heads.py` re-pointed at 2.205b's own ON arm for the settled counts with the full 2.202 path.
**The 12 tiles** (blind, nothing of ours drawn, neutral orange box, key apart): from (b)'s changes -- 3 heads whose beam reading changed because a stroke became owned, 2 heads
whose stem changed (one accidental- or dynamic-owned finder stem among them: the 5% risk above), 3 CONTESTED strokes (question: "what is this ink: which mark, or two?",
Brahms accidental|rest first), 1 box ownership refuses that main kept; and the 2.202 tiles RE-SHOWN with their new outcome -- 2, 5, 6, 12 (predicted to move to Sean's answer)
and one of 1 / 4 / 10 (predicted unchanged, the erase-thinned beam: a control). Judged right -> wrong must be 0.
**No colour question at the milestone: already ruled** (DECISIONS 2026-10-22, Sean: "the color should just be applied at output. Everything else before that is intended to help determine what it is"). A contested stroke (446 / 668 on the sample) ABSTAINS in ADJUDICATE with both candidates kept, as built; INFER may choose among them, labelled; EXPORT alone colours the result. The milestone asks Sean only the tiles' own question ("what is this ink: which mark, or two?").

## MILESTONE RESULT (2.205; main merged `a21aab575`; fast tier 9,061 passed, 0 failed; `results/2.205/`, `out/print/2.205-stroke-owner/`)
**Subsets first** (Sean 2026-10-25). (a) ownership alone, Litolff 8, 16 / Brahms 0, 14: NOTHING CHANGED in the file, right -> wrong 0 (117 / 196 judged tiles);
759 / 360 cells carry a `stroke_owner` verdict, contested 138 / 108 strokes. (b) ownership with beams + stems in both arms: notes not written 620 -> 613 / 604 -> 597,
red bars 34 -> 33 (Brahms), right -> wrong 0.
**First full (b) run: ONE right -> wrong**, Litolff p10 (2.154 tile 7, Sean: eighth; ON wrote a quarter). **Cause**: the note's flag hook (stroke 19, on its own stem 22) lay
in detector boxes classed `dynamicF` (the detector named a Litolff flag as a forte letter, as it does other ink in that cell), so the letter tier owned the hook before the flag
reader could read it. **Lesson**: a letter box has the same failure as a rest box on a stem -- the detector's CLASS is a guess, so its claim needs a structural test, not only a
shape one. **Fix** (`shape_fit`, `touches_a_note`; CONVENTION ASSUMED: a dynamic letter is printed clear of the notes): a letter never owns a stroke that touches a head's
stroke or a stem touching one -- the claim order acting (heads before letters), with a control that breaks the order and gives the flag back to the letter. Re-run on a subset
holding p10 (Litolff 8, 10, 16 / Brahms 0, 14): right -> wrong 0 (138 / 196), notes not written 944 -> 934 / 604 -> 597.
**Full frozen sample, (b), after the fix** (`out/lane-report/2.205b.txt`): the consumers in both arms, ownership OFF vs ON.
- Litolff: notes +35 -13, accidentals +9 -1, flags +7 -8 ~1, beams +14 -7 ~7, ties +2, slurs +8, values ~2, pitches ~1, blue marks +12 -1; red bars 0 -> 0;
  **notes not written 2,801 -> 2,779**; judged right -> wrong **0** (233 tiles).
- Brahms: notes +29 -10, rests +1, accidentals +12 -2, dots +17 -4, flags +6 -9, beams +7 ~1, ties +6 -2, slurs +8 -2, articulations +9 -2, values ~3, blue marks
  +15 -35; **red bars 173 -> 171**; **notes not written 3,363 -> 3,343**; judged right -> wrong **0** (232 tiles).
- Words +3 -6 / +8 -21: NOT gather noise -- run (a) re-gathers both arms too and its words did not move. They follow the notes: a written word is placed on a note, and (b) writes / drops notes; not chased further (no judged answer moved).
- **Run (a), ownership alone, full sample** (`out/lane-report/2.205a.txt`): NOTHING CHANGED in the exported file on either plate (notes not written 2,563 / 3,202, red bars 0 / 166 both arms), judged right -> wrong 0 (233 / 232) -- OFF-vs-ON of the decision itself changes no output, as designed.
- Ownership on the full sample (`multi_claim_2205b.json`): contested 399 / 655 strokes; Brahms accidental|rest 190 (2.192's bulb).
**The 2.204 stem `disagree` abstentions** (`stem_disagree_owner.py`, both arms stems ON): Litolff 178 OFF (the coordinator's 167, main merged) -> ownership removes **23**
(13 agree, 8 map silent, 1 old refused, 1 cannot tell) and adds 7: 178 -> 162; Brahms 96 -> 5 removed, 6 added. **Ownership does not remove them**, and should not be
expected to: their reasons are 2.204's own rules on strokes no mark owns -- `finder_stem_but_wrong_side` 76 / 59, `finder_stem_is_not_a_stroke_beside_the_head` 56 / 32,
`finder_stem_but_barline` 46 / 5. The crop check's causes (fused heads, chord stems over 8 sp called barlines -- Sean 2026-10-26: a long stem through stacked heads is
a chord stem, never a barline --, neighbours' stems) are 2.204's side and length rules; they are 2.204's to fix. Ownership's part (Sean 2026-10-26): no head may claim a
shared chord stem -- it never does (a head never owns a vertical stroke; `TestAStemSharedByAChord`: a three-note chord and a second with heads on both sides, pure and
through the pipeline).
**The 12 tiles** (`out/print/2.205-stroke-owner/tiles/sheet.png`; key `out/print/2.205-stroke-owner/key.json`; question per tile: "what is the boxed ink -- a note
(which value, flag or beam on its stem), a rest, or something else?"): 3 beam readings ownership changed (tiles 4, 5 narrowed -> decided; 11 abstained -> decided eighth),
2 stem readings (7, 12: 2.204 `disagree` -> agrees, now decided), 2 contested strokes (1 head|rest, 9 accidental|rest), 1 head box ownership contests that main kept (6),
and the 2.202 tiles re-shown: 2 (sharp's crossbar), 6 (head + ledger), 12 (slur start) -- predicted to move to Sean's answer -- and 1 (erase-thinned beam: the control,
predicted unchanged). Not answered yet.

## 2.205 TILES ANSWERED (Sean 2026-10-26; `out/print/2.205-stroke-owner/answers.json`)
**Score (ON, the 8 notes ownership wrote or moved): 7 right, 1 wrong.** Right: 2 quarter, 3 dotted quarter, 4 dotted quarter, 7 eighth (Sean first said quarter, then
corrected it to eighth), 8 dotted quarter (OFF wrote a dotted eighth, the 2.202 hook-as-flag; ON a dotted quarter), 11 eighth, 12 half. Tiles 2 and 3 were not written OFF.
Tiles 1, 6, 9 (contested strokes; run (a) changes no file) are eighth rests, tile 10 (control) an eighth, unchanged. Judged right -> wrong stays 0.
**The one wrong decision: tile 5** (Litolff p4, `glyph/4/0/8/0/5`): ink Sean reads as part of a C clef, written as a blue quarter.
**Cause (measured on the saved record).** (1) The detector drew `noteheadBlackOnLine` (conf 0.44) on the clef's body, plus a `tie` box beside it (`.../4`). (2) Nothing
claims that ink: the staff's clef is DECIDED `alto` only by `clef_from_other_systems` -- no `clef_located` row exists for staff 8 -- so there is no clef area claim there. The
only leading-column claim runs x 316-372.6 (barline/brace), the key claim starts at 427.5, and the head box sits at 385.8-417.8, in the unclaimed gap that is the clef.
(3) The note reader treats the box as a head (`notehead_is_not_a_notehead` decided False on the class alone; the fill check says `not_head_sized`, and a stem was borrowed from
a neighbour: `wrong_side`). (4) OFF the duration was NARROWED {quarter, eighth} because YOLO drew 2 beam boxes; the stroke map saw no beam stroke over it ("agrees", 0 beams) and
the bar rule took the lone remaining value. So ownership did not invent the note; it removed the doubt about a beam from a "head" that was never a head.
**Process lesson.** A clef we carry from other systems still has ink on this one; a decided value with no located ink leaves its ink unclaimed, and the detector's guess
(a head) then stands unopposed. The missing fact is the claim, not the beam. The beam answer was right (no beam); the question asked of the box was wrong.
**Source fix, not a 2.205 rule:** claim the clef's ink on a staff whose clef is carried (locate it from the leading column / other systems' clef width) so tier 0 owns it
before any head can; secondarily the detector class on clef ink (`not_head_sized` fill is already a signal the head reader declines to use). Ownership is correctly ordered
here and needs no new rule; the clef claim is a GATHER fix to be rostered, not built in 2.205.
**Tile 7 correction:** Sean's first answer (quarter) was corrected to eighth; ON's eighth is right, so no cause hunt was needed.

## 2.208 THE CLEF CLAIMS ITS OWN INK ON EVERY STAFF (STAGED GATHER; flag `OMR_CLEF_SLOT_CLAIM`, OFF; branch `lane-2.208-clef-claim`)
**Cause.** `gather_claimed_register` files a clef claim only from a located clef (cell-0 frame, or a header read that overrode a head) or a clef-sized detector box. A staff with neither
(clef DECIDED later, in EVALUATE, by carry from other systems) files no clef claim: the header column stops at the system's clef offset, the key claim starts later, and the clef's ink in
between is claimed by nobody. **Lesson:** a decided value with no located ink leaves its ink unclaimed; the detector's guess then stands unopposed. A second layer: the line finder (cv_lines)
drew a "stem" on the clef's own curl, and the consult treats any touching stem as proof of a note, so the claim alone refused nothing (Litolff p4 s8: stem centre inside the slot).
**Count (20261022-night records, frozen sample pages, `count_clef_gap_2_208.py`).** Staves with no cell-0 clef claim: Litolff 9 of 172 (2 had a header-window locator row), Brahms 1 of 199.
Detector boxes in that slot: Litolff 8 (7 noteheadBlackOnLine, 1 ledgerLine), Brahms 1. Crop check (10 staves, one sheet): every one shows a clef (alto 5, bass 2, treble 2, plus one) and every box sits on clef ink.
**Fix.** `gather_clef_slot_claim` (after the key object): per such staff one `clef` area claim, READ, `source: clef_slot`, from the system's clef offset to the key claim (cap: widest sibling clef + 0.75 sp), plus the 2.198 ink claim.
`claimed_by._stemmed`: for slot claims only, a stem whose centre stands in the slot is the clef's ink. CONVENTION ASSUMED: a system opens with a clef on every staff / FALSIFIED BY a print-confirmed note in the slot / NOT CONFIRMED beyond two plates.
**Measures (main with 2.205 ON; `out/print/2.208/`).** (1) Exported file, frozen sample, OFF vs ON: Litolff notes -3, blue marks -3, words +1; Brahms notes -1, words -1 (a "does not add up" note gone), red bars 166 -> 165. 10 slot claims; 7 heads refused by them (4 had been written).
One head still a note: Litolff p6 s0 (`glyph/6/1/0/0/10`), touched by a key flat's stem outside the slot. (2) 12 blind tiles `out/print/2.208/tiles/sheet.png` (8 on clef ink: 4 changed, 3 refused-but-never-written, 1 still a note; 4 controls = first real notes after the clef); key `out/print/2.208/key.json`. Not answered yet.
(3) Judged answers right->wrong: 0 on both plates (233 / 232 tiles). Subset (2 pages per plate) was clean first. Tests: `test_staged_clef_slot_claim_2_208.py` (11, mutation of the stem rule fails the stem test).

## 5b. CAUSE OF THE 9 CHANGED HEADS (2.202 milestone; read-only, no gather, no code change; branch `cause-2.202`; my look at 600 dpi, not Sean's -- rule 7)
Cause first: **the stroke map measures ink BEFORE any mark owns it, and the beam rules are shape rules.** Every one of the 9 changed heads (all main-right) is a beam rule applied to ink that is not
that stem's beam: a real beam the erased raster thinned (4), the ink of a head / accidental at the far end of a short stem (3), a slur's thin start (2). Process lesson: a `beam` / `hook` role
is "horizontal, across >= 2 verticals, thick" -- a description of ANY dark stroke -- and the lane wired it before the ink was claimed (step 4 of the plan) and before the 0.5 cut was measured on
the second plate (section 1 said "Brahms must be measured before any default"; the first Brahms data was the tiles). Tools: `beams_cause.py` (all narrowed heads, streams the two gathered ON records, 22 s),
`beam_thickness.py`, `erased_cell.py`; crops `out/print/2.202-cause/` (`sheet_tiles_{0,1,2}.png` the 9, `sheet_sample_{0..6}.png` 20 `disagree_narrowed`, `sheet_sc_{0..6}.png` 20 `stroke_candidate`; left = plain print, right =
strokes boxed: green beam, cyan beam_stub, blue span_thin, red hook, orange hook_or_stub, grey other; magenta = detector beam/flag box; black = the head's stem stroke; `erased_t04.png` = what the map reads).

**The 9 (record rows from the ON gathered record; Q.STROKE fields in sp):**
| tile | plate p | settled | the stroke that decided it | what it really is on the print |
|---|---|---|---|---|
| 1 | Litolff 8 | disagree_narrowed [1]->[0,1] | beam, 4.7 long, **0.187 thick**, `span_thin`; tip counts 0 | the eighth beam lying ON the top staff line; page ink there is 0.7 sp thick |
| 4 | Litolff 16 | same | beam, 6.0 long, **0.187**, `span_thin` | the same, on the 2nd line (page ink 0.57-0.7 sp) |
| 10 | Litolff 8 | same | beam, 3.6 long, **0.187**, `span_thin` | the same as tile 1, one cell left |
| 11 | Brahms 12 | same | beam, 5.0 long, **0.497** (cut 0.5), `span_thin` | a sloped beam (-6 deg) whose low end touches the bottom line; page ink 0.5-0.69 sp |
| 2 | Brahms 14 | stroke_candidate [0]->[0,1] | `beam` 3.1 long, 0.52 thick, 21.9 deg, touches the sharp's two verticals AND the stem, centre 3.6 sp inward on a 4.0 sp stem | the CROSSBAR OF THE SHARP beside the head |
| 5 | Brahms 14 | stroke_candidate [1]->[1,2] | `beam` 2.6 long, **1.16 thick**, sagitta 0.47, 62 deg, centre 3.8 sp inward (counted with the real beam, 0.62) | the cluster of heads at the stem's far end (two levels counted where the print has one) |
| 6 | Brahms 0 | stroke_candidate [0]->[0,1] | `beam` 1.9 long, 0.81 thick, touches the stem and the chord's upper stem, 3.5 sp inward on a 4.9 sp stem | the notehead merged with its ledger line / staff line (the head itself) |
| 8 | Brahms 19 | hook_as_flag [0]->[1] | `hook`: flat, 1.06 long, **0.06 thick**, touches the stem (0.25 contact) AND a blob (0.5) that continues | the thin START OF A SLUR that begins at the stem tip (the detector boxed it as a `beam`) |
| 12 | Brahms 4 | hook_as_flag [0]->[1] | `hook`: curve, 1.58 long, 0.24 thick, touches the stem (0.31) AND a 3.8 sp stroke (0.56) | the start of a slur at the stem tip (same) |

**Causes, with the cut each one breaks:**
1. **A beam the staff-line erase thinned (tiles 1, 4, 10; 11 as its near-miss) -- 4 of 9.** The map reads `image_no_staff`; where the beam lies on a line the erase takes more than the line's 0.12 sp and leaves a sliver on one side:
   `erased_t04.png` shows the beam solid between two stems and a thin remnant at both ends; the stroke's median run is 0.187 sp where the page (the binary, line included) has 0.57-0.7. Breaks: `BEAM_MIN_THICKNESS_SP` 0.5, applied
   to a thickness taken after the erase. The cut is not a gap on the whole sample either (`results/2.202/beam_thickness_*.json`, horizontal strokes across >= 2 stems under detector beam boxes): thickness 0.3-0.5 is 21 of 372 (Litolff) and 44 of 269
   (Brahms) of them, 0.6-0.7 the mode of beams; section 1's gap (0.437 | 0.546) was two pages. Tile 11 is the 0.003 knife edge (a pixel count / space).
2. **Ink of another mark at the far end of the stem counted as a beam (tiles 2, 5, 6) -- 3 of 9.** Breaks the tip window: 0.5 sp past the tip, 3.3 sp inward, tested by the stroke's BOX overlapping the window, so on any stem shorter
   than ~4.5 sp the window reaches the head end, where a notehead cluster, a ledger line, a sharp's bar or a dynamic letter is "horizontal, wider than tall, >= 0.5 thick, touching this stem and one more vertical": role `beam`. Nothing in
   `role_of` knows the stroke is a head's. This is the cause of the milestone's "+levels" (`stroke_candidate`) heads.
3. **A slur's thin start read as a flag hook (tiles 8, 12) -- 2 of 9.** Breaks "one stem, thinner than a beam, <= 1.6 sp, on a stem with no spanning beam": all three are true of a slur that starts at the tip. What a flag hook is NOT: its far end is
   free. Both hooks touch a second, non-stem stroke (blob 41, stroke 17 of 3.8 sp) in the same connected component; the stem tip carries a slur / tie / arc box the detector may call a `beam` (tile 8).

**Does it explain the ~130 / ~110 held-out notes?** Yes. All 236 (Litolff) / 191 (Brahms; +2 hook heads) narrowed heads, classified by script (`beams_cause.py`, cause = the measured stroke at the tip; script vs my hand label agree on 48 of the 49 inspected heads; the one miss is tile 8, whose slur carries no slur box so the script says hook_other):
| cause (settled kind) | Litolff | Brahms |
|---|---|---|
| head-end ink counted as a beam (`stroke_candidate`) | 156 | 102 |
| tip counts a stroke 0-1.5 sp from the tip only (`stroke_candidate`, "at_tip") | 23 | 10 |
| beam thinned by the erase, < 0.30 sp (`disagree_narrowed`) | 22 | 33 |
| beam 0.30-0.50 sp (`disagree_narrowed`) | 21 | 25 |
| two levels fused in one slab >= 1.0 sp, counted once (`disagree_narrowed`) | 0 | 15 |
| the beam stroke does not touch this stem (stem short of the beam or beam starts at the stem's edge) | 8 | 3 |
| no stroke / other | 6 | 6 |
| hook = slur origin (script: 1 by slur box, 1 `hook_other` = tile 8 by hand) | 0 | 2 |
Causes 1+2 are 199 of 236 (84%) and 160 of 191 (84%); with the fused slab 92% on Brahms. The held-out notes (2694-2563 = 131, 3311-3202 = 109) are the bars the narrowed heads leave unsettled, so they follow these causes, not a different one.
Crop look, 20 `disagree_narrowed` (Litolff 10, Brahms 10, seeded random, not the tile heads): thinned or thin beam 14 (6 on a line < 0.3, 8 at 0.37-0.50), fused double slab 4 (Brahms 5/0/1/7/1, 5/0/3/5/4, 19/0/12/0/10 and /13), beam not touching the stem 2
(Litolff 10/1/8/6/10, 9/0/2/0/4). 20 `stroke_candidate` (same): 18 head-end ink (heads, a head row, a ledger line, a dynamic `f`), **2 real**: Litolff 10/0/9/10/3 (a beam on a staff line the readers never found -- OFF says quarter;
the map is right) and Brahms 4/1/13/4/6 (a true second beam over the stem). So the map also sees things main misses; the 23 / 10 `at_tip` heads are where those live (2 of 2 inspected real) and must NOT be thrown away with the rest.

**What each cause points to (nothing built; each needs the tiles again, rule 5):**
1. Measure a beam's thickness where the map's own raster is not the eraser's: for a stroke whose centre is within ~0.4 sp of a staff line take the run on `binary` (line included) or add the erased band back; and re-measure the 0.5 cut on BOTH plates'
   strokes under detector beam boxes before it is a number (CLAUDE §4, a cut measured on one plate only NARROWS).
2. Count a stroke at the tip only where its CONTACT with the stem lies in the window (not its box), and let a head / accidental / dynamic / ledger own its ink first: a stroke whose box is >= 30% inside a notehead, accidental or dynamic box is not a candidate
   beam. This is plan step 4 (claiming) arriving as a precondition of step 3, not after it.
3. A hook is a flag only when it is a FREE END (touches only this stem) and lies in no detector slur / tie / system-arc box (`_not_a_decided_arc` is the existing test for the CV beam path); an arc that starts at the stem tip is read by the arc readers.
4. A slab thicker than ~1.0 sp across >= 2 stems is two levels (`_fused_double_beams` already says so for the CV path); a beam stroke that comes within ~0.5 sp of the stem's end joins it (2 of 20).

## 5c. 2.202b: the three measurement faults of 5b (branch `lane-2.202b-beam-faults`; code + unit tests + read-only re-measure on the 2.202 records, NO gather, NO lane_report; nothing defaulted, nothing landed)
Path: STAGED GATHER (`stroke_map.py`, flag `OMR_STROKE_MAP`) + STAGED ADJUDICATE (`beam_strokes.py`, flag `OMR_BEAMS_FROM_STROKES`); both OFF. Fenced edits: `stroke_map._restored_thickness` (+ one call in `map_strokes`), `beam_strokes.tip_reading` / `local_thickness` /
`StrokeView.profile`, and ONE line in `rhythm._stroke_views` (it now passes the row's `profile_sixteenths` into the view; nothing else in `rhythm.py` moved -- 2.205 merges around it).
Scripts: `beam_faults_live.py` (re-run the map on the 8 + 8 sample pages without a gather, old vs new thickness), `beam_faults_thickness.py` (the distribution under detector beam boxes), `beam_faults_records.py` (`--settle`: re-run `tip_reading` on every duration head of the two ON records
with the old / new code, against main's level count `before`); results `results/2.202b/`. Tests `test_stroke_thickness_2_202b.py` (7), `test_beam_faults_2_202b.py` (18); with the 2.195 / 2.198 / 2.202 files 88 pass.

**Cause first (rule 3): the 0.19 sp beam is the staff-line ERASER's bug, not the map's.** `staff_line_removal.remove_staff_lines_from_cell` walks the vertical run through a line row only `cap + 2` = 37 rows either side (`_vertical_runs_through`, "bounded at max_search")
and erases the run when it is <= `crossing_cut` (0.45 sp = 45 rows). A beam 0.64 sp thick HANGING from a line has the line row near the top of its run: the walk goes 6 up and 37 down = 44 <= 45, so the band 705..748 is erased and rows 749..768 (the 0.19 sp sliver) are
left. I re-cut the cell of the p16 tile (`glyph/16/0/1/8/3`, sp 100 px; line thickness measured by the eraser 32 px = 0.32 sp: Litolff's lines are fat): raw run 705..768 = 0.64 sp, erased raster 749..768 = 0.19 sp, the walk 44 rows. So any ink taller than the cut whose edge
is at a line is cut back by up to 0.37 sp below / above that line, for EVERY reader of `image_no_staff`, not only the stroke map. **Process lesson:** a "bounded walk compared with an unbounded cut" erases what it was built to protect (the in-file comment says a beam must never be erased);
the 2.202 cause (5b: "the erase takes more than the line") was right and the mechanism is one line. NOT fixed here (shared reader, outside the fence, it moves every CV consumer and the legacy path); the candidate is `reach >= ceil(crossing_cut) + 1`, needing its own byte-for-byte read of all consumers -- Sean's call to open it as a roadmap item.

### Fault 1 -- beam thickness read off the erased raster (`stroke_map._restored_thickness`, constant `THICKNESS_FROM_UNERASED`, default True inside the OFF flag group)
For a horizontal / curve stroke, the stroke's own pixels grown, per column, through CONTIGUOUS pixels the eraser removed (`raw & ~erased`: the eraser only ever takes line rows and the run it walked with them, so no neighbour's ink comes back), at CANONICAL resolution (a first draft at the
16 px/sp reduction joined a line 0.06 sp clear of a beam). Used only where a column touches erased ink; otherwise the old reading exactly. The p16 tile stroke: 0.187 -> 0.64.
**"Subtract the line" was measured and REFUSED.** Taking the line band at the run's end off again (first draft, Litolff, reduced resolution; `results/2.202b/thickness_line_subtracted_litolff_reducedres.json`) rescued 1 of the 9 on-line strokes under beam boxes that read < 0.5 (0.64 -> 0.31 on the tile: the
printed beam covers the 0.32 sp line, it does not sit beside it); the unsubtracted reading rescued 4 and leaves the 0.45-0.55 band empty on-line. The rule cannot tell "line beside the beam" from "line inside the beam" from one column, and the measured population says inside.
**New thickness distribution** (`beam_faults_thickness.py`; horizontal strokes touching >= 2 stems under a detector BEAM box; Litolff 372, Brahms 269; on-line = centre within 0.4 sp of a staff line; counts):
| | Litolff on-line | Litolff off-line | Brahms on-line | Brahms off-line |
|---|---|---|---|---|
| OLD (2.202) < 0.5 / 0.5-0.55 / >= 0.55 | 9 / 0 / 75 | 38 / 6 / 244 | 18 / 1 / 68 | 78 / 4 / 100 |
| NEW < 0.5 / 0.5-0.55 / >= 0.55 | **5** / 0 / 80 | 37 / 4 / 247 | **12** / 1 / 74 | 75 / 2 / 105 |
28 (Litolff) and 33 (Brahms) of those strokes moved at all; 4 and 6 on-line strokes crossed the 0.5 cut. The 0.5 cut is a gap only where the line was the problem: on-line Litolff has nothing between 0.45 and 0.55 (one at 0.40-0.45, then 8 at 0.55-0.60), but off-line Litolff has 1 + 4 in 0.45-0.55 and
Brahms has 3 on-line and 4 off-line there: **the cut is not a gap on Brahms either way** (section 5b's finding stands; the 0.437 | 0.546 gap was two Litolff pages). I did not move 0.5.

### Fault 2 -- a fused double beam (`beam_strokes.tip_reading`, `FUSED_*`)
Convention: two beams stacked = beam 0.5 + gap 0.25 + beam 0.5 = 1.25 sp (the pitch of the tip window, 0.75 sp a level); a single beam is 0.5-0.7 (the on-line / off-line `>= 0.55` mode above is 0.6-0.7). A slab counts as TWO levels when ALL hold: its median thickness >= 1.0 (Sean's rule),
its thickness AT THIS STEM'S x >= 1.0 (`local_thickness`: the 12-sample `profile_sixteenths`, mean of three), < 1.75 (three fused would be 2.0: not measured, left as one), horizontal, and its outer edge within 0.6 sp of the tip. The two extra conditions are measured, not guessed: the median alone
doubled 6 Brahms heads main reads as ONE level (a group whose second beam covers only some stems: the same stroke is 0.5 sp over the first half and 1.3 over the second; the stem on the single half is 0.31-0.66 locally, the 12 stems on the double half 0.8-1.6) and a local value alone doubled 16 Litolff heads
(a 1.3 sp bump in a 0.7 sp beam where a head merges with it). With both: **Brahms 8 of the 15 `fused_double` heads now equal main (fused alone: 8 settled, 0 broke; 1 head broke in combination with the thickness fix); Litolff 0 / 0** (the other 7 have a local value of 0.81-0.96, below Sean's 1.0: they stay narrowed).

### Fault 3 -- a beam that stops short of the stem (`beam_strokes.tip_reading`, `JOIN_*`)
The gap that sets "within ~0.5 sp" is NOT measurable from the stroke geometry: the box-to-box gap of every non-touching (beam, stem) pair in a cell is flat from 0.0 to 1.5 sp (Litolff per 0.1 sp: 41 56 66 100 75 | 77 86 73 93 91 96 114 103 122 118; Brahms 14 44 31 75 66 | 41 50 38 43 41 54 62 69 64 45; `record_hists.json`).
For HEADS: the 8 + 4 `join_missing` heads have gaps 0.00-0.37 sp (median ~0.2); the unrestricted rule (any beam-role stroke within 0.5 sp counts) settled 12 heads to main and BROKE 26 Litolff + 13 Brahms heads that already agreed (18 of the 26 are a 1.0-1.3 sp slab 2.4-3.7 sp long = a head cluster at the stem's far end;
the rest thin one-stem-short strokes beside a neighbouring group's beam). So I did NOT ship the unrestricted rule. What ships is the narrower one the data allow: the stem has NO level at its tip yet, and the stroke's OUTER edge is within 0.6 sp of the tip (a first level), and it is no thicker than one beam. Measured effect (J alone, vs 2.202): Litolff +2 settled / -1 broken,
Brahms 0 / 0 -- i.e. **1 of 11 `join_missing` heads settle, and the rule is close to inert**. It is kept because it cannot hurt and says what the data support; whether to keep it at all is the lane's call. (The restriction rides on the same constant, `JOIN_MAX_GAP_SPACES` 0.5, Sean's number; the control sets it to 0 and shows the RED case turn.)

### What the fixes settle on the EXISTING 2.202 records (`beam_faults_records.py --settle`; every duration head with a stem stroke, a side and no flag levels: Litolff 2,886, Brahms 3,950; "agrees" = the tip's level count equals main's `before`; arms T = thickness, TF = + fused, TFJ = + join)
| | Litolff | Brahms |
|---|---|---|
| heads that DISagreed with main (2.202) -> agree now | **41** | **59** |
| heads that AGREED with main (2.202) -> disagree now | 10 | 8 |
| T alone / + fused / + join (settled) | 39 / 0 / 2 | 51 / 8 / 0 |
**By 5b's cause (the old code classifies; counts are heads that now equal main):** thin remnant < 0.30: Litolff 21 of 22, Brahms 30 of 33; thin 0.30-0.50: 18 of 21, 21 of 24; fused double: -, 8 of 15; join missing: 1 of 8, 0 of 3; **head-end ink (the 156 / 102 + the `at_tip` 23 / 10): 0 settle** -- that is cause 2 of 5b, the ownership lane
(2.205), outside this lane's fence by design. So of 5b's "199 / 160" heads (causes 1+2): 43 / 57 thin heads were this lane's (39 / 51 settle); 156 / 102 are 2.205's.
**The 9 milestone tiles (`out/lane-report/2.202-tiles/key.json`, its numbering; my read of the script, not Sean's tiles):** 6 of the 9 changed heads (tiles 2, 3, 5, 7, 9, 11 -- all `disagree_narrowed`, thin remnant or near-cut) now equal main's level count (1); tiles 4 and 10 (`stroke_candidate`, head-end blob) are unchanged (2 vs main 1: 2.205);
tile 12 (`other`, main 2, strokes 1) unchanged. The two hook-as-flag heads of 5b are not in this lane (cause 3, the slur-origin rule).
**The 18 broken heads** (Litolff 10 = 9 thickness + 1 join; Brahms 8 = 7 thickness + 1 fused-in-combination): of the 9 Litolff thickness ones, 6 (p2) are a real beam now read at the tip (0.12 -> 0.62) ALONGSIDE the head-end blob the 2.202 count had taken for the level (a 1.29 sp stroke 3.5-4.0 sp inward): main's 1 was
matched by the wrong stroke and is now 2 -- the blob is 2.205's; 3 (p4) are a real beam 0.25 -> 0.63 at 0.2-0.3 sp from the tip, count 2 (the second counted stroke I did not inspect). Of the 7 Brahms: 4 are a 0.36-0.47 stroke 3.4-3.9 sp INWARD of the tip now 0.57-0.73 (head-end ink, same cause); 3 (p25) are a 0.41 -> 0.57-0.61 stroke 0.1-1.3 sp from the tip where
main says 0 levels (a beam main missed, or a slur on a line: needs a crop). None of this was shown to Sean; nothing here replaces his 12 blind tiles.

**Not shown (said, not hidden):** (1) "agrees with main" is a control, not truth (rule 5/7): 6 of 9 tiles settle to the value 5b's crop look says is right (all main-right), nothing more. (2) The live re-map covers the 8 + 8 frozen sample pages; the heads are the 2.202 records' (same pages), every thickness joined by (cell, ordinal) with 0 box mismatches.
(3) No `lane_report`, so Measures 1 and 3 (the exported file; Sean's judged right->wrong) are NOT measured here -- the next step is the milestone run with these constants and the 12 blind tiles, after 2.205's ownership filter is in front of `_beams_from_strokes`. (4) The staff-line eraser's bounded walk is a finding, not a fix.
(5) The `_restored_thickness` growth costs CPU in the stroke map (not timed; only strokes touching erased ink pay it).

## 5d. 2.202c: re-measure on the landed eraser (all five eraser flags ON; main e83bd6fc9 + 63ccef6de; branch `lane-2.202c-beams-remeasure`, merged from `lane-2.202b-beam-faults`, which holds 2.202 + 5b + 5c)
Main fast tier before any change: 9,179 passed, 11 skipped, 2 xfailed, 0 failed (serial, 993 s).
**Cause first: with the eraser fixed the thinned beam is GONE (0 thin_remnant / thin_near_cut heads on Litolff p9 + Brahms p19; 5b had 43 of 236 on Litolff), as 5c's bounded-walk finding said; what is left is 5b cause 2, head-end ink counted as a level (12 of 15 narrowed Litolff p9 heads, 2 of 8 Brahms p19).** The owner mask (`OMR_STROKE_OWNER`, ON) does not claim it: the stroke is a 1.0-1.6 sp slab 3.7 sp inward on a 4-8 sp stem (the other voice's heads). Process lesson: a bug fixed at its source (eraser) removes a whole cause downstream, so a held lane is re-measured, not re-argued; and the tip window (0.5 out, 3.3 in) is a box test that cannot tell a level from anything that merely lies in it. Fix: levels are STACKED from the tip (`STACK_FILTER`; first outer edge within 1.0 sp of the tip, each next within 0.75 sp of the previous inner edge) -- 12 of 12 Litolff head-end heads settle to main's count, 0 broken (Brahms 1 of 4; `stack_resettle.py`, no gather). Unit tests `test_beam_stack_2_202c.py` (3, with the control).
**Subset (Litolff 4, 9; Brahms 14, 19; `lane_report --flag OMR_BEAMS_FROM_STROKES --from gather`, 1,426 s):** litolff notes -2 flags -1 beams -1 (notes not written 652 -> 654; before the fix Litolff p9 alone was -8); brahms notes +1 -6 flags +1 -5 dots +1 -2 beams +1 -2 ~1 (934 -> 939). Judged right->wrong 0 / 0, right->narrowed 0 / 0. Tiles `out/print/2.202c/tiles/sheet.png`, key `out/print/2.202c/key.json`.
**The 8 beam-doubt lost notes:** only Litolff `glyph/9/0/4/0/3` is in the subset: still `narrowed beam_discounted_uncertain` ON and OFF, `beams_from_strokes` never consulted -- not recovered. The other 7 (Litolff p6; Brahms p4, p5, p25) are not on these pages: full sample pending. check: 198.

## 5e. 2.202c tiles answered, and 2.202d: a clean tip refutes a box on no beam ink (branch `lane-2.202c-beams-remeasure`)
Sean's answers (`out/print/2.202c/answers.json`, 2026-10-27): 1 quarter, 3 dotted quarter, 4 quarter (ON removed a false flag: right), 7 dot (right), 8 sixteenth (right); 5 quarter and 9 dotted quarter (OFF wrong, ON not written); 6 eighth (OFF right, ON lost); 2 eighth; controls 10, 12 right, 11 wrong in both arms (an eighth written as a 16th, existing). Judged right->wrong 0.
**Cause first (one cause for 5, 6, 9, and 2): a beam box the map removes (it stands on no beam- or hook-shaped stroke) stays as a CANDIDATE level, so a head main decided as an eighth is narrowed [0, 1] (`beams_ambiguous`); a narrowed head leaves its bar unsettled, so EVERY note of the bar is held out, including heads whose own duration is decided (tile 6 `glyph/19/1/10/7/15`: decided eighth ON, lost only because its bar holds tiles 9 and 3's narrowed heads; tile 2 the same in a Litolff bar).** The map was right on all three narrowed heads (0 levels); the loss was the candidate it kept. Process lesson: removing a false value is half the job -- the lane measured what the false value did to the head, not what the removal did to the BAR; a "narrowed" verdict is not free, it costs the bar its notes (counted, not hidden, but written nowhere).
**Fix (`adjudicate_duration`, inside `OMR_BEAMS_FROM_STROKES`, settled word `clean_tip`; `beam_strokes.tip_clean`):** every removed box stands on NO beam/hook-shaped stroke AND the stem's tip is clean (no beam-shaped or contested stroke touching the stem or within 0.5 sp of it in the tip window; a blob -- a head at the short stem's far end -- and a stroke another mark owns do not count), then the box is refuted by the ink (Sean 2026-10-16 "Clean tip means no beam"): its level is not a candidate and the head's own value stands, DECIDED. Not a bar-sum pick, no argmax. Where the tip is not clean (a long unclassified curve, a contested beam stroke, a hook on another stem) the head stays narrowed (twin tests). 5 narrowed heads of the subset have a clean tip (Brahms 14: 2, 19: 3), the 3 `decided` box_narrowed heads and Litolff p4's hook case are unchanged. Tests `test_staged_beams_from_strokes_2_202.py` (+2), `test_beam_stack_2_202c.py` (3); beam / stroke / duration selection 1,026 pass; full fast tier not re-run.
**Subset re-run (Litolff 4, 9; Brahms 14, 19; `out/lane-report/2.202d-sub`, 1,418 s):** brahms notes +1 -1, flags +1 -5, dots +1, note values ~5, notes not written 934 -> 934 (was 939; OFF 934); litolff notes -2, flags -1, beams -1, not written 652 -> 654 (unchanged by this fix). judged right->wrong 0 / 0, right->gone 0 / 0. Heads now: tile 5 quarter, tile 9 dotted quarter (decided 1.5), tile 1 quarter, tile 6 eighth written. Still lost, NOT this cause: Litolff p4 `glyph/4/0/8/11/7` (hook on another stem, tip not clean) and Litolff p9 `glyph/9/0/4/0/3` (`beam_discounted_uncertain` ON and OFF, map not consulted). Tiles `out/print/2.202d/tiles/sheet.png`, key `out/print/2.202d/key.json`.

## 5f. 2.202d tiles answered; 2.202e: two stroke-reader faults, both already named in 5b/5c (branch `lane-2.202c-beams-remeasure`)
Sean (`out/print/2.202d/answers.json`): 1 dotted quarter, 4-5 quarter, 8 quarter, 7 sixteenth, 6 part of an ff (the Litolff p4 "note" is not a note: dropping it is right); controls 9-12 right; **BAD 2** (`glyph/19/1/5/1/3`, ON gains an eighth flag on a dotted quarter) and **BAD 3** (`glyph/19/0/12/0/5`, a real 16th ON loses).
**Cause first.** Tile 2: the "hook" is stroke 42, 1.06 sp long, **0.06 sp thick**, horizontal, touching the stem (0.25) AND a second stroke (0.5): the thin start of a slur at the stem tip -- 5b's cause 3 (its tiles 8 and 12), whose fix (a flag's far end is FREE) 5b proposed and nobody built, because 2.202b took only 5b's causes 1 and 2 and 4. Tile 3: the beam stroke across the bar is 1.19 sp thick (a double slab) whose SECOND beam starts at this stem (profile in sixteenths `8 11 11 11 14 | 21 22 20 19 20 19 13`: the jump 14 -> 21 sits at the stem's x), so the 12-sample profile reads 0.96 at the stem, under the 1.0 local cut: one level counted, `disagree_narrowed [1,2]`, bar held out. It is the eraser lane's tile 5 and `OMR_BEAM_OWN_EXTENT` is NOT the cause here (the stroke map saw one slab, correctly; the old pair rules decide it). Process lesson: **a fix list is a debt list** -- 5b named four causes; 2.202b built three; the fourth came back as a bad tile two rounds later. A lane's cause list must be closed or explicitly dropped, not left in prose.
**Fixes (STAGED ADJUDICATE, `beam_strokes.tip_reading`, inside `OMR_BEAMS_FROM_STROKES`):** (1) `FREE_END_HOOK`: a hook that touches any stroke other than this stem is not a flag. (2) `FUSED_LOCAL_MIN_SPACES` 0.8 (was the shared 1.0): 5c measured single-beam stems 0.31-0.66 locally and double 0.8-1.6, so 0.8 sits at the gap's edge, the median >= 1.0 and the outer-edge conditions unchanged. Re-settled on the 2.202d-sub records (no gather): at 0.8, Brahms 3 more heads equal main's level count, none fewer, Litolff 0 (cut 0.9: 1; 0.75/0.7: same as 0.8). Tests `test_beam_stack_2_202c.py` (5); beam / stroke / duration selection 1,417 pass.

## 5g. 2.202e FULL FROZEN SAMPLE (`lane_report --flag OMR_BEAMS_FROM_STROKES --from gather --out out/lane-report/2.202e`, 7,746 s; main 63ccef6de + 2.202b..e; `results/2.202e/report.txt`)
Fast tier: 9,210 passed, 11 skipped, 2 xfailed, 1 failed -- the judged index was stale after the 2.202c/d `answers.json` files; `judged build` rebuilt it (18 pass). `check` open 198.
**Measure 1 (exported file):** litolff notes +2 -18, accidentals +2 -3, flags +4 -6, beams -16 ~2, note values ~1, blue +1 -5, words +4 -1, red bars 0 -> 0, notes not written 2560 -> 2576. brahms notes +6 -24, rests -2, accidentals -5, dots -1, flags +7 -14, beams +6 -20 ~1, slurs -9, articulations -6, note values ~8, blue +17 -20, wedges -1, words +9 -7, red bars 163 -> 162, not written 3168 -> 3188. (2.202 milestone, before the fixes: notes -133 / -113, not written +131 / +109.)
**Measure 3 (judged):** right->wrong **0 / 0**; **right->narrowed 3 (Litolff) + 1 (Brahms)**: `rhythm-leftovers-2 tile 8` `glyph/2/1/7/13/1`, `rhythm-leftovers-3 tiles 2, 6` `glyph/2/1/7/13/3`, `/0`, and `2.81-review control_2` `glyph/0/0/0/4/9` -- all `disagree_narrowed [1,1] -> [0,1]`, the map counts no level at the tip where main's (right) one stands; causes `other`, `no_stroke`, `join_missing` (not one cause). wrong->right 1 / 0. This is not 0 right->gone: nothing lands on it.
**Narrowed heads, all `beams_from_strokes` kinds** (`beams_cause.py`): Litolff 48 (was 236), Brahms 33 (was 191): thin_remnant 0 (was 43 / 63); head-end blob 4 / 2 (was 156 / 102); fused_double 2 / 3; join_missing 7 / 3; thin_near_cut 2 / 3; no_stroke 4 / 0; other 9 / 0; `at_tip` 20 / 22 (a real second level in 2 of 2 inspected in 5b: not a loss). So the three fixed causes closed ~85% of the narrowing; the rest is a spread of small causes.
**Tiles** `out/print/2.202e/tiles/sheet.png`, key `out/print/2.202e/key.json` (seed 12, none of the 12 already in `judged-tiles.json` or the 2.202c/d keys): 9 changed + 3 controls.

## 5h. 2.202e tiles answered (Sean, `out/print/2.202e/answers.json`; OFF/ON from `out/lane-report/2.202e/work/*.symbols.json` and `*.on.mini-record.json`)
Sean: 1 eighth, 2 dotted quarter, 3 eighth, 4 eighth, 5 eighth, 6 quarter, 7-12 eighth.
**ON right (2) + same value (2):** 6 (OFF eighth blue -> ON quarter), 9 (OFF nothing -> ON eighth blue), 4 and 7 (eighth both arms, only beam->flag changed). **Neutral (2):** 2 (OFF eighth+dot, wrong) and 3 (OFF quarter, wrong), ON writes nothing. **Controls 10-12:** right. **ON loses a right note (3):** tiles 1 and 5 (Litolff p6 `glyph/6/0/1/10/2`, `glyph/6/1/8/10/5`) and 8 (Brahms p12 `glyph/12/0/12/12/6`): OFF wrote the right eighth; ON's `duration` verdict is `narrowed`, reason `beams_ambiguous`, so the note is not written (counted, not invented).
**Right->wrong (a wrong value written over a right one): 0. Right->gone: 3** -- the same class as 5f's "right->narrowed 3+1". Cause: not yet looked at; these three are the next thing to open (the stroke map's beam count at the head is ambiguous where main read a beam). Not defaulted.
