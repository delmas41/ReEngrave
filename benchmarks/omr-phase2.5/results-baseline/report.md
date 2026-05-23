# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **3**
- Total detections in scored cells: 54
- Pending (not yet verdict'd): 2

## Overall

- TP (right location): **41**
- FP: **11**
- FN (missed noteheads): **0**
- Precision: **78.8%**
- Recall: **100.0%**
- F1: **88.2%**
- Notehead pitch accuracy (of correctly-located noteheads): **100.0%** (40 / 40)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| barline | 0 | 1 | 0 | 0.0% |
| flag | 0 | 2 | 0 | 0.0% |
| notehead | 40 | 2 | 1 | 95.2% |
| rest | 1 | 3 | 1 | 25.0% |
| stem | 0 | 2 | 0 | 0.0% |
| time_sig_digit | 0 | 1 | 0 | 0.0% |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| wtc-p5 | 3 | 41 | 11 | 0 | 78.8% | 100.0% | 88.2% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| wtc-p5-sys0-s0-m0 | 9 | 6 | 0 | 2 | 60.0% | 100.0% | 75.0% | 100.0% |
| wtc-p5-sys0-s0-m1 | 14 | 2 | 0 | 0 | 87.5% | 100.0% | 93.3% | 100.0% |
| wtc-p5-sys0-s0-m2 | 18 | 3 | 0 | 0 | 85.7% | 100.0% | 92.3% | 100.0% |

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
