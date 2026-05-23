# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **3**
- Total detections in scored cells: 42
- Pending (not yet verdict'd): 1

## Overall

- TP (right location): **41**
- FP: **0**
- FN (missed noteheads): **0**
- Precision: **100.0%**
- Recall: **100.0%**
- F1: **100.0%**
- Notehead pitch accuracy (of correctly-located noteheads): **100.0%** (40 / 40)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| notehead | 40 | 0 | 1 | 100.0% |
| rest | 1 | 0 | 0 | 100.0% |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| wtc-p5 | 3 | 41 | 0 | 0 | 100.0% | 100.0% | 100.0% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| wtc-p5-sys0-s0-m0 | 9 | 0 | 0 | 1 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 0 | 0 | 0 | 100.0% | 100.0% | 100.0% | 100.0% |

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
