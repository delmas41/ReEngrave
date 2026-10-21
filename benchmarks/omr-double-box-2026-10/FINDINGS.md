# 2.185 — double boxing census, all classes (Sean 2026-10-21)

Read-only. 20261020-night whole-movement records, both plates; "double" = two or more detector boxes on one ink at IoU >= 0.5
(20/20 uniform random crops real doubles; band 0.3-0.5 4/8 real per plate; below 0.3 mostly neighbours). Scripts here; crops
`out/print/2.185-double-box/` (own checks, NOT Sean's answers). Lane report reproduced below by the manager (the lane's Write was refused).

## Cause (rule 3)
Production runs the detector once per CELL crop with class-wise NMS (`iou=0.7`, `agnostic_nms=False`). Neighbouring staves' cell
rectangles overlap, so one ink is boxed once per cell (99.5% of cross-staff pairs: each box inside the other staff's cell), and
class-wise NMS keeps two classes on one ink. Most doubles are already resolved downstream; the HARM is where the two boxes differ
in class and the later rule refuses both (heads, rests) or keeps both and cannot choose (accidentals, flags) -- there is no
duplicate rule for accidentals, flags, dynamics, arcs or beams.
Process lesson: a raw double count looks alarming and is mostly the pipeline already working; harm appears only by following each
group to the exported file and looking at crops.

## Size
| | Litolff | Brahms |
|---|---:|---:|
| boxes in doubles | 11,639 / 37,698 (30.9%) | 40,107 / 100,535 (39.9%) |
| inks | 5,315 | 18,034 |
Causes (inks): cross-staff cell overlap 2,993 / 12,270; same cell different class 876 / 2,816; same cell same class IoU .5-.7
1,252 / 2,437; views (2.172) + stem-end (2.179) passes 34+67 / 301+23; unexplained (same cell same class IoU >= .7) 36 / 62.
Before vs after 2.172: production doubles unchanged (20261018 vs 20261020); views add 34 / 301 inks, recover real rests but leave
the weaker wrong-class production box beside them.

## Harm in the exported file
| harm | Litolff | Brahms |
|---|---|---|
| printed accidental dropped: two accidental boxes of different class own one head, `apply_printed_accidental` writes nothing (export `heads_contradicted`) | 74 heads | 740 heads |
| phantom accidental on an eighth-rest bulb kept, alters next note (8/8 Brahms crops wrong) | 9 | 47 |
| real heads refused as duplicates (~half of dup-refused inks real, 10 crops each) | ~24 of 44 | ~5 of 15 |
| eighth rests refused as a different-class pair (2.182a/2.184) | 10 | 88 |
| flag8th + flag16th both kept on one stem (7/7 readable crops one flag; value effect not traced) | 3 | 76 |
| note or rest written twice | 0 | 0 |

**Manager check (2026-10-21):** the 74/740 equal the exporter's own `heads_contradicted` counter, so they were a computation, not
an independent measurement (rule 7). Recomputed the box overlap of each contradicted head's owners from the extracts: Litolff 71 of
74 same ink (IoU >= .5), 3 separate marks; Brahms 718 of 740 same ink, 5 touching, 17 separate. 10 crops
(`t_bra_acc_diff_head_sheet.png`): all clear, uncrowded naturals/flats.

Limits: "real symbols lost" from 10-crop looks, not Sean; dynamics and accidental carry not traced into the file; IoU 0.5 a cut
checked on crops, not a convention; Brahms file-level figures from the exporter's census (export not re-run).

**Correction (manager, 2026-10-21, after 2.184):** the HARMFUL doubles are NOT the cross-cell overlap. All 74 / 740 contradicted
accidentals have both boxes from reader `detector` in ONE crop (same glyph page/system/cell/staff prefix), and 2.184 traced all 98
rest pairs to one crop too and reproduced them (6/6, 63/63) by re-running the detector; `agnostic_nms=True` cuts rest pairs 71 -> 5
Brahms, 6 -> 2 Litolff. Cause of the harm: class-wise NMS (`agnostic_nms=False`) in the production pass keeps two classes on one ink.
Cross-cell overlap is the bulk of doubles and is resolved downstream.
