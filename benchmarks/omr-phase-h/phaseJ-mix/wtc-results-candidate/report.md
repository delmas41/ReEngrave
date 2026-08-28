# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **3**
- Total detections in scored cells: 69
- Pending (not yet verdict'd): 25

## Overall

- TP (right location): **44**
- FP: **0**
- FN (missed noteheads): **0**
- Precision: **100.0%**
- Recall: **100.0%**
- F1: **100.0%**
- Notehead pitch accuracy (of correctly-located noteheads): **100.0%** (44 / 44)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| notehead | 44 | 0 | 2 | 100.0% |
| rest | 0 | 0 | 3 | — |
| structural | 0 | 0 | 20 | — |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| wtc-p5 | 3 | 44 | 0 | 0 | 100.0% | 100.0% | 100.0% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| wtc-p5-sys0-s0-m0 | 9 | 0 | 0 | 8 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m1 | 11 | 0 | 0 | 5 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 24 | 0 | 0 | 12 | 100.0% | 100.0% | 100.0% | 100.0% |

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
