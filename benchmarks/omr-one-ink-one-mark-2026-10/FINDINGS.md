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
