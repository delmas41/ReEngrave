# Who may override whom -- the STAGED override and dependency map (ROADMAP 2.163)

**Date:** 2026-10-17. **Path:** STAGED only. **Read from:** main `2320c2ea`
(`tools/omr/staged/`), the night records' facts
(`library/_shared-records/overnight-20261016-night/`, summary and
`regather-report-facts/*.facts.json`; the 300 MB records were not loaded) and
`benchmarks/omr-regather-report-2026-10/20261016-night/*.report.md`. No code
changed, no gather, no replay. Extends the 2.149 audit
(`benchmarks/omr-bar-sum-holdout-2026-09/FINDINGS.md` §2.149) and the 2.154-1
decider table. Where this document and the tree disagree, the tree is right.

**The rules it is checked against.** CLAUDE §3 (EVALUATE writes only what
follows; INFER chooses only among a reader's own candidates and never overturns
a DECIDED verdict; EXPORT never argmaxes a narrowing), CLAUDE §4 (READ / GUESSED
/ UNREAD; bar arithmetic may CONFIRM, never SUPPLY, and never shortens a note
with no flag and no beam seen; the two exceptions are 2.154's bare stem and
2.158's lone event, both written GUESSED), DECISIONS 2026-10-16 (the note
reading order: notehead, stem, beam or flag, chord / shared stem, slash or
anything else -- a later step never overturns an earlier one) and DECISIONS
2026-10-17 (a bar holding an undecided note has no known length: it may not
vote against a meter, refute a carry or undo a bar-sum move).

