# `arc_kind`: the reading decides, the grammar records — and the grammar is a coin flip

2026-09-09. The fourth of the six declared stubs, filled. 199 arcs on one page
went from `not_implemented` to decided.

## Why it does not use the grammar it computes

`OMR_ARC_RECLASS` — the position-grammar veto — is default-OFF for a measured
reason: engraved 0.1306 → 0.1306 (+2 edits, 24 firings), scan 0.8387 → 0.8391,
**+130 edits, ALL of them in the tie→slur half**. Turning the grammar into a
gate here would enable half a refused flag by the back door, on the path with
the least measurement behind it.

So the DETECTOR'S CLASS decides and the grammar is recorded beside it —
additive evidence, never a gate.

## ⚠️ And the record now says the refusal was right

Beethoven 5 / Litolff `984073` `--pages 2`, 199 arcs:

| | |
|---|--:|
| decided | **199** (tie 119, slur 80) |
| grammar available (≥2 flanked heads) | **81 of 199 (40.7%)** |
| grammar AGREES with the reading | **42** |
| grammar DISAGREES | **39** |

**51.9% agreement — a coin flip.** And the split matches the flag's measured
attribution exactly: the expensive direction, tie→"says slur", is **28 of the
39** disagreements, while slur→"says tie" is 11. `OMR_ARC_RECLASS` measured
ALL +130 of its scan cost in the tie→slur half; this page shows why, from an
independent direction and with no truth file.

⚠️ **IT IS A RATE, NOT A COUNT OF ERRORS.** A disagreement says one of the two
readings is wrong and does **not** say which — the same shape as the
false-attachment probe (a note under a beam carries no flag), which this file
records as "a RATE and never a count". Do not read 39 as 39 misread arcs.

⚠️ **59.3% of arcs have no grammar at all** — fewer than two detected
noteheads under the arc's padded span (histogram: 73 arcs with 0 flanked
heads, 45 with 1). On a scan the heads an arc binds are often not all
detected. So even a grammar that worked would reach two arcs in five.

## Decisions inside it

- ⚠️ **STAFF STEPS, never spelled pitches.** The far head of a cross-barline
  tie does not restate its accidental and the resolver spells it plain, so a
  spelled-pitch key breaks truth-matched ties (+21 engraved edits, every loss
  a same-step `F#4 → F4` pair). The input is `Q.NOTEHEAD_STAFF_POSITION`, a
  clef-free measured step, and a test asserts `Q.PITCH` is NOT in `wants`.
- ⚠️ **The span is PADDED.** An arc is drawn BETWEEN its outer noteheads, so
  its ink stops inside both outer centres; unpadded, the Contrabass read
  `n1 → n4` in every bar whose truth is `n0 → n5`.
- ⚠️ **The canonical frame is CORRECT here**, unusually: the arc and the heads
  it flanks were cut from ONE cell, so they share a frame by construction. It
  is `arc_owner`, which asks about OTHER staves, that needs page pixels.

## ⚠️ `gather_glyph_families` was gathering in a frame that could not answer

It shipped 2026-09-09 emitting CANONICAL coordinates only. `arc_owner` asks
"whose noteheads does this arc hug" of every staff in the system — a
cross-staff comparison — so its declared input was **present and in the wrong
frame**. That is the fault `Q.ONSET_COLUMN` paid for (1,062 columns at 76.6%
corroborated, 699 agreeing to the FLOAT, which no scan does). Page pixels are
now carried beside the canonical ones, DECLINED rather than defaulted where
the cell cannot supply them.

⚠️ **`coverage()` cannot see this shape**: it reports such a family as `stub`
(input gathered), not `starved`. **A quantity can be gathered in the wrong
frame and look fed.**

## Tests

10 in `test_staged_arc_kind.py`. The load-bearing mutation — make the grammar
overturn the reading, i.e. the refused behaviour — turns exactly the two guard
tests RED. ⚠️ The first draft of the harness guessed the adjudicate API and
failed 8 of 10; the real idiom is `log.freeze(); adjudicate.run(log)`. The
harness also refused the `Q.GLYPH_BOX` read until it was DECLARED
(`UndeclaredEvidence`) — `Evidence` doing its job, so that `missing` and
`declined` can mean something.
