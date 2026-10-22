# The system-break rule: three fixes tried, all rejected, and why

**2026-08-31. Outcome: NOT FIXED. `assign_systems` still requires `bridging == 0`.**
This records the attempt so the next one starts from the measurements rather
than from the idea.

## What was wrong, and what the target was

`system_grouping.assign_systems` breaks a system only where the crossing-column
count is EXACTLY zero. Three adjudicated pages are genuine breaks with nonzero
bridging, so all three merge:

| page | truth | got | bridging at the true break |
|---|--:|--:|--:|
| B9 p25 | 2 | 1 | 66 |
| B9 p60 | 2 | 1 | 324 |
| B5 p40 | 3 | 1 | 3 and 11 |

Ground truth: `eval_grouping.py` (12 hand-read B9 pages + 2 B5), baseline
**12/14**, plus B5 p40 adjudicated from the margin in
`LEGATO_CROSSCHECK_2026-08-31.md`.

## Attempt 1 — how far RIGHT the crossing ink reaches

Idea: inside a system the barlines run its full height *including the closing
barline at the right edge*, so crossing ink runs out to the margin; at a real
break it stops short. Measured as the rightmost bridging column over the scan
window (`probes/fulldist.py`).

On the ground-truth pages this looked decisive — **262 boundaries, zero overlap**:

| | n | min | max |
|---|--:|--:|--:|
| true breaks | 10 | 0.000 | **0.958** |
| non-breaks | 252 | **0.969** | 0.980 |

It also subsumes the old rule (nothing crossing = reach 0.0). Implemented with a
threshold of 0.965 in the gap, and `eval_grouping.py` went **12/14 → 14/14**,
B5 p40 → `[7, 7, 7]`, no page regressed.

**Then the 54-page cross-check: 12 pages newly over-split.** Every one outside
the two Beethoven editions the threshold was measured on.

| | before | after | LEGATO |
|---|--:|--:|--:|
| La Mer p20 | 1 | **16** | 1 |
| Haendel lead-sheet p20 | 2 | **12** | 2 |
| Ravel Boléro p2 | 4 | **8** | 4 |
| Mahler 5 p10 | 1 | **4** | 1 |

Fixes 3 pages on 2 editions, breaks 12 on five others. Net loss. Reverted.

## Attempt 2 — reach measured against the staves' own right end

The page-wide window was the obvious suspect, so the reference became
`min(upper.x_end, lower.x_end)` — "does the ink reach the right end of THESE
staves" (`probes/variantB.py`). On the ground-truth pages it separates even more
cleanly:

    true breaks   2.15 .. 29.05 staff-spacings short of the staves' right end
    non-breaks   -0.13 ..  0.13

And it fails the same way. On the corpora attempt 1 broke, boundaries that are
*inside* a system sit up to **145 spacings short** — the exact signature of a
break.

## Attempt 3 — the band this module's own docstring specifies

Reading the module more carefully turned up something worth keeping regardless
of this fix: **the code does not implement its documented design.** The docstring
says the count runs over

> the band running from the **top line of the upper staff to the bottom line of
> the lower staff**

and argues that measuring the gap alone fails *for exactly the reason seen here*,
naming B9 p25's 66 columns. But `gap_bridging_counts` measures
`upper.bottom_y + 2 → lower.top_y - 2` — the gap only.

So attempt 3 was simply to implement what was written (`probes/variantC.py`).
It does not separate either:

    true breaks  [0, 0, 0, 2, 12, 14, 14, 20, 555, 808]
    non-breaks   min=11  p5=21  med=109  max=1796

Breaks at 12/14/14/20 sit inside a non-break range starting at 11, and two
breaks land at 555 and 808. **Whether the docstring should be corrected or the
code brought up to it is now an open question** — but the documented version is
not the fix, so nothing was changed.

## Attempt 4 — the bracket, against the WIDER ground truth

Retried after the set was widened to 23 pages / 5 editions, on the one direction
attempts 1-3 left open: **the bracket is the single element that genuinely spans
a whole system and stops at its end**, so isolating it should sidestep the
barline-continuity problem entirely. Measured in a zone anchored on the staves'
left edge, band running through both staves, so barlines never enter it.

**Perfect recall, no precision.** All 15 true breaks read 0 — but so do many
within-system gaps, and `min(non-break) = 0` in **every one of 32 configurations**
(zone left edge 2/3/5/8 spacings × right edge 0.5/2.0 × band through-staves or
gap-only × ink fraction 0.6/0.8). Zone width made no difference at all.

Not an anchor problem: `x_start` is tight on the offending pages (B9 p50 spans
278-307 about a median of 290; B5 p47 142-175 about 172). There is simply no
continuously-inked column in the bracket zone at some within-system boundaries —
a system bracket is a thin, curved, tapered engraving, not a printed rule, and
whether it clears an ink-fraction test over a tall band is *itself* an edition
property. Same mechanism as attempts 1-3, one layer down.

