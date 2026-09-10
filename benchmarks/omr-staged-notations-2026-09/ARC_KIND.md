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

## ⚠️⚠️ The arbiter is silent where it is most needed — a peer's principle, tested here

The question is **not mine**. It comes from the meter/boundary session, stated
as a principle: *the case that most needs an arbiter is the case where the
arbiter is silent.* A page whose meter the reader mangles is a page whose ink
is degraded, and the same degradation stops its bars from summing — on the
Breitkopf system misreading `9/8` as `9/4`, **not one of its seven bars clears
the cross-staff quorum**.

`arc_kind` has the same shape, and it holds. Detector confidence as the
ink-quality proxy, 199 arcs, `probe_arc_grammar_confidence.py`:

⚠️ **The last two rows are a split of AVAILABLE, not of MISSING** — 42 + 39 =
81. They are labelled rather than indented, because an earlier draft of this
table put them under MISSING and a reader trusting the nesting got the exact
OPPOSITE of the finding: it read as the grammar both being unable to speak
about those arcs and agreeing with them. Caught by the meter/boundary session.

| population | n | median conf | q1–q3 |
|---|--:|--:|---|
| grammar MISSING (no pair of heads) | 118 | **0.408** | 0.321–0.644 |
| grammar AVAILABLE | 81 | **0.563** | 0.353–0.734 |
| — of the 81 available, AGREES with the reading | 42 | **0.694** | 0.522–0.797 |
| — of the 81 available, DISAGREES | 39 | **0.391** | 0.305–0.626 |

Two things fall out.

**1. The grammar is absent disproportionately on the weaker readings** (0.408
against 0.563). It is silent where a reading most needs checking — the peer's
principle, in a second mechanism, on a different page.

**2. And it sharpens: among arcs the grammar CAN speak about, disagreement
tracks confidence hard — 0.391 against 0.694.** The agreement rate is not flat
across the page; it collapses on weakly-read arcs.

⚠️⚠️ **THIS DOES NOT SAY WHICH READING IS WRONG, AND THE TWO EXPLANATIONS ARE
OPPOSITE.** Either (a) the disagreements are where the DETECTOR is wrong, and
the grammar is right there — in which case a confidence-gated veto would help;
or (b) the ink is bad, so BOTH readings are unreliable and a veto would swap
one unreliable reading for another. **The data cannot separate them**, and
reading it as (a) is exactly the mistake the flag/beam contradiction probe
warns about: it is a RATE and never a count.

⚠️ **What it DOES establish is that a flat agreement rate is the wrong summary.**
The 51.9% figure above is an average over two populations that behave
differently, and a future pricing of `OMR_ARC_RECLASS` on this path must
stratify by confidence rather than quote one number.

⚠️ **NOT GATED ON, deliberately — n = 1 page, 1 document.** This is precisely
the restraint the meter letter path already records: *"Confidence separates
the populations cleanly (0.887–0.927 engraved, 0.377–0.560 scan) and is
deliberately not gated on — four rows on two documents is not a threshold."*
199 arcs on one page is not a threshold either.

## The GATHER change moved nothing — two full re-gathers, not a re-adjudication

⚠️ **THE TWO CHEAP INSTRUMENTS ARE BOTH BLIND TO THIS**, established by the
duration-reader session catching itself about to report a vacuous pass.
`readjudicate.py` rebuilds a `Log` from a SAVED record's observations, so a
gather change never enters the rebuild and it passes **by construction**;
`reexport_arm.py` has the mirror-image blind spot on the export side. The
uncovered middle is *"did GATHER change what ADJUDICATE sees"*, and the only
instrument for it is two full runs of the same page.

`regather_control.py`, Beethoven 5 / Litolff `984073` `--pages 2`, before and
after the page-box fields landed on `Q.ARC_BOX` / `Q.REST` /
`Q.ARTICULATION_MARK`:

| | |
|---|--:|
| quantities compared | 24 |
| quantities that MOVED | **1 — `arc_kind`, the change under test** |
| `duration` | 939 → 939, **0 changed** |
| `pitch` | 816 → 816, 0 changed |
| `event` | 314 → 314, 0 changed |
| `glyph_owner` | 518 → 518, 0 changed |

⚠️ It doubles as a DETERMINISM control: detection confidences have been
measured moving between runs on byte-identical code, so 23 quantities
returning identical across two full runs is what makes the `arc_kind` delta
attributable rather than assumed.

