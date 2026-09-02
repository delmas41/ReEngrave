# Phase real-FT — Ready to label (`v1-2026-05-17-orchestral`)

**Status:** ✅ **READY** — 186 orchestral cells prepped. Pre-labels were
regenerated 2026-05-18 with the newer
`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` weights (Phase 3.3 model,
F1 98.8% on the held-out verdict cells, +2.5 pts vs the 8-shard model).
Original 8-shard pre-labels preserved at `detections-8shards-old/`,
`verdicts-8shards-old/`, `overlays-8shards-old/` for reference. Labels
in this session will land in the new versioned catalog under
[data/user-labeled/v1-2026-05-17-orchestral/](../../data/user-labeled/).

**Worktree:** `.claude/worktrees/cool-kare-05197c/`
**Benchmark dir:** `benchmarks/omr-phase-realft/`
**Catalog dir (output):** `data/user-labeled/v1-2026-05-17-orchestral/`

## What changed in this session

1. **Catalog tooling shipped.** Each labeling session now becomes an
   immutable `vN-DATE-NAME/` directory under `data/user-labeled/`, and the
   catalog YAML unions all versions for retraining. See
   [data/user-labeled/README.md](../../data/user-labeled/README.md) for
   the full contract. *(Superseded 2026-09-02: the union is no longer
   automatic — membership comes from `data/user-labeled/catalog-versions.txt`,
   a recorded training decision; the README has the current contract.)*
   Three new scripts:

   - [tools/omr/training/verdicts_to_yolo_labels.py](../../tools/omr/training/verdicts_to_yolo_labels.py)
     — turns `<cell>.verdict.json` files into a versioned YOLO dataset.
   - [tools/omr/training/build_catalog_yaml.py](../../tools/omr/training/build_catalog_yaml.py)
     — rebuilds `catalog.yaml` (what training points at) by unioning all
     version dirs with per-version 15% val holdouts.
   - [tools/omr/training/data/deepscoresv2_208_classes.json](../../tools/omr/training/data/deepscoresv2_208_classes.json)
     — the 208-class vocabulary, pulled directly from
     `deepscoresv2-yolov8l-8shards-100ep.pt`'s `model.names`. Used as a
     torch-free fallback by both scripts.

2. **imgsz=2048 re-run tried and reverted.** The prior session expected
   `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt` to land and noted that
   "even 8shards at imgsz=2048 will produce much cleaner pre-labels."
   I tried that — it did **not** hold up. At imgsz=2048 the un-fine-tuned
   8shards weights over-fire badly: detection count jumps from 14,598
   (median 65) at imgsz=640 to 36,668 (median 225) at imgsz=2048, with
   83% of detections being notehead-on/in-space — likely overlapping
   boxes for the same notehead since NMS doesn't suppress across the
   bigger feature map. Labeling burden tripled with no recall benefit
   visible by spot-check. The imgsz=2048 run is archived under
   `detections-imgsz2048-aborted/`, `overlays-imgsz2048-aborted/`,
   `verdicts-imgsz2048-aborted/` for posterity, but the live
   `detections/`, `overlays/`, `verdicts/` are back on the imgsz=640
   baseline.

   **Implication for the planned fine-tune:** the imgsz=2048 win was
   supposed to come from FINE-TUNING at that size, not just inferring at
   it. Once a v1 fine-tune trained at imgsz=2048 lands, *those* weights
   will produce clean imgsz=2048 pre-labels. For now, imgsz=640 is the
   right call.

## Cell counts (unchanged from the prior session)

| Piece | Pages used (1-based) | Cells |
|---|---|---|
| Beethoven Symphony No. 5 | 5, 15, 25, 35 | 40 |
| Mahler Symphony No. 5 | 25, 70, 130, 180, 220 | 50 |
| Debussy *La Mer* (orch. score) | 15, 45, 75, 105 | 48 |
| Ravel *Bolero* | 5, 15, 25, 35 | 48 |
| **Total** | | **186** |