**How a verdict is changed at all.** `record.Log.record` refuses a second
verdict on one (subject, quantity) unless it names `supersedes=`, and refuses a
superseding verdict that reaches its own prior through its other inputs
(`UphillConsequence`) unless the rule declares `single_pass`. So the complete
list of "a later step changes an earlier verdict" is the list of `supersedes=`
sites (18 in `tools/omr/staged/`, 2 of them `single_pass_revision=True`), plus
the places that never write a verdict but READ one differently from how it was
decided (a narrowing taken at its first candidate; a chord's mode at EXPORT).
Both kinds are below.

Marks: **OK** obeys the rules; **VIOLATION** names the rule; **UNCLEAR** two
rulings or two readings fit. "Flag" is the gate and its default on main;
"always" means no flag. Reach is from last night's run unless a date is given.

---

## 1. ADJUDICATE

Order (live `adjudicate.ORDER`): ... `notehead_is_not_a_notehead` ...
`glyph_owner` ... `dot_role` ... `stem_direction` ... `duration` > `head_stem` >
`stem_value` > `event` > `meter` > `onset_column` > `voices` ... Note that
`duration` (reading-order steps 1-3) runs BEFORE `head_stem` (step 2, which
stem) and `stem_value` (step 4); the stem's value reaches the duration only in
EVALUATE (`share_stem_value`).

| # | file:function | changes | on what evidence | flag (default) | mark |
|---|---|---|---|---|---|
| A1 | `adjudicate.py:adjudicate_one` (856-870) | would supersede a prior verdict of the same decision when `spec.revises` is set | -- | no `@decision` sets `revises`; inert | OK (dead path; keep it dead) |
| A2 | `adjudicators/ownership.py:reconcile_group_owners` (5218), run right after `glyph_owner` | a mark-group member's DECIDED `glyph_owner` is overruled by the group's ledger-backed owner (`overruled_by_ledger`); abstained members adopt it | the other members' DECIDED ledger verdicts (`LEDGER_OWNER_REASONS`) | `OMR_MARK_GROUPS` (ON) | OK -- connects a decision; the ledger names the owner (page-facts §5); never a refused box |
| A3 | `ownership.py:reconcile_articulation_twins` (4034), after `articulation_owner` | a DECIDED owner becomes ABSTAINED `duplicate_of_twin` / `lost_to_twin` / `twin_owners_disagree` | one printed mark, two owners; nearer / rank / lower staff (Sean 2026-10-11) | always | OK |
| A4 | `ownership.py:reconcile_dot_owners` (5354, 5400), after `dot_role` | a dot's (and its notehead-class twin box's) DECIDED `glyph_owner` is re-pointed to its note's owner | DECIDED `dot_role` + the head's owner | `OMR_DOT_FOLLOWS_NOTE` (ON) | OK -- a dot follows its note |
| A5 | `adjudicators/aug_dot_join.py:reconcile_unjoined_dots` (465, 489), after `duration` | a DECIDED plain duration becomes NARROWED {plain, dotted}; a narrowing is widened with dotted candidates | a dot box (or a dot-shaped refused head box, 2.151) beside the head whose position cannot tell | `OMR_AUG_DOT_JOIN` (ON), `OMR_DOT_BOXED_AS_A_HEAD` (ON) | OK by ruling (2.127, 2.151; Sean 2026-10-14/16). Note the move class: a later reading may WIDEN a DECIDED value to a narrowing (never decide it). Brahms 38 `dot_seen_beside_a_plain_note` |
| A6 | `adjudicators/rhythm.py:adjudicate_duration` (3865 head-first block; late `head_fill_from_ink` at ~4809) | the head's fill is read first (2.148 / 2.159) only inside a head-sized or located box; every other box still reaches the LATE hollow reading after beams / flags / tip, which can only narrow {black, half, whole} | 2.148 slit, 2.23 window | `OMR_HEAD_FILL_FIRST` (ON), `OMR_HEAD_FILL_LOCATED_BOX` (ON) | UNCLEAR -> **2.161 in flight** (box gate / no stem touching). Litolff 114, Brahms 231 narrowed `head_fill_from_ink`; 2.159: 283 of 345 are refused non-notes |
| A7 | `rhythm.py:adjudicate_duration` `open_head_flag_contradiction` (4362), `second_hollow_contradicted_by_marks` (4295), `whole_class_filled_on_a_stem` | a head read OPEN at step 1 is narrowed / abstained because a flag or beam was read on its stem (step 3) | flag / beam rows | always | VIOLATION (reading order: step 3 reopens step 1) -- small: Litolff 4 / 8, Brahms 12 / 11 |
| A8 | `adjudicators/stem_value.py:adjudicate_stem_value` (763-936) | the stem's base is the HOLLOW mates' (2.0) even beside a DECIDED filled mate; a DECIDED mate's value outranks a mate's narrowing; a beam at the tip against a hollow head narrows (`hollow_head_on_a_beamed_stem`) | the other heads' DURATION verdicts on the same `Q.HEAD_STEM` | always (`OMR_OWN_STEM_UNISON_BOTH` ON governs membership) | UNCLEAR -- 2.149 #4. Sean 2026-10-09 ("one stem one value, no exceptions", his tiles 3/4/6/8/14) vs 2026-10-16 (step 4 never overturns step 1). It decides, it does not narrow, where two decided fills disagree (rule 8) |
| A9 | `rhythm.py:_carry_meter` / `_corroborate` / `_bar_lengths_for` (5764) and `_meter_from_bars` (7550), inside `adjudicate_meter` | a carried meter is REFUSED (`carry_outweighed_by_the_bars`, `carry_not_corroborated`) or a meter is NAMED from this system's bars; the bar lengths count a NARROWED note at `candidates[0]` | DURATION verdicts of the system's bars (whole-rest bars excluded) | always (`OMR_METER_CARRY` / `OMR_METER_FROM_BARS` were removed, ON since 2026-09-15) | VIOLATION (DECISIONS 2026-10-17) -> **2.162 in flight** (its branch touches `rhythm.py` and `consequences.py`). Brahms last night: 6 of 53 systems abstained (3 + 3), 710 bars then judged by the file's carried meter; under 2.153 ON, 88 whole rests written at 4 beats |
| A10 | `rhythm.py:adjudicate_voices` | reads durations and the meter to split voices; writes `Q.VOICES`, changes no duration | -- | always | OK (consumer, no override; `_voice_count` feeds E6) |

## 2. EVALUATE

