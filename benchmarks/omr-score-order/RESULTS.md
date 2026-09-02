# The score-order prior — instrument identity from position

**2026-08-28.** Thread 3 of `docs/next-steps-omr-2026-08-28.md`.

Score order is one of the strongest conventions in music printing: instruments
run top to bottom in family order and never out of it. So "which instrumentation
is this page?" is not a classification — it is a monotone alignment of the
staves against a small library of standard layouts, which is the machinery
`slots.py` already uses to align one system against another. Only the reference
differs: there it is the largest system observed, here it is a layout the
printing tradition supplies.

Reproduce: `python3 benchmarks/omr-score-order/eval_score_order.py`.
Ground truth is `ground_truth.json` — two pages read part by part off a render
of the left margin, which is the irreplaceable half of this benchmark.

## Results

| page | evidence | layout chosen | named | correct | precision |
|---|---|---|---:|---:|---:|
| beet5-p15 sys 0 (12 staves) | position only | classical-condensed | 7 / 12 | 7 | **1.00** |
| beet5-p15 sys 0 | + clefs the CV locator reads | classical-condensed | 7 / 12 | 7 | 1.00 |
| beet5-p15 sys 0 | + the true clefs | classical-condensed | 11 / 12 | 11 | **1.00** |
| lamer-p25 (21 staves) | position only | late-romantic-large | 5 / 21 | 4 | 0.80 |
| lamer-p25 | + clefs the CV locator reads | classical-condensed | 1 / 21 | 1 | 1.00 |
| lamer-p25 | + the true clefs | **french-large** | 12 / 21 | 12 | **1.00** |

**Clefs are what choose the tradition.** On La Mer, position alone picks the
German large-orchestra layout; the true clefs pick the French one, which is
right — Debussy's publisher prints the piccolo BELOW the flutes, and a bassoon
in bass clef and a viola in alto are the anchors that hold the middle of the
system in place. Position alone gets 8 of 21 staves right there; with clefs it
is 18 of 21 before the agreement filter, 12 of 12 after it.

**End to end, on the page that previously had nothing.** Beethoven 5 p.15 is a
scan with no text layer, so `contextual.py` used to stop at *"no text layer —
instrument identity unavailable"*. It now reports 10 of 12 staves, 8 correct:

```
Flute Oboe Clarinet Bassoon Horn Trumpet Timpani  — all correct
Violin ✓   Violin ✗(Viola)  Violin ✗(Cello)       — the two errors
```

Both errors are one thing: the viola and cello staves' clefs are **misread as
treble**, and the prior faithfully concluded that three treble staves are three
violin staves. It inherits the clef problem exactly as the key-signature reader
does, and for the same reason.

That is why identity deduced from position was **not** allowed to drive clef
correction (`contextual.py`): using it there would let the prior rewrite the
clefs whose misreading produced it. It is written into the JSON as
`instrument_source: "score_order"`, where a reader can see it and judge it.

**Narrowed 2026-09-01, and this page is why it is safe.** The loop needs the
SLOT'S OWN clef to be in the prior's evidence, so the gate is now `slot not in
clef_by_slot` rather than a blanket refusal — a name deduced for a slot the
prior saw no clef for carries no echo of a clef it would then rewrite. The
errors described just above are untouched by it: the prior's failure here is
calling string staves *violins*, and a violin proposes the treble those staves
already carry, so nothing is applied. Beethoven 5 p.15 changes zero clefs under
the new gate; La Mer p.25 changes one, staff 20 treble → bass on a `Contrabass`
the part list above confirms. End to end 146 → 148/166 free and 149 → 151 paid.
See `benchmarks/omr-clef-geometry/RESULTS.md`, "JOB C" — including why the +2
is worth less than it looks.

## Two design decisions that measurement forced

**Confidence is agreement, not margin.** The first version offered a fit only
when the best layout beat the runner-up by a margin. That is the wrong
instrument: the natural margin between neighbouring traditions is about 0.05 per
staff — Beethoven 5 p.15 fits `classical-condensed` at 1.000 and
`classical-shared-bass` at 0.952 while being **12 of 12 correct** — so any
threshold that rejects a coin flip also rejects a page read perfectly. What
separates a confident staff from a doubtful one is whether the plausible layouts
*agree about that staff*. Every layout within 0.15/staff of the best now votes,
weighted by score, and a staff is named only at 0.75 agreement. Swept:

| agreement | with clefs | position only |
|---|---|---|
| 0.60 | 29 named, 27 correct | 18 named, 13 correct |
| **0.75** | **23 named, 23 correct** | **12 named, 11 correct** |
| 0.80 | 22 named, 22 correct | 5 named, 4 correct ← cliff |

