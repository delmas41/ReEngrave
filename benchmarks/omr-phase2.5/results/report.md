# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **3**
- Total detections in scored cells: 38
- Pending (not yet verdict'd): 0

## Overall

- TP (right location): **32**
- FP: **6**
- FN (missed noteheads): **1**
- Precision: **84.2%**
- Recall: **97.0%**
- F1: **90.1%**
- Notehead pitch accuracy (of correctly-located noteheads): **100.0%** (31 / 31)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| flag | 0 | 1 | 0 | 0.0% |
| notehead | 31 | 0 | 0 | 100.0% |
| rest | 1 | 2 | 0 | 33.3% |
| stem | 0 | 2 | 0 | 0.0% |
| time_sig_digit | 0 | 1 | 0 | 0.0% |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| wtc-p5 | 3 | 32 | 6 | 1 | 84.2% | 97.0% | 90.1% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| wtc-p5-sys0-s0-m0 | 0 | 1 | 1 | 0 | 0.0% | 0.0% | — | — |
| wtc-p5-sys0-s0-m1 | 14 | 2 | 0 | 0 | 87.5% | 100.0% | 93.3% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 3 | 0 | 0 | 85.7% | 100.0% | 92.3% | 100.0% |

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
