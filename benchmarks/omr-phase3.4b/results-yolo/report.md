# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **22**
- Total detections in scored cells: 566
- Pending (not yet verdict'd): 327

## Overall

- TP (right location): **237**
- FP: **2**
- FN (missed noteheads): **5**
- Precision: **99.2%**
- Recall: **97.9%**
- F1: **98.5%**
- Notehead pitch accuracy (of correctly-located noteheads): **96.9%** (221 / 228)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 1 | 0 | 42 | 100.0% |
| clef | 0 | 0 | 7 | — |
| dynamic | 0 | 0 | 5 | — |
| flag | 3 | 0 | 4 | 100.0% |
| notehead | 228 | 2 | 39 | 99.1% |
| ornament | 0 | 0 | 4 | — |
| rest | 5 | 0 | 21 | 100.0% |
| structural | 0 | 0 | 202 | — |
| time_sig_digit | 0 | 0 | 3 | — |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| beet5-p10 | 2 | 2 | 0 | 3 | 100.0% | 40.0% | 57.1% |
| wtc-p10 | 5 | 30 | 2 | 0 | 93.8% | 100.0% | 96.8% |
| wtc-p5 | 15 | 205 | 0 | 2 | 100.0% | 99.0% | 99.5% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| beet5-p10-sys0-s1-m1 | 1 | 0 | 2 | 8 | 100.0% | 33.3% | 50.0% | 100.0% |
| beet5-p10-sys0-s1-m2 | 1 | 0 | 1 | 7 | 100.0% | 50.0% | 66.7% | 0.0% |
| wtc-p10-sys0-s0-m0 | 6 | 2 | 0 | 25 | 75.0% | 100.0% | 85.7% | 100.0% |
| wtc-p10-sys0-s0-m1 | 6 | 0 | 0 | 11 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m2 | 6 | 0 | 0 | 6 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m3 | 6 | 0 | 0 | 15 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m4 | 6 | 0 | 0 | 8 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m0 | 9 | 0 | 0 | 14 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 0 | 0 | 13 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 0 | 0 | 23 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m0 | 10 | 0 | 0 | 11 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m1 | 14 | 0 | 0 | 17 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s1-m2 | 15 | 0 | 1 | 13 | 100.0% | 93.8% | 96.8% | 92.9% |
| wtc-p5-sys1-s2-m0 | 21 | 0 | 0 | 21 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m1 | 19 | 0 | 0 | 22 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s2-m2 | 4 | 0 | 0 | 15 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys1-s3-m0 | 14 | 0 | 0 | 13 | 100.0% | 100.0% | 100.0% | 85.7% |
| wtc-p5-sys1-s3-m1 | 16 | 0 | 0 | 23 | 100.0% | 100.0% | 100.0% | 86.7% |
| wtc-p5-sys1-s3-m2 | 2 | 0 | 0 | 8 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m0 | 16 | 0 | 1 | 26 | 100.0% | 94.1% | 97.0% | 92.9% |
| wtc-p5-sys2-s4-m1 | 14 | 0 | 0 | 13 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m2 | 19 | 0 | 0 | 15 | 100.0% | 100.0% | 100.0% | 100.0% |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (2 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
