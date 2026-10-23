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
two Litolff pages (0.67 MB a page). Still ~520 bytes a row; what is left is the envelope and the named fields -- pooling per cell is plan step 9. The file-level number after the `subjects` fix: NOT MEASURED YET (see Open).

## 2. Byte-identical check (PYTHONHASHSEED=0, detector cache, `--musicxml`, pages Litolff 2,4)
Litolff, flag OFF vs ON: the MusicXML and its coverage JSON are byte-identical (`cmp`), with the code BEFORE the `subjects` fix (record: 44,393 -> 63,654 observations, 46 `ink` claims, 136 vs 90
`claimed_area` rows). Brahms pages 4,5 OFF finished; its ON arm and the OFF-vs-OFF re-gather were stopped by the coordinator for Sean's overnight re-gather. Open: Litolff ON re-run on the final
code, Brahms ON, Brahms OFF2 (the one Surya word of 2.195). Not claimed.

## 3. Sanity count: 2.185's same-cell different-class doubles as shared stroke sets (`glyph_strokes_census.py`, Litolff pages 2,4 ON record)
199 pairs (same cell, different class, IoU >= 0.5): **167 stand on the same stroke set**, 28 overlap without being equal, 4 have an empty list. Examples: a head and a whole rest on one blob,
keyFlat/keySharp on three strokes, dynamicF/dynamicZ. Control: 10,559 same-cell different-class pairs with IoU 0 and strokes: none shares a stroke. Brahms: not run (Open).

## 4. `check`
`python3 -m tools.omr.staged.check`: TOTAL 203, status ok. By design: reach +1 (`Q.GLYPH_STROKES` unread), wiring +2 (`Q.GLYPH_STROKES.shares`, `Q.CLAIMED_AREA.shares`). wiring -5 stale entries removed (`area_sp2`,
`staff_lines_left` truly gone; `profile_sixteenths`, `staff_local`, `cell_n_below_floor` are still written but through a conditional dict the tool cannot see, so the drop is partly the tool's blind spot).
Fast tier (final code): 8825 passed, 0 failed (12 skipped, 2 xfailed).