Target was 200 ± 20; 186 lands inside the acceptable band (180–220).

- **Beethoven 5 page 10 is excluded** (held-out test from phase 3.1).
- Beethoven 5 page 1 was originally on the plan but it's a title page
  with no staves — phase-1 selection found 0 cells.
- Brahms 1, Beethoven 7/9, Schubert 8, Tchaikovsky 5 were **not**
  downloaded — IMSLP returned bot-check HTML for every URL tried. The
  Mahler / Debussy / Ravel local PDFs substitute. To add Brahms, drop a
  PDF in `data/orchestral_pdfs/` and run an incremental cell-selection
  pass (it'll become its own `vN-…-brahms/` in the catalog).

## Instrument-family / scan-quality spread

| Piece | Distinct staves | Scan quality |
|---|---|---|
| Beethoven 5 | 15 (s0–s17) | **low** — vintage 1-bit scan, heavy ink binarization |
| Mahler 5 | 20 (s0–s23) | medium — visible Sauvola artifacts but recognizable |
| Debussy *La Mer* | 18 (s0–s19) | medium — dense orchestration, some heavy ink |
| Ravel *Bolero* | 28 (s0–s29) | **high** — clean modern Eulenburg-style scan |

Cells were sampled with uniform stride across each page's (system ×
staff × measure) reading order, so the mix spans top-of-page (winds),
middle (strings), and bottom (low brass / percussion) for each piece.

## Cell extraction

Selector:
[tools/omr/annotate/select_cells_orchestral.py](../../tools/omr/annotate/select_cells_orchestral.py)
— monkey-patches `measure_extractor.PAD_ABOVE/BELOW_STAFF_LINES` to **2.5**
staff-line-spacings (default is 4, which spills into adjacent orchestral
staves; 1.25 clips ledger lines and dynamics). PAD=2.5 captures dynamics,
slurs, and most ledger lines for a single staff-measure without serious
overlap into the neighboring instrument.

Manifest: [cells.json](cells.json).

## Pre-labeling weights

`tools/omr/training/data/weights/deepscoresv2-yolov8l-8shards-100ep.pt`
(88 MB), run at `imgsz=640`.

Inference args:
`--conf 0.10 --device auto --time-n-runs 1 --imgsz 640`.

To re-run with newer weights once they exist:

```bash
cd .claude/worktrees/cool-kare-05197c

python3 -m tools.omr.annotate.run_yolo \
    --manifest benchmarks/omr-phase-realft/cells.json \
    --cells $(python3 -c "import json; print(' '.join(e['cell_id'] for e in json.load(open('benchmarks/omr-phase-realft/cells.json'))))") \
    --weights tools/omr/training/data/weights/<new-weights>.pt \
    --out-dir benchmarks/omr-phase-realft/verdicts \
    --detections-out benchmarks/omr-phase-realft/detections \
    --overlays-out benchmarks/omr-phase-realft/overlays \
    --baseline-verdicts "" \
    --conf 0.10 --device auto --imgsz 640 --time-n-runs 1
```

If the new weights were trained at imgsz=2048, swap `--imgsz 640 → 2048`.
That overwrites `verdicts/`, `detections/`, `overlays/` in place. **The
cell PNGs and `cells.json` stay valid.** Any `.verdict.json` files Sean
filled are preserved (`run_yolo.py` only writes `.md` pre-labels and
detection JSONs).

## How to launch the labeling UI

From the worktree root:

```bash
python3 -m tools.omr.annotate.server \
    --bench-dir benchmarks/omr-phase-realft \
    --port 5050
```

Open <http://127.0.0.1:5050>. Endpoints (smoke-tested in this session):

