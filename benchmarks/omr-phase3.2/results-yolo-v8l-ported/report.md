# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **24**
- Total detections in scored cells: 997
- Pending (not yet verdict'd): 757

## Overall

- TP (right location): **232**
- FP: **8**
- FN (missed noteheads): **10**
- Precision: **96.7%**
- Recall: **95.9%**
- F1: **96.3%**
- Notehead pitch accuracy (of correctly-located noteheads): **96.4%** (216 / 224)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 1 | 0 | 25 | 100.0% |
| clef | 0 | 0 | 8 | — |
| dynamic | 0 | 0 | 3 | — |
| flag | 2 | 0 | 6 | 100.0% |
| notehead | 224 | 8 | 373 | 96.6% |
| ornament | 0 | 0 | 7 | — |
| rest | 5 | 0 | 118 | 100.0% |
| stem | 0 | 0 | 1 | — |
| structural | 0 | 0 | 216 | — |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| beet5-p10 | 4 | 4 | 7 | 1 | 36.4% | 80.0% | 50.0% |
| wtc-p10 | 5 | 27 | 1 | 3 | 96.4% | 90.0% | 93.1% |
| wtc-p5 | 15 | 201 | 0 | 6 | 100.0% | 97.1% | 98.5% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| beet5-p10-sys0-s1-m0 | 0 | 3 | 0 | 18 | 0.0% | — | — | — |
| beet5-p10-sys0-s1-m1 | 2 | 0 | 1 | 185 | 100.0% | 66.7% | 80.0% | 50.0% |
| beet5-p10-sys0-s1-m2 | 2 | 3 | 0 | 121 | 40.0% | 100.0% | 57.1% | 50.0% |
| beet5-p10-sys0-s1-m3 | 0 | 1 | 0 | 79 | 0.0% | — | — | — |
| wtc-p10-sys0-s0-m0 | 6 | 1 | 0 | 21 | 85.7% | 100.0% | 92.3% | 100.0% |
| wtc-p10-sys0-s0-m1 | 6 | 0 | 0 | 18 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m2 | 4 | 0 | 2 | 14 | 100.0% | 66.7% | 80.0% | 100.0% |
| wtc-p10-sys0-s0-m3 | 6 | 0 | 0 | 36 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m4 | 5 | 0 | 1 | 22 | 100.0% | 83.3% | 90.9% | 100.0% |
| wtc-p5-sys0-s0-m0 | 9 | 0 | 0 | 12 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 0 | 0 | 15 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 0 | 0 | 25 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m0 | 9 | 0 | 1 | 16 | 100.0% | 90.0% | 94.7% | 100.0% |
| wtc-p5-sys0-s1-m1 | 14 | 0 | 0 | 19 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m2 | 15 | 0 | 1 | 12 | 100.0% | 93.8% | 96.8% | 92.9% |
| wtc-p5-sys1-s2-m0 | 21 | 0 | 0 | 21 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m1 | 19 | 0 | 0 | 18 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m2 | 1 | 0 | 3 | 7 | 100.0% | 25.0% | 40.0% | 100.0% |
| wtc-p5-sys1-s3-m0 | 14 | 0 | 0 | 15 | 100.0% | 100.0% | 100.0% | 85.7% |
| wtc-p5-sys1-s3-m1 | 16 | 0 | 0 | 19 | 100.0% | 100.0% | 100.0% | 86.7% |
| wtc-p5-sys1-s3-m2 | 2 | 0 | 0 | 3 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m0 | 16 | 0 | 1 | 27 | 100.0% | 94.1% | 97.0% | 92.9% |
| wtc-p5-sys2-s4-m1 | 14 | 0 | 0 | 13 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m2 | 19 | 0 | 0 | 21 | 100.0% | 100.0% | 100.0% | 100.0% |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (8 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
