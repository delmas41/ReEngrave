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

## Measured (Litolff whole-movement replay, run before Sean's three-things rule; Brahms replay NOT run to the end: stopped on the coordinator's instruction)
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
