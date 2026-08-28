# Sizing the detector's input per cell

**2026-08-28.** Reproduce with:

```bash
python3 benchmarks/omr-detector-scale/probe_detector_scale.py   # the response curve
python3 -m tools.omr.training.end_to_end_eval                   # per-cell (the default)
python3 -m tools.omr.training.end_to_end_eval --imgsz 512       # the best fixed value
```

> **Read `../omr-imgsz-sweep-2026-08/findings.md` alongside this.** Another
> session found the same bug the same day, from the opposite direction — 161
> hand-labeled orchestral cells rather than authored fixtures — and landed
> `imgsz 2048 → 512` on main. This document is the reconciliation: the two sets
> of measurements agree, one line of its stated mechanism does not survive, and
> the remaining disagreement is only about whether the right answer is a smaller
> constant or a per-cell rule.

---

## The number that started this

The end-to-end benchmark reported the pipeline returning **2–2.5× the notes that
exist** on clean authored input, while the structure around them was correct —
`ensemble` at **103 notes against 45**, with four parts and four measures both
right. So the extra notes could not be blamed on layout.

They were not spread thinly over the page. They were in two piles. Sorting
`ensemble`'s 103 noteheads by page position:

| page region | noteheads |
|---|---|
| the clef, x < 780 | 12 |
| the `4/4` time signature, 780 ≤ x < 900 | **44** |
| everything else — the actual music | 47 |

**Fifty-six of the 103 were on the clef and the time signature**, more than the
whole page's true note count. Drawing the detector's own boxes on the images it
was given shows what it was doing: the vertical stroke of each `4` came back as
a stack of nine "noteheads", the treble clef's lower loop as one more, and the
real noteheads — where found at all — as thin slivers lying across the top of
the ellipse instead of boxes around it.

That last detail is the tell. These were not confident wrong answers. They are
the shapes you get when a model has stopped recognising the object and started
firing on fragments of ink.

## The mechanism

A detector does not see pixels, it sees a **staff space**. `imgsz` is a pixel
budget; what decides whether the model recognises a notehead is how large that
notehead is once ultralytics has resized the image. That resize is
aspect-preserving — the longest side goes to `imgsz` — so

```
staff space shown  =  canonical staff space  ×  imgsz / longest side of cell
```

The pipeline makes two scale decisions independently and they multiply.
`measure_extractor` upscales every cell so its staff SPAN is 400 px — a staff
space of 100 — and `transcribe` then ran the detector at `imgsz=2048`, which for
a cell 1200–1300 px on its long side enlarges it again. The model was shown a
staff space of **100–200 px**. It was fine-tuned on DeepScoresV2 *pages*, where
that is a couple of dozen pixels. The comment justifying 2048 — "matches the
production weights' fine-tuning resolution" — is true of a page and false of a
canonical cell.

### One correction to the other session's account

`../omr-imgsz-sweep-2026-08/findings.md` states that "ultralytics letterboxes the
input to `imgsz × imgsz` regardless of source size, so a larger `imgsz` is simply
more pixels, more anchors and more detections". The first half is not what the
default predict path does, and it matters, because it is the step from which
"the fix is a constant, not a cell-relative rule" was derived. Checked directly:

| cell | `imgsz` | shape fed to the model |
|---|---|---|
| 2048×957 | 512 | 512×256 |
| 807×1200 | 512 | 352×512 |
| 300×1200 | 512 | 128×512 |
| 1331×1200 | 2048 | 2048×1856 |

`predictor.pre_transform` builds `LetterBox(imgsz, auto=rect, ...)`, and for a
single image `rect` is true, so it pads only to a stride multiple. Even forcing
the square path changes only the padding: content is still scaled by
`imgsz / longest side`. Either way the model sees the symbol at a size that
depends on the cell, not on `imgsz` alone.

### Why their size-band evidence looked flat anyway

Their table shows false positives per cell at a fixed `imgsz` being nearly the
same across cell-size bands, which is real and is the observation that pointed
them at a constant:

