# 2.311 -- why every red bar is red (first cause, ALL red bars)

STAGED, one saved gather per plate (`lit-a`, `bra-a`), no re-gather; classifier `redbar_classify.py`, driver `redbar_ranking.py`. The first cause keeps
`redbars.cause_of`'s order (Sean read 12 random bars aloud and it matched every time); each vague bucket is then split by a test on the record's own rows.
Value risk: `wrong` = the sum matches EXACTLY a dot printed and not read, so a plain value written READ is probably wrong; `sum` = the bar does not add up, so a
written value (or a mark) is wrong or missing -- the record cannot say which; `unread` = the bar is red only because something was marked unread.

## combined: 585 red bars

| # | cause | record's reason words | bars | share | owner | wrong / sum / unread |
|--|--|--|--|--|--|--|
| 1 | a chord on one stem whose members' values the marks do not settle: chord held | chord_value_undecided: head_and_marks (35); chord_value_undecided: stem_tip_reads_no_beam (7); chord_value_undecided: stem_value_follows (2) | 48 | 8.2% | EXPORT export.py `chord_value_undecided` (from ADJUDICATE adjudicate_duration chord reasons) | 0 / 5 / 43 |
| 2 | a note on a stem with beam ink beside it that was judged uncertain (no flag, no sure beam): value held | duration_narrowed: beam_discounted_uncertain (47) | 47 | 8.0% | ADJUDICATE rhythm.py::adjudicate_duration (`beam_discounted_uncertain`; INFER inferences.py BARE_STEM) | 0 / 8 / 39 |
| 3 | a narrow mark refused as 'not a note', alone inside this staff's own cell: may be a real head not read | not_a_notehead:too_narrow (41); not_a_notehead:stem_end_ink_disagrees (4); not_a_notehead:on_a_rest (1) | 46 | 7.9% | ADJUDICATE notehead_precision.py::adjudicate_notehead_is_not_a_notehead | 0 / 21 / 25 |
| 4 | a note's beam could not be told (joined to its neighbours or not): value held | duration_narrowed: beams_ambiguous (41) | 41 | 7.0% | ADJUDICATE rhythm.py::adjudicate_duration (beams branch) | 0 / 5 / 36 |
| 5 | long: a rest counted here is the exact surplus, or one step too long (a stroke read as a rest, or a rest value too long) | does not add up, long (38) | 38 | 6.5% | ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest + rhythm.py rest value | 0 / 38 / 0 |
| 6 | every mark in the cell was given to another staff (owned elsewhere), the bar written empty | owned_by_another_staff (28) | 28 | 4.8% | ADJUDICATE adjudicate_glyph_owner | 0 / 0 / 28 |
| 7 | short, no cause found, and the bar holds notes written shorter than a quarter whose value comes from beams/flags (a beam/flag read may be wrong) | does not add up, short (22); does not add up, two voices disagree (1) | 23 | 3.9% | ADJUDICATE rhythm.py::adjudicate_duration (beams / flags) | 0 / 23 / 0 |
| 8 | short by half the note: a dot is printed beside a plain written note and the detector drew no box on it | does not add up, short (23) | 23 | 3.9% | GATHER detector (dot never boxed); ADJUDICATE aug_dot_join.py cannot join a dot with no box | 23 / 0 / 0 |
| 9 | red only because a RIGHTLY refused mark (a neighbour staff's head or rest cut by the cell edge, or a sliver of a head we read) was filed as an unread gap; every real mark of the bar was written | partial; only refusals: a neighbour's mark cut by the cell edge / a sliver of a head read (21) | 21 | 3.6% | EXPORT export.py `_attach_unplaced` (marks the gap for a refusal not in `_NOT_A_GAP_REASONS`) | 0 / 0 / 21 |
| 10 | long and no test fired (unexplained) | does not add up, long (21) | 21 | 3.6% | unknown | 0 / 21 / 0 |
| 11 | two voices disagree because the second voice is a copy of marks already counted in the first (the same boxes written twice) | does not add up, two voices disagree (20) | 20 | 3.4% | EXPORT voice assignment (export.py `_place_notes` / voice split) | 0 / 20 / 0 |
| 12 | every mark in the cell was refused as ink of a barline/word/dynamic or as a twin box | not_a_notehead:claimed_by:barline (9); not_a_notehead:on_a_dynamic_letter (3); not_a_notehead:claimed_by:word (2) | 20 | 3.4% | ADJUDICATE claim order (barline / word claim) + notehead_precision | 0 / 0 / 20 |
| 13 | short: mark-sized ink on the staff inside no detector box (a note or rest never boxed) | does not add up, short (18) | 18 | 3.1% | GATHER detector (a box it never drew has no subject) | 0 / 18 / 0 |
| 14 | no note or rest boxed, yet mark-sized ink on the staff: never boxed by the detector | no head or rest box in the bar; 1 unboxed head- or rest-sized ink pieces on the staff (12); no head or rest box in the bar; 2 unboxed head- or rest-sized ink pieces on the staff (3); no head or rest box in the bar; 4 unboxed head- or rest-sized ink pieces on the staff (1) | 16 | 2.7% | GATHER detector (a box it never drew has no subject) | 0 / 0 / 16 |
| 15 | a rest-like mark refused inside this staff (stroke into a head, outside its staff, has a stem...) | not_a_rest:rest_stroke_into_a_head (14); not_a_rest:rest_is_a_slashed_stem (1) | 15 | 2.6% | ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest | 0 / 9 / 6 |
| 16 | long: the bar adds up exactly to another common meter (3, 4 or 6 quarters): the meter carried may be stale | does not add up, long (14) | 14 | 2.4% | EVALUATE meter carry (`OMR_METER_CARRY`) / ADJUDICATE meter reader | 0 / 14 / 0 |
| 17 | does not add up and every written note is GUESSED (blue): the sum inherits the guesses | does not add up, short (13) | 13 | 2.2% | INFER inferences.py | 0 / 13 / 0 |
| 18 | a head read but its pitch could not be placed (no clef in force / ledger unread) | no_pitch (12) | 12 | 2.1% | EVALUATE consequences.py::restate_pitch | 0 / 1 / 11 |
| 19 | no note or rest boxed and no mark-sized ink on the staff (bar printed empty or only lines) | no head or rest box and no head- or rest-sized ink on the staff (12) | 12 | 2.1% | GATHER cell / EXPORT empty-bar rule | 0 / 0 / 12 |
| 20 | short: rest-sized ink in the bar the rest reader could not tell (shape / claimed / head beside) | does not add up, short (11) | 11 | 1.9% | ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest | 0 / 11 / 0 |
| 21 | long by exactly one dot: a dot written that taking away would fill the bar | does not add up, long (10) | 10 | 1.7% | ADJUDICATE rhythm.py::adjudicate_dot_role | 0 / 10 / 0 |
| 22 | short: the bar holds ONE written event under a known meter, plain, and nothing else read (rest of the bar unread or the event is longer) | does not add up, short (10) | 10 | 1.7% | INFER inferences.py one-event rule did not fill it (the event was READ, not narrowed) | 0 / 10 / 0 |
| 23 | short and no test fired (unexplained) | does not add up, short (10) | 10 | 1.7% | unknown | 0 / 10 / 0 |
| 24 | a rest whose shape and the place it hangs disagree: value held | rest_duration_narrowed: rest_slot_contradicts_class (9) | 9 | 1.5% | ADJUDICATE rhythm.py::adjudicate_duration (`rest_slot_contradicts_class`) | 0 / 0 / 9 |
| 25 | long: a whole rest is written beside notes of the same voice and counted as a whole bar of silence | does not add up, long (9) | 9 | 1.5% | ADJUDICATE rest value (restWhole shape) + EXPORT voice assignment | 0 / 9 / 0 |
| 26 | a dot beside a plain note, augmentation or staccato not decided: value held | duration_narrowed: dot_seen_beside_a_plain_note (8) | 8 | 1.4% | ADJUDICATE rhythm.py::adjudicate_dot_role + adjudicate_duration | 0 / 3 / 5 |
| 27 | long: one written note a step shorter would fill the bar exactly (a value read too long: head fill / unread flag or beam) | does not add up, long (7) | 7 | 1.2% | ADJUDICATE rhythm.py::adjudicate_duration (head fill / flags) | 0 / 7 / 0 |
| 28 | a beam is certain but does not reach this note: value held | duration_narrowed: beam_certain_not_joined (6) | 6 | 1.0% | ADJUDICATE rhythm.py::adjudicate_duration | 0 / 1 / 5 |
| 29 | flag ink beside a stem seen but the flag not read: value held | duration_narrowed: flag_ink_unread (6) | 6 | 1.0% | ADJUDICATE rhythm.py::adjudicate_duration (`flag_ink_unread`) | 0 / 0 / 6 |
| 30 | long: a note standing at the bar's edge, counted here, is the exact surplus (it may belong to the next bar) | does not add up, long (5) | 5 | 0.9% | EXPORT export.py note-to-bar placing (`_place_notes`) / measure_extractor cells | 0 / 5 / 0 |
| 31 | the head shape and the flag/stem disagree: value held | duration_narrowed: open_head_flag_contradiction (2); duration_narrowed: whole_class_filled_on_a_stem (1) | 3 | 0.5% | ADJUDICATE rhythm.py::adjudicate_duration | 0 / 0 / 3 |
| 32 | a box too wide to be one mark left unread | unread:wide_box_unread (3) | 3 | 0.5% | EXPORT export.py `unread:wide_box_unread` | 0 / 0 / 3 |
| 33 | one head counted twice (two written heads on the same place) | does not add up, short (2); does not add up, two voices disagree (1) | 3 | 0.5% | EXPORT export.py::_place_notes (duplicate guard) | 0 / 3 / 0 |
| 34 | a small (grace-sized) head counted at full value | does not add up, long (3) | 3 | 0.5% | ADJUDICATE notehead class (no grace reader) | 0 / 3 / 0 |
| 35 | no note or rest boxed; rest-sized ink there that the rest reader could not tell | no head or rest box; rest-sized ink abstained: shape_cannot_tell (2) | 2 | 0.3% | ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest (abstained) | 0 / 0 / 2 |
| 36 | short by a dot: a dot box decided 'augmentation' beside a plain written note, not written on it | does not add up, two voices disagree (1); does not add up, short (1) | 2 | 0.3% | ADJUDICATE aug_dot_join.py / EXPORT dot attach | 2 / 0 / 0 |
| 37 | another read mark not written | ink_is_a_whole_rest (1) | 1 | 0.2% | EXPORT export.py::_place_notes | 0 / 1 / 0 |
| 38 | two voices disagree and no test fired (unexplained) | does not add up, two voices disagree (1) | 1 | 0.2% | unknown | 0 / 1 / 0 |

## litolff: 309 red bars

| # | cause | record's reason words | bars | share | owner | wrong / sum / unread |
|--|--|--|--|--|--|--|
| 1 | a chord on one stem whose members' values the marks do not settle: chord held | chord_value_undecided: head_and_marks (18); chord_value_undecided: stem_value_follows (2); chord_value_undecided: stem_tip_reads_no_beam (2) | 24 | 7.8% | EXPORT export.py `chord_value_undecided` (from ADJUDICATE adjudicate_duration chord reasons) | 0 / 2 / 22 |
| 2 | a narrow mark refused as 'not a note', alone inside this staff's own cell: may be a real head not read | not_a_notehead:too_narrow (18); not_a_notehead:stem_end_ink_disagrees (4); not_a_notehead:on_a_rest (1) | 23 | 7.4% | ADJUDICATE notehead_precision.py::adjudicate_notehead_is_not_a_notehead | 0 / 7 / 16 |
| 3 | a note's beam could not be told (joined to its neighbours or not): value held | duration_narrowed: beams_ambiguous (22) | 22 | 7.1% | ADJUDICATE rhythm.py::adjudicate_duration (beams branch) | 0 / 2 / 20 |
| 4 | short, no cause found, and the bar holds notes written shorter than a quarter whose value comes from beams/flags (a beam/flag read may be wrong) | does not add up, short (18) | 18 | 5.8% | ADJUDICATE rhythm.py::adjudicate_duration (beams / flags) | 0 / 18 / 0 |
| 5 | short: mark-sized ink on the staff inside no detector box (a note or rest never boxed) | does not add up, short (17) | 17 | 5.5% | GATHER detector (a box it never drew has no subject) | 0 / 17 / 0 |
| 6 | a note on a stem with beam ink beside it that was judged uncertain (no flag, no sure beam): value held | duration_narrowed: beam_discounted_uncertain (16) | 16 | 5.2% | ADJUDICATE rhythm.py::adjudicate_duration (`beam_discounted_uncertain`; INFER inferences.py BARE_STEM) | 0 / 3 / 13 |
| 7 | two voices disagree because the second voice is a copy of marks already counted in the first (the same boxes written twice) | does not add up, two voices disagree (15) | 15 | 4.9% | EXPORT voice assignment (export.py `_place_notes` / voice split) | 0 / 15 / 0 |
| 8 | long: a rest counted here is the exact surplus, or one step too long (a stroke read as a rest, or a rest value too long) | does not add up, long (13) | 13 | 4.2% | ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest + rhythm.py rest value | 0 / 13 / 0 |
| 9 | no note or rest boxed, yet mark-sized ink on the staff: never boxed by the detector | no head or rest box in the bar; 1 unboxed head- or rest-sized ink pieces on the staff (8); no head or rest box in the bar; 2 unboxed head- or rest-sized ink pieces on the staff (3); no head or rest box in the bar; 4 unboxed head- or rest-sized ink pieces on the staff (1) | 12 | 3.9% | GATHER detector (a box it never drew has no subject) | 0 / 0 / 12 |
| 10 | every mark in the cell was given to another staff (owned elsewhere), the bar written empty | owned_by_another_staff (12) | 12 | 3.9% | ADJUDICATE adjudicate_glyph_owner | 0 / 0 / 12 |
| 11 | long and no test fired (unexplained) | does not add up, long (11) | 11 | 3.6% | unknown | 0 / 11 / 0 |
| 12 | long: the bar adds up exactly to another common meter (3, 4 or 6 quarters): the meter carried may be stale | does not add up, long (10) | 10 | 3.2% | EVALUATE meter carry (`OMR_METER_CARRY`) / ADJUDICATE meter reader | 0 / 10 / 0 |
| 13 | short: the bar holds ONE written event under a known meter, plain, and nothing else read (rest of the bar unread or the event is longer) | does not add up, short (10) | 10 | 3.2% | INFER inferences.py one-event rule did not fill it (the event was READ, not narrowed) | 0 / 10 / 0 |
| 14 | short: rest-sized ink in the bar the rest reader could not tell (shape / claimed / head beside) | does not add up, short (10) | 10 | 3.2% | ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest | 0 / 10 / 0 |
| 15 | a head read but its pitch could not be placed (no clef in force / ledger unread) | no_pitch (9) | 9 | 2.9% | EVALUATE consequences.py::restate_pitch | 0 / 0 / 9 |
| 16 | a rest whose shape and the place it hangs disagree: value held | rest_duration_narrowed: rest_slot_contradicts_class (9) | 9 | 2.9% | ADJUDICATE rhythm.py::adjudicate_duration (`rest_slot_contradicts_class`) | 0 / 0 / 9 |
| 17 | every mark in the cell was refused as ink of a barline/word/dynamic or as a twin box | not_a_notehead:on_a_dynamic_letter (3); not_a_notehead:claimed_by:word (2); not_a_rest:claimed_by:word (1) | 9 | 2.9% | ADJUDICATE claim order (barline / word claim) + notehead_precision | 0 / 0 / 9 |
| 18 | a rest-like mark refused inside this staff (stroke into a head, outside its staff, has a stem...) | not_a_rest:rest_stroke_into_a_head (7); not_a_rest:rest_is_a_slashed_stem (1) | 8 | 2.6% | ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest | 0 / 2 / 6 |
| 19 | no note or rest boxed and no mark-sized ink on the staff (bar printed empty or only lines) | no head or rest box and no head- or rest-sized ink on the staff (8) | 8 | 2.6% | GATHER cell / EXPORT empty-bar rule | 0 / 0 / 8 |
| 20 | red only because a RIGHTLY refused mark (a neighbour staff's head or rest cut by the cell edge, or a sliver of a head we read) was filed as an unread gap; every real mark of the bar was written | partial; only refusals: a neighbour's mark cut by the cell edge / a sliver of a head read (7) | 7 | 2.3% | EXPORT export.py `_attach_unplaced` (marks the gap for a refusal not in `_NOT_A_GAP_REASONS`) | 0 / 0 / 7 |
| 21 | long: a whole rest is written beside notes of the same voice and counted as a whole bar of silence | does not add up, long (7) | 7 | 2.3% | ADJUDICATE rest value (restWhole shape) + EXPORT voice assignment | 0 / 7 / 0 |
| 22 | a beam is certain but does not reach this note: value held | duration_narrowed: beam_certain_not_joined (5) | 5 | 1.6% | ADJUDICATE rhythm.py::adjudicate_duration | 0 / 1 / 4 |
| 23 | long: a note standing at the bar's edge, counted here, is the exact surplus (it may belong to the next bar) | does not add up, long (5) | 5 | 1.6% | EXPORT export.py note-to-bar placing (`_place_notes`) / measure_extractor cells | 0 / 5 / 0 |
| 24 | does not add up and every written note is GUESSED (blue): the sum inherits the guesses | does not add up, short (4) | 4 | 1.3% | INFER inferences.py | 0 / 4 / 0 |
| 25 | long by exactly one dot: a dot written that taking away would fill the bar | does not add up, long (4) | 4 | 1.3% | ADJUDICATE rhythm.py::adjudicate_dot_role | 0 / 4 / 0 |
| 26 | a box too wide to be one mark left unread | unread:wide_box_unread (3) | 3 | 1.0% | EXPORT export.py `unread:wide_box_unread` | 0 / 0 / 3 |
| 27 | long: one written note a step shorter would fill the bar exactly (a value read too long: head fill / unread flag or beam) | does not add up, long (3) | 3 | 1.0% | ADJUDICATE rhythm.py::adjudicate_duration (head fill / flags) | 0 / 3 / 0 |
| 28 | short by half the note: a dot is printed beside a plain written note and the detector drew no box on it | does not add up, short (3) | 3 | 1.0% | GATHER detector (dot never boxed); ADJUDICATE aug_dot_join.py cannot join a dot with no box | 3 / 0 / 0 |
| 29 | a dot beside a plain note, augmentation or staccato not decided: value held | duration_narrowed: dot_seen_beside_a_plain_note (2) | 2 | 0.7% | ADJUDICATE rhythm.py::adjudicate_dot_role + adjudicate_duration | 0 / 0 / 2 |
| 30 | flag ink beside a stem seen but the flag not read: value held | duration_narrowed: flag_ink_unread (2) | 2 | 0.7% | ADJUDICATE rhythm.py::adjudicate_duration (`flag_ink_unread`) | 0 / 0 / 2 |
| 31 | no note or rest boxed; rest-sized ink there that the rest reader could not tell | no head or rest box; rest-sized ink abstained: shape_cannot_tell (2) | 2 | 0.7% | ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest (abstained) | 0 / 0 / 2 |
| 32 | one head counted twice (two written heads on the same place) | does not add up, short (1); does not add up, two voices disagree (1) | 2 | 0.7% | EXPORT export.py::_place_notes (duplicate guard) | 0 / 2 / 0 |
| 33 | a small (grace-sized) head counted at full value | does not add up, long (2) | 2 | 0.7% | ADJUDICATE notehead class (no grace reader) | 0 / 2 / 0 |
| 34 | the head shape and the flag/stem disagree: value held | duration_narrowed: whole_class_filled_on_a_stem (1) | 1 | 0.3% | ADJUDICATE rhythm.py::adjudicate_duration | 0 / 0 / 1 |
| 35 | two voices disagree and no test fired (unexplained) | does not add up, two voices disagree (1) | 1 | 0.3% | unknown | 0 / 1 / 0 |

## brahms: 276 red bars

| # | cause | record's reason words | bars | share | owner | wrong / sum / unread |
|--|--|--|--|--|--|--|
| 1 | a note on a stem with beam ink beside it that was judged uncertain (no flag, no sure beam): value held | duration_narrowed: beam_discounted_uncertain (31) | 31 | 11.2% | ADJUDICATE rhythm.py::adjudicate_duration (`beam_discounted_uncertain`; INFER inferences.py BARE_STEM) | 0 / 5 / 26 |
| 2 | long: a rest counted here is the exact surplus, or one step too long (a stroke read as a rest, or a rest value too long) | does not add up, long (25) | 25 | 9.1% | ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest + rhythm.py rest value | 0 / 25 / 0 |
| 3 | a chord on one stem whose members' values the marks do not settle: chord held | chord_value_undecided: head_and_marks (17); chord_value_undecided: stem_tip_reads_no_beam (5); chord_value_undecided: refused_strokes_are_slurs_or_too_thin_for_a_beam (1) | 24 | 8.7% | EXPORT export.py `chord_value_undecided` (from ADJUDICATE adjudicate_duration chord reasons) | 0 / 3 / 21 |
| 4 | a narrow mark refused as 'not a note', alone inside this staff's own cell: may be a real head not read | not_a_notehead:too_narrow (23) | 23 | 8.3% | ADJUDICATE notehead_precision.py::adjudicate_notehead_is_not_a_notehead | 0 / 14 / 9 |
| 5 | short by half the note: a dot is printed beside a plain written note and the detector drew no box on it | does not add up, short (20) | 20 | 7.2% | GATHER detector (dot never boxed); ADJUDICATE aug_dot_join.py cannot join a dot with no box | 20 / 0 / 0 |
| 6 | a note's beam could not be told (joined to its neighbours or not): value held | duration_narrowed: beams_ambiguous (19) | 19 | 6.9% | ADJUDICATE rhythm.py::adjudicate_duration (beams branch) | 0 / 3 / 16 |
| 7 | every mark in the cell was given to another staff (owned elsewhere), the bar written empty | owned_by_another_staff (16) | 16 | 5.8% | ADJUDICATE adjudicate_glyph_owner | 0 / 0 / 16 |
| 8 | red only because a RIGHTLY refused mark (a neighbour staff's head or rest cut by the cell edge, or a sliver of a head we read) was filed as an unread gap; every real mark of the bar was written | partial; only refusals: a neighbour's mark cut by the cell edge / a sliver of a head read (14) | 14 | 5.1% | EXPORT export.py `_attach_unplaced` (marks the gap for a refusal not in `_NOT_A_GAP_REASONS`) | 0 / 0 / 14 |
| 9 | every mark in the cell was refused as ink of a barline/word/dynamic or as a twin box | not_a_notehead:claimed_by:barline (9); not_a_rest:rest_is_a_duplicate_box (1); not_a_notehead:notehead_is_a_duplicate_box (1) | 11 | 4.0% | ADJUDICATE claim order (barline / word claim) + notehead_precision | 0 / 0 / 11 |
| 10 | long and no test fired (unexplained) | does not add up, long (10) | 10 | 3.6% | unknown | 0 / 10 / 0 |
| 11 | short and no test fired (unexplained) | does not add up, short (10) | 10 | 3.6% | unknown | 0 / 10 / 0 |
| 12 | does not add up and every written note is GUESSED (blue): the sum inherits the guesses | does not add up, short (9) | 9 | 3.3% | INFER inferences.py | 0 / 9 / 0 |
| 13 | a rest-like mark refused inside this staff (stroke into a head, outside its staff, has a stem...) | not_a_rest:rest_stroke_into_a_head (7) | 7 | 2.5% | ADJUDICATE family_precision.py::adjudicate_rest_is_not_a_rest | 0 / 7 / 0 |
| 14 | a dot beside a plain note, augmentation or staccato not decided: value held | duration_narrowed: dot_seen_beside_a_plain_note (6) | 6 | 2.2% | ADJUDICATE rhythm.py::adjudicate_dot_role + adjudicate_duration | 0 / 3 / 3 |
| 15 | long by exactly one dot: a dot written that taking away would fill the bar | does not add up, long (6) | 6 | 2.2% | ADJUDICATE rhythm.py::adjudicate_dot_role | 0 / 6 / 0 |
| 16 | short, no cause found, and the bar holds notes written shorter than a quarter whose value comes from beams/flags (a beam/flag read may be wrong) | does not add up, short (4); does not add up, two voices disagree (1) | 5 | 1.8% | ADJUDICATE rhythm.py::adjudicate_duration (beams / flags) | 0 / 5 / 0 |
| 17 | two voices disagree because the second voice is a copy of marks already counted in the first (the same boxes written twice) | does not add up, two voices disagree (5) | 5 | 1.8% | EXPORT voice assignment (export.py `_place_notes` / voice split) | 0 / 5 / 0 |
| 18 | flag ink beside a stem seen but the flag not read: value held | duration_narrowed: flag_ink_unread (4) | 4 | 1.5% | ADJUDICATE rhythm.py::adjudicate_duration (`flag_ink_unread`) | 0 / 0 / 4 |
| 19 | no note or rest boxed and no mark-sized ink on the staff (bar printed empty or only lines) | no head or rest box and no head- or rest-sized ink on the staff (4) | 4 | 1.5% | GATHER cell / EXPORT empty-bar rule | 0 / 0 / 4 |
| 20 | no note or rest boxed, yet mark-sized ink on the staff: never boxed by the detector | no head or rest box in the bar; 1 unboxed head- or rest-sized ink pieces on the staff (4) | 4 | 1.5% | GATHER detector (a box it never drew has no subject) | 0 / 0 / 4 |
| 21 | long: the bar adds up exactly to another common meter (3, 4 or 6 quarters): the meter carried may be stale | does not add up, long (4) | 4 | 1.5% | EVALUATE meter carry (`OMR_METER_CARRY`) / ADJUDICATE meter reader | 0 / 4 / 0 |
| 22 | long: one written note a step shorter would fill the bar exactly (a value read too long: head fill / unread flag or beam) | does not add up, long (4) | 4 | 1.5% | ADJUDICATE rhythm.py::adjudicate_duration (head fill / flags) | 0 / 4 / 0 |
| 23 | a head read but its pitch could not be placed (no clef in force / ledger unread) | no_pitch (3) | 3 | 1.1% | EVALUATE consequences.py::restate_pitch | 0 / 1 / 2 |
| 24 | the head shape and the flag/stem disagree: value held | duration_narrowed: open_head_flag_contradiction (2) | 2 | 0.7% | ADJUDICATE rhythm.py::adjudicate_duration | 0 / 0 / 2 |
| 25 | long: a whole rest is written beside notes of the same voice and counted as a whole bar of silence | does not add up, long (2) | 2 | 0.7% | ADJUDICATE rest value (restWhole shape) + EXPORT voice assignment | 0 / 2 / 0 |
| 26 | short by a dot: a dot box decided 'augmentation' beside a plain written note, not written on it | does not add up, two voices disagree (1); does not add up, short (1) | 2 | 0.7% | ADJUDICATE aug_dot_join.py / EXPORT dot attach | 2 / 0 / 0 |
| 27 | a beam is certain but does not reach this note: value held | duration_narrowed: beam_certain_not_joined (1) | 1 | 0.4% | ADJUDICATE rhythm.py::adjudicate_duration | 0 / 0 / 1 |
| 28 | another read mark not written | ink_is_a_whole_rest (1) | 1 | 0.4% | EXPORT export.py::_place_notes | 0 / 1 / 0 |
| 29 | one head counted twice (two written heads on the same place) | does not add up, short (1) | 1 | 0.4% | EXPORT export.py::_place_notes (duplicate guard) | 0 / 1 / 0 |
| 30 | a small (grace-sized) head counted at full value | does not add up, long (1) | 1 | 0.4% | ADJUDICATE notehead class (no grace reader) | 0 / 1 / 0 |
| 31 | short: mark-sized ink on the staff inside no detector box (a note or rest never boxed) | does not add up, short (1) | 1 | 0.4% | GATHER detector (a box it never drew has no subject) | 0 / 1 / 0 |
| 32 | short: rest-sized ink in the bar the rest reader could not tell (shape / claimed / head beside) | does not add up, short (1) | 1 | 0.4% | ADJUDICATE unboxed_rest.py::adjudicate_unboxed_ink_is_a_rest | 0 / 1 / 0 |

## Controls: how often each test's evidence also sits in a bar that is NOT red

A test that fires as often on bars that add up as on red bars explains nothing by itself. Share of bars carrying the evidence (cells of the count pages):

| evidence | Litolff red | Litolff not red | Brahms red | Brahms not red |
|--|--|--|--|--|
| dot_evidence_beside_a_plain_note | 8.7% of 309 | 14.4% of 2375 | 23.6% of 276 | 24.2% of 1758 |
| duplicate_head | 2.9% of 309 | 0.0% of 2375 | 0.7% of 276 | 0.0% of 1758 |
| foreign_note | 0.0% of 309 | 0.2% of 2375 | 0.0% of 276 | 0.6% of 1758 |
| head_given_away | 0.0% of 309 | 0.1% of 2375 | 0.4% of 276 | 0.7% of 1758 |
| small_head | 1.0% of 309 | 0.2% of 2375 | 0.4% of 276 | 0.2% of 1758 |
| tuplet_mark | 0.3% of 309 | 0.1% of 2375 | 0.0% of 276 | 0.1% of 1758 |
| unboxed_mark_ink | 30.7% of 309 | 13.0% of 2375 | 15.9% of 276 | 6.8% of 1758 |
| unboxed_rest_ink | 8.7% of 309 | 3.2% of 2375 | 8.7% of 276 | 3.9% of 1758 |
| whole_rest_beside_notes | 2.9% of 309 | 0.0% of 2375 | 0.4% of 276 | 0.0% of 1758 |

Rows resting on an arithmetic fit only (`one note a step long`, `a rest too long`, `fills another meter`, `beam/flag values`) are the weakest witness:
the bar sum can confirm, never supply (CLAUDE.md section 4). Rows resting on ink we sized (`unboxed ink`, `dot ink`) fire on 7-24% of bars that add up
(table above): only the exact-sum match (dot) or the record's own verdict (unboxed rest) makes them a mechanism. Cause rows that come straight from
the record's reason words (`lost_*`, `twin_*`, `nothing_*`) carry no such caveat.