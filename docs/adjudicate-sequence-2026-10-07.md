# The ADJUDICATE sequence — what runs, in what order, and which orderings are real

**Date:** 2026-10-07. **Path:** STAGED (`tools/omr/staged/adjudicate.py`,
`adjudicators/`, `pipeline.decide`). **Authority:** `adjudicate.ORDER` and
the `@decision` declarations; the derived table is
`python3 -m tools.omr.staged.inventory`, and the order check is
`inventory --check`. This document is a reading of the tree on that date;
where it and the tree disagree, the tree is right (CLAUDE.md rule 10).

Second of the per-stage sequence documents; GATHER is
`docs/gather-sequence-2026-10-06.md`.

---

## 1. What happens around the stage (`pipeline.decide`)

1. GATHER has frozen the log. `adjudicate.run` freezes it again if a caller
   forgot — ADJUDICATE may not gather.
2. `adjudicate.run` walks `ORDER` (§2). For each quantity it takes the
   registered decision, computes the decision's **domain** (`subjects_for`),
   and runs `adjudicate_one` on every subject in it (§1a).
3. The A/B divergence table, if `--against` was given, is computed **here**,
   before anything downstream can restate a value.
4. `--through adjudicate` returns here. Otherwise GROUPS runs (which
   witnesses agree, a report with no consumer by design), then EVALUATE.

### 1a. One decision on one subject (`adjudicate_one`)

1. Build an `Evidence` view of the frozen log for this subject. Every read
   the decision makes goes through it and is checked against the decision's
   declared `wants`; an undeclared read raises `UndeclaredEvidence`.
2. Call the decision. It returns a `Ruling`: a value, a reason word, the
   rows it `used`, optional `candidates` (a narrowing), optional `margin`.
   A stub, or a `None` return, becomes an abstention `not_implemented`.
3. The reason must be in the decision's declared `reasons`, or
   `UndeclaredReason` is raised.
4. **Margin floor** (COMPETITIVE decisions only — today just `clef`): a
   value whose margin is under the floor is dropped to `margin_below_floor`;
   if the ruling supplied candidates they survive as a NARROWED verdict
   rather than vanishing.
5. Outcome: a value → DECIDED; no value but ≥2 candidates → NARROWED;
   otherwise ABSTAINED (a single surviving candidate is not a narrowing).
6. The verdict's `basis` is the ancestor closure of every row it looked at;
   `missing` and `declined` record every quantity it asked for and did not
   get, so a decision that ran too early is visible on its own verdict.
7. `log.record` appends it. A second verdict on the same (subject,
   quantity) without `revises=` raises `AlreadyAdjudicated` — the
   single-pass regime is a property of the machine, not a promise.

---

## 2. The order (`adjudicate.ORDER`, 51 decisions)

The **verdict inputs** column is the other decisions whose *verdict* this
one reads (`ev.verdict`/`ev.verdicts`); GATHER rows are not listed. A blank
means its position is free. Derived from `REGISTRY` on 2026-10-07; the full
column set (domain, mode, every consumed row, who consumes it, legacy
sibling, checkability) is `inventory`'s table and is not repeated here.

