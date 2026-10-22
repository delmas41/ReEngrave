# The INFER sequence — what runs, in what order, and which orderings are real

**Date:** 2026-10-07. **Path:** STAGED (`tools/omr/staged/infer.py`,
`inferences.py`, `pipeline.decide`). **Authority:** `infer.RULES` (the
`@rule` registrations in `inferences.py`, in file order), `infer.run`,
`infer._admit`, and `evaluate.run_over` for the pass that follows. This
document is a reading of the tree on that date; where it and the tree
disagree, the tree is right (CLAUDE.md rule 10).

Fourth of the per-stage sequence documents: GATHER
`docs/gather-sequence-2026-10-06.md`, ADJUDICATE
`docs/adjudicate-sequence-2026-10-07.md`, EVALUATE
`docs/evaluate-sequence-2026-10-07.md`.

---

## 1. What happens around the stage (`pipeline.decide`)

1. EVALUATE has run and returned its report.
2. `--through evaluate` returns before this point. Otherwise
   `infer.stage_should_run()` asks whether **any rule is enabled** — two
   rules are `ALWAYS_ON` since roadmap 0.2c, so under default settings the
   stage always runs; the `inference` key is absent from the record only
   when no rule is enabled (`test_infer_bypass` reaches that by removing
   the always-on rules from the registry).
3. **INFER** (`infer.run(log, evaluated)`) — §2. It refuses to run without
   EVALUATE's report (`NotEvaluated`) and refuses an unfrozen log
   (`LogNotFrozen`): the two orderings "after EVALUATE" and "never loosens
   GATHER" are arguments it cannot be called without, not conventions.
4. **The bounded second EVALUATE** (`evaluate.run_over(log,
   infer.inferred_verdicts(log))`) — the same rule loop as the first pass,
   same order, firing only where a rule's cause, or a verdict it declares
   it also reads, is one INFER just wrote. One pass; a consequence of a
   consequence of an inference is not reached, by design. Its report rides
   inside `inference` as `reevaluation`.
5. EXPORT.

### 1a. One proposal (`infer._admit`) — every guard, in one place

For each rule in registration order, for each subject at its scope, the
rule returns `Proposal`s (never verdicts). For each:

1. No prior verdict on the target → skipped `no_prior_verdict`.
2. Prior is DECIDED → skipped `prior_is_decided`. **An inference never
   overturns a reading** (rule 3). `INFERABLE` is NARROWED and ABSTAINED
   only.
3. Prior is NARROWED and the proposed value is not one of the reader's own
   candidates → `ValueNotAdmitted` raised (rule 4: INFER chooses among what
   was admitted; widening the field is a second reader and belongs in
   ADJUDICATE).
4. The witnesses are partitioned by provenance closure
   (`independent_groups`): two witnesses resting on a shared row are one
   signal. The partition is recorded on the verdict's `correlated`.
5. The harness — not the rule — builds the verdict: `decider="infer:<rule>"`,
   `detail["inferred"]=True`, the prior always in `basis`, the prior's
   candidates carried forward, `supersedes` pointing at the prior.
   `log.record` appends it; the narrowing stays on the record.

The report lists `inferred`, `skipped` with reasons, `stubs`, `disabled`
(a rule held back by its own switch, named with the flag) and `reach`
per rule — so a rule that was off, a rule that ran and found nothing, and
a page with nothing to infer are three different lines.

---

## 2. The rules, in the order they run (`infer.RULES`, registration order)

`run` iterates `RULES` as registered — there is no sort. The order is the
order of the `@rule` decorators in `inferences.py`.

| # | rule | target | scope | gate | reads |
|---|---|---|---|---|---|
| 1 | `collapse_duration_by_column` | duration | system | `OMR_INFER` (default ON) | onset_column, event, duration, glyph_box, glyph_owner |
| 2 | `collapse_duration_to_barline` | duration | system | `OMR_INFER` (default ON) | same; refuses a witness whose own length reached it through the meter |
| 3 | `collapse_slot_index_to_family_block` | slot_index | system | always on (promoted 0.2c; 25 of 25 against the print) | slot_index, instrument, clef_glyph |
| 4 | `fill_clef_gap` | clef | document | always on (promoted 0.2c) | clef, **slot_index**, instrument |
| 5 | `fill_part_key` | key_signature | document | `OMR_PART_KEY` (default ON) | key_signature, part_key, **slot_index**, margin_label |

