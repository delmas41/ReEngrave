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
