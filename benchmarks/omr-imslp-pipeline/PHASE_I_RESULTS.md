# Phase I — Music-start-anchored homography retrain (FAILED, archived)

**Date:** 2026-05-24
**Branch:** `claude/interesting-curran-3ca1b7`
**Compute:** Vast.ai Denmark RTX 4090 (~$0.27 actual GPU + ~$1 bandwidth/setup overhead, total $1.30)
**Status:** ❌ **Model collapsed — broken weights archived, prod unchanged**

## TL;DR

Phase H attempts 1 + 2 both failed and diagnosed the catalog labels'
~50 px x-offset as the binding constraint for fine-tuning. Phase I
restructured the homography in `phase_e_emit_labels.py` to anchor on the
*music-start* x (not the cell edges) and regenerated all 154,737 catalog
labels with the fix in place. Visual verification on Beethoven 1 mvt 1
p007 and Beethoven 8 mvt 1 p001 confirmed clef boxes and noteheads now
sit on the actual printed symbols.

The fine-tune retraced Phase H attempt 1's failure mode almost exactly:

- **WTC verdict set (30 cells, conf=0.10, imgsz=2048):** 0 detections per
  cell, 0 of 30 cells with verdicts ported. F1 effectively 0% (vs prod
  99.2% on the 3-cell scored sample).
- **Beethoven 5 p10 spot-check (conf=0.25):** 0 detections (vs prod 300).
  At conf=0.001 the model produces 300 detections dominated by
  `noteheadBlackInSpace` (top class is plausible — the model recognizes
  the music — but confidence is too low to use at any usable threshold).
- **Training trajectory:** cls_loss 94.7 → 4.8 over 8 epochs.
  EarlyStopping triggered at epoch 8 (patience=5 with the uninformative
  val mAP signal). Best weights saved at epoch 3.

Conclusion: **the x-offset was not the binding constraint.** The model
still finds the "predict nothing" shortcut even with structurally
correct label positions. The Phase H docs implicated the offset; the
Phase I data shows the diagnosis was incomplete.

## What we built (the fix itself is sound)

1. **`detect_pdf_music_start_x()`** in `phase_e_emit_labels.py` — given
   the binarized cell + staff line ys + an `is_system_first` flag,
   returns the page-coord x where the music begins. Approach:
   morphological vertical opening kills staff lines, per-column ink
   density finds glyph runs, the rightmost dense column in the leftmost
   35% of the cell marks the end of the clef+keysig+timesig setup.
2. **`detect_verovio_music_start_x()`** — walks the parsed
   `MeasureStaffData` for the leftmost notehead/rest x (Verovio internal
   coords). Falls back to the leftmost element of any kind.
3. **New `compute_homography()` signature** — replaces the
   `pdf_cell_x0/x1` source/dest with explicit `source_left_x`,
   `source_right_x`, `pdf_dest_left_x`, `pdf_dest_right_x`. The legacy
   form is preserved as `compute_homography_legacy()` for visual A/B.
4. **`process_movement()` wiring** — on system-first cells, both
   detectors run and feed the homography. Non-system-first cells keep
   the existing behavior (no clef setup to skip).
5. **Visual validators** — `phase_i_overlay_compare.py` (full-page
   OLD-vs-NEW side-by-side) and `phase_i_zoom_check.py` (cropped
   first-system view). Confirmed on B1 p007 + B8 p001:
   * OLD: green clef boxes collapsed at cell-left, ~120 px to the right
     of the actual printed clef.
   * NEW: green clef boxes stretched leftward to cover the actual clef
     and keysig region; red noteheads centered on printed noteheads.
6. **`phase_i_launch_training.sh`** — Phase 3.4 v1b config (SGD
   lr0=0.0005 momentum=0.937, no mosaic, no rotation, hsv_v=0.4 only,
   patience=5) plus the catalog-only data yaml.

## What the regenerated labels look like

The fix preserves label COUNT exactly: 154,737 labels across 26 (work,
edition, mvt) tuples, 0 homography failures, identical match-rate per
movement as the Phase H run.

The fix CHANGES the per-label x position on system-first cells. Sample
offsets detected:

| Edition / page | Cell width | Music-start offset from cell-left |
|---|---:|---:|
| B1 mvt 1 p007 (movement-first, C major) | 365 px | 114-120 px per staff |
| B1 mvt 1 p008 (mid-movement) | 596 px | 139-186 px per staff |
| B8 mvt 1 p001 (movement-first, F major) | 364 px | 132 px per staff |

For comparison, the OLD homography mapped Verovio's staff-line-left x
(near the clef) to the PDF cell-left x, then mapped Verovio's first
notehead position to a PDF position ~50 px to the left of the actual
notehead. The NEW homography skips the clef setup space on both sides
and overlap with actual noteheads improves visibly.

## Training trajectory (identical shape to Phase H attempt 1)

From `benchmarks/omr-imslp-pipeline/phase-i-results/results.csv`:

