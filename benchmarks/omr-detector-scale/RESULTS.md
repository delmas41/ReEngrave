# The detector was being shown the wrong scale

**2026-08-28.** Reproduce with:

```bash
python3 -m benchmarks.omr-detector-scale.probe_detector_scale   # (see below)
python3 -m tools.omr.training.end_to_end_eval
```

---

## The number that started this

The end-to-end benchmark reported the pipeline returning **2–2.5× the notes that
exist** on clean authored input, while the structure around them was correct:

| fixture | parts | measures | notes reported / true |
|---|---|---|---|
| melody | 1/1 | 12/6 | 61 / 24 |
| keyboard | 2/2 | 4/4 | 45 / 27 |
| ensemble | 4/4 | 4/4 | **103 / 45** |

`ensemble` is structurally perfect — four parts, four measures — so nothing else
confounds the note count. It was the right place to start, and it turned out the
extra notes were not spread thinly over the page. They were in two piles.

## Where the 103 actually were

Sorting `ensemble`'s 103 noteheads by their page x-coordinate:

| page region | noteheads |
|---|---|
| the clef, x < 780 | 12 |
| the `4/4` time signature, 780 ≤ x < 900 | **44** |
| everything else — the actual music | 47 |

**Fifty-six of the 103 were on the clef and the time signature**, which is more
than the whole page's true note count. A further 23 were a column of boxes 3 px
wide stacked on the left edge of the last measure. Drawing the detector's own
boxes on the images it was given shows what it was doing: the vertical stroke of
each `4` came back as a stack of nine "noteheads", the treble clef's lower loop
as one more, and the real noteheads — where they were found at all — as thin
slivers lying across the top of the ellipse rather than boxes around it.

That last detail is the tell. These were not confident wrong answers; they were
the shapes you get when the model has stopped recognising the object and started
firing on fragments of ink.

## The mechanism

A detector does not see pixels, it sees a **staff space**. `imgsz` is only a
pixel budget; what decides whether the model recognises a notehead is how large
that notehead is once ultralytics has letterboxed the image to `imgsz`:

```
staff space shown  =  canonical staff space  ×  imgsz / longest side of cell
```

The pipeline makes two scale decisions independently and they multiply:

1. `measure_extractor` upscales every cell so its staff SPAN is 400 px — a
   staff space of **100**.
2. `transcribe` then runs the detector at `imgsz=2048`, which for a cell
   1200–1300 px on its long side enlarges it by another ~1.6×.

The model is shown a staff space of **100–200 px**. It was fine-tuned on
DeepScoresV2 *pages*, where a staff space is a couple of dozen pixels. The
comment justifying 2048 — "matches the production weights' fine-tuning
resolution" — is true of a page and false of a canonical cell.

## The response curve

Holding each cell fixed and varying only `imgsz`, over 30 measures of authored
music across all three fixtures, where every note count is exact:

| staff space shown | detected/true | measures exactly right | median box width | notehead conf |
|---|---|---|---|---|
| 8 | 0.89 | 24/30 | 1.28 | 0.85 |
| 12 | 0.89 | 24/30 | 1.29 | 0.87 |
| **16** | **0.89** | **24/30** | **1.29** | **0.91** |
| 20 | 0.88 | 24/30 | 1.27 | 0.90 |
| 22 | 0.88 | 24/30 | 1.27 | 0.89 |
| 26 | 0.96 | 17/30 | 1.27 | 0.88 |
| 38 | 1.23 | 4/30 | 1.24 | — |
| 50 | 1.77 | 3/30 | 0.87 | — |
| 70 | 1.29 | 4/30 | 0.57 | — |
| 100 | 1.41 | 1/30 | 0.45 | — |
| 150 *(the old default)* | 1.91 | 3/30 | 0.23 | — |

