# What clef does the pipeline finally assign? — 2026-08-29

Three separate threads of `docs/next-steps-omr-2026-08-28.md` ended by pointing
at clef reading: the key signature is fitted against a slot table the clef
chooses, the score-order prior takes clefs as its strongest evidence, and the
July domain-gap conclusion rested partly on "mostly-treble clefs". None of them
could say how accurate clefs actually are, because the existing clef benchmarks
measure the *parts* — `eval_orchestral_clefs.py` scores the CV locator's
precision, `probe_clef_rejection.py` scores window coverage — and not the clef
a staff ends up carrying.

`eval_pipeline_clefs.py` measures that, against the hand-read clefs already in
`benchmarks/omr-key-signature/ground_truth.json`.

```bash
python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py            # detection only
python3 benchmarks/omr-clef-geometry/eval_pipeline_clefs.py --contextual
```

## The baseline is much better than the project's own record of it

52 staves across three pages (Beethoven 5 p.2, Pastoral p.2, WTC p.17):

| source | staves | correct | accuracy |
|---|---:|---:|---:|
| detector | 39 | 37 | **95%** |
| positional default | 11 | 9 | 82% |
| CV locator | 2 | 2 | 100% |
| **overall** | **52** | **48** | **92%** |

That is not the picture the documentation carries — "clef coverage ~23% on
19th-century prints", "on scans where every staff reads as treble". Those
numbers were measured before the `imgsz` fix, which is the same correction that
took Boléro p.1 from 13 clefs to 24 of 24
(`benchmarks/omr-detection-probe-2026-08/findings.md`). **Clef DETECTION is no
longer the wall it is written up as.** What remains is narrower and one-directional:

    every error is a non-treble clef read as treble
    bass -> treble x2, alto -> treble x2

## A part keeps its clef between systems

Three of the four errors are staves whose own part reads *correctly in the other
system of the same page*. So the fix needs no new evidence, only the knowledge
of which staves are the same part — which `slots.py` established.

`contextual._fill_defaulted_clefs` gives a staff that read **no** clef the clef
its part read elsewhere, when every reading of that part agrees. Result: 48/52
→ **49/52 (94%)**, one staff fixed (the Pastoral bassoon, defaulted to treble in
system 0 and read as bass in system 1), none broken.

**This is not the cross-system clef vote that was tried and dropped in 2026-07**
(`docs/internal-consistency-checks.md`). That one majority-voted each role's
*final* clef across same-sized systems and failed two ways: same-sized systems
are not the same instruments on a condensed score, and the majority reading can
be the wrong one, so it flagged correct staves. Both objections are answered
structurally rather than argued with — the parts come from slot **alignment**
rather than equal staff counts, and **nothing that was read is ever overruled**;
only a silence is filled, and only on unanimity. `TestSlotClefContinuity` holds
that line with the two failure cases as tests.

## Measured and rejected: letting the score-order prior correct clefs

`clef_correction.propose_clef` proposes a clef from the instrument's own
convention, vetoed by the staff's register, and only where nothing read a clef —
exactly the right shape for these errors. It fires zero times on these pages,
because the staves in question have no label and so no identity.

The score-order prior (shipped 2026-08-28) supplies identity without labels, and
on Pastoral p.2 it correctly names the unlabelled bassoon. Letting it through to
clef correction was tried:

| | overall | errors |
|---|---|---|
| gate in place | 48/52 | bass→treble ×2, alto→treble ×2 |
| gate lifted | 48/52 | bass→treble ×1, alto→treble ×2, **treble→bass ×1** |

It fixes the bassoon and **breaks a correct treble staff**, trading a right
default for a wrong correction at no net gain. The register veto inside
`propose_clef` did not catch it. The gate stays: identity deduced from position
still does not drive clef correction.

## What is left

Three errors, all non-treble read as treble, and only one kind now:

- **Pastoral p.2 viola** — alto in both systems, read treble in one and
  defaulted treble in the other, so there is nothing on the page to borrow from
  and no label to name it. The score-order prior gets this staff wrong too (it
  says Violin), for the same reason: every piece of evidence available says
  treble.
- **Beethoven 5 p.2 bassoon, system 1** — read bass in system 0 and *detected*
  as treble in system 1. Filling silences cannot help; this needs a reading to
  be overruled, which is the thing this layer deliberately will not do.

Both are cases where the page itself does not carry the answer in any form the
pipeline can already see.

## Measured and rejected: the dossier as a clef source on these pages

The dossier records each part's `written_clef`, so it knows the answer to all
three. It cannot deliver it. `--dossier` changes nothing here (beet5-p2 21/22
and pastoral-p2 17/20 with and without), because slot-level facts are gated on
the part count matching the staff count — and a printed score condenses, 18
parts reaching a page as 11 staves.

Joining them by ALIGNMENT instead was tried, reusing the monotone aligner from
`score_layouts` with the work's own parts and clefs:

| join | aligned clefs correct | filling defaults would |
|---|---|---|
| alignment, gaps + continuation | 32 / 42 | fix 0, break 1 |
| ...plus a condensation move (several parts on one staff) | 35 / 42 | fix 0, break 1 |

The condensation move is what a printed score actually does, and adding it
helped in aggregate — but it made Beethoven 5's first system *worse* (11/11 →
9/11) and neither version gets the staves that matter right. The reason is
circular in a way no tuning fixes: the only evidence available for deciding
which parts condense onto which staff is position and **the clefs already
read** — which is precisely what is wrong on those staves. The dossier knows
the clef but cannot be told which staff to put it on.

That experiment was reverted rather than left in place: unused machinery that
looks endorsed is worse than none. Making the dossier usable here needs a join
with independent evidence — the margin instrument names are the obvious one,
and `staff_labels` already reads them where there is a text layer.