Order (live `evaluate.execution_order()`): `name_part` > `restate_pitch` >
`respell_accidental` > `move_glyph` > `apply_printed_accidental` >
`share_stem_value`[single_pass] > `size_reinstated_rest` > `size_unboxed_rest`
> `size_head_ink_rest` > `size_measure_rest` > `reconcile_chord_duration` >
`reconcile_duration`[single_pass] > `reinstate_rest_between_staves` >
`pair_word_and_dynamic`. The four meter-caused rules are ordered by FILE
position only (evaluate-sequence §3). A bounded second pass (`run_over`) fires
after INFER on the inferred verdicts.

| # | file:function | changes | on what evidence | flag (default) | mark |
|---|---|---|---|---|---|
| E1 | `consequences.py:share_stem_value` (604; `stem_value_follows`) | a head's DECIDED or NARROWED duration is REWRITTEN to the stem's `written` / `dots` / `beam_levels` AND `head_fill` | a DECIDED `Q.STEM_VALUE` (A8) | always; `single_pass_revision=True` | UNCLEAR, same question as A8 (2.149 #4): step 4 overwrites steps 1-3 including the fill. Reach: EVALUATE-decided durations Litolff 1,517 / Brahms 2,423 last night, of which `reconcile_duration` is 126 / 283 and the rest is stem sharing + rest sizing (not split in the facts; counting the split needs the record) |
| E2 | `consequences.py:size_measure_rest` (225; `whole_rest_means_the_bar`) | a lone DECIDED `restWhole` takes the bar's length | `_bar_beats_at` (the meter in force); DECIDED removals only (`_left_the_bar`) | always | OK (convention; it reads the meter's length, never a sum) |
| E3 | `size_reinstated_rest` / `size_unboxed_rest` / `size_head_ink_rest` (768-896) | a reinstated rest gets a duration | its own rest verdict | always | OK (prior is normally None) |
| E4 | `consequences.py:reconcile_chord_duration` (680; `chord_mate_shares_the_stem`) | a NARROWED head is DECIDED to the one candidate whose beam level its single DECIDED stem-mate has | two durations on one `Q.STEM` row | always (cause `meter`, reads no meter) | OK (connects within candidates; refuses `head_fill_from_ink` triples) |
| E5a | `consequences.py:reconcile_duration` (1015; `meter_reconciliation`) PICK | one NARROWED event settled to the candidate that lands the bar | the bar sum against `_bar_beats_at` | `OMR_BAR_SUM_CONFIRM_ONLY` unset = arm a (ON): refused whenever a narrowed note stands in the bar, except a bare stem's unbeamed value | OK since 2.154 (Sean's exception) |
| E5b | `reconcile_duration` MOVE via `_admitted` (1419) | a DECIDED note's beam level is moved +/-1 when the bar then lands uniquely; `_shortens_without_evidence` is applied to NARROWED candidates only, so a DECIDED quarter with no flag and no beam seen can be made an EIGHTH by the bar | arithmetic alone (missed-rest ink witness for a lengthening only) | arm a leaves it ON; arm b (`all`) OFF | **VIOLATION (CLAUDE §4: the bar never supplies, never shortens a note with no flag and no beam seen)**. Reach: `reconcile_duration` blue 126 Litolff / 283 Brahms last night (picks + moves); on 20261014 the MOVES were 78 / 104, of them 70 / 88 shortenings (holdout FINDINGS 2.154-2). Not in flight (arm b was measured: fixes 4, breaks 3) |
| E5c | `reconcile_duration` per-head loop (`for note in notes`, 1160-) | a DECIDED chord's heads are searched one at a time, so ONE head of a decided chord can be moved alone | arithmetic | as E5b | VIOLATION (one stem one value, Sean 2026-10-09) -- a subset of E5b |
| E6 | `consequences.py:reinstate_rest_between_staves` (2099) via `_bar_total_excluding` (1966) | a refused rest is reinstated where the staff's bar is short by the group's length; the bar total counts a NARROWED note at `candidates[0]` | bar sum x voice count | always; NOT under `OMR_BAR_SUM_CONFIRM_ONLY` | VIOLATION (DECISIONS 2026-10-17; latent: 0 verdicts in the night records, 2.154-1) -> belongs to **2.162** |
| E7 | `restate_pitch`, `move_glyph` (1469), `respell_accidental`, `apply_printed_accidental._supersede` (1811) | pitch / accidental superseded on a clef, owner or key change | the cause verdict | always | OK (downhill consequences; no note value) |
| E8 | `evaluate.run_over` after INFER (pipeline.py:246) | `share_stem_value` may re-fire on an INFER-guessed duration (it declares its own duration as a read): the GUESSED verdict is replaced by a DECIDED `stem_value_follows` | a DECIDED stem value | always | OK, noted: the guess label is lost, but the replacement rests on a decided reading; `reconcile_duration` cannot re-fire here (its cause is `meter`) |