| # | decision | scope | verdict inputs |
|---|---|---|---|
| | *document* | | |
| 1 | `movement_spans` | document | *(its own GATHER row, when `--movements` was given)* |
| | *structure* | | |
| 2 | `system_membership` | system | |
| 3 | `staff_group` | staff | |
| 4 | `measure_partition` | staff | |
| 5 | `staff_ordinal` | staff | |
| 6 | `system_staff_count` | system | |
| | *identity — before ownership and before the clef (A-ORDER-2)* | | |
| 7 | `instrument` | staff | staff_ordinal, staff_group |
| 8 | `slot_index` | staff | instrument, staff_ordinal, system_staff_count, staff_group |
| 9 | `part_partition` | document | slot_index, staff_ordinal, system_staff_count, instrument |
| 10 | `group_symbol` | system | staff_group, instrument, system_staff_count |
| | *header facts, with identity in hand* | | |
| 11 | `clef` (COMPETITIVE, margin floor) | staff | instrument |
| 12 | `keysig_marker_is_not_a_marker` | glyph | |
| 13 | `system_key` | system | clef, keysig_marker_is_not_a_marker |
| 14 | `part_key` | document | clef, keysig_marker_is_not_a_marker, system_key, slot_index, instrument, movement_spans |
| 15 | `key_signature` | staff | clef, keysig_marker_is_not_a_marker, system_key, part_key, slot_index, instrument |
| | *what a thing IS — before the questions that assume the answer* | | |
| 16 | `ledger_is_not_a_ledger` | glyph | |
| 17 | `notehead_is_not_a_notehead` | glyph | ledger_is_not_a_ledger, system_staff_count |
| 18 | `accidental_is_not_an_accidental` | glyph | |
| 19 | `rest_is_not_a_rest` | glyph | notehead_is_not_a_notehead |
| 20 | `arpeggiato_is_not_an_arpeggiato` | glyph | |
| 21 | `arc_is_not_an_arc` | glyph | |
| 22 | `dynamic_is_not_a_dynamic` | glyph | |
| 23 | `articulation_is_not_an_articulation` | glyph | |
| 24 | `flag_is_not_a_flag` | glyph | |
| 25 | `tuplet_marker_is_not_a_marker` | glyph | |
| | *ownership* | | |
| 26 | `glyph_owner` | glyph | instrument, clef, ledger_is_not_a_ledger |
| 27 | `arc_owner` | glyph | glyph_owner |
| 28 | `arc_kind` | glyph | |
| 29 | `tie_pair` | glyph | arc_kind, arc_owner, arc_is_not_an_arc, glyph_owner, notehead_is_not_a_notehead |
| 30 | `dot_role` | glyph | glyph_owner |
| 31 | `articulation_owner` | glyph | glyph_owner |
| 32 | `accidental_owner` | glyph | accidental_is_not_an_accidental, notehead_is_not_a_notehead, glyph_owner |
| 33 | `fermata_owner` | glyph | glyph_owner |
| 34 | `ornament_owner` | glyph | glyph_owner |
| 35 | `pedal_owner` | glyph | group_symbol, staff_group |
| 36 | `ottava_owner` | glyph | |
| | *rhythm* | | |
| 37 | `stem_direction` | glyph | |
| 38 | `notehead_is_a_whole_rest` | glyph | |
| 39 | `tuplet_ratio` | cell | tuplet_marker_is_not_a_marker |
| 40 | `duration` | glyph | dot_role, tuplet_ratio, stem_direction, flag_is_not_a_flag, arc_kind, group_symbol, staff_group, glyph_owner |
| 41 | `event` | cell | stem_direction |
| 42 | `meter` | system | duration, system_staff_count, event, measure_partition, movement_spans, notehead_is_not_a_notehead, **and the previous system's `meter`** (§3) |
| 43 | `onset_column` | system | event |
| 44 | `voices` | cell | stem_direction, event, onset_column, meter, duration |
| | *bars the detector left nothing in* | | |
| 45 | `unread_mark` | cell | onset_column |
| 46 | `empty_bar_whole_rest` | cell | |
| 47 | `notehead_position` | glyph | |
| | *after voices* | | |
| 48 | `wedge_anchor` | glyph | glyph_owner, voices |
| | *text* | | |
| 49 | `dynamic` | cell | glyph_owner, dynamic_is_not_a_dynamic, group_symbol, staff_group |
| 50 | `direction` | cell | |
| 51 | `printed_bar_number` | system | |

All 51 registered decisions are in `ORDER` and every name in `ORDER` is
registered (`inventory --check`). There are no stubs.

---

## 3. Does order matter?

Yes — but only in one way, and the stage already guards it twice.

ADJUDICATE reads a frozen log, so the order is free for every GATHER row:
a decision reading `Q.GLYPH_BOX` gets the same rows wherever it sits. The
order binds exactly where a decision reads another decision's **verdict**
(the column in §2). Everything in `ORDER`'s comments about "beside the
fermata" or "with the other text decisions" is kinship.

**The guards GATHER did not have:**

1. **Static.** `inventory --check` knows `ORDER` and every decision's
   `wants`, and reports a want that is a verdict of a decision later in
   `ORDER` in one line: *"X wants the VERDICT Y, which ORDER runs AFTER it
   — it will always read None"*. This caught `wedge_anchor` before
   `voices`, `meter` before `event`, and `onset_column` after `voices`,
   each time by the tool and not by review. ⚠️ It has a hole, found while
   writing this (§4): it classifies a want by who PRODUCES it, not by how
   the decision READS it, and a quantity that is both gathered and decided
   is exempt from the order check altogether.
2. **Runtime.** `Evidence.verdict` on a verdict that does not exist yet
   records the quantity in the verdict's own `missing`. A decision that
   runs too early abstains with the gap written on it. GATHER's
   `log.rows()` returns empty with no trace; this stage's reads leave one.

So a misorder here fails **quiet and visible**, where in GATHER it failed
quiet and invisible. That is why no `AdjudicateOrderError` is proposed.

**One edge the static check cannot see.** `meter` reads the *previous
system's* `meter` verdict for the carry (`rhythm.py`
`_adjacent_corroborated_cautionary` and the carry helpers at ~4416/4731,
`ev.verdict(Q.METER, subject=prev)`). That is a dependency *within* one
decision on the order its subjects are visited in, not between two
decisions, so `inventory` has nothing to compare. It holds because
`subjects_for` returns subjects in `Subject`'s own ordering — a frozen
dataclass ordered on (kind, page, system, …), numeric, so page 10 comes
after page 2 — and `log.record` writes each verdict before the next subject
is visited. If `subjects_for` ever shuffled, the carry would read `None`
and abstain with `meter` in `missing`: visible, not wrong.

