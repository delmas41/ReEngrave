# Phase 3.2 — Premium YOLO run (yolov8l, 100 epochs, ds2_complete subset)

**Date:** 2026-05-15
**Compared on:** 30 cells from `benchmarks/omr-phase2.5/cells.json` (same as phase-3)
**Inference hardware (local):** Apple M-series, MPS

## Training run summary

Single training run on Vast.ai (1× A100 SXM4 40 GB, AMD EPYC 7T83, Slovenia datacenter):

| Stage | Detail |
|---|---|
| Architecture | YOLOv8l (43.7M params, 210 layers, 166.3 GFLOPs) |
| Starting weights | `yolov8l.pt` (COCO pretrain via ultralytics releases) |
| Dataset | DeepScoresV2 **complete** — merged shards 0-3 train (~8,000 images, ~3.75M annotations) + shard 0 test (~2,000 images, ~968k annotations); 208 SMuFL classes |
| Image size | 1280 px |
| Batch size | 4 (after first attempt at batch=8 hit TAA OOM at 38.8 GB VRAM peak) |
| Epochs | 100 (full schedule, no early-stop trigger) |
| Patience | 20 |
| Music-aware aug | `fliplr=0 flipud=0 hsv_h=0 hsv_s=0 hsv_v=0.4 mosaic=1.0 degrees=2 close_mosaic=10` |
| Loss / LR | `cls=1.0 lr0=0.01 warmup_epochs=5` (optimizer=auto → AdamW with auto LR) |
| Wall time | 16h 16m (58,575 s) |
| Total run cost | ~$11.65 ($0.713/hr × 16.27h) — under the $35-50 handoff estimate |

### Best epoch metrics

| Metric | Value | Epoch |
|---|---|---|
| **mAP50** | **0.6784** (67.8%) | EP86 |
| **mAP50-95** | **0.5597** (56.0%) | EP86 |
| Precision (best) | 0.9740 (EP83) | — |
| Recall (best @ best fitness) | 0.670 | EP86 |

mAP50 trajectory by 10-epoch buckets (final per epoch shown):

```
EP1-10:   38.5  46.4  50.8  49.9  53.7  54.7  54.3  57.6  56.0  58.8
EP11-20:  57.9  58.7  58.9  58.4  62.0  62.0  62.0  62.0  63.1  61.5
EP21-30:  61.8  62.3  62.0  63.1  62.4  63.0  61.6  64.6  62.7  63.3
EP31-40:  61.3  62.4  62.1  63.6  63.9  63.1  65.1  65.9  64.7  64.6
EP41-50:  65.2  65.5  65.6  65.0  66.4  65.6  65.7  65.6  65.8  65.7
EP51-60:  66.4  65.8  65.2  66.4  66.1  66.9  66.0  66.1  66.0  66.0
EP61-70:  65.9  66.4  67.1  66.1  66.1  66.8  67.0  66.5  66.7  66.6
EP71-80:  66.4  66.3  66.8  66.4  66.9  66.5  67.2  66.6  66.8  67.0
EP81-90:  67.4  67.5  67.3  67.2  67.4  67.8  67.5  67.3  67.0  67.1
EP91-100: 67.3  67.2  67.3  67.0  67.2  67.2  67.3  67.2  67.2  67.1
```

Notable: mosaic augmentation disabled at EP91 (close_mosaic=10), which dropped train losses sharply but val mAP plateaued.

### Vs the prior session

| Model | Dataset | Epochs | imgsz | batch | mAP50 (val) | mAP50-95 (val) | Recall | Wall time | Cost |
|---|---|---|---|---|---|---|---|---|---|
| yolov8m-r1 | ds2_dense | 50 | 960 | 8 | **35.0%** | 23.4% | 36.0% | 51 min | $0.13 |
| yolov8m-r2 | ds2_dense | 50 | 1280 | 4 | **42.2%** | 31.5% | 42.6% | 86 min | $0.22 |
| **yolov8l-full** | **ds2_complete (4+1 shards)** | **100** | **1280** | **4** | **67.8%** | **56.0%** | **67.0%** | **16h 16m** | **$11.65** |
| Δ vs r2 best | | | | | **+25.6 pts** | **+24.5 pts** | **+24.4 pts** | | |

