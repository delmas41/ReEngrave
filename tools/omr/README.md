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
              "clef_source":  "cv_locator",   // OPTIONAL — present only when
                                              // the clef came from a fallback
                                              // reader rather than the main
                                              // detector: "specialist" (the
                                              // --clef-weights model) or
                                              // "cv_locator" (shape-located
                                              // C clef). Absent otherwise,
                                              // including when the staff
                                              // inherited a default.
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

### Time-signature inference (back-fill)

DSv2 misclassifies time-sig digit glyphs, so `parse_time_signature` returns
`null` on most measures. After a page is built, `rhythm.backfill_page_time_signatures`
decides a page meter and back-fills it onto the measures/staves whose detection
failed. This feeds the per-measure `rhythm_sum_warning` check and the LilyPond
/ MusicXML exporters (which otherwise hardcode 4/4). Two methods, most-reliable
first:

1. **Propagate a dominant DETECTED meter.** When a propagatable meter — a
   `C`/cut-`C` glyph, or a plausible digit meter (numerator 2-16, denominator a
   power of two) — is read on ≥3 measures with no plausible dissent, it's
   propagated across the page. Digit-stack meters used to be excluded because
   the detector misreads the stacked instrument-grouping numbers left of the
   clefs ("Flöten 1 2 3 4") as a time signature; now that the left-edge filter
   (below) drops those at the source, plausible digit meters aggregate safely
   too. ⚠️ **Caveat found while validating this: the DSv2 digit detector barely
   detects orchestral time signatures at all** — a printed 3/4 across every
   staff of Boléro p.1 and a printed 2/4 on Mahler 5 p.1 both yielded *zero*
   valid detections (only left-edge misreads, filtered out). So digit
   propagation is correct but rarely gets a real orchestral signal; the only
   reliably-detected meter in testing is the `C`/cut-`C` glyph.
2. **Beat-sum inference** as the fallback: majority-vote the per-measure
   resolved lengths (per time-column, taking the fullest staff at each column),
   firing **only when one standard meter wins near-consensus (≥0.8)**. The bar
   is high because observed lengths are *biased*, not just noisy — on a sparse
   page no instrument fills the whole bar, so per-column-max UNDER-counts
   (Boléro p.1, a real 3/4, had most columns at ~2.0 and a 0.6 gate inferred a
   wrong 2/4). Near-consensus abstains on a mere plurality; it's a last resort.

**Left-edge misread filter.** `parse_time_signature` rejects any time-sig glyph
whose left edge sits within `_TIMESIG_MIN_X_CANONICAL` (16) canonical px of the
cell's left edge. A real time signature is engraved after the clef (observed
≥35 canonical px in), whereas the detector clamps spurious reads of the stacked
instrument-grouping numbers / margin junk to x==0 — so this cleanly drops the
`2/4` / `6/66` / `666/666` misreads that polluted orchestral pages while leaving
the real `C` detections (and their propagation) untouched. Canonical coords are
scale-normalized, so the threshold is DPI-independent.

- A back-filled `time_signature` carries `"source"` (`"detected_propagated"`
  or `"inferred"`) plus `votes` / `voters` (and `confidence` for `inferred`);
  a *detected* one has only `numerator` / `denominator` / `raw` and is never
  overwritten.