**The dual quantities, and the two ways to get them wrong.** Five
quantities are both a GATHER row and a decision: `system_staff_count`,
`staff_ordinal`, `movement_spans`, `printed_bar_number`, `meter`.
`system_membership` (#2) declares `wants=(Q.SYSTEM_STAFF_COUNT, …)` and
reads it with `ev.rows` — the GATHER row from `gather_systems`, not #6's
verdict. A script that treats every want of a verdict-quantity as a
verdict edge therefore reports a backward edge that is not there (the
first draft of this document did). `inventory` avoids that false alarm by
calling such a want `both` — and then **never order-checks a `both`
want at all** (`inventory.py` ~496–514 and `_problems`, which tests only
`kind == "verdict"`). So the opposite mistake is invisible to it: a
decision that reads the *verdict* of a dual quantity from before that
decision has run. The §2 column above was derived from the bodies
(`ev.verdict`/`ev.verdicts` calls), which is the classification the check
should use.

---

## 4. Examination

**Should anything move?** No decision's position is wrong. Every verdict
edge points backward in `ORDER` (my script and `inventory --check` agree),
and every placement comment in `ORDER` that claims a dependency names a
real one. Positions that are genuinely free, by the tree's own account:
`keysig_marker_is_not_a_marker` could sit with the other refusals but is
placed above `clef` because its first consumer is #13; `empty_bar_whole_
rest`, `notehead_position`, `direction`, `printed_bar_number`, `ottava_
owner`, `arpeggiato_is_not_an_arpeggiato` read GATHER only and could sit
anywhere; `notehead_is_a_whole_rest` reads nothing from ADJUDICATE and is
placed early on principle ("what a thing IS before the questions that
assume it"), which is the right principle.

**Found: the static order check cannot fail on a dual quantity.** Run in
process on 2026-10-07 against `inventory.build()`'s own rows:

- control — `voices` moved ahead of `event`: reported (three lines:
  `event`, `onset_column`, `meter`). The check can fail.
- `slot_index` moved ahead of `system_staff_count`, whose VERDICT it reads
  (`identity.py:373`, `ev.verdict(Q.SYSTEM_STAFF_COUNT, …)`): the
  `system_staff_count` edge is **not reported** (only `instrument`, which
  the same move also crossed). The check passes on a real misorder.

Today every such read is correctly ordered (the §2 derivation agrees with
`ORDER`), so nothing is wrong on the tree; the guard just has no teeth for
eleven verdict reads of the five dual quantities (`identity.py:369,373`,
`notehead_precision.py:452,526`, `rhythm.py:3632,4326,4361,4416,4731,
5041,6085`, `header.py:636`). The runtime `missing` trace still covers
them.

*Built the same day (ROADMAP 2.62, Sean: "Yes"):* `inventory._body_reads`
walks the decision's body and helpers (the walk `_never_read` always did)
and also collects every `Q.X` passed to `.verdict`/`.verdicts`/`.admitted`;
each `consumes` entry carries `read_as_verdict`, and `_problems`
order-checks a want when it is a pure verdict OR read as one. `kind` still
says `both` for the dual quantities — the row-vs-verdict distinction is a
property of the reader, not the quantity. The control above is now
`test_a_late_verdict_read_of_a_BOTH_quantity_is_caught`, run RED first.

**Known, not new.** Two declarations are inert and recorded as such in
`inventory`'s known gaps: `tuplet_ratio` declares `beam_stroke` and never
reads it; `meter` declares `dossier_fact` and never reads it (no dossier on
the scan path by protocol). And `glyph_owner`'s scoring does not read
`notehead_is_not_a_notehead` even though it runs after it — the ordering
guarantees a refused glyph is never *written*, not that it cannot *win* a
contest (2.4a's own note).

**Stale text, fixed.** `ASSUMPTIONS.md` A-ORDER-1 said "the 21-item LIST"
(it is 51), and its "how to falsify" was "permute it" — `inventory --check`
has done that job statically since it existed, and the runtime `missing`
field does it per verdict. Updated to say so.

**The contrast with GATHER is the finding.** GATHER had the order rule
only in a docstring and no guard; ADJUDICATE has the rule in a tool and a
trace on every verdict. The 2.58 fix brought GATHER one step toward this
(one reader that raises). The general shape — a reader that can tell from
the record that its input never ran, and says so — is what GATHER's other
dependent readers (re-centre consumers, far-head) still lack.

---

## 5. What changed (this document only)

`ASSUMPTIONS.md` A-ORDER-1: the list size corrected, the two guards named
with the static one's hole, the within-decision carry edge recorded. The
order itself holds on the tree and no decision moved. The one code change
is ROADMAP 2.62 (§4): `inventory --check` now order-checks a verdict read
of a dual quantity.