- `/` — cell list with status badges (empty / partial / pre-filled)
- `/cells/<cell_id>` — detail view with overlay PNG + per-detection radio buttons
- `/cells/<cell_id>/overlay.png` — annotated cell with numbered detection boxes
- `/cells/<cell_id>/verdict.json` — GET returns current state, POST writes
  `<cell_id>.verdict.json` next to the `.md`
- `/queue` — flies through one detection at a time; **C/F/P/U** keys for
  TP / FP / Wrong-Pitch / Unsure, arrow keys to navigate.

A POST round-trip on `beet5-p5-sys0-s0-m0` was tested in this session
(test verdict cleaned up before handoff). `verdicts/` currently contains
only the pre-filled `.md` files.

## Estimated labeling time

5–10 min/cell × 186 = **15–31 hours** total. At ~78 dets/cell average
(median 65) and ~5–10 sec/click via keyboard shortcuts, that lines up.
The 200+ detection cluster (10 cells, mostly Mahler tutti) will take
longer than average; the 1–9 cluster (15 cells, Bolero sparse) will fly
by.

## Detection distribution (imgsz=640)

```
n_dets   cells
0        0
1–9      15    ← Bolero sparse measures + a few empty Beethoven cells
10–49    58    ← Bolero / clean simple measures (label target zone)
50–99    58    ← typical orchestral measure
100–199  45    ← dense Mahler / Debussy tutti
200+     10    ← heavily over-detected dense passages
```

Total: 14,598 detections across 186 cells (median 65, mean 78, max 300).

The 5 worst offenders (skip / skim on first pass, come back later):

- `mahler5-p25-sys0-s1-m3` — 300 detections
- `mahler5-p130-sys2-s12-m11` — 285
- `lamer-p105-sys0-s7-m4` — 277
- `mahler5-p70-sys0-s0-m0` — 255
- `beet5-p15-sys1-s3-m2` — 233

## When labeling is done — feeding the catalog

The whole point of this session is that **labels compound**. Follow the
sequence below; each step is a single command from the worktree root.

### 1. Convert the verdicts into a versioned catalog entry

```bash
python3 -m tools.omr.training.verdicts_to_yolo_labels \
    --verdicts-dir benchmarks/omr-phase-realft/verdicts \
    --manifest     benchmarks/omr-phase-realft/cells.json \
    --version-name v1-2026-05-17-orchestral \
    --out-root     data/user-labeled \
    --labeler      sean \
    --description  "Beethoven 5 / Mahler 5 / La Mer / Bolero, 186 cells, imgsz=640 pre-labels"
```

Output:

```
data/user-labeled/v1-2026-05-17-orchestral/
  images/<cell>.png    (symlinks back to benchmarks/.../cells/)
  labels/<cell>.txt    (YOLO format: cls cx cy w h)
  metadata.json
```

### 2. Rebuild the catalog YAML

```bash
python3 -m tools.omr.training.build_catalog_yaml \
    --root data/user-labeled --val-fraction 0.15
```

Regenerates `data/user-labeled/catalog.yaml` (what fine-tuning points
at), plus `_catalog_train.txt` and `_catalog_val.txt`. The 15% val split
is per-version-deterministic (hash-seeded), so re-running with the same
`--seed reengrave` produces the same split — safe to re-run any time.

### 3. Spawn the fine-tune task

