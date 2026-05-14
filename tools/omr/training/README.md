# DeepScoresV2 -> YOLOv8 Training Pipeline

End-to-end pipeline to fine-tune a YOLOv8m detector on the DeepScoresV2
music-symbol dataset, then evaluate the resulting weights against this
project's actual cells.

**Status: scaffold only.** The dataset has not been downloaded and no
weights have been trained. Every script in this directory was written to
be runnable later on a GPU machine — see "Why we don't use this yet"
below for the cost/benefit assessment.

---

## TL;DR commands (in order)

```bash
# 0. Install training deps (one-time, on the GPU machine)
pip install -r tools/omr/training/requirements-training.txt

# 1. Download DeepScoresV2 dense subset (~6.5 GB compressed)
python3 -m tools.omr.training.download_dataset --out data/deepscoresv2/
tar -xzf data/deepscoresv2/ds2_dense.tar.gz -C data/deepscoresv2/

# 2. Convert to YOLO format (writes data/deepscoresv2-yolo/data.yaml)
python3 -m tools.omr.training.prepare_yolo_data \
    --src data/deepscoresv2 --dst data/deepscoresv2-yolo

# 3. Smoke-test the env (1 epoch on a synthetic 10-image dataset, ~30 s)
python3 -m tools.omr.training.train_yolo --smoke

# 4. Real fine-tune (50 epochs at imgsz=1280; ~10-16 h on RTX 3090)
python3 -m tools.omr.training.train_yolo \
    --data data/deepscoresv2-yolo/data.yaml \
    --weights yolov8m.pt \
    --epochs 50 --imgsz 1280 --batch 16 --device 0

# 5. Evaluate the new best.pt on DeepScoresV2 val + WTC sample cells
python3 -m tools.omr.training.eval_on_score_cells \
    --weights data/deepscoresv2-yolo/runs/ds2-yolov8m/weights/best.pt \
    --data data/deepscoresv2-yolo/data.yaml \
    --cells benchmarks/omr-phase2.5/cells.json
```

---

## Files in this directory

| File | Purpose |
|---|---|
| `__init__.py` | Package marker |
| `deepscores_classes.py` | Embedded snapshot of DeepScoresV2's ~135 class names (also lives inside the dataset's own JSON) |
| `download_dataset.py` | Fetches the dataset archive from Zenodo |
| `prepare_yolo_data.py` | Converts DeepScoresV2 JSON -> YOLO `.txt` labels + `data.yaml` |
| `train_yolo.py` | Wraps `ultralytics.YOLO.train()` |
| `eval_on_score_cells.py` | mAP@0.5 on DeepScoresV2 val + raw counts on WTC cells |
| `requirements-training.txt` | Pinned training-time deps (ultralytics, PyYAML, Pillow) |

---

## Dataset

**DeepScoresV2** (Tuggener et al., ICPR 2020/2021) is the canonical
training corpus for printed-music symbol detection.

- ~300k synthetically-rendered score pages
- ~135 SMuFL-aligned symbol classes
- Oriented bounding box annotations (we use the axis-aligned `a_bbox`
  field — YOLOv8 standard, not OBB)
- License: CC BY-SA 4.0 (cite Tuggener et al. 2020 in derived work)

### Where to download

The script targets the Zenodo release:

- Zenodo record: <https://zenodo.org/records/4012193>
- Project landing page: <https://tuggeluk.github.io/>
- Annotation toolkit: <https://github.com/yvan674/obb_anns>

If the URLs in `download_dataset.py` 404 because the record was updated,
visit the Zenodo search page and update the manifest:

> <https://zenodo.org/search?q=DeepScoresV2>

Two archive variants are published:

- **Dense subset** (`ds2_dense.tar.gz`, ~6.5 GB) — recommended for an
  initial fine-tune. Default.
- **Complete set** (`ds2_complete.tar.gz`, ~80 GB) — pass `--full`.
  Overkill for a first pass; downloads can take hours and require
  serious disk.

After download, extract:

```bash
tar -xzf data/deepscoresv2/ds2_dense.tar.gz -C data/deepscoresv2/
```

