# `adjudicate_slot_index` — a rule that was described in bold and never built

**2026-09-14.** The ranked next work of
[docs/handoff-2026-09-11-phase-2-opened.md](../../docs/handoff-2026-09-11-phase-2-opened.md)
§6a/§8.1, verified and measured. The implementation was left as **unverified WIP**
on `claude/slot-index-by-name` when the previous session hit its usage cap — no
suite, no controls, no measurement. This is that verification.

---

## 1. What was wrong, and why it is the worst shape

`adjudicate_slot_index`'s docstring stated **in bold** that a short system pairs
by instrument NAME and abstains where the name was not read. **The function
contained no such branch and returned the staff's ordinal on every path** —
including on a branch it labelled `reason="named"`.

That is worse than a stale comment. A stale comment describes something that
*used to be true*; this described the code in front of you, in the imperative,
and was false. Its consumer (`adjudicate_part_partition`, then the exporter)
read the result as a document-wide identity.

## 2. The measurement — the rule against hand-read print truth

`probe_rule_vs_print.py`, on **Beethoven 5 / Litolff, pdf pages 1-4: 7 systems,
75 staves**. Two committed, independent sources, neither a reading of the other:

- **truth** — `printed-lineups.json`, a human on the print, corroborated by
  `printed-staves.json`'s prose;
- **names** — `margin-label-reach.log`, what the reader (text layer + Surya +
  Tesseract) *actually* produced: **50 labels over 75 staves**.

It runs the decision's own `_forced_pairing` and the decision's own
`instruments.lookup` — not a reimplementation.

| | staves placed | correct | **wrong** | abstained |
|---|--:|--:|--:|--:|
| the ordinal (incumbent) | 75 | 63 | **12** | 0 |
| the name rule | 50 | 50 | **0** | 25 |

⚠️ **THE CROSS-TAB IS THE RESULT, AND "IT FIXES 12" WOULD BE FALSE.** Per staff:

| incumbent → rule | staves | |
|---|--:|---|
| wrong → **ok** | **3** | a graft becomes the right slot |
| wrong → **abstain** | **9** | a graft becomes an honest gap |
| ok → abstain | **16** | right by position, now withheld |
| ok → ok | 47 | unchanged |
| **ok → wrong** | **0** | no new graft |

**All 12 grafts are removed and none is created — but only 3 are repaired.**
The other 9 become abstentions, and **16 staves the ordinal placed correctly are
withdrawn**. Net: 75 placements → 50, all 50 right.

Whether that trade is good is a question about the consumer, not this decision,
and the repo has already answered it for `_stitch_slots`: *joining by position
would graft one instrument's music onto another*. An abstention costs a
fragment; a graft costs a Timpani part carrying the Viola's key signature.

### The 12 grafts are two systems, and both are interior suppression

```
p3/s1 (8 staves)  — 7 wrong: suppresses Oboi, Trombe, Timpani
p4/s0 (11 staves) — 5 wrong: suppresses Timpani, splits the bottom staff
```

Everything below the first suppressed staff shifts up by one. The page names its
own suppression exactly where it happens: p3/s1 reads `Fl. Cl. Fag. Cor.` — **no
`Ob.`** — and the rule puts those four on slots **0, 2, 3, 4** where the ordinal
says 0, 1, 2, 3.

## 3. ⚠️⚠️ TWO CLAIMS THIS MEASUREMENT REFUTES

### 3a. The ambiguity machinery never fires on this document

Branch counts over every short-system staff:

| branch | fires |
|---|--:|
| `unnamed` → abstain | **25** |
| **forced** → a slot | **38** |
| `cands != 1` → `ambiguous_pairing` | **0** |
| `unpaired == best` → condition (b) | **0** |

`_forced_pairing`'s own docstring says of the repeated-name case: *"the
repeated-name case is exactly the one an orchestral page prints (two horn
staves), so this is the common case and not a corner."* **On this document it is
neither — it fires zero times**, and a mutation that deletes the whole
`cands != 1` branch changes the measured result by **nothing**.

⚠️ **And the reason is structural, not luck.** The only name repeated in the
reference is `Violin` (slots 7, 8) — and **no short system ever reads a violin
label**, because the strings are the family this edition stops labelling on
continuation systems. The ambiguity guard is dormant *by the same mechanism*
that produces the 25 abstentions. So: **the guard is correct (unit-tested,
mutation-tested red) and this measurement does not corroborate it.**

