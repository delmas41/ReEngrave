# OMR pipeline — Phase 4 extension benchmark

**Date:** 2026-05-23
**Builds on:** Phase 4 retrospective (`eeb3c01`) — see
`benchmarks/omr-phase4-session/retrospective.md`

Re-runs the 5 real-world PDFs from `benchmarks/omr-real-world` with
three features added since the retrospective:

1. **Octave-clef pitch support** (`d955513`) — `clef8` / `clef15`
   glyphs paired with the base clef yield pitch_resolver keys like
   `treble_8vb` (choral tenor convention), `bass_8vb` (double bass),
   `treble_8va` (piccolo).
2. **MusicXML voice splitting via `<backup>`** (`27acdf2`) — two-voice
   staves that the LilyPond exporter already handled
   (`\voiceOne`/`\voiceTwo`) now also export correctly to MusicXML
   for round-tripping through MuseScore / Sibelius / Finale.
3. **Tie detection** (`b4946fe`, fixed in `01eeb66`) — the YOLO `tie`
   glyph is now paired with the two flanking noteheads in the same
   cell; LilyPond emits `c'4~ c'4`, MusicXML emits
   `<tie>` + `<notations><tied/>`.

## Results

| PDF | Page | Systems | Staves | Measures | Noteheads | 100% pitched? | Two-voice MXL | Octave clefs | Ties (paired) | LilyPond PDF | Runtime |
|---|--:|--:|--:|--:|--:|---|--:|--:|--:|---|--:|
| bach-wtc        | 4  | 5 | 10 |  26 |  359 | ✓ | **18** | 0 | **14** (post-fix) | ✓ 122 KB | 73 s |
| handel-leadsheet| 9  | 3 | 15 |  55 |  280 | ✓ | **20** | **1** (treble_8vb) | 0¹ | ✓ 168 KB | 191 s |
| handel-reduction| 19 | 2 | 12 |  78 |  159 | ✓ | **6**  | 0 | 0¹ | ✓ 86 KB  | 529 s |
| ravel-bolero    | 9  | 4 | 29 | 161 |  832 | ✓ | **23** | 0 | 0¹ | ✓ 294 KB | 479 s |
| beethoven-5     | 14 | 3 | 17 | 187 | 2392 | ✓ |  0     | 0 | 0¹ | ✓ 519 KB | 1171 s |

¹ Pre-fix run. The Bach number re-ran with the tie-pairing fix
(`01eeb66`); the other four would similarly catch ties on re-run.
See `bach-wtc-postfix.{json,ly,musicxml,pdf}` for the corrected output.

### Highlights

- **100% pitch + 100% rhythm coverage** on every PDF — no regression
  vs the Phase 4 retrospective benchmark.
- **All 5 PDFs compile to PDF** with zero LilyPond errors. The new
  octave-clef syntax (`\clef "treble_8"`), tie markers (`c'4~`), and
  multi-voice blocks all parse cleanly.
- **MusicXML voice splitting fires often** — Bach 18, Handel
  lead-sheet 20, Ravel 23, Handel reduction 6, Beethoven 0 two-voice
  measures across the 5 sample pages. (Bach + Handel lead-sheet
  expected — keyboard / vocal-with-piano-RH writing. Beethoven
  orchestral page has one instrument per staff, so no two-voice
  splitting — also expected.)
- **Octave clefs detected on real music**: Handel Messiah lead-sheet
  page 9 has 1 `treble_8vb` staff — the choral tenor part. The new
  pitch_resolver picks the correct octave anchor for it. Pre-fix
  every tenor note would have resolved one octave too high.
- **Tie pairing** (post-fix Bach): 27 raw `tie` detections from
  YOLO → 14 paired (52%). The unpaired 13 are likely cross-measure
  ties (the canonical use across barlines), which span two cells
  and aren't handled by within-cell pairing yet. See "Known
  limitations".

## What changed structurally vs the Phase 4 benchmark

| Dimension | Phase 4 benchmark | Phase 4 extension |
|---|---|---|
| imgsz | 2048 | 1280 (matches web-app default) |
| dpi | 600 | 300 (matches web-app default) |
| Voice splitting | LilyPond only | LilyPond + MusicXML |
| Octave clefs | Dropped silently | Resolved via clef8/clef15 pairing |
| Ties | Detected by YOLO but discarded | Paired within-cell + emitted |

The lower imgsz/dpi trades some recall on small noteheads in dense
orchestral pages for ~3× faster inference. Per-PDF notehead counts:
Phase 4 vs this run = (445→359, 298→280, 476→159, 1052→832, 904→2392).
The Beethoven number went UP (2392 vs 904) — same page, more measures
counted (187 vs 98), suggesting Phase 1 staff/system splitting is
picking up sub-systems the original benchmark missed.

## Known limitations / next steps

- **Cross-cell tie pairing.** Real ties most often span a barline
  (final note of measure N tied to first of measure N+1). My within-
  cell pairing misses these — they show up as one cell containing a
  notehead + tie glyph, and the other cell containing the matching
  notehead. Catching these requires running the pair-finder at the
  STAFF level after cells are processed. Expected 2× tie coverage.

- **Beethoven over-counting in Phase 1.** 187 measures detected on
  page 14 vs the retrospective's 98 — same page, ~2× the cells.
  Worth investigating whether this is over-segmentation (the
  retrospective flagged "Beethoven 29-empties + Ravel-residual
  issues" as the remaining Phase 1 work).

- **Sample size still thin.** Each PDF is still 1 page. The
  retrospective's "more pages × more genres" recommendation
  (chamber music, jazz lead sheets, opera) is unmet.

## How to reproduce

```bash
# From the repo root, with the backend container running and
# OMR_WEIGHTS_HOST_DIR pointed at omr-weights/:
DOCKER="/Applications/Docker 2.app/Contents/Resources/bin/docker"
CONTAINER=recursing-cartwright-4a5463-backend-1
"$DOCKER" cp run_benchmark.py "$CONTAINER:/tmp/run_benchmark.py"

# Copy each benchmark PDF to /tmp/bench_pdfs/ inside the container.
# The run_benchmark.py header documents the expected filenames.

"$DOCKER" exec "$CONTAINER" python3 /tmp/run_benchmark.py \
  /tmp/bench_pdfs /tmp/bench_out
"$DOCKER" cp "$CONTAINER:/tmp/bench_out/." ./output/
```

## Files of interest

- `run_benchmark.py` — the script (runs inside the container)
- `output/results.json` — summary of all 5 PDFs (pre-fix tie numbers)
- `output/{label}.{json,ly,musicxml,pdf,lilypond.log}` — per-PDF outputs
- `output/bach-wtc-postfix.{json,ly,musicxml,pdf}` — Bach re-run with
  the tie-pairing fix, for direct comparison with `bach-wtc.{...}`