The expected layout is:

```
data/deepscoresv2/
    images/
        lg-NNNN-foo.png
        ...
    deepscores_train.json   # COCO+OBB-style annotations
    deepscores_test.json
```

`prepare_yolo_data.py` then mirrors this into:

```
data/deepscoresv2-yolo/
    images/train/    (symlinks to data/deepscoresv2/images/...)
    images/val/
    labels/train/    (one .txt per image)
    labels/val/
    data.yaml
```

---

## Hardware tiers and time estimates

| Tier | VRAM | 50-epoch ETA | Notes |
|---|---|---|---|
| Apple Silicon M1/M2/M3 (MPS) | unified | 12-24 h | Works via `--device mps`, but slow per watt. Suitable for smoke tests only. |
| RTX 3070/3080 (8-10 GB) | 8-10 GB | 14-20 h | OK but may need `--batch 8` if OOM at `imgsz=1280`. |
| RTX 3090/4090 (24 GB) | 24 GB | 10-16 h | Sweet spot. Recommended cloud-rental target. |
| A100 40 GB | 40 GB | 6-10 h | Fastest practical option. |
| A100 / H100 80 GB | 80 GB | 4-8 h | Diminishing returns vs A100 40 GB at this batch size. |

**Disk usage:**

- Dense archive: ~6.5 GB compressed, ~12 GB extracted
- YOLO conversion adds: ~0 GB (symlinks images by default) or +12 GB
  with `--no-symlink`
- ultralytics `runs/` directory: ~500 MB per run (best.pt + last.pt +
  plots + per-epoch logs)

**Recommended: 30-40 GB free disk for a clean run.**

---

## Cheapest path to trained weights

Renting cloud GPU is currently the cheapest option:

| Provider | GPU | Price/hr (spot/preemptible) | 12-h fine-tune cost |
|---|---|---|---|
| Lambda Labs | RTX A6000 / A100 40 GB | ~$0.80-1.30 | ~$10-16 |
| Vast.ai | RTX 3090 (community) | ~$0.20-0.50 | ~$2.50-6 |
| RunPod | RTX 3090 / A100 | ~$0.40-2.00 | ~$5-24 |
| AWS spot (g5.xlarge) | A10G 24 GB | ~$0.40-0.60 | ~$5-8 |

**Recommendation: Vast.ai RTX 3090 spot instance, ~$5 round trip.**
Budget half a day of wall-clock to be safe (download + extract + train
+ eval). Total cost incl. transfer should land around $10.

---

## Smoke test

Before launching a real training run, validate that ultralytics, torch,
and the GPU driver all work end-to-end:

```bash
python3 -m tools.omr.training.train_yolo --smoke
```

This synthesizes a 10-image, 1-class dataset, runs 1 epoch at
`imgsz=320` and `batch=2`, and prints the resulting metrics dict. Should
take <2 min on MPS or <30 s on a 3090. If this fails, the real training
run will too.

The dry-run for data conversion (no real dataset required) is:

```bash
python3 -m tools.omr.training.prepare_yolo_data --dry-run --dst /tmp/yolo-dry
```

This synthesizes a 2-image mock matching DeepScoresV2's JSON shape and
exercises the full conversion path.

---

## Interpreting the eval output

`eval_on_score_cells.py` prints two blocks:

```json
{
  "deepscoresv2_val": {
    "map": 0.71,        // mAP@0.5:0.95 (the strict benchmark number)
    "map50": 0.84,      // mAP@0.5 (the looser, more commonly reported one)
    "map75": 0.79,
    "mp": 0.86,         // mean precision
    "mr": 0.81          // mean recall
  },
  "score_cells": {
    "n_sampled": 5,
    "per_cell": [
      {
        "cell_id": "wtc-p5-sys0-s0-m0",
        "n_detections": 12,
        "category_breakdown": {"notehead": 10, "barline": 1, "stem": 1},
        ...
      },
      ...
    ]
  }
}
```

**What good looks like:**

- `map50 >= 0.80` on DeepScoresV2 val (published baselines for YOLOv8m
  on this dataset hover around 0.83-0.88)
