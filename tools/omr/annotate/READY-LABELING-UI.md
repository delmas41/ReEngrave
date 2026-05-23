# READY — interactive labeling UI (v1, 2026-05-17)

The legacy markdown-editor labeling workflow has been replaced with an
**interactive FastAPI app** that renders one HTML page per cell with
canvas-overlay bbox visualization, a categorized SMuFL archetype
picker, and keyboard hotkeys for sub-second-per-decision throughput.

Built in this session:

| File | Purpose |
|---|---|
| [tools/omr/annotate/server.py](server.py) | FastAPI app — routes, schema, v1→v2 migration, image crops |
| [tools/omr/annotate/build_archetypes.py](build_archetypes.py) | One-shot: render 168 Bravura PNGs into `static/archetypes/` |
| [tools/omr/annotate/static/index.html](static/index.html) | Cell-list landing page |
| [tools/omr/annotate/static/index.js](static/index.js) | Cell-list filter/search |
| [tools/omr/annotate/static/cell.html](static/cell.html) | Labeling page skeleton |
| [tools/omr/annotate/static/cell.js](static/cell.js) | Labeling page logic (canvas + picker + hotkeys + autosave) |
| [tools/omr/annotate/static/app.css](static/app.css) | Shared styles for both pages |
| [tools/omr/annotate/static/bravura/Bravura.otf](static/bravura) | Bravura font (SMuFL reference, SIL OFL) |
| [tools/omr/annotate/static/bravura/glyphnames.json](static/bravura/glyphnames.json) | SMuFL name → codepoint map |
| [tools/omr/annotate/static/archetypes/](static/archetypes/) | 168 × 72px PNG thumbnails — one per unique class |
| [tools/omr/annotate/static/archetypes/README.md](static/archetypes/README.md) | DSv2 class → SMuFL glyph mapping table |

Modified (extended for schema_v2):

| File | Change |
|---|---|
| [tools/omr/training/verdicts_to_yolo_labels.py](../training/verdicts_to_yolo_labels.py) | Dispatches on `schema_version`; v2 reads bbox + class inline from the verdict, v1 falls back to the original detection-join path |
| [data/user-labeled/README.md](../../../data/user-labeled/README.md) | Documents v2 schema, the UI launch / hotkeys, and the new conversion table |

---

## Launch

```bash
# From the worktree root:
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-phase-realft
# or:
python3 -m tools.omr.annotate.server --verdicts-dir benchmarks/omr-phase-realft/verdicts
# (the bench dir is the verdicts dir's parent)
```

Then open **<http://127.0.0.1:5050>** in a browser. Pick a cell from
the list; the labeling page opens with the cell PNG overlaid with
every detection bbox.

Existing schema_v1 verdict files (e.g. in `benchmarks/omr-phase2.5/`)
load transparently — the server migrates them to v2 in memory and
writes v2 on first save. Old verdicts in `benchmarks/omr-phase2.5/`
are not modified until the labeler touches them.

---

## Hotkeys

| Key | Action |
|---|---|
| `t` | mark selected detection **TP** |
| `f` | mark selected detection **FP** (drops it) |
| `c` | open the **class picker** (fix the class — verdict becomes `WRONG_CATEGORY`) |
| `b` | enter **draw-bbox** mode (fix the bbox — verdict becomes `WRONG_BBOX`) |
| `u` | mark **unsure** (drops it) |
| `n` / `p` | next / prev detection inside the cell |
| `Tab` / `Shift+Tab` | next / prev cell (flushes save first) |
| `1`–`9` | jump to category tab while the picker is open |
| `Esc` | close picker / cancel draw mode |

`t`/`f`/`u` and clicking a class in the picker auto-advance to the
next pending detection so a fluent labeler can stay on the home row.

---

