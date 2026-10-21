# 2.182a -- rest pairs refused as a different-class duplicate (STAGED, ADJUDICATE)

Question: the parked 2.182 reported "58 rests / 28 cells refused as a DIFFERENT-class pair" from one agent's look at 5 hand-picked Brahms
pages. Rule 7: recount before it opens a lane.

## Mechanism (read from code)
STAGED `adjudicators/family_precision._duplicate_box_refusal` (2.15): two rest boxes in one cell with IoU >= REST_DUPLICATE_IOU_MIN. Same
class: one survivor, the other refused. Different class: BOTH refused (rule 8). Verdict `rest_is_not_a_rest` = True, reason
`rest_is_a_duplicate_box`, `detail.duplicate_disagrees_with` = the other box's obs ids (same-class carries `detail.duplicate_of` instead).

## Count (records: library/_shared-records/{beethoven5-litolff,brahms1-breitkopf}-mvt1-whole-20261020-night.record.json, whole movement, live verdicts only)
Cluster = boxes linked by disagreement (one ink). All 98 clusters have every member refused. `rest_is_a_duplicate_box` same-class refusals
(not counted below, a control): Litolff 86, Brahms 683.

| plate | boxes refused | clusters (inks) |
|---|---|---|
| Litolff | 20 | 10 |
| Brahms | 184 | 88 |
| both | 204 | 98 |

Class pairs, clusters: Brahms 8th+16th 39, 8th+quarter 32, 16th+32nd 3, 8th+8th+quarter 3, 16th+8th+quarter 2, 8th+whole 2, and 1 each
half+quarter, HBar+HBar+whole+whole, 8th+HBar, 16th+8th+8th, HBar+whole, quarter+whole, 16th+quarter. Litolff: 16th+32nd 3, 16th+8th 2,
quarter+whole 2, half+quarter 1, half+whole 1, 8th+quarter 1.
So the earlier 58 / 28 is the right order for ONE slice of Brahms 8th-vs-16th/quarter (71 clusters, 8th/16th/quarter pairs only) but the
whole-movement figure is ~3.5x it; neither is a count of readable rests until Sean looks at the tiles.

## Tiles (Sean's blind check)
out/print/2.182a-rest-pairs/tile_01..12.png, README.md there. 9 cases drawn at random with `random.Random(2182)` from the 98 clusters (both
plates pooled, sorted by doc then glyph id before sampling), 3 controls (single-box rests the reader kept, one each rest8th/rest16th/
restQuarter, no other rest box in the cell, same RNG), shuffled. One blue box each (union of the cluster's boxes +4 px). KEY (not in the
tiles folder): out/print/2.182a-key.json -- tile, kind, doc, page, glyph ids, both detector classes and confidences.
Scripts: extract.py (stream a record, ijson), count.py, tiles_2_182a.py.

