# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **25**
- Total detections in scored cells: 276
- Pending (not yet verdict'd): 3

## Overall

- TP (right location): **244**
- FP: **29**
- FN (missed noteheads): **0**
- Precision: **89.4%**
- Recall: **100.0%**
- F1: **94.4%**
- Notehead pitch accuracy (of correctly-located noteheads): **96.6%** (225 / 233)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 1 | 1 | 0 | 50.0% |
| flag | 5 | 6 | 0 | 45.5% |
| notehead | 233 | 22 | 3 | 91.4% |
| rest | 5 | 0 | 0 | 100.0% |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| beet5-p10 | 5 | 5 | 15 | 0 | 25.0% | 100.0% | 40.0% |
| wtc-p10 | 5 | 30 | 8 | 0 | 78.9% | 100.0% | 88.2% |
| wtc-p5 | 15 | 209 | 6 | 0 | 97.2% | 100.0% | 98.6% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| beet5-p10-sys0-s0-m0 | 0 | 1 | 0 | 0 | 0.0% | — | — | — |
| beet5-p10-sys0-s1-m0 | 0 | 7 | 0 | 0 | 0.0% | — | — | — |
| beet5-p10-sys0-s1-m1 | 3 | 3 | 0 | 0 | 50.0% | 100.0% | 66.7% | 66.7% |
| beet5-p10-sys0-s1-m2 | 2 | 3 | 0 | 2 | 40.0% | 100.0% | 57.1% | 50.0% |
| beet5-p10-sys0-s1-m3 | 0 | 1 | 0 | 0 | 0.0% | — | — | — |
| wtc-p10-sys0-s0-m0 | 6 | 7 | 0 | 0 | 46.2% | 100.0% | 63.2% | 100.0% |
| wtc-p10-sys0-s0-m1 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m2 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m3 | 6 | 1 | 0 | 0 | 85.7% | 100.0% | 92.3% | 100.0% |
| wtc-p10-sys0-s0-m4 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m0 | 9 | 1 | 0 | 0 | 90.0% | 100.0% | 94.7% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m0 | 10 | 1 | 0 | 0 | 90.9% | 100.0% | 95.2% | 100.0% |
| wtc-p5-sys0-s1-m1 | 14 | 0 | 0 | 1 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m2 | 16 | 2 | 0 | 0 | 88.9% | 100.0% | 94.1% | 92.9% |
| wtc-p5-sys1-s2-m0 | 21 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m1 | 19 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m2 | 4 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s3-m0 | 15 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 86.7% |
| wtc-p5-sys1-s3-m1 | 17 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 87.5% |
| wtc-p5-sys1-s3-m2 | 2 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m0 | 17 | 1 | 0 | 0 | 94.4% | 100.0% | 97.1% | 92.9% |
| wtc-p5-sys2-s4-m1 | 14 | 1 | 0 | 0 | 93.3% | 100.0% | 96.6% | 100.0% |
| wtc-p5-sys2-s4-m2 | 19 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (12 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|
| noteheadBlack | dynamicForte | 4 |
| noteheadBlack | restWhole | 3 |
| flag16thDown | V in vivace | 2 |
| noteheadBlack | restQuarter | 2 |
| noteheadWhole | time signature 3/8 | 2 |
| flag16thDown | d in dim. | 1 |
| flag16thDown | tempo bpm 2 in 92 | 1 |
| flag8thUp | bracket for tempo marking | 1 |
| noteheadBlack | quarter note tempo marking | 1 |

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
