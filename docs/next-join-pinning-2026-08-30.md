# Next: pin the labelled slots in the part-to-staff join

Written 2026-08-30, after the join was measured directly for the first time.
**Read `benchmarks/omr-part-staff-join-2026-08/RESULTS.md` before starting.**

---

## The prompt

> The dossier's part-to-staff join (`tools/omr/dossier.py:join_parts_to_slots`,
> which calls `tools/omr/score_layouts.py:align_to_layout`) has one structural
> failure that no amount of labelling fixes: **the work's part list and the
> printed page can disagree about order, and the alignment is monotone.**
>
> Measured on Beethoven 5 p.48 (`benchmarks/omr-part-staff-join-2026-08/`): the
> page prints `Timp.` at slot 8 and the three trombones at 9-11, while the
> MusicXML part list has Alto/Tenor/Bass Trombone at indices 14-16 and Timpani at
> 17. Having consumed Timpani, a monotone alignment cannot go back, so slots 9-11
> return `None`. It costs exactly the alto, tenor and bass clefs the dossier
> exists to supply. **Perfect labels give 13/17; the realistic labels this edition
> prints give 12/17.**
>
> **Hypothesis to test: a labelled slot should PIN its part.** The margin labels
> know the PRINT's order, which is the thing the part list does not. Pin each slot
> whose label resolves unambiguously to exactly one part, then run the existing
> monotone alignment independently on each span BETWEEN consecutive pins. That
> permits the transposition a single monotone pass forbids, while keeping the
> aligner's merge/extend/gap machinery inside each span.
>
> **Measure it first, and only ship it if it wins.** The harness already exists:
>
>     python3 benchmarks/omr-part-staff-join-2026-08/eval_join.py
>
> Current numbers, which are the bar:
>
>     page                  no labels   perfect   as printed
>     beet5-p2  (18->11)       10/11      11/11      10/11
>     pastoral-p2 (15->10)      3/10       9/10       9/10
>     beet5-p48 (23->17)        8/17      13/17      12/17
>
> A win means beet5-p48's "as printed" column rises materially (the three
> trombone slots are the target) with **no regression on the other two pages**.
>
> These must also be unchanged, and each is a real guard rather than a formality:
>
>     python3 -m pytest tools/omr/tests -q                      # 1043 passed
>     PYTHONPATH=. python3 benchmarks/omr-score-order/eval_score_order.py
>         # position 11/12, read clefs 5/10, true clefs 23/23 — this path aligns
>         # against STANDARD LAYOUTS with allow_merge=False, and pinning must not
>         # reach it, because there the labels are what is being predicted
>     python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py --contextual --dossier
>         # 50/52, and the per-source breakdown must not change either
>
> Add tests that FAIL without the change — the existing precedence tests in this
> repo passed under both rules for a while because their fake detector never
> exercised the branch, and that is a trap worth not repeating.

---

## What to be careful about

**Do not pin on an ambiguous label.** `instruments.AMBIGUOUS_ALIASES` exists
precisely because `Tp.` is timpani or trumpet and `Basso` is the contrabass or a
bass voice, resolved by score position rather than by the alias table. A pin is a
hard constraint, so it must only be taken where the label resolves to exactly one
part of this work. Where a work has several parts of one instrument — "Violin 1"
and "Violin 2" both canonicalise to `Violin` — a bare label like `Viol.` does not
identify which, and pinning it would be a guess wearing a constraint's clothes.

**Do not pin on clefs.** The join deliberately never scores on clefs, because
supplying clefs is what it is for and doing so would be circular exactly where it
matters. That constraint still holds; see the docstring of `join_parts_to_slots`
and the three attempts recorded in
`benchmarks/omr-clef-geometry/PIPELINE_CLEF_RESULTS.md`.

**Pinning interacts with `anchored`.** Today `anchored` marks slots lying between
the first and last labelled slot, and only anchored facts are trusted. If pinning
lands, reconsider what anchoring should mean — a span between two pins is
constrained on both sides in a stronger sense than today's definition, and the
foot-of-system anchor was already measured and **disproven** (50/52 → 44/52,
`benchmarks/omr-margin-labels-2026-08/`), so do not reintroduce it by accident.

**Expect the merge budget to still be open afterwards.** It is a separate, real
problem and it is second in the ranking, not first: *this page needs k merges and
the work offers j conventional ones* is a global constraint that a locally-scoring
DP cannot express. Naming the cello-and-bass condensation as a cheap pair was
measured and lost (Pastoral 9/10 → 7/10) because a cheap cross-instrument merge
lets the aligner condense whenever it is short of staves rather than only where
the engraving does.

## If it does not win

Say so and write it up, with the numbers, next to the RESULTS file. Four proposals
were built, measured and rejected in the two days before this one — the
foot-of-system anchor, the accidental-role override, majority-steered
re-segmentation and "confirm the empty signature first" — and each write-up is
worth more than the change would have been, because it stops the next attempt
repeating it.
