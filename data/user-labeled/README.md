# `data/user-labeled/` — the versioned label catalog

This directory is the **single source of truth** for hand-labeled YOLO training
data on real orchestral / piano scores. Every labeling session you run becomes
an immutable `vN-YYYY-MM-DD-descriptor/` directory; the catalog YAML unions
all versions so re-training picks them all up automatically.

The whole point of this layout is to **compound effort**: every minute spent
labeling shows up in every future model.

## Directory shape

```
data/user-labeled/
  README.md                          ← this file
  catalog.yaml                       ← generated; ultralytics consumes this
  _catalog_train.txt                 ← generated; list of train PNGs
  _catalog_val.txt                   ← generated; list of val PNGs
  _catalog_summary.json              ← generated; per-version counts + meta
  v1-2026-05-17-orchestral/          ← one labeling session
    images/<cell-id>.png             ← cropped cell PNGs (symlinks by default)
    labels/<cell-id>.txt             ← YOLO format: cls cx cy w h, normalized
    metadata.json                    ← labeler, date, totals, source verdicts
    data.yaml                        ← (optional, not required for retraining)
  v2-2026-06-NN-piano-solo/          ← second session — never modifies v1
    images/...
    labels/...
    metadata.json
```

**Rules:**

1. **Versions are immutable.** Once a `vN-…/` directory exists, never edit its
   contents. To fix a mistake, write a new version that supersedes the bad
   cells (and update the catalog generator if needed to skip the bad ones).
2. **One session = one directory.** Don't mix sessions inside a single version.
3. **Naming:** `vN-YYYY-MM-DD-descriptor/` — version, ISO date, short
   descriptor (`orchestral`, `piano-solo`, `bach-wtc-rerun`, …). The `vN`
   prefix is what `build_catalog_yaml.py` looks for; the rest is for humans.

The class vocabulary is the **208-class DeepScoresV2 list** (the same list the
YOLOv8l weights were trained against). It's read from the trained `.pt` file at
catalog-build time, with `tools/omr/training/data/deepscoresv2_208_classes.json`
as a fallback if torch isn't installed. After deduping, those 208 names
collapse to **168 unique classes** in the picker (DSv2 lists every glyph
twice across two annotation sets).

## The labeling UI

`tools/omr/annotate/server.py` is a local FastAPI app that renders an
interactive page per cell:

- a center overlay of the cell PNG with each detection drawn as a
  color-coded bbox (TP green, FP red, WRONG_CATEGORY orange,
  WRONG_BBOX purple, unsure grey, human-added blue);
- a left sidebar listing every detection with verdict badges;
- a right panel showing the cropped close-up, model prediction, and
  the verdict buttons (`✓ TP` / `✗ FP` / `🔄 Fix class` /
  `✂ Fix bbox` / `⏸ Unsure`);
- a class picker (tabs across 9 categories, grid of Bravura archetype
  thumbnails per tab) that opens when you hit `c` or `Fix class`.

See `tools/omr/annotate/READY-LABELING-UI.md` for the full hotkey list
and architecture notes.

## Workflow: add a labeling session

1. **Pick cells.** Use `tools/omr/annotate/select_cells_orchestral.py` (or its
   piano-solo cousin) to crop measure-cells from PDFs. Output: a benchmark
   manifest at `benchmarks/<phase>/cells.json` plus PNGs under
   `benchmarks/<phase>/cells/`.

2. **Pre-label with current best weights.**
   ```bash
   python3 -m tools.omr.annotate.run_yolo \
       --manifest        benchmarks/<phase>/cells.json \
       --cells           $(jq -r '.[].cell_id' benchmarks/<phase>/cells.json) \
       --weights         tools/omr/training/data/weights/<newest>.pt \
       --out-dir         benchmarks/<phase>/verdicts \
       --detections-out  benchmarks/<phase>/detections \
       --overlays-out    benchmarks/<phase>/overlays \
       --imgsz 2048 --conf 0.10 --device auto
   ```

