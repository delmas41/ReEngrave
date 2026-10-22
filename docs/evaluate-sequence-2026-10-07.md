# The EVALUATE sequence — what runs, in what order, and which orderings are real

**Date:** 2026-10-07. **Path:** STAGED (`tools/omr/staged/evaluate.py`,
`consequences.py`, `groups.py`, `pipeline.decide`). **Authority:**
`evaluate.DOWNHILL`, `evaluate.RULES` (the `@rule` registrations in
`consequences.py`, in file order) and `evaluate._pass`. This document is a
reading of the tree on that date; where it and the tree disagree, the tree
is right (CLAUDE.md rule 10).

Third of the per-stage sequence documents: GATHER
`docs/gather-sequence-2026-10-06.md`, ADJUDICATE
`docs/adjudicate-sequence-2026-10-07.md`.

---

## 1. What happens around the stage (`pipeline.decide`)

1. ADJUDICATE has run and the divergence table, if any, is taken.
2. **GROUPS** (`groups.run`) — between ADJUDICATE and EVALUATE, and the
   position is the claim: it reports whether several witnesses to ONE fact
   agree, *as adjudicated*, before any consequence restates a value. Six
   declared redundancies: `meter_across_staves` (off the meter-template
   rows), and `measure_count / instrument / clef / staff_group /
   key_signature _across_systems` (off verdicts). The report has **no
   consumer**, deliberately (A-WIT-6): seeing that witnesses disagree is
   one job and acting on it is another. A disagreement implicates the
   whole group and never names a culprit.
3. **EVALUATE** (`evaluate.run`) — one pass over the rules, §2.
4. `--through evaluate` returns here. Otherwise INFER runs, and then a
   **second, bounded EVALUATE pass** (`evaluate.run_over`) fires only the
   rules whose cause, or a verdict they declare they also read
   (`reads_beyond_cause`), is one of the verdicts INFER just wrote. Same
   loop body, same order; one pass, no fixpoint. Its report rides inside
   `inference` as `reevaluation`. (The INFER document will take that up.)

### 1a. One rule at one subject (`evaluate._pass`)

For each rule in execution order, for each subject at the rule's scope:

1. Find the **cause** verdict at the subject or any ancestor
   (`_cause_for`): a rule's scope is its *effect's* scope and the cause
   may be coarser — the meter is a SYSTEM verdict driving a CELL rule.
   An exact-subject lookup once made every such rule silently dead.
2. Skip, and say why, if the cause is absent (`cause_absent`), abstained
   (`cause_abstained` — a consequence of a fact nobody settled must not
   fire on a default) or narrowed (`cause_narrowed` — reported apart from
   an abstention because a later rule could choose among the survivors).
3. On the bounded second pass only: skip unless the cause or a declared
   extra read is one of the inferred verdicts
   (`not_downstream_of_an_inference`).
4. Call the rule. It returns the verdicts it wrote; each is recorded with
   `supersedes` naming what it replaces. `Log.record` refuses a verdict
   that supersedes something in its own `basis` (`UphillConsequence`) —
   the fixpoint refused by the machine — unless the rule declared
   `single_pass` and the verdict carries `single_pass_revision`
   (`reconcile_duration` alone, A-DUR-3).
5. Every firing is appended to the report as
   `(consequence, subject, effect)`; a stub is listed, not run.

---

## 2. The order

### 2a. `DOWNHILL` — the direction

A rule's `cause` must sit strictly earlier in this list than its
`effect`, checked **at import** (`check_downhill` raises `UphillRule`):

```
system_membership, staff_group, measure_partition, instrument, slot_index,
part_partition, part_name, clef, key_signature, glyph_owner, pitch,
accidental_owner, accidental, meter, duration, rest_is_not_a_rest
```

### 2b. The rules, in the order they run

`_pass` sorts `RULES` by **the DOWNHILL rank of the cause**, and Python's
sort is stable — so rules with the same cause run in **registration
order**, which is their order in `consequences.py`. Ten rules:

| # | rule | cause → effect | scope | reads besides the cause | bound (short) |
|---|---|---|---|---|---|
| 1 | `name_part` | instrument → part_name | staff | `slot_index` | writes a name; changes no note |
| 2 | `join_parts` | part_partition → part_name | document | — | **stub** (declared, never run) |
| 3 | `restate_pitch` | clef → pitch | staff | `notehead_position` (2.56), `notehead_staff_position`, existing `pitch` | one pitch per head with a position and no pitch; an abstained clef gives none |
| 4 | `respell_accidental` | key_signature → accidental | staff | `pitch`, existing `accidental` | re-spells the letter only; never re-derives the key |
| 5 | `move_glyph` | glyph_owner → pitch | glyph | `clef` of the winning staff, `far_head_owner_ledger`, `glyph_band_distance` | restates one glyph's pitch on the staff that won it; loser superseded, not deleted |
| 6 | `apply_printed_accidental` | accidental_owner → accidental | glyph | `pitch`, `glyph_owner`, `glyph_box`, existing `accidental` | the owned head and later same-letter-and-octave heads in the cell; never leftward |
| 7 | `size_measure_rest` | meter → duration | cell | `duration`, `glyph_owner` | a bar whose only standing duration is one dotless `restWhole`; takes the bar's length |
| 8 | `reconcile_chord_duration` | meter → duration | cell | `duration` | a NARROWED head settles to its one DECIDED stem-mate's beam count, only to a value it already offered |
| 9 | `reconcile_duration` | meter → duration | cell | `duration`, `event`, `glyph_owner` | ±1 beam level on at most one note; the bar must land exactly; unique answer; `single_pass` |
| 10 | `reinstate_rest_between_staves` | meter → rest_is_not_a_rest | glyph | `duration`, `event`, `voices`, `stem_direction`, `glyph_owner`, `glyph_band_distance`, existing `rest_is_not_a_rest` | a doubly refused rest group goes back on the one staff whose shortfall equals it |

