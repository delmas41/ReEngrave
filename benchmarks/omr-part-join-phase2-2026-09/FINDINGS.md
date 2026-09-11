# Observation 5 — "none of the measure math makes sense"

⚠️ **Written by the MANAGER from the agent's own report**, because the harness
refused a subagent-written findings file. Every number here is the agent's and
every probe that produced it is committed beside this file
(`probe/`, `out/{partition,numbering,join-arm,mutate-join,margin-label-reach}.txt`).
The narrative is transcribed, not re-derived; where this file and a probe
disagree, **the probe is right**.

Phase 2 of [docs/plan-2026-09-10-wire-first-then-reconcile.md](../../docs/plan-2026-09-10-wire-first-then-reconcile.md).
Sean, reading the first cleanup artefact against the print: *"none of the
measure math makes sense."*

---

## 1. The exact partition

Derived from the **exporter's own** system map and asserted measure-for-measure
against the XML, so these are the file's numbers rather than a reconstruction:

```
part     meas   p1/s0  p2/s0  p2/s1  p3/s0  p3/s1  p4/s0  p4/s1
P1-P8     111      16     16     15     16     18     15     15
P9-P11     93      16     16     15     16     --     15     15
P12        16      16     --     --     --     --     --     --
```

| part | identity | what is missing |
|---|---|---|
| P1-P8 | `111 = 111 − 0` | nothing |
| P9-P11 | `93 = 111 − 18` | **p3/s1**, the 8-stave system |
| P12 | `16 = 111 − 95` | every system but `p1/s0` |

`8×111 + 3×93 + 16 = 1183`, the file's own count. **Balances on every part,
0 unexplained** — the standard the `entire staff` separation set.

**The third fact is the one Verovio complained about**: measures are numbered
**cumulatively within a PART**, so `p4/s0` begins at **64 or 82 depending on
which part you are in**, and `p4/s1` at 79 or 97. That is
`Mismatching measure number 87`, to the bar.

---

## 2. The join was not refusing — it was joining WRONG

`join_decided: "slot"`, `join_used: "slot"`, 12 parts, 0 stranded. ⚠️ **And the
"slot" WAS the staff's own ordinal**: all 75 `Q.SLOT_INDEX` verdicts read
reason `full_lineup`, whose own detail says *"positional: no identity was read
here"*.

The chain, each link a grep or a record fact:

1. ⚠️⚠️ **`pipeline.run_staged` takes `pdf_path`, rasterises with it, and DROPS
   IT.** `gather()` has a `pdf_path` parameter whose only supplying call site
   in the entire repo is `gather()`'s own forward to the reader — **a parameter
   with no producer**. Consequence on every staged run ever made:
   `margin_label` files **0 verdicts and 75 abstentions**, `not_implemented`,
   detail *"no pdf_path supplied to gather()"*.
2. `instrument` → `no_evidence` **75 of 75**. (`roster_entry` →
   `out_of_scope`, *"no work id / roster supplied"* — the second route is off
   too.)
3. `slot_index` → the ordinal, 75 of 75.
4. `adjudicate_part_partition` → `join: "slot"` over that table.
5. The exporter honoured it and joined systems of **12, 11 and 8** staves **by
   position**.

**The graft: 12 of 75 staff-systems carry a different instrument from their
part**, `{p3/s1: 7, p4/s0: 5}` — **independently reproducing the
key-signature session's figure from the measure math**, including **P7
(Timpani) holding the VIOLA's staff on p3/s1**, which is where its seven
sharps came from. (4 further rows are condensation — `Violoncello` against
`Violoncello e Basso`, derived from the label's own `e` — and are reported
apart; conflating them gives 16.) ⚠️ **The suppressions are INTERIOR** — Oboi
is 2nd of 11, Timpani 7th — which is the whole of it.

---

## 3. ⚠️⚠️ Padding vs joining — and the answer is NOT the obvious one

**A correct join makes the measure numbers WORSE.** Grouping every printed
staff-system under the instrument the page actually prints there gives
**111 / 93 / 78 / 31**, not equal parts — Timpani falls to 78. **So the eight
parts that read 111 today read 111 BECAUSE the graft lends them another
instrument's bars.** The histogram and correctness are different axes, and
optimising the histogram optimises the wrong one.

Three repairs, and **the ORDER is load-bearing**:

1. **The join must stop guessing** — *shipped, see §4.*
2. **Number a measure by its place in the DOCUMENT's bar sequence, not the
   part's running count.** Writes no music, needs no meter, makes
   `<measure number=N>` name one instant. **Not shipped** — it needs a fact no
   quantity holds, and lands in the emission loop two sibling agents were
   editing.
