# Phase H — Catalog-augmented YOLO retrain (Attempts 1 & 2 — both FAILED, neither promoted)

**Date:** 2026-05-24
**Branch:** `claude/interesting-curran-3ca1b7`
**Compute:** Vast.ai UK RTX 4090 (attempt 1, $0.75) + Netherlands RTX 4090 (attempt 2, $0.17). Total $0.92.
**Status:** ❌ **Both attempts failed — broken weights archived, prod unchanged**

## What we tried, two ways

1. **Attempt 1 — all 154k catalog labels (30 epochs):** model collapsed to predicting
   only `clefG` at conf<0.05; 0 detections per Bach WTC cell at conf=0.10.
2. **Attempt 2 — filter to high-match-rate movements only (113 train images,
   patience-stopped at epoch 6):** model still degraded. Bach WTC went from
   prod's 72–157 detections/cell to 5–27 detections/cell of wrong categories
   (a 959×12-pixel "restHBar" stripe, a "beam" overlaying a staff line).
   `noteheadBlackOnLine` (the most-frequent symbol on Bach piano music)
   went from prod's 78 detections on Beethoven 5 p10 → **zero** for the
   trained model. New "staff" hallucinations appeared.

**Conclusion:** even with the partial-label problem filtered out, the
remaining catalog labels are not training-grade for fine-tuning. The
~50 px x-offset and the orchestral-biased class distribution are
sufficient on their own to shift the model's priors in ways that hurt
both Bach (wrong things detected) and would likely hurt orchestral
recall too (we just can't measure it because the orchestral val is also
noisy). Recommendation in "Lessons" section below now restated more
strongly.

## Attempt 2 (filter-only fix) — added 2026-05-24 after attempt 1 commit

After attempt 1 collapsed, hypothesized that the "predict nothing" failure
mode was driven by movements where 30-50% of cells had no labels (XML
match rate <95%). Filter test:

- **Filtered train:** 113 images across 6 movements, all with XML-match
  rate ≥ 97%. Val unchanged (124 images, 7 movements).
- **Same config as attempt 1:** SGD lr0=0.0005, momentum=0.937,
  mosaic=0, degrees=1, batch=4, imgsz=1280.
- **Patience-stopped at epoch 6** (vs attempt 1 running all 30):
  val mAP didn't improve so EarlyStopping triggered. train/cls_loss
  dropped 74→16 in 6 epochs vs attempt 1's 91→4 over 30. Less drift
  from prod baseline.

**Beethoven 5 p10 spot-check, conf=0.25:**

| Class | Prod | Attempt 2 (filtered, 6 ep) |
|---|---:|---:|
| Total detections | 300 | 177 |
| noteheadBlackOnLine | 78 | **0** |
| noteheadBlackInSpace | 46 | 12 |
| noteheadHalfOnLine | 10 | 21 |
| noteheadHalfInSpace | 9 | 19 |
| restWhole | 12 | 12 |
| clefG | 14 | **0** |
| clefF | 8 | 8 |
| keyFlat | 29 | 17 |
| slur | 27 | 16 |
| tie | 19 | 14 |
| rest8th | 14 | 9 |
| **(new)** staff | 0 | 16 |

The model has **shifted its priors**: under-predicts black noteheads
(the dominant Bach class), over-predicts half noteheads, drops clefG,
and hallucinates "staff" objects (likely confusing staff lines with the
labeled "barline → staff-tall" rectangles from the catalog warp).

**Bach WTC verdict scoring:** 5-27 detections per cell (vs prod's
72-157), and `ported=0` for every cell — the spatial ports of human
verdicts to YOLO detections found no matches, meaning the model's
detections aren't where the music symbols actually are. F1 effectively
0%, well below the ≥95% promotion gate.

**Decision:** Do NOT promote. Archived at
`tools/omr/training/data/weights/_archive/2026-05-24-phase-h-attempt2-filtered-6ep.pt`.

