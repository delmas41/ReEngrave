# Labeling batch: hollow noteheads — Brahms 1, Breitkopf & Hartel

One of five print-diverse follow-ups to
[`benchmarks/omr-labeling-hollow-2026-08`](../omr-labeling-hollow-2026-08/README.md).
Read that batch's README for **why** hollow noteheads, and its
[AUDIT.md](../omr-labeling-hollow-2026-08/AUDIT.md) for how the first one
actually went. The first round labelled **one edition**; the failure is
appearance-specific, so this round varies the press.

## The edition

| | |
|---|---|
| work | Brahms, Symphony No. 1 in C minor, Op. 68 — movement I |
| edition | Breitkopf & Hartel, *Brahms Samtliche Werke* |
| publisher | Breitkopf & Hartel |
| source | IMSLP 317803 (`library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf`) |
| raster | ~5280x6945 ccitt bitonal @~534 ppi (dimensions vary per page) |
| pages used | PDF pages 1, 2, 3 (0-based) |

A **third house style** — Breitkopf & Hartel's collected edition — and a
different compression, ccitt rather than jbig2, which degrades an old print in
its own way.

The movement is *Un poco sostenuto* in **6/8**. ⚠️ That meter is also why this
batch is thin, and the mistake is worth recording: a bar is three quarter-beats,
so the sustained wind lines under the opening are **dotted quarters**, which are
solid. Only a dotted *half* is hollow. A page-level look at the horns suggested
a rich page; the cells say otherwise.

PDF page 0 is left out entirely — it is the page
`benchmarks/omr-scan-e2e-2026-09` scores.

## What is in it

**56 cells.** Every page was chosen by *looking at it* and every cell by a
hollow-notehead score — see below. Scores of the kept cells run
2–6 (mean 3.2); the per-cell
figure is in `HOLLOW_HINTS.txt`.

| source page | cells |
|---|---|
| PDF page 1 | 19 |
| PDF page 2 | 16 |
| PDF page 3 | 21 |

## How these cells were chosen — and why not by meter shortfall

The first round ranked bars by how far their detected content fell short of
their own meter, which it measured as worth **four times uniform sampling**.
That was tried first here and **does not transfer**, for two reasons found by
measuring rather than by argument:

**1. It ranks bars the pipeline got WRONG, which is the same thing as a hollow
notehead only where the page prints them.** Three pages of Beethoven's *Allegro
con brio* gave 51 nicely-ranked cells; twelve read at random contained **not
one** hollow head. That movement is beamed quavers throughout, so its short
bars are short for beam reasons.

**2. On most editions the meter is never read, so there is nothing to rank.**
Short bars found per page:

| | short bars/page | meters read |
|---|--:|---|
| Beethoven 5 / Litolff | 43–49 | `2/4` correctly |
| Dvorak 9 / Simrock | 2–16 | `4/4`, `3/2`, `1/1` mixed |
| Scheherazade / Eulenburg | 1–7 | `4/1`, `1/4` — garbage |
| Mahler 5 mvt I / Peters | 1–3 | none |

The Mahler case is structural and worth remembering: the *Trauermarsch* is in
**cut common**, and `time_signature_locator` deliberately never searches for
`timeSigCutCommon` — a stroked C correlates with any vertical ink over any
rounded blob, and enabling it once claimed a meter on seven systems that print
none. **So `select_short_bar_cells` is blind on a cut-common movement by
construction.**

So the filter moved to what is actually being looked for. A hollow notehead is
an ink ring around a white lens, so each cell is scored by counting the
**enclosed white regions of notehead-counter size and shape** in its
staff-line-removed crop.

⚠️ **This is a cell RANKER, not a detector, and the difference is the whole
point.** `benchmarks/omr-first-run-2026-08/DURATIONS.md` already closed the
detector route: as a way of proposing boxes it gave 662 candidates for 68 real
half notes. Asking only *does this cell contain one* is a far weaker question,
and it validates. Against the first round's 48 cells, where Sean's own verdicts
say which 25 hold a hollow head:

