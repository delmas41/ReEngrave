# The staged slot carry — reach ZERO exactly where it is needed

⚠️⚠️ **CORRECTION, ADDED AT LANDING THE SAME NIGHT — READ THIS FIRST. THE
MEASUREMENT'S PREMISE CHANGED UNDER IT.** A parallel session flipped
`OMR_SLOT_FAMILY_BLOCK` **ON by default** (`infer.py:146`, deny-list) hours
after this was measured. That rule is exactly the one §"What this means"
below names as standing in front of the carry, and CLAUDE.md records it placing
**15 of these very 25** staves. **So the "reach ZERO" figure is a property of a
record gathered with that rule OFF, and it is now stale for the default
configuration.** What survives untouched is the *structure* of the finding —
**the carry is keyed on a SLOT, so its reach is whatever the slot rule leaves
it**, and the two are in series rather than in competition. ⚠️ **The number
must be re-taken on a record gathered with the current defaults**, and that
needs ≥2 systems, so a one-page gather cannot answer it. Nothing else in this
file is affected; the engraved arm had slots either way.


**2026-09-22.** `benchmarks/omr-roster-truncation-reprice-2026-09` ranked this
second: the LEGACY path stamps one instrument name per SLOT onto every staff of
that slot on every page (`contextual.py:1527`); the STAGED path has no
equivalent, because `adjudicate_instrument` is `Kind.STAFF` reading
`Q.MARGIN_LABEL` at `Scope.EXACT`. **A sixth instance of *"shipped means the
LEGACY path"*.** It asked for per-slot reach on a staged record before anything
is built. **Measured — and it reverses the ranking.** No file under `tools/`
changed; nothing is proposed.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**ASSUMED** — an engraver spells an instrument in full on a movement's first
system and ABBREVIATES it on continuation systems, and the abbreviation names
the same instrument at the same place in the score order. That is what a slot
carry encodes.
**WHAT WOULD FALSIFY IT** — a page where two systems print different
instruments at one ordinal. That is precisely the graft `_slots_are_ordinals`
refuses, and this repo has paid 12-of-75 for it.
**NOT CONFIRMED WITH SEAN.**

## The result — the carry's reach is decided by the SLOT, not by the name

| record | staff-systems | unnamed | of those, **reachable by a carry** |
|---|--:|--:|--:|
| **Litolff scan**, pp.1-4 (4 systems, short lineups) | 75 | **25** | **0** |
| **Engraved render**, 3 pages (full lineup) | 54 | 4 | **4** |

⚠️⚠️ **ALL 25 UNNAMED STAVES ON THE SCAN HAVE NO SLOT EITHER** — every one is
`slot_index: unnamed_in_short_system` — **so a carry keyed on a slot has no
key.** The blocker is the SLOT, not the name.

⚠️⚠️ **AND THAT IS THE WRONG WAY ROUND.** The carry is reach-**positive**
exactly on a FULL-LINEUP page, which is where the ordinal join already works
and identity is least at risk; and reach-**zero** on a SHORT system, which is
the only place identity is actually hard. **A carry would help where help is
not needed and be silent where it is.**

## The four engraved cases are right, and they show the convention working

| staff | what the page prints | the lexicon | a carry would say |
|---|---|---|---|
| `staff/0/0/6`, `/7` | `Bassoon 1`, `Bassoon 2` | **resolves** | — (already named) |
| `staff/1/0/6`, `/7` | **`Bsn 1`**, **`Bsn 2`** | `not_in_lexicon` | **Bassoon** |
| `staff/2/0/6`, `/7` | **`Bsn 1`**, **`Bsn 2`** | `not_in_lexicon` | **Bassoon** |

The renderer spells it in full on page 0 and abbreviates on continuations —
**the convention above, observed** — and the carry names all four correctly,
checkable against page 0's own reading rather than against a guess.

⚠️ **A separate, cheaper finding falls out: `Bsn` is a LEXICON GAP.** A plain
English abbreviation the reader does not know. Fixing the lexicon would close
these four **without any carry at all** — and it is the intervention this repo
already has a validated harness for
(`benchmarks/omr-lexicon-2026-09`, dump-and-replay over 1,422 real labels plus
the 1,651 × 223 cross product). **Not shipped here**: an alias is GLOBAL, and
this repo's rule is that a lexicon change is priced on that cross product
first.

## What this means for the ranking

**The staged slot carry should not be built next.** Its reach on the document
every lane measures on is **zero**, and the thing standing in front of it is
the SLOT — which already has a mechanism: `adjudicate_slot_index`'s
`family_block` tier (FORCED, ADJUDICATE) and `OMR_INFER`'s
`collapse_slot_index_to_family_block`, which CLAUDE.md records placing **15 of
these very 25**. ⚠️ **So a carry is DOWNSTREAM of that rule, not an alternative
to it**, and its reach should be re-measured on a record where the slots have
been placed — which this one predates.

## What is NOT established

- **n = 2 records, 1 scan + 1 render, one work.**
- ⚠️ **No accuracy is claimed for the scan side at all** — reach is zero, so
  there is nothing to be right or wrong about.
- The four engraved cases are checked **against page 0's own reading**, not
  against a print — though the truth MusicXML names those parts Bassoon.
- ⚠️ **The composition with the family-block slot rule is NOT measured.** It
  needs a fresh gather on today's tree; the shared record carries no
  `family_block` verdict.
- Nothing was re-gathered, exported or scored. **No OMR-NED** — musicdiff does
  not score `<part-name>`.
