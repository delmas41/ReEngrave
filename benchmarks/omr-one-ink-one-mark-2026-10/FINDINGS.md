# 2.186 -- ONE INK, ONE MARK (STAGED GATHER merge + ADJUDICATE ownership + EXPORT guess; flag `OMR_ONE_INK_ONE_MARK`, default OFF)

## Cause (rule 3) and the process lesson
Production runs the detector once per CELL with class-wise NMS (`agnostic_nms=False`, iou 0.7, floor 0.25). Reproduced from the detector, not read off a
record: re-running it on Litolff p4/7/16 and Brahms p21/23 gives the stored boxes in 1,537 of 1,537 cells (`live_check_2_186.py`, results/live_*.json), and
the merge on the live boxes equals the merge on the stored ones. Two separate causes, one of them found only because Sean widened the lane:
1. SAME cell: two classes of one family both clear the floor on one ink -> two boxes -> later rules refuse both (rests) or write nothing (accidentals,
   `apply_printed_accidental` on a head two glyphs of different alteration own).
2. ACROSS cells: a neighbouring staff's crop boxes the same ink again. `glyph_owner` (the existing cross-staff contest) already decides which staff owns
   it and the exporter already drops the non-owner copy of a NOTE or REST -- but nothing asked `glyph_owner` about an ACCIDENTAL
   (`adjudicate_accidental_owner` read the ownership of HEADS only), so the copy in the wrong cell could own a head of the wrong staff.
Process lesson: 2.185 called cross-cell doubles "harmless" because it counted them at the box level and followed them to the file for notes and
rests only; accidentals have a different path (no mark-group, no export-time owner drop). A "harmless" verdict is a claim about ONE path; check every
family's own path before generalising. And the existing `MARK_GROUP` rep ("most confident member") is exactly the stronger-box-by-confidence rule Sean
rules out -- it decides nothing for accidentals and for rests is preceded by the owner drop, so the rep never overrules ownership.

## What was built (all behind `OMR_ONE_INK_ONE_MARK`, OFF)
- `staged/one_ink.py` (pure): within ONE cell, boxes of DIFFERENT classes of ONE family (`rest`, `accidental` of `yolo_detector._CATEGORY_MAP`; not `key*`,
  not flags, not heads) at IoU >= 0.5 become one box: stronger class, `detail.one_ink = {rivals, margin, winner}`; winner-centred, no chaining; same class left
  alone; never across families. Called by `gather` right after `detector.detect`; `one_ink.plan` is the one function the live path and the replay share.