⚠️⚠️ **AND THE COMPARISON ITSELF WAS UNPROVENANCED WHEN I RAN IT.** The staged
result JSON recorded NOTHING about which tree built it, so `MOVED: nothing`
would have been indistinguishable from *"you compared two runs of the same
tree"* or *"you compared a file with itself"* — the cached-arm trap the
meter/boundary session found in its own `run_arms.py`, one layer down. My
comparison was sound because I remembered which tree produced each file, which
is **a habit and not a mechanism**.

Closed: `staged/__main__.py` now stamps every record with its commit and a
`dirty` flag, and `regather_control.py` **exits non-zero** rather than report
an unstamped or same-tree pair. ⚠️ A DIRTY tree is never equal to itself — a
SHA cannot tell two sets of uncommitted edits apart — a rule adopted from the
meter session rather than re-derived. The committed artefact is regenerated
with `--allow-unstamped` so it carries its own caveat instead of looking
clean, and the refusal is verified to exit 2 **without a pipe**, because
`| tail` eats exit codes.

This is the empirical half of the duration-reader session's code-level
argument, which reached the same conclusion by reading rather than running:
`_rest_ruling` touches only `.score`, `.value` and `.id` on a `Q.REST` row and
**never reads `.detail`**, so added detail fields cannot reach a duration. Two
routes, one answer — and the run is the one that could have gone red.

### ⚠️ The boundary of that principle — and my own example of it was WRONG

The general form, agreed with the meter/boundary session: *wherever the first
reader is worst, the second is most often absent — and an availability or
agreement rate quoted as ONE number averages two populations that behave
differently.*

I offered a scope note: it holds where both readers depend on the **same ink**,
and would not follow for readers with independent failure modes — *a margin
label and a clef, say, where the label can be crisp on a page whose staves are
broken.*

⚠️⚠️ **THAT COUNTEREXAMPLE IS FALSE ON THIS CORPUS AND I ASSERTED IT WITHOUT
CHECKING.** `CLAUDE.md:4285`, measured over the 20-row scan gate: of the
unresolved non-treble staves — the entire population a label could ever help —
**29 of 29 have no label printed at all.** The margin label and the clef DO
fall silent together there.

⚠️ But they fail together for a **different reason**, and that is the part
worth keeping: not because the ink is degraded, but because the engraver
omitted the label on continuation systems. So the refined boundary, which is
the meter session's and came out of my error:

> **Two readers can be correlated through the DOCUMENT'S CONVENTIONS, not only
> through its ink.**

That is a wider hazard than the one I was scoping, and it is not measured —
it needs measuring rather than asserting, which is exactly what I failed to do.

⚠️ The same-ink form has clean examples on both sides in this repo, which is
what makes it evidenced rather than stated: **correlated** — bar sums and meter
glyphs, arc-grammar heads and arc class, and a roster at
`source_kind: "page"`, which CLAUDE.md already calls *"an OMR output of the
same raster"* and REFUSES; **independent** — a dossier fact, and the catalog
`works` tier at `source_kind: "catalog"`, *"independent of the truth
MusicXML"*.

So the hazard is the reason `source_kind` is load-bearing, reached from a new
direction: an arbiter carrying `page` fails together with what it arbitrates.
**If you want a second witness that does not fall silent exactly when it is
needed, it must not come off the same raster.**

⚠️⚠️ **THE RULE WAS NOT NEW TODAY — IT WAS UNNAMED, AND THIS REPO HAD ALREADY
APPLIED IT ONCE.** Found by the meter/boundary session verifying my 29-of-29
rather than quoting it onward. CLAUDE.md's probability-gates section argues for
`clef_register_warning` on exactly this ground: *"It needs NO instrument label,
which is what makes it worth having: 29 of 29 unresolved non-treble staves on
the scan corpus have no label printed at all, so it is the evidence that
survives exactly where label evidence is structurally unavailable."* That is a
second witness chosen **because it does not fall silent with the first** —
reached independently in the clef area, written down, and never generalised.
Three instances: the `source_kind` tiers, `clef_register_warning`, and the
meter's bars.

⚠️ **And the same 29 does DOUBLE DUTY, which is worth separating before anyone
cites it from here.** At `CLAUDE.md:4285` it is evidence that *label reading
cannot lift the clef number* — a REACH statement about a population. At
`CLAUDE.md:2300` it is the *justification for a label-free witness* — the
silent-arbiter rule. Same number, two conclusions, and only the second is this
one.