## 3. INFER

Every proposal goes through one guard, `infer._admit` (713): prior must exist
and be NARROWED (never DECIDED or ABSTAINED), the value must be one of the
prior's candidates (`ValueNotAdmitted`), the prior is always in the basis, the
candidates travel forward, `inferred: True` is stamped by the harness.

| # | file:function | changes | on what evidence | flag (default) | mark |
|---|---|---|---|---|---|
| I1 | `infer.py:_admit` (713) | the only writer | -- | `OMR_INFER` (ON) | OK -- this is the model guard |
| I2 | `inferences.py:collapse_bare_stem_by_bar` (2181) + `_bare_stem_confirmations` | a bare stem's narrowing to its UNBEAMED value where the bar lands | bar arithmetic; declines `meter_not_from_the_print`, `meter_rests_on_these_bars`, `decided_neighbour_rests_on_the_narrowing`, tuplets, ungrouped events | `OMR_BARE_STEM_BAR` (ON) filtered by 2.154 | OK (Sean's exception, GUESSED). Brahms 14, Litolff 0 |
| I3 | `inferences.py:collapse_narrowed_by_bar` (2229) + `lone_event_decline` (2079) | bare-stem confirmations, and a LONE event's one candidate that fills a printed-rooted bar (`lone_event_fills_bar`) | as I2; one event, no rest, meter reaches the print | `OMR_NARROWED_BAR` (ON), `OMR_LONE_EVENT_FILLS_BAR` (ON) | OK (Sean's exception, GUESSED). Litolff 44, Brahms 55 |
| I4 | `collapse_duration_by_column` / `collapse_duration_to_barline` (366, 466) | a narrowing to the length a neighbour staff read at the same onsets | neighbour durations; refuses meter-derived witnesses (`_witness_is_meter_derived`) | `OMR_INFER` (ON) | OK. Litolff 4 / 2 |
| I5 | `collapse_arc_ink_not_beam` (2309) | a bare stem's unbeamed candidate where every refused stroke is slur / tie ink | arc verdicts, tip window | `OMR_ARC_INK_NOT_BEAM` (ON) | OK (2.121) |
| I6 | `fill_clef_gap`, `fill_part_key`, `collapse_slot_index_to_family_block` | clef / key / slot where the reader abstained | other staves' verdicts | always / `OMR_PART_KEY` (ON) | OK. Neither the clef nor the key reader anywhere reads a duration (checked: `adjudicators/{clef,key_slots,header,identity}.py`, INFER `reads=`) |
| I7 | `collapse_dynamic_by_ink` | -- | -- | `OMR_DYNAMIC_INK_PICK` (OFF) | OK |

## 4. EXPORT