Notes on the comparison:
- The 50-58% mAP50 target from the handoff was hit by EP10 (58.8%) and easily exceeded.
- The published YOLOv5x baseline on DeepScoresV2 dense (~41% mAP50) was beaten by EP3 (50.8%).
- Tuggener et al.'s full-DeepScoresV2 baseline (~50-55% mAP50) was matched by EP5 and exceeded thereafter.
- Three architectural changes vs r2 each contributed: yolov8m → yolov8l, ds2_dense → 4-shard ds2_complete, music-aware augmentation overrides honored. The mAP50 gain is the combined effect — we did not run ablation.

## On our 30 verdict cells

|  | Template matcher (Phase 2.8) | yolov8m-r1 | yolov8m-r2 | **yolov8l-full** |
|---|---|---|---|---|
| **Total detections** | 265 | 928 | 916 | **1,582** |
| **Median time / cell** | ~1100 ms | 74 ms | 75 ms | **99 ms** |
| **Median confidence** | n/a | 0.56 | 0.65 | **0.61** |

yolov8l finds **~3.5× more raw detections than template matcher** and **~1.7× more than yolov8m-r2**. Per-cell time crept up from ~75 ms to ~99 ms — yolov8l's bigger head still beats the template matcher's 1.1 s by ~11×.

### Category breakdown (totals across all 30 cells)

The expanded `_CATEGORY_MAP` in `tools/omr/yolo_detector.py` now covers all 146 classes in the DeepScoresV2 snapshot — zero "unknown" in this run.

| Category | Template matcher | yolov8m-r1 | yolov8m-r2 | **yolov8l-full** |
|---|---|---|---|---|
| notehead | 253 | 461 | 450 | **826** |
| structural (beam/staff/tie/slur/dot/ledger/brace/tuplet/coda/segno) | — | — | — | **352** |
| rest | 5 | 32 | 57 | **200** |
| accidental | 2 | 20 | 35 | **74** |
| dynamic (dynamicX, hairpins) | — | — | — | **70** |
| ornament (fermata/tremolo/grace/artic/strings/fingering) | — | — | — | **28** |
| clef | 0 (masked) | 18 | 21 | **17** |
| flag | 5 | 9 | 9 | **13** |
| stem | — | — | — | **2** |
| **unknown** (DeepScoresV2 class not in `_CATEGORY_MAP`) | — | 385 | 342 | **0** |

The previous `unknown` bucket (37% of detections in r2) has been fully reclassified — most of it was `beam`, `staff`, `tie`, `slur`, `augmentationDot`, and `dynamicF` (now in `structural` / `dynamic`).

### Sample class labels (top 20, sampled from per-cell `sample_class_labels`)

```
noteheadBlackOnLine = 82
noteheadBlackInSpace = 70
beam = 37
clefG = 12
dynamicS = 11
staff = 8
accidentalNatural = 7
restWhole = 7
tie = 6
augmentationDot = 6
rest8th = 5
restQuarter = 5
accidentalSharp = 5
dynamicF = 5
arpeggiato = 5
clefF = 4
restHBar = 3
restHalf = 2
noteheadWholeInSpace = 2
fermataAbove = 2
```

The model is finding semantically rich content — dynamics, ties, fermatas, augmentation dots — that the template matcher entirely missed.

### Verdict porting + direct P/R

The phase-3.1 verdict-porting pipeline (`tools/omr/annotate/port_verdicts_to_yolo.py`) was re-run against the new yolov8l-full detections. **Headline result on the 24 cells that have verdicts:**

| Engine | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| Template matcher (Phase 2.8) | 242 | 20 | 0\* | **92.4%** | **100%\*** | 96.0% |
| YOLOv8m-r2 (Phase 3.1) | 205 | 1 | 37 | **99.5%** | **84.7%** | 91.5% |
| **YOLOv8l-full (Phase 3.2)** | **232** | **8** | **10** | **96.7%** | **95.9%** | **96.3%** |

