# NEXT SESSION — give instrument identification its other channels

Sean, 2026-09-21: *"I thought we had figured out the instrument to line issue.
Using the natural order of instruments, the list of instrumentation from the
score or a dossier and the addition of any clefs that could be read as well as
family brackets — would all add up to clarity of the instrumentation. Did we
lose that at some point?"*

**He is right, and the answer is that most of it was never connected to the
reader that actually runs.** This brief is the verified state and the
constraints. **Everything in §1 was re-checked against the tree on 2026-09-21;
nothing here is quoted from memory.**

---

## 1. THE VERIFIED STATE

`adjudicate_instrument` (`tools/omr/staged/adjudicators/identity.py`) is, in
its entirety as far as evidence goes:

```python
labels = ev.rows(Q.MARGIN_LABEL)
if not labels:
    return Ruling.abstain("no_evidence")
...
roster_rows = ev.rows(Q.ROSTER_ENTRY, scope=Scope.SELF_AND_ANCESTORS)
```

**It reads exactly TWO quantities.** `grep` of its body for `ev.rows(` /
`ev.verdict(` returns those two lines and nothing else.

| Sean's channel | declared? | READ? |
|---|---|---|
| margin label | `wants` | **yes** |
| work roster / instrumentation list | `wants` | **yes — but only to filter a label already read** |
| natural order of instruments | `reasons=("score_order", …)` | **no branch can return it** |
| family bracket | `wants=(… Q.STAFF_GROUP)` | **never read — inert** |
| clef | — | **no** |
| staff ordinal | `wants=(… Q.STAFF_ORDINAL)` | **never read — inert** |

⚠️⚠️ **THE ROSTER IS UNREACHABLE ON EXACTLY THE STAVES THAT NEED IT.** The
`no_evidence` return happens **before** the roster is fetched, so a staff with
no margin label never reaches the one tier that carries
`source_kind: "catalog"` — the tier this repo chose *because it does not fall
silent when the raster is bad*. A staff the page does not label is precisely
the case a work-level roster exists for, and it is the case that exits first.

