# `tools/omr` — Optical Music Recognition pipeline

Local OMR system that reads engraved music PDFs and produces structured
symbol detections. Built around a YOLOv8l detector fine-tuned on
DeepScoresV2 + a small hand-labeled real-orchestral catalog.

**Current production model:** `deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`
(Phase 3.3, F1 **98.8%** on the 25-cell Bach WTC verdict set).

---

## TL;DR — Transcribe a PDF

```bash
# From the repo root (not from tools/omr/):
python3 -m tools.omr.transcribe path/to/score.pdf --out out.json

# Specific pages only, with overlay PNGs for debugging:
python3 -m tools.omr.transcribe score.pdf --pages 0-4 \
    --out out.json --overlays-dir overlays/

# Different weights (e.g., the v1b realft model):
python3 -m tools.omr.transcribe score.pdf \
    --weights tools/omr/training/data/weights/deepscoresv2-yolov8l-realft-v1b.pt \
    --out out.json
```

### Export to a notation file

After producing the JSON, convert it to LilyPond or MusicXML:

```bash
# LilyPond (.ly) — compile with `lilypond out.ly` for a PDF:
python3 -m tools.omr.export out.json --format lilypond --out out.ly

# MusicXML (.musicxml) — opens in MuseScore, plays back in DAWs, round-
# trips through the web app's existing LilyPond/PDF exporter:
python3 -m tools.omr.export out.json --format musicxml --out out.musicxml
```

Both formats are produced from the same JSON via
`tools.omr.export` (which internally uses `tools.omr.voicing` to group
same-x noteheads into chords). The pipeline end-to-end:

```
PDF → transcribe.py → out.json → export.py → out.ly  or  out.musicxml
                                              ↓
                                          lilypond out.ly → out.pdf
```

The output JSON groups detections by `page → system → staff → measure`
and is documented in detail in [`transcribe.py`](transcribe.py) (top
docstring).

**Best for:** clean engraved PDFs (typeset modern editions, IMSLP-style
public-domain scores).
**Degrades on:** handwritten manuscripts, photocopies of photocopies,
extreme densities (full Mahler orchestral page, lots of dynamics + text
markings).

---

## What's in this directory

```
tools/omr/
├── transcribe.py              ← Single-file entry point: PDF → JSON
├── export.py                  ← JSON → LilyPond / MusicXML (Phase 4d)
├── voicing.py                 ← Chord-grouping helper used by export
├── rhythm.py                  ← Duration parsing (Phase 4c)
├── line_detection.py          ← Classical-CV stems + beams (Phase 4f)
├── run_pipeline.py            ← Older Phase-1-only CLI (staves/measures only,
│                                no symbol detection). Mostly for debugging
│                                the staff/measure extractor in isolation.
├── preprocessing.py           ← PDF → PageImage (render, binarize, deskew)
├── staff_detector.py          ← PageImage → PageWithStaves
├── measure_extractor.py       ← Barline detection + cell extraction
├── staff_line_removal.py      ← Optional staff-line removal pass
├── pitch_resolver.py          ← Heuristic pitch from notehead y-position
├── visualize.py               ← write_overlay(): debug PNGs
├── yolo_detector.py           ← Wraps ultralytics; produces SymbolDetection
├── template_matcher.py        ← Legacy template matcher + SymbolDetection class
├── types.py                   ← PageImage, Staff, Barline, MeasureCell, ...
├── symbol_library/            ← Bravura SMuFL archetypes
├── training/                  ← YOLO training scripts + DSv2 prep + weights
└── annotate/                  ← FastAPI app for hand-labeling cells
```

---

## The pipeline