**A part can take more than one staff.** Two horns, a harp, divided violins:
without a continuation move the alignment slips by one at the horns of La Mer
p.25 and never recovers — 8 of 21 staves right. With it, the same page is 21 of
21 before filtering. A layout is a list of PARTS; a page prints staves.

## What it settles

`Tp.` is Timpani in the German and Italian tradition and Trumpet in the English
one. The lexicon had to pick one, and picked Timpani with a comment naming the
page it was measured on and saying a score-order prior should settle it
properly. It now does: `instruments.AMBIGUOUS_ALIASES` declares the ambiguity
and `score_layouts.resolve_ambiguous_label` reads the answer off the position —
timpani below the trumpets, trumpet where the trumpets are, and no opinion at
all where the prior cannot see. The alias table is unchanged, so a page the
prior cannot read keeps exactly the reading it had.

## Limits

- **The library is small and European.** Ten layouts. A tradition it does not
  carry gets abstention, not a wrong answer — but it does mean the prior is
  silent on, say, a brass band or a gamelan score.
- **It inherits clef reading**, as above.
- **Two hand-read pages is a thin ground truth.** Precision is 1.00 on
  everything it named with correct clefs, over 23 staves. That is a real number
  but a small one, and the two orchestral pages of the key-signature benchmark
  can no longer be scored on this machine (their PDFs are gone), so this is what
  there is.

---

## The ruler was wrong in two ways — corrected and widened, 2026-09-01

Job C's identity half opened on a number from this file: *the prior names 12 of
33 staves at 0.92 precision from position, and 0.50 on read clefs, which is what
production uses.* **Production uses neither.** Both halves of that sentence
describe configurations no run performs, and the corrected measurement says
something different about where the work is.

### 1. "read clefs" is the CV locator alone, and the locator is 3 staves of 166

`read_clefs()` calls `locate_clef` and nothing else — deliberately, so this
benchmark needs no weights, and the docstring says so. But production hands
`fit_layouts` the output of `contextual._read_clefs_by_slot`, and on the ten-page
clef corpus its 122 sourced clefs are **97 detector + 12 header + 9 dossier + 3
locator + 1 slot-continuity**, the detector alone at 98% on the staves it covers.

Quoting 0.50 as production's number is quoting the weakest reader in the stack.
A `--pipeline` arm now measures the real thing.

### 2. The benchmark fits ONE SYSTEM; production fits the page

`fit_layouts(len(reference))` — the slot set `assign_slots` builds across every
system of the page — and one fit then reaches every system through the slots.
Scoring a system at a time is a second way to measure something that never runs.
A `--production` arm now goes through `apply_contextual_analysis` itself, with
the label readers switched off so what is measured is the prior.

### 3. The corpus was 2 pages of 1 edition

`--wide` adds two truth sources that were already in the repo: 36 staves the PDF
text layer names across 12 systems of Beethoven 5 and 6, and Beethoven 5 p.48's
17 hand-read slots. Nine pages, four editions.

⚠️ **The manifest's stored `instrument` is not ground truth — its `text` is.**
That file was written on 2026-08-31 and froze a lexicon bug fixed hours later the
same day: Beethoven 5 p.59's three trombones are stored as `Tr. Alt.` → Alto,
`Tr. Ten` → Tenor and `Tr. Bas` → Trumpet — two singers and a trumpet where the
page prints trombones. A stored resolution measures the lexicon of its day, so
the harness re-resolves the printed text through today's.

### What the corrected ruler says

```
python3 benchmarks/omr-score-order/eval_score_order.py --wide --production
```

| arm | named | correct | precision |
|---|--:|--:|--:|
| position only | 22 | 21 | **0.95** |
| read clefs — the CV locator, as before | 24 | 13 | 0.54 |
| **PRODUCTION — page-level fit, every reader** | **44** | **32** | **0.73** |
| true clefs — the ceiling | 36 | 33 | 0.92 |

So the prior is **not** the narrow, high-precision thing the old number
described. In production it names twice what the position arm does — 44 against
22 — at 0.73. The lever is no longer coverage. It is precision.

### Where the 12 errors are, and they are one shape

Seven of the twelve come from four pages where the winning layout is far too
small for the system, and the continuation move — which exists so that two horns
or a divided violin section can take more than one staff — is carrying every
part instead of a few:

| staves per part of the winning layout | pages | named right | named wrong |
|---|--:|--:|--:|
| 0.82 – 1.09 | 7 | **32** | 5 |
| 1.75 | 4 | **0** | **7** |