3. **Human-label.** Launch the UI and click through:
   ```bash
   python3 -m tools.omr.annotate.server \
       --bench-dir benchmarks/<phase> --port 5050
   # (or, equivalently)
   python3 -m tools.omr.annotate.server \
       --verdicts-dir benchmarks/<phase>/verdicts
   ```
   Then open <http://127.0.0.1:5050>. Each cell gets a
   `<cell_id>.verdict.json` written in **schema_version 2** (see "Verdict
   schemas" below). Verdicts autosave 1.2 s after the last edit; the
   indicator in the top bar shows `saving…` / `saved` / `ERROR`.

   The UI is keyboard-first:

   | Key | Action |
   |---|---|
   | `t` | mark selected detection TP |
   | `f` | mark selected detection FP |
   | `c` | open the class picker (fix the class) |
   | `b` | enter draw-bbox mode (fix the bbox) |
   | `u` | mark unsure (drop from training) |
   | `n` / `p` | next / prev detection within the cell |
   | `Tab` / `Shift+Tab` | next / prev cell |
   | `1`–`9` | jump to category tab while the picker is open |
   | `Esc` | close picker / cancel draw mode |

   The class picker shows a tab per category (notehead / rest / accidental
   / clef / flag / dynamic / ornament / time_sig / structural) and a grid
   of Bravura archetype thumbnails for that category. Clicking a tile sets
   `human_corrected_class` and advances to the next pending detection.

   For "fix bbox" and "add missed detection", the UI enters draw mode:
   click-and-drag on the cell image to draw the new bbox. For fix-bbox
   the verdict becomes `WRONG_BBOX` and the class stays as the model's
   prediction (unless you also hit `c`). For add-missed the picker opens
   immediately after the drag so you can pick the class.

4. **Convert to YOLO labels.**
   ```bash
   python3 -m tools.omr.training.verdicts_to_yolo_labels \
       --verdicts-dir   benchmarks/<phase>/verdicts \
       --manifest       benchmarks/<phase>/cells.json \
       --version-name   v2-2026-06-15-piano-solo \
       --out-root       data/user-labeled \
       --labeler        sean \
       --description    "WTC book 1, 60 measure-cells across 5 preludes"
   ```
   The converter writes `data/user-labeled/v2-2026-06-15-piano-solo/`
   (`images/`, `labels/`, `metadata.json`) and never touches earlier versions.

5. **Rebuild the catalog.**
   ```bash
   python3 -m tools.omr.training.build_catalog_yaml \
       --root data/user-labeled --val-fraction 0.15
   ```
   This regenerates `catalog.yaml`, `_catalog_train.txt`, `_catalog_val.txt`,
   and `_catalog_summary.json`. The val split is per-version-deterministic
   (hash-seeded), so re-running with the same seed produces the same split —
   safe to re-run any time.

6. **Re-train.** Point fine-tuning at the new catalog (see next section).

## Verdict schemas

Two on-disk schemas live side-by-side. The labeling UI **writes
schema_v2**; the converter reads either and emits the same YOLO label
format from both.

### schema_version 2 (current)

The UI uses this for every new save. Bboxes and corrected classes are
stored inline in the verdict file, so the converter doesn't have to
look up the model's detection JSON to recover them.

```jsonc
{
  "cell_id": "beet5-p15-sys0-s0-m0",
  "schema_version": 2,
  "labeled_at_utc": "2026-05-17T07:00:00+00:00",
  "detections": [
    {
      "id": "D0",
      "verdict": "TP" | "FP" | "WRONG_CATEGORY" | "WRONG_BBOX" | "unsure" | null,
      "model_predicted_class": "noteheadBlackOnLine",
      "human_corrected_class": null,        // populated when WRONG_CATEGORY
      "model_predicted_category": "notehead",
      "human_corrected_category": null,
      "model_bbox": {"x": 100, "y": 200, "w": 12, "h": 10},
      "human_bbox": null,                   // populated when WRONG_BBOX
      "confidence": 0.89,
      "notes": ""
    }
  ],
  "added_detections": [
    {
      "id": "H0",                           // "H" prefix = human-added
      "human_class": "fermataAbove",
      "human_category": "ornament",
      "bbox": {"x": 350, "y": 180, "w": 18, "h": 8},
      "notes": ""
    }
  ]
}
```

### schema_version 1 (legacy, read-only)

Files written by the older markdown-editor server live in older bench
dirs (e.g. `benchmarks/omr-phase2.5/verdicts/`). They look like:

```jsonc
{
  "cell_id": "beet5-p10-sys0-s0-m0",
  "verdicts": [
    {"detection_id": "D0", "smufl_name": "accidentalFlat", "verdict": "FP"}
  ],
  "fn_noteheads": []
}
```

When the UI reads a v1 file it migrates to v2 in memory (so the labeler
sees a fully-populated v2 state). On first save the file is rewritten
as v2. The converter reads v1 directly without rewriting — old
versions of `data/user-labeled/` stay reproducible.

## Verdict → YOLO conversion rules

The converter (`verdicts_to_yolo_labels.py`) translates each decision
into a YOLO line `cls_id cx cy w h` (normalized) as follows.

### Schema v2 (canonical)

| Decision | YOLO bbox | YOLO class |
|---|---|---|
| `verdict: TP` | `model_bbox` | `model_predicted_class` |
| `verdict: WRONG_CATEGORY` | `model_bbox` | `human_corrected_class` |
| `verdict: WRONG_BBOX` | `human_bbox` | `human_corrected_class` if set, else `model_predicted_class` |
| `verdict: FP` | — | **dropped** (model hallucinated nothing real) |
| `verdict: unsure` | — | **dropped** (no usable signal) |
| `verdict: null` (pending) | — | **dropped** (not labeled yet) |
| `added_detections[]` (FN) | `bbox` | `human_class` |

### Schema v1 (legacy)

| Decision | YOLO bbox | YOLO class |
|---|---|---|
| `verdict: TP` | detection's bbox | detection's `smufl_name` |
| `verdict: TP` with `wrong_pitch` | same as TP | same as TP (pitch is downstream) |
| `verdict: FP` (no `actual_label`) | — | **dropped** |
| `verdict: FP` with `actual_label` | detection's bbox | `actual_label` |
| `verdict: unsure` or `""` | — | **dropped** |
| `fn_noteheads[].x_canonical/y_canonical` | synthesized at (x, y) with median-notehead w/h, fallback `(28, 32)` | `class_name` if set, else `noteheadBlackOnLine` |

## Re-training

The catalog is fine-tuning territory, not from-scratch — 200–2000 hand-labeled
cells is too small for from-scratch training on a 208-class detector. Start
from the latest DSv2-pretrained weights and fine-tune.

Canonical command (run from worktree root):

```bash
python3 -m tools.omr.training.train_yolo \
    --data    data/user-labeled/catalog.yaml \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-8shards-100ep.pt \
    --imgsz   2048 \
    --epochs  60 \
    --batch   4 \
    --lr0     0.0005 \
    --patience 15 \
    --mosaic  0.0 \
    --device  auto \
    --project tools/omr/training/data/runs \
    --name    finetune-catalog-$(date +%Y%m%d)
```

Notes on these knobs (they matter a lot at small dataset sizes):

- **`lr0=0.0005`** — 1/20 of the default (`0.01`). DSv2 pretraining is strong;
  a big LR will scramble the backbone. Start low, raise only if val loss
  plateaus too early.
- **`mosaic=0.0`** — mosaic augmentation pastes 4 random training images
  together. With ~200 images it ends up showing the model the same
  scrambled cells over and over and learns the seams. Disable.
- **`patience=15`** — early-stop if val mAP doesn't improve for 15 epochs.
  With small data, overfitting is the failure mode, not undertraining.
- **`imgsz=2048`** — orchestral cells are tall (~900 canonical px) so we want
  the detector to see them at their native scale, not downsampled. The
  pretrained weights were `8shards`/`imgsz=1280` but ultralytics supports
  any inference `imgsz`; matching train and inference at 2048 is the goal.
- **`batch=4`** — `imgsz=2048` is heavy on memory. On M-series MPS, 4 is
  usually the cap before OOM. Bump to 8 on a 24GB+ CUDA box.

After training, the resulting weights are at:
```
tools/omr/training/data/runs/finetune-catalog-<date>/weights/best.pt
```
Use those as the new pre-labeling weights for the *next* session — the loop
closes.

## Adding a new class type to the vocabulary

Don't. The 208-class list is fixed by the pretrained model — adding a class
requires retraining the model head from scratch. If you find yourself wanting
a new class (e.g. some specific articulation DSv2 didn't include), either:

  - Use an `actual_label: "<existing-class>"` mapping to fold it into the
    nearest existing class, or
  - File a followup to do a head-reset retrain on a different label space.

The 208-class JSON at `tools/omr/training/data/deepscoresv2_208_classes.json`
is a frozen snapshot. **Do not edit it.**

## FAQ

**Q: Why is the val set per-version instead of one global split?**
A: So that val numbers are comparable across re-builds. If you randomly
splat 15% of *everything* into val each time, the val set changes every
rebuild and your val mAP curve is noisy for no reason. Per-version splits
keep last month's val set intact while next month's session adds its own
val cells.

**Q: Can I delete or rename a version?**
A: Renaming yes (rebuild the catalog after); deleting yes if you genuinely
want it gone. Don't *edit* contents of an existing version — write a new
version instead.

**Q: How big should each session be?**
A: Whatever you can finish in a sitting. The catalog handles any size.
Sweet spot for a single sitting is probably 50–200 cells (≈4–16 hours of
labeling), but smaller is fine — even 30-cell sessions accumulate.

**Q: I changed my mind about a label. Can I re-label a cell?**
A: Yes — re-label it in the verdict UI (the cell's `.verdict.json` is
mutable), then **convert into a new version** with the corrected labels.
The catalog YAML will include both the old (wrong) and new (correct)
copies of the cell, which is bad. To avoid duplicates, copy the relevant
cell IDs out of the old `vN/labels/` (and `images/`) into the new
version, then delete them from the old version. (This is the one
"editing an old version" exception — and even then, prefer just
abandoning the old version and starting a fresh one if many cells are
affected.)

**Q: Where does the catalog point training? Why list-of-paths files?**
A: `catalog.yaml` has `train: data/user-labeled/_catalog_train.txt` and
`val: data/user-labeled/_catalog_val.txt`. Ultralytics accepts a text
file of one image path per line, which lets us union version directories
without copying anything.
