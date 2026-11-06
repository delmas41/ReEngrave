# Verdict rule, written BEFORE any arc number was computed (2026-11-06)

Question: does the SAME production detector (weights routed by `--weights auto`, per-crop `imgsz_for_cell` = 16 px per staff space, conf 0.25, staff
lines intact, `one_ink.merge` after) box the far half of an arc that a per-cell crop cuts at a barline, when given a crop that straddles the barline
(B: half a bar each side; B2: one bar each side) or the whole staff row of the system (C)?

Population: the cut test's barline-crossing REAL arcs (branch `arc-barline-cut-test`, ef226deba: ledger fate != not_an_arc, box cut at a PRINTED barline).
A right-cut box + a left-cut box across one barline is one item. Pages: Litolff 2,4,6,8,9,10,11,16; Brahms 0,5.

"Boxes the far half" of item K by arm X: a tie/slur box M of X overlaps K in y (>= 0.5 of the shorter), reaches back over at least half of K, and
extends >= 0.75 sp past the barline on the far side. "Whole": M also reaches K's far end (and a pair's partner far end) within 0.5 sp.

WORTH BUILDING: B or C boxes the far half of >= 2/3 of the cut items on BOTH plates, AND new false arc boxes < 5 per page, AND no loss on uncut arcs.
NOT WORTH IT: fewer than 1/3 on either plate.   Between: mixed (reported, not decided).

Control (must be able to fail): arm A re-detected cell by cell must reproduce the saved record's arc boxes (IoU >= 0.9, same class) on the page;
the same cells re-run at a wrong imgsz (1024) must NOT reproduce them.
New false arc box: a tie/slur box of X that overlaps no arc box of the record (IoU < 0.3 and < 50% inside either) and is not a far-half box of a cut item.
Upper bound until judged on the page map (record glyph box under it) and a crop look at a sample.

# RESULT (2026-11-06): MIXED, not WORTH BUILDING as the rule is written

Numbers: results/summary.txt. Crops (12 on cut arcs, 20 on new boxes): out/print/arc-barline-crop-trial/ (local, not committed).

Control reproduced: arm A re-detected cell by cell gives 1330/1330 (Litolff) and 1085/1085 (Brahms) of the saved record arc boxes at IoU>=.9; at imgsz 1024 it gives 0/18 and 3/160.
Far half boxed (all cut items, Litolff / Brahms): A alone 8% / 25%. B (half bar each side) 55% / 71%. B2 (one bar each side) 66% / 73%. C (staff row, same 16 px per space via explicit imgsz) 75% / 80%.
Rule: C clears 2/3 on both plates; B does not on Litolff. But new arc boxes (no record arc under them): C 29 / 16 per page, B 30 / 82. A look at 20 sampled new boxes: about 30% are real arcs A missed, the rest sit on staff lines, beams, rests, heads. False boxes are about 10-20 per page, over the limit of 5. C also finds only 72% / 89% of the uncut arcs A finds (IoU .5): a supplement, not a replacement.
Crop look (12): most C boxes sit whole on the arc across the barline; B boxes often stop short of the far end; one C box (Brahms p5) is over-wide (three bars). Cost: C 6.6 / 7.7 s per page vs A 16.7 / 12.7 s. max_det raised to 3000 for C and B2 only (C strips reached 230 boxes; no A or B call reached 300).
