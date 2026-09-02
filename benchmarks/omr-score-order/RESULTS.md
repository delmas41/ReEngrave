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
