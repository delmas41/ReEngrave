# A dotted REST reads as undotted — the asymmetry, closed

2026-09-10. `docs/handoff-2026-09-10-the-duration-reader.md` §5.1, PARKED and
unclaimed by both sessions that found it. Taken here.

## 1. THE FAULT

`_rest_ruling` did `ev.rows(Q.AUG_DOT)` on the REST's own glyph subject —
**the exact fault fixed for noteheads the day before, in the same function,
one branch over.** GATHER files a dot at the DOT's own glyph, so asking a
rest's subject for one returns nothing and every dotted rest read as undotted.

⚠️ **What made it worth fixing is not the dot, it is the ASYMMETRY.** The
module handled dots for noteheads and silently not for rests, **which is worse
than the consistent gap it replaced**: a reader of the code cannot tell a
deliberate limitation from an oversight, and neither can a consumer of the
verdict.

## 2. IT IS NOT A NEW RULE — the legacy path already does this

`rhythm._pair_dots_to_targets` builds `dot_targets = noteheads + rests` and
scores both under the SAME two constants, with the comment *"dots after rests
are rarer but real"*. So the staged reader was **DIVERGING from the paid-for
rule, not reading it more narrowly**, and the fix needs no new geometry and no
new constant — which is what settles the one open question the handoff left
(whether a rest wants its own window, with n=1 to calibrate on: it does not,
because the legacy rule has shipped without one).

Two changes: `_attached_dots` scores `Q.NOTEHEAD_CLASS` **and** `Q.REST` as one
pool, and `_rest_ruling` reads its dots the way the notehead branch does.

⚠️ **THE RECIPROCITY ONLY HOLDS OVER THE WHOLE POOL, which is why the pool had
to widen and not just the read.** A dot is claimed where THIS event is the best
target the dot has. Scored against noteheads alone, a dot printed after a rest
is awarded to some notehead further off. So widening the pool can TAKE a dot
from a notehead — that is the rule working, and it is the cost this benchmark
was built to measure.

## 3. MEASURED — Litolff Beethoven 5, pdf pages 1-3

One gather, adjudicated twice (`rest_dot_arm.py`, `readjudicate`'s harness
imported rather than copied), so the arms carry no detector jitter.

| | |
|---|--:|
| subjects with a duration | 1863 old / 1863 new |
| verdicts that MOVED | **none** |
| dotted rests | 0 → 0 |
| dotted notes | 1 → 1 |

**Nothing moved, in either direction — so the cost in §2 is zero here and so is
the benefit.**

## 4. ⚠️⚠️ THE ZERO IS ABOUT REACH, AND SAYING SO IS THE POINT

A change that moves nothing because it is inert and one that moves nothing
because the page holds nothing to move are **the same number**. This document
holds:

| | |
|---|--:|
| `aug_dot` rows over 3 pages | **20** |
| of those, in a cell that also holds a rest | **8** |
| rest rows | 524 |
| notehead rows | 1339 |

Twenty dots, one of which reaches a notehead at all. Litolff `984073` is
catalogued *"low-res bitonal"* and is the document already recorded as firing
**49 flag boxes and 35 dots** where a Breitkopf scan fires **371 and 656** — so
this is a DETECTION limit, and it is the same limit this thread has already
recorded twice. **A zero on this page is not evidence that the rule is inert.**

The probe therefore prints its REACH before any arm and takes
`--positive-control`, which turns dots off entirely — a change this document
DOES hold ink for — so that "nothing moved" can be told apart from "the
instrument is dead". ⚠️ Without it, this file would be reporting a clean,
believable zero of exactly the kind this repo has a recorded case of.

**The control RAN, and its result is weaker than the word "control" suggests:**

```
POSITIVE CONTROL — with ALL dots off, 1 verdicts move (instrument LIVE)
```

⚠️ **That is the output as this arm ACTUALLY PRINTED IT, kept verbatim.** The
probe was reworded AFTER this run to report its range instead of the bare word
"LIVE" — so a re-run prints a longer line, and the committed artefact is not
stale, it is the record of what was read when the conclusion below was drawn.

⚠️⚠️ **ONE. That is the probe's ENTIRE DYNAMIC RANGE on this document, and it
is the honest headline rather than a footnote.** A control that can move one
verdict rules out a probe comparing a file with itself and **cannot detect a
regression smaller than one verdict** — which is every regression this change
could plausibly cause. So the §3 zero is confirmed to be a real re-adjudication
and is still uninformative about the rule. Reading "instrument LIVE" as a clean
bill of health would be the same mistake as reading the zero as a result, one
step further back; the probe's own output was reworded to say the range rather
than to say "live".

## 5. WHAT IS ESTABLISHED, AND WHAT IS NOT

**Established:** the divergence from `_pair_dots_to_targets` is closed; the
rule is exercised by six unit tests with **five mutation arms red** (revert the
read, revert the pool, rests-only pool, drop the x gate, drop the y window) and
a green control; and on a real scan it costs **nothing** — no notehead loses a
dot.

⚠️ **NOT established: that it GAINS anything.** The handoff's own measurement
is the honest scale — of 848 `aug_dot` rows across three documents, 752 attach
to a notehead and **exactly ONE** to a rest. This is CONSISTENCY, not payoff,
and it should never be quoted as a reading improvement.

⚠️ **NOT established: the cost on a dot-rich document.** The one place widening
the pool could take a dot from a notehead is a page with dots near rests, and
this document has eight such dots and no movement. **Breitkopf Brahms 1 is the
document to re-run this on** (371 flags / 656 dots); it is the same second
publisher this thread already needed for the meter floors.