**Updated diagnosis:** the filter-only fix is insufficient. Even with
clean (≥97% match) labels, the residual issues — most importantly the
~50 px x-offset, but also the catalog's class-distribution bias toward
orchestral patterns (half notes, ties, beams) — are enough to shift the
model away from Bach-style detection. The x-offset fix from
PHASE_E_SUMMARY Phase F is now upgraded from "should do" to **required
gate** for any future Phase H retry.

---

## TL;DR (attempt 1)

Fine-tuning `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` on the Phase G
catalog labels for 30 epochs at SGD lr0=0.0005 / batch 4 collapsed the
model. After training:

- **WTC verdict cells:** 0 detections per cell at conf=0.10 (prod gives
  72–157 detections per cell at the same threshold).
- **Beethoven 5 p10:** 0 detections at conf=0.25, all 300 detections
  classified as `clefG` at conf=0.01 (prod gives 300 detections spread
  across 15+ classes).

The training **looked healthy by the loss numbers** — `cls_loss` dropped
from 90.93 (epoch 1) to 4.09 (epoch 30), a 95% reduction. The val mAP50
was uninformative (catalog val labels too noisy; see Finding 2 below).
The model "minimized" `cls_loss` by learning the shortcut of predicting
**nothing** rather than the actual task. This is what happens when many
training cells have systematically incomplete labels.

Weights archived at
`tools/omr/training/data/weights/_archive/2026-05-24-phase-h-attempt1-broken.pt`.
Production weights stay in place. The catalog labels are NOT
training-grade as-is.

## What we actually did vs. the handoff

The handoff in `tools/omr/training/HANDOFF_CATALOG_AUGMENTED_TRAINING.md`
called for a 30-epoch mix of full DSv2 (~165k images) +
200×-upsampled catalog (~80k effective). During the run we hit three
findings that forced a pivot:

### Finding 1 — Class-space mismatch (resolved)

Prod weights declare `nc=208` with DSv2-dense names (`clefG`, `clefF`).
Phase G catalog labels were emitted against the 146-class
`DEEPSCORES_V2_CLASSES` snapshot using SMuFL-form names (`gClef`,
`fClef`). Fine-tuning naively triggered
`Overriding model.yaml nc=208 with nc=146` → classification head
re-init → catastrophic forgetting (the Phase 3.4 v1 failure).

Fix: `phase_h_remap_labels.py` loads the prod weights' name list,
builds a snapshot→prod index map via name match + manual aliases for
the clef-naming differences (gClef↔clefG, etc.), and rewrites all 523
label files. 154,737/154,737 labels remapped, 0 dropped. Confirmed
post-remap: `Model summary: 210 layers, 43,790,208 parameters` (no
head re-init).

### Finding 2 — Orchestral val labels too noisy for mAP (acknowledged)

The catalog labels carry a documented `~50 px x-offset residual`
(PHASE_E_SUMMARY Phase F section). On the held-out val (124 images,
50,311 instances) this offset alone defeats IoU≥0.5 matching: **prod
weights themselves score mAP50 = 0.0001** on this set. The handoff's
"+5 mAP50 on orchestral holdout" target is therefore unmeasurable
with current data. Demoted to informational; WTC F1 was the only
real go/no-go gate.

### Finding 3 — Full mix-mode wall time is impractical (pivot)

Measured per-step time on RTX 4090 batch 4 imgsz 1280 = ~0.2 s. For
245k images/epoch (165k DSv2 + 80k upsampled catalog), that's ~3.4
hours/epoch, 100+ hours / ~$80 for 30 epochs. The handoff's "5–12 h"
estimate assumed batch 6 on A100 80 GB with a much smaller DSv2
sample. Pivoted to **catalog-only fine-tune** following Phase 3.4 v1b
precedent (warm-start preserves DSv2 knowledge via low LR; the v1b
run dropped WTC F1 only 0.3 pts after fine-tuning on 49 cells).

