# The staged exporter reads nine quantities, and `dynamic` was not one of them

2026-09-09. `adjudicate_dynamic` stopped being a stub on 2026-09-09, decides,
and files a verdict per cell. `grep '<dynamics' tools/omr/staged/export.py`
returned **zero** — as did the same grep for `<direction>`, `<wedge>`,
`<slur>`, `<tied>`, `<articulations>`, `<fermata>`, `<ornaments>` and
`<notations>`, all nine.

*The value existed and nothing read it* — this project's highest-yield
pattern, occurring **inside the architecture built to stop it**.

## What changed

`_place_directions` mirrors `_place_notes`: a pass over the record that files
each decided dynamic word onto its cell, rendered through the LEGACY
`_mxl_direction` and `_mxl_empty_measure`, both of which already take exactly
`(x, kind, text)`. No new renderer.

## Measured — one gather, exported twice

Beethoven 5 / Litolff `984073`, `--pages 2` (the two-system page; 11 staves,
22 measure-partitions). `reexport_arm.py` re-exports the SAME saved record
under each arm, so **no detector jitter enters**.

| | BEFORE (HEAD) | AFTER |
|---|--:|--:|
| `<dynamics>` in the file | **0** | **80** |
| notes | 589 | 589 |
| rests | 228 | 228 |
| balance | balanced | balanced |

⚠️ **Strictly additive, checked rather than claimed**: with the `<direction>`
markup lines removed the two files are **byte-identical** (`md5`
`491fd69d…` both arms, zero `diff` lines). music21 parses the result and
reads back **80 Dynamic objects across 11 parts**.

## ⚠️⚠️ The A/B found a second defect: `decided_but_unwritten` was UNREACHABLE

The BEFORE arm wrote zero `<dynamics>` and still reported
`decided_but_unwritten: []`. The branch order was

```
elif decided:                 -> "decided"
elif written is not None:     -> "decided_but_unwritten" if decided else ...
```

so the third branch consumed every decided family and the fourth could only
ever see `decided == 0`. **The guard sat on a dead branch.** A decision that
decided and reached no file was reported as `decided`, which reads like
success. *A check that cannot fail is worse than no check* — `health.py`
learned the same lesson from a clause that emptied its own EMPTY CELLS list
in one line.

⚠️ It was found by the controlled A/B, **not by review**, and not by the 466
tests that were green over it.

## ⚠️ Two headlines now, because they are two faults

`detected_and_unrepresented` is a **RECORD** gap — no quantity, a stub, or a
stub whose input is not gathered. `decided_and_unwritten` is an **EXPORT**
gap — the decision decided and no file received it. The repairs differ:
*write an adjudicator* against *read the verdict you already have*.

⚠️ Keeping them apart is why the first headline **fell by ~284 glyphs on
beet5-p3 the day `dynamic` stopped being a stub, with nothing reaching a
file** — a family changed BUCKET and the number improved. Quote both.

## ⚠️ A third defect: the hairpins were counted twice

`dynamicCrescendoHairpin` starts with `dynamic`, so a plain prefix test let
the `dynamic` family AND the `wedge` family both claim it, and where both
were unrepresented the headline charged the same ink twice.
`gather_glyph_families` is routed by CLASS *"never by the detector's
`category`"* for exactly this glyph — the coverage table carried the fault
that finding exists to prevent, one module over. `_claims` is now
longest-prefix-wins, derived, so a future overlapping family resolves without
a hand-written exclusion.

## ⚠️ `<part-group>` was scoped and NOT built — zero reach, measured

`adjudicate_group_symbol` **abstains `no_identity` on both systems** of this
page, because `instrument` abstains `no_evidence` on **22 of 22 staves** —
the documented scan behaviour, and its own docstring says the consumer should
fall back to the incumbent rule. `staff_group` does decide (blocks of 8/6/8),
so the GROUPING is known and only the SYMBOL is not; asserting `bracket`
without identity would be the positional default this pipeline refuses
everywhere else. **Measure REACH before accuracy**: building it would ship a
renderer testable only synthetically.

## Placement — a declared simplification

Marks go at the HEAD of the bar. The legacy events path places a dynamic
against its NEAREST NOTE (`_direction_slots`); this path cannot, because the
marks carry a **page** x and the noteheads a **canonical** one, and comparing
the two is precisely the frame error that made `Q.ONSET_COLUMN` report 1,062
columns of nothing. A `<direction>` carries no duration and is legal at
offset 0. ⚠️ Placement is also exactly what stops a correctly recovered `sf`
from PAIRING with a truth, so a flat metric here would not mean this is free.

## Refusal inherited, not re-litigated

A narrowed (unspellable) verdict writes nothing. That is
`OMR_PARTIAL_DYNAMICS`, built, measured over the 20-row scan gate and
REFUSED: `complete` +15 edits with **not one row better**, `other` +30.

## Tests

13 new in `test_staged_export.py`. Three mutation arms run RED against the
intended tests (drop the events-branch emission → 3 red; pass `None` to
`_mxl_empty_measure` → 1 red; `_claims` back to a plain prefix → 2 red).
⚠️ The `decided_uncounted` test's first draft asserted it of `slur` and failed
`stub != decided_uncounted` — a stub is reported as a stub before any of this
— so it now exercises the branch by removing `dynamic`'s counter, which is
that family's shipped state until this session.
