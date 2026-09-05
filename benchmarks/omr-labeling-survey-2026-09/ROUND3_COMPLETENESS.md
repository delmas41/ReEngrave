# Round 3 — completing the cells, and the diagnosis that was wrong

**Date:** 2026-09-03 · **Status:** labeling complete, cloud re-run not yet spent.

Follows `CLOUD_2048_RESULTS.md` (the 30-epoch imgsz-2048 run: a real half-note
gain, with a completeness regression that made it unshippable) and
`NEXT_ITERATION.md` (the ordered plan out).

## The plan's diagnosis was a minority of the problem

`NEXT_ITERATION.md` named the gap precisely: the completion pass had boxed only
black noteheads and augmentation dots, so **rests and accidentals** were
unlabeled background, and 30 epochs learned to suppress them. That is true. It
is also not most of it.

Measured before doing any labeling — production detector over the 198 cells that
actually emit a YOLO label, every detection bucketed by whether ANY pass had
ever covered its class:

| bucket | detections |
|---|--:|
| **NEVER BOXED** | **377** |
| boxed: noteheads | 334 |
| skip: classical CV (stem/beam/staff) | 109 |
| boxed: accidentals | 50 |
| boxed: aug dots | 23 |
| boxed: rests | 23 |

**41.2% of detected ink, across 142 of 198 cells.** And the composition is not
what the plan assumed:

    dynamics 165 · slurs 99 · ties 26 · clefs 29 · articulations 19
    ledger lines 12 · timeSig 8 · flags 7 · fermata 5

**Dynamics + slurs (264) are 3.6x the rests+accidentals gap (73).** Labeling only
what the plan named and re-running the cloud job would have spent the GPU and
hit a variant of the same wall.

⚠️ Detector output is not truth, so this was spot-checked before being acted on:
eight crops per class, eyeballed. **dynamicP 8/8 real, dynamicF 8/8 real, slur
8/8 real**; ties ~60%, clefG ~60% (three boxes on noteheads). The two dominant
families are solid, so the ordering survives a generous FP discount.

## The work was split by which labeler is good at which family

Not one method for everything — the two families fail differently and the
round-2 audit had already measured that.

| family | labeler | why |
|---|---|---|
| rests, accidentals | HUMAN | round-2 audit found the model FP-prone exactly here (restWhole on slur arcs, accidentalDoubleSharp on trills) |
| dynamics, slurs, ties | MODEL, audited | spot-checked 8/8 clean; the same method that produced the black noteheads in v8-v12 |
| clefs | HUMAN, 24 cells | model ~60% precise, and only 24 cells contain one |
| ledger lines, flags, time sigs | left | small, and partly classical-CV territory |

**Campaign total: 760 human boxes over 493 cells** — 411 hollow from earlier
rounds, **296 rests/accidentals** and **25 clefs** this round, plus 28
slurs/ties/hairpins another session drew on Brahms. Three cells unswept.

Every batch was audited by crop-and-eyeball plus geometric probes. **Zero label
errors found.** The probes flagged five boxes across three batches and all five
were the PROBE being wrong, not the label:

- Litolff: four half/whole rests "misplaced" — orchestral parts displace rests
  for voicing, so a half rest legitimately sits on the bottom line.
- Mahler 5: two key-signature boxes away from the staff head — a mid-movement
  KEY CHANGE, printed after a barline.
- Scheherazade: two whole rests below the bottom line — DIVISI, the lower
  voice's whole-bar rest written under the staff.

That is why none of them is committed as a test. They encode textbook
single-voice placement and orchestral engraving does not oblige.

## Two general lessons this round paid for

**1. Measure the unboxed ink BEFORE a long fine-tune.** The check is cheap — run
the detector over the training cells, bucket by class — and it is the only thing
that catches an under-scoped completion before the GPU spend. This is the third
time the "detected, then dropped" shape has bitten this project.