Rules 7–10 share the cause `meter` (rank 13) and are ordered among
themselves by file position alone: lines 167, 358, 453, 1295.

---

## 3. Does order matter?

Yes, in two ways, and the stage guards one of them well and the other
by accident.

**Across causes — guarded.** A rule reading a verdict another rule
*writes* must run after it: `respell_accidental` (4) reads `pitch`,
written by `restate_pitch` (3); `apply_printed_accidental` (6) reads
`pitch` and `glyph_owner`; the meter rules read `duration`. All of these
hold because the sort key is the cause's DOWNHILL rank and the written
quantities sit between. The one ordering that *loses* information is
known and recorded: `move_glyph` (5) rewrites a moved glyph's pitch after
`respell_accidental` (4) has already spelled it, so the sounding pitch of
a moved glyph is routed at EXPORT rather than revised here (CLAUDE.md
§4c; pinned by `test_infer_clef_gap` through `DOWNHILL`).

**Within a cause — guarded by file order only.** The four meter rules
have real dependencies among themselves:

- `reconcile_chord_duration` (8) must run before `reconcile_duration` (9):
  a chord member it settles from NARROWED to DECIDED is what the bar sum
  then reads. **Pinned** — `test_staged_chord_duration` asserts the file
  order within the meter-caused rules and says in its docstring that file
  order is the tie-break.
- `reinstate_rest_between_staves` (10) must run after `reconcile_duration`
  (9): it reads the bar's completeness, which (9) may just have changed.
  **Not pinned by any test.** And the comment that claims to guard it —
  on `Q.REST_IS_NOT_A_REST` in `DOWNHILL`: *"Downhill of `Q.DURATION` on
  purpose … Placing this any earlier would let it fire on a total
  `reconcile_duration` was about to correct"* — attributes the ordering
  to the **wrong mechanism**. `DOWNHILL` position of an *effect* has no
  bearing on when a rule runs; only the *cause's* rank does, and all four
  share one. What actually orders (10) after (9) is that its `@rule` sits
  at line 1295. Someone who moved the function up the file to keep the
  rest rules together would reorder execution and nothing would say so.
- `size_measure_rest` (7) before `reconcile_duration` (9): harmless
  either way today — `reconcile_duration` skips rests when choosing what
  to re-read and a lone-rest bar has no note to change — but file order
  is still the only thing deciding it.

**What cannot go wrong.** Uphill edges are refused twice: at import
(`UphillRule`) and at record time (`UphillConsequence`). There is no
`while` anywhere and the docstrings say there must never be one.

---

## 4. Examination

**Should anything move?** No rule runs in the wrong place. The execution
order is right; what is wrong is the *reason the tree gives* for part of
it, and the absence of a guard on one edge.

**Finding.** `DOWNHILL` reads as if it orders rules; it orders *causes*.
Two rules with one cause are ordered by where they were typed. One of the
three such edges is pinned, one is documented against the wrong
mechanism, one is unguarded and harmless. The misleading comment is the
same shape as GATHER's "only three forced edges": a sentence a reader
would reorder on.

*Built the same day (ROADMAP 2.63, Sean: "Yes"):* `evaluate.execution_order()`
keys the stable sort on `(DOWNHILL.index(cause), DOWNHILL.index(effect))`
and `_pass` consumes it — so the `Q.REST_IS_NOT_A_REST` comment is now
true, since `duration` sits above `rest_is_not_a_rest`. Registration
order still decides the one pair that shares both cause and effect
(chord before reconcile), which `test_staged_chord_duration` pins by file
order on purpose. On the real registration the order is unchanged; the
change is what guarantees it. `test_staged_evaluate_order.py`, run RED
first: the documented sequence; the control (meter rules registered
reversed → the reinstatement still last, where the old key put it first);
the shared pair still follows registration; `_pass` calls the rules in
`execution_order`'s order, proved by behaviour. The `DOWNHILL` comment is
rewritten to say what governed before and what governs now.

**Known, not new.** `join_parts` is a declared stub and the only one.
`restate_pitch` emits nothing for an abstained clef (A-EVAL-2, superseded
in principle by Sean's own procedure but not rebuilt). Four rules declare
`reads_beyond_cause` for the bounded second pass; the others read only
their cause and gathered rows, by declaration.

---

## 5. What changed (this document only)

`ASSUMPTIONS.md` A-EVAL-1 gains the tie-break fact. ROADMAP 2.63 (§4) is
the one code change: the effect's rank enters the sort, so DOWNHILL's
own comment is now the reason the reinstatement runs last.
