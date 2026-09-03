# Labeling batch: hollow noteheads — Debussy *La mer*, Durand (French)

**Phase 2 of the hollow-notehead row** — the four missing engraving traditions
named in
[`benchmarks/omr-labeling-survey-2026-09/SURVEY_DESIGN.md`](../omr-labeling-survey-2026-09/SURVEY_DESIGN.md)
§2 (**Durand** / Universal / Jurgenson / Novello). Rounds 1–2 cut the row
across the five German + miniature houses; this round adds the distinct
national/period traditions. Read
[`../omr-labeling-hollow2-2026-09/README.md`](../omr-labeling-hollow2-2026-09/README.md)
for the method, and
[`../omr-labeling-hollow-2026-08/AUDIT.md`](../omr-labeling-hollow-2026-08/AUDIT.md)
for why every batch is drawn from scratch.

**This is the Durand / French column** — canonical French engraving, distinct
glyphs. Round 1's "Boléro" control was a *born-digital Durand typeset*, so the
French **scan** appearance was genuinely unrepresented until now.

## The edition

| | |
|---|---|
| work | Debussy, *La mer*, CD 111 — movement I, *De l'aube à midi sur la mer* |
| edition | Durand & Fils, Paris (plates D. & F. 6532, 6838) |
| publisher | Durand |
| tradition | **French** (survey column #5) |
| source | IMSLP 15420 (`library/editions/debussy/la-mer-cd-111/debussy--la-mer-cd-111--durand-fils--imslp15420.pdf`) |
| raster | 2736x3582 px grayscale (~300 ppi native), rendered @600 dpi for the cut |
| pages used | PDF pages 1–6 (0-based) = printed pages 144–149; the movement begins on PDF page 0 (printed 143), skipped for its title header |

**Why this movement.** *De l'aube* is the sustained one — the *Très lent*
opening holds the timpani on whole notes under a trill, the low strings and
divided winds on tied half notes, and the harps on shimmering figures over the
top. It is hollow-rich, but less concentrated than Mahler's pedal: the
running-32nd "water" texture is dense, so the yield is lower.

## What is in it

**56 cells**, chosen by the round-2 enclosed-white ranker (`hollow_score.py`),
**band 2–6** (kept scores **2–6, mean 3.5**; per-cell figure in
`HOLLOW_HINTS.txt`). Cells/page: `{1:11, 2:8, 3:8, 4:11, 5:9, 6:9}`.

⚠️ **La mer's running texture is exactly what inflates the ranker** — its
densest cells score 9–23 (beamed-semiquaver gaps and slur crossings, not
noteheads), which is why the band is **capped at 6**, dropping that whole tail.

**Draw-from-scratch.** `detections/` holds an empty stub per cell — no model
pre-labels. Every box is a human one.

**Expected yield ≈ 15–25 hollow boxes** — comparable to round-2's weaker
German batches (Simrock/Dvořák ≈19, Breitkopf/Brahms ≈23). By eye, roughly
15–25 of the 56 cells carry a hollow notehead (the whole notes under trills,
the sustained-wind and half-note chords); the rest are the *water*-texture
running figures and the French tempo text (*Modéré, sans lenteur — Dans un
rythme très souple*). The **Durand engraving of a hollow notehead** is the
point — that appearance is what these cells carry.

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
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow3-2026-09-durand-lamer
# → http://127.0.0.1:5050
```