- `category_breakdown` on WTC cells contains mostly `notehead`, `stem`,
  `barline`, `clef` — not `unknown`
- Detection counts on a WTC piano-staff cell typically 8-20

**What bad looks like:**

- `map50 < 0.50` -> training didn't converge; check loss curves in
  `runs/ds2-yolov8m/results.csv`
- `category_breakdown` dominated by `unknown` -> class-name mapping in
  `tools/omr/yolo_detector.py` doesn't match the names in the trained
  model's `model.names`. Inspect and extend `_CATEGORY_MAP`.

---

## Why we don't use this yet

As of 2026-05-14:

1. **Single-engine OMR is not yet the bottleneck.** Phase 2.7's template
   matcher hits 100% precision on n=3 fully-annotated WTC cells. The
   immediate next step is expanding the annotation set (n=3 -> n=20+) to
   find where the template matcher *actually* fails, not building a
   second detector that competes with an unmeasured baseline.

2. **Training is a 10-20 h commitment of GPU + wall-clock + ~$10
   cloud spend.** Cheap, but not free. We should do it once we know what
   we want it to be better at.

3. **YOLOv8 with DeepScoresV2 fine-tuning gets a known ~85% mAP@0.5 on
   the val set.** That's a real number, but DeepScoresV2 is synthetic.
   The gap between "synthetic val mAP" and "real-scan detection
   quality" is large and only the `eval_on_score_cells` step will tell
   us how big.

4. **The wiring is already in place.** `tools/omr/yolo_detector.py` and
   `tools/omr/annotate/run_yolo.py` already accept a `--weights`
   argument. When this pipeline produces a `best.pt` we can swap it
   straight in without code changes.

**Pre-conditions to revisit this:** template matcher annotated to n=20+,
template-matcher precision visibly degrading (say <90% on some cells),
or a clear class of failure (e.g. accidentals on dense pages) that
points at a detector-quality root cause.

---

## Known unknowns

- **DeepScoresV2 annotation schema version drift.** The JSON shape in
  `prepare_yolo_data.py` was derived from the published paper + the
  `obb_anns` GitHub README. The actual JSON ships variations (`cat_id`
  is sometimes a list, sometimes a string); the parser handles both
  paths but a future release could introduce a third. If parsing
  silently produces zero annotations, dump one record and compare
  against the parser's expected keys.

- **Class name string match between trained weights and
  `_CATEGORY_MAP`.** The mapping in `tools/omr/yolo_detector.py`
  normalizes via `lower()` and `isalnum()` so it tolerates
  `"noteheadBlackOnLine"` vs `"notehead_black_on_line"` vs
  `"NoteheadBlack"`. If a real trained model uses entirely different
  names (e.g. integer indices into a different ontology), the
  detector will emit `category="unknown"` and put the raw label in
  `smufl_name`. This is recoverable — extend the mapping — but it
  means the first eval on WTC cells may show all detections as
  "unknown" until the mapping is filled in.

- **Image-size choice (`imgsz=1280`).** Music symbols are small; 1280
  is the largest size that fits comfortably on a single 24 GB GPU at
  `batch=16`. If memory pressure hits, halve `batch` before reducing
  `imgsz` — smaller symbols suffer disproportionately at lower
  resolution.

- **Augmentation defaults.** ultralytics' default training
  augmentations include mosaic + random affine; these are fine for
  natural images but can corrupt music staves (rotation breaks pitch
  semantics). If retraining shows lower recall than expected, pass
  `--extra-kwargs degrees=0 perspective=0 mosaic=0.5` (TODO: surface
  these as flags rather than buried in `extra_kwargs`).

---

## Citations

If you publish or share derived work, cite:

> Tuggener, L., Satyawan, Y. P., Pacha, A., Schmidhuber, J., & Stadelmann, T.
> (2020). *The DeepScoresV2 Dataset and Benchmark for Music Object Detection.*
> 25th International Conference on Pattern Recognition (ICPR), 9188-9195.

Plus ultralytics YOLOv8 (Jocher et al., 2023) and any model card you
publish for the resulting weights.
