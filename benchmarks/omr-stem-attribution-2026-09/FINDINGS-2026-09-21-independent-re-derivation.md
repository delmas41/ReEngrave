# The end rule, refused a SECOND time — independently, and by a different route

**2026-09-21.** ⚠️⚠️ **READ [`FINDINGS.md`](FINDINGS.md) FIRST. THIS LANE
DUPLICATED IT AND DID NOT KNOW.** That file is dated **2026-09-20**, it was
**already in this directory** when this lane was dispatched, and it had already
withdrawn the same rule after Sean read the crops. This file is the
**independent re-derivation**, kept for the one thing a duplicate is good for:
it reaches the same refusal by a route the first pass never used.

**No code changed.** `git diff 28749347..13c9ca08 -- tools/` is empty. The
deliverable is 15 probes, 20 tests, an 11-arm battery (11 RED), two
adjudication files, 31 JSON artefacts and 136 crops.

## 0. Why this exists, and whose fault it is

The 2026-09-18 handoff ranks *"a stroke belongs to the head at ONE OF ITS
ENDS"* as next work #1. A session on **09-20** did that work and **withdrew
it**. The 09-21 dispatch was written from the 09-18 handoff without checking
this directory, so the lane was briefed to build something its own benchmark
folder already refuted.

⚠️ **The prescribed check would not have caught it.** The brief said to run
`git log --all --oneline -S "_stems_on" -- tools/`. The 09-20 work **changed no
`tools/` file** — because it was withdrawn — so an `-S` search over `tools/`
returns nothing. **A withdrawn investigation is invisible to a code search by
construction.** The check that would have worked is `ls` on the benchmark
directory named after the thing.

> **Before dispatching work named in a handoff, read the benchmark directory
> named after it — not just the code. The most relevant prior art is the work
> that concluded "do not build this", and that work leaves no trace in `tools/`.**

## 1. The refutation, structurally — verifiable in six lines, no records needed

`adjudicate_stem_direction`:

```python
mine = _stems_on(head_box, stems)
if not mine:
    borrowed = _direction_from_a_beam_mate(ev, cell, head_box, stems)
```

The beam-mate tier is reached **only when `_stems_on` returns EMPTY**. The
26-head standoff is built from heads that tier answered, so **every head in it
has an empty stem set by construction.** An end constraint makes `_stems_on`
strictly narrower, and narrowing an empty set leaves it empty.

**All 44 heads the print has EVER adjudicated on this thread** — the crop
pass's 26-head standoff and the stroke lane's 18 crops, including its 6-of-6
DISAGREE stratum — **have no overlapping stem in either shared record, and the
record's own verdict for all 44 is `no_stem`.** The proposed rule only ever
*removes* an attribution. **It cannot reach one of them.**

⚠️ So the 09-18 handoff's *"two lanes, two instruments, one conclusion"*
merges two populations, **neither of which the repair it proposes can touch.**
Control: 39 of 44 sit in cells that do carry strokes, 38 where another head
takes one — they are stemless by how each was *sampled*, not by accident.

## 2. The natural statistic is an artifact

Position along the stroke as a **fraction** of its length scores a head at the
end of a *short* stroke as "mid-stroke" by arithmetic. On 24 crops selected
that way, every MID pair had a stroke of 1.39-2.20 head-heights and every END
pair 2.42-4.63 — **all 24 were at an end.** The scale-free measure is distance
to the nearer end **in head-heights**.

On it: beyond 0.8 head-heights, **15 of 969 (Litolff) and 9 of 1,256
(Breitkopf)** solo pairs. p99 = 0.93 / 0.70. **No empty interval and no
plateau**, so any cut would be fitted to the sample — none is proposed.
Chord strokes behave completely differently (241/792 and 264/646).

## 3. The safety argument is false

The rule's structural safety claim was that a **one-head stroke cannot be a
chord**, so the documented double-stop regression is out of reach. It is not:
**7.5% / 7.8% of solo pairs have a chord partner the overlap test missed**
(`glyph/3/1/10/2/16` has two partners at −2.05 head-heights). ⚠️ This is the
same shape as §0(a) of the 09-20 file, where a chord test that required a
companion **above *and* below** could not see an octave pair — reached here
from the opposite direction.

## 4. The print, on the population the rule CAN reach

A census, not a sample: all 8 Breitkopf far-from-end pairs plus 8 at-an-end
controls. Frame control 0/16; canonical→page affine residual **0.000 px over
3,337 heads**. **Controls 8/8 correct. FAR: 2 settled, 6 `cannot_tell` — right
once, wrong once.**

## 5. ⚠️⚠️ The lane inverted its own interim conclusion

It first reported the fault as 10× commoner in `OMR_STEM_STROKE`'s strokes and
called the repair a prerequisite for that flag. A sensitivity check — triggered
by the print catching its probe missing a **visible** dyad by 19.5 px — shows
that population is **93% chords** at a 2-head-height tolerance. The shipped
share is **flat** across tolerances (4 of 5, 8 of 9 have no partner at any);
the profile share climbs 22% → 71% → 93%.

**So the defect in that reader runs the OPPOSITE sign: a chord's members are
not all joined to their shared stroke. `_stems_on` is too NARROW there, not too
wide.** ⚠️ That agrees with the 09-20 file's own conclusion from a third
direction — its residual was *"clean notes with basic stems"* and its real
finding was **two stems fused into one component**.

## 6. ⚠️⚠️ NEW, AND REPO-WIDE: the shared records can no longer license a rebuild

A `readjudicate`-style **CONTROL 1** (rebuild the record's own verdicts and
require them to reproduce) **FAILS on today's tree — 2,760 of 2,993
durations.** Not a harness fault: this lane's `rebuild()` is **AST-identical**
to the canonical one (now pinned by a test). **Seven commits have touched
`rhythm.py` since the record's tree `9d4ccc85`** — verified at integration, and
one of them is literally *"meter: an uncorroborated change is not carried off
its system, and both flags default ON"*.

> **Any future A/B on `library/_shared-records/` must be base-vs-arm on ONE
> tree. The record's own committed verdicts are no longer a baseline.**

⚠️ **CONTROL 2 passed** and independently reproduced the 09-18 handoff's own
figure: **152 verdicts move, all `no_stem → decided`** — exactly the beam-mate
tier's stated reach.

## 7. What is NOT established

One adjudicator, who also wrote the crop tool; no inter-rater figure. **The
adjudicator got 2 of 24 tiles wrong at sheet magnification** — a measured error
rate, on the easier plate. The print settles only 2 of 8; **Litolff's 15 were
never cropped**; the profile reader's 124 tiles were rendered and **not
adjudicated**. No effect on any file — `<voice>`/`<backup>` were not measured,
because with no rule there is nothing to measure. No OMR-NED, deliberately.
n = 2 documents, 2 publishers. The shadow curve says a *partner exists*, not
that the pair is a chord; only `G86` was confirmed by eye.

## 8. Ranked next work

1. **Join a chord to its stroke** — reach 115 of 124 profile pairs, 98 / 73
   shipped. Same line, *widened* rather than narrowed.
2. Adjudicate the 9 shadow-free profile pairs against the print.
3. The fused two-stem run — already under way in
   `benchmarks/omr-stem-run-split-2026-09`, which is where the 09-20 file
   points.
