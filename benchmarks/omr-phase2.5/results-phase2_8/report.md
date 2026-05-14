# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **25**
- Total detections in scored cells: 265
- Pending (not yet verdict'd): 3

## Overall

- TP (right location): **242**
- FP: **20**
- FN (missed noteheads): **0**
- Precision: **92.4%**
- Recall: **100.0%**
- F1: **96.0%**
- Notehead pitch accuracy (of correctly-located noteheads): **96.5%** (223 / 231)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 1 | 1 | 0 | 50.0% |
| flag | 5 | 0 | 0 | 100.0% |
| notehead | 231 | 19 | 3 | 92.4% |
| rest | 5 | 0 | 0 | 100.0% |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| beet5-p10 | 5 | 5 | 12 | 0 | 29.4% | 100.0% | 45.5% |
| wtc-p10 | 5 | 30 | 3 | 0 | 90.9% | 100.0% | 95.2% |
| wtc-p5 | 15 | 207 | 5 | 0 | 97.6% | 100.0% | 98.8% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| beet5-p10-sys0-s0-m0 | 0 | 1 | 0 | 0 | 0.0% | — | — | — |
| beet5-p10-sys0-s1-m0 | 0 | 6 | 0 | 0 | 0.0% | — | — | — |
| beet5-p10-sys0-s1-m1 | 3 | 1 | 0 | 0 | 75.0% | 100.0% | 85.7% | 66.7% |
| beet5-p10-sys0-s1-m2 | 2 | 3 | 0 | 2 | 40.0% | 100.0% | 57.1% | 50.0% |
| beet5-p10-sys0-s1-m3 | 0 | 1 | 0 | 0 | 0.0% | — | — | — |
| wtc-p10-sys0-s0-m0 | 6 | 3 | 0 | 0 | 66.7% | 100.0% | 80.0% | 100.0% |
| wtc-p10-sys0-s0-m1 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m2 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m3 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m4 | 6 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m0 | 9 | 1 | 0 | 0 | 90.0% | 100.0% | 94.7% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m0 | 10 | 1 | 0 | 0 | 90.9% | 100.0% | 95.2% | 100.0% |
| wtc-p5-sys0-s1-m1 | 14 | 0 | 0 | 1 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m2 | 16 | 1 | 0 | 0 | 94.1% | 100.0% | 97.0% | 92.9% |
| wtc-p5-sys1-s2-m0 | 21 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m1 | 19 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m2 | 4 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s3-m0 | 14 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 85.7% |
| wtc-p5-sys1-s3-m1 | 16 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 86.7% |
| wtc-p5-sys1-s3-m2 | 2 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m0 | 17 | 1 | 0 | 0 | 94.4% | 100.0% | 97.1% | 92.9% |
| wtc-p5-sys2-s4-m1 | 14 | 1 | 0 | 0 | 93.3% | 100.0% | 96.6% | 100.0% |
| wtc-p5-sys2-s4-m2 | 19 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (20 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
