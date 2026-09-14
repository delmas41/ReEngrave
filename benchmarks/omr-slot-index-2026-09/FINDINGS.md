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