| # | file:function | changes | on what evidence | flag (default) | mark |
|---|---|---|---|---|---|
| X1 | `export.py:_bar_holds_out` (per bar) and `_partial_bar_plan` (5473; 2.117) | a bar whose written events do not fill the meter is HELD or written PARTIAL with a red gap; a NARROWED note is refused first (`duration_narrowed`: Litolff 319, Brahms 1,242) so it is never summed | `_bar_quarters(meter)` | `OMR_PARTIAL_BARS` unset = on | OK (a bar with a narrowed note is marked, never decided) |
| X2 | `export.py:_events` (3382) -> `voicing.group_chords_in_measure` (voicing.py:112); mirrored by `consequences._event_totals` (501) | a chord's duration is the MODE of its heads' durations where they disagree | an argmax | always | **VIOLATION (CLAUDE §3: EXPORT never argmaxes; a disagreement on one stem is a narrowing)**. `share_stem_value`'s own docstring names it. Reach bound: stem values NARROWED (`stem_levels_unread`) Litolff 124, Brahms 818 -- the chords whose heads may still disagree |
| X3 | `export.py` `_lone_whole_rest_is_the_bar`, `meter_at(... in_force)`, `lilypond.py` `OMR_LILY_CARRIED_METER_REST` | a whole rest and the held-bar test use the meter in force in the FILE (the last written `<time>`), also on a system whose own `meter` verdict ABSTAINED (`meter_carried_in_file`) | the file's carry | always / ON | UNCLEAR: page-facts say a meter holds until the printed return, so carrying in the file is the convention; but a system ADJUDICATE refused (`carry_outweighed_by_the_bars`) is then judged by the meter it refused, with nothing marked. Brahms 710 bars judged on a carried meter (the abstained-system share needs the record) |
| X4 | `export._place_notes` honours DECIDED refusals; `_drop` ledger | nothing re-decided | -- | -- | OK |

## 5. GATHER

GATHER decides nothing, but one step forecloses a later reading:
`gather._owner_marks_for_cell` / `line_detection` `refuse_owned` deletes any
stroke >= 0.8 inside a rest-class box before `Q.STEM` exists (holdout FINDINGS
2.150-1 R2). A stem boxed `restQuarter` loses its stem; 2.150b now refuses most
such boxes as rests, but *"the stem the false box deleted is NOT restored"*.
Litolff 58 / Brahms 126 narrow `restQuarter` boxes (2.150-2). UNCLEAR -- not an
override of a verdict, but evidence removed before step 2 can read it; 2.150
proposal 2, not built.

---

## 6. Every consumer of a bar's length or sum

