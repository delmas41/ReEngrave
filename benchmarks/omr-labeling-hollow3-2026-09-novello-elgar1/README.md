# Labeling batch: hollow noteheads — Elgar 1, Novello (English)

**Phase 2 of the hollow-notehead row** — the four missing engraving traditions
named in
[`benchmarks/omr-labeling-survey-2026-09/SURVEY_DESIGN.md`](../omr-labeling-survey-2026-09/SURVEY_DESIGN.md)
§2 (Durand / Universal / Jurgenson / **Novello**). Rounds 1–2 cut the row
across the five German + miniature houses; this round adds the distinct
national/period traditions. Read
[`../omr-labeling-hollow2-2026-09/README.md`](../omr-labeling-hollow2-2026-09/README.md)
for the method, and
[`../omr-labeling-hollow-2026-08/AUDIT.md`](../omr-labeling-hollow-2026-08/AUDIT.md)
for why every batch is drawn from scratch.

**This is the Novello / English column** — the Elgar/Edwardian engraving
tradition, unrepresented until now.

## The edition

| | |
|---|---|
| work | Elgar, Symphony No. 1, Op. 55 — movement III, *Adagio* |
| edition | Novello & Co., London, 1908 |
| publisher | Novello |
| tradition | **English** (survey column #10) |
| source | IMSLP 56155 (`library/editions/elgar/symphony-1-op55/elgar--symphony-1-op55--novello-co-1908--imslp56155.pdf`) |
| raster | 4500x5998 px grayscale (600 ppi native), rendered @600 dpi for the cut |
| pages used | PDF pages 98–104 (0-based) = printed pages 95–101, the *Adagio*, ending "attacca" on PDF page 104 |

**Why this movement.** The *Adagio* is Elgar's sustained centre — the wind and
brass hold tied half notes and dotted halves over long empty bars (*fpp*,
*muta in A*), the bassoons carry a full row of sustained half notes into the
"attacca", and there are scattered whole notes in the string harmonics and
pedal points. It is the English tradition's answer to Mahler's pedal, minus the
seven-octave A: hollow-rich and low-density.

⚠️ **Deliberately not the movement openings.** Elgar's first-movement
*Andante nobilmente* and the Finale's *Lento* both open with the full
instrument list in the margin and heavy motto material; the *Adagio* interior
is cleaner and more sustained.

## What is in it

**56 cells**, chosen by the round-2 enclosed-white ranker (`hollow_score.py`),
**band 2–6** (kept scores **2–6, mean 2.9**; per-cell figure in
`HOLLOW_HINTS.txt`). Cells/page: `{98:7, 99:7, 100:8, 101:9, 102:7, 103:13, 104:5}`.

**Draw-from-scratch.** `detections/` holds an empty stub per cell — no model
pre-labels. Every box is a human one.

**Expected yield ≈ 35–50 hollow boxes.** By eye, roughly 30–38 of the 56 cells
carry a hollow notehead — the Adagio's tied/sustained half notes are abundant,
with some whole notes. The false cells are the expression text (*SOLO*/*TUTTI*,
*dim.*, *arco*) and the occasional beamed run; skip them.

## The pass

`batch_config.json` names a **single "hollow noteheads" pass** — one symbol in
the picker, click to place a staff-sized box (on-line vs in-space by click
position):

| slot | half note | whole note |
|---|---|---|
| on line | `noteheadHalfOnLine` | `noteheadWholeOnLine` |
| in space | `noteheadHalfInSpace` | `noteheadWholeInSpace` |

## Label it

```bash
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow3-2026-09-novello-elgar1
# → http://127.0.0.1:5050
```