**What the wider ground truth bought:** this died in one measurement, before any
production change and before the 54-page cross-check. Attempt 1 needed an
implementation, a 14/14 score and a regression sweep to be caught. That is the
set doing its job.

**Worth keeping from it:** bracket-zone reach of 0 is a NECESSARY condition —
15/15 true breaks satisfy it and it never misses one. It is not sufficient alone,
but a future combined rule could use it as the cheap first filter and spend a
more expensive test only on the candidates it admits.

## Attempt 5 — instrument-label continuity (semantic, not typographic)

The idea that motivated it: labels RESTART at a system. That is a fact about the
music rather than about the engraving, so it should be immune to the mechanism
that killed attempts 1-4. Labels come from the production chain (text layer on
B9 and Boléro, Surya on the other 8 pages).

Four formulations, all against the 23-page set:

| rule | TP | FN | FP |
|---|--:|--:|--:|
| any instrument repeats | 10 | 5 | 58 |
| repeats, resetting at each predicted break | 10 | 5 | 21 |
| score-order RANK decreases (rank from the repo's own `LAYOUTS`) | 12 | 3 | 10 |
| rank-decrease **AND** bracket-reach 0 | 12 | 3 | **5** |

The shipped rule makes **3 page-level errors** on the same 23 pages. The best of
these makes 8. Rejected.

Four reasons it does not get there, all visible in the data:

- **Labels are sparse exactly where help is needed.** La Mer p2 carries 2 labels
  across 20 staves, Mahler p20 carries 1 across 16. A rule that needs labels
  cannot decide the pages that have none.
- **Localization is off by one** whenever the new system's top staff is
  unlabelled: B9 p25 predicts 12 for a true break at 11, Boléro p10 predicts 17
  for 16. Worse, intersecting with bracket-reach then DISCARDS those, which is
  why the combined rule's FP drop costs it nothing in FN but loses the two hits
  it had — the errors just move.
- **The canonical rank is itself edition-dependent.** Averaging the repo's ten
  layouts puts Violin (0.58) ahead of Timpani (0.67) and Percussion (0.83), so
  every Mahler page running Trombone → Tuba → Pauken → Gr.Tr. → Erste Viol.
  reads as a rank decrease and invents a break. Same failure shape as before,
  in a different coordinate system.
- **Doing it properly is circular.** `align_to_layout` would pick the right
  layout per page instead of averaging, but it is monotone and operates per
  SYSTEM — it needs the systems this rule is trying to find.

## Why none of them travel — the mechanism

**In orchestral engraving, barlines are deliberately broken between instrument
families.** Winds, brass and strings each get their own barline run. So "what
crosses this gap, and how far" is a property of the EDITION's engraving
convention, not of whether a system ends there.

Beethoven 9 and Beethoven 5 (the ground-truth editions) happen to run barlines
across their group gaps, which is why every signal looked clean on them. Mahler,
La Mer, Boléro and the Handel reductions do not, so within-system gaps there
carry the same signature as a break. Two editions is not a sample; it is a
coincidence that held twice.

That is the same lesson the clef thresholds taught, recorded in CLAUDE.md, and
it caught this work despite being known in advance — the ground-truth set is
narrow enough that a rule can score 14/14 on it and still be badly wrong.

## What the next attempt should have

- ✅ **DONE — ground truth from more than two editions.** Eight pages of Mahler 5,
  La Mer and Boléro were hand-read off the left margin and added to
  `eval_grouping.py`, chosen as the pages the rejected rule over-split so the
  next idea fails fast rather than scoring 14/14 and shipping. The set is now
  **23 cases across 5 editions**, and connectivity scores **20/23 (87%)** on it —
  the three failures still the known merges. Any candidate rule must hold all
  eight of these AND fix the three, which attempt 1 provably could not.

| score | page | staves | systems |
|---|--:|--:|--:|
| Mahler 5 | 2 / 10 / 20 | 15 / 18 / 16 | 1 / 1 / 1 |
| La Mer | 2 / 20 | 20 / 16 | 2 / 1 |
| Boléro | 2 / 10 / 20 | 27 / 32 / 19 | 4 / 2 / 1 |
- **The 54-page cross-check as the regression gate**, since it is the only thing
  that caught attempt 1. Run it before believing `eval_grouping.py`.
- A signal that does not assume barline continuity across group gaps. The
  bracket is the one element that genuinely spans a whole system and stops at
  its end — isolating the bracket column specifically, rather than counting all
  crossing ink, is the direction this leaves unexplored.

## Kept from the attempt

- `probes/fulldist.py`, `probes/variantB.py`, `probes/variantC.py` — the three
  measurements, runnable, so the next attempt starts with data.
- B9 (IMSLP 516488) is restored to the corpus, so `eval_grouping.py` runs at all.
- Three adjudicated failure pages: B9 p25, B9 p60, B5 p40.