Open a **separate** spawn (don't fine-tune from this session) with:

> Fine-tune YOLOv8l on the catalog at `data/user-labeled/catalog.yaml`
> using the canonical command in
> [data/user-labeled/README.md](../../data/user-labeled/README.md#re-training).
> Start from `deepscoresv2-yolov8l-8shards-100ep.pt`, imgsz=2048,
> lr0=0.0005, mosaic=0.0, 60 epochs with patience=15. Evaluate the
> resulting weights against Bach WTC (`benchmarks/omr-phase2.5/`) and
> the held-out Beethoven 5 page 10 (`benchmarks/omr-phase3.1/`), report
> F1 deltas vs. the 8shards baseline, and copy the best weights into
> `tools/omr/training/data/weights/` with a date-stamped name. That
> weight then becomes the pre-labeling base for the next labeling
> session, closing the loop.

## Future labeling sessions

Same flow, different `--version-name`. Suggested cadence:

| Session | What to label | Expected catalog dir |
|---|---|---|
| 2 | Piano solo (WTC, Chopin etudes) — fills in the simple-density end | `v2-2026-NN-NN-piano-solo/` |
| 3 | Brahms / Tchaikovsky orchestral — once IMSLP cooperates | `v3-2026-NN-NN-romantic-orchestral/` |
| 4 | Targeted FP-heavy cases — re-label cells where the new model still over-detects | `v4-2026-NN-NN-fp-targeted/` |

Don't touch `v1-2026-05-17-orchestral/` after this session. If labels in
it turn out wrong, override them by **adding** the corrected cell to a
later version (the catalog will include both — you'd then trim the bad
copies out of v1 by hand, but only as an exception).

## Tool changes that landed in this worktree

- **New (this session):** [tools/omr/training/verdicts_to_yolo_labels.py](../../tools/omr/training/verdicts_to_yolo_labels.py)
  — verdict-JSON → versioned YOLO dataset converter.
- **New (this session):** [tools/omr/training/build_catalog_yaml.py](../../tools/omr/training/build_catalog_yaml.py)
  — catalog YAML builder unioning all `vN-…/` version dirs.
- **New (this session):** [tools/omr/training/data/deepscoresv2_208_classes.json](../../tools/omr/training/data/deepscoresv2_208_classes.json)
  — torch-free 208-class name fallback.
- **New (this session):** [data/user-labeled/README.md](../../data/user-labeled/README.md)
  — the catalog contract.
- **Carried over from prior session:** [tools/omr/annotate/select_cells_orchestral.py](../../tools/omr/annotate/select_cells_orchestral.py)
  — per-instrument cell selector with tight padding.
- **Carried over from prior session:** [tools/omr/annotate/run_yolo.py](../../tools/omr/annotate/run_yolo.py)
  — `--overlays-out` and `--imgsz` flags.

## Known caveats

- **Source-PDF binarization.** Beethoven 5 / *La Mer* cells look heavily
  inked because the source PDFs are 1-bit-equivalent vintage scans;
  Sauvola at 600 DPI then thickens everything further. This is realistic
  data for the real-world OMR pipeline, but the model will fight visual
  noise during fine-tuning. If accuracy plateaus, consider running
  preprocessing at higher k (`binarize(rgb, k=0.4)`) or skipping the
  binarize step entirely for these PDFs.
- **`staff (structural)` over-detection.** The DeepScoresV2-trained
  model emits a separate `staff` detection per visible staff line; many
  cells have several of these. The labeling UI shows them as separate
  detections. Leave them in — fine-tuning should learn to suppress them
  once we have labels saying "no staff detection here". If a `staff`
  detection is on a real staff line, mark FP. If it actually covers a
  symbol (rare), mark TP + actual_label.
- **PAD=2.5 graze.** A handful of cells (mostly Mahler tutti measures)
  show a thin band of the adjacent instrument's outer staff lines.
  Don't label detections in those bands — they belong to the next staff.
- **FN noteheads only carry (x, y, pitch).** The labeling UI only
  captures a center point for human-added noteheads. The converter
  synthesizes a bbox from the median TP-notehead size in the same cell
  (default `(28, 32)` canonical px), and defaults the class to
  `noteheadBlackOnLine`. If you find yourself wanting to flag non-notehead
  symbols as FN, the converter currently can't represent that — flag it
  as a followup to extend the UI rather than working around it.
- **imgsz=2048 archived for diagnosis, not for labeling.** The
  `*-imgsz2048-aborted/` directories contain the over-firing run. If
  you want to inspect why imgsz=2048 broke (e.g. NMS tuning), they're
  there. Otherwise feel free to delete them.