| | selects | correct | precision |
|---|--:|--:|--:|
| score ≥ 1 | 22 | 20 | **91%** |
| score ≥ 2 | 14 | 14 | **100%** |
| top-20 | 20 | 18 | 90% |
| *(uniform)* | — | — | *52%* |

**A band, not a top-N.** The count inflates on a lighter print without meaning
more half notes: Dvorak's top-scoring cells run 9–47 and are runs of beamed
semiquavers, where the "counters" are the gaps between beams and the loops of
the word *cresc.* Cells are therefore drawn from the band **2–6** and sampled
randomly inside it.

## Measured yield for THIS batch

Twelve of these 56 cells were read by eye: **3 of 12 contain at least one
hollow notehead**, 5 in total. Scaled to the batch, expect **≈ 23
hollow noteheads**.

**The thinnest of the five.** In 6/8 the sustained wind lines are written as *dotted quarters*, which are solid — only the dotted halves are hollow, and there are fewer of them than the page's look suggests. Kept because Breitkopf's ccitt scan is an appearance nothing else here covers.

That is a count of what is *visible in the crop*, not a promise — some will
turn out to be a bled `p` or the eye of an `8`, and some hollow heads will be
in the other 44 cells.

## ⚠️ Draw from scratch — the detections files are empty on purpose

`detections/` holds an empty stub per cell. **Nothing is pre-labelled and
nothing should be.**

The first round was planned as triage, on the assumption that the model boxes
most black noteheads correctly and only the hollow heads need drawing. Its
audit measured that assumption and it is false on this kind of print: **116 of
117 model pre-labels were culled as false positives** — firing on slur arcs, on
barlines, on staff lines, on the bowl of a printed **p**, and 45 of them on the
very glyphs Sean had just called hollow. Exactly one survived.

## What to draw

- `noteheadHalfOnLine` / `noteheadHalfInSpace`
- `noteheadWholeOnLine` / `noteheadWholeInSpace`

On-line versus in-space is the **notehead's own** position, not the stem's.

**Completeness matters, and it is scoped.** Anything left unboxed is trained as
background. The first round's export labelled the *notehead / rest /
accidental* enumeration completely and accepted that clefs, slurs and dynamics
in those cells go unlabelled — recorded in its AUDIT.md as a real cost rather
than taken silently. Do the same: box every notehead, rest, accidental,
augmentation dot and flag in a cell you touch, or skip the cell. Skip anything
too bled to read — a guess is worse than an absence.

Per CLAUDE.md, **never** box staff lines, stems or beams (classical CV detects
those upstream and YOLO cannot bbox a thin line), and never box free text.

## Labelling it

```bash
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1
# → http://127.0.0.1:5050
```

`a` draws a new box and stays in draw mode (`Esc` stops) · `c` fixes a class
(`/` searches) · `b` redraws a bbox · `Del` removes the selected box · `Tab`
moves on and autosaves. Full rules: CLAUDE.md, "Hand-label cells for OMR
training".

## When the labelling is done

```bash
python3 -m tools.omr.training.verdicts_to_yolo_labels \
    --verdicts-dir benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/verdicts \
    --manifest benchmarks/omr-labeling-hollow2-2026-09-breitkopf-brahms1/cells.json \
    --version-name v<n>-2026-09-hollow-breitkopf --out-root data/user-labeled \
    --labeler sean --description "hollow noteheads, Breitkopf Brahms 1 sostenuto opening" \
    --dry-run
```

`noteheadHalf*` and `noteheadWhole*` are already DSv2 classes, so this adds
examples rather than classes and none of the Phase 3.4 head-reinitialisation
risk applies. Catalog membership is a **training-time decision** — it lives in
`data/user-labeled/catalog-versions.txt`, and `build_catalog_yaml` builds
exactly what that file lists.

Then commit the verdicts. They are irreplaceable human work and the cell PNGs
are gitignored by design.
