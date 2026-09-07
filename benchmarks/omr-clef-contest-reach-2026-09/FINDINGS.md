# Does `clef_evidence["contest"]` have a population to act on?

**2026-09-07 · reach gate · transcribed by the coordinator (the harness blocked the
agent from writing a report file). Probe, cross-check and `reach.json` are committed
beside this and carry the raw data.**

## The verdict

**The gate CLEARS, narrowly — and the recommendation should still NOT be built as
written, because the consumer already exists.** Over the 20-row scan gate (**396
staves, 20 pages, 5 distinct documents**): every staff records a contest, but the
population whose resolution could differ is **22 staves** where the argmax overturns
a clef a reader had already established. **15** of those have an instrument
`clef_correction` will admit; **14** satisfy the pre-registered
`instrument_source == "label"` gate, over **3 distinct documents**. Against the fill
tier's **5 proposals / 0 applied**, that is not a null.

⚠️ **The trap named in the work order was not hypothetical — it inverts the verdict.**
All **22 of 22** overturns carry `n_resolved == 1` and **not one carries a
`disagrees` key.** A probe counting `disagrees` reports **zero reach** and kills the
recommendation on a field that is absent by construction exactly where the answer is.

## ⚠️ The consumer this proposes already exists, and is disabled

`veto_implausible_clef_changes` (`clef_correction.py:516`) already walks each staff's
measures, catches a mid-staff clef change, **reasons with the instrument in hand**,
and restates the affected measures — behind the same provenance gate, and behind
**`OMR_INSTRUMENT_CLEF_DEFAULT`, which is off.**

Of the 15 reachable overturns: **3 would be handled today by flipping that flag**;
**12 would not** — and they are blocked not by missing evidence but by
`MID_STAFF_CHANGE_VETOES`, **a hand-listed table of two triples**
(`Violin treble→bass`, `Viola alto→bass`).

**So the work is not "give the record a consumer". It is "the consumer exists, is
disabled, and its coverage table is two rows long."** Different task, far cheaper,
much smaller blast radius.

## ⚠️ Reach is an UPPER BOUND on defects — half the residual is correct music

No page was hand-read. All **twelve** uncovered residuals are listed below (the three
Cello rows are collapsed into one line). Several are ordinary engraving a consumer must
**not** undo — the function's own docstring says *"cello changes (tenor/treble) are
real and never touched"* and *"Viola→treble is deliberately NOT vetoed."*

| | flip | conf | prima facie |
|---|---|--:|---|
| brahms-p1 s12 · brahms-p3 s26 · brahms-p4 s26 | Cello `tenor→bass` | 0.819 / 0.374 / 0.333 | **ordinary** |
| brahms-p4 s17 | Bassoon `tenor→bass` | 0.483 | **ordinary** |
| mahler-p3 s6 | Trombone `bass→tenor` | 0.604 | **ordinary** |
| mahler-p4 s16 | Viola `alto→treble` | 0.582 | **ordinary** |
| brahms-p4 s11 | Viola `alto→tenor` | 0.435 | unusual |
| beethoven-984073-p1 s11 | Contrabass `bass→treble` | 0.664 | implausible |
| beethoven-984073-p4 s11 | Flute `treble→bass` | 0.501 | implausible |
| brahms-p2 s2 | Clarinet `treble→bass` | 0.346 | implausible |
| mahler-p3 s10 | Violin `treble→tenor` | 0.547 | implausible |
| mahler-p4 s10 | Timpani `bass→treble` | 0.259 | implausible |

**The actionable residual is nearer 5–6 than 12.** Same shape as the Simrock
ledger-zone audit, where a 6.9% raw flag rate adjudicated to ~0.9%.

⚠️ **Confidence is not the discriminator.** The implausible flips run 0.259–0.664 and
the ordinary ones 0.333–0.819 — heavy overlap, and CLAUDE.md already records a
*refused* confidence ceiling on the sibling read. **The instrument is.**

## By document — n is 5, not 20

| document | rows | staves | overturns | reachable | label-gated |
|---|--:|--:|--:|--:|--:|
| brahms-1 / Breitkopf | 4 | 97 | 8 | 8 | **8** |
| mahler-5 / Peters | 4 | 65 | 6 | 4 | 4 |
| beethoven-5 / Litolff | 8 | 150 | 7 | 3 | 2 |
| dvorak-9 / Simrock | 3 | 60 | 1 | 0 | 0 |
| bach / Peters | 1 | 24 | 0 | 0 | 0 |

⚠️ Two of the eight Beethoven rows are the **same Litolff plate scanned twice** and
are not independent evidence. **Brahms 1 alone supplies 8 of the 14.**

## Two corrections to the record

**(a) `disagrees` is worse than absent — it is FALSE on a real disagreement.** It
compares only the **top two** ranked candidates, so a three-way contest whose top two
agree reads `False` while a genuine dissent sits third:

```
brahms-p2 staff 14 m0   clefG 0.927 | clefG 0.878 | clefF 0.317      disagrees=False
dvorak-p7 staff 23 m0   clefF 0.903 | clefF 0.664 | clefCAlto 0.276  disagrees=False
```

**(b) Reach fails silently where no margin label is printed.** Dvořák p6 and p7
report `labelled_staves: 0` — **45 staves, zero reachable** — on a document that
reads fine elsewhere. Any consumer gated on instrument identity inherits this.

## Provenance

Own `--tag=clefcontest`; **fixtures directory did not exist at start**; wall clock
**2566 s**, of which **1604 s** is transcription — *a cached arm returns in seconds*.
`OMR_SURYA_KEEP_ALIVE=0`; the shared server untouched. This arm's own pooled figure
is 0.8438 / 74,873 and is **deliberately not differenced** against the recorded
0.8444, which sits on a tree many commits stale under a ±6 noise floor.

**Guards proved by running, not asserted** — six refusal paths each exit 2, including
the one that matters: **pages present, staves absent.** Five self-test mutants each
caught. Four independent cross-checks, all keyed differently, all clean; the
staff-count join refused twice for real before it was corrected.

## ⚠️ Scope

**This measures REACH ONLY.** No accuracy claim, no edit-count delta, no A/B.
Whether acting on these staves improves OMR-NED is unmeasured, and the ordinary-music
residual above is a concrete reason it might not. **The next step is a human reading
~12 staves against the print** — that converts an upper bound into a defect count,
and nothing should be built before it.
