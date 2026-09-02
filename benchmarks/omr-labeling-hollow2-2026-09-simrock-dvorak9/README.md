# Labeling batch: hollow noteheads — Dvorak 9, Simrock 1894

One of the five print-diverse follow-ups to
[`benchmarks/omr-labeling-hollow-2026-08`](../omr-labeling-hollow-2026-08/README.md).
Read that batch's README for **why** hollow noteheads, and its
[AUDIT.md](../omr-labeling-hollow-2026-08/AUDIT.md) for how the first one
actually went.

## The edition

| | |
|---|---|
| work | Dvorak, Symphony No. 9 in E minor, Op. 95 'From the New World' — movement I |
| edition | N. Simrock, Berlin, 1894, plate 10139 |
| publisher | N. Simrock |
| source | IMSLP 405834 (`library/editions/dvorak/symphony-9-op95/dvorak--symphony-9-op95--simrock-1894--imslp405834.pdf`) |
| raster | 5088x6976 jbig2 bitonal @601 ppi |
| pages used | PDF pages 5, 6, 7 (0-based); the movement begins on PDF page 4 |

A **different publisher and a different decade** from the Litolff Beethoven —
Simrock's Berlin house style, 1894 — at the same scan resolution, so the
variable is the printing rather than the photograph. Simrock's ink is
noticeably lighter and its lines thinner than Litolff's, which is the point.

PDF page 5 (printed 183) is transcribed for the meter but **contributes no
cells** — it is the page `benchmarks/omr-scan-e2e-2026-09` scores.

⚠️ **This is the small batch of the set** and deliberately so: only 25 bars on
these three pages fall short of their own meter by the 25% the selector
requires, against 43-49 per page on the Beethoven. That is the selector
declining to pad rather than a failure — the same thing Boléro p.4 did in the
first batch. The pages do print the class: a half note under a trill is plainly
visible in `dvorak9-p8-sys1-s10-m2`.

## What is in it

**25 cells**, chosen by meter shortfall (`select_short_bar_cells`),
not uniformly — a bar whose detected content does not fill its own meter is
missing something, and ranking by that is worth about four times uniform
sampling. Meters read: `4/4` ×18, `2/4` ×3, `3/4` ×2, `3/2` ×1, `1/1` ×1.

| source page | cells |
|---|---|
| PDF page 5 | 2 |
| PDF page 6 | 7 |
| PDF page 7 | 16 |

`SHORT_BAR_HINTS.txt` carries the per-cell figure — the meter, how many beats
resolved, how many are missing. **A bar missing about half its meter is the
signature of an undetected half note.** It is a place to look, not a claim.

### The pages were checked before the cells were cut

⚠️ **The shortfall ranking finds bars the pipeline got WRONG, which is the same
thing as a hollow notehead only where the page prints them.** A first attempt
at this round ranked 51 cells off three pages of Beethoven's *Allegro con
brio*; a look at twelve of them at random found **not one** hollow head,
because that music is beamed quavers throughout and its short bars are short
for beam reasons. The pages were re-picked and the batch rebuilt.

So every page in this batch was **looked at first** — rendered as a legible
band and read for open noteheads — and only pages that visibly print them were
sent to the selector. That check is worth more than any deficit threshold, and
it is the thing to repeat before building the next batch.

## ⚠️ Draw from scratch — the detections files are empty on purpose

`detections/` holds an empty stub per cell. **Nothing is pre-labelled and
nothing should be.**

The first batch was planned as triage, on the assumption that the model boxes
most black noteheads correctly and only the hollow heads need drawing. The
audit measured that assumption and it is false on this kind of print: **116 of
117 model pre-labels were culled as false positives** — firing on slur arcs, on
barlines, on staff lines, on the bowl of a printed **p**, and 45 of them on the
very glyphs Sean had just called hollow. Exactly one survived.

So there is nothing to confirm here. Every box in this batch is drawn by hand
with `a`.

## What to draw

The classes this batch exists for:

- `noteheadHalfOnLine` / `noteheadHalfInSpace`
- `noteheadWholeOnLine` / `noteheadWholeInSpace`

On-line versus in-space is the **notehead's own** position, not the stem's.

**Completeness matters, and it is scoped.** Anything left unboxed is trained as
background. The first batch's export resolved this by labelling the
*notehead/rest/accidental* enumeration completely and accepting that clefs,
slurs and dynamics in those cells go unlabelled — recorded in AUDIT.md as a
real cost rather than taken silently. Do the same here: box every notehead,
rest, accidental, augmentation dot and flag in a cell you touch, or skip the
cell. Skip anything too bled to read — a guess is worse than an absence.

Per CLAUDE.md, **never** box staff lines, stems or beams (classical CV detects
those upstream and YOLO cannot bbox a thin line), and never box free text.

## Labelling it

```bash
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9
# → http://127.0.0.1:5050
```

`a` draws a new box and stays in draw mode (`Esc` stops) · `c` fixes a class
(`/` searches) · `b` redraws a bbox · `Del` removes the selected box · `Tab`
moves on and autosaves. The full rules are in CLAUDE.md under "Hand-label cells
for OMR training".

## Expected yield

Calibrated on the first batch, whose Beethoven half is the same failure mode:
**0.87 hollow boxes per cell** for cells missing ≥ 1.25 beats and 0.29 for
those missing 0.75–1.25. This batch has 19 and 5 of them, so the estimate
is **≈ 18 hollow noteheads**.

⚠️ **The predictor is the print, not the deficit.** The first batch's ten
Boléro cells were short by *more* beats than any Beethoven cell and yielded
**zero** — a clean 2016 typeset, where the model reads hollow heads perfectly
well and the missing beats came from something else. Every page here is a
scan of old print for that reason, but the rate is measured on one edition and
Simrock's ink is not Litolff's; treat the figure as an order of magnitude.

## When the labelling is done

```bash
python3 -m tools.omr.training.verdicts_to_yolo_labels \
    --verdicts-dir benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9/verdicts \
    --manifest benchmarks/omr-labeling-hollow2-2026-09-simrock-dvorak9/cells.json \
    --version-name v<n>-2026-09-hollow-simrock --out-root data/user-labeled \
    --labeler sean --description "hollow noteheads, Simrock 1894 Dvorak 9 Adagio" \
    --dry-run
```

`noteheadHalf*` and `noteheadWhole*` are already DSv2 classes, so this adds
examples rather than classes and none of the Phase 3.4 head-reinitialisation
risk applies. Catalog membership is a **training-time decision** — it now lives
in `data/user-labeled/catalog-versions.txt`, and `build_catalog_yaml` builds
exactly what that file lists.

Then commit the verdicts. They are irreplaceable human work and the cell PNGs
are gitignored by design.
