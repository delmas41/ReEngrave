# Pre-fill admission signals — what separates the 8 errors (2026-09-03)

The measured handoff left the pre-fill at **precision 0.84 exact / 0.94 kind**
over 50 boxes on six completely-labeled Brahms cells, and ranked
"confidence-banded admission" as the highest-value next idea: turn the one
number into a precision/coverage curve and admit only from the clean end.
This benchmark asks the question the idea depends on: **which recorded
signals actually separate the 8 errors from the 42 correct boxes?**

`probe_admission.py` recomputes the pre-fill live through `mxl_verdicts`'s
own functions, replicates `score_cell`'s greedy IoU matching per box (the
pooled numbers reproduce the recorded run exactly — 50 / 42 / 47), and prices
each candidate admission policy. Run from the repo root:

```bash
python3 benchmarks/omr-prefill-admission-2026-09/probe_admission.py
```

## The table

| policy | n | coverage | precision exact |
|---|--:|--:|--:|
| P0 admit everything (the recorded figure) | 50 | 1.00 | 0.840 |
| P1 exact-position alignment matches only (`near`=False) | 44 | 0.88 | **0.818** |
| P4 cell `strength_exact` ≥ 0.75 | 43 | 0.86 | 0.814 |
| P5 cell `strength_exact` ≥ 0.9 | 33 | 0.66 | 0.879 |
| S size veto alone (defer small heads to the human) | 47 | 0.94 | 0.872 |
| C parity-consistent cells only | 40 | 0.80 | 0.900 |
| V everything, variant re-derived from the reference | 50 | 1.00 | 0.880 |
| **P7 composite: matched + parity-consistent + not-small + ref-variant** | 37 | 0.74 | **1.000** |

## What the signals turned out to mean

**1. The alignment's own confidence signals are the WRONG axis — one is
anti-correlated.** All six `near` (one-step-off) matches are exact-correct,
so filtering them *lowers* precision (0.840 → 0.818). And cell
`strength_exact` misranks: the cleanest cell in the set (`p3-s5-m5`, 6/6
exact) has the LOWEST `strength_exact` (0.333), while every error sits in
cells at 0.75–0.917. Banding on the aligner's scores — the obvious reading
of "confidence-banded admission" — buys almost nothing here.

**2. Parity consistency is the cell-level signal that works.** For each
cell, ask whether its exact-correct boxes agree on ONE mapping between the
reference note's diatonic parity and the printed on-line/in-space variant.
Five of six cells agree; the one that cannot (`p2-s3-m4`, offsets {0,1}) is
exactly the cell holding all 3 unmatched phantoms and the third flip — 4 of
the 8 errors. A pairing that puts reference notes on the wrong detections
scrambles parity, so inconsistency is a symptom of exactly the failure the
admission gate needs to catch, and it separates the cell that
`strength_exact` cannot (0.75 vs the clean cell's 0.333).

**3. The reference already knows the line/space variant, and the pre-fill
throws that away.** `expected_head_class` keeps the DETECTOR's variant by
design ("position and size the detector read — only the KIND"). But the
alignment key *is* the reference's staff position: whenever the pairing is
right, the reference's variant is the printed one at exactly the same
confidence. Re-deriving the variant from the matched truth note fixes 2 of
the 3 flips outright (`p4-s10-m5` #8/#10, IoU 0.39/0.41 boxes whose class
becomes right even though the box stays where the detector put it), abstains
on the third (its cell is parity-inconsistent), and breaks nothing among the
47 checked. This is a pre-fill code change with measurable value BEFORE any
detector improvement.

**4. The size veto closes the grace ceiling as a deferral.** A box below
0.85× the cell's own median in BOTH dimensions catches both grace heads
(41×38, 44×45 against 51–83 wide neighbours) at the cost of deferring one
correct box. Deferred, not relabelled — the human decides; nothing is
claimed about what a grace note is.

## ⚠️ How to read the 1.000

The composite's 37/37 is **in-sample on n=50, on the same biased six cells
the 0.84 came from, with the policy chosen while looking at the 8 errors.**
It is a demonstration that the errors are separable by signals already in
(or derivable from) the records — a ceiling, not a claim. The out-of-sample
test is a RANDOM completion pass scored with the same probe. What survives
that pass decides what `mxl_verdicts` may admit as labels.

Two of the three error families also confirm the structural claim from the
measured handoff: the flips and phantoms are the DETECTION's placement, so
the whole curve should shift up with the imgsz-2048 re-ship with no pre-fill
change — re-measure with this probe when the new weights land.

## Shipped, same day (Phase A)

The mechanisms above landed in the pre-fill itself (see version_memory.md
2026-09-03): the variant follows the matched reference note on exact pairs,
within-measure tie chains collapse by the reading — a fifth signal, found by
the conflict review, using the same gate tremolo has — every decision now
carries an admission tier (`labels` / `queue` with reasons, a flip demoting
its whole cell), and `--score` prices the tiers. Six-cell A/B: **exact
0.840 → 0.880**, kind unchanged, and the built-in labels tier reads
**22/22 = 1.000 at 0.44 coverage** — stricter than P7 above because at
pre-fill time there is no human-calibrated parity, so any detected flip
demotes its cell. Batch conflicts 5 → 4: `s3-m6`'s tie chain resolved
(both blank-paper hints gone); `s2-m2` stays a conflict because the READING
shows two heads at the position — a duplicate detection the re-ship should
clean up, at which point it resolves itself; the two accidental-glyph
conflicts remain deliberately. The tiers are still metadata: nothing is
auto-admitted until the random completion pass re-prices them out-of-sample.