- ADJUDICATE: `adjudicate_accidental_owner` asks `glyph_owner` FIRST: another staff owns the ink -> abstain `owned_by_another_staff`; contest undecided ->
  abstain `ownership_undecided`; counted in the export census (partition stays at `unaccounted` 0). `adjudicate_rest_is_not_a_rest`: a merged rest NO rule
  refused ends NARROWED `one_ink_merged` (last, after every refusal: Sean's tiles 2 and 9 stay refused by their own rules).
- EXPORT: `one_ink_guess_of` -> written GUESSED/blue with candidates (winner first) and margin; the head an accidental alters and the later notes it governs
  go blue. The READ bar `one_ink.ONE_INK_READ_MARGIN` is None: nothing is READ until Sean sets it on tiles.
- Subsumed: nothing is deleted. With the flag ON the different-class branch of `_duplicate_box_refusal` still fires for pairs below IoU 0.5 (Litolff 3 of 10
  pair inks, e.g. the 2.182a tile-4 restQuarter+restHalf) and for 2.172 view boxes, so it is NOT dead; it is now the residual branch.
- NOT merged, with the reason: FLAGS. `adjudicate_duration` already treats flag8th*+flag16th* as two votes, breaks the tie with the stem-tip hook count
  (`hooks_counted`) or narrows (`flags_disagree`); a merge would replace that with an argmax. Litolff: flags_disagree 8, hooks_counted 27, unchanged by the flag.
- NOT done, and why (instruction: stop and report): filing the ink as a `Q.CLAIMED_AREA` claim through the 2.181 register. `claims.covering` only reads rows;
  the filer (`gather_claimed_register`) and the one consult (`claimed_by.consult`, owners `clef|leading_column|meter`, an unknown owner falls into the
  `leading_column` branch) are register internals lane 2.183 is editing, so an `ink` owner cannot be expressed without editing them.
- Tests: `tools/omr/tests/test_staged_one_ink_2_186.py` (23, each refusal/keep has a control).

## Measured by the shared lane report (`python3 -m tools.omr.staged.lane_report --flag OMR_ONE_INK_ONE_MARK`, frozen sample, re-gathered OFF and ON; Sean's 2026-10-21 rule)
Files: `lane-report/report.txt`, `report.json`; tiles `out/print/2.186-one-ink-one-mark/` (seed 2188, orange box), key `out/print/2.186-key.json`.
| plate (8 pages) | exported file, ON vs OFF | red bars | judged right->wrong |
|---|---|---|---|
| Litolff | rests +2, accidentals +21 -12, pitches ~37, blue marks +34 -2 | 0 -> 0 | 0 (233 tiles) |
| Brahms | notes +2, rests +5, accidentals +201 -58, dots +1, ties +8 -12, slurs -4, pitches ~253, blue marks +201 -7, words +1 -4 | 166 -> 166 | 0 (232 tiles) |
Not explained: Brahms ties/slurs/words/dots move though the flag touches only rests and accidentals. Ties follow pitch (an applied accidental changes the pitch a tie needs); words/dots/slurs have no mechanism in this lane. No OFF-vs-OFF re-gather control was run (the tool prints `OFF==record NOT CHECKED` in re-gather mode); if one shows the same movement it is gather non-determinism, not the flag. The OFF==stored control IS established for the replay below.
A first version of the lane dropped the absorbed boxes, which shifted every later glyph index in the cell (a judged notehead tile went `not_found`, Litolff glyph/10/1/1/8/8); the report caught it. Now the absorbed box is KEPT at its index and refused (`rest_is_a_duplicate_box` / `one_ink_absorbed`); the sample shows 0 gone.

## Background: Litolff whole-movement replay (first design, boxes dropped; superseded by the sample above), run before Sean's three-things rule; Brahms replay NOT run to the end: stopped on the coordinator's instruction)
Record 20261020-night, replay = stored gather rows + the same merge, ADJUDICATE..export (`replay_2_186.py`). CONTROL: flag OFF live verdicts equal the stored
ones: rest_is_not_a_rest 2969/2969, accidental_owner 1508/1508, accidental 4323/4323, duration 14867/14867.
| exported file, Litolff | OFF | ON |
|---|---:|---:|
| rests written | 2884 | 2888 (+4, all blue) |
| printed accidentals applied | 460 | 495 (+35) |
| notes in file / pitched | 11771 / 8887 | 11775 / 8887 |
| notes written blue | 2145 | 2248 (+103: heads and later notes under a merged accidental) |
| heads_contradicted (accidental census) | 74 | 3 |
| red bars / bars that add up | 508 / 4834 of 4834 | 507 / 4835 of 4835 |
| notes_not_written_total | 4543 | 4532 |
| key-signature verdicts differing; flag votes (flags_disagree, hooks_counted) | -- | 0 ; unchanged |
| Sean's judged index (right / wrong / narrowed / abstained) | 135 / 28 / 6 / 2 | identical: right->wrong 0 |
SAME-cell part: 210 accidental inks merged (222 boxes absorbed), 7 rest inks merged. Rests: 4 written blue `one_ink_merged`; the other 3 stand refused by
the rule that names them (rest_has_a_stem +1, rest_is_a_barline +1, rest_on_a_dynamic_letter +1). Accidental pairs are overwhelmingly flat vs natural
(natural<-flat 89, flat<-natural 74 of 210): the plate that merges ascenders makes those two the common confusion.
CROSS-cell part (ownership): 6 accidental inks where the non-owner copy owned a head in OFF no longer do; 190 glyphs now carry `owned_by_another_staff`
(184 of them were already abstained for a geometry reason -- only the label changed), 2 `ownership_undecided`. 183 of 200 cross-staff accidental groups
have a decided owner; the owner cell's class differs from the most confident member's in 28 (Litolff) of those; rests: 12 cross-staff groups, 0 differ.
Brahms (census only, from the record's own rows, `cross_cell.py`): accidentals 725 cross-staff groups, 693 owner decided, 222 where the most confident
member is in the other cell, 36 with a different class; rests 141 groups, 139 decided, 54 other-cell, 0 class differences. Brahms merges on p21+p23 live: 127
winners, 148 boxes absorbed. Brahms exported-file OFF/ON: pending the 2.188 command.

## Margin distribution (every merged ink, detector-confidence gap winner minus best rival, Litolff)
accidental n=210: min .001, p10 .021, p25 .077, median .168, p75 .283, p90 .429, max .619; 0.1-bins 65/56/39/25/19/5/1.
rest n=7: .009 .009 .041 .133 .230 .594 .594. Brahms: pending. Nothing is READ at any margin until Sean sets the bar on tiles.

## Limits
Replay applies the merge to stored production boxes (equal to live on 1,537 cells); the 2.172 view boxes are never merged. IoU 0.5 is checked on crops (2.185),
not a convention. Class correctness of the merged winner is NOT confirmed: that is the tiles.

---

# 2.190 -- ACCIDENTAL SHAPE CHECK among the detector's candidates (flag `OMR_ACCIDENTAL_SHAPE`, default OFF; on top of 2.186)
Sean 2026-10-21 "Yes". STAGED GATHER (measurement) + ADJUDICATE (`adjudicate_accidental_owner`). Tools: `benchmarks/omr-accidental-shape-2026-10/`.

## Cause (rule 3)
Sean's 2.186 tiles: of 9 changed notes OFF right 1, ON right 6; every ON error is a NATURAL (tile 2 lost, 6 written sharp, 8 written flat; control 4 sharp in both arms).
Findings, all STAGED GATHER rows of the 20261020-night record on the frozen sample pages, merged exactly as 2.186 merges (`confusion_2_190.py`):
- Merged pairs are overwhelmingly natural-versus-something. Litolff (8 pages) 83 merged inks: flat over natural 33, natural over flat 33, natural over sharp 7, 10 others. Brahms 362: natural over sharp 102, flat over natural 79, natural over flat 55, flat over sharp 50, sharp over natural 41, sharp over flat 19, 16 others.
- The detector-confidence margin does not tell the right winner: median margin about 0.2 on both plates (Brahms p25 .10 / p75 .35), and the inks where the shape reader (below) names the RIVAL have the same margins as those where it agrees (Litolff switch p10/p25/p50/p75/p90 .02/.05/.13/.20/.39 vs agree .03/.09/.18/.31/.45; Brahms .02/.06/.16/.26/.37 vs .03/.10/.24/.37/.45). So no margin cut separates them.
- Tile 2 is NOT a bug. Brahms p25, key signature has Eb. Two boxes on one ink: accidentalFlat .658 and accidentalNatural .610 (margin .048). 2.186 merged to the flat; a flat under a key that already has the flat writes no accidental, so the natural vanished and the note became E-flat. Not `owned_by_another_staff`, not `ownership_undecided`. It is the flat/natural confusion, in its quietest form.
- My own crop look (24 merged inks, ~14 Brahms + 10 Litolff, a model's look and NOT blind: I had seen the detector's answers before reading the Brahms sheet; Sean's tiles are the evidence): on Brahms about 12 of 14 inks read as naturals, and the detector's winner was flat or sharp in about 9 of those 12; Litolff scans are too blobby for me to call. Per pair kind (Brahms): flat-over-natural and sharp-over-natural winners were mostly natural on the print; natural-over-X winners were mostly right.
Process lesson: 2.186 treated "the stronger class by detector confidence" as safe inside a merge, because the detector looked right on a handful of crops. A class decision between two near classes needs a second READER of the ink, and the cut must be measured on the print, not on the confidence. Also: the first shape features (corner ink DENSITY) looked reasonable and failed on sharps (the stems stand at a quarter and three quarters of the width, so a 30% corner caught 20-50% of them); the dump of 1,352 erased crops, not the idea, set the final windows. Check the reader on a population where the answer is known (confident single-class boxes) before using it on the merged ones.

## What was built
- `staged/accidental_shape.py` (pure): `measure` reads the staff-ERASED cell raster inside the glyph's box: drops specks (< 8% of the box's ink), takes the tight ink box, reads two corners as STEM STRENGTH (best 3-column vertical run, as a fraction of the window height): bottom-left (left 45% x bottom 20%) and top-right (right 45% x top 20%). Flat = BL present, TR absent; natural = both absent; sharp = both present; anything else (a corner between the zones, TR present with BL absent, double sharp/flat) = unclear. Cut-offs: present >= 0.60, absent <= 0.25. Measured on the mark's own ink relative to its own box; no staff position is used, so a tilted staff cannot move it (page-facts section 3).
- It is a SECOND READER of the SAME raster the detector read, not an independent source (CLAUDE section 5). It only CHOOSES AMONG the detector's candidates for the ink (the winner and its merged rivals): never a class the detector did not offer. The cut-offs came from crops of two plates, so by CLAUDE section 4 they may only NARROW; nothing is READ on the shape (`SHAPE_READ` is None); whatever it picks is written GUESSED (blue) with both candidates carried.
- GATHER (`gather._accidental_shape_detail`, flag ON only): `detail.shape` {bl, tr, shape, zones, margin} and `detail.position_by_class` (the staff position each offered class anchors at) on the ACCIDENTAL_STAFF_POSITION row. Measurement only. ADJUDICATE (`adjudicate_accidental_owner`): classifies from the filed corner numbers (a cut-off change needs no re-gather); a clear shape naming a RIVAL replaces the confidence winner (alteration, `detector_class`, the anchored position, `one_ink.winner/rivals`, `chosen_by: shape`, `shape_check` on the verdict); unclear/unread, a shape the detector did not offer, or a single class leave the 2.186 result; singles are only recorded.
- Tests `test_staged_accidental_shape_2_190.py` (19): three synthetic glyphs read as themselves; CONTROLS that fail when broken (an upside-down natural is not a natural; whole-glyph windows cannot tell a natural from a sharp; a speck is `unread`); every "chooses" test has a twin (flag OFF, unclear, shape not offered, single class, agrees with winner); the position follows the chosen class; never READ. Also `lane_report --replay-gathered` and `--tag DIR` (see Method).

## Method (how the three measures were taken)
A live gather of the 16+2 sample pages for both arms takes over an hour on a shared box (another lane's gathers ran ahead of mine; 2 Litolff pages took 8 min even with the detector cached). So: `build_slices_2_190.py` takes the stored GATHER rows of the night slices (2.186 checked merge-on-stored == live on 1,537 of 1,537 cells), applies the 2.186 merge, and files the shape rows with the same gather function on the cell rasters `prepare_pages` cuts and staff-erases. Then `lane_report --flag OMR_ONE_INK_ONE_MARK=1:1 --flag OMR_ACCIDENTAL_SHAPE --tag <slices> --from adjudicate --replay-gathered`: BOTH arms have 2.186 ON; the arms differ only in the shape flag. Control: both arms reproduce the night record's duration/rest verdicts 8,958/8,958 (Litolff) and 12,324/12,324 (Brahms). A live gather of these rows is not run: any difference between this replay and a live gather would be in the cell cut, which is the same function.

## The three measures (`benchmarks/omr-accidental-shape-2026-10/lane-report/report.txt` (+ symbols.json of each arm); 2.186-only vs 2.186 + shape)
| plate (8 pages) | exported file, shape ON vs OFF | red bars | judged right->wrong |
|---|---|---|---|
| Litolff | accidentals +15 -1 ~3, pitches ~26 (4 unplaced B-flat eighths carry B natural), blue marks +9 | 266 -> 266 | 0 (254 tiles) |
| Brahms | accidentals +25 -4 ~37, pitches ~78, ties +2 -2, slurs +2, blue marks +24 -2 | 166 -> 166 | 0 (232 tiles) |
Not explained: the ties/slurs on Brahms (a pitch change moves a tie's need; the slurs have no mechanism in this lane) -- the 2.186 report carried the same unexplained movement.
Where the shape had a choice (merged inks with a position row): Litolff 80 -- agrees with the winner 40, names the RIVAL (switch) 30, unclear 7, names a class the detector did not offer 3. Brahms 321 -- agrees 134, switch 85, unclear 58, not offered 44. `table_2_190.py` has it by pair kind. The 47 "not offered" are mostly flat-over-sharp and sharp-over-flat where the shape says NATURAL (Sean's tiles 4 and 8): the detector never offered natural, so by rule 6 they stay as 2.186 left them (blue, wrong). That is the decision for Sean below, not for this lane.
Reader sanity (detector-vs-shape on the confident, un-merged boxes, conf > .75, model vs model, NOT truth): flat boxes read BL ~1.0, TR 0 (p5-p95 .87-1 / 0-.11); natural boxes BL and TR 0 (p90 .33); sharp boxes both ~1 (p5 .82). Un-merged single classes (Brahms): flat 386 of 477 read flat, sharp 176 of 215 read sharp, natural 94 of 161 read natural (42 unclear).

## Sean's 12 tiles of 2.186 (key `out/print/2.186b-accidentals/key.json`), before = 2.186 ON, after = 2.186 + shape
1 sharp: sharp / sharp (unchanged, right). 2 natural: E-flat, accidental lost / natural, blue (FIXED). 3 none directly in front (natural earlier in the bar): none, carried pitch B-sharp / none, carried pitch B-flat (the asked question stays right, but the carried pitch is wrong both ways, since the print says natural earlier -- not investigated). 4 natural: sharp / sharp (still wrong; natural not offered by the detector). 5, 7, 9, 10, 11 natural: natural / natural (right, unchanged). 6 natural: sharp / natural, blue (FIXED). 8 natural: flat / flat (still wrong; natural not offered). 12 natural: natural / natural (control, plain). Right on the asked question: before 8 of 12, after 10 of 12 (the two fixes). Nothing Sean judged goes right->wrong (0 on 486 judged tiles).

## Fresh blind tiles
`out/print/2.190-accidental-shape/tiles/sheet.png` (12 tiles, 9 accidental changes, 3 unchanged accidentals, seed 190, orange box on the note; Sean's earlier tiles excluded), key `out/print/2.190-accidental-shape/key.json` (outside the folder). Question: which accidental is printed directly in front of the boxed note: sharp, flat, natural, or none?

## Limits
The shape reader and the detector read one raster; agreement of the two is not an independent confirmation, only Sean's tiles are. Cut-offs are tuned on two plates and Sean's 12 tiles. The sample is 8 pages a plate; a rare shape may miss it. Not done: Litolff p1-level whole-movement, a live gather.


# 2.193 -- MISSING NATURALS (flag `OMR_NATURAL_CANDIDATE`, default OFF; on top of 2.186 + 2.190, both ON)
Sean 2026-10-22 "Open lanes for both". STAGED GATHER (shared detector) + ADJUDICATE (`adjudicate_accidental_owner`). Tools: `natural_cause_2_193.py` (cause), `natural_crops_2_193.py` (look sheet), `tiles_2_193.py`; data `lane-report-2.193/` (`cause_2_193.json` = every accidental ink of the sample with the raw natural score).

## Cause (rule 3), measured on the raw head tensor
Method: the 20261020-night record's 8+8 sample pages, every cell holding a non-key accidental box; the PRODUCTION detector re-run on each cell (same routed weights, `imgsz_for_cell`, conf 0.25, class-wise NMS 0.7) with the tensor `(4+nc, N)` NMS receives kept. Control that can fail: the live boxes equal the stored record's (Litolff 613 of 613 winner boxes, 80 merged groups = stored 80; Brahms 1719 of 1719, 321 = 321).
- Target inks = the shape reader (2.190) says NATURAL and the detector offered no natural: Litolff 27 (all single boxes), Brahms 74 (27 inside a 2.186 merge, 47 single boxes), total 101. NOT "47": 2.190's "47 not offered" counted every `shape_not_offered` (any shape); the natural-shaped merged ones are Brahms 27, Litolff 0, and 2.190 never counted the 74 SINGLE boxes at all (a single box is never merged, so it never reached `choose`).
- Why natural was absent (per ink, over every anchor whose box overlaps the ink at IoU >= 0.5): natural scored BELOW the 0.25 floor on every anchor in 96 of 101 (Litolff 26/27, Brahms 70/74); 1 Litolff has a natural box surviving nearby at IoU < 0.5; Brahms 3 had a natural best-class anchor >= 0.25 that class-wise NMS removed / did not merge and 1 was beaten by another class on its anchor (argmax). So it is NOT suppression by NMS or by the per-anchor argmax: the natural channel is simply under-scored on these inks (a class-confusion/training matter, not a wiring one).
- How far below: natural score on target inks, Litolff min 0 / p25 .010 / median .026 / p75 .087 / max .171; Brahms p25 .019 / median .056 / p75 .147 / max .357. Controls: inks where the detector offered a natural and the shape agrees: median .76 (Litolff) / .75 (Brahms); inks whose shape reads flat or sharp (no natural offered): median .005 / .003, p90 .074 / .060, p99 .18 / .23.
- My own look (rule 7; a model's look, NOT blind; 32 crops over two sheets, seeds 1 and 7, `natural_crops_2_193.py`): Brahms targets are overwhelmingly printed naturals (about 12 of 16 clearly); Litolff targets are small blobby signs and mostly read as FLATS to me (about 6 of 16 Litolff crops look natural; the rest flat or unreadable), so on Litolff the shape reader's "natural" is not trustworthy and a natural candidate there is the riskiest. Sean's tiles are the evidence.
Process lesson: a count taken from a summary function's reason code ("not offered") is not a count of the thing the reason is named for; and a population defined on the MERGED inks leaves the single boxes unseen. Before opening a lane, re-derive the count from the raw data with a control that can fail (here: live boxes == stored boxes), then look.

## What was built (all behind `OMR_NATURAL_CANDIDATE`, OFF)
- `tools/omr/natural_candidate.py`: the flag, `STORE_FLOOR` 0.01 (what GATHER files), `LOWER_BOUND` 0.05 (what ADJUDICATE accepts), `IOU_MIN` 0.5.
- Detector: `YoloDetector.detect(natural_candidates=True)` (gather passes it only with the flag on) asks `detector_cache.predict(aux=(natural_id, STORE_FLOOR))` for every anchor whose NATURAL score is above the store floor, whatever the anchor's best class is (the standard candidates hold only the argmax class above the floor, so the natural was never in them). The returned detections are unchanged; for each accidental box that is not key* and not itself a natural, `SymbolDetection.natural_score` = best natural score over anchors at IoU >= 0.5 with that box. No box is ever added; an ink with no accidental box gets nothing (the notehead/key/natural boxes are not touched: test).
- Cache: the aux arrays (`nidx/nbox/nscore`) are stored in the same entry under the SAME key. An entry written without them (or at a higher floor) cannot serve it: that call re-reads the page once and rewrites the entry as a superset (a cold read the first time per page, hits afterwards; other lanes' entries stay valid and are only upgraded). The plain path (no cache dir) captures the same tensor.
- GATHER (`_accidental_shape_detail`): files `detail.natural_candidate {conf, alteration, anchor_fraction, position}` on the position row, only when the ink's offered classes hold no natural. ADJUDICATE: the natural joins the candidates `choose` looks at only when `conf >= LOWER_BOUND`; it is taken only if the 2.190 shape reader READS NATURAL (both corners clear-absent); the choice is written one_ink/GUESSED (blue) carrying the natural with its own score and the class it replaced; a natural that is not chosen leaves no trace on the mark. Singles (a flat/sharp drawn alone) are included: that is the larger group.
- Lower bound 0.05, measured not tuned to a target: it is about where fewer than 15% (Litolff) / 12% (Brahms) of non-natural-by-shape inks sit (the natural channel's ordinary noise on a non-natural ink); on the 101 targets it keeps 11 of 27 Litolff and 41 of 74 Brahms. CLAUDE section 4: set on two plates, so it only NARROWS (shape must still say natural; written blue). A change to the bound between STORE_FLOOR and above needs no re-gather. NOT tuned to Sean's tile: see tile 2.186 #4 below (score 0.0499).
- Tests `test_staged_natural_candidate_2_193.py` (13): chooses with natural shape + score; also inside a 2.186 merge; twins: flag OFF, flat shape, unclear shape, score under the bound, no natural score, a natural already offered; detector side: the score comes from an anchor over the same ink only, none from an anchor elsewhere, only accidental flat/sharp boxes get one, and the aux arrays hold an anchor whose argmax is another class while the standard candidates never do. Flag row in `docs/flags-2026-09.md`. `staged.check` 193 = 193 (origin/main).

## The three measures (`lane-report-2.193/report.txt`; `--from gather`, both arms live gathers of the frozen sample, OFF = main with 2.186+2.190 ON)
| plate (8 pages) | exported file, ON vs OFF | red bars | judged right->wrong |
|---|---|---|---|
| Litolff | accidentals +2 ~2, pitches ~5, blue marks +2 (5038 notes/rests paired) | 0 -> 0 (notes not written 2554 -> 2554) | 0 (233 tiles) |
| Brahms | accidentals +8 -3 ~28, ties -2, pitches ~40, blue marks +26 (6519 paired) | 166 -> 166 | 0 (232 tiles) |
Not explained: the 2 ties on Brahms (a pitch change moves a tie's need; no mechanism in this lane), the same as in 2.186/2.190. Lane report control "OFF == record" cannot run in gather mode (no saved verdicts); the cause control above (live == stored boxes) covers it. Wall time 10,861 s for both arms of both plates on a shared box.

## Sean's four earlier tiles (the natural the detector never offered), before = 2.190 ON, after = + 2.193
- 2.186 #8 (Brahms p4, printed natural, was flat + A-14): now NATURAL, pitch A4, blue. FIXED.
- 2.186 #4 (Brahms p25, printed natural, was sharp): UNCHANGED (sharp, blue). The ink's natural score is 0.0499, 0.0001 under the 0.05 bound; the bound is NOT moved to catch it (rule 5/7: a cut-off set to catch a tile is tuning on the test).
- 2.190 #6 (Brahms p19, printed natural, was flat): UNCHANGED (flat, blue): here the shape reader itself reads FLAT (bl .91, tr 0), a shape error, not a missing candidate; natural score 0.055.
- 2.190 #9 (Brahms p12, a note whose sharp was lost): UNCHANGED: the ink is natural-shaped but no anchor scored a natural >= 0.01 at all, so there is no candidate.
So 1 of 4 fixed; the other 3 name the limits (a bound on the edge, the shape reader's own error, a natural with no score at all).

## Fresh blind tiles
`out/print/2.193-missing-naturals/tiles/sheet.png` (12 tiles: 9 accidental changes drawn in proportion to the changes, Brahms 8 / Litolff 1, + 3 unchanged controls; one note per tile; orange box on the note; Sean's earlier accidental tiles 2.186b and 2.190 excluded; seed 193), key `out/print/2.193-missing-naturals/key.json` (outside the tile folder). Question: which accidental is printed directly in front of the boxed note: sharp, flat, natural, or none?

## Limits
The natural score and the shape reader are one detector, one raster: not independent. The Litolff effect is small (4 accidental changes) and my look doubts it. The bound 0.05 is on the edge for at least one of Sean's tiles. A natural with no score at all (tile #9) needs a different source (training, not wiring). No default flipped.
