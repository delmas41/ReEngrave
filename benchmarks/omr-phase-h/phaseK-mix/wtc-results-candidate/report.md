# Phase 2.5 — template matcher scoring report

- Manifest cells: **30**
- Cells with at least one filled verdict: **1**
- Total detections in scored cells: 18
- Pending (not yet verdict'd): 17

## Overall

- TP (right location): **0**
- FP: **1**
- FN (missed noteheads): **0**
- Precision: **0.0%**
- Recall: **—**
- F1: **—**
- Notehead pitch accuracy (of correctly-located noteheads): **—** (0 / 0)

## By category

| Category | TP | FP | Pending | Precision |
|---|---|---|---|---|
| ornament | 0 | 1 | 7 | 0.0% |
| rest | 0 | 0 | 1 | — |
| structural | 0 | 0 | 1 | — |
| time_sig_digit | 0 | 0 | 8 | — |

## By piece

| Piece | Cells | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| wtc-p5 | 1 | 0 | 1 | 0 | 0.0% | — | — |

## Per-cell

| Cell | TP | FP | FN | Pending | P | R | F1 | Pitch acc |
|---|---|---|---|---|---|---|---|---|
| wtc-p5-sys0-s0-m0 | 0 | 1 | 0 | 17 | 0.0% | — | — | — |

## Matcher confusions (FP detections, when labeled)

What the matcher reported vs what the user said it actually is. Counts only FPs where the user filled in `actual_label`. (1 FP detections were left unlabeled and are excluded from this section.)

| Matcher said | Actual | Count |
|---|---|---|

---

_Precision = TP / (TP + FP)._  
_Recall = TP / (TP + FN); FN counts noteheads listed in the verdict file's FN section._  
_Pitch accuracy = correct-pitch / (correct-pitch + wrong-pitch), considering only noteheads at the right location._
