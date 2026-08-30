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

## The same join does NOT work for key signatures

The join returns each part's `written_fifths` as well as its clef, and thread 2
of the handoff ended by naming this join as the blocker for the dossier seeding
key signatures. It was measured on the same 42 staves, filling only staves whose
signature nothing read, only where the join is anchored:

    fix 5, break 4

Barely positive, and the breaks are systematic rather than noisy:

| staff | dossier | printed on this page |
|---|---|---|
| C Trumpet | 3 flats | none |
| C, G Timpani | 3 flats | none |
| Bb Clarinet | 1 flat | 1 flat ✓ |
| Oboe | 1 flat | 1 flat ✓ |

The dossier is right about the WORK and wrong about this PRINTING. Whether
natural brass and timpani carry a key signature is an editorial convention that
varies between editions — the Gradus MusicXML gives them one, this
19th-century engraving does not — while the transposing woodwinds, where the
written signature genuinely differs from concert pitch and the reader most needs
help, come out right.

So the join supplies clefs and not key signatures. A clef is a property of the
part; a natural-brass key signature is a property of the edition, and the
dossier is not a dossier of this edition.

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

## The dossier, once its parts can be joined to the page

The dossier records each part's `written_clef`, so it knows the answer to all
three remaining errors. Delivering it took three attempts, and the first two
are worth keeping because they say what the join actually needs.

**Attempt 1 — the existing gate.** `--dossier` changes nothing here (beet5-p2
21/22, pastoral-p2 17/20, with and without), because slot-level facts require
part count == staff count and a printed score condenses: 18 parts reach a page
as 11 staves.

**Attempt 2 — align on clefs and position.** Reusing the monotone aligner with
the work's parts: 32/42 staves joined correctly, and adding a condensation move
(several parts on one staff) took it to 35/42 — but filling defaults from it
would fix 0 and break 1. The reason is circular: the evidence for deciding
which parts condense was position and **the clefs already read**, which is what
is wrong on the staves that matter.

**Attempt 3 — align on the margin LABELS, never the clefs.** This is the join
(`dossier.join_parts_to_slots`). Three things make it work:

- **Labels as the evidence.** Independent of the clefs it exists to supply, so
  it cannot be circular. Labels are read per staff and joined through *slots*,
  so a name read in one system reaches every system of the page.
- **Condensation priced by instrument.** A merge of two parts with the same
  name (Flauti 1 and 2) is cheap; joining different instruments — the
  "Violoncello e Basso" case — is dearer but allowed. With one price for both,
  the aligner drops the second violin rather than condensing cello with bass,
  and the whole string section slips by one: 17/42 against 28/42.
- **Trust only between anchors.** A slot with a labelled slot above *and* below
  is pinned on both sides and cannot slip. Past the last label the join is
  guessing — and measurably so: on these two pages it is right on **7 of 7 wind
  staves, including an unlabelled bassoon**, and wrong on the string section,
  which carries no labels at all.

Anchored, the join may do what nothing else in this module does: **overrule a
clef that was read**. That licence comes from what a dossier is — not another
reader with an opinion, but the score. It is confined to anchored slots
precisely because the licence is dangerous: unanchored, the same join walks into
the strings and gets three staves wrong.

Measured: **49/52 → 50/52 (96%)**. One clef applied, on Beethoven 5 p.2's
bassoon, which the detector had read as treble. Nothing else moved. What the
reader said is kept on the staff as `clef_overridden_by_dossier`, so seeding can
never hide how well the page was read.

## What is left

Two staves, and they are the same staff: the Pastoral viola, alto in both
systems, read treble in one and defaulted treble in the other. Nothing on the
page says otherwise — the score-order prior calls it a violin for the same
reason — and the dossier knows it is a viola but cannot be trusted there,
because that page carries only two labels and both sit above the strings.

> ⚠️ **The "more labels" lever is CLOSED — measured 2026-08-30.** The vision
> reader was run on this page and scored 5 of 5 on the labels that are printed,
> correctly returning nothing for staves 5-9, which carry none. The margin crop is
> committed as evidence. This edition labels winds and horns on every page and
> never a string, so no better reader can obtain a label below the strings at any
> price. What the evidence points at instead is the foot of the system as an
> implicit anchor, since every tradition in `score_layouts.py` ends the same way.
> `benchmarks/omr-margin-labels-2026-08/VISION_CEILING_2026-08-30.md`.

The lever for it is more labels, not a better join: `staff_labels` reads what
the text layer offers, and `contextual`'s `vision_fallback=True` reads the
margin with Claude for about a cent per system. One more label anywhere below
the strings would anchor the whole section.
