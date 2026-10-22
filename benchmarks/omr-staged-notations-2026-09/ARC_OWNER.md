# `arc_owner`: the arc goes to the staff whose noteheads it hugs

2026-09-09. The fifth of the six declared stubs, filled — `OMR_ARC_ATTRIBUTION`'s
rule moved onto the staged path, with its measured constants **imported** from
`tools/omr/export.py` rather than restated, so the two cannot drift.

## Measured — Beethoven 5 / Litolff `984073` `--pages 2`, 199 arcs

| reason | n |
|---|--:|
| `no_better_staff` (stays) | 171 |
| `no_rival_staff` (nothing to compare with) | 16 |
| **`hugs_noteheads` (moves)** | **12** |

⚠️⚠️ **EVERY ONE OF THE 12 MOVES IS TO AN ADJACENT STAFF — delta ±1, six each
way, zero exceptions.** That is the measure-cell padding signature and an
independent corroboration that the rule finds the real fault rather than
noise: it is the same shape this repo already measured for the dynamic
letters, where 24% of them stand in the band of the staff **immediately
above — distance exactly 1, no exceptions**. Nothing in the rule knows about
adjacency; it fell out.

The separation is clean:

| | own clearance | winning rival |
|---|---|---|
| the 12 that MOVED | **3.80–9.24 spaces**, and 6 of 12 cover NOTHING in their own staff at all | 0.000–0.455 spaces |
| the 171 that STAYED | median **0.530 spaces** | — |

An arc covering nothing in its own staff is claimed outright: it binds no note
there, so there is nothing for it to be. Six of the twelve are that case.

⚠️ **The stayed population is not uniformly hugging** — 47% are under 0.5
spaces, median 0.530. The clean separation is on the MOVED side, which is what
the comparative rule is for.

## The refusals it honours

- ⚠️ **IT MOVES, IT NEVER DELETES.** `drop` measured 2,388 edits against
  `move`'s 2,371 — better arm-for-arm — and was REFUSED: it gets there by
  emitting 20 fewer slurs, **12 of them real**, the metric's under-prediction
  reward. Keeping the loser addressable is what lets a later identity
  correction reach it.
- ⚠️ **COMPARATIVE, never a threshold.** The clearance tail is not clean
  enough to threshold on, so an arc leaves only where another staff explains
  it BETTER. A one-staff page can never move an arc, by construction.
- ⚠️ **Distance to the staff LINES is the trap**, exactly as for notes: an
  engraver opens the gap above a staff *precisely so* its ledger notes and
  their slurs can live there.

## ⚠️ Heads are grouped by their OWNER, not by the cell they were cut from

The legacy rule says it in one line: the noteheads *"have already been
arbitrated across staves and each staff's head set is the one a READER would
see"*. A cross-staff duplicate is FILED on the staff that detected it, so
grouping by subject asks "whose heads does this arc hug" against head sets
ownership has already corrected — comparing the arc against a page nobody
sees. This is where A-ORDER-2 pays: `glyph_owner` is decided BEFORE this runs,
so its answer is simply available.

## ⚠️ Two mutations SURVIVED the first eleven tests

Written down because it is the finding, not a footnote. Deleting
`_ARC_RIVAL_MARGIN_SPACES` and grouping heads by subject staff both left the
suite GREEN — the tests only ever exercised rivals that beat the incumbent by
a mile, and no fixture had a head whose owner differed from its subject, which
is *precisely the population the rule exists for*. Four more tests close both;
re-run, each mutation now turns exactly one red.

⚠️ `_ARC_RIVAL_MARGIN_SPACES` is a measured PLATEAU — every value 0.25–0.75
reattributes the same arcs over the eleven works, and the answer first moves
at 0.90 — so a rival that is merely NEARER must not take the arc. A test
asserts the constants are IMPORTED.

## ⚠️ The input was in the wrong frame until today

`gather_glyph_families` emitted CANONICAL coordinates only — measured inside
ONE cell — so this decision's declared input was present and could not answer
its own cross-staff question. That is the fault `Q.ONSET_COLUMN` paid for. A
row with no page box now ABSTAINS `no_page_frame`; it is never compared in the
cell frame. An anti-drift test asserts the gatherer still carries it, because
if it ever stops, this decision silently abstains on every arc.

## ⚠️ They decide and still do not reach a FILE

Both arc quantities now report `decided_uncounted` in `coverage()` — the
report saying, correctly, that it cannot tell whether they were exported
because no counter exists. They were not: `<slur>` and `<tied>` are still
unwritten. **Three stubs remain** (`articulation_owner`, `wedge_anchor`,
`direction`), and `direction` is the only one still input-starved.

## ⚠️ The arc EXPORT is a separate unit, and here is the number that says so

`_mxl_note` already takes `tied_to_next`, `tied_from_prev` and `slur_states`,
so rendering is pure reuse — but **an arc crossing a barline is detected
TWICE**, once per measure cell, and emitting each as its own `<slur>` would
write two slurs where the music has one. That is why `annotate_slurs` sat
implemented, tested and UNWIRED from `89277a2` until 2026-09-01 on the legacy
path.

Measured on this page: **32 of 199 arcs (16.1%) begin within 20 canonical px
of their cell's left edge** — the cross-barline signature.

⚠️ **And the metric would not catch it.** OMR-NED is symmetric, so it rewards
emitting MORE symbols: the first cut of the legacy slur work LOWERED pooled
OMR-NED (0.2449 → 0.2436) while RAISING the edit count and the `wrong slur`
category. An arc export without the merge could look like an improvement while
being a regression.

So the remaining work is `_merge_arcs_across_barlines`'s three measured
constants moved onto this path — a boundary tolerance (0.5 spaces), a
continuation tolerance (2.0 spaces, a plateau over 1.0–6.0) and a notehead pad
(0.25 widths) — plus the `number=` allocator and the both-ends-same-voice rule.
It is its own unit of work with its own measurement, not a bolt-on here.
