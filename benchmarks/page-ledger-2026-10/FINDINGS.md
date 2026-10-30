# ROADMAP 2.240 -- cells are views, the page is the ledger (STAGED GATHER geometry; measurement + design, nothing built)

Branch `lane-2.240-page-ledger` 34cb3f3a3 (measure_cells.py, box_where.py, pick_crops.py, crops.py; out/{litolff,brahms}.json). Written by the manager from the lane's report. Counts: 20261029-night frozen-sample slices on the master cell maps (Litolff 9 pages, Brahms 8). Control: the de-dup reproduces the 2.236 readout exactly (16.9% / 19.0%).

## Why it was done
- 2026-05-14, first pipeline (19caa533d): per-measure max-zoom canonical crops (~400 px staff span) padded 4 spaces each side for ledger lines and dynamics above, ledger lines and pedal below; tested on Bach WTC piano, where staves are far apart and the bands never met. Horizontally barline to barline, no pad.
- 2026-08-28 (80f18eeee): on conductor's scores the padded bands overlap and one head was detected once per staff (Mahler 54 notes vs 22 true); fixed DOWNSTREAM by `_dedupe_cross_staff_detections` (nearest band), whose own commit admits 19 Brahms notes put on the wrong staff -- "exactly the ledger-line case the padding exists for".
- 2026-09-01 (81446a0b4): the ledger ladder and range became the arbiter; pad grows to 6 where there is room (measure_extractor.py:40-66: stems ~3.5 sp, Mahler duration 0.864 -> 0.455 when tight; Brahms Vn1 B6 exported as timpani Ab1; cell height coupled to OMR_IMGSZ, 4.0 -> 4.6 sp cost 3 of 45 notes).
- Then a run of downstream repairs: OMR_ARC_ATTRIBUTION (09-04), phantom notes through the padding (09-14, 14 of 25), barlines clipped at exactly +-4.00 sp (09-20). Sean labels these same padded cells, so the detector's view is frozen by its labels (recut_cells refuses a frame mismatch).
**Cause in one line:** a crop chosen for the detector (a VIEW) also became the unit of ownership (a LEDGER); every later reader inherited "my cell = my ink".

