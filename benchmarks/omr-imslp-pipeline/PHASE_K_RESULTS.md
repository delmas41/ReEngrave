# Phase K — CV-detected stem/beam labels with XML count validation (❌ FAILED, NOT promoted)

**Date:** 2026-05-25
**Branch:** `claude/interesting-curran-3ca1b7`
**Compute:** Vast.ai Poland RTX 4090 ($0.604/hr × ~75 min ≈ $0.77 + bandwidth ≈ $0.20)
**Status:** ❌ **Catastrophic detection collapse — archived, NOT promoted**

## TL;DR

Phase J Mix's stem/beam labels came from Verovio SVG positions warped via
a homography with ~5-20 px error — pixel-imperfect for thin-line YOLO
bboxes. Phase J Mix was still promoted to prod (WTC F1 = 100%) but lost
beam detection on Beethoven 5 p10 (prod 13 → Phase J 8) and never solved
the 0-stem detection problem.

Phase K's hypothesis: replace stem/beam labels with classical-CV
detections from `tools/omr/line_detection.py` (which find the actual
printed pixel positions), validated against Verovio SVG counts within
±25% (stems) / ±50% (beams). Visual inspection on B1 mvt1 p008 and B8
mvt1 p001 confirmed Phase K labels are pixel-accurate (vs Phase J's 5-20
px offset).

**The hypothesis was correct about label accuracy. But mix-mode training
on those labels broke prod.**

| Metric | Prod | Phase J Mix (promoted) | **Phase K Mix** |
|---|---:|---:|---:|
| WTC F1 | 99.2% | 100.0% | **0.0%** (1/30 cells, TP=0 FP=1) |
| Beethoven 5 p10 total | 300 | 300 | **3** |
| - black noteheads | 147 | 183 (+24%) | **1** |
| - clefG | 14 | 14 | **0** |
| - stem | 0 | 0 | **0** |
| - beam | 13 | 8 (-38%) | **0** |
| - staff (=barline) | 18 | 16 | **0** |

The trained model emits 3 total detections at conf=0.25 on a dense
orchestral page: 1 noteheadBlackInSpace and 2 timeSigCommon. Every
other class went to zero, including the structural classes Phase K was
designed to teach.

## Root cause: prod-208 class IDs collide with DSv2 dense class IDs in mix training

Phase K labels use prod-208 class IDs:
  - 41 = stem
  - 121 = beam
  - 207 = barline

The DSv2 dense subset used in mix mode (1,714 images) uses the native
DSv2 0-145 class space, where:
  - 41 = noteheadDoubleWholeOnLineSmall (a notehead)
  - 121 = keyboardPedalUp (a pedal mark)
  - 207 = doesn't exist (DSv2 has only 146 classes)

When YOLO trains on the mix:
  - 80% of "class 41" examples come from DSv2 and show noteheads
  - 20% of "class 41" examples come from Phase K catalog and show stems
  - The two visual shapes have nothing in common
  - The class-41 head gets contradictory gradient signals every batch

The model resolves this by collapsing toward predicting nothing — net
training loss is lower if the head just doesn't fire on either pattern
than if it tries to learn an impossible "this thing is both a notehead
*and* a stem" decision boundary.

Phase J Mix had the same theoretical collision (Phase J also emitted
class 41 = stem and class 121 = beam in prod-208 space) but worked
because Phase J catalog labels ALSO emitted noteheads, clefs, key sigs,
etc. in their proper DSv2 indices — which dominated the gradient signal
and overwhelmed the small minority of stem/beam labels in those slots.
The model learned "class 41 = notehead, mostly" because that's what 95%
of examples agreed on.

Phase K's pure-structural-only labels removed that anchoring signal.
Now class 41 is *only* stem-in-catalog vs notehead-in-DSv2 — no
dominant interpretation. The training collapsed.

**Additional pipeline bug found and fixed (does not change the result):**

Phase J's `phase_h_build_splits.py` writes `nc: 146` in
`data-catalog-only.yaml` and `data-j-mix.yaml`, but the catalog emits
labels with class 207. With `nc: 146`, ultralytics filtered every
class-207 label as out-of-range during val cache building, leaving the
val set with zero valid labels and crashing the training with
`RuntimeError: No valid images found in ... cache`.

Fixed on-instance by editing the yamls to `nc: 208` (with 62 stub
class names appended). This unblocked training to run all 30 epochs,
but did not address the more fundamental class-ID collision above.

For future structural-only mix runs, `phase_h_build_splits.py` should
output `nc: 208` when the label set targets prod-208 class IDs. Left
unfixed in this commit since it doesn't matter unless we revisit
catalog-augmented training with a non-conflicting class scheme.

## Pipeline (worked as designed at the label-emit level)

### 1. Label emitter (`phase_k_emit_labels.py`)

Self-contained module that reuses:
  - `phase_e.VerovioCache` for measure ↔ SVG mapping
  - `phase_j.parse_measure_structural` for expected stem/beam COUNTS
  - `tools.omr.line_detection.detect_stems` / `detect_beams` for
    POSITIONS (classical-CV ink runs in canonical cell coords)

