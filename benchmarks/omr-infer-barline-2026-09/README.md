# `collapse_duration_to_barline` — the second INFER rule

The first rule's funnel declined **191 of 357** narrowed durations at one
condition, with a comment saying why:

> No next onset in this bar, so this note runs to the BARLINE and its length
> is the bar's — which is the meter, which this rule may not read.

That is right about the METER and wrong about the NEIGHBOUR. A note's length
is the gap from its onset column to the barline, and we do not have to compute
that gap from the meter to know it: a neighbouring staff that stands at the
same column and also has nothing after it has already measured the same gap
and called it something.

## What is here

| file | what it is |
|---|---|
| `mutate.py` | the mutation battery, with an in-flight sentinel and a verified restore |
| `FINDINGS.md` | the reach on the shared record, once measured |

The rule itself is `tools/omr/staged/inferences.py`; its unit fixture is
`tools/omr/tests/test_infer_barline_rule.py`, which is also the first fixture
either registered rule has ever had.

## The guard that makes it legal

`Q.METER` is absent from the rule's `reads`, and that had to be earned rather
than declared. Two consequences hand a duration out FROM the meter —
`size_measure_rest` and `reconcile_duration` — and both put the meter row in
their `basis`. Borrowing such a length would read the meter by proxy: the
value would be meter-derived while `reads` truthfully said it was not,
`infer.scoring_conflict` would report clean, and `probe/bar_fill.py` would
quietly stop being an independent self-check.

So a witness whose provenance closure contains `Q.METER` is refused, using
`Log.quantities_in_closure` — the primitive `adjudicate.py` already uses for
its circularity filter, not a new mechanism.

## ⚠️ What it does not establish

Accuracy. No inferred note here has been checked against the print. The rule
is bounded, labelled and superseding-visible like every verdict this stage
writes, and on a cleanup count each one is a thing a human might have to take
back out.
