# Phase L — Slot remap retry (❌ FAILED differently, NOT promoted)

**Date:** 2026-05-25
**Branch:** `claude/interesting-curran-3ca1b7`
**Compute:** Vast.ai Finland RTX 4090 ($0.495/hr × ~2.5 h ≈ $1.10 + ~$0.20 bandwidth)
**Status:** ❌ **Beethoven 5 p10 still collapses to 3 detections; archived, NOT promoted**

## TL;DR

Phase K trained on stem/beam labels in prod-208 class slots 41 and 121,
which collided with the DSv2 dense subset (where those slots mean
notehead/pedal). The result was catastrophic class collapse — Beethoven
5 p10 dropped from prod's 300 detections to 3.

Phase L's hypothesis: relocate stem/beam to the prod-extended slot
range (146-207) which DSv2 dense never populates, eliminating the
collision. Concretely:

  - stem    41 → **160**  (prod has a duplicate "stem" name there)
  - beam   121 → **200**  (prod has a duplicate "beam" name there)
  - barline 207           (unchanged, already DSv2-free)

The training itself was *much* healthier than Phase K's:

| Metric | Phase J Mix (promoted) | **Phase L Mix** |
|---|---:|---:|
| val_cls_loss @ epoch 1 | 15.42 | **7.40** |
| val_cls_loss @ epoch 5 | 4.50 | **0.29** |
| val_cls_loss @ epoch 30 | 4.34 | **0.27** |
| WTC F1 (3 cells) | 100.0% | **100.0%** ✓ |
| Beethoven 5 p10 total | 300 | **3** ✗ |

So Phase L PASSES the WTC F1 gate (no notehead damage on simple Bach
cells) but FAILS the orchestral collapse gate — same Beethoven 5
behaviour as Phase K.

## Root cause: slot remap removed the only gradient pressure on
catalog classes

Inference on Beethoven 5 p10 at every confidence threshold from 0.25
down to 0.01:

| Conf | Total dets | Slot 41 (stem) | Slot 121 (beam) | Slot 160 (stem) | Slot 200 (beam) | Slot 207 (staff) |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25 | 3   | 0 | 0 | 0 | 0 | 0 |
| 0.10 | 11  | 0 | 0 | 0 | 0 | 0 |
| 0.05 | 28  | 0 | 0 | 0 | 0 | 0 |
| 0.01 | 87  | 0 | 0 | 0 | 0 | 0 |

The model emits **zero detections at any structural slot, at any
confidence threshold.** It also under-detects everything else (87
total at conf=0.01 vs prod's 300 at conf=0.25).

Where Phase K trained at colliding slots (41/121) and trashed those
classes via contradictory gradients, Phase L trained at DSv2-free
slots (160/200/207) — which made the *opposite* problem: the DSv2
gradient never touches those slots, and the catalog labels alone are
too few (12k stems + 7k beams + 43k barlines = 19% of mix samples
shared across 5,269 + 1,693 + 43,362 cells) to drive learning to
detect at those slots.

The model's optimum, given conflicting "DSv2 says don't predict at
slot 160" (zero positive examples) vs. catalog's "DO predict at slot
160 in 12% of cells", is roughly "ignore slot 160 — DSv2 dominates".

The val_cls_loss going down so cleanly (0.27) actually reflects the
model getting *better at the DSv2 classes*, not the catalog ones. The
val metric was misleading.

## Why Phase J Mix worked despite the same theoretical bug

Phase J emitted noteheads + clefs + keysigs + barlines + stems + beams
ALL in the same prod-208 slots. The notehead/clef labels (the
overwhelming majority) gave the model strong shared-slot gradient
signal with DSv2. The stem/beam labels were a minority but couldn't be
ignored — every training batch had them right alongside the noteheads,
in the same slots DSv2 was teaching.

Phase L's pure-structural labels stripped that anchoring signal. With
nothing in slots 0-145 in the catalog, the model effectively learned
"the catalog images contain noteheads/clefs/etc. (same as DSv2),
ignore the funny labels at slots 160/200/207."

## What this tells us about the bigger picture

Both Phase K (slot collision) and Phase L (slot isolation) failed on
Beethoven 5 p10. The promoted Phase J Mix only works on orchestral
content because its catalog labels OVERLAP with DSv2 in the
dominant classes.

The honest reading: **the YOLO catalog-augmented mix-mode training
path may not be the right tool for stem/beam detection at all.**
Phase 4's classical-CV detector in `tools/omr/line_detection.py`
already detects stems and beams from morphology + connected
components. The OMR pipeline already uses it. The end-user impact
of "YOLO also detects stems" is small if classical CV is already
doing it (and the precision benchmark planned next will measure
exactly how well classical CV does).

## Decision

**Archive, do NOT promote.**

Phase J Mix remains the promoted prod model
(`omr-weights/deepscoresv2-yolov8l-phase-j-mix-30ep.pt`, WTC F1 = 100%).

Phase L's broken weights archived at:
`tools/omr/training/data/weights/_archive/2026-05-25-phase-l-mix-superseded.pt`

## Pipeline-level fixes applied during Phase L (kept regardless of outcome)

1. **`phase_h_build_splits.py`** now writes `nc: 208` with the prod
   model's actual class names (read directly from
   `omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`), instead
   of the 146-class DSv2 list. This was the root cause of Phase K's
   "No valid images found in cache" crash. Phase L would have hit
   the same error without this fix.