## Schema v2 (what the UI saves)

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
      "human_corrected_class": null,          // set when WRONG_CATEGORY
      "model_predicted_category": "notehead",
      "human_corrected_category": null,
      "model_bbox": {"x": 100, "y": 200, "w": 12, "h": 10},
      "human_bbox": null,                     // set when WRONG_BBOX
      "confidence": 0.89,
      "notes": ""
    }
  ],
  "added_detections": [
    {
      "id": "H0",                             // "H" = human-added
      "human_class": "fermataAbove",
      "human_category": "ornament",
      "bbox": {"x": 350, "y": 180, "w": 18, "h": 8},
      "notes": ""
    }
  ]
}
```

Why this layout: the converter no longer has to look up
`detections/<cell>.json` to recover a bbox — everything needed to emit
a YOLO label is inline. If `run_yolo.py` is re-run between labeling
and conversion, the existing labels stay valid.

---

## Converter behavior (v2)

`tools/omr/training/verdicts_to_yolo_labels.py` reads either schema.
For v2 the rules are:

| Verdict | YOLO bbox | YOLO class |
|---|---|---|
| `TP` | `model_bbox` | `model_predicted_class` |
| `WRONG_CATEGORY` | `model_bbox` | `human_corrected_class` |
| `WRONG_BBOX` | `human_bbox` | `human_corrected_class` if set else `model_predicted_class` |
| `FP` | — | dropped |
| `unsure` | — | dropped |
| `null` (pending) | — | dropped |
| `added_detections[]` | `bbox` | `human_class` |

For v1, the rules are unchanged from before.

---

## End-to-end smoke test (run 2026-05-17)

1. `python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-phase-realft`
2. `GET /api/cell/beet5-p15-sys0-s0-m0/verdict` → returns fresh
   schema_v2 state, source=`new`, 18 detections.
3. `POST /api/cell/beet5-p15-sys0-s0-m0/verdict` with 2 TP, 1 FP, 1
   WRONG_CATEGORY (→ noteheadHalfOnLine), 1 WRONG_BBOX (→ restHBar
   with new bbox), 1 added (fermataAbove). 13 pending.
4. File appears on disk as `<cell>.verdict.json` with
   `schema_version: 2` and `labeled_at_utc` populated.
5. `python3 -m tools.omr.training.verdicts_to_yolo_labels …
   --version-name v-smoke-…` reports:
   - 2 TP, 1 WRONG_CATEGORY, 1 WRONG_BBOX, 1 added, 1 FP-dropped, 13 pending-dropped
   - 5 YOLO labels written
6. Decoding the labels back to canonical pixels confirms each row uses
   the correct bbox source (model_bbox for TP/WRONG_CAT, human_bbox
   for WRONG_BBOX, bbox for added) and the correct class.
7. `python3 -m tools.omr.training.build_catalog_yaml` picks up the new
   version once renamed to a `v…/` prefix.

Cleanup: the smoke verdict was removed after testing so
`benchmarks/omr-phase-realft/verdicts/` is back to the pre-test state.

---

## What's *not* yet built (followups)

- **Adding a `WRONG_BBOX + WRONG_CATEGORY` combo to the picker UI.**
  The schema supports it (set `human_bbox` and `human_corrected_class`
  together; the converter prefers `human_corrected_class`), but the
  hotkey flow currently sets only one at a time — labeler has to hit
  `b` then `c` sequentially.
- **Zoom / pan on the overlay.** Long cells (~900 px tall) currently
  scale to fit; tiny detections can be hard to click. Browser zoom
  works as a workaround.
- **Search by class name in the picker.** Categories cover most cases
  but a "type to filter" box inside the picker would speed up the
  long ornament tab (45 classes).
- **Pitch capture.** Schema_v1 captured `wrong_pitch` and
  `fn_noteheads[].pitch` for the pitch-resolver. Schema_v2 drops both
  — pitch is a downstream concern and didn't justify the UI cost.
  When/if the pitch-resolver lands, add an optional `pitch` field
  per detection and one per added_detection.
- **Multi-user / concurrent labeling.** The server reads the file on
  every GET and writes on every POST; two users hitting the same cell
  would race. For single-user local labeling (the actual use case)
  this is fine.

---

## Regenerating the archetypes

Only needed when Bravura updates or the DSv2 vocabulary changes:

```bash
python3 -m tools.omr.annotate.build_archetypes
```

This re-renders all 168 PNGs and rewrites
`static/archetypes/README.md`. Commit the updated PNGs.
