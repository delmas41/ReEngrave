# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **3**
- Total detections in scored cells: 335
- Pending (not yet verdict'd): 95

## Overall

- TP (right location): **236**
- FP: **4**
- FN (missed noteheads): **0**
- Precision: **98.3%**
- Recall: **100.0%**
- F1: **99.2%**
- Notehead pitch accuracy (of correctly-located noteheads): **100.0%** (236 / 236)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| accidental | 0 | 0 | 1 | — |
| notehead | 236 | 3 | 49 | 98.7% |
| ornament | 0 | 0 | 1 | — |
| rest | 0 | 0 | 8 | — |
| structural | 0 | 1 | 36 | 0.0% |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| wtc-p5 | 3 | 236 | 4 | 0 | 98.3% | 100.0% | 99.2% |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| wtc-p5-sys0-s0-m0 | 56 | 2 | 0 | 22 | 96.6% | 100.0% | 98.2% | 100.0% |
| wtc-p5-sys0-s0-m1 | 91 | 2 | 0 | 39 | 97.8% | 100.0% | 98.9% | 100.0% |
| wtc-p5-sys0-s0-m2 | 89 | 0 | 0 | 34 | 100.0% | 100.0% | 100.0% | 100.0% |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (4 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