2. **`phase_l_launch_training.sh`** added — Phase K launcher with
   `data-j-mix.yaml` referenced correctly. (Has a NAME-line bug: still
   uses `NAME=phase-k-$MODE` because a sed regex didn't match it. Did
   not affect training quality, just confused the runs directory name
   — actual best.pt landed in `runs/phase-k-mix-2/` despite being a
   Phase L run.)

## Followup ideas (NOT pursued)

If we revisit catalog-augmented structural training:

1. **Hybrid labels — Phase K (slot 41/121) but ALSO include noteheads
   at matching DSv2 slots.** Same approach Phase J Mix used, but with
   the pixel-accurate stem positions from CV instead of Verovio-warped
   ones. This combines Phase K's accurate label positions with Phase J's
   gradient-anchoring trick.

2. **Pure-catalog (no mix) with frozen backbone.** `--freeze` set high
   enough that only the head moves. Avoids DSv2 conflict entirely. Risk:
   model loses orchestral generalization since the backbone can't update.

3. **Two-stage training.** First mix-warm with Phase J labels, then a
   short polish run with Phase L labels at frozen backbone. Tries to
   keep prod's notehead behavior while pushing structural detection.

None of these are the obvious next step. The cleaner next step is to
**measure how good classical CV is on its own** before deciding whether
YOLO needs to also do this work. That's the stem/rhythm precision
benchmark we built during Phase L (see
`benchmarks/omr-stem-precision/`).

## Cost summary

| Run | Spend |
|---|---:|
| Phase L mix (Finland 1x RTX 4090) | ~$1.10 + ~$0.20 bandwidth |
| **Phase L total** | **~$1.30** |
| Cumulative catalog-augmented training | **~$6.80** |

## Artifacts

```
benchmarks/omr-imslp-pipeline/
  phase_l_emit_labels.py             ← slot-remap wrapper around Phase K
  phase_l_batch_emit.py              ← batch driver across 26 movements
  phase_l_launch_training.sh         ← Phase K launcher; NAME-bug noted above
  phase-l-labels/                    ← gitignored; 63,785 labels at slots 160/200/207
  phase-l-output/batch_summary.json  ← per-movement stats
  PHASE_L_RESULTS.md                 ← this file

tools/omr/training/data/weights/_archive/
  2026-05-25-phase-l-mix-superseded.pt   ← broken weights, kept for history
```

Validation artifacts under `benchmarks/omr-phase-h/phaseL-mix/`
(local-only, gitignored).

## What Phase L taught us

1. **The class-ID collision was a real bug but not the underlying
   problem.** Fixing it (slot remap) didn't fix Beethoven 5 collapse;
   the model still ignored the catalog signal.

2. **Pure-structural catalog labels can't compete with DSv2's gradient
   in mix mode.** Without shared slots, the catalog's small footprint
   gets ignored. The model focuses on the dominant signal (DSv2
   noteheads/clefs).

3. **`val_cls_loss` is misleading in mix mode.** It went down 15× from
   Phase J Mix's 4.34 to Phase L's 0.27. We interpreted that as "model
   is learning". The actual interpretation: model is learning the DSv2
   side of the mix; catalog signal is irrelevant to the loss going down.

4. **The pipeline-level nc=208 fix in `phase_h_build_splits.py`** is
   load-bearing for any future catalog-aug mix runs. Without it,
   structural-only catalog labels crash ultralytics' val cache builder.
