# Re-gather report: Beethoven 5 mvt 1 (Litolff scan), 20261016-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Beethoven 5 mvt 1 (Litolff scan), 20261014-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

## 0. One screen

### Run

- **tree**: 1d42c4aa (previous: 8b9eb97c)
- **landings since the previous night**:
  - 145 commits (merges left out); the newest 15:
  - 0cc03864 Land 2.155: OMR_STEM_AT_BAR_EDGE default ON (Sean 2026-10-16)
  - accfdf66 Land 2.157 (Sean 2026-10-16): replay harness dangling ids; ROADMAP LANDED, DECISIONS line, version_memory
  - 1e9d6410 2.155: continue-a-level checked without gathers (tile 13 right, tile 4 blocked, 39 of 40 tile cells unchanged); 40-tile tables, reach, FINDINGS 10.12; fast tier green, check 192
  - 46e5ce62 2.157: replay harness re-points every row id a GATHER row carries (tooling; no pipeline output change)
  - d51da408 2.155: a continued level is MERGED into the stroke it continues (kept apart, a neighbour's stem read two levels); 40-tile cell check + tile-13 replay probes
  - 7f259a2c 2.155: a found stem may continue a beam level the other stems make, never start one (Sean 'Yes'); tests fail with either side removed
  - 7c564ae5 2.155b FINDINGS: four narrowings become decided wrongs, not three
  - 886d408c 2.155b: Sean's 20 answers recorded and scored (defaults base 13/2/4/1 -> arm 18/2/0/0; 2.153 rule ON 1/2/15/1 -> 17/2); tile 13 traced to the beam guard, tile 10 to head fill; judged index rebuilt
  - 9c27c5c4 Park 2.156 grace notes (Sean 2026-10-16): overfill + small heads should suggest grace notes when revisited
  - ce6cf27c 2.155 tightened: Sean's 20 tiles re-scored (defaults 12/3 -> 14/4, 2.153 rule ON Litolff 4/1 -> 11/0), reach (Litolff 158, Brahms 6, no new beam strokes), 20 blind tiles 2.155b, FINDINGS 10.9-10.10; fast tier green
  - d22afa2a 2.156 phase 1b: rules checked against fetched sources and the print
  - 1438eeef Correct grace-note slash rule: Sean was guessing; slash + after-trill rules rest on 2.156 research (Sean 2026-10-16)
  - 723a49fe 2.156 phase 1: grace-note engraving research + read-only STAGED trace and counts
  - d9353217 Grace-note rules (Sean 2026-10-16) into page-facts + DECISIONS; claim 2.156, open and claim 2.157 (replay harness)
  - 6b54129a 2.155b cutter: skip the conditions not gathered (Brahms 2.153-rule runs cut by Sean)
- **flags/settings that differ from defaults**:
  - OMR_SURYA_KEEP_ALIVE=0
- **weights**: --weights auto (weight routing off)
- **pages**: 1-16
- **wall time**: 64 min (gather through INFER; exit 0) (previous: 65 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| parts in the file | 12 | 12 |
| staves named (staff rows over all systems) | 203 (not named: 128) | 203 (not named: 128) |
| staves held out (counted, not placed in a part) | 0 | 0 |
| meter, per system: read / carried / guessed / narrowed / abstained | 1 / 30 / 0 / 0 / 0 | 1 / 30 / 0 / 0 / 0 |
| key, per staff and system: read / carried / guessed / narrowed / abstained | 136 / 0 / 195 / 0 / 0 | 136 / 0 / 195 / 0 / 0 |
| clef, per staff and system: read / carried / guessed / narrowed / abstained | 317 / 0 / 11 / 3 / 0 | 317 / 0 / 11 / 3 / 0 |
| bars marked unread (red) | 1,457 (-82) | |
| MusicXML written | yes 3.7 MB | yes |
| LilyPond written / compiled / warnings | yes / yes / 21 | yes / yes / 24 |

### Biggest movers since the previous night

| row | was | now | change |
|---|---|---|---|
| blue guessed by rule / reconcile_duration | 225 | 126 | -99 |
| bars / held out | 699 | 584 | -115 |
| export not written / bar_does_not_add_up | 1,662 | 1,406 | -256 |
| blue kept in partial bars / onset_from_partial_bar_suffix | 125 | 160 | +35 |
| rests / refused total | 598 | 670 | +72 |
| blue kept in partial bars / onset_from_partial_bar_prefix | 68 | 96 | +28 |
| bars / written with guesses | 963 | 874 | -89 |
| noteheads: how long / guessed at glyph level | 2,392 | 2,189 | -203 |
| noteheads: which pitch / guessed at glyph level | 2,380 | 2,180 | -200 |
| blue guessed by rule / collapse_narrowed_by_bar | 62 | 40 | -22 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 3,729 (+171) | all notes written, none guessed |
| written with guesses | 874 (-89) | written; at least one note/dynamic is a guess (blue) |
| partial | 174 (+13) | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 584 (-115) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 699 (+20) | nothing read in this bar; padded and marked red |
| **total bars (parts x measures)** | 6,060 | |

- bars: in 6,060 = unread, empty 699, written plain 3,729, held out 584, partial 174, written with guesses 874 (sum 6,060) -> balanced
- check, partial bars: file vs exporter: file 174, exporter 174 -> agrees
- check, held-out bars (named + doubled-staff copies): file vs exporter: file 584, exporter 584 -> agrees
- check, unread-empty bars: file vs exporter: file 699, exporter 699 -> agrees
- check, unread-empty bars named by the exporter: file vs exporter: file 699, exporter 699 -> agrees

Bars with notes read off the page: 5,014 (-20). Tacet bars padded with rests (written, not unread): 347. Meter: 0 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 155, short_without_an_unread_symbol 343, nothing_before_or_after_the_gap 30.

Red marks written: 1457. Equation: empty 699 + held out 584 + partial 174 = 1457 (the partial bars carry 175 red bracketed gaps) -> balanced.

## 2. Symbols: what happens to each kind at each stage

GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.

### 2a. Per symbol kind, at glyph level (computed here from the record)

| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |
|---|---|---|---|---|---|---|---|---|
| noteheads: how long | 11,399 | 1,590 (+41) | 8,144 (-58) | 352 (+21) | 1,313 (-4) | 0 | 2,189 (-203) | balanced |
| noteheads: which pitch | 11,399 | 1,590 (+41) | 9,714 (-41) | 0 | 0 | 95 | 2,180 (-200) | balanced |
| rests | 2,873 +132 | 670 (+72) | 2,215 (-65) | 22 | 98 | 0 | 0 | balanced |
| accidentals | 1,508 | 0 | 647 (-1) | 0 | 861 (+1) | 0 | 0 | balanced |
| slurs | 1,225 | 5 | 1,213 | 0 | 7 | 0 | 0 | balanced |
| ties | 1,419 | 498 | 921 | 0 | 0 | 0 | 0 | balanced |
| articulations | 18 | 11 | 3 | 1 | 3 | 0 | 0 | balanced |
| dots | 601 | 0 | 459 | 0 | 142 | 0 | 0 | balanced |
| fermatas | 178 | 0 | 156 | 0 | 22 | 0 | 0 | balanced |
| ornaments | 3 | 0 | 2 | 0 | 1 | 0 | 0 | balanced |
| hairpins | 0 +5 | 0 | 5 | 0 | 0 | 0 | 0 | balanced |

Is-it-really-one refusals for every family, from the exporter's own `family_refusals` (kept / refused / abstained):

- ledger_is_not_a_ledger: kept 1,761, refused 5,919, abstained 21 (inside_the_staff 5199, on_a_staff_line 693, no_head_on_the_rung 25)
- accidental_is_not_an_accidental: kept 1,508, refused 0, abstained 0
- rest_is_not_a_rest: kept 2,203, refused 670, abstained 0 (rest_has_a_stem 121, rest_is_a_duplicate_box 104, rest_touches_two_staff_lines 98)
- arpeggiato_is_not_an_arpeggiato: kept 1,876, refused 21, abstained 0 (in_a_key_signature_slot 21)
- arc_is_not_an_arc: kept 2,141, refused 503, abstained 0 (ink_is_a_staff_line 502, in_a_key_signature_slot 1)
- dynamic_is_not_a_dynamic: kept 1,589, refused 0, abstained 0
- articulation_is_not_an_articulation: kept 7, refused 11, abstained 0 (ledger_between_staff_and_note 11)
- flag_is_not_a_flag: kept 252, refused 2, abstained 0 (in_a_key_signature_slot 2)
- keysig_marker_is_not_a_marker: kept 528, refused 0, abstained 0
- tuplet_marker_is_not_a_marker: kept 13, refused 0, abstained 0

Top reasons per kind (refused, narrowed, abstained):

- **noteheads: how long** (each detected notehead box: is it a real notehead, and what length is it): refused stacked_head_duplicate 444; refused clipped_fragment 342; refused too_narrow 258; abstained: owned_by_another_staff 1313; narrowed: beam_discounted_uncertain 186; narrowed: beams_ambiguous 80; narrowed: head_fill_from_ink 46
- **noteheads: which pitch** (the same boxes: which line or space, and so which note name): refused stacked_head_duplicate 444; refused clipped_fragment 342; refused too_narrow 258
- **rests** (each detected rest box: is it a real rest, and what length): refused rest_has_a_stem 121; refused rest_is_a_duplicate_box 104; refused rest_touches_two_staff_lines 98; abstained: rest_stands_where_no_rest_hangs 98; narrowed: rest_slot_contradicts_class 22
- **accidentals** (sharps/flats/naturals: which notehead they belong to): abstained: no_candidate 718; abstained: is_a_key_signature_marker 123; abstained: ambiguous_height 14; abstained: head_belongs_to_a_nearer_staff 6
- **slurs** (curved lines read as slurs): refused ink_is_a_staff_line 5; abstained: same_pitch_accidental_unread 5; abstained: stack_slur_over_two_same_pitch_notes 2
- **ties** (curved lines read as ties): refused ink_is_a_staff_line 497; refused in_a_key_signature_slot 1
- **articulations** (accents, tenuto, staccatissimo: which note): refused ledger_between_staff_and_note 11; abstained: no_notehead 3; narrowed: heads_about_equally_near 1
- **dots** (small dots: lengthening a note or marking it short (staccato)): abstained: dot_role_ambiguous 121; abstained: on_a_stroke 12; abstained: no_notehead_or_rest_in_cell 4; abstained: on_a_barline 2
- **fermatas** (fermatas: which note): abstained: no_carrier 21; abstained: owned_by_another_staff 1
- **ornaments** (trills, turns, tremolo): abstained: no_notehead 1

### 2b. Readings that belong to a staff or system, not to one box

| reading | boxes | verdicts | read | carried | guessed (INFER) | decided (yes/no) | narrowed | abstained | other | balance |
|---|---|---|---|---|---|---|---|---|---|---|
| clefs (one per staff and system) | 513 | 331 | 317 | 0 | 11 | 0 | 3 | 0 | 0 | balanced |
| key signatures (one per staff and system) | 542 | 331 | 136 | 0 | 195 | 0 | 0 | 0 | 0 | balanced |
| meters (time signatures) (one per system) | 82 | 31 | 1 | 30 | 0 | 0 | 0 | 0 | 0 | balanced |
| instrument names (one per staff) | 0 | 331 | 203 | 0 | 0 | 0 | 0 | 128 | 0 | balanced |
| direction words (one verdict per inked cell; most say no word is there) | 0 | 5,377 | 0 | 0 | 0 | 5,376 | 0 | 1 | 0 | balanced |
| dynamic words (one verdict per inked cell (most say no dynamic); the boxes are single letters) | 1,589 | 5,377 | 0 | 0 | 0 | 5,342 | 17 | 18 | 0 | balanced |
| tuplet ratios (the 3 over a triplet) | 13 | 12 | 0 | 0 | 0 | 3 | 0 | 9 | 0 | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detector boxes | decided | abstained | written to the file | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 1,508 | 647 (-1) | 861 (+1) | 370 (+10) | n/a | emitted |
| articulation | 18 | 13 | 5 | 3 | n/a | emitted |
| clef | 513 | 328 | 14 | 0 | n/a | emitted |
| direction | 0 | 5,376 | 1 | 74 | n/a | emitted |
| dot | 601 | 459 | 142 | 360 (+14) | n/a | emitted |
| dynamic | 1,589 | 5,342 | 35 | 558 | 35 | emitted |
| fermata | 178 | 156 | 22 | 78 (+1) | n/a | emitted |
| key | 542 | 331 | 195 | 0 | n/a | emitted |
| note | 11,399 | 15,091 | 0 | 6,731 (+136) | 1632 | emitted |
| ornament | 3 | 2 | 1 | 0 | n/a | decided_but_unwritten |
| rest | 2,873 | 0 | 0 | 2,178 (+9) | 51 | abstained |
| slur | 1,225 | 1,054 (-1) | 0 | 182 (-2) | n/a | emitted |
| tie | 1,419 | 1,583 (+1) | 0 | 228 (+5) | n/a | emitted |
| time | 82 | 31 | 0 | 0 | n/a | emitted |
| tuplet | 13 | 3 | 9 | 0 | n/a | emitted |
| wedge | 0 | 5 | 0 | 1 (+1) | n/a | emitted |


(`rest` reads 'abstained' only because the exporter has no separate rest verdict; rests are read, see 2a. `decided` counts verdicts, which can exceed boxes where one box has several.)

- export: events in the log -> file: in 14,404 = written 8,488, not written (reasons below) 5,916 (sum 14,404) -> balanced
(Of the written events, 419 notes were doubled onto a condensed slot and 2 rests duplicated across voices; the exporter nets those out.)

Notes and rests not written, by reason (top 12):

- bar_does_not_add_up: 1,406 (-256)
- owned_by_another_staff: 1,327 (-4)
- not_a_notehead:stacked_head_duplicate: 444 (-4)
- not_a_notehead:clipped_fragment: 342
- duration_narrowed: 319 (+21)
- not_a_notehead:too_narrow: 258
- not_a_notehead:notehead_is_a_duplicate_box: 251 (-6)
- mark_group_duplicate: 143 (-2)
- not_a_rest:rest_has_a_stem: 121 (+1)
- ink_is_a_whole_rest: 109
- not_a_rest:rest_is_a_duplicate_box: 104
- not_a_rest:rest_touches_two_staff_lines: 98

Two stages, one fact: the record's refusals (ADJUDICATE) against the exporter's drop reasons of the same name: 26 of 26 reasons agree exactly.

Every standing glyph verdict of the quantities above is in a row, on a refused box, or on a box of a kind no row covers: 9 of 9 quantities account for all their verdicts.
- pitch: 2,309 of 13,603 verdicts sit on boxes of another kind (e.g. a pitch computed for a rest box) -- listed, not hidden

Kept boxes that nothing was asked about (no verdict): noteheads: which pitch 95.

## 3. How sure are the guesses

Blue items written: **1,718 (-100)** (notes 1,632 (-95), rests 51 (-5), dynamics 35). By the rule that guessed:

- fill_part_key: 1,061 (+53) (a pitch read through a key signature that was inferred for the part)
- fill_clef_gap: 197 (+8) (a pitch read through a clef that was inferred)
- reconcile_duration: 126 (-99) (length chosen only because the bar then adds up)
- collapse_narrowed_by_bar: 40 (-22) (length narrowed to a few candidates, one chosen by the bar)
- dynamic_with_an_unread_letter: 35 (a dynamic word with a letter that could not be read)
- collapse_arc_ink_not_beam: 2 (-3) 
- collapse_duration_to_barline: 1 (length chosen to run to the barline)

Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the readable notes either side of an unread gap):

- onset_from_partial_bar_prefix: 96 (+28)
- onset_from_partial_bar_suffix: 160 (+35)

Of the guesses INFER made (record): 284 standing. Candidates it chose between: {'2': 80, '3': 4, '0': 199, '4': 1}. Evidence gap between the chosen candidate and the runner-up: {'gap 1': 54, 'tie': 31, 'one candidate': 199} ('tie' = the chosen value had no more support than another).
Durations that are guesses at glyph level: 1986; of those, settled by the bar's arithmetic alone (the weakest witness): 130.

**Refusals and how close they came** (2.106): 33104 refusals/narrowings in the record, 398 carry a margin, **32706 carry none** (rules not yet covered, or structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, since most rules declare no band). Biggest groups:

| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |
|---|---|---|---|---|---|---|---|---|
| unboxed_ink_is_a_rest | shape_cannot_tell | abstained | 185 | 185 | 62 | 61 | 62 | -0.009 at p16 sys1 staff7 cell5 glyph350000 |
| duration | head_fill_from_ink | narrowed | 114 | 101 | 39 | 18 | 57 | 0 at p6 sys1 staff9 cell2 glyph9 |
| unboxed_ink_is_a_rest | claimed_by_another_class | abstained | 82 | 81 | 28 | 26 | 28 | -0 at p16 sys1 staff3 cell7 glyph350000 |
| clef | margin_below_floor | narrowed | 10 | 0 | 7 | 0 | 3 | 0 at p4 sys0 staff8 |
| narrow_box_is_an_eighth_rest | shape_cannot_tell | abstained | 5 | 5 | 2 | 0 | 3 | -0.1 at p10 sys1 staff8 cell3 glyph3 |
| unboxed_ink_is_a_rest | head_beside_it | abstained | 2 | 2 | 1 | 0 | 1 | -0.13 at p5 sys0 staff6 cell5 glyph350000 |

## 4. Unknown and unread, in one place

- unread marks red: 1,457 (-82)
- staves held out unidentified: 0
- unidentified parts: 0
- noteheads owner not read: 10 (+2)
- noteheads no pitch: 95
- notes whose length stayed undecided (narrowed, abstained, chord): {'narrowed': 319, 'rest abstained': 98, 'chord undecided': 96}
- evidence the deciders asked for and did not find (record `adjudication.missing_evidence`, top 8): human_box_verdict 39,846, glyph_owner 24,706, rest 16,009, letter_look_cover 12,586, tuplet_ratio 12,576, aug_dot 11,507, head_line_cut 10,616, notehead_letter_ink 9,794

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 3,169 over 16 pages (about 198 per page). Previous: 3352.

Five worst pages: p15: 118 red + 180 blue; p4: 97 red + 186 blue; p14: 110 red + 150 blue; p6: 99 red + 150 blue; p13: 126 red + 98 blue.

Five worst staves (instrument, page): Viola p6: 9 red + 41 blue; Viola p15: 12 red + 38 blue; Viola p4: 9 red + 40 blue; Bassoon p16: 9 red + 38 blue; Violin [P8] p4: 4 red + 39 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Viola | 399 (+29) | 279 (-8) | 149 (-7) | 138 (-38) | 6 |
| Bassoon | 445 (+21) | 277 (-26) | 130 (-2) | 156 (-17) | 2 |
| Violin [P8] | 627 (-5) | 251 (+1) | 107 (+3) | 173 (-14) | 2 |
| Violin [P9] | 617 (+20) | 213 (+2) | 114 (-13) | 129 (-40) | 3 |
| Cello | 337 (+8) | 144 (-7) | 167 (-3) | 140 (-5) | 1 |
| Flute | 382 (+20) | 154 | 119 (-11) | 126 (-22) | 4 |
| Oboe | 376 (+20) | 155 (+9) | 108 (-16) | 139 (-46) | 2 |
| Contrabass | 334 (+12) | 87 (-14) | 126 (-2) | 24 (-2) | 0 |
| Clarinet | 611 (+32) | 60 (-15) | 137 (-9) | 168 (-30) | 3 |
| Horn | 357 (+29) | 34 (-20) | 105 (-8) | 109 (-15) | 7 |
| Timpani | 170 (+12) | 14 (-7) | 105 (-4) | 64 (-4) | 0 |
| Trumpet | 393 (+38) | 15 (-15) | 91 (-11) | 40 (-23) | 1 |

## 6. Detected, then dropped

Detector boxes whose class no family reads (never reach a decision): {'arpeggiato': 1897, 'stringsDownBow': 3, 'caesura': 3, 'segno': 1} (of 37,137 boxes).
Detected and unrepresented in the record: none. Decided but not written to the file: {'ornament': 3}.
Ink rows no class explains (Q.INK): 5377.

## 7. The top reasons, with one place to look

(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)

- 1,313 x noteheads: how long: abstained: owned_by_another_staff -- e.g. p1 sys0 staff4 cell3 glyph1
- 718 x accidentals: abstained: no_candidate -- e.g. p1 sys0 staff2 cell6 glyph0
- 528 x bar held out: does not add up -- e.g. p1 sys0 staff0 cell3 (bar 4, part P1)
- 497 x ties: refused, ink_is_a_staff_line -- e.g. p1 sys0 staff1 cell7 glyph1
- 444 x noteheads: how long: refused, stacked_head_duplicate -- e.g. p1 sys0 staff3 cell7 glyph2
- 343 x bar stays held: short_without_an_unread_symbol -- e.g. p2 sys0 staff0 cell5 (bar 22, part P1)
- 342 x noteheads: how long: refused, clipped_fragment -- e.g. p1 sys0 staff3 cell3 glyph2
- 258 x noteheads: how long: refused, too_narrow -- e.g. p1 sys0 staff2 cell0 glyph9
- 251 x noteheads: how long: refused, notehead_is_a_duplicate_box -- e.g. p1 sys0 staff9 cell14 glyph3
- 186 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p2 sys0 staff2 cell12 glyph3

## 8. Regression guards

- judged: right 113, wrong 26, narrowed 9, abstained 1, not_found 13, unscored 119 (Sean's past answers on the tiles that fall on this record)  (previous: right 104, wrong 39, narrowed 5, abstained 1, not_found 13, unscored 119 (Sean's past answers on the tiles that fall on this record))
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

78 of 78 rows balance. No imbalance.