⚠️ `score_order` is **a vocabulary word with no branch** — the third
documented instance of that shape (after `roster` itself and
`adjudicate_slot_index`'s docstring rule).

---

## 2. THE REACH — measured, before any accuracy claim

`library/_shared-records/beethoven5-p1-p4-ink-identity.record.json`
(provenance `e38dbc25`, **clean tree**):

```
instrument verdicts:  decided/label 49   decided/roster 1   abstained/no_evidence 25
```

**Of those 25 abstaining staves:**

| channel on the record | count |
|---|--:|
| `Q.STAFF_ORDINAL` | **25 of 25** |
| `Q.CLEF_GLYPH` | **17 of 25** |
| `Q.CLEF_POSITION` | **17 of 25** |
| `Q.CLEF_LOCATED` | 3 of 25 |
| `Q.MARGIN_LABEL` | **0 of 25** — correctly; that is why they abstain |

`staff_group` decides **75 of 75** at `reason="bracket_block"`, and
`roster_entry` is on the DOCUMENT. **So every one of the 25 has at least one
unread channel sitting on the record**, and the family bracket is available for
all 75.

⚠️ **THAT IS REACH, NOT ACCURACY.** *The evidence is present* and *the evidence
would name it* are different claims and this brief only establishes the first.
Breitkopf is the opposite case — **91 of 97 named, 6 abstaining** — so it can
corroborate a rule but cannot exercise one.

---

## 3. THE STRUCTURAL FACT THAT CHANGES THE DESIGN

```
ORDER  1  staff_group        <- the family bracket, ALREADY decided
ORDER  5  instrument         <- this decision
ORDER  6  slot_index
ORDER  7  part_partition
ORDER  9  clef               <- the clef VERDICT, decided LATER
```

⚠️⚠️ **`adjudicate_instrument`'s OWN DOCSTRING INSTRUCTS SOMETHING IMPOSSIBLE.**
It says the score-order tier *"must therefore read `Q.CLEF` THROUGH `Evidence`
— never by reaching around it"*. **`Q.CLEF` does not exist at ORDER 5.** The
instruction is right about the hazard and wrong about the object.

**CLAUDE.md already records the resolution** (*A PREMISE ENCODED IN A REFUSAL
OUTLIVES ITS REASON*, instance 2): the circularity fear is true of **`Q.CLEF`,
a verdict**, and **false of `Q.CLEF_GLYPH` / `Q.CLEF_POSITION`, which are
GATHER facts available at every ORDER**. Sean, on that: *"We should know what
these are regardless of clef, and having a clef would only reinforce the
finding."*

So the clef channel is reachable — as **ink**, not as a verdict — and reading
it cannot close the loop `clef_correction.py:566` exists to prevent.
**Whatever is read must go through `Evidence` so it lands in `Verdict.basis`.**

---

## 4. ⚠️⚠️ PRIOR ART — READ THESE BEFORE WRITING ANYTHING

A session that skips this will re-derive a refuted result. All four are in the
tree; the first is the one that matters most.

1. **`benchmarks/omr-slot-index-2026-09/FINDINGS.md`** — **naming unnamed
   staves BY POSITION was already measured and it GRAFTS.** It scores *more*
   correct (66 vs 50) **and grafts 9 staves doing it** — *the guess wearing a
   number, priced.* Any score-order tier must beat that bar, not rediscover it.
2. **`benchmarks/omr-unnamed-block-slot-2026-09/FINDINGS.md`** — the family
   block that DID ship (`OMR_SLOT_FAMILY_BLOCK`, default ON since 2026-09-21).
   It places a staff without naming it, and its refusals are deliberate.
3. **`benchmarks/omr-staff-identity-labels-2026-09/FINDINGS.md`** — **29 of 29
   unresolved non-treble staves print NO LABEL AT ALL.** Better label reading
   cannot reach this population; that route is closed by measurement.
4. **`benchmarks/omr-part-instrument-check-2026-09/FINDINGS.md`** and
   **`benchmarks/omr-unnamed-staves-2026-09/`** — the check that asks whether
   one part carries one instrument, and the first pass at this population.

⚠️ **A WITHDRAWN INVESTIGATION IS INVISIBLE TO `git log -S`**, because it
changes no code. **`ls benchmarks/` for anything named after the thing** before
concluding a route is untried — that exact miss cost a lane a full day on
2026-09-21.

---

## 5. WHAT THE FLIP OF 2026-09-21 DID AND DID NOT DO

`OMR_SLOT_FAMILY_BLOCK` (default ON) **places** 15 of those 25 staves — they
join the right part. **It does not NAME them.** `export._default_name` is
reached whenever the instrument verdict abstained and returns
`f"Staff p{page}-s{system}-{staff}"` — *"A COORDINATE, NOT A GUESS"*.

**So the symptom Sean sees in a file — parts called `Staff p1-s0-3` — is this
decision abstaining, not the join failing.** The two were fixed apart and only
one of them is done.

---

## 6. THE CONSTRAINTS (non-negotiable, all from CLAUDE.md)

1. **ASK FIRST.** Before the first line of code, say out loud: how would a
   HUMAN read this off the page, and what ENGRAVING CONVENTION governs it?
   Then ask Sean. `docs/ask-first-conventions.md`.
2. **A wiring pass may CONNECT a decision; it may not let one GUESS.** An
   abstention is a counted gap. A wrong name is a graft, and a graft is silent.
3. **`Mode.ADDITIVE` — evidence CONTRIBUTES, it never GATES.** Sean, 2026-09-17.
   No channel may veto another into silence.
4. **It must still ABSTAIN.** Five unnamed staves against six reference slots
   genuinely do not determine which is which, and saying so is the right answer.
5. **Measure REACH before accuracy**, and report it even when it refutes the
   brief — that is how the C-clef lane produced its result.
6. **IMPORT the rules, never restate them.** `score_layouts.LAYOUTS` holds 10
   canonical orders; `slots.align` exists; `work_roster.decide` is measured at
   28 firings over 1,422 labels. A second copy of any of them will drift.
7. **The basis must record the dependency** — read through `Evidence`, never
   around it, or the circularity filter cannot see what you used.
8. **A mutation battery**, with a byte snapshot, an in-flight sentinel,
   `PYTHONDONTWRITEBYTECODE=1`, and **a judge that does NOT contain pytest's
   elapsed time** (that shape voided two published batteries on 2026-09-20).

---

## 7. WHAT WOULD MAKE IT A RESULT

- **Reach first**, per channel, on both shared records.
- **A print check.** `benchmarks/omr-part-join-phase2-2026-09/printed-lineups.json`
  is a human reading the plate, keyed `(page, system)` exactly as the record's
  subjects are, so the join needs no geometry. ⚠️ It is **LITOLFF ONLY** — an
  arm that scores a Brahms record against it reported **21 grafts that were its
  own**, and scoring is opt-in per record for that reason.
- **Grafts are the metric, not correctness.** The bar set on 2026-09-14 was
  *placed 50 / correct 50 / **wrong 0** / abstained 25*. A rule that names more
  staves and grafts one is worse than one that names fewer and grafts none.
- **No OMR-NED.** musicdiff does not score `<part-name>`; the metric is blind
  to this whole family and would mislead.

---

## 8. WHAT IS NOT ESTABLISHED BY THIS BRIEF

- **That any channel would name any staff correctly.** §2 is reach.
- **That the clef helps.** 17 of 25 carry a glyph; whether alto/tenor/bass
  discriminates *which* string part is unmeasured, and the record holds
  **74 `clefG`, 17 `clefF` and ZERO C clefs** — `_GLYPH_TO_CLEF` maps `clefC`
  to nothing by design, so the one clef that uniquely names a viola may never
  speak. **Check this before building on the clef.**
- **Anything about a second publisher.** Breitkopf has 6 abstentions; the
  domain is a property of a publisher's LABELLING PRACTICE.
- **Anything about the engraved family**, which is untouched.