A notehead is about **1.25 staff spaces** wide, so the box-width column says
whether the boxes are notehead-shaped at all. It holds at 1.27–1.30 across the
whole plateau and then collapses — the count and the shape fail together, which
is what makes this a scale problem rather than a threshold problem.

Two cautions about reading this table. **The aggregate ratio is the wrong
criterion**: it passes through exactly 1.00 at a staff space of 30, but only
16/30 measures are individually right there — over- and under-counting cancel.
Exact per-measure agreement is the honest column. And the plateau is **broad**,
8 → 22, so the choice is not knife-edge; `TARGET_STAFF_SPACE_PX = 16` sits in
its middle with about a factor of two of margin either way, at the confidence
peak, and is where the fixtures' clef and time-signature counts also come out
exactly right (7 clefs on 7 staves, 14 digits on 7 `4/4` marks) where the wide
end finds neither.

## The same thing on a real page

Not a fixture artifact. Bach WTC p.1, two cells, same sweep — and the first has
a hand count:

| cell | staff space shown 16–26 | at 2048 (staff space ~167) | hand count |
|---|---|---|---|
| staff 5, measure 3 | **7** noteheads, boxes 1.23 spaces, conf 0.86–0.92 | 33 noteheads, boxes 0.13 spaces | **7** |
| staff 5, measure 8 | 2 noteheads, boxes 1.25 spaces | 31 noteheads, boxes 0.15 spaces | — |

The same page also shows why this stayed hidden. Five of its staves produce one
full-width cell each, and `_upscale_to_canonical` caps cell width at
`MAX_CELL_WIDTH_PX = 2048` — so those cells were never upscaled much, landed at
a staff space of **19**, and came back with perfect 1.25-space boxes. Cells in
the good regime and cells in the bad regime sit side by side on one page,
decided by whether the width cap happened to bite.

## The fix

`yolo_detector.imgsz_for_cell` computes `imgsz` from the cell's own canonical
staff spacing so the model is always shown ~16 px, and `detect(imgsz=None)` —
now the default everywhere — uses it. Nothing else moves: ultralytics returns
boxes in the source image's frame whatever `imgsz` was, so every downstream
consumer sees the same canonical coordinates it saw before. `--imgsz 2048`
reproduces the old behaviour exactly.

## End to end

`python3 -m tools.omr.training.end_to_end_eval`, at the pipeline's own 600 DPI:

| fixture | notes → | truth | pitch recall | precision | duration |
|---|---|---|---|---|---|
| melody | 61 → **23** | 24 | 0.375 → 0.708 | 0.148 → 0.739 | 0.889 → 0.882 |
| keyboard | 45 → **27** | 27 | 0.407 → **1.000** | 0.244 → **1.000** | 0.364 → **1.000** |
| ensemble | 103 → **45** | 45 | 0.400 → **0.956** | 0.175 → **0.956** | 0.167 → 0.860 |

`keyboard` is now exactly right: every note, every pitch, every duration.
`melody` is still held down by a separate, known bug — it reads 12 measures
where there are 6, because a single staff has no cross-staff vote and its note
stems are read as barlines. Its note count is now 23 against a truth of 24; the
recall ceiling is the over-segmentation, not the detector.

751 tests pass, 3 xfailed — unchanged.

## Two things this also explains

**The F1 98.8% and the production pipeline were never the same configuration.**
`training/eval_on_score_cells.py` calls `detect()` without an `imgsz` and so ran
at the wrapper's old default of **640**, while the pipeline ran at 2048. The
headline quality figure was measured at a setting no production run used.

**"The model finds zero key markers on the header crop at any imgsz"**
(`tools/omr/README.md` → "Each reader gets the picture it can read") tested 640,
1280 and 2048. All three are far too large for a crop a few staff spaces wide;
the conclusion drawn from them — that a letterboxed sliver is outside the
model's training distribution — described the symptom correctly and named the
wrong cause. Worth re-testing at the per-cell scale before that note is trusted.