### 3b. The abstentions are the page's limit, not the rule being timid

Checked rather than assumed. On `p4/s0`, 6 winds are named through slot 5 and
5 unnamed staves remain for reference slots 6-11 — **one suppression among six
positions**, and nothing read says which. On `p3/s1`, 4 unnamed staves remain for
7 slots. In both the evidence genuinely does not determine the answer, so
abstaining is right and **the lever for the 25 is label reach on string staves**,
which CLAUDE.md already measures as structurally unavailable on these editions
(*29 of 29 unresolved non-treble staves print no label at all*).

## 4. The probe has teeth — mutation-tested on the real data

| mutant | result |
|---|---|
| place an unforced staff by position | **50 / 0 wrong — unchanged** (branch never reached) |
| place **unnamed** staves by position | **66 correct / 9 WRONG** — 9 grafts, caught |
| drop condition (b) | `test_two_staves_competing_for_ONE_reference_slot_both_abstain` goes RED |

The second is the one that matters: "name what you can, position the rest" scores
*more correct* than the rule (66 vs 50) and grafts 9 staves doing it. That is the
guess-wearing-a-number the docstring refuses, and the probe prices it.

## 5. ⚠️ A SEPARATE DEFECT, FOUND IN PASSING AND NOT FIXED HERE

The reference lineup the rule builds reads **slot 11 = `Bass voice`** — the page
prints `Basso.` and the lexicon returns a SINGER on an orchestral score. This is
the trap CLAUDE.md documents at length (35 rows on the edition tier). It is
**inert here** — no short system reads `Basso`, for the same reason the ambiguity
guard is dormant — so the measured result does not depend on it. Recorded rather
than repaired: it belongs to the lexicon/position channel, not to this decision.

## 6. Scope

- **n = 1 document, 1 publisher, 4 pages, 1 movement.** The truth file says so in
  its own `_not_established`.
- **This measures the RULE on real reader output, not an end-to-end run.** A
  cloud container has no `omr-weights/` and no `library/`, so GATHER cannot read
  a page; `slot_arm.py` is the end-to-end arm and needs a record this container
  cannot make. What that misses is how names *reach* the decision
  (`_names_by_system`, ordinal indexing) — covered by
  `test_staged_slot_by_name.py`, not by this.
- Suite: **3,760 passed**, 2 failed, both `test_direction_text.py::TestReaderSelection`
  and both **pre-existing on `origin/main`** (verified in a clean worktree).

## 7. Reproduce

```bash
PYTHONPATH=. python3 benchmarks/omr-slot-index-2026-09/probe_rule_vs_print.py
PYTHONPATH=. python3 -m pytest tools/omr/tests/test_staged_slot_by_name.py -q
```

---
---

# 2026-09-15 — the END-TO-END arm, on a machine with weights and a library

**§6 above says what the 2026-09-14 measurement does not establish: it ran the
RULE over recorded reader output in a container with no `omr-weights/` and no
`library/`, so "how names *reach* the decision (`_names_by_system`, ordinal
indexing)" was covered by unit tests and by nothing else.** `slot_arm.py` is the
end-to-end arm and had never been run. This is that run. **The measurement above
stands unchanged**; everything here is new.

One gather (`run_gather.sh`, unmodified), **33 min**, clean tree
`ce7b8ba7`, `provenance.dirty: false` — then that ONE gather adjudicated twice
and, separately, **exported** twice, so the two arms differ only in
`adjudicate_slot_index` and no detector jitter enters.

---

## 1. REACH, and the segmentation under it

| | |
|---|--:|
| staff-systems gathered | **75** |
| `Q.MARGIN_LABEL` observations | **50** |
| `Q.INSTRUMENT` decided | **50** (`no_evidence` 25) |
| `Q.SLOT_INDEX` decided | **50** (`unnamed_in_short_system` 25) |

Per system: **12 / 7 / 7 / 7 / 4 / 6 / 7**, reproducing the committed
`margin-label-reach.log` distribution exactly. ⚠️ Without `--surya --ocr` this
arm is DEAD and says so: the free text-layer rung reads 0 of 75 on this 1870
scan, and both arms would then abstain identically.