## Training config (final)

```
weights         deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt
data            data-catalog-only.yaml (nc=208, prod names)
                  train: 399 images (19 movements)
                  val:   124 images (7 holdout movements)
                  total labels: 154,737 (remapped to prod-208)
epochs          30 (no early-stop — val mAP slowly creeping)
batch           4 (24 GB RTX 4090 limit)
imgsz           1280
optimizer       SGD lr0=0.0005 momentum=0.937 warmup_epochs=1
aug             fliplr=0 flipud=0 hsv_h=0 hsv_s=0 hsv_v=0.4
                mosaic=0 degrees=1 (Phase 3.4 v1b proven)
wall time       13.86 min
cost            $0.75
```

## Training trajectory

Selected epochs from `results.csv`:

| Epoch | train/box_loss | train/cls_loss | train/dfl_loss | val/box_loss | val/cls_loss | val/mAP50 |
|---|---:|---:|---:|---:|---:|---:|
| 1   | 5.11 | 90.93 | 2.77 | 5.18 | 38.00 | 2e-5 |
| 3   | 5.07 | 13.34 | 2.48 | 5.10 | 7.88  | 5e-5 |
| 5   | 5.01 | 6.27  | 2.08 | 5.09 | 5.42  | 1e-5 |
| 10  | 4.71 | 4.51  | 1.68 | 4.71 | 3.87  | 5e-4 |
| 20  | 4.37 | 4.08  | 1.54 | 4.46 | 3.66  | 1.5e-3 |
| 30  | 4.32 | 4.09  | 1.53 | 4.40 | 3.64  | 1.85e-3 |

`cls_loss` plateaued at ~4 by epoch 10 and didn't materially change for
the remaining 20 epochs. **In hindsight this plateau was the model
having found the "predict nothing" shortcut, not real convergence.**

## Validation results — confirmed model collapse

### Bach WTC verdict set (30 cells, conf=0.10, imgsz=2048, MPS)

| Engine | Detections/cell range | F1 (3-cell sample) |
|---|---|---:|
| Prod | 72–157 | 99.2% |
| Phase H | **0** on every cell | — (no detections to score) |

### Orchestral spot-check: Beethoven 5 p10 (RGB rendered at 300 DPI)

Detection counts at different confidence thresholds:

| conf | Prod | Phase H |
|---|---:|---|
| 0.25 | 300 (78 noteheadBlackOnLine, 46 noteheadBlackInSpace, 27 slur, 19 tie, 14 clefG, 14 keyFlat, 14 rest8th, 12 restWhole, 10 noteheadHalfOnLine, …) | **0** |
| 0.10 | (similar distribution) | **0** |
| 0.05 | — | 9 (**all `clefG`**) |
| 0.01 | — | 300 (**all `clefG`**) |

The Phase H model has effectively collapsed to predicting a single
class (clefG) with near-zero confidence everywhere. At any reasonable
inference threshold (≥0.10), it produces zero detections.

## Root cause analysis

The catalog labels generated by Phase G have two systematic noise
sources documented in `PHASE_E_SUMMARY.md`:

1. **~50 px x-offset residual** on warped element positions.
2. **50–85% XML-match rate** on some non-Werke editions
   (B2 Litolff mvt 4, B2 Ricordi mvt 1+2, B8 imslp-06303 mvts 1–3,
   B8 imslp-875077 mvts 2–3). Cells that don't match get NO labels,
   even though the page is full of music symbols.

The combined effect during YOLO training: the model sees pages with
many visible symbols but only a small (and slightly misaligned) subset
of them labeled. The detection loss heavily penalizes "predict
something we don't have a label for" (false positives). The optimal
shortcut: predict **nothing**. SGD finds this minimum within ~10
epochs, then sticks.