3. **Pad the tacet spans** — the REST path, a sibling's lane. ⚠️ **Must follow
   1 and 2.** Padding first would give P2 the oboe's bars *and* the
   clarinet's, at correct numbers — **the complaint stops and the wrong notes
   remain**, which is worse, because a graft counted as a note error ranks the
   work into the wrong module. It also needs a bar length, and the meter is
   decided on **1 system of 7** here.

---

## 4. Shipped

* **`run_staged` forwards `pdf_path`**; `--surya` / `--ocr` are opt-in on the
  staged CLI. ⚠️ **REACH measured first**: the cascade reads **50 labels over
  75 staves**, 12 of 12 on the opening system; the free text-layer rung reads
  **0 of 75** on this 1870 scan. ⚠️ **Page 3's 8-stave system reads
  `Fl. Cl. Fag. Cor.` — no `Ob.`**: the print itself confirming the
  suppression, with the anchors exactly where the graft is.
* **`_slots_are_ordinals`** — a slot table that is `0..n-1` on every system
  **expressed no suppression**, so joining on it *is* the ordinal join the
  branch above it just refused → `deduced_anchor` → fragments. ⚠️ **The rule
  is STRUCTURAL, not a reason string**, and the re-gather proves why: 50 slots
  are now reason `named` and **the value is still the ordinal on all 75**. A
  provenance filter would have re-admitted the graft the moment one label was
  read.

**End-to-end arm, one re-gather:** `margin_label` 0 → **50** · `instrument`
0 → **50 decided** · `part_partition` `slot` → `deduced_anchor` · export
**12 parts → 75 fragments** · **total measures 1183 → 1183, conserved to the
unit** · `balanced: True`, census `unaccounted` empty. **48 of 75 parts now
carry a real `<part-name>` against 0 of 12** — the artefact's third recorded
defect, closed as a side effect.

**Controls**: 14 tests; mutation battery **9 arms all red, positive control
green**. ⚠️ Two of the first run's results were the BATTERY's own — an anchor
occurring twice, and a survivor in which bypassing the check so that
*everything* refuses left the suite **green**, because every refusal test was
satisfied by a rule that refuses unconditionally. *A battery of refusal tests
can pass by refusing everything*, arriving for the third time in this repo.

---

## 5. ⚠️ The cost, stated plainly: 12 parts → 75 fragments

Taken deliberately, **one predicate to revert**. The argument: **the graft is
SILENT and fragments are LOUD.** A grafted part looks like a clean score and
carries another instrument's music; a fragment is visibly unfinished. ⚠️ **This
is a judgement about which failure a human can see, and it is SEAN'S to
overrule** — the revert is one predicate.

## 6. Refused

Joining by ordinal across disagreeing systems (it was already happening, and
was removed); padding (not this lane, and wrong to do first); implementing the
short-system name pairing — the right next job, but it needs `slots.align`
wired and its own measurement.

---

## 7. Corrections

* The manager's brief said `instrument` abstains on **22 of 22** staves here.
  On this artefact it is **75 of 75** — 22 was an older 3-page `group_symbol`
  figure.
* The brief framed the slot join as unable to *help*. **It is not passive — it
  is ACTIVE AND WRONG.**
* ⚠️⚠️ **`adjudicate_slot_index`'s docstring states in bold that a short system
  pairs by instrument NAME and abstains where unread. The function contains no
  such branch.** A documentation shape not previously recorded here: **a rule
  described in a docstring and never built** — worse than a stale claim,
  because it reads as a claim about the code in front of you.
* The staged `Q.SLOT_INDEX` is **not** the legacy contextual `slot_index`;
  `OMR_SLOT_STITCH`'s knobs entry describes a different mechanism, and the
  legacy path is untouched by this change.
* ⚠️ **New hazard surfaced by reading labels at all**: `Basso.` → **Bass
  VOICE**, a singer on a Beethoven symphony, 1 of 50. `adjudicate_instrument`
  calls `instruments.lookup` raw, with neither `AMBIGUOUS_ALIASES` /
  `score_layouts` nor the roster veto the legacy pass added for exactly that
  string. ⚠️ **The trade runs both ways** — the same absence makes
  `Tp.` → Timpani **correct** here, which the legacy position prior gets
  **wrong** on this very edition.

## 8. Ranked next

1. `adjudicate_slot_index` implementing **its own docstring's** short-system
   rule, reusing `slots.align` and reading its `build_reference` warning first.
2. The **numbering** repair (§3 item 2).
3. **Padding** the tacet spans (§3 item 3) — after 1 and 2.
4. The **roster** route: `run_staged` takes `roster`, and nothing on the CLI
   supplies it.
5. Re-price `OMR_METER_CARRY`, which repair 3 now depends on.
