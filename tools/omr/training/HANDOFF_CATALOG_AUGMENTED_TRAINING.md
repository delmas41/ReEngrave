# Handoff prompt — catalog-augmented YOLO retrain (Phase H / "Phase 3.5")

Drop the block below into a fresh Claude Code session (or follow it yourself) to launch the catalog-augmented retrain. Builds on the Phase F/G work that generated YOLO labels for orchestral score pages by warping known XML element positions onto PDFs.

## Why this run

The current production weights (`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`) hit F1 98.8% on the Bach WTC verdict set but degrade on dense orchestral pages (Mahler, Debussy, etc.) where the training data was thinner. Phase E generated ~130,000 catalog-grade YOLO labels across 7 catalog-ready editions of Beethoven 1/2/4/6/8 — real orchestral scans with auto-synthesized labels from the matching MusicXML. Mixing this into a fine-tune should close the orchestral gap without sacrificing the WTC performance.

## Where the data is

Run the Phase G batch first to regenerate the labels into a clean directory:

```bash
cd /Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/interesting-curran-3ca1b7
python3 benchmarks/omr-imslp-pipeline/phase_g_batch_emit.py --skip-overlays
```

This writes:

```
benchmarks/omr-imslp-pipeline/phase-e-labels/
  {work}-{edition}-mvt{N}/
    labels/
      p{NNN}.txt          ← YOLO label file per PDF page
    summary.json          ← {pages, cells, labels, xml_match_rate}
benchmarks/omr-imslp-pipeline/phase-g-output/
  batch_summary.json      ← aggregate across all (work, edition, mvt) tuples
```

The summary at the time of writing (commit `c05aeab`):

| Metric | Value |
|---|---:|
| Total runs (edition × mvt) | 26 planned (24 succeed; B6 mvt 3+4 + B4 mvt 3 skipped) |
| Pages processed | ~480 |
| Cells extracted | ~46,000 |
| Labels emitted | ~130,000 |
| 100% XML-measure match runs | majority (some non-Werke editions have repeats that cause measure-count drift, dropping match rate to 50-85%) |

The labels are in standard YOLO format: `class_id cx cy w h` (normalized to image dims, [0,1]). Class IDs come from `tools/omr/training/deepscores_classes.py` — the existing 146-class DSv2 list. **Barlines are intentionally not in the YOLO set** — DSv2 doesn't have a barline class; the production pipeline uses classical CV for barline detection.

## The mix-train plan

1. **Decide the mixing ratio**. The Phase E plan was 50/50, but DSv2 ships ~165,000 images and the catalog has ~480 page images. A literal 50/50 by image-count would over-weight the small catalog set. Suggested options:

   - **Option A (recommended):** sample DSv2 normally, then upsample the catalog by 100-200× so each catalog image gets seen 100-200 epochs per DSv2 epoch. Catalog → ~50,000-100,000 sampled images per epoch, DSv2 → ~165,000.
   - **Option B:** use the standard YOLO multi-dataset blending (`data.yaml` with two `path` entries) and let ultralytics interleave them.

2. **Build the merged `data.yaml`**:

   ```yaml
   # data-catalog-mix.yaml
   path: /workspace/reengrave-training/data
   train:
     - deepscoresv2-yolo/train.txt    # standard DSv2 train split
     - catalog-labels/train.txt        # the Phase E label list
   val:
     - deepscoresv2-yolo/val.txt       # use DSv2 val for sanity
     - catalog-labels/val.txt          # held-out catalog mvt (e.g. B1 mvt 4) for orchestral mAP
   nc: 146
   names: # paste from deepscores_classes.py DEEPSCORES_V2_CLASSES
   ```

   For the catalog-labels split, hold out one full movement per edition as val (e.g. `beethoven-symphony-1-imslp-52848-mvt4` → val; everything else → train). This gives you mAP on unseen orchestral pages without leaking measures into train.

3. **Image paths.** The YOLO label files reference PDF pages by index but the actual images aren't rendered ahead of time. Two paths:

   - **Render once.** Walk `phase-e-labels/` and for each `{work}-{edition}-mvt{N}/labels/p{NNN}.txt`, render the corresponding PDF page at 300 DPI (the same DPI the labels were warped against) and save as `images/p{NNN}.png`. ~480 PNGs × ~3.5 MB ≈ 1.7 GB.
   - **On-the-fly.** Write a custom ultralytics `Dataset` that calls `render_page()` per index. Slower per step but no disk cost.

   **Recommend: render once.** Disk is cheap on Vast.ai. Add this to the prep step.

