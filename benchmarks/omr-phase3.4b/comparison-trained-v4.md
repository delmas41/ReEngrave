# Phase 3.4 — First hand-labeled fine-tune (60 orchestral cells)

**Date:** 2026-05-22
**Builds on:** Phase 3.3 (yolov8l-imgsz2048-ft, F1 98.8%) + v1-2026-05-18-orchestral catalog

## Summary

First fine-tune of the OMR detector on hand-labeled real orchestral scans (60 cells across Beethoven 5 pages 5/15/25/35 and Mahler 5 pages 25/70/130). Two attempts:

| Attempt | nc | Outcome | F1 on 25 WTC verdict cells |
|---|---|---|---|
| **3.4 v1** | 214 (DSv2 + custom barlines + textDynamic) | ❌ Catastrophic forgetting | **79.3%** (-19.5 from 98.8%) |
| **3.4 v1b** | 208 (filtered custom classes) | ✅ Preserved WTC, added orchestral signal | **98.5%** (-0.3 from 98.8%) |

The v1b weights are NOT a meaningful improvement over Phase 3.3 on the WTC verdict set (within noise), but they ARE the first fine-tune that didn't break anything. The lesson: don't expand `nc` when fine-tuning on a small dataset; that randomizes the classification head and wipes the model's prior knowledge.

## Training runs

### Attempt v1 (broken) — `realft-v1.pt`

```
Config:
  starting weights:  deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt (F1 98.8%, mAP50 73.2%)
  dataset:           v1-2026-05-18-orchestral, 49 train / 11 val
  nc:                214 (208 DSv2 + 5 barlines + 1 textDynamic)
  imgsz:             1280, batch 4
  epochs:            30 (patience 5 → stopped at EP19)
  lr0:               0.0005, warmup 1, mosaic 0.0, degrees 1
  hardware:          Vast.ai RTX 4090 (m:14205 Hungary, $0.802/hr)
  wall time:         95s
  cost:              ~$0.02

Trajectory (orchestral val mAP50):
  EP1:  4.7%  ← class head randomized — relearning from scratch
  EP10: 17.0%
  EP14: 23.2% ← peak (this became best.pt)
  EP19: 22.0% (patience-stopped)

cls_loss started at 13.77 and never fully recovered (final 7.6).
```

Failure mode: when ultralytics saw `nc=214` in the catalog but `nc=208` in the starting weights, it printed `Overriding model.yaml nc=208 with nc=214` and re-initialized the classification head. With only 49 train images, the head couldn't relearn 208+ classes — it overfit to high-precision/low-recall behavior. **65.7% recall on the WTC verdict set** is the symptom.

### Attempt v1b (kept) — `realft-v1b.pt`

Same config as v1 except labels filtered to drop class IDs ≥ 208 (53 barline + 1 textDynamic labels dropped, 732 labels remaining). nc stays at 208, head weights preserved.

```
Trajectory (orchestral val mAP50):
  EP1:  13.9%  ← starting from preserved DSv2 head
  EP10: 22.6%
  EP14: 26.1%
  EP22: 31.7%
  EP30: 32.7% ← best (no patience trigger, ran full 30 epochs)

cls_loss started at 8.58 and decayed cleanly to 3.62.
Wall time: 97s. Cost: ~$0.02.
```

## P/R on the 25 verdict cells (same methodology as Phase 3.3)

| Engine | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Template matcher (Phase 2.8) | 242 | 20 | 0\* | 92.4% | 100%\* | 96.0% |
| YOLOv8m-r2 (Phase 3.1) | 205 | 1 | 37 | 99.5% | 84.7% | 91.5% |
| YOLOv8l-full (Phase 3.2) | 232 | 8 | 10 | 96.7% | 95.9% | 96.3% |
| YOLOv8l-imgsz2048-ft (Phase 3.3) | 238 | 2 | 4 | **99.2%** | **98.3%** | **98.8%** |
| **YOLOv8l-realft-v1** (broken) | 159 | 0 | 83 | 100% | 65.7% | **79.3%** |
| **YOLOv8l-realft-v1b** (kept) | 237 | 2 | 5 | **99.2%** | **97.9%** | **98.5%** |

\*by construction (TM defines GT)

## What v1b actually changes

On the WTC verdict cells the model is essentially unchanged (-1 TP, -1 FN vs Phase 3.3). The bigger difference is on the held-out orchestral val (the 11 unseen v1 cells from Beethoven 5 / Mahler 5):