- The page dict gains `"inferred_time_signature": {...}` when the vote fires.
- Deliberately conservative ("leave it null rather than guess wrong"): it
  abstains on pages whose rhythm resolution is too noisy for a clear mode
  (dense conductor's scores, tuplet-heavy passages), so the effective meter
  stays `null` there rather than a wrong guess. Only the bar **length** is
  inferred — compound meters surface as their simple equivalent (6/8 → 3/4,
  12/8 → 6/4) with the same length.

### Clef reading (geometry, not classification)

An alto clef and a tenor clef are **the same glyph printed one staff line
apart**. So are soprano, mezzo-soprano and baritone clefs — five clefs, one
drawing, five positions. Nothing in the ink distinguishes them, which means a
detector class label *cannot* carry the distinction no matter how well the
model is trained. DSv2 also has only two C-clef classes (`cClefAlto`,
`cClefTenor`), so soprano/mezzo/baritone are unrepresentable in that label space
at all. This is why a clef-targeted fine-tune couldn't fix alto/tenor confusion:
it's a mislabelled task, not an under-trained model
(`benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md`).

`clef_geometry.py` splits the work along the line where the evidence actually
falls. The detector keeps what it can see — that there's a clef here, and which
family it belongs to (G / C / F), a real visual distinction. Geometry decides
the rest: the glyph's named line is snapped to the nearest of the five staff
lines, and the clef is looked up by `(family, line)`.

```
CLEF_BY_FAMILY_LINE   line: 1 (bottom) … 5 (top)
  G   1 french        2 treble
  C   1 soprano       2 mezzosoprano   3 alto   4 tenor   5 baritone
  F   3 varbaritone   4 bass           5 subbass
```

That one table is the single source of truth: `pitch_resolver._CLEF_ANCHORS`
and `export._MXL_CLEF_SIGN` are both *derived* from it, so a clef the geometry
can name is automatically one the pitch resolver can anchor and the exporters
can write (`\clef soprano`, `<sign>C</sign><line>1</line>`).

- A **C clef is symmetric about the line it names**, so its named line is
  simply the middle of its box — exact, and true of archaic engraved C clefs
  as much as of a modern font.
- **G and F clefs keep their class label by default.** They aren't symmetric,
  so their line would need a calibrated offset, and the payoff isn't there:
  treble and bass dominate those families, french/varbaritone/subbass are
  vanishingly rare, and a wrong guess transposes every pitch on the staff.
  `ClefGeometryConfig(families=...)` can enable them.
- **Abstention.** If the snapped line is more than `max_residual` (0.35 line
  spacings) from a real staff line, or the staff has no clean 5-line geometry,
  the class label stands rather than a guess.

### Clef *location* — when no model sees a clef at all

Geometry fixes which clef a detection is. It can't help when there's no
detection, and on some material there is none: on 19th-century C-clef
counterpoint prints (Nottebohm's *Beethovens Studien*) the production model and
the clef specialist between them find **zero** clefs on a page carrying one per
staff — even at confidence 0.03. The archaic "ladder" C clef simply isn't in
the distribution DSv2 was rendered from, so no threshold reaches it. Every staff
then falls back to the position default and a page of soprano/alto/tenor
counterpoint transcribes as treble.

`clef_locator.py` finds it by shape instead, the way Phase 4f handles stems and
beams: strip the vertical rules (the barline sits a few pixels from the clef)
and the horizontal ones (staff lines and their residue), cluster what's left in
the header strip, and take the first glyph-sized cluster. It is accepted only if
it carries the C-clef signature — symmetric about its own centre — and that same
symmetry then locates the named line, refined to the axis the ink actually
balances about so a stray surviving fragment can't drag the answer onto the next
line.

It is deliberately narrow:

- **C clefs only.** They have the one shape signature that survives any
  engraving style. A G or F clef yields nothing.
- **It stops at the first glyph-sized cluster.** A too-tall cluster (a G clef)
  ends the search rather than being skipped — otherwise the key signature's
  first sharp, which is narrow, tall and beautifully symmetric, gets read as
  the staff's clef.
- **It only speaks when nothing else did.** Gated on no clef having been read
  for that staff by either model, so it can add a reading but never overturn
  one. `--no-clef-locator` disables it; `staff["clef_source"]` says
  `"cv_locator"` when it fired.

Measured (`benchmarks/omr-clef-geometry/RESULTS.md`): exact on LilyPond-engraved
reference staves for all five C clefs, treble and bass declined; **zero** false
positives over 10 pages of Bach WTC piano; correct alto/tenor reads on Handel,
Boléro, La Mer and Beethoven 5; and no change to notehead or detection counts
anywhere (Mahler 5 p.11 stays at the 2506-notehead production baseline).


---

## Reading a staff's header (clef + key signature)

**You do not need to turn anything on, and you do not need any extra weights.**
Everything in this section runs by default in `transcribe`, from the production
`--weights` model plus classical CV. There is one entry point — `transcribe` —
and no separate tool to invoke.

A staff's header is the strip at its start holding the clef, the key signature
and the time signature. All three readers work from the same measured window,
so they cannot disagree about where the clef ends and the signature begins.

### The window is measured, not assumed

Header readers used to work from "the left 42% of the staff-START measure
cell", and that cell does not reliably contain the header. `Staff.x_start` is
the longest unbroken ink run on the middle staff line, so on a faded print the
run — and the cell with it — begins *after* the clef. Measured on Beethoven 5
p.2 (IMSLP 575951), a system whose eleven staves are physically flush at page
x≈285:

```
x_start:  547, 436, 383, 777, 1007, 985, 1233, 1001, 927, 1048, 986
```

The staff-start cell began at x=383 — past the treble clef (310–355) and past
all three key-signature flats (360–395). It contained a whole rest and a
barline. NOTES.md records the same failure on Nottebohm's multi-fragment
layouts; it happens on ordinary orchestral prints too.

`staff_header.py` measures the window from the page instead: the staff *band*
carries ink where the individual lines are broken, so the left edge is found by
walking left along the band from a column known to be inside the staff, stopping
at the system's initial vertical rule (which also keeps the walk out of the
instrument names). It is taken per SYSTEM as the minimum over its staves — a
staff whose anchor sits deep in the music stops at the first barline it meets
and over-reports, a sound staff walks back to the truth, and the minimum picks
the sound one. On the system above it gives 287, against an eyeballed 285.

It does not touch `Staff.x_start` or measure segmentation. Phase 1 has no
regression baseline (NOTES.md), so the measurement lives beside Phase 1 rather
than inside it, and the clef readers switch to it only where the measure cell
demonstrably starts past the header.

### Key signatures are read by position, not by counting

A key signature is N copies of one glyph at staff positions fixed by the clef —
it is pure geometry, and counting detections throws that away. Four flats
printed and three detected used to read as E♭ major instead of A♭, silently,
moving every B, E and A on the staff.

`key_signature_geometry.py` fits the observed positions to the slot table for
(clef, N). Flats seen at slots 1, 2 and 4 mean **four flats with the third
missed**, not three — the gap in the pattern says so. Off-slot ink stops
counting at all. The tables are written out per clef, because the conventions
have real exceptions: treble's third sharp sits *above* the staff, bass's
seventh flat *below* it, and tenor's first sharp drops an octave outright, so
deriving one clef's table from another's is wrong. A clef without a table
abstains.

The fit solves for one shared glyph-anchor offset (a flat's box centre sits
above the note it alters), requires the first slot to be observed, and never
extends past the last observation — so it recovers gaps but cannot invent a
signature it did not see.

**This applies to the detector's own markers, not just the locator's.** Where
the detector fires — clean modern engravings, mostly — its `keySharp`/`keyFlat`
boxes are fitted to the slots rather than counted, and counting is wrong there
in a specific, common way. Measured on WTC p.17 (E major, four sharps on every
staff, a clean engraving):

| | correct |
|---|---|
| counting the markers | 6 / 10 |
| fitting their positions | 7 / 10 |
| …and reconciled across the page | **10 / 10** |

Each step fixes a different failure. The staff the FIT rescued had five markers:
the four real sharps, landing exactly on the bass slots [2, 5, 1, 4], plus one
stray above the staff — counting reads five, the fit sets the stray aside and
reads four. The three the VOTE rescued had lost their FIRST sharp to the
detector, reading +1, +1 and +2; no amount of looking at those staves alone can
recover that (the "first slot must be observed" rule forbids it, and lifting the
rule is what once let two glyphs report five sharps). Only the page can say, and
it does: the same part reads four sharps in the other systems.

`key_signature_locator.py` finds the accidentals when the detector sees none,
which on real prints is the normal case: on Beethoven 5 p.1, across 3,246
detections on a page whose every string and woodwind staff carries three flats,
the model emits **zero** `keySharp`/`keyFlat`. The locator strips the vertical
rules, traces the staff lines off (see below), and looks for a run of similar,
glyph-sized clusters right after the clef. Sharps and flats zigzag in opposite
directions, so for a run of two or more the pattern itself says which it is; a
run of one falls back to ink distribution (a flat is bottom-heavy, a sharp is
balanced about its middle).

### Tracing the staff lines off

The lines have to come off before any of this is readable, and on these prints
they are **0.15–0.31 staff spaces thick** (a modern engraving is nearer 0.08)
and they wander. Generic morphology either leaves them or shreds the
accidentals with them; either way the header arrives as one connected mass.

`header_ink.trace_staff_line` / `erase_staff_lines` follow each line instead:
Phase 1 knows its nominal y, which is enough to walk the ink run at that height
column by column, measure how thick the line is actually printed, and erase
that band along its real path. Ink above *and* below an erased band means a
glyph continues through it — but that also holds along a line thicker than the
band, so only *narrow* runs of such columns are bridged back. A glyph crosses a
line over a narrow x-range; a line's own residue crosses for as far as it runs.

### Reconciling across the page

One staff's reading is fragile. `key_signature_vote.py` reconciles them using
two redundancies a single staff cannot see: the same part appears in every
system down the page, and every staff of a system is in one concert key.

The concert-key relation is weaker than it looks — for key K the legal written
signatures are {K−3, K, K+1, K+2, K+3}, so an under-counted signature usually
lands on a *legal* offset (three flats misread as one flat looks exactly like a
correctly-notated B♭ instrument). What works is that transposing instruments are
a minority: the page's **modal** written signature is the reference, and
departing from it is a claim that needs evidence — a strong reading, or the same
part read in another system.

The vote rejects and carries; it never synthesises a signature from the
reference, because the reference cannot know a staff's transposition.

**Both readings go through it** — detected and located alike. That is the point
of doing the reading in one pass before the measures: a signature the detector
under-counted and one the locator found by shape are the same kind of claim, and
the page decides between them together. Where the vote has ruled on a staff, the
measure pass does not re-read its key signature from cell 0 — that reading is
the one the vote already saw and judged, in isolation and without the page. Later
cells still run, so a genuine mid-staff key change is still picked up.

### Each reader gets the picture it can read

The detector reads the staff-start MEASURE cell; the CV locator reads the
measured HEADER window. That split is measured, and it goes the opposite way to
what you would guess. On WTC p.17 the model finds **zero** key-signature markers
on the header crop at imgsz 640, 1280 and 2048 alike, and almost no clefs — on
the same staff's measure cell it finds four or five markers and the right clef.

A narrow crop is better input for classical CV, which doesn't care what scale
the ink arrives at, and worse for a model trained on whole cells, which sees a
letterboxed sliver as nothing it knows. Cropping to the header is what makes the
CV locator work at all and what makes the detector go blind, so neither reader
is given the other's picture.

### What it is measured at

Two ground-truth pages, every signature read off the page by eye (Beethoven 5
p.2 and Beethoven 6 p.2 — 42 staves, both systems each):

| | correct | wrong | missed | correct abstentions |
|---|---|---|---|---|
| per-staff reading | 10 | 7 | 19 | 8 |
| after the vote | 10 | **2** | 22 | 8 |

Recall is about a third, and that is the honest number: where it reads a
signature it reads it exactly (three-flat staves come back with all three
accidentals at residuals of 0.03–0.24 steps against a half-step tolerance), and
where it cannot it abstains. Both surviving errors are one genuine misread — a
clarinet's sharp read as a flat, which agrees with the page's reference and so
cannot be told from a non-transposing part by any structural argument.

**The reading only ever seeds a staff where the detector found no
key-signature accidental at all** — the same "speaks only when the detector is
silent" rule the C-clef locator follows. A score the detector reads correctly
today cannot be changed by it. `staff["key_signature_source"] == "cv_locator"`
says when it fired, and `staff["key_signature_reason"]` says what the vote
decided and why.

All of these figures are reproducible — `benchmarks/omr-key-signature/` holds
the hand-read ground truth for all three pages and the script that scores it:

```bash
python3 benchmarks/omr-key-signature/eval_key_signatures.py
```

### It inherits the clef problem

Those numbers are what the reader achieves **given a correct clef** — the
evaluation supplied the true clef for each staff, because the slot table is
chosen by it.

In the pipeline the clef is not given, and that turns out to matter more than
expected. The plan had been that a wrong clef costs recall rather than
correctness: treble, bass and alto slot patterns are the same shape a constant
apart, so a signature fitted against the wrong one should push the solved offset
past tolerance and be dropped. Measured end-to-end, that is not reliable — with
every staff defaulted to treble, two bass staves carrying three flats came back
as **two sharps**, a different accidental type fitting a different prefix well
inside tolerance.

So a staff whose clef is only the positional default is **skipped**. Reading a
key signature against a guessed clef is guessing twice.

To make that gate something other than a permanent off switch, the clef is
*read* in the header pass: one inference per staff, with the production
detector, on the header crop — a few staff spaces wide, against the hundreds of
inferences the measures need. Without it the estimate on a first page would only
ever be the position default, and the reader would be gated off on every treble
and bass staff in the score. That read is used ONLY to choose the slot table; it
is not written to the output, and the measure pass still reads the clef its own
way.

The consequence is that the two features improve together: where clefs read
well, key signatures are read for most staves; on scans where the detector calls
every staff treble, the key-signature reader stays quiet. That is the right
failure, but it is the honest ceiling on this work today — clef *detection* on
such scans is itself unsolved (see "Clef location" above).

### `--clef-weights` is optional, and is not general-purpose weights

The one footgun worth naming. `--clef-weights` takes a **clef-specialist
checkpoint** — a model fine-tuned specifically to read clefs. It is an optional
enhancement, not a requirement: header reading works without it. Pointing it at
ordinary detection weights (including the production `--weights` file) makes
clefs *worse*, not better, because the specialist's clef read overrides the main
detector's. If you have no clef-specialist checkpoint, leave it unset.

---

## CLI reference

```
usage: transcribe.py [-h] [--out OUT] [--pages PAGES] [--weights WEIGHTS]
                     [--clef-weights CLEF_WEIGHTS] [--clef-reader-conf CONF]
                     [--no-header-reading] [--no-clef-locator]
                     [--clef-reader-imgsz N] [--clef-reader-header-frac F]
                     [--no-clef-locator]
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
  --clef-weights W      OPTIONAL, and NOT general-purpose weights: this takes a
                        CLEF-SPECIALIST checkpoint (a model fine-tuned to read
                        clefs). You do not need it — header reading is on by
                        default and needs no extra files. When set, a 2nd
                        detector reads each staff's clef + time signature from
                        its header and overrides them, which helps on some
                        orchestral scans (~+2% runtime; the main --weights model
                        still does all symbols). Pointing it at ordinary
                        detection weights makes clefs WORSE. Env:
                        OMR_CLEF_WEIGHTS. NB the current clef weights read clefs
                        but NOT time-sig digits (DSv2 gap). See
                        benchmarks/omr-clef-demo/DEMO_AND_AUDIT_RESULTS.md.
  --clef-reader-conf C  Min confidence for a specialist override (def 0.30)
  --clef-reader-imgsz N     Specialist inference imgsz on its crop (def 640)
  --clef-reader-header-frac F  Left fraction of the start cell read (def 0.42)
  --no-header-reading   Disable the staff-header pass: measuring each staff's
                        header window and reading its key signature from it.
                        On by default, needs no weights. The reading only seeds
                        staves where the detector found no key-signature
                        accidental, so this cannot fix a wrong DETECTED
                        signature — it only removes the fallback. See "Reading
                        a staff's header" above.
  --no-clef-locator     Disable the classical-CV C-clef locator. It runs only
                        where NO model read a clef, and recognises only C
                        clefs, so it can add a reading but never overturn one.
                        Pass this to reproduce pre-locator output exactly.
                        See "Clef location" above.
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

### If you are an agent reading this

**Call `transcribe`. That is the whole interface.** Clef reading, C-clef
location, header measurement and key-signature reading are all inside it and
all on by default; there is no separate step to run and nothing to enable.

- **Do not pass `clef_weights` unless you have a clef-SPECIALIST checkpoint.**
  It is not "better weights" — it is a second model fine-tuned only for clefs,
  whose clef read overrides the main detector's. Passing the production weights
  (or any general detection checkpoint) there makes clefs worse. If in doubt,
  omit it.
- **Do not call `clef_locator`, `key_signature_locator`, `clef_geometry`,
  `key_signature_geometry` or `staff_header` directly** to transcribe a score.
  They are components `transcribe` composes in a specific order — the locators
  are gated to speak only where the detector is silent, and calling one on its
  own loses that gating. Read them directly only when you are testing or
  debugging that one component.
- **`read_headers=False` and `locate_c_clefs=False` are for reproducing older
  output**, not for fixing a bad read. Both readers only ADD a reading where
  nothing else produced one, so turning them off cannot correct a wrong result
  — it can only remove a fallback.
- **Check `staff["clef_source"]` and `staff["key_signature_source"]`** to see
  which reader produced a value. Absent means the detector or a default; a
  `key_signature_reason` explains what the cross-page vote decided.

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
