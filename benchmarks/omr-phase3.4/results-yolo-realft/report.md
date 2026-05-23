# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **22**
- Total detections in scored cells: 226
- Pending (not yet verdict'd): 67

## Overall

- TP (right location): **159**
- FP: **0**
- FN (missed noteheads): **83**
- Precision: **100.0%**
- Recall: **65.7%**
- F1: **79.3%**
- Notehead pitch accuracy (of correctly-located noteheads): **96.8%** (149 / 154)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 0 | 0 | 9 | — |
| dynamic | 0 | 0 | 4 | — |
| notehead | 154 | 0 | 30 | 100.0% |
| rest | 5 | 0 | 14 | 100.0% |
| structural | 0 | 0 | 10 | — |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| beet5-p10 | 2 | 3 | 0 | 2 | 100.0% | 60.0% | 75.0% |
| wtc-p10 | 5 | 28 | 0 | 2 | 100.0% | 93.3% | 96.6% |
| wtc-p5 | 15 | 128 | 0 | 79 | 100.0% | 61.8% | 76.4% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| beet5-p10-sys0-s1-m1 | 1 | 0 | 2 | 14 | 100.0% | 33.3% | 50.0% | 100.0% |
| beet5-p10-sys0-s1-m2 | 2 | 0 | 0 | 4 | 100.0% | 100.0% | 100.0% | 50.0% |
| wtc-p10-sys0-s0-m0 | 6 | 0 | 0 | 2 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m1 | 6 | 0 | 0 | 4 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m2 | 5 | 0 | 1 | 0 | 100.0% | 83.3% | 90.9% | 100.0% |
| wtc-p10-sys0-s0-m3 | 6 | 0 | 0 | 8 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p10-sys0-s0-m4 | 5 | 0 | 1 | 0 | 100.0% | 83.3% | 90.9% | 100.0% |
| wtc-p5-sys0-s0-m0 | 5 | 0 | 4 | 2 | 100.0% | 55.6% | 71.4% | 100.0% |
| wtc-p5-sys0-s0-m1 | 11 | 0 | 3 | 3 | 100.0% | 78.6% | 88.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 14 | 0 | 4 | 3 | 100.0% | 77.8% | 87.5% | 100.0% |
| wtc-p5-sys0-s1-m0 | 7 | 0 | 3 | 1 | 100.0% | 70.0% | 82.4% | 100.0% |
| wtc-p5-sys0-s1-m1 | 12 | 0 | 2 | 2 | 100.0% | 85.7% | 92.3% | 100.0% |
| wtc-p5-sys0-s1-m2 | 12 | 0 | 4 | 2 | 100.0% | 75.0% | 85.7% | 90.9% |
| wtc-p5-sys1-s2-m0 | 8 | 0 | 13 | 2 | 100.0% | 38.1% | 55.2% | 100.0% |
| wtc-p5-sys1-s2-m1 | 9 | 0 | 10 | 1 | 100.0% | 47.4% | 64.3% | 100.0% |
| wtc-p5-sys1-s2-m2 | 2 | 0 | 2 | 2 | 100.0% | 50.0% | 66.7% | 100.0% |
| wtc-p5-sys1-s3-m0 | 3 | 0 | 11 | 3 | 100.0% | 21.4% | 35.3% | 66.7% |
| wtc-p5-sys1-s3-m1 | 9 | 0 | 7 | 4 | 100.0% | 56.2% | 72.0% | 88.9% |
| wtc-p5-sys1-s3-m2 | 2 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys2-s4-m0 | 12 | 0 | 5 | 5 | 100.0% | 70.6% | 82.8% | 90.9% |
| wtc-p5-sys2-s4-m1 | 11 | 0 | 3 | 3 | 100.0% | 78.6% | 88.0% | 100.0% |
| wtc-p5-sys2-s4-m2 | 11 | 0 | 8 | 2 | 100.0% | 57.9% | 73.3% | 100.0% |

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