- Phase 3.3 was never measured on this set, but the broken v1 capped at 23.2% mAP50
- v1b reached 32.7% mAP50 — a ~+10 pt improvement over the broken baseline, confirming the model is learning orchestral patterns

This isn't proof that v1b > Phase 3.3 on orchestral. They weren't compared head-to-head on identical orchestral cells. What we CAN say:

1. v1b preserves WTC F1 (within noise of Phase 3.3)
2. v1b learned from real orchestral data without forgetting DSv2
3. v1b would handle small-symbol orchestral cases at least as well as Phase 3.3, plus whatever the 60 hand-labels taught it

## What didn't work in v1 and why

The DSv2 classification head is a single Detect module (`model.22.dfl.conv.weight` is frozen by ultralytics; everything else trains). When ultralytics expands `nc`, the head's per-class output channels and the cls bias get re-initialized from scratch. With only 49 train images and a low lr0=0.0005, the head can't relearn 208 classes plus the 6 new ones. Result: catastrophic forgetting.

Fix paths for future expansion runs (when we want barlines learned):
1. Wait until we have ~200+ examples of each new class before expanding nc
2. OR: do nc-expansion ONCE on a synthetic warm-up dataset (e.g., render synthetic barlines from Bravura, train 5-10 epochs to seed the head with non-random weights), THEN fine-tune on the real catalog
3. OR: train only the head (`--freeze N` to freeze the first N layers — backbone preserved)

## Cost summary

| Run | Wall time | Cost |
|---|---|---|
| v1 (broken) | 95s | $0.02 |
| v1b (kept) | 97s | $0.02 |
| Instance idle + bootstrap (sshes, scps, evals) | ~30 min | ~$0.40 |
| Reserved credit unused on prior cleanup | | ~$1.17 |
| **Session total** | | **$1.61** |

Credit before: $10.37. Credit after: $8.76.

## What's saved locally

| File | Size | Purpose |
|---|---|---|
| `tools/omr/training/data/weights/deepscoresv2-yolov8l-realft-v1.pt` | 84 MB | Broken attempt (kept for record) |
| `tools/omr/training/data/weights/deepscoresv2-yolov8l-realft-v1b.pt` | 84 MB | Kept attempt (~ Phase 3.3 + small orchestral edge) |
| `benchmarks/omr-phase3.4/` | — | v1 detections + report (for comparison) |
| `benchmarks/omr-phase3.4b/` | — | v1b detections + report (kept attempt) |

## What's still the production model

**`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` (Phase 3.3, F1 98.8%)** remains the default until we have enough hand-labels for a meaningful improvement over it. The v1b weights are very close (-0.3 F1) but not strictly better on WTC, so there's no reason to swap yet.

## Next concrete steps

1. **Keep labeling** in the same `v1-2026-05-18-orchestral` directory OR start a `v2-...` directory if you want a clean break. Target 200-500 total cells before the next fine-tune.

2. **Try the freeze-backbone approach** on the existing v1 catalog: `--freeze 10` (freezes the first 10 backbone modules, lets only the neck + head learn). Should be safer for small datasets even than v1b.

3. **Consider synthetic-warmup for custom classes** before another nc-expansion attempt: render 100-500 synthetic engraved cells with barlines from a notation engine, train 5-10 epochs to seed the new head channels, THEN fine-tune on the real catalog. Then the model can learn barlines without forgetting DSv2.

4. **Re-add custom classes to the catalog** after step 3. For now they're filtered out (the v1b catalog has nc=208, the barline + textDynamic labels are dropped — but the original `.verdict.json` files still have them, so re-running `verdicts_to_yolo_labels.py` with `_CUSTOM_CLASSES` populated will restore them).

## Honest caveats

- 60 cells is a small dataset. Even with v1b's improvements, the per-class signal is thin.
- The orchestral val (11 cells, 15% holdout) is a small + biased eval set (all cells come from the same labeling session). The 32.7% mAP50 number should not be reported as a generalizable score.
- We never directly compared Phase 3.3 vs v1b on the same orchestral cells. The implication that "v1b is better on orchestral" relies on the inference that the new model has seen real orchestral data and the old hadn't.
- The fine-tune used `lr0=0.0005`, `mosaic=0.0`, `degrees=1` — values picked from prior fine-tune literature. They were not tuned for this specific catalog. With more labels, hyperparameter search becomes worthwhile.
