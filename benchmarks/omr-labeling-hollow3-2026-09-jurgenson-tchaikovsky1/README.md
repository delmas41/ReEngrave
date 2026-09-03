# Labeling batch: hollow noteheads — Tchaikovsky 1 Adagio, Jurgenson (Russian)

**Phase 2 of the hollow-notehead row** — the four missing engraving traditions
named in
[`benchmarks/omr-labeling-survey-2026-09/SURVEY_DESIGN.md`](../omr-labeling-survey-2026-09/SURVEY_DESIGN.md)
§2 (Durand / Universal / **Jurgenson** / Novello). This is the **Jurgenson /
Russian column.**

## ⚠️ This is a substitute work — read this first

The survey named **Tchaikovsky 4 (IMSLP 377460)** for the Jurgenson column, and
flagged it "skewed — needs care", offering **Tchaikovsky 6 (922722)** as the
cleaner alternative. On inspection **Tchaikovsky 4 is unusable for the hollow
row** and **Tchaikovsky 6 is not in the library**, so this batch uses
**Tchaikovsky Symphony No. 1** — the same house, the same Russian tradition, a
full orchestra — choosing the best available Jurgenson *work* for this symbol
row, which is exactly how the survey chose every other representative (Peters →
Mahler 5 *Adagietto* for its sustained writing).

**Why Tchaikovsky 4 was rejected** (measured, not assumed):
- the scan is **skewed** throughout (the deskew recovers it, but);
- the work is **dense end to end** — no sustained slow movement; the Andantino
  is flowing quavers, the Scherzo is pizzicato (solid), the Finale is fast;
- so the enclosed-white ranker fires on **text loops and beam gaps, not
  noteheads**: two band-2–6 cells sampled at random both scored 3 with **zero**
  hollow notes — the round-2 "inflates on dense/texty prints" failure at full
  strength.

The other full-orchestra Jurgenson works fail too: the **1812 Overture**
(23744) opens on a chorale in *quarter* notes buried under the printed
performance-note text (measured — band cells are title/Cyrillic text, not
hollow), and the **Serenade Op. 48** (380582) is a string orchestra. Tchaikovsky
1's **Adagio cantabile** (mvt II, "Land of Gloom, Land of Mist") is the one
Jurgenson orchestral page with genuine sustained hollow content.

## ⚠️ …and it is a LOW-RESOLUTION scan

The native raster is **1500x2210 px (~72 ppi effective)** — the lowest in the
whole survey, well below the other three Phase-2 batches (2736–4500 px) and
every round-2 batch (2938–5409 px). The cells are soft. **The open/solid
distinction still reads clearly** (verified by eye — the whole notes and
half-note chords are unambiguous), so the batch is labellable, but weigh the
resolution when deciding whether the labelled cells earn a place in the training
mix — that is a separate, gated decision (SURVEY_DESIGN §4), not this batch's to
make.

## The edition

| | |
|---|---|
| work | Tchaikovsky, Symphony No. 1 "Winter Daydreams", Op. 13 — movement II, *Adagio cantabile ma non tanto* ("Land of Gloom, Land of Mist") |
| edition | P. Jurgenson, Moscow, 1875, plate 2513 |
| publisher | Jurgenson |
| tradition | **Russian** (survey column #9) |
| source | IMSLP 369941 (`library/editions/tchaikovsky/symphony-1-op13/tchaikovsky--symphony-1-op13--jurgenson-1875--imslp369941.pdf`) |
| raster | **1500x2210 px jpeg (~72 ppi native — LOW)**, rendered @300 dpi for the cut |
| pages used | PDF pages 40–44 (0-based) = printed pages 37–41, the sustained "1 SOLO" section of the Adagio |

**Why these pages.** The Adagio's sustained-chord accompaniment under the wind
solos (tied half and whole notes, pages 41–43 especially) is the hollow
content. The movement *opening* (printed 35–36) was excluded — its winds rest,
so it is mostly empty cells; the later climax is dense. A first 8-page cut
over-sampled the empty opening, so this cut is tightened to the five
sustained pages.

## What is in it

**56 cells**, chosen by the round-2 enclosed-white ranker (`hollow_score.py`),
**band 2–6** (kept scores **2–6, mean 3.4**; per-cell figure in
`HOLLOW_HINTS.txt`). Cells/page (0-based): `{40:8, 41:12, 42:13, 43:10, 44:13}`.

**Draw-from-scratch.** `detections/` holds an empty stub per cell — no model
pre-labels. Every box is a human one.

**Expected yield ≈ 25–35 hollow boxes.** By eye, roughly 19–25 of the 56 cells
carry a hollow notehead — page 43 is nearly all tied sustained chords. The false
cells are the flowing solo-melody quavers (solid) and the *a due* / *sempre*
markings; skip them.

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
python3 -m tools.omr.annotate.server --bench-dir benchmarks/omr-labeling-hollow3-2026-09-jurgenson-tchaikovsky1
# → http://127.0.0.1:5050
```