**2. Degradation has TWO directions and a naive probe sees one.** Asked whether
a batch was a bad scan, the first three proxies — ink density, fragmentation,
staff-line continuity — all said mid-pack. They only detect decay by BREAKING.
This corpus decays by BLOOMING: ink spreads until staff lines fatten and
counters close, and **a bloomed staff line is perfectly CONTINUOUS, so it scores
WELL on a continuity metric while being unreadable.** Every batch here is
bloomed (lines at 0.20-0.27 of a staff space against a clean 0.08-0.12). Any
future scan-quality probe needs both directions.

What actually separated the batches was the SWING, not the quality: per-cell
music ink runs CoV 0.67 on Litolff (7% near-empty cells) to 2.51 on Mahler 1
(84%). That observation is what surfaced the next item.

## Sweeping cells that cannot become training data

A cell only becomes training data if it carries a box — the converter's
`_is_filled` is false for an inspected-empty cell, so it emits no label and is
not used as background either. Sweeping the near-empty majority buys a coverage
record nothing reads.

Pooling only the box-carrying cells took the remaining sweep from **328 cells to
152**, with identical training signal. `omr-labeling-marks-focus-2026-09` and
`omr-labeling-clefs-2026-09` are built that way, with `origin.json` recording
each cell's home batch and `merge_focus_back.py` writing the verdicts back
additively.

## A config is not a coverage record

Brahms 1 was left to the session holding it, on the reasonable assumption that
its "completion" palette — which lists rests and accidentals — covered the same
ground. Checked against its VERDICTS rather than its config: 55 cells stamped
`hollow noteheads`, **zero stamped for any completion pass**. Eleven Brahms
cells are in v8, so they would have entered the retrained mix with rests and
accidentals as background — the exact bug this round exists to close,
reintroduced through the one batch nobody swept. Swept here as an 11-cell focus
batch.

**What a pass covered is in `inspected_passes`. A palette listing a class only
means someone COULD have boxed it.**

## Closing measurement — 68.1% → 23.5%

`residual_background.py`, one fixed detector over the same 280 cells, asking per
BOX whether each detection is covered by anything in the merged verdict:

| stage | uncovered detections |
|---|--:|
| before round 3 (`--before`) | 923 / 1355 = **68.1%** |
| + human rests, accidentals, clefs + model dynamics/slurs/ties | 486 = **35.9%** |
| + audited black-notehead top-up | **319 = 23.5%** |

Black noteheads fell **200 → 22** uncovered, which is what the top-up was for.

**The residue, and what is honest to say about it.** What remains is slurs 75,
clefs 29, ties 27, dynamics 17, timeSig 11, flags 10.

⚠️ **This is an UPPER BOUND, not a defect count.** Detector output is not truth
in either direction, and some uncovered detections are false positives that
SHOULD train as background — clefG measured ~60% precision in the spot check,
so a good share of those 29 are ink that is not a clef, and the round's own
`sempre`-as-dynamic family is the worked example of a detection that must stay
unlabelled. The number is meaningful as a before/after delta on one detector,
never as an absolute.

The slur/tie residue is partly deliberate: `complete_marks.py` sets per-family
confidence floors FROM the spot check (slur 0.60, tie 0.75), so lower-confidence
real arcs are left rather than admitted at a precision the audit did not
support. Whether that trade is right is a question for the next round's
measurement, not a thing to guess at now.

## What is NOT done

- The cloud re-run has not been spent. Gate on BOTH axes — beet5-p1 hollow (note
  recall, where p29 won) and the widened scan-e2e (full-symbol OMR-NED, where
  p29 lost). They disagreed last time; the narrow one alone would have shipped a
  regression.
- Three drafted non-German scan-e2e rows await a human confirming their windows
  (`works-draft-nongerman.json`).
- ⚠️ **The benchmark cannot validate the traditions the training covers.**
  Universal, Novello and Durand are in the training set and have no reference
  encoding in the library, so no row can test them. This belongs beside any
  quoted gate result.