Per-cell validation:
  - For stems: if `|detected − expected| / expected ≤ 0.25`,
    emit all detected stem detections. Else skip cell.
  - For beams: same with tolerance 0.50 (SVG polygons-per-segment
    don't 1:1 correspond to CV ink-strokes after stacked-beam splitting).
  - For barlines: synthesized at `cell.right_edge`, same as Phase J.

Canonical → page-coord conversion uses `cell.bbox_page_px` (page origin)
plus `cell.upscale_factor` (canonical_h / page_h_of_cell).

### 2. Batch run (`phase_k_batch_emit.py`)

Same 26 (work, edition, mvt) tuples as Phase G/J. Totals across 523 pages:
  - 51,130 cells total, 43,362 (85%) matched XML
  - 5,269 cells emitted stems → 12,998 stem labels
  - 1,693 cells emitted beams → 7,425 beam labels
  - 43,362 barlines
  - Grand total: **63,785 labels** (vs Phase J's 148k = 43% the volume)

The skip rates are high (83% for stems, 95% for beams) because we
strictly drop cells where CV and XML disagree. Fewer-but-accurate labels
was the explicit design goal.

### 3. Visual validation (passed)

Overlays on B1 mvt1 p008 (densely-orchestrated):
  - Green stem boxes pixel-perfect on actual printed stems
  - Blue beam boxes on actual beam strokes
  - Red barlines exactly on barlines

Confirmed Phase K labels do NOT have the 5-20 px offset Phase J suffered.
The labels themselves are high-quality.

### 4. Training (caught the class-ID collision)

Same Phase 3.4 v1b config as Phase J:
  - Warm-start from prod weights
  - SGD lr0=0.0005 momentum=0.937 warmup_epochs=1
  - batch 4, imgsz 1280, device 0
  - fliplr=0 flipud=0 hsv_v=0.4 only (no mosaic, no rotation)
  - epochs=30 patience=5

Training trajectory (after the nc=208 fix):

| Epoch | train/box_loss | train/cls_loss | notes |
|---|---:|---:|---|
| 1   | 0.80 | 0.70 | warmup |
| 3   | 0.69 | 0.31 | cls_loss halved |
| 6   | 0.69 | 0.31 | settling |
| 11  | 0.67 | 0.28 | best cls_loss |
| 18  | 0.68 | 0.32 | drifting |
| 30  | — | — | ran all 30 epochs, no EarlyStop fired |

The training loss looked healthy — the catastrophic failure shows up
*only* at inference time. Loss going down doesn't help when the model
is learning to dampen rather than to detect.

## Decision

**Archive, do NOT promote.**

Phase J Mix remains the promoted prod model
(`omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt`, WTC F1 = 100%).

Phase K's broken weights archived at:
`tools/omr/training/data/weights/_archive/2026-05-25-phase-k-mix-superseded.pt`

## Followup ideas (NOT pursued)

If we revisit catalog-augmented structural training, the path is:

1. **Move catalog labels to non-DSv2 class IDs.** Use prod-208 slots
   146-207 (which DSv2 dense never populates) for stem/beam/barline:
     - stem → 200 (new slot)
     - beam → 201 (new slot)
     - barline → 207 (current slot, already DSv2-free)
   Then mix training has zero label-class collisions.

2. **Drop the mix entirely and freeze most of the backbone.** Pure
   catalog training with `--freeze` set high enough that only the head
   moves. Risk: prod knowledge of other classes degrades when no DSv2
   gradient is present.

3. **Two-stage training.** First, mix-warm with Phase J labels (which
   we know works) to lock in current behavior. Second, freeze backbone
   + train head only on Phase K labels at the non-DSv2 slot scheme.

The current promoted Phase J Mix's stem-detection gap (0 stems on
orchestral) is best handled in inference, NOT in YOLO training. The
classical-CV `tools/omr/line_detection.py` detects stems and beams
fine — and the OMR pipeline already uses it. There's no end-user
problem to solve here unless we want stems represented as YOLO
detections specifically (which we don't — see Phase 4f writeup).

## Cost summary

| Run | Spend |
|---|---:|
| Phase K mix (Poland 1x RTX 4090) | ~$0.77 + ~$0.20 bandwidth |
| **Phase K total** | **~$1.00** |
| Cumulative catalog-augmented training | **~$5.50** |

## Artifacts

```
benchmarks/omr-imslp-pipeline/
  phase_k_emit_labels.py             ← CV-detected structural label emitter
  phase_k_batch_emit.py              ← batch driver across 26 movements
  phase_k_launch_training.sh         ← Phase J launcher + data-j-mix.yaml fix
  phase-k-labels/                    ← gitignored; 63,785 labels
  phase-k-output/batch_summary.json  ← per-movement stats
  PHASE_K_RESULTS.md                 ← this file

tools/omr/training/data/weights/_archive/
  2026-05-25-phase-k-mix-superseded.pt   ← broken weights, kept for history
```

Validation artifacts under `benchmarks/omr-phase-h/phaseK-mix/`
(local-only, gitignored).

## What Phase K taught us

Two real findings, even though the run itself failed:

1. **CV-detected stem/beam positions ARE pixel-accurate** — the visual
   validation confirmed labels land on real ink, not the 5-20 px-off
   Verovio-warped positions Phase J used.

2. **Catalog-augmented mix training requires class-ID hygiene.** Phase J
   Mix's success masked a latent class-ID collision (catalog used DSv2
   indices for new prod-208 meanings). Pure structural-only labels
   stripped away the notehead-anchoring that hid the bug. Future
   catalog labels should target prod-208 slots that DSv2 doesn't
   populate.
