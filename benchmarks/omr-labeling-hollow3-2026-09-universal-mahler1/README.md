# Labeling batch: hollow noteheads — Mahler 1, Universal Edition (Vienna)

**Phase 2 of the hollow-notehead row** — the four missing engraving traditions
named in
[`benchmarks/omr-labeling-survey-2026-09/SURVEY_DESIGN.md`](../omr-labeling-survey-2026-09/SURVEY_DESIGN.md)
§2 (Durand / **Universal** / Jurgenson / Novello). Rounds 1–2 cut the row
across the five German + miniature houses (Litolff, Breitkopf, Peters,
Eulenburg, Simrock); this round adds the distinct national/period traditions.
Read
[`../omr-labeling-hollow2-2026-09/README.md`](../omr-labeling-hollow2-2026-09/README.md)
for the method and the two selector lessons it learned the hard way, and
[`../omr-labeling-hollow-2026-08/AUDIT.md`](../omr-labeling-hollow-2026-08/AUDIT.md)
for why every batch is drawn from scratch.

**This is the Universal-Edition / 20th-century-Viennese column** — the Mahler
cycle, a genuinely distinct engraving appearance from the 19th-century German
houses already labelled.

## The edition

| | |
|---|---|
| work | Mahler, Symphony No. 1 — movement I, *Langsam. Schleppend. Wie ein Naturlaut* |
| edition | Universal Edition, Vienna, 1906, plate U.E. 2931 |
| publisher | Universal Edition |
| tradition | **20th-c Viennese** (survey column #8) |
| source | IMSLP 17070 (`library/editions/mahler/symphony-1-gmw-11/mahler--symphony-1-gmw-11--edition-1906--imslp17070.pdf`) |
| raster | 2861x3817 px grayscale (~337 ppi native), rendered @600 dpi for the cut |
| pages used | PDF pages 0–4 (0-based) = printed pages 3–7; the movement — and the score — begins on PDF page 0 |

**Why this movement.** The opening is the single richest hollow-notehead source
in the whole survey. The famous seven-octave A *Naturlaut* pedal holds the
strings on tied **whole notes bar after bar** (Celli / Bässe / Viola
harmonics), so where the German houses give this class a handful of cells a
page, Mahler's intro gives it most of them — and it is the class with the least
existing coverage (**whole notes: 23 boxes across v1–v7**, against 130 for half
notes). Low staff-density (long empty wind lines under a held pedal) is exactly
what draw-from-scratch wants.

## What is in it

**56 cells**, chosen by the round-2 enclosed-white ranker (`hollow_score.py`):
count the notehead-counter-shaped white regions in each cell's
staff-line-removed crop, then take the **band 2–6** (not a top-N — the count
inflates on beamed runs and text). Kept scores run **2–6, mean 3.0**; the
per-cell figure is in `HOLLOW_HINTS.txt`. Cells/page: `{0:9, 1:8, 2:5, 3:14, 4:20}`.

**Draw-from-scratch.** `detections/` holds an empty stub per cell — no model
pre-labels (round 1 measured 116 of 117 pre-labels false on a scan). Every box
is a human one.

**Expected yield ≈ 50–70 hollow boxes.** A full-batch read by eye: roughly
35–40 of the 56 cells carry at least one hollow notehead (many carry several —
a tied pedal spans a whole bar), the rest are the opening's German tempo /
expression text (*Langsam. Schleppend*, *in weiter Entfernung*, *Nicht
schleppen*) whose letter-loops the ranker also counts. Skip those; label what
the cell shows.

## The pass

`batch_config.json` names a **single "hollow noteheads" pass** — the picker
shows one symbol, and a click places a staff-sized box, choosing on-line vs
in-space by where you click:

| slot | half note | whole note |
|---|---|---|
| on line | `noteheadHalfOnLine` | `noteheadWholeOnLine` |
| in space | `noteheadHalfInSpace` | `noteheadWholeInSpace` |

## Label it

```bash
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow3-2026-09-universal-mahler1
# → http://127.0.0.1:5050
```