4. **Warm-start from the production weights**:

   ```bash
   python3 -m training.train_yolo \
     --data data-catalog-mix.yaml \
     --weights data/weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt \
     --epochs 30 \
     --imgsz 1280 \
     --batch 6 \
     --device 0 \
     --patience 10 \
     --workers 8 \
     --fliplr 0 --flipud 0 \
     --hsv_h 0 --hsv_s 0 --hsv_v 0.4 \
     --mosaic 0.5 \
     --degrees 2 \
     --name ds2-yolov8l-catalog-mix-ft \
     --extra-kwargs '{"cls": 1.0, "lr0": 0.001, "warmup_epochs": 2}'
   ```

   Notes:
   - `lr0=0.001` (10× lower than the full DSv2 train) — fine-tune, don't blow up the existing weights.
   - `epochs=30 patience=10` — short fine-tune; should converge in 15-25 epochs since the model already knows DSv2.
   - `mosaic=0.5` — half the time, mix 4 images. Helps regularize the orchestral fine-tune.
   - `imgsz=1280` — same as the production model (don't change the inference resolution).

5. **Validate before promoting**:

   - Run the new model against the existing Bach WTC verdict set with `tools/omr/training/eval_on_score_cells.py`. F1 should stay ≥ 95% (target: stay ≥ 98%).
   - Run against a holdout catalog movement (e.g. B1 mvt 4) — measure mAP50 specifically on orchestral classes (`noteheadBlack*`, `clef`s, accidentals, rests). Target: +5-10 mAP50 vs the production weights on this set.
   - Run against the orchestral real-world benchmark (`benchmarks/omr-real-world/`) — verify it does *not* regress on the 5 hand-checked PDFs there.

   Only promote the new weights if both bars pass.

## Known limitations of the catalog data

These are documented in `benchmarks/omr-imslp-pipeline/PHASE_E_SUMMARY.md`:

- **~50 px x-offset residual** on system-first cells (warped notehead positions are 30-50 px left of the actual notehead). YOLO bbox is ~20-25 px wide at 300 DPI, so labels still overlap actual noteheads — training-grade noisy, not wrong. If training quality suffers, fix per-cell first.

- **PDF→XML measure drift** on some non-Werke editions. The B2 Litolff mvt 4 and B2 Ricordi mvt 1 show 50-85% XML-match rates instead of 100%. The unmatched cells get no labels (rather than wrong ones), so it's a recall hit on those movements, not a precision hit.

- **Beethoven 4 imslp-411721 mvt 3** boundary is unverified. The Heugel edition doesn't print a "III" header, so the Scherzo's start page is best-guess. Excluded from the batch.

- **Beethoven 6 imslp-57857 mvts 3/4 transition** is mid-page (p66, system 2 introduces Tromboni for the Gewitter Sturm). Cells on p66 can't be cleanly assigned to a single movement. Excluded from the batch.

## Compute estimate

| Item | Estimate |
|---|---|
| GPU | A100 40GB (or RTX 4090 24GB if 4090 batch=4 still fits) |
| Wall time | 4-8 hours (30 epochs × ~10 min/epoch on A100, 13 min on 4090) |
| Cost | $7-12 on A100 at ~$1.30/hr |
| Output weights | `runs/detect/ds2-yolov8l-catalog-mix-ft/weights/best.pt` |
| If best > prod weights on both validation bars | Promote to `data/weights/deepscoresv2-yolov8l-catalog-mix-ft-30ep.pt` and update `tools/omr/yolo_detector.py`'s default weights path |

## Rollback

If the new model regresses on the Bach WTC verdict set or the real-world benchmark, do nothing — the production weights at `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` stay in place. The catalog labels themselves remain valuable training data for a future iteration (e.g. with the x-offset fix landed, or with finer-grained catalog selection).

## Pre-flight

Before launching, run a 1-edition smoke test locally to confirm the data layout:

```bash
python3 benchmarks/omr-imslp-pipeline/phase_g_batch_emit.py --dry-run  # confirm 26 runs planned
python3 benchmarks/omr-imslp-pipeline/phase_e_emit_labels.py --max-pages 2   # confirm a single edition works
ls benchmarks/omr-imslp-pipeline/phase-e-labels/beethoven-symphony-1-imslp-52848-mvt1/labels/
head benchmarks/omr-imslp-pipeline/phase-e-labels/beethoven-symphony-1-imslp-52848-mvt1/labels/p007.txt
```

The label rows should look like:
```
27 0.232415 0.713 0.024 0.040
0 0.250381 0.711 0.012 0.0048
...
```
(class_id is 0-145, the rest are normalized [0,1]).