⚠️ **AND THE THING THE PROBE COULD NOT CHECK, CHECKED FIRST: our segmentation
agrees with the print on 7 systems of 7** (12 / 11 / 11 / 11 / 8 / 11 / 11).
That matters because the probe keys its truth on the PRINT while the record
keys on OUR OWN reading, and because `_pick_reference` takes **the widest
system WE READ**, not the widest the page prints — one mis-segmented system
would have moved every slot silently. `part_join_arm.py` prints this table
before any slot is read.

## 2. It reproduces the probe EXACTLY — to the staff, not to the total

| | placed | correct | **wrong** | abstained |
|---|--:|--:|--:|--:|
| probe, 2026-09-14 (recorded reader output) | 50 | 50 | **0** | 25 |
| **this run, end to end** | **50** | **50** | **0** | **25** |

And the cross-tab, which is the claim that can actually fail — the probe's
numbers are in §2 above and these are this run's:

| incumbent → rule | probe | **end to end** |
|---|--:|--:|
| wrong → ok | 3 | **3** |
| wrong → abstain | 9 | **9** |
| ok → abstain | 16 | **16** |
| ok → ok | 47 | **47** |
| **ok → wrong** | 0 | **0** |

**Every cell identical.** So `_names_by_system`'s ordinal indexing and the
reference pick behave on a real record exactly as they did on the reader log,
and §6's open item is closed for this document. ⚠️ **The CONTROL that makes
that a result rather than a tautology**: the two arms are compared per staff
before any count is read, and they **differ on 28 of 75** — a run in which they
agreed would exit non-zero rather than report a clean equality.

## 3. ⚠️⚠️ THE NUMBER SEAN IS WAITING ON: **75 fragments → 37 parts**, and the graft is gone

`adjudicate_part_partition` stops refusing. `_slots_are_ordinals` is now
**False**, because the 8-stave system p3/s1 places its four read names at slots
**0, 2, 3, 4** — a table with a GAP, which is the whole thing the predicate asks
for.

| | BEFORE (the ordinal) | **AFTER (the rule)** |
|---|---|---|
| `part_partition` | `deduced_anchor` `{join: ordinal, reason: slots_are_ordinals}` | **`slot`** `{join: slot, slots: [0..11]}` |
| `join_used` in the file | `fragments` | **`slot`** |
| **exported `<part>`** | **75** | **37** = 12 joined + **25 stranded** |
| **GRAFTS** | **12** | **0** |
| condensation (reported apart) | 4 | 0 |
| measures / notes | 1183 / 2473 | **1183 / 2473, identical** |
| parts with a real `<part-name>` | 50 of 75 | 12 of 37 |

Both files parse. **The accounting control holds on both arms, and it holds by
RAISING**: `to_musicxml` throws `Unbalanced` rather than returning a flag, so
two completed exports *are* the balance check passing — not a number anyone had
to read.

⚠️ **37 is not 12, and the 25 are the abstentions arriving in the file.** The
exporter strands a staff with no slot into its own part. That is the §2 trade
made visible: 25 staff-systems that the ordinal placed (16 of them correctly)
are now separate fragments rather than sitting — 9 of them wrongly — inside
another instrument's part.

### ⚠️⚠️ AND THE PHASE-2 PREDICTION IS CONFIRMED TO THE MEASURE

`benchmarks/omr-part-join-phase2-2026-09/FINDINGS.md` predicted from the measure
math alone that a correct join gives **111 / 93 / 78**, not equal parts, because
the plate suppresses Oboi and Trombe on one system and Timpani on two. The
exported file:

```
Flute 111   Clarinet 111   Bassoon 111   Horn 111      (all 7 systems)
Oboe   93   Trumpet   93                               (111 - 18: no p3/s1)
Timpani 78                                             (111 - 18 - 15)
Violin 16   Violin 16   Viola 16   Cello 16   Bass voice 16
```

**111 / 93 / 78 exactly**, reached from a different direction by an independent
run. The five string parts sit at **16** — page 1's system only — because this
edition stops labelling its strings on continuation systems, which is the same
mechanism as the 25 abstentions and not a second fault.

⚠️ **Two file-shape observations, neither repaired here.** The 25 stranded
fragments are written FIRST and the 12 joined parts last, so the score's part
order is no longer the printed top-to-bottom order. And **slot 11 is exported as
`Bass voice`** — §5's lexicon defect, previously inert, now reaching the FILE as
the `<part-name>` of a real joined part.

