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

## Step 2 -- one owner per page mark; arcs and hairpins read page-wide (lane-2.240-s2-owner; STAGED GATHER, decides nothing yet)
**Cause and process lesson.** "Whose mark is this?" was asked of each padded cell's COPY, after the copies existed, so every answer
became a choice between copies (`glyph_owner`'s `distance` tie-break, `owned_by_another_staff`, `belongs_to_a_nearer_staff`, the twin
rules) -- and nearness slipped in as the default because a copy carries no evidence the other copy lacks. Asked once of the PAGE mark,
the question has only page evidence to answer it with: the staff's own lines, the ledger lines, the stem. Lesson: when a rule has to pick
between two copies, the copies are the bug; ask the question of the thing they copy. The same holds for arcs: 2.166 traced one curve PER
STAFF, so an arc in the gap was read twice and every later reader inherited two arcs.

**Prior work.** docs/ink-rules.md: `owned_by_another_staff` (duration 710/948 fires, accidental, articulation, dot), `belongs_to_a_nearer_staff`,
`notehead_is_a_duplicate_box`, `glyph_owner` `distance` (2,621/5,190, ~94% of contests), `reconcile_group_owners` /
`reconcile_articulation_twins` -- all kind C (double-count workarounds). LEGACY `_dedupe_cross_staff_detections` (80f18eeee, nearest band;
its own commit admits 19 Brahms notes misfiled). benchmarks: omr-staged-dedupe-2026-09 (the staged path did decide the contest; nearness
did it), omr-local-staff-2026-09 (per-cell line grid, may fall back staff-wide -- this step reads `staff_line_ys_canonical`, so inherits
it), owner-two-witnesses-2026-10 (2.216: ledger right 8/8 vs stem 0/8 -> Sean's option B), omr-arcs-system-2026-10 (per-staff trace),
omr-arc-attribution-2026-09, omr-arc-binding-2026-10 (2.223: binding to notes is a later page-wide step; not done here),
omr-hairpin-cv-2026-09 / _archive/omr-staged-wedge-2026-09 (CV wedges page-wide; detector almost never boxes a hairpin). page-facts §5
rejected list: nothing on ownership or arcs.

**Built** (flag `OMR_PAGE_OWNER`, default OFF, allow-list, needs `OMR_PAGE_MARKS`; module `tools/omr/staged/page_owner.py`, one GATHER
call after `gather_head_stem_reach`; `page_marks.gather_page_marks` now returns its boxes on `Marks`):
- (a) step-1 rule fix from Sean's tiles 2 and 7: two ink-disjoint boxes of ONE cell that both lie inside one box of the other cell are one
  mark -- only for long/lettered families (dynamic, beam, arc, hairpin, flag, text); a head/rest/accidental/dot box holding two of them
  stays two (a chord is not one head). The 0.5 share is NOT tuned; near misses within 0.05 are counted as a margin only.
- (b) `Q.PAGE_MARK_OWNER`, one row per page mark: `inside_staff` (centre within 0.75 sp of a staff's own outer line, in the bar at its x)
  -> that staff; else, heads only: the far-head ledger reading of each view (`Q.FAR_HEAD_OWNER_LEDGER`; two views count ONCE; views naming
  two staves -> GUESSED with both), the stem (`Q.HEAD_STEM_REACH`) a second witness. **Deviation from the brief, on purpose:** a stem that
  names the other staff does NOT make the head GUESSED -- DECISIONS 2026-10-28 (Sean, 2.216 option B, "plain, not blue") reverses the
  10-27 rule for that case, and DECISIONS outrank a brief; it is recorded as `ledger_over_stem` with both staves as candidates, and four of
  the 12 tiles ask Sean about exactly those. CLAUDE.md §5 still says "disagree -> GUESSED" and is stale on this point (manager: one line).
  No witness -> ABSTAIN `owner_no_rungs` (ledger read, named nothing: counted, our failure) / `owner_no_witness`; any non-head family
  outside every staff -> `owner_follows_its_note` (its owner is the note it binds to: 2.223 / step 3). Nearness decides nothing.
- (c) `Q.PAGE_SPAN`, one row per arc / hairpin READ PAGE-WIDE (Sean 2026-10-30). Arcs: the 2.166 per-staff traces joined ACROSS staves
  when their seed boxes are one page mark or their traces cover the same page pixels (>= 0.5 of the shorter's columns on overlapping rows);
  a page arc never holds two views of one staff that the per-staff tracer kept apart (the first cut glued two slurs through a long
  neighbour trace -- seen on a tile before it went to Sean, fixed, unit-tested). An arc box no trace followed is a witness only
  (`span_untraced`). Hairpins: each CV wedge (`Q.WEDGE_BOX`, page-wide) is one hairpin, two wedge reads on one box are one; every page mark
  whose box lies inside it is recorded `boxed_as` (the detector boxes hairpins as beams). Nothing consumes the claim yet: the consumer is
  `stroke_owner`'s tiers, which this lane's fence forbids (2.242 owns `own_strokes`); step 3.
- (d) retire nothing; `page_owner compare REC` lists every old cell-copy rule against the owner by place.

**Capture readout** (`OMR_SPLIT_JOINS=0 python3 -m tools.omr.staged.page_owner readout litolff:20261029-night brahms:20261029-night`,
master cells, all 17 frozen-sample pages; out `s2/rec0|rec1/page_owner.json`). ⚠️ The 10-29 slices were gathered before 2.239 landed:
with 2.239's `OMR_SPLIT_JOINS` on, the re-cut stroke maps miss the record on 127 of 352 Litolff p2 cells (their boxes would silently drop
out); with it off every cell matches box for box. A readout off a night record must re-cut with that record's own flags.
| | Litolff (9 pp.) | Brahms (8 pp.) |
|---|---|---|
| head marks: inside_staff / ledger / ledger+stem agree / ledger_over_stem / stem alone | 3,886 / 283 / 730 / 6 / 106 | 4,484 / 257 / 1,049 / 2 / 74 |
| head marks abstained `owner_no_rungs` | 122 | 165 |
| GUESSED (two views' ledger readings name two staves) | 0 | 0 |
| marks seen from TWO staves: decided / abstain (no_rungs, follows_its_note) | 928 / 5, 1,104 | 1,717 / 16, 2,292 |
| arcs: per-staff views -> page arcs (joining two staves' views; crossing a barline) | 804 -> 535 (269; 453) | 1,363 -> 948 (415; 694) |
| arc boxes no trace followed (witness only) | 409 | 2,570 |
| hairpins read page-wide (detector boxes inside them) | 4 (1 hairpin, 1 mark) | 53 (82 beam, 1 arc) |
Step 1 with the pieces rule (`page_marks readout`, same pages): Litolff unchanged (0 merges by the rule); Brahms 17 merges, `cell_twice`
110 -> 92, twin ink 171,040 -> 163,174 px. Near misses (share 0.45-0.5): Litolff head 10, dynamic 8, flag 3; Brahms beam 15, arc 9, dynamic
3, flag 2, head 1, whole rest 1 -- recorded, not tuned.

**The old rules against the owner, by place** (`page_owner compare` on the WRITTEN ON records, Litolff pp. 2,4 / Brahms pp. 4,5, full
ADJUDICATE; `s2/compare_written.log`): `duration:owned_by_another_staff` agrees 254 / 366, disagrees 1 / 0; `glyph_owner` ledger tiers
(note_first, direction, density, ladder) agree 282 / 797, disagree 0; `stem_toward_staff` 222 / 13 agree, 0 disagree; `staff_band` 43 /
277 agree; `glyph_owner:distance` agrees 153 / 425, DISAGREES 11 / 12, owner silent 836 / 1,231 (heads 87 / 32; the rest dynamics, arcs,
beams, ledgers, marks -- the families whose owner is their note); `glyph_owner:range_veto` agrees 9 / 0, DISAGREES 0 / 45 (Brahms: the
written-range veto overrides the staff's own lines or ledger); `belongs_to_a_nearer_staff` agrees 2 / 2, silent 8 / 6;
`notehead_is_a_duplicate_box` fires are same-staff twins (27 / 7, no staff choice). On the frozen-sample slices (stored verdicts only):
`owned_by_another_staff` agrees 710 / 934, silent 4 / 14, disagrees 0. So step 3 can retire `owned_by_another_staff` for heads and the
ledger/stem/staff-band tiers where they agree; `distance` cannot simply go -- on heads it decides 87 / 32 marks the owner abstains on
(no rungs, no stem) and disagrees on 23; `range_veto`'s 45 Brahms disagreements need tiles first.

**Controls that can fail** (`page_owner controls REC --page N`; Litolff p2, p4, Brahms p4 -- all pass): (a) NEVER NEARNESS: with every ledger
and stem row removed, 0 of the 113 / 236 / 194 heads outside every staff band get an owner, while the nearest-staff arm would decide all
of them; (b) a two-staff head the ledger decided, with ONE view's reading turned to the other staff, becomes GUESSED with both staves (the
first version of this control picked a mark whose other view had no reading and FAILED -- the flip then decided the other staff; it now
picks a mark two views agree on); (c) a two-view page arc: one view's trace moved one space apart -> two arcs; unmoved -> one. Unit tests
`tools/omr/tests/test_page_owner_2_240.py` (20), every CONTROL arm can fail.

**File** (OFF vs ON, OCR held fixed with `--no-surya`, master cells, shared detector cache; `s2/byte_identity.sh`): the exported MusicXML is
NOT byte-identical: Litolff +1 `cresc.` word, Brahms -1 `Cresc` word. A content diff of every GATHER row (row ids blanked, `s2/rowdiff.py`)
shows the only differing rows are OCR -- `direction_word` (read by `surya` even under `--no-surya`: 59 / 164 rows), the word claims built on
them (5 / 3) and `input_domain` (2 / 2). Every non-OCR row is identical. Step 1 called its `--no-surya` run byte-identical: that was luck;
`--no-surya` does not hold the direction-word reader fixed. The shared lane report (`LANE_REPORT_SAMPLE=s2/sample2.json lane_report --flag OMR_PAGE_MARKS --flag OMR_PAGE_OWNER --from gather --cell-map master --tag 20261029-night`, Surya on, `s2/lane_report.log`): Litolff pp. 2,4 and Brahms pp. 4,5 -- NOTHING CHANGED in the exported file (1,497 / 2,145 notes+rests paired); Sean's judged answers right->wrong 0 (188 / 174 tiles), unwritten->wrong 0.

**Tiles for Sean** `out/print/2.240-s2-tiles/tiles/` (12; key `out/print/2.240-s2-tiles/key.json`, outside the tile folder): 7 owner decisions
(4 `ledger_over_stem`, 3 `stem`; no GUESSED case exists on the sample) on the staff the record names, 5 page-wide marks (one hairpin, four
arcs, two of them joined from two staves' views, three crossing a barline). Question: what is in the box, one mark or more; for a note,
is it the full staff's in the picture or another's.

**Open.** Sean's 12 tiles; a consumer for `Q.PAGE_SPAN` (stroke_owner tier 0 -- fenced this round); the 23 `distance` and 45 `range_veto`
disagreements (tiles before step 3); 2,570 Brahms arc boxes no trace followed (the detector's arc class on staff lines, step 1's crops 4-5);
GUESSED never fires on the sample, so the both-staves path is proved only by its control.

## Step 2, round 2 -- Sean's tiles answered (lane-2.240-s2-owner; STAGED GATHER, flags OFF)
**Cause and process lesson.** Tile 11 (Litolff p4, a head that belongs to the staff BELOW) was NOT "a staff's own line read as a ledger": the one rung
the upper staff's reading counted (row 2392.5, one space under it) is a SLUR's ink -- the curve `gather_system_arcs` traced from the lower staff's
crop (`Q.SYSTEM_ARC` trace rows 2389-2393 at x 1111) -- and the head's own line (the lower staff's ledger) completed the chain. The ledger reader
asks "is there ink on a ledger row?", and an arc on that row is ink. The manager's hypothesis (a staff line) is real too, but elsewhere: of 1,757
Brahms owner-ledger rows (pp. 4,5) 554 dropped a rung, 768 rungs that were ANOTHER staff's own line and 111 that were arc ink; of 2,434 Litolff
rows (pp. 2,4,6,16) 428 dropped 467 other-staff-line and 59 arc-ink rungs. Lesson: a ledger reading is evidence only on ink nothing else owns;
the arcs were traced (2.166) before the ledger reader ran and nothing consulted them. Second lesson (process): a Litolff re-gather of fewer than
~16 pages reads NO far head (`no_page_shape`: the pool of 8 clean on-line heads is reached only by page 16's own 9), so the 2-page lane-report
sample cannot see a Litolff ledger change at all; tile 11 was reachable only through a gather of pages 2,4,6,16 (page 16 releases the held pages).

**Built** (OMR_PAGE_OWNER, OFF): (1) `far_head_reader.read_absolute_position / FarHeadPage.read / far_head_owner.read_toward` take an optional
`not_ledger(y)`; `page_owner.not_ledger_maker` says `other_staff_line` (within the page line thickness of another staff's line, per-bar grid at the
head's x) or `arc_ink` (inside a traced arc's rows at a column within 3 px of the head); `gather._file_owner_ledger_readings` re-reads each candidate
with it ONLY when the flag is on and files the dropped rungs and the unfiltered reading on the same row (`not_ledger_dropped`, `unfiltered_pos`).
The exported position reading (`Q.FAR_HEAD_LEDGER_POSITION`) is untouched. (2) `arc_owner`: an arc takes the staff its END HEADS are owned by
(heads in `arcs_system`'s own end window, on the side the curve's notes lie; an arc is over its notes); ends naming two staves abstain
(`ends_disagree`), no end heads abstain (`no_end_heads`), an unowned end head abstains, one end only is GUESSED (`one_end`). Binding arcs to notes
is 2.223's (branch lane-2.223-anchoring, unmerged, `bind_curve`); only the owner's part was built here, its own staff never an input. (3) the
hairpin witness (Sean 2026-10-31): a READ hairpin between two staves over the head's x, head wholly above/below its rows and inside the stretch of
the two staves round it -> upper / lower staff; names a head ledger+stem named nobody (`hairpin`); agrees (`+hairpin`); disagrees -> GUESSED with both
staves (`hairpin_disagrees`), the ledger/stem owner kept. (4) from the 2.245 hand-off: a head box >= 3.0 sp wide is not one head -> abstain
`owner_box_not_one_head` (the constant of `box_kind.HEAD_BOX_MAX_W_SP`, restated: that branch is unmerged). NOT done: building page marks only
from boxes ADJUDICATE has not refused -- GATHER runs before ADJUDICATE and decides nothing, so the filter belongs to the consumer (step 3: owner
row + the refusal verdict by place), not to `gather_page_marks`.

**Numbers** (`s3/measure.py`, `s3/measure_*.json`; O = OFF rows, F = ON rows, H = F + hairpin witness; master cells).
- Tile answers: tile 11's head now decided `staff/4/1/2` (the lower staff), reason `stem` (its upper reading lost the slur rung; fresh gather: the
  unfiltered upper reading did not fit either, so this is shown by the rung list, not by a flip); tile 5's arc -> `staff/6/1/3` (above) GUESSED
  `one_end`; tile 8's arc -> `staff/5/1/12` (below) decided `ends_agree` -- all three as Sean answered; tile 12 (a 5.2 sp 'head' on a slur) -> abstain
  `owner_box_not_one_head`. `s3/check_arcs.py`.
- Owners changed by the ledger filter: Brahms pp. 4,5: 8 owner-ledger readings changed, 1 head owner (`glyph/4/0/10/5/5` abstain -> ledger; the other
  two changes in the first count were tile 12's box and a non-head mark); Litolff pp. 2,4,6,16: 3 readings changed, 0 head owners. Hairpin witness:
  0 head marks on all 17 sample pages -- every head in a hairpin's x span is inside a staff's band (rule 1 decides; `s3/hairpin_diag.py`). Its first
  version (no locality) disagreed on 9 Brahms heads: all were far from the hairpin (a head of the top staff against a hairpin 12 staves down) -- the
  rule must be local, and now is (test).
- Arc owners (all 17 sample pages, slices): Litolff 535 arcs: 303 decided `ends_agree`, 148 GUESSED `one_end`, 84 abstain; owner on a staff the arc was
  not traced from 25. Brahms 948: 624 / 275 / 49; 73 on another staff.
- Old rules vs owner (`s3/compare_written.log`, full pipeline ON, Brahms pp. 4,5 / Litolff 2,4): `glyph_owner:distance` disagrees 13 / 11 (was 12 / 11),
  `range_veto` disagrees 45 (was 45), `owned_by_another_staff` agrees 367 / 254. The filter and the hairpin move neither number: step 3 cannot yet
  retire `distance` or `range_veto`.
- Lane report (3 measures; `s3/lane_report.log`): exported file NOTHING CHANGED (Litolff 1,497, Brahms 2,143 paired); judged right->wrong 0 (188 / 174
  tiles), unwritten->wrong 0.
- Sean's 12 new tiles: `out/print/2.240-s3-tiles/` (key.json beside the folder): the places of s2 tiles 5, 8, 11, four more arcs on a staff they were
  not traced from, three `ledger_over_stem`, the one filter-decided head, one control.
- Shared box: the big-record lock `library/_shared-records/.record-load.lock` was stale from 09:34 to 10:43 and stalled three lanes; I removed
  the empty directory.
**Open.** Sean's 12 tiles; the `one_end` GUESSED arcs (a third of all) -- a window question for 2.223; `arc_ink` can drop a REAL ledger an arc
passes over (Litolff p4 bar 3: the lower staff's own ledger at 2433.5 was dropped as arc ink; the head still has its stem) -- tile it before step 3;
page marks from unrefused boxes (step 3).