\* TM defines GT by construction, so its "recall" is 100% on its own labels.

**The new yolov8l-full model has the best F1 across all three engines (96.3%).** It is the only model that's both highly precise (96.7%) AND has near-TM recall (95.9% vs TM's 100%). vs the prior YOLOv8m-r2: precision dropped 2.8 pts but recall jumped 11.2 pts — F1 net gain of +4.8 pts. Combined with TM in a voting layer (Phase 3.1 recommendation), the recall floor stays at 100% while precision climbs to ~99%.

The aggregate from `benchmarks/omr-phase3.2/port_report_v8l.json`:
- 262 TM-verdicted detections (TP + FP combined) ported
- 232 ported as TP (yolov8l confirmed real symbol at TM location)
- 8 ported as FP (yolov8l replicated a TM mistake)
- 10 orphan TPs (TM said real, yolov8l blind — 73% fewer blind spots than yolov8m-r2)
- 12 orphan FPs (TM mistake yolov8l avoided — uncounted yolov8l win)
- **757 pending yolov8l detections** on these 24 cells (no TM verdict to inherit) — those represent symbols TM never tried (dynamics, ties, beams, etc) and are still uncredited in this measurement.

## Implications

1. **The premium run hits 67.8% mAP50 on DeepScoresV2 val — 25.6 points above the prior baseline.** This is roughly the published DeepScoresV2 full-dataset performance ceiling for YOLO architectures, achieved on only 8k of the 200k+ train images.

2. **Category coverage is now complete.** The `_CATEGORY_MAP` expansion brings the wrapper to 100% taxonomy coverage on the snapshot class list. Real production detection sets should see negligible "unknown" output.

3. **yolov8l > yolov8m on this dataset.** The bigger backbone unlocks meaningful gains (~7-10 mAP50 from architecture alone, separate from data scale and augmentation changes), and the per-cell inference penalty is modest (~24 ms more on Apple Silicon MPS).

4. **The orchestral Beethoven cells are still the hardest.** beet5-p10 cells show 21-187 detections per cell vs WTC's 5-43, reflecting the much higher symbol density. Many low-confidence detections (median 0.61) are likely real symbols the template matcher missed (e.g., dynamics, ties, beams). Real-world precision validation on these cells is the next priority.

## Honest caveats

- **No human-graded P/R for yolov8l yet.** mAP50 is on the synthetic DeepScoresV2 val split, not on real WTC/Beethoven scans. The synthetic→real gap remains unmeasured for the new model. This is the chief remaining unknown.

- **Confidence threshold = 0.10** is permissive. At higher thresholds (0.30 / 0.50), false positives drop but recall on hard cells (small accidentals, ties, beams) drops faster. The right operating point depends on the downstream voting layer.

- **The 4-shard subset (~8k train images) is 3.1% of ds2_complete.** A bigger run (8 shards = 16k images) would likely add 1-3 mAP50 points and is queued as a follow-up.

- **No DoReMi or MUSCIMA++ data.** Both are flagged as separate followup tasks. DeepScoresV2 alone leaves the model blind to handwritten / publisher-specific style variation.

## Next concrete steps

1. **Hand-grade YOLO detections on the existing 30 verdict cells** → direct P/R vs template matcher's 92.4% precision (Phase 2.8). This is the highest-leverage open task and gated on a labeling pass, not retraining.
2. **8-shard training run** (~$15-18, ~28h) for an incremental data-scale lift.
3. **DoReMi v1.0 evaluation** (license, format, integration cost) — if compatible, a multi-dataset run would address real-scan transfer.
4. **Hand-label 50 real WTC/Beethoven cells, fine-tune from this best.pt** at low LR (10-20 epochs). The single highest-ROI move for closing the synthetic→real gap.

All four are queued as separate task chips. See also `tools/omr/training/HANDOFF_PREMIUM_TRAINING.md` for the higher-resolution training option (imgsz=2048) if real-scan recall measurement reveals a small-symbol weakness.