Every rule is `sideways` (looks across siblings — the thing EVALUATE
structurally cannot do), states a `bound` and a
`why_witnesses_are_independent`, and `forbids_argmax` (a rule may report
`support` and may never choose by it; asserted by the suite). No stubs.

---

## 3. Does order matter?

Inside INFER, in exactly one place, and it is carried by file order —
but, unlike EVALUATE before 2.63, **it is pinned and says so.**

- Rules 4 and 5 read `Q.SLOT_INDEX` through `log.verdict`, which returns
  the *latest* verdict on the subject — so a slot rule 3 inferred is what
  they see, and a staff whose slot was NARROWED gets its clef gap filled
  or its key filled only because rule 3 ran first. `test_infer_clef_gap`
  (`:429`) and `test_staged_key_by_part` (`:472`) each assert the index of
  the slot rule is below theirs in `RULES`. The dependency is real, the
  guard is a test on registration order, and both tests name that as the
  mechanism.
- Rules 1 and 2 share a target and cannot interfere: a duration rule 1
  collapses is DECIDED by the time rule 2 looks and is skipped
  `prior_is_decided`. Their populations are disjoint by construction
  (has a next onset in the bar / runs to the barline).
- Nothing reads an inferred `clef` or `key_signature` inside this stage;
  the consumers are in the second EVALUATE pass.

**Across the stage boundary — what the bounded second pass can reach.**
`run_over` fires an EVALUATE rule only where its cause or a declared extra
read is an inferred verdict. From each target:

| inferred target | EVALUATE rules that can fire on it | how |
|---|---|---|
| `clef` | `restate_pitch`; `move_glyph` | cause; `reads_beyond_cause` (the winning staff's clef — declared exactly so a glyph moved onto a repaired staff is not half-repaired) |
| `key_signature` | `respell_accidental` | cause |
| `slot_index` | none | no rule has it as cause; `name_part` reads it only into `basis` |
| `duration` | none | the meter rules' cause is `meter`, not `duration` |

The last row is a property worth stating plainly: an inferred duration is
not re-checked against the bar by `reconcile_duration`. That is
consistent — the inference chose among candidates the reader admitted,
and the bar-sum rule already ran over those candidates in the first pass
— but it means the record carries no post-inference bar check. If one
is ever wanted it is a new rule with `cause=duration`, not a second pass.

**What cannot go wrong.** An inference cannot be unlabelled, cannot
overturn a DECIDED verdict, cannot propose a value outside the admitted
set, and cannot run before EVALUATE or on an open log — each by a raise
in the harness, not a convention. `Log.record`'s `UphillConsequence` is
live underneath.

---

## 4. Examination

**Should anything move?** No. The order is registration order, there is
one real dependency in it, and that dependency is pinned by two tests
that say "registration order" in their own words. The 2.63 lesson from
EVALUATE — a comment crediting the wrong mechanism — does not recur here:
the mechanism is named correctly where it is relied on.

**Should the order be declared rather than pinned?** Not worth it at five
rules. A declared `after=` field would replace two honest tests with a
field nobody reads; the tests are the declaration. Revisit if a sixth
rule reads a fourth target.

**Known, not new.** The two duration rules were never print-checked
(roadmap 2.3 switched them on by Sean's decision with three subjects
against the print). `fill_clef_gap`'s abstained-prior path has no
candidate set to bound it, so its bound comes from its own evidence (a
clef decided elsewhere on the same part, or the instrument's default
clef) — stated on the rule. `scoring_conflict` exists so nobody scores an
inference by the quantity it consumed.

---

## 5. What changed (this document only)

No code. `ASSUMPTIONS.md` gains A-INF-1, the registration-order fact
and its two pins, so the next reader does not have to re-derive it.