In `cls_loss` terms this looks like normal convergence (91→4) because
when the model emits no high-confidence detections, the classification
loss is dominated by the "background" target which is trivially zero.
**`cls_loss` decreasing is not evidence of model improvement** when
trained on incomplete labels.

## Decision

- ❌ **Do NOT promote.** The model is functionally broken.
- ✅ Archived at `tools/omr/training/data/weights/_archive/2026-05-24-phase-h-attempt1-broken.pt`.
- ✅ Production weights (`omr-weights/deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`)
  stay in place.

## Lessons + next steps

### What this run did teach us

1. **The snapshot→prod label remapping (`phase_h_remap_labels.py`) is
   correct** and reusable for any future catalog data: 154,737 / 154,737
   labels remapped cleanly, model summary confirmed no head re-init.
2. **The 313 MB phase-h-data tarball + remote bootstrap + scp + tmux
   training loop on Vast.ai works end-to-end** for under $1 of compute.
   Future iterations can iterate quickly on this setup.
3. **The orchestral catalog val is structurally uninformative** until
   the x-offset is fixed. Don't gate future runs on its mAP.

### Required before any retry

1. **Fix the ~50 px x-offset.** The structural fix is described in
   `PHASE_E_SUMMARY.md` Phase F section: detect the clef body's
   right-edge in the PDF cell, trim both source and destination of the
   homography proportionally. Until this lands, catalog labels remain
   sub-training-grade even for fine-tuning.
2. **Drop low-match-rate movements from the catalog train set.** The
   "predict nothing" failure mode is driven by partially-labeled
   pages. Only train on movements with ≥95% XML match (which would
   remove ~9 of 26 mvts and ~30k labels, but the remaining 120k+
   would be clean signal).
3. **OR: switch to "ignore_unlabeled" training mode** by masking
   regions of cells that have no XML match, rather than feeding them
   as fully-labeled pages. Requires either:
   - Excluding entire pages where label density / page-area ratio is
     low, OR
   - Using a per-image confidence mask in the loss function
     (custom ultralytics callback).
4. **Add a clean smoke-validation step BEFORE long training.** A
   1-epoch fine-tune followed by a 5-cell WTC F1 check would have
   caught this collapse in <5 min, before committing to the 30-epoch
   run. Future retries should always run the WTC F1 check on the
   epoch-1 weights before continuing.

### Cost stayed within budget

User authorized $7–15 (mix mode). Actual spend: **$0.75** on the
pivoted catalog-only run + smoke tests. Plenty of credit remains
($67.97) for a corrected retry after the x-offset fix lands.

## Artifacts

```
benchmarks/omr-imslp-pipeline/
  phase_h_render_pages.py          ← 300-DPI render + downsize to 1280 max
  phase_h_build_splits.py          ← train/val + yamls (nc=208 + prod names)
  phase_h_remap_labels.py          ← snapshot-146 → prod-208 remapper (CORRECT, reusable)
  phase_h_build_bundle.sh          ← tarball builder
  phase_h_remote_bootstrap.sh      ← pip + DSv2 prep + {DATA_BASE} sub
  phase_h_launch_training.sh       ← training launcher
  phase_h_validate_local.sh        ← WTC scoring + orchestral spot-check
  phase_h_verify_overlay.py        ← visual label/image alignment check
  phase-h-data/                    ← gitignored (313 MB)
    images/<key>/p###.png          ← rendered cells (523 PNGs)
    labels/<key>/p###.txt          ← REMAPPED prod-208 labels
    labels.snapshot146/            ← backup of original snapshot-146 labels
    data-catalog-only.yaml         ← nc=208, prod names
    data-catalog-mix.yaml          ← (unused; would need DSv2 prep)
    train.txt / val.txt / train.repeated.txt / splits.json
  PHASE_H_RESULTS.md               ← this file

tools/omr/training/data/weights/
  _archive/
    2026-05-24-phase-h-attempt1-broken.pt   ← 88 MB; do NOT promote
```