```
                  ┌───────────────────────┐
                  │   render_page (PyMuPDF)│        Phase 1 — Image foundation
                  └───────────┬───────────┘        (no ML; ~1–3 s/page @ 600 DPI)
                              ▼
                  ┌───────────────────────┐
                  │  detect_staves         │
                  │  (horizontal projection│
                  │  + clustering)         │
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  detect_barlines       │
                  │  (vertical projection  │
                  │  on each staff system) │
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  extract_measures      │
                  │  → list[MeasureCell]   │
                  │   (canonical 2048 px   │
                  │    height per staff)   │
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  YoloDetector.detect   │    Phase 3 — Symbol detection
                  │  (yolov8l, imgsz=640)  │    (CPU/MPS/CUDA, ~0.15–0.4 s/cell)
                  └───────────┬───────────┘
                              ▼
                  ┌───────────────────────┐
                  │  transcribe.py groups  │
                  │  + emits JSON          │
                  └───────────────────────┘
```

### Phase 1 — `MeasureCell` extraction (no ML)

`preprocessing.render_page()` rasterizes a PDF page at 600 DPI (default),
producing a `PageImage` with RGB + Sauvola-binarized variants.

`staff_detector.detect_staves()` finds 5-line staves via horizontal ink
projection clustering. Groups them into `Staff` objects with a
`system_index` (sibling staves on the same line).

`measure_extractor.detect_barlines()` runs vertical ink projection
within each staff and finds the dominant vertical strokes. Returns
`PageWithStaves` with `Staff.barlines` populated.

`measure_extractor.extract_measures()` slices each (staff × measure)
rectangle and rescales it into a canonical-height image where the staff
span is normalized to a known size (~CANONICAL_STAFF_SPAN_PX). This
gives the YOLO detector a scale-invariant input — a quarter note from a
miniature score and a quarter note from a 11×17 conductor's score look
the same after extraction. The original page-pixel bbox is preserved in
`MeasureCell.bbox_page_px` so downstream output maps back cleanly.

`staff_line_removal.remove_staff_lines()` optionally produces a
staff-removed variant (`MeasureCell.image_no_staff`) for components that
work better without the lines. The YOLO detector is trained on cells
*with* staff lines (DSv2 convention) and uses `MeasureCell.image`.

### Phase 3 — YOLOv8l symbol detection

`yolo_detector.YoloDetector` wraps an ultralytics YOLO model. It:

1. Reads `MeasureCell.image` (canonical-size, BGR or grayscale).
2. Runs the model with `agnostic_nms=True` (collapses overlapping
   semantically-similar boxes — e.g. `dynamicF` + `dynamicFF` on one
   `ff` mark) and `imgsz=2048` (matches the production weights'
   fine-tuning resolution).
3. Maps each box's class id back to a SMuFL glyph name + category.
4. Returns `list[SymbolDetection]` in canonical-cell coordinates.

`transcribe.py` does the final step: for each cell's detections, it
proportionally re-projects each box into source-page pixels using the
cell's `bbox_page_px` rectangle, so consumers get both `bbox` (canonical)
and `bbox_page` (page-pixel) per detection.

### Class space

The DSv2 classification head has **208 classes** (the canonical
DeepScoresV2 class list — see
`tools/omr/training/data/deepscoresv2_208_classes.json`). The labeling UI
also defines **6 custom classes** at IDs 208–213
(`barlineSingle`, `barlineDouble`, `barlineFinal`, `repeatRight`,
`repeatLeft`, `textDynamic`). Those are **not yet learned** by the
current production weights — see "Known limitations" below.

---

## Output schema

`transcribe.py` writes a single JSON document:

```jsonc
{
  "source_pdf": "score.pdf",
  "weights":    "tools/omr/training/data/weights/.../ft-30ep.pt",
  "conf_threshold": 0.25,
  "iou_threshold":  0.5,
  "agnostic_nms":   true,
  "imgsz":          2048,
  "dpi":            600,
  "n_pages_processed":  3,
  "n_systems_total":    6,
  "n_staves_total":     12,
  "n_measures_total":   84,
  "n_detections_total": 1923,
  "n_noteheads_total":              445,    // all category=="notehead" detections
  "n_noteheads_pitched_total":      445,    // those for which pitch resolved
  "n_noteheads_with_duration_total": 445,   // those given a duration_beats
  "n_rests_total":                  27,
  "n_rests_with_duration_total":    26,
  "runtime": { "phase1_s": 8.2, "yolo_s": 4.1, "total_s": 12.3 },
  "pages": [
    {
      "page_index":   0,            // 0-based
      "page_size_px": [5100, 6600], // at source DPI
      "skew_corrected_deg": 0.0,
      "n_systems":    2,
      "systems": [
        {
          "system_index": 0,
          "n_staves":     2,
          "staves": [
            {
              "staff_index":  0,
              "clef":         "treble",       // effective clef for this staff
              "key_signature": {
                "sharps":      7,             // C-sharp major
                "flats":       0,
                "alterations": {
                  "F": "#", "C": "#", "G": "#", "D": "#",
                  "A": "#", "E": "#", "B": "#"
                }
              },
              "time_signature":  {"numerator": 4, "denominator": 4, "raw": "4/4"},
              "n_measures":      4,
              "measures": [
                {
                  "measure_index":   0,
                  "bbox_page_px":    [186, 268, 1755, 715],
                  "clef":            "treble",   // active clef at this measure
                  "key_signature":   { ... },    // active key sig at this measure
                  "time_signature":  { ... },    // active time sig at this measure
                  "n_detections":    20,
                  "detections": [
                    {
                      "class":      "clefG",
                      "category":   "clef",
                      "bbox":       [44, 108, 124, 356],   // cell-local
                      "bbox_page":  [220, 351, 95, 273],   // source page
                      "confidence": 0.974,
                      "pitch":      null              // null for non-noteheads
                    },
                    {
                      "class":           "noteheadBlackInSpace",
                      "category":        "notehead",
                      "bbox":            [657, 386, 62, 51],
                      "bbox_page":       [689, 564, 47, 39],
                      "confidence":      0.921,
                      "pitch":           "F#4",          // chromatic — key sig + inline
                                                          // accidentals applied
                      "duration_beats":  0.25,            // in quarter-note units
                      "duration_type":   "sixteenth",
                      "dots":            0                // # augmentation dots
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

### `bbox` vs `bbox_page`

| Field | Coordinate system | Use for |
|---|---|---|
| `detections[].bbox` | Canonical cell coords (px) | Cropping the symbol out of `MeasureCell.image` |
| `detections[].bbox_page` | Source-page pixels at `dpi` | Drawing on the source PDF / overlaying back |
| `measures[].bbox_page_px` | Source-page pixels at `dpi` | Cropping the whole measure from the PDF |

All page-pixel boxes are `[x, y, w, h]` (top-left + size), at the `dpi`
the page was rendered at (default 600 — same as a 600 DPI bitmap).

---

## CLI reference

```
usage: transcribe.py [-h] [--out OUT] [--pages PAGES] [--weights WEIGHTS]
                     [--conf CONF] [--imgsz IMGSZ] [--iou IOU]
                     [--no-agnostic-nms] [--dpi DPI]
                     [--overlays-dir OVERLAYS_DIR] [--quiet]
                     pdf

End-to-end OMR transcription: PDF → JSON detections.

positional arguments:
  pdf                   Source PDF path

