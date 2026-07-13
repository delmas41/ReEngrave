# Clef pseudo-label fine-tune — Phase 0 results (2026-07-13)

Clean fine-tune from the production checkpoint on 62 correctly-labeled clef
cells (v5 + v6 = Boléro/La Mer/Beethoven 5/Mahler 5; 63 clefs: 14 alto, 12
tenor, 19 bass, 18 treble). Frozen backbone (freeze=10), AdamW lr0=0.001, 30
epochs, imgsz 1280, MPS. Output: omr-weights/deepscoresv2-yolov8l-clef-ft-2026-07-13.pt
(production weights untouched).

## Result — measured with tools/omr/training/clef_count_eval.py (44-cell set)

| metric | production | fine-tuned |
|---|---|---|
| clef DETECTED | 4/44 (9%)  | **44/44 (100%)** |
| type accuracy (15 GT) | 0/15 (0%) | **13/15 (87%)** |
| treble / bass / tenor | 0 each | **5/5, 5/5, 2/2** |
| alto | 0/3 | 1/3 (2 read as tenor) |

Forgetting check (noteheads vs GT on dense cells): fine-tuned matches GT counts;
production over/under-detected. Non-clef totals DROPPED (less hallucination). No
catastrophic forgetting.

## Verdict: KEEP. The clean clef fine-tune fixes the all-treble disease.

## Caveats / next
- Small eval (44 clef cells + 4 forgetting cells). Broader audit needed before
  deploying as production default (rebuild a working WTC F1 general eval — the
  old catalog-val mAP is meaningless on canonical cells).
- alto/tenor confusion (2 alto→tenor): same C-clef glyph one line apart; add
  more alto examples.
- v1-v4 still contaminated (accidental key-sig/note split) — clean before reuse.
- Deploy by setting OMR_WEIGHTS_PATH to the new .pt once broader-validated.