## Vertical vs horizontal
**Vertical: pad 4 or 6 sp, real overlap.** 29% (L) / 34% (B) of cell area is inside two cells; stroke ink seen twice 16.9% (1.80M of 10.64M px) / 19.0% (6.95M of 36.57M); 100% between two staves of one system (93% / 82% in the gap, 7% / 18% inside the other staff's lines). Same-class box pairs from two staves' cells at IoU >= 0.5: 1,653 of 19,951 boxes (L), 3,541 of 30,077 (B; 778 noteheads). Boxes centred on ANOTHER staff's lines 204 / 1,346 (flat tie/beam boxes on a neighbour's line 118 / 508, which this cell's eraser leaves alone). Boxes in the pad gap: 36% / 43%.
**Horizontal: no pad, no overlap** (same staff, two bars: 0 px), but not "absolute": one x per barline per system (`_measure_x_boundaries` measure_extractor.py:1391 uses `bl.x`, the cluster mean; `_system_barline_columns` l.1247 fits each rule's tilt and throws the slope away; l.1272 records Litolff p6 s1 drifting 21 px). The cut runs THROUGH the barline: its ink is split between two cells on 78% (L, 2,072 of 2,672) / 83% (B, 1,515 of 1,835) of staff-barlines, so every barline reaches the stroke maps as two half-barline edge strokes. Tilt: Litolff |rule - cut| >= 0.45 sp on 74 staff-barlines (2.8%), max 1.49 (p1, not crop-checked); Brahms max 0.36. Straddling ink through the rule off the staff 501 / 1,157 (slurs, ties, beams, hairpins), each cut in two; `arcs_system` re-joins arcs from >= 2 cells: 51 of 804 (L), 160 of 1,363 (B).

## What it costs (fresh fires L / B, docs/ink-rules.md)
Rules that exist only to undo the vertical overlap: duration `owned_by_another_staff` 710 / 948; glyph_owner `distance` (nearest-staff tiebreak) 2,621 / 5,190; accidental owned_by_another_staff + head_belongs_to_a_nearer_staff 85 / 246; notehead belongs_to_a_nearer_staff 19 / 14; `clipped_fragment` 177 / 165; `rest_clipped_by_crop` 30 / 176; articulation owned_by_another_staff 0 / 8; reconcile_articulation_twins 0 / 3; the cross-staff part of the duplicate-box rules (not split). Inferred mostly vertical: arc `ink_is_a_staff_line` 287 / 2,570, part of too_narrow / no_ink_under_box. Conventions that stay but are contested only because two cells saw the note: ledger owner 1,840 / 2,251; ladder/range 248 / 1,080. Horizontal-edge rules: the arcs_system join, head_oval's bar-left-edge case (2.164), 2.155 stem cut at a bar edge, dot_role/notehead on_a_barline, the rest barline family, consequences.py:977, the per-cell barline claim (gather.py:295). Notes lost: historical only (19 misfiled, B6 as Ab1, 14 phantom notes, 5 phantom timpani arcs); not measured on today's tree.

## Design: cells are views, the page is the ledger
1. Detector unchanged (same crops, pad, imgsz, weights); LEGACY measure_extractor untouched; every change a STAGED consumer.
2. Page identity for every reading: new GATHER step `gather_page_marks` -- boxes of one family from two cells are ONE mark when their page boxes sit on the same ink strokes; merged once, both views kept as witnesses (two readings of one raster count once, CLAUDE §4). Replaces the IoU twin rules, the cross-staff half of the duplicate rules, and owned_by_another_staff as a refusal.
3. One owner per page mark: ledger lines name the staff, stem second witness, disagreement GUESSED with both staves, "no rungs either way" abstains, never nearness (page-facts §3). `distance` stops deciding.
4. Stroke map on the page: one per system on the page raster, staff lines erased once per staff from its own local geometry; one stroke id, its staff measured locally; erased-raster consumers read through a cell window (`strokes_in(cell)`).
5. Horizontal: barlines become tilted page columns (keep the fitted slope); the claim follows the tilt and owns the whole rule once; brackets kept out (2.239); straddling arcs/hairpins/beams are page-wide claims; a mark's bar is decided by its notes' x against the tilted column, not by which crop held it.
Steps, each proved by capture readout + Sean's p0 labels + tiles with the file as a veto: (1) record page-mark ids only (twin ink -> 0); (2) owner per page mark, tiles on every disagreement; (3) retire the twin and nearer-staff rules where (2) matches them and the tiles; (4) tilted barline columns + whole-rule claim, after 2.239; (5) page stroke map behind a cell window (largest; byte-compare stroke ids on non-overlapping cells first); (6) straddle claims for beams.
Risks: crop-sensitive detector (never change its cells; `cell_map verify` guards); LEGACY shares measure_extractor; a merge could fuse two real marks (stacked heads, unison on two staves) -- merge on shared ink strokes, not IoU, and tile the merges; the page stroke map changes every erased-raster consumer at once (cell window + byte identity); two scan publishers only (tilt differs a lot). Crops: out/print/2.240-crops (6, "is this one mark?"; not yet shown to Sean; tile05 boxes a whole line).

## Sean's answers on the crops (2026-10-30)
1 arc, 2 dotted quarter, 3 eighth, 4-5 staff line, 6 tie. Every crop supports the design: marks crossing a barline are one mark (1, 6); a head seen from two staves' crops is one note (2, 3); tie/beam boxes on a neighbour's staff line are that staff line (4, 5), which only page-wide line erasure removes.

## Step 1 -- page-mark ids (lane-2.240-s1-page-marks; STAGED GATHER, decides nothing)
**Cause and process lesson.** A head in the gap between two staves is boxed once per staff's padded crop, and every reader since 2026-08 has
asked "which cell's box is the real one?" (IoU twin rules, nearest-staff tiebreaks) instead of "is this the same ink?". The lesson: the
question "same mark?" belongs to the page ink, not to the boxes' geometry -- IoU merges a head with its stacked neighbour and misses a
clipped view; shared page ink does neither.

**Built.** Flag `OMR_PAGE_MARKS` (default OFF, allow-list). New module `tools/omr/staged/page_marks.py`; one GATHER call site in
`gather.gather()` right after `gather_glyph_strokes` (`_page_marks.gather_page_marks(log, pws, cells, local, detections, stroke_cells)`).
Row `Q.PAGE_MARK` (one per detector box, on its glyph subject; value = page-mark ordinal per page; detail family, members, cells, ink_px,
why, pairs [other key, share, IoU, merged, reason]; a box whose cell has no stroke map ABSTAINS). Reader `READERS.CV_PAGE_MARKS`; CLAIM
coverage; `reach.KNOWN_GAPS` (producer only) and `STAGE_OF_FILE` GATHER; `lane_report.GATHER_MODULES` (the flag re-gathers).
Rule: a box's ink = page pixels dark on `pws.page.binary`, on a stroke of its own cell (labels sampled onto the cell's page rectangle exactly
as `claim_readout` does), inside the box. Two boxes of one family (`stroke_owner.family_of`) from two cells are one mark when they share
>= 0.5 of the smaller one's ink (the register's one cut, not tuned), greedy by share, and a mark never holds two boxes of one cell that do
not themselves share that ink (`cell_twice_in_mark`). Same-cell twins with no second cell are left to 2.186.