| Epoch | train/box_loss | train/cls_loss | train/dfl_loss | val/cls_loss | val/mAP50 |
|---|---:|---:|---:|---:|---:|
| 1   | 5.11 | 94.72 | 2.51 | 42.71 | 1e-5 |
| 3   | 5.06 | 14.39 | 2.26 | 8.17  | 2.1e-4 *(best)* |
| 5   | 5.03 | 6.26  | 2.03 | 5.39  | 1e-5 |
| 7   | 4.95 | 5.03  | 1.78 | 4.12  | 4e-5 |
| 8   | 4.82 | 4.77  | 1.73 | 4.07  | 2.8e-4 *(EarlyStopping)* |

`cls_loss` plateaued near 5 by epoch 8 — same shape as Phase H attempt 1
which plateaued at 4. The "predict nothing" shortcut works regardless of
label x-position, because if the model never emits high-confidence
predictions then it never accumulates positional or classification
loss; it sits in a degenerate minimum that any gradient descent finds
within a handful of epochs.

## Decision

- ❌ **Do NOT promote.** WTC F1 = 0% on the 3-cell scored sample (target
  was ≥ 95%). The model is functionally broken at any usable inference
  threshold.
- ✅ **Archived** at
  `tools/omr/training/data/weights/_archive/2026-05-24-phase-i-fixed-offset-broken.pt`.
- ✅ Production weights
  (`omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`) stay in
  place.

## Updated diagnosis (revising PHASE_H_RESULTS.md)

Phase H attempts 1 + 2 implicated the catalog labels' ~50 px x-offset
as the binding constraint. Phase I removed that constraint and the
model still collapsed. So the offset alone — and probably even
combined with the partial-label filter — is **not** the binding
constraint. Three candidate root causes remain:

1. **Catalog class distribution is too different from Bach.**
   Orchestral catalog has lots of half noteheads, ties, slurs,
   articulations; Bach piano is dominated by black noteheads on staff
   lines / in spaces. Fine-tuning on the catalog skews the priors away
   from the Bach distribution even when individual labels are accurate.
2. **The Phase 3.4 v1b config is too aggressive for 19 movements of
   catalog data.** v1b's precedent was 49 hand-labeled cells — three
   orders of magnitude less data. With 399 catalog pages × dense labels,
   the same lr0/momentum may push the model further than v1b did.
3. **Catalog labels still have other systematic noise beyond x-offset.**
   Possible candidates: bbox widths are heuristic, y-position depends on
   per-class `_element_extent` defaults, partial-label movements
   (50-85% match) still inject "this page is mostly background"
   signal. Per-page label DENSITY (label count / page area) is
   probably much lower in catalog than in DSv2 — the model may be
   learning "predict less" as a global prior.

The next experiments (not run in this session — would need more
compute budget) ranked by promise:

1. **Filter to ≥97% match AND apply the x-offset fix.** Phase H
   attempt 2 tried the filter alone (still failed); Phase I tried the
   fix alone (still failed); the combination is untested.
2. **Mix mode at small DSv2 sample.** Take 5-10k DSv2 images
   (not the full 165k) + the 399 catalog images. Keeps the Bach-style
   distribution alive in the gradient. Compute estimate: ~$5-8.
3. **Much lower lr0 (e.g., 1e-4) or freeze the backbone for the
   catalog fine-tune.** Limits how far the model can drift from the
   prod baseline. Cheap to try (~$0.30).
4. **Reduce cls_loss weight in the loss function.** YOLO's default
   weights `box=7.5 cls=0.5 dfl=1.5` may overweight cls when the
   training data is class-distribution-shifted. Lower cls weight
   (e.g., 0.1) might let the box/dfl signal dominate.

## Artifacts

```
benchmarks/omr-imslp-pipeline/
  phase_e_emit_labels.py             ← UPDATED: music-start detectors + new homography signature
  phase_i_overlay_compare.py         ← NEW: full-page OLD-vs-NEW overlay
  phase_i_zoom_check.py              ← NEW: cropped first-system OLD-vs-NEW overlay
  phase_i_launch_training.sh         ← NEW: Phase 3.4 v1b training config
  phase-i-overlay/                   ← gitignored; visual A/B PNGs
  phase-i-results/
    results.csv                      ← training trajectory (8 epochs, early-stopped)
    train.log                        ← full training log
  PHASE_I_RESULTS.md                 ← this file
  phase_h_build_bundle.sh            ← UPDATED: include phase_i_launch_training.sh in bundle

tools/omr/training/data/weights/
  _archive/
    2026-05-24-phase-i-fixed-offset-broken.pt   ← 88 MB; do NOT promote
```

## Cost

| Item | Spend |
|---|---:|
| Vast.ai UK m:76756 (Phase I attempt 1, lost during pip install) | ~$0.08 |
| Vast.ai Denmark m:44872 (Phase I attempt 2, completed) | ~$0.27 |
| Bandwidth (egress for 469 MB bundle + torch install) | ~$0.95 |
| **Phase I total** | **~$1.30** |
| Phase H total (attempts 1 + 2) | $0.92 |
| **Cumulative on catalog-augmented training** | **$2.22** |

Credit remaining: ~$66.40 (budget was < $2 for Phase I per the
handoff; came in slightly over because the first instance vanished
during the bootstrap's pip-install step and a second one had to be
rented from scratch).