Nothing sits between 1.09 and 1.75. At 1.75 it is `string-quartet` stretched
over Beethoven 5 p.40's seven-staff condensed systems — calling each top staff
Violin, where the page prints Oboe, Oboe and Bassoon — and `classical-condensed`
stretched over La Mer's 21 staves, where the true layout is `french-large`. La
Mer's own truth is 21 staves for 17 parts, **1.24**: real division does not reach
1.75.

**The root cause is a gap in the layout library, not a bad fit.** The ten layouts
run 2, 4, 4, 4, 11, 12, 13, 16, 17, 20 parts, and there is **no
orchestra-plus-voices layout at all**. Beethoven 9's choral finale is 21 staves
of orchestra and six vocal staves; the best the library can offer is a 12-part
classical layout stretched to 1.75, and the prior then calls the vocal block
Viola. That is the same page whose two "gains" the clef benchmark records under
JOB C in `benchmarks/omr-clef-geometry/RESULTS.md` — a wrong identity landing on
the right clef class.

### Shipped: the missing layout, and the abstention it makes free

**`choral-orchestral`, 24 parts.** A choral symphony or requiem, where **the
strings split around the voices** — violins and viola above the vocal block,
cellos and basses below it. No other layout here does that, and nothing else in
the library is bigger than 20 parts. Beethoven 9's finale is the canonical case
and Beethoven 5 p.15's edition prints the same shape; Mahler 2 and 8 and the
Verdi Requiem are the same instrumentation.

Beethoven 9 p.120 now fits it at **0.88 staves per part** instead of
`classical-condensed` at 1.75, and the alignment is musically right where it
speaks: staff 3 Bassoon, 5 Horn, 7 Trumpet, 8 Timpani, 10 Violin, 11 Viola,
19 Cello, 20 Contrabass — against a hand-read clef column that has the viola's
waist plainly on line 3 at staff 11.

**`MAX_STAVES_PER_PART = 1.5`**, from the table above. With the layout in place
this costs nothing at all, because the page it would have cost is no longer in
the stretched regime.

| harness | before | after |
|---|--:|--:|
| identity, **PRODUCTION** arm — 9 pages, 4 editions | 44 named / 32 correct, **0.73** | 37 / 32, **0.86** |
| identity, locator arm, `--wide` | 24 / 13, 0.54 | 11 / 10, 0.91 |
| identity, position arm, `--wide` | 22 / 21, 0.95 | 20 / 19, 0.95 |
| `eval_score_order` default — position | 12 / 11, 0.92 | 10 / 9, 0.90 |
| `eval_score_order` default — read clefs | 10 / 5, 0.50 | 2 / 2, 1.00 |
| `eval_pipeline_clefs --assist none` | 148 / 166 | **146 / 166** |
| `eval_pipeline_clefs --assist vision` | 151 / 166 | **149 / 166** |
| base 3 · `probe_clef_rejection` · `check_clef_precision` | 52/52 · 68/720 · FP 13 | unchanged |
| `pytest tools/omr/tests` | 1114 | 1116 |

**No correct name is lost anywhere.** The production arm keeps all 32 and drops
7 wrong ones; the position arm's 22→20 is La Mer, where the new layout joins the
vote band and the agreement filter then names three staves instead of five.

### What it costs, stated first because it is the number people quote

**Clef accuracy goes DOWN by two, on both arms**, and both are beet9-p120:
16/21 → 14/21. Those two staves were the whole of Job C's `+2`, and they were a
wrong identity producing a right clef class — `classical-condensed` stretched
over the page called the vocal block Viola, and a viola's alto clef scores
against a truth that deliberately records the generic `c-clef`.

With the right layout the prior names those staves **nothing**: the agreement
filter finds the plausible layouts disagreeing there, which is the truthful
answer for six vocal staves in a corpus of orchestral layouts. And correct
identity would not recover the points either — `instruments.py` gives Soprano,
Alto and Tenor a **treble** default, the modern convention, so a correctly named
choral staff proposes treble and nothing moves. The handoff predicted exactly
this ceiling.

So the trade is 2 clef staves for 13 points of identity precision, on a clef
corpus that cannot see identity at all. Worth knowing before quoting either.

### Still open

* **The vocal-clef convention.** A 19th-century vocal part prints soprano, alto
  and tenor C clefs where a modern one prints treble. That is a fact about the
  edition, not the instrument, so it does not belong in `default_clef`; it wants
  something that knows the print's date or reads the glyph. Six staves of
  beet9-p120 wait on it.
* **beet9-p60 fits at 2.18 staves per part** and now abstains — 24 staves
  against `classical-shared-bass`'s 11. It is a Beethoven 9 page too, so the new
  layout does not cover it either; look at what 24 staves of that edition
  actually are before adding another.
