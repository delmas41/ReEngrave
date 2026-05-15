# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **22**
- Total detections in scored cells: 500
- Pending (not yet verdict'd): 294

## Overall

- TP (right location): **205**
- FP: **1**
- FN (missed noteheads): **37**
- Precision: **99.5%**
- Recall: **84.7%**
- F1: **91.5%**
- Notehead pitch accuracy (of correctly-located noteheads): **96.4%** (190 / 197)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 1 | 0 | 18 | 100.0% |
| clef | 0 | 0 | 10 | — |
| dynamic | 0 | 0 | 1 | — |
| flag | 2 | 0 | 5 | 100.0% |
| notehead | 197 | 1 | 45 | 99.5% |
| ornament | 0 | 0 | 4 | — |
| rest | 5 | 0 | 18 | 100.0% |
| structural | 0 | 0 | 193 | — |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| beet5-p10 | 2 | 1 | 0 | 4 | 100.0% | 20.0% | 33.3% |
| wtc-p10 | 5 | 6 | 1 | 24 | 85.7% | 20.0% | 32.4% |
| wtc-p5 | 15 | 198 | 0 | 9 | 100.0% | 95.7% | 97.8% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| beet5-p10-sys0-s1-m1 | 0 | 0 | 3 | 10 | — | 0.0% | — | — |
| beet5-p10-sys0-s1-m2 | 1 | 0 | 1 | 26 | 100.0% | 50.0% | 66.7% | 0.0% |
| wtc-p10-sys0-s0-m0 | 6 | 1 | 0 | 14 | 85.7% | 100.0% | 92.3% | 100.0% |
| wtc-p10-sys0-s0-m1 | 0 | 0 | 6 | 10 | — | 0.0% | — | — |
| wtc-p10-sys0-s0-m2 | 0 | 0 | 6 | 7 | — | 0.0% | — | — |
| wtc-p10-sys0-s0-m3 | 0 | 0 | 6 | 11 | — | 0.0% | — | — |
| wtc-p10-sys0-s0-m4 | 0 | 0 | 6 | 8 | — | 0.0% | — | — |
| wtc-p5-sys0-s0-m0 | 9 | 0 | 0 | 11 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 0 | 0 | 10 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 0 | 0 | 21 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m0 | 9 | 0 | 1 | 10 | 100.0% | 90.0% | 94.7% | 100.0% |
| wtc-p5-sys0-s1-m1 | 14 | 0 | 0 | 15 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m2 | 15 | 0 | 1 | 13 | 100.0% | 93.8% | 96.8% | 92.9% |
| wtc-p5-sys1-s2-m0 | 21 | 0 | 0 | 20 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m1 | 19 | 0 | 0 | 17 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m2 | 0 | 0 | 4 | 5 | — | 0.0% | — | — |
| wtc-p5-sys1-s3-m0 | 14 | 0 | 0 | 14 | 100.0% | 100.0% | 100.0% | 85.7% |
| wtc-p5-sys1-s3-m1 | 16 | 0 | 0 | 18 | 100.0% | 100.0% | 100.0% | 86.7% |
| wtc-p5-sys1-s3-m2 | 0 | 0 | 2 | 3 | — | 0.0% | — | — |
| wtc-p5-sys2-s4-m0 | 16 | 0 | 1 | 24 | 100.0% | 94.1% | 97.0% | 92.9% |
| wtc-p5-sys2-s4-m1 | 14 | 0 | 0 | 11 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m2 | 19 | 0 | 0 | 16 | 100.0% | 100.0% | 100.0% | 100.0% |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (1 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