options:
  --out OUT             Output JSON file (default: stdout)
  --pages PAGES         Pages to process: e.g. '0,4,9' or '0-4' (default: all)
  --weights WEIGHTS     YOLO weights path (default: Phase 3.3, F1 98.8%)
  --conf CONF           Detection confidence threshold (default: 0.25)
  --imgsz IMGSZ         YOLO inference image size (default: 2048 — matches
                        the production weights' fine-tuning resolution)
  --iou IOU             NMS IoU threshold (default: 0.5)
  --no-agnostic-nms     Disable agnostic NMS
  --dpi DPI             Source-page render DPI (default: 600)
  --overlays-dir DIR    If set, write per-page overlay PNGs here
  --quiet               Suppress per-page progress logs
```

### Picking knobs

| Goal | Setting |
|---|---|
| Default — clean engraved scores | (defaults — `conf=0.25`, `imgsz=2048`, `iou=0.5`, agnostic NMS on) |
| Higher recall (more, noisier detections) | `--conf 0.10` |
| Cleaner output (fewer borderline calls) | `--conf 0.35` |
| Faster on simple / low-density scores | `--imgsz 1280` or `--imgsz 640` |
| Lower-DPI scan (300 DPI source) | `--dpi 300` |
| Debug / visual inspection | `--overlays-dir overlays/` then open the PNGs |

`agnostic_nms=True` (the default) is important for music notation: the
detector frequently fires multiple overlapping boxes on the same symbol
(e.g. `dynamicF` + `dynamicFF` on one `ff`). Agnostic NMS collapses
them to the highest-confidence one regardless of class. Turn it off
with `--no-agnostic-nms` if you specifically want to see every
candidate.

---

## Using from another agent / Python code

```python
from pathlib import Path
from tools.omr.transcribe import transcribe, DEFAULT_WEIGHTS

result = transcribe(
    pdf_path=Path("score.pdf"),
    pages=[0, 1, 2],
    weights=DEFAULT_WEIGHTS,
    conf_threshold=0.25,
)

# Walk the structure
for page in result["pages"]:
    for sys_ in page["systems"]:
        for staff in sys_["staves"]:
            for measure in staff["measures"]:
                for det in measure["detections"]:
                    if det["category"] == "notehead":
                        print(measure["measure_index"], det["class"],
                              det["bbox_page"], det["confidence"])
```

The `transcribe` function loads the YOLO model once, then iterates pages
internally — call it once per PDF for best throughput.

---

## Weights

Production weights live in `tools/omr/training/data/weights/`. The
canonical chain (best on the WTC verdict cells):

| Weights | F1 (WTC verdict) | Notes |
|---|---|---|
| `deepscoresv2-yolov8m-r1-imgsz960-50ep.pt` | — | First mid-size run |
| `deepscoresv2-yolov8m-r2-imgsz1280-50ep.pt` | 91.5% | Phase 3.1 |
| `deepscoresv2-yolov8l-full-100ep.pt` | 96.3% | Phase 3.2 |
| `deepscoresv2-yolov8l-8shards-100ep.pt` | — | 8-shard subset |
| **`deepscoresv2-yolov8l-imgsz2048-ft-30ep.pt`** | **98.8%** | **Phase 3.3 (default)** |
| `deepscoresv2-yolov8l-realft-v1b.pt` | 98.5% | Phase 3.4 (first real-orchestral fine-tune; no improvement on WTC, learned some orchestral signal but not yet adopted) |

See `benchmarks/omr-phase3.3/comparison-trained-v3.md` and
`benchmarks/omr-phase3.4b/comparison-trained-v4.md` for full
methodology + per-class breakdown.

---

## Known limitations

- **Custom classes (barlines, textDynamic) are not yet learned.** Phase
  3.4 attempted to expand `nc` from 208 → 214 and caused catastrophic
  forgetting (F1 cratered to 79.3%). The labeling UI captures these
  classes in `.verdict.json` files, but `verdicts_to_yolo_labels.py`
  filters them out when building the training catalog. Re-introduce
  when there are ~200+ examples per new class, or seed via synthetic
  warm-up. See `benchmarks/omr-phase3.4b/comparison-trained-v4.md`.

- **No structural/musical reasoning yet.** `transcribe.py` emits raw
  detections grouped by spatial cells. There is no voicing, no rhythm
  parsing, no key-signature inference, no MusicXML output. That layer is
  the job of downstream tools that consume this JSON.

- **Rhythm parsing is hybrid YOLO + classical-CV** (Phase 4c + 4f).
  Each notehead / rest gets `duration_beats`, `duration_type`, and
  `dots`. Algorithm: notehead class gives the intrinsic duration
  (whole / half / black); for black noteheads, classical-CV stem
  detection (`tools/omr/line_detection.py`) finds the stem attached
  to the notehead, then we count distinct vertical beam levels
  attached to that stem (1 = 8th, 2 = 16th, 3 = 32nd, ...). Beam
  detection uses both YOLO's beam class and a classical-CV horizontal
  morphology pass for redundancy. Falls back to a paired flag
  detection if no beam, then to "quarter" if neither. Dots are paired
  to the nearest left-side notehead at the same y position.

  Why classical CV here? YOLO bounding boxes are structurally bad at
  thin lines (extreme aspect ratios, mostly-empty bboxes). The Phase
  3.3 model emits **zero stem detections** even at conf=0.05, and its
  beam bboxes routinely end 20-50 px short of the actual beam stroke.
  Morphological opening + connected components handles these shapes
  natively, in milliseconds per cell, deterministically.

  Known quirks:
  - Per-measure beat sums are close to but not exactly the time
    signature on busy keyboard music — LilyPond bar-check warnings
    typically report fractional offsets (e.g. 1/32, 3/32) rather than
    full-beat errors as in Phase 4c v1.
  - **No chord voicing yet** — multiple noteheads at the same
    x-position are merged into one chord (Phase 4e), but stem-up vs
    stem-down separation into multiple voices isn't done.

- **Time signature uses the detector's per-digit classes**
  (`timeSig0`–`timeSig9` plus `timeSigCommon` / `timeSigCutCommon`).
  The DSv2 model often misclassifies time-sig digits, so this field
  is **`null` for many pages**. When it does fire it's parsed via
  geometry (top digits = numerator, bottom = denominator).

- **Orchestral conductor's scores.** The current model was trained
  predominantly on DSv2 (synthetic) + 60 hand-labeled real cells.
  Dense conductor's scores (Mahler 5, Debussy La Mer) work but with
  more false negatives on small dynamics + grace notes. The labeling
  pipeline (`tools/omr/annotate`) is the path to fixing this.

- **MusicXML + LilyPond export.** `tools/omr/export.py` produces
  files that LilyPond renders to PDF and that MuseScore / `musicxml2ly`
  accept. Systems with exactly 2 staves are wrapped in `\new PianoStaff`
  (LilyPond) or `<part-group><group-symbol>brace</group-symbol>`
  (MusicXML). When a staff has measures with both stem-up AND stem-down
  noteheads, LilyPond renders it as a two-voice block (`\voiceOne` +
  `\voiceTwo`). MusicXML voice-splitting via `<backup>` was added
  2026-05-23 (`export.py`, `_mxl_voice_events`) — both exporters now
  handle two-voice measures. Bar-check warnings on LilyPond output
  reflect the rhythm-parsing approximation (Phase 4c/g caveats).

---

## Going further

- **Theory layer:** an optional, env-gated enrichment pass
  (`MAESTRO_BRIDGE_ENABLED` / `MAESTRO_PITCH_RERANK_ENABLED`) runs the
  Maestro Analyzer over OMR output — key detection, rhythm validation,
  scholarly cross-check, and M4 pitch re-ranking with auto-correction.
  Lives in `tools/maestro_bridge/` (node/tsx, host-side) +
  `backend/modules/theory_layer.py`. See
  `docs/maestro-integration-plan.md`.

- **Labeling more cells:** `tools/omr/annotate/` is a FastAPI
  labeling UI. Hand-label cells in `data/user-labeled/vN-...` then
  run `tools/omr/training/build_catalog_yaml.py` and
  `tools/omr/training/verdicts_to_yolo_labels.py` to prepare a new
  fine-tune. Recommended next milestone: 200–500 labeled cells.

- **Training:** `tools/omr/training/train_yolo.py` is the
  ultralytics wrapper. See
  `benchmarks/omr-phase3.3/comparison-trained-v3.md` for the
  hyperparameters that produced the current production weights.

- **Benchmarks:** `benchmarks/omr-phase*/` directories hold the
  per-phase reports + the 25-cell WTC verdict set that all the F1
  numbers reference.