## Sean's tiles (answered 2026-10-21)
Verbatim: "1. 8 rest 2. tip of an 8th stem 3.8 rest 4. 4 rest 5. 8 rest 6. 8 rest 7.8 rest 8. 4 rest 9. part of a barline and ff 10-12. 8 rest".
Recorded in out/print/2.182a-rest-pairs/answers.json (per tile: Sean's answer, key kind, detector classes and confidences).

n=9 cases, one random draw (seed 2182). 7 of 9 are real rests: 6 eighths (tiles 3, 5, 6, 10, 11, 12) and 1 quarter (tile 4). 2 are NOT
rests: tile 2 (tip of an 8th stem; boxed rest16th 0.436 > rest8th 0.35) and tile 9 (part of a barline and ff; boxed rest32nd 0.548 >
rest16th 0.454).
If the higher-confidence class were taken it would be right on 6 of the 7 real rests (3, 4, 6, 10, 11, 12) and wrong on tile 5 (restQuarter
0.663 > rest8th 0.256, Sean: 8 rest), and it would invent a rest on tiles 2 and 9.
Controls: tile 7 (rest8th 0.575) and tile 8 (restQuarter 0.45) right; tile 1, kept as a single rest16th 0.598, is an EIGHTH rest per Sean --
a kept rest with the wrong value.
Reading: the refusal of a different-class pair on one ink throws away real rests (7 of 9, 6 of them eighths), so the loss is real; but the
two non-rests show the pair cannot simply take the stronger class.

# 2.184 -- why a clean rest gets two classes (STAGED GATHER; Part 1 diagnosis, Part 2 built OFF and NOT measured)

Scripts: extract184.py, cause184.py, slices_2_184.py, replay_2_184.py, tiles_2_184.py here; probe/2.184/{replay,analyse,features,pagescan}.py. Records 20261018-night and
20261020-night, both plates. Sean's question: why can we read these well elsewhere and not here?

## Mechanism (counted, not asserted)
Every one of the 98 pair inks (Litolff 10, Brahms 88) is made of 2-4 boxes of reader `detector` -- the PRODUCTION pass on ONE bar crop.
| question | answer |
|---|---|
| a box from a 2.172 view / re-read (`yolo_detector_view`, `yolo_rescue_lowconf`) | 0 of 98 (of 741 Brahms view rest boxes none is in a pair) |
| both boxes in ONE cell (same-cell class-wise NMS) | 98 of 98 |
| a second rest box of ANOTHER cell on the same ink (lane 2.185's cross-cell overlap) | 1 of 98 (Brahms), incidental; the pair itself is within one cell |
| present before the views (20261018-night) | 97 of 98 at the same ink, same classes; the 98th (Brahms p22, 32nd+16th) is production boxes in the later run only (floor noise) |
Cause: `YoloDetector.detect` is called with class-wise NMS (`agnostic_nms=False`, documented at `gather.py` ~386-410): each class channel is scored
independently, so an ink whose 8th AND 16th (or quarter) channel both clear the 0.25 floor keeps both boxes, and `_duplicate_box_refusal`
(rule 8) refuses both. Reproduced from the code, not the record: re-running the production detector (same weights, `imgsz_for_cell`) on Litolff p4/7/16 and
Brahms p6/20/21/23/24/26 gives the record's pairs 6 of 6 and 63 of 63, and the same run with `agnostic_nms=True` leaves 2 of 6 (Litolff) and 5 of 71 (Brahms).
So the answer to "views or merge" is: not the views; the class-wise NMS, which is the merge. Cross-cell overlap (2.185) is a separate doubling and does not make these pairs.

## Why "elsewhere" reads: it is the same reading, the 0.25 floor decides
Brahms replay pages, per production rest ink: 8th-class inks 1,272; rival class >= 0.25: 65 (pairs); rival in [0.05, 0.25): 131 (silent, under the floor); none: 1,076.
Pair top-class conf median 0.64 vs 0.71 for singles. Not explained by: staff space shown to the net (pair rate 2-6% flat over 15-17.5 px), box height/width in spaces
(1.96 vs 1.94 h, 1.18 vs 1.18 w), vertical position, imgsz. By page it is lumpy: p21 21.8%, p23 10.5%, p26 9.8% of 8th-class inks vs ~0-3% on most pages; not tracked by
staff-line thickness (p6, p22 thick, 2.7% and 4.9%). Unexplained remainder: WHY those pages' rests (not scan weight alone). Crops (page 21, 18 pair vs 18 single
inks, `/tmp` sheets): the same Breitkopf ball-and-stroke eighth rest, clean, no visible difference to the eye -- it is the detector's score split, not the page.
Corollary seen once (2.182a tile 1): a KEPT single box can carry the wrong class silently (rest16th 0.598, Sean: 8th rest).

## Part 2 (built before the coordinator's stop; OFF, unmeasured)
`OMR_REST_PAIR_STRONGER_BLUE` (default OFF) in `family_precision` (`_rest_pair_outcome`, `_rest_pair_narrowing`) + `export.rest_pair_guess_of`: the stronger box continues through every later rest rule
(stem, barline, letter cover, width floor ... a refused winner leaves the ink refused) and ends NARROWED `rest_pair_stronger`, written GUESSED with both classes and the
confidence gap; the weaker is refused as a duplicate. 9 tests pass (`test_staged_rest_pair_blue_2_184.py`). The replay (OFF control 2969/2969 on Litolff) was stopped
mid-run; OFF vs ON on the exported file and the 12 tiles are NOT done (tiles_2_184.py written, not run). Stopped for Sean: if class-wise NMS is the one place to fix for all
families (2.185: 718 Brahms accidentals dropped the same way), a merge fix may replace this blue rule.