| `imgsz` | 600–1000 px | 1000–1500 px | ≥1500 px |
|--:|--:|--:|--:|
| 640 | 8.5 | 12.7 | 8.8 |
| 1280 | 32.6 | 32.4 | 20.7 |
| 2048 | 52.6 | 60.0 | 45.2 |

A canonical cell is **12 staff spaces tall** — 4 for the staff, 4 padding above
and below — so its canonical height is pinned near **1200 px** whatever the
music. Every cell narrower than that has `longest side = 1200`, and therefore
shows `100 × imgsz / 1200 = imgsz / 12` — a pure function of `imgsz`, with cell
width not entering at all. Most measure cells are in that regime, so banding by
size *cannot* separate the two hypotheses there.

Where the bands do separate them, their own numbers lean the other way: the
**≥1500 px band has the lowest FP rate at every `imgsz`** (8.8 / 20.7 / 45.2
against 12.7 / 32.4 / 60.0). Those are the width-dominant cells, which are shown
a smaller staff space — exactly as the scale model predicts.

## The response curve

Holding each cell fixed and varying only `imgsz`, over 30 measures of authored
music across all three fixtures, where every note count is exact:

| staff space shown | detected/true | measures exactly right | median box width |
|---|---|---|---|
| 8 – 22 | 0.88–0.89 | **24/30** | 1.27–1.30 ✓ |
| 26 | 0.96 | 17/30 | 1.27 |
| 38 | 1.23 | 4/30 | 1.24 |
| 50 | 1.77 | 3/30 | 0.87 |
| 100 – 150 *(the old default)* | 1.41–1.91 | 1–3/30 | 0.23–0.45 ✗ |

A notehead is about **1.25 staff spaces** wide, so the box-width column says
whether the boxes are notehead-shaped at all. It holds across the plateau and
then collapses: the count and the shape fail together, which is what makes this
a scale problem rather than a threshold problem.

**The aggregate ratio is the wrong criterion.** It passes through exactly 1.00 at
a staff space of 30, where only 16/30 measures are individually right — over- and
under-counting cancel. Exact per-measure agreement is the honest column.

## What the curve does not capture

There is also an **absolute-resolution floor**, and the fixtures cannot see it
because every cell in them is either 1200 px tall or 2048 px wide. On WTC p.1,
whose staves each produce one full-width cell that `MAX_CELL_WIDTH_PX` squeezes
to a canonical staff space of 19, a small constant starves the detector:

| cell (2048×229, canonical space 19) | shows | noteheads found |
|---|---|---|
| per-cell (`imgsz` ≈ 1700) | 15.9 px | 5, 0, 39, 3, 21, 52, 30, 30, 44, 24 |
| fixed 512 | 4.8 px | 5, 0, 40, 3, 21, 52, 30, 30, 44, 24 |
| fixed 256 | 2.4 px | 1, 0, 22, **0**, 14, 13, 14, 13, 16, 7 |

512 clears the floor here despite showing only 4.8 px; 256 loses roughly half the
notes. So "lower the constant further" is not safe, and a purely scale-based
account of the curve is incomplete at the small end. The per-cell rule sits well
clear of both ends.

## Per-cell against the best fixed values

Same tree, same weights, at the pipeline's own **600 DPI**:

| setting | melody (24) | keyboard (27) | ensemble (45) |
|---|---|---|---|
| **per-cell** | 23 · R .708 · P .739 | 27 · R **1.000** · P **1.000** | 45 · R **.956** · P **.956** · dur .860 |
| fixed 256 | 23 · R .708 · P .739 | 27 · R **1.000** · P **1.000** | 45 · R **.956** · P **.956** · dur **1.000** |
| fixed 384 | 22 · R .667 · P .727 | 27 · R .963 · P .963 | 52 · R .956 · P .827 |
| fixed 512 *(main)* | 30 · R .667 · P .533 | 31 · R .926 · P .806 | 57 · R .867 · P .684 |
| fixed 640 | 38 · R .792 · P .500 | 38 · R .852 · P .605 | 69 · R .844 · P .551 |
| fixed 2048 *(old)* | 61 · R .375 · P .148 | 45 · R .407 · P .244 | 103 · R .400 · P .175 |

Per-cell beats 512 on every fixture and every metric, and ties 256 — which the
capped-cell table above then rules out. The reason is visible in what each rule
actually shows the model:

| cell | per-cell shows | fixed 512 shows |
|---|---|---|
| ensemble staff 0 m0 (2048×957, space 80) | 16.2 px | 20.0 px |
| ensemble staff 0 m1 (1331×1200, space 100) | 16.8 px | 38.5 px |
| melody m1 (301×1200, space 100) | 16.0 px | 42.7 px |
| WTC staff 2 m0 (2048×229, space 19) | 15.9 px | 4.8 px |

A constant lands *inside* the plateau on wide header cells and *past its edge* on
narrow interior cells — on the same page. That is the whole of the remaining
disagreement, and it is why the answer is a rule rather than a number.

## On real orchestral prints

The key-signature layer reads the detector's `keySharp` / `keyFlat` markers, so it
moves with this. Scored against hand-read ground truth
(`../omr-key-signature/eval_key_signatures.py --mode pipeline`), same tree:

| page | pinned 1280 *(what the harness used to force)* | fixed 512 | **per-cell** |
|---|---|---|---|
| Beethoven 5 p.2 | 0 correct / 0 wrong, 0/22 voted | 0 / 0, 0/22, 64s | **3 / 2**, 5/22, **30s** |
| Beethoven 6 p.2 | 0 correct / 4 wrong, 5/20 voted | 3 / 0, 6/20, 67s | **11 / 0**, 12/20, **28s** |
| Bach WTC p.17 | 10 / 0, 10/10 | 10 / 0, 10/10, 9s | 10 / 0, 10/10, 10s |

Beethoven 6 goes from **three correct signatures to eleven**, with no wrong ones,
on a 19th-century print where `tools/omr/README.md` records the detector emitting
*zero* key-signature markers. That claim was measured at an `imgsz` on the wrong
side of the cliff; a good deal of the "the detector goes blind on orchestral
prints" story may be the same artifact, and is worth re-opening.

Report the cost honestly: **Beethoven 5 gains three correct readings and two
wrong ones**, where before it abstained on all sixteen. This layer's doctrine
prefers a miss to a wrong answer — a missed signature leaves a staff where it
was, a wrong one re-pitches every note on it — so that trade is not free, and it
is the one result here that argues for more scrutiny rather than less.

Per-cell is also about **twice as fast** as the constant on these pages, because
the narrow orchestral cells get a small `imgsz` instead of 512.

> `../omr-key-signature/RESULTS.md` quotes pipeline-mode figures taken at the
> pinned 1280 and is now stale in that section. Its `component` mode, which runs
> no YOLO, is unaffected.

## The fix

`yolo_detector.imgsz_for_cell` computes `imgsz` from the cell's own canonical
staff spacing so the model is shown `TARGET_STAFF_SPACE_PX` (16), and
`detect(imgsz=None)` — now the default — uses it. Nothing else moves:
ultralytics returns boxes in the source image's frame whatever `imgsz` was, so
every downstream consumer sees the coordinates it saw before. `--imgsz 512` and
`--imgsz 2048` reproduce the two earlier defaults.

## Notes carried over from the other session, still true

**The F1 98.8% and the production pipeline were never the same configuration.**
`training/eval_on_score_cells.py` calls `detect()` without an `imgsz` and so ran
at the wrapper's old default of **640**, while the pipeline ran at 2048.

**The two defaults disagreed with each other** — the CLI at 2048, the web app's
`OMR_IMGSZ` at 1280 — and both were too large. Both now size per cell.

**`transcribe.py` had already recorded the effect for the clef reader** ("on a
0.42 crop, imgsz 640 beats 1280", `clef_reader_imgsz=640`). It was never
generalised to noteheads.

## One more claim this puts in doubt

`tools/omr/README.md` → "Each reader gets the picture it can read" says the model
finds *zero* key markers on a header crop "at imgsz 640, 1280 and 2048 alike",
and concludes that a letterboxed sliver is outside the model's training
distribution. A header crop is a few staff spaces wide; all three of those values
are far on the wrong side of the cliff, so the sweep sampled three points and no
contrast. The observation stands, the cause may not. Flagged in the README, not
acted on.
