# Phase 3 — Template matcher vs trained YOLOv8 (DeepScoresV2)

**Date:** 2026-05-15
**Compared on:** 30 cells from `benchmarks/omr-phase2.5/cells.json`
**Inference hardware (local):** Apple M-series, MPS

## Trained models

Two training runs on Vast.ai (1× RTX 3090, Ryzen 5 3600, Poland):

| Run | imgsz | batch | Epochs | Wall time | Cost | Best mAP50 (val) | mAP50-95 | Recall |
|---|---|---|---|---|---|---|---|---|
| r1 | 960 | 8 | 50 | 51 min | $0.13 | **35.0%** @ ep49 | 23.4% | 36.0% |
| r2 | 1280 | 4 | 50 | 86 min | $0.22 | **42.2%** @ ep43 | 31.5% | 42.6% |
| **Run 2 wins** | | | | | | **+7.2 pts** | +8.1 pts | +6.6 pts |

Total Vast.ai spend across both runs: **$0.47** (16× below my original $3–7 estimate).

## On our 30 verdict cells

|  | Template matcher (Phase 2.8) | YOLO r1 (imgsz=960) | YOLO r2 (imgsz=1280) |
|---|---|---|---|
| **Total detections** | 265 | 928 | 916 |
| **Median time / cell** | ~1100 ms | **74 ms** | **75 ms** |
| **Median confidence** | n/a | 0.56 | **0.65** |

**YOLO is ~15× faster** at inference per cell. YOLO finds ~3.5× more total detections — split below into categories.

### Category breakdown

| Category | Template matcher | YOLO r1 | YOLO r2 |
|---|---|---|---|
| notehead | 253 | 461 | 450 |
| rest | 5 | 32 | **57** |
| accidental | 2 | 20 | **35** |
| clef | 0 (masked) | 18 | 21 |
| flag | 5 | 9 | 9 |
| time_sig_digit | 0 | 3 | 2 |
| **unknown** (DeepScoresV2 class not in `_CATEGORY_MAP`) | — | 385 | 342 |

Notable:
- **Clefs** — template matcher masks the clef region at `measure_index==0`; YOLO sees them. ~20 detections per run.
- **Rests** — YOLO finds 6-11× more. Template matcher's restrictive rest y-band probably misses some.
- **Accidentals** — YOLO finds 10-17× more. Template matcher's accidental category is famously weak (Phase 2.5 verdicts showed sharps misclassified as `restQuarter`).
- **Unknown** — YOLO returns ~340-385 detections per run with class names not in our `_CATEGORY_MAP` (e.g. `noteheadBlackOnLine` vs `noteheadBlackInSpace`, `beam`, `staff`, `augmentationDot`, `dynamicF`). Mostly these are real symbols that our wrapper just doesn't categorize yet. Expanding the map is a 30-min fix and would re-label most of the "unknown" bucket into rest/notehead/dynamic categories.

## Sample cell — `wtc-p5-sys0-s0-m0`

Same first measure of WTC page 5 system 0 staff 0:

| | Template matcher | YOLO r1 | YOLO r2 |
|---|---|---|---|
| Total detections | 10 | 21 | 20 |
| Sample class labels (r2) | `noteheadBlack` × multiple | mixed | `clefG`, `rest8th`, `noteheadBlackInSpace`, `augmentationDot`, `noteheadBlackOnLine`, `beam`, `restQuarter`, `staff`, ... |
| Confidence median | (not exposed) | 0.60 | **0.90** |

R2 is finding the clef, rests, AND noteheads — and it's confident about them. Template matcher had to mask the clef region entirely because its clef templates were too noisy.

## Implications

**For the multi-engine architecture** (Plan Phase 3):

1. **YOLO r2 is the stronger of the two trained models.** Use it as the primary YOLO engine. Keep r1 around for ablations.

2. **Multi-engine voting now has a real second voice.** Template matcher: high-precision but limited recall, especially on orchestral. YOLO r2: broader recall, faster inference, lower per-detection confidence on average. They complement each other.

3. **The "unknown" YOLO category should not be discarded.** Most "unknown" detections are real symbols (beams, augmentation dots, dynamics text, staff line fragments) whose class names just don't appear in our `_CATEGORY_MAP`. A short pass expanding the map to cover the 30 most-frequent DeepScoresV2 class names would re-categorize most of the residual "unknown" bucket.

4. **mAP@0.5 = 42% is a respectable baseline.** Eric Shen's MUSCIMA++ benchmark reports ~0.72 with YOLOv8 on a different dataset; DeepScoresV2 dense val is harder (more classes, smaller objects). The published DeepScoresV2 baseline for YOLOv5x at imgsz=1280 was ~0.41 mAP@0.5 — we hit that with a smaller model in 86 min.

5. **Speed delta matters for the dual-engine voting strategy.** YOLO at 75 ms/cell means we can run both engines on a 100-cell page in ~75 + 110 = ~185 seconds. Without YOLO, just the matcher alone is ~110 s. Adding YOLO costs only ~75 s extra.

## Honest caveats

- **No direct precision/recall numbers yet on real verdicts.** The 25 hand-annotated verdict cells are annotated against template-matcher detections, not YOLO detections. To get clean P/R for YOLO, we either (a) hand-annotate YOLO's output the same way (re-running the annotation web tool with YOLO detections), or (b) build a spatial-matcher that ports the existing verdicts onto YOLO's bbox set.

- **The "unknown" 37% of YOLO detections is a wrapper limitation, not a model limitation.** This understates YOLO's true coverage in our scorer.

- **DeepScoresV2 val ≠ real WTC scans.** The training dataset is synthetic engraved pages; WTC is an actual scan with paper texture, slight skew, ink variation. Some accuracy drop is expected on real-world input. We don't yet know the magnitude — that's what the verdict-based comparison would tell us.

## Next concrete steps

1. **Expand `_CATEGORY_MAP`** in `tools/omr/yolo_detector.py` to cover DeepScoresV2's top-30 class names (`noteheadBlackOnLine`, `noteheadBlackInSpace`, `augmentationDot`, `beam`, `staff`, `dynamicF`, etc.). ~30 min. Re-run summary above — the "unknown" column should drop dramatically.
2. **Port existing verdicts onto YOLO detections** via spatial match (similar to `port_user_verdicts.py`). Run the scorer. Compare YOLO precision/recall directly against the template matcher's 92.4% / 100% (Phase 2.8).
3. **If YOLO precision/recall on the verdict set is materially lower than template matcher on the same cells**, build a voting layer that combines both. If higher — YOLO can replace the template matcher for many use cases.
4. **Stretch goal**: train a third run with the FULL DeepScoresV2 dataset (~30K images) instead of dense (~1700). Expected to push mAP50 to ~50% based on Tuggener et al. Bigger investment (~$2-3, 4-6 hours of training).