| consumer | stage | takes a NARROWED note as | guarded by |
|---|---|---|---|
| `rhythm._bar_lengths_for` -> `_corroborate` (carry) and `_bars_opinion` (meter from bars) | ADJUDICATE `meter` | `candidates[0]` | nothing -> A9, 2.162 |
| `rhythm.adjudicate_voices` | ADJUDICATE | its standing verdict | (splits only) |
| `consequences.size_measure_rest` | EVALUATE | not summed (reads the meter's length) | -- |
| `consequences.reconcile_duration` | EVALUATE | `candidates[0]` in the total, then REFUSES the bar under arm a unless every narrowed note is a bare stem | 2.154 arm a |
| `consequences._bar_total_excluding` -> `reinstate_rest_between_staves` | EVALUATE | `candidates[0]` | nothing -> E6 |
| `inferences.solve_bare_stem_bar` (both bar rules, `lone_event_decline`) | INFER | an unknown with its candidate lengths (never one value) | printed-meter root, closure guards, 2.154 filter |
| `export._bar_holds_out`, `_partial_bar_plan`, `_lone_whole_rest_is_the_bar` | EXPORT | refused before summing (`duration_narrowed`) | X1 |
| `regather_report` / coverage counters | report | as EXPORT | -- |

## 7. Every place a value is copied between notes

| copier | direction | what is copied | mark |
|---|---|---|---|
| `stem_value.adjudicate_stem_value` -> `share_stem_value` | stem -> every head on it | `written`, `dots`, `beam_levels`, **`head_fill`** | UNCLEAR (A8 / E1) |
| `reconcile_chord_duration` | decided mate -> narrowed mate | beam level only, within candidates | OK |
| `reconcile_duration` chord units (`_narrowed_chords`, `_common_options`) | the bar -> every head of a wholly-narrowed chord | one landing shared | OK under arm a (bare stems only) |
| `solve_bare_stem_bar` / `lone_event_decline` | the bar -> every head of one event | one length common to all members | OK (GUESSED) |
| `voicing.group_chords_in_measure` / `_event_totals` | heads -> the event | the MODE | VIOLATION (X2) |
| `reconcile_dot_owners`, `reconcile_group_owners` | note -> dot; group -> member | the owner | OK |

## 8. Does the meter, key or clef depend on note durations?

Only the meter: `adjudicate_meter` reads DURATION through `_bar_lengths_for`
(A9) and `adjudicate_voices` reads both. The clef (`adjudicators/clef.py`,
`fill_clef_gap`) and the key (`key_slots.py`, `header.py`, `system_key`,
`part_key`, `fill_part_key`) read no duration, event or bar sum. The meter's
dependence is the one that produced Sean's "measure math overriding the
meter" (DECISIONS 2026-10-17).

---

## 9. Dependency cycles (A reads B, B reads A)

1. **meter <-> duration.** `adjudicate_meter` reads the bars' DURATIONS to
   corroborate or refuse a carry (A9); `size_measure_rest`, `reconcile_duration`
   and the INFER bar rules read METER and supersede DURATION. Broken by stage
   order (ADJUDICATE votes once, EVALUATE repairs once), by `_corroborate`
   never reading a whole-rest bar, by `reconcile_duration`'s `single_pass=True`
   and by INFER's `meter_rests_on_these_bars` closure guard. The guard that is
   MISSING is on the first leg: a narrowed note enters the meter's sum at its
   first candidate (2.162).
2. **stem_value <-> duration.** `adjudicate_stem_value` reads its members'
   DURATIONS; `share_stem_value` writes every member's DURATION from it
   (`single_pass`); then `reconcile_duration` may move ONE head of a decided
   chord (E5c), so the heads of one stem can disagree again after they were
   made to agree. `_event_totals` then takes the mode (X2).
3. **duration -> dot -> duration.** `dot_role` (reads `glyph_owner`) feeds
   `_attached_dots` inside `adjudicate_duration`; `reconcile_unjoined_dots`
   then re-widens the duration for a dot the join missed. One pass each way;
   no loop, but two readers of one dot.
4. **INFER guess -> EVALUATE decided.** `run_over` lets `share_stem_value`
   replace an INFER guess with a DECIDED `stem_value_follows` (E8). Not a
   cycle; a label change.
5. **ADJUDICATE abstains the meter -> EXPORT carries it anyway** (X3): the
   refusal in A9 and the carry in the file are two readers of one fact with
   two answers, the same shape as 2.79's `_bar_beats_at` finding.

---

## 10. Violations, ranked by whole-movement reach

Reach is last night's count (20261016-night) unless dated; "bound" is an upper
bound because the facts files do not split EVALUATE's durations by decider.

| rank | item | rule broken | reach (Litolff / Brahms) | in flight? | one-line fix |
|---|---|---|---|---|---|
| 1 | E5b `reconcile_duration` MOVES a DECIDED value, including a quarter to an eighth with no flag and no beam seen (`_admitted` skips `_shortens_without_evidence` for DECIDED notes) | §4 bar sum never supplies / never shortens without evidence | 126 / 283 `reconcile_duration` guesses written (picks + moves); 2026-10-14 moves 78 / 104, shortenings 70 / 88 | no (2.154 arm b parked) | in `_admitted`, offer a DECIDED note `old+1` only where `_eighth_evidence(note)` is non-empty; keep `old-1` |
| 2 | A9 the meter carry is refused, or a meter named, by bar sums that count a NARROWED note at `candidates[0]` | DECISIONS 2026-10-17 | Brahms 6 of 53 systems abstained -> 710 bars judged on the file's carry; under 2.153 ON 88 whole rests at 4 beats | **yes, 2.162** | in `_bar_lengths_for`, a bar holding a NARROWED note contributes no length (or a min..max range that may only agree) |
| 3 | A8 + E1 the stem's value overwrites a DECIDED head fill (step 4 over step 1), deciding where two decided fills disagree | reading order 2026-10-16 (vs Sean 2026-10-09 "no exceptions") | <= 1,391 / 2,140 EVALUATE durations not from `reconcile_duration` (stem sharing + rest sizing, unsplit) | no | in `adjudicate_stem_value`, where a DECIDED hollow and a DECIDED filled head share one stem, NARROW the stem value (`stem_fills_disagree`) instead of taking the hollow; `share_stem_value` then fires nothing. Ask Sean first: his 2.78 tiles were slashes and duplicates, which 2.137 / 2.142 now refuse upstream |
| 4 | X2 EXPORT writes a chord at the MODE of its heads' durations | §3 EXPORT never argmaxes | <= 124 / 818 narrowed stem values | no | in `group_chords_in_measure`, a chord whose heads disagree on `written` is held out of the bar (red) or written GUESSED with the disagreement, never the mode |
| 5 | X3 EXPORT judges a system's bars by the file's carried meter after ADJUDICATE refused that carry | rule 8 (a fallback converts "cannot tell" into an answer) -- or the page convention, read the other way | 710 Brahms bars on a carried meter (abstained-system share needs the record) | partly (2.162 should stop most refusals) | where the system's `meter` verdict ABSTAINED, write its bars as read with a "meter unread" mark and do not hold or size them by `in_force`; count them |
| 6 | A7 a flag or beam read at step 3 reopens a head read open at step 1 | reading order | 12 / 23 | no | keep the head's value; file the flag / beam as `flag_on_an_open_head` (unread mark on the stem), never narrow the head |
| 7 | E6 `_bar_total_excluding` counts a narrowed note at its first candidate | DECISIONS 2026-10-17 | 0 verdicts (latent) | should join 2.162 | return `None` when any standing note in the bar is NARROWED |
| 8 | E5c one head of a DECIDED chord moved alone | one stem one value | subset of rank 1 | no | in `reconcile_duration`, search a DECIDED chord as one unit (every head moves together or none) |
| 9 | A6 the late `head_fill_from_ink` narrowing after beams / flags, outside the head-sized box | reading order (residual of 2.148) | 114 / 231 narrowings (most are non-notes) | **yes, 2.161** | -- |
| 10 | GATHER `refuse_owned` deletes a stem inside a rest box | not an override; evidence foreclosed | 58 / 126 boxes (2.150) | no (2.150 proposal 2) | do not delete a stroke from a rest box that 2.150b will refuse; or restore `Q.STEM` on refusal |

Marked OK and not ranked: A1-A5, A10, E2-E4, E5a, E7, E8, I1-I7, X1, X4.

---

## 11. Can the structure be made simpler? (for Sean)

Yes, and the shape is already half there. Today every rule carries its own
little guard -- `_admitted` has one, `bare_stem_confirmable` another,
`_shortens_without_evidence` a third, `lone_event_decline` a fourth, INFER has
`_admit`, the record has `AlreadyAdjudicated` and `UphillConsequence` -- and
the two finds this week (the bar sum picking from a narrowing, then the bars
voting a meter out with a narrowed note counted at its first candidate) were
both places where one of those small guards was missing while the others were
present. The simpler structure is ONE question asked in ONE place: *may this
step change that verdict?* -- answered from two facts the record already
carries, the verdict's stage and reading-order step (notehead 1, stem 2, beam
or flag 3, shared stem 4, anything else 5, bar sum 6, carried meter 7) and the
proposing rule's step. The answer table is short: a later step may NARROW an
earlier DECIDED value only by widening it (the dot case), never replace it; a
bar sum (step 6) may only confirm, with your two named exceptions written
GUESSED; nothing may read a NARROWED note as one number, so any sum over a bar
with one in it returns "unknown" to every caller at once -- meter vote, bar
repair, rest reinstatement, export alike; and INFER's existing `_admit` is just
this check for its stage. Put that in `Log.record` (where the supersede guard
already lives) and in one `bar_length(cell)` helper that every consumer in §6
calls, and the per-rule guards become redundant and can be deleted one at a
time; a new rule then cannot forget a guard, because it is not the rule's to
write. The cost is one lane with no output change expected and a test per row
of the answer table; the finds above (ranks 1, 2, 5, 6, 7) all become one-line
entries in that table instead of five separate fixes.