**(a) Byte identity.** Re-gathers on the master cells, shared detector cache, serial, `--no-surya`: Litolff pp. 2,4 and Brahms pp. 4,5 --
exported MusicXML byte-identical OFF vs ON (ON records carry 5,782 / 9,291 `page_mark` rows). The first try through `lane_report --from
gather` (Surya on) was NOT identical (Litolff +4 blue, Brahms +1 accidental ~1 pitch +1 blue -1 word); a content diff of the gathered rows
(row ids blanked) shows the only differing rows are OCR rows -- `margin_label` read by Surya in one arm and by tesseract in the other,
`direction_word`, and the word claims built on them (67 / 124 rows) -- the OCR server under shared load, not this step. ADJUDICATE replay is
deterministic (OFF re-run == OFF; ON with page_mark rows stripped == ON). Lesson: a GATHER byte-identity test must hold OCR fixed.

**(b) Readout** (`python3 -m tools.omr.staged.page_marks readout REC...`; 20261029-night frozen-sample slices, master cells, all 17 pages):
| | Litolff (9 pp.) | Brahms (8 pp.) |
|---|---|---|
| boxes -> page marks | 19,951 -> 17,338 | 30,077 -> 25,157 |
| merged pairs | 2,781 (head 872, dynamic 777, arc 345, beam 320, accidental 183) | 5,143 (head 995, beam 938, arc 783, dynamic 597, accidental 420) |
| 2.240's same-class two-staff IoU>=0.5 pairs (control) | 1,654 (2.240: 1,653; one pair at IoU 0.4996 rounds to 0.5 here) | 3,541 (= 2.240) |
| ... of them merged | 1,643 | 3,497 |
| merges at IoU < 0.5 (clipped views, fragments) | 966 | 1,285 |
| refused candidate pairs | share_below 142, cell_twice 33, no_shared_ink 18, no_ink 4 | share_below 628, cell_twice 110, no_shared_ink 62, no_ink 11 |
| twin ink (one family, two cells) before -> after | 707,694 -> 11,230 px (-98.4%) | 3,518,243 -> 171,040 px (-95.1%) |
Residual twin ink by family: Brahms beam 109k, arc 30k, dynamic 21k, head 4k; Litolff dynamic 5.5k, head 3.9k. It is the refused pairs:
long marks (beam / slur boxes that are often a hairpin, an accent or a staff line) whose boxes cover different spans, and `cell_twice`
(a dynamic or beam boxed as two pieces in one cell and one piece in the other).

**(c) Controls that can fail** (`page_marks controls REC --page N`; unit tests `tools/omr/tests/test_page_marks_2_240.py`, 13):
one real head copied into the neighbour cell's view MERGES (Brahms p4, Litolff p4); a real stacked third (two whole heads of one cell, one
space apart, boxes overlapping) copied into the neighbour cell stays TWO marks (Brahms p4, Litolff p2) and the broken arm (no guard, share 0)
FUSES it, so the control can fail; the first version of this control picked a 6 px edge fragment as "the second head" and failed -- the
control now asks for two whole heads; an identical copy of the rows reads identically; the readout re-derived from re-cut master cells
reproduces the gather's own `Q.PAGE_MARK` partition box for box (Litolff pp. 2,4 ON record: 2,716 + 3,066 rows, equal). Unit: one head two
cells merges; another family on the same ink does not; blank paper never merges whatever the IoU; a clipped view merges; unison on two
staves stays two; flag OFF files nothing; a cell with no stroke map abstains per box.

**(d) Tiles for Sean** `out/print/2.240-s1-tiles/tiles/` (12; key `out/print/2.240-s1-tiles/key.json`): 6 merges, 3 `cell_twice` refusals,
3 near-miss `share_below` refusals, all in the gap between staves, both plates. Question: "is the ink in the box one mark?" Looked at, every
tile: merges 3, 4, 5, 6, 8, 10 look like one mark each (a slur boxed as beam, a staccato, two heads, a slur, a hairpin boxed as beam);
refusals 2 (one p) and 7 (one beam) look like ONE mark refused -- `cell_twice` is too strict where one cell boxed one mark twice; 1 and 11
are a slur plus a tie (two marks, refusal right); 9 looks like ONE flag refused at share 0.492 (a near miss); 12 a "beam" pair on a staff line (Sean's crop 4-5 kind).

**What step 2 needs from this.** Read `Q.PAGE_MARK` and give each mark ONE owner staff (ledger lines name it, stem second witness,
disagreement GUESSED with both staves, no rungs abstain -- never nearness); retire `owned_by_another_staff` and the IoU twin rules only where
the owner agrees with them on tiles. Open: whether `cell_twice` should admit two non-overlapping boxes of one cell that both lie inside one
box of the other cell (tiles 2, 7 decide), and the long-mark residue (beams / arcs), which is really detector class noise (hairpins and
accents boxed as beam) plus the barline cut (steps 4, 6).
