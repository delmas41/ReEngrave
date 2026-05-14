# Phase 3 MVP — template matcher vs YOLOv8 (COCO weights) side-by-side

**Date:** 2026-05-14
**Cells:** 3 pre-filled WTC (s0-m0, s0-m1, s0-m2) + 1 unfilled (s1-m0)
**Template matcher state:** post-Phase 2.7 (rest y-band gate active, all fixes on)
**YOLO state:** ultralytics YOLOv8m with pretrained COCO weights (80 generic classes — no music symbols)
**YOLO conf threshold:** 0.05 (very permissive, to surface ANY detections)
**Device:** Apple Silicon MPS

## Goal of this comparison

This is an MVP — the wiring exists, weights are not domain-trained. The
point is NOT to show YOLO wins, but to show:

1. `YoloDetector` produces `SymbolDetection` objects in the same shape as
   the template matcher.
2. `tools/omr/annotate/score.py` runs unchanged on YOLO output.
3. With COCO weights, YOLO finds 0 music symbols on score cells (because
   COCO has no music classes — only person/car/animal/etc.). This is the
   honest baseline.

If/when DeepScoresV2-pretrained weights become available (or we fine-tune
on a music dataset), only the `--weights` argument changes; no code
changes required.

## Side-by-side counts

| Cell | Template matcher | YOLOv8m (COCO) |
|---|---|---|
| wtc-p5-sys0-s0-m0 | 10 detections, all category=notehead, P=100% (post-Phase 2.7) | 5 detections, all category=unknown (bird×4, apple×1), conf range [0.05, 0.52], 0 music symbols |
| wtc-p5-sys0-s0-m1 | 14 detections (13 noteheads + 1 rest), P=100% | 2 detections, both unknown (bird, traffic light), conf range [0.11, 0.23], 0 music symbols |
| wtc-p5-sys0-s0-m2 | 18 detections, all noteheads, P=100% | 1 detection, unknown (bird), conf=0.07, 0 music symbols |
| wtc-p5-sys0-s1-m0 (unfilled) | not scored | 15 detections, all unknown (bird×10+), conf range [0.06, 0.53], 0 music symbols |

## YOLO detection category breakdown (across all 4 cells)

| Category | Count |
|---|---|
| unknown (COCO bird/apple/traffic light) | 23 |
| notehead | 0 |
| rest | 0 |
| accidental | 0 |
| barline | 0 |
| clef | 0 |
| flag | 0 |

## YOLO confidence distribution

| Cell | min | median | max | mean |
|---|---|---|---|---|
| s0-m0 | 0.053 | 0.099 | 0.516 | 0.177 |
| s0-m1 | 0.114 | 0.173 | 0.231 | 0.173 |
| s0-m2 | 0.069 | 0.069 | 0.069 | 0.069 |
| s1-m0 | 0.056 | 0.154 | 0.534 | 0.214 |

Most "detections" are below 0.20 confidence — they're floor-of-the-curve
COCO classifier noise. The two ~0.52 outliers (s0-m0 "bird" at conf 0.52,
s1-m0 "bird" at conf 0.53) are stable across runs; presumably the COCO
classifier is reading note-stems-with-flags as bird-like vertical shapes
with horizontal wing-protrusions. Not informative for music.

## Does YOLO find the same noteheads the template matcher finds?

**No.** Zero overlap. YOLO with COCO weights detects 0 noteheads on these
cells. The template matcher detects all 41 ground-truth noteheads at 100%
precision (Phase 2.7).

The `port_verdicts` matcher (which matches detections by category +
proximity) found 0 baseline TPs adjacent to any YOLO detection — meaning
NOT EVEN ACCIDENTAL LOCATION OVERLAP with the human-verified template-
matcher TPs.

## Wall-clock inference time

Median per-cell inference (excluding the first warmup run, n=5):

| Cell | Median (s) |
|---|---|
| s0-m0 | 0.021 |
| s0-m1 | 0.023 |
| s0-m2 | 0.022 |
| s1-m0 | 0.023 |

~22 ms/cell on Apple Silicon MPS. Wall-clock is fine; YOLO is fast.

For comparison, the template matcher's wall-clock is substantially
slower (~1-3 s per cell for the slide-the-template-across-image NCC
pass, depending on library size), but produces the correct output.

## Honest assessment

YOLOv8m with COCO weights is **useless** as an OMR detector. It finds 0
musical symbols and emits garbage class labels. This is the expected
null result. The point of running it was to:

1. Confirm `pip3 install --user ultralytics` works on macOS (it does).
2. Confirm the wrapper produces `SymbolDetection` objects the scorer
   accepts (it does — the scorer ran end-to-end with no errors).
3. Confirm wall-clock inference time is acceptable (~22 ms/cell on MPS).
4. Establish the floor for "what does Phase 3 look like with the wrong
   weights?" so future Phase 3.x work has a baseline to beat.

## What would actually make YOLO useful for OMR

In rough order of effort/expected payoff:

1. **Train YOLOv8 on DeepScoresV2** (134 music symbol classes,
   ~250k labelled symbols, public dataset). Estimated effort: ~1 day on a
   single GPU. This is the canonical move and likely produces a strong
   detector for printed scores.

2. **Fine-tune from DeepScoresV2** on a small set of WTC / Beethoven cells
   from the same printing tradition. Probably +5-10 pp precision over
   the public-dataset-only model.

3. **Find published music-OMR YOLO weights.** I searched HuggingFace for
   `deepscores`, `yolo music`, `omr` — no public YOLOv8 music weights
   exist as of 2026-05-14. The closest hit was
   `imadbekkouch/medieval_music_yolov8` (medieval notation, not modern
   common-practice-period scores; an instance-segmentation ONNX, not
   pretrained YOLOv8 detection weights). Not useful as a starting point
   for printed common-practice notation.

## Next step

Decide whether to spend the ~1 day to train YOLOv8 on DeepScoresV2 (Phase
3.5), or to skip Phase 3 entirely and invest in widening the template-
matcher's annotation set instead (Phase 2.5 expansion).

The signal we now have:

- Template matcher: 100% precision on 3 WTC cells (n=3, optimistic
  ceiling; recall is currently a 100% artifact of zero FN annotations).
- YOLO with off-the-shelf COCO weights: 0% useful detections.
- YOLO inference time: cheap (~22 ms/cell on MPS).

The infrastructure (wrapper, run script, scorer compatibility) is in
place so a future session can swap in DeepScoresV2-trained weights with
a single `--weights` argument.
