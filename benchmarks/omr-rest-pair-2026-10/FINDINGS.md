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
