# The missed barlines, and the ground truth that was wrong (2026-08-31)

The first end-to-end run reported 13 measures where the page has 16. Fixing it
turned up two causes in the pipeline and one in the measurement.

## First: the truth was wrong

The run was scored against **17** measures. The page has **16**.
`probe_page_measures.py` counts barlines as full-height ink columns on staves
that rest all page — and a **time signature is full-height ink too**, numerator
across the upper two spaces, denominator across the lower two. Its column on
Beethoven 5 p.1 is six pixels wide, which is exactly a barline's width, so a
width filter could not tell them apart either.

All five tacet staves agreed on 17, and that agreement was worthless: all five
print the same time signature, so all five made the same mistake. **Agreement
across staves cannot catch an error every staff shares** — the same trap the
margin-label benchmark hit with its unverifiable "recovered" column.

What does separate them is that a barline is drawn *through* to the next staff
of its bracketed group and a time signature stops at the staff lines. Measured
on this page: every barline 1.00, the time signature 0.05. Either side counts,
because a barline stops at a group boundary — looking only below the Timpani,
which is the bottom of its bracket, found one barline out of seventeen.

## Then: two defects, both assuming barlines are vertical

**The page is warped.** One barline's x drifts monotonically down the staves by
up to 40 px between the top staff and the bottom — over three times the
clustering tolerance. `_intersystem_connectivity` dropped a vertical column at
the cluster's mean x, so by the third gap it was probing beside the line, and
three real barlines scored 0.27–0.36 against a 0.40 gate. They had passed the
vote — 9, 12 and 10 of 12 staves — and died on a geometry assumption.

The fix fits the line to the staves that observed it (`_barline_x_at`) and
probes along it. **Theil-Sen, not least squares**: a note stem near the column
joins the cluster and votes, and two such among nine dragged a least-squares fit
far enough off that a real barline still scored 0.36 with the slope modelled.

| cluster | connectivity before | after |
|---|---|---|
| 2040 | 0.73 | 0.82 |
| 2157 | 0.55 | 0.82 |
| 2227 | 0.36 | **0.36 → 0.82 with Theil-Sen** |
| 2333 | 0.27 | **0.82** |
| 2458 | 0.36 | **0.73** |
| 2600 | 0.91 | 1.00 |

Beethoven 5 p.1: **17 of 17 barlines, 0 false, 16 measures against a truth of
16.** Pages 2–6 unchanged.

**And a braced piano system has no one to vote with.** On a two-staff system the
rule is that both staves must agree, which is right when both can see. On WTC I
Prelude 1 page 4 the left hand reads all four barlines of every system and the
right hand — thick with sixteenths — reads *none* of them and thirty-one of its
own stems instead. Five systems of three bars each came out as **one bar**.

Rescuing those needed a test that a stem cannot pass, and the gap test is not
it: a fugue's long stem crosses the brace gap and scores 1.00 connectivity (WTC
I p.6, x=3018). What no stem does is run from the top of the upper staff to the
bottom of the lower. `_spans_system` takes the weakest band of the column along
the fitted line; measured over four braced systems, every real interior barline
1.00 and every stem 0.52 or below.

| WTC I | before | after |
|---|---|---|
| Prelude p.3 | 4,4,4,3,4,**1** barlines per system | 4,4,4,3,4,**4** |
| Prelude p.4 | **1,1,1,1,1**,4 | **4,4,4,4,4,4** |

The rescue is **additive**: the vote still accepts on its own. Letting the span
test filter instead cost every system its opening rule, which often does not
span the brace because the brace is drawn separately — four barlines per system
down to three. And the hand-verified `TestWTCPage5` ground truth caught the
first version of the rescue inventing a bar; that is the test that made the gap
test's inadequacy visible.

## What it cost

Splitting the fused measures re-cuts the cells, and the detector sees different
crops at different scales, so the page's note reading moved too — and not only
upward:

| | 13 measures (before) | 16 measures (after) |
|---|---|---|
| measures | 13 / 16 | **16 / 16** |
| noteheads emitted | 170 | 159 |
| exact-pitch recall | 0.612 | 0.571 |
| step recall | 0.782 | 0.714 |
| duration recall | 0.374 | 0.361 |
| bar-check failures | 104 | 104 |

Six matched notes lost. Worth saying plainly rather than reporting only the
structural win: the page is now barred correctly, and the per-cell detection is
slightly worse for it. Both are true, and the first is the one that makes the
output a score rather than a bag of notes.

## Reproducing

```bash
python3 benchmarks/omr-first-run-2026-08/probe_page_measures.py
python3 benchmarks/omr-first-run-2026-08/probe_barlines.py
```