## 4. ⚠️⚠️ WHAT THIS RUN REFUTED: `slot_arm.py`'s OWN graft classifier under-counted

The first end-to-end run reported the incumbent at **10 grafts and 6
condensations**. The probe and the measure-math partition both say **12**, split
`{p3/s1: 7, p4/s0: 5}`. `_report`'s test was
`printed.startswith(slot) or slot.startswith(printed) or " e " in printed`,
which asks nothing about instruments:

* **`Violino II` STARTSWITH `Violino I`** — the p4/s0 staff the ordinal files
  under the FIRST violin's part read as condensation;
* the third clause excuses **any** name containing ` e ` against **any** slot,
  so `Violoncello e Basso` filed under `Violino I` read as condensation too.

Both are grafts. **Fixed** (`slot_arm.classify`): a printed staff condenses
reference parts iff the slot's name is one of the ` e `-separated parts it
prints — an exact membership test, **no threshold, nothing tuned**. It is
CHECKED rather than chosen: it lands on `{p3/s1: 7, p4/s0: 5}` = 12, agreeing
with two prior independent measurements where the old rule agreed with neither.

⚠️ **It moves the AFTER arm by NOTHING** — that arm has zero of both under
either rule — so the RULE's result never rested on this. What it corrects is the
incumbent it is measured against, in the direction that flattered the incumbent.

⚠️ **The same shape this file already records, one layer out**: §2 warns that
conflating condensation with a graft *"was already measured turning 12 into
16"*. This is that hazard in the other direction, and it was in the instrument
written to avoid it.

**Controls**: `slot_arm.py --self-check` (no record, no weights) asserts the
whole 16-row table, the 12/4 split and the by-system split, with a positive
control in the same class — *a staff under its own part reads `ok`* — because a
rule calling every disagreement a graft would satisfy the graft count alone.
`mutate_classify.py`: **6 arms, all red, positive control green**, every anchor
asserted unique before it is applied. ⚠️ **A seventh arm SURVIVED and was an
EQUIVALENT MUTANT**: deleting a `.strip()` on the split components changed
nothing, because the separator carries its own spaces — so the **code was
deleted** rather than a fixture invented to make the arm go red.

## 5. What is NOT established

* **Not accuracy of the 50 names.** This reproduces the probe's placements; it
  does not re-adjudicate whether the reader's strings are right (`Obol.` still
  reads at low confidence, and slot 11 is still `Bass voice`).
* **Not that 37 is better than 75 for a human.** This measures what the join
  does, not what a cleanup count costs. Sean's §5.2 decision in
  `docs/handoff-2026-09-11-phase-2-opened.md` is still open — what has changed
  is that it is now *37 parts with the graft gone*, not *75 fragments*, and the
  25 fragments are exactly the staves nothing named.
* **Not the 72-hour claim about other documents.** `_pick_reference`'s
  tie-break, the `cands != 1` branch and condition (b) still fire **0 times**
  here, for §3a's structural reason.
* **Nothing about a second publisher or a second edition**, and nothing about
  pdf page 5 onward.

**n = 1 document, 1 publisher, 1 movement, pdf pages 1-4, 7 systems, 75
staves** — the same window as every figure above it, and the *low-res bitonal*
Litolff `984073` that CLAUDE.md calls the pessimistic end of the corpus.

## 6. Reproduce

```bash
bash   benchmarks/omr-slot-index-2026-09/run_gather.sh          # ~33 min, needs weights + library
python3 benchmarks/omr-slot-index-2026-09/slot_arm.py      OUT/record-labels.json --verbose
python3 benchmarks/omr-slot-index-2026-09/part_join_arm.py OUT/record-labels.json --xml-dir OUT/xml
python3 benchmarks/omr-slot-index-2026-09/slot_arm.py --self-check     # no record needed
python3 benchmarks/omr-slot-index-2026-09/mutate_classify.py
```

⚠️ The record is **134 MB** and is deliberately not committed; `out/` holds the
gather log and both arms' output. ⚠️ Each arm rebuilds the whole `Log` and
re-runs ADJUDICATE, so `slot_arm.py` took **44 min** here (two arms) and
`part_join_arm.py`, which also runs EVALUATE and exports, **31-50 min** —
bracketed rather than stated, because it was observed running at 31 min and
finished before the next check.
