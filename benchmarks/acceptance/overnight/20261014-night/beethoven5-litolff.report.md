# Re-gather report: Beethoven 5 mvt 1 (Litolff scan), 20261014-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Beethoven 5 mvt 1 (Litolff scan), 20261013-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

## 0. One screen

### Run

- **tree**: 8b9eb97c (previous: ca46eae4)
- **landings since the previous night**:
  - 117 commits (merges left out); the newest 15:
  - 8b9eb97c 2.133: flags rows for OMR_MARK_SHAPE_LINE_REMOVED (OFF)
  - 58ef640c 2.133: rebuild the judged index
  - a9dbc32a land 2.133 with OMR_MARK_SHAPE_LINE_REMOVED OFF: ROADMAP, DECISIONS, version_memory
  - 2a3eaa4f land 2.132 with OMR_STACKED_HOLLOW_PAIR OFF: ROADMAP, DECISIONS, version_memory
  - 728c7049 ROADMAP START HERE after 2026-10-15 (manager session 10-13->15)
  - 0efd4c46 2.132: FINDINGS (written by the manager from the lane report)
  - b0a916c5 2.132: stem reach of the pair (longest of the stems at an edge), Litolff fixtures, flags rows, ROADMAP, version_memory, probes, 15 blind tiles
  - 1cb659a0 2.132: OMR_STACKED_HOLLOW_PAIR (default OFF) -- a hollow second head a third apart, kept where two hollow slots on the page raster and a stem past the pair agree
  - 0fc874cb 2.133: Sean -- all 8 Litolff candidates are round staccato dots
  - 67185a50 2.133: page-raster mark shape with the staff line bridged out (OMR_MARK_SHAPE_LINE_REMOVED, OFF, measurement only), FINDINGS 8, Litolff round-dot candidates
  - 2c240ed7 2.131: rebuild the judged index (Sean's 2.131 answers)
  - 60481b2e 2.131: off-test sets the flag off explicitly
  - 8284fef9 2.131: land OMR_STACCATISSIMO_SHAPE ON (Sean: 1), flags row, DECISIONS, ROADMAP, version_memory
  - 25f11185 ROADMAP 2.133: claim staccatissimo shape with the staff line removed at the mark
  - 5052f006 2.131: Sean's answers, FINDINGS 7 (tip sharpness does not separate yet), row-width profile on Q.MARK_SHAPE
- **flags/settings that differ from defaults**:
  - OMR_SURYA_KEEP_ALIVE=0
- **weights**: --weights auto (weight routing off)
- **pages**: 1-16
- **wall time**: 65 min (gather through INFER; exit 0) (previous: 55 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| parts in the file | 12 | 12 |
| staves named (staff rows over all systems) | 203 (not named: 128) | 203 (not named: 128) |
| staves held out (counted, not placed in a part) | 0 | 0 |
| meter, per system: read / carried / guessed / narrowed / abstained | 1 / 30 / 0 / 0 / 0 | 1 / 30 / 0 / 0 / 0 |
| key, per staff and system: read / carried / guessed / narrowed / abstained | 136 / 0 / 195 / 0 / 0 | 136 / 0 / 195 / 0 / 0 |
| clef, per staff and system: read / carried / guessed / narrowed / abstained | 317 / 0 / 11 / 3 / 0 | 317 / 0 / 11 / 3 / 0 |
| bars marked unread (red) | 1,539 (-13) | |
| MusicXML written | yes 3.8 MB | yes |
| LilyPond written / compiled / warnings | yes / yes / 24 | NO (tools.omr.staged.export.Unbalanced: lilypond: 14272 noteheads+rests in the log, 8059 written and 6338 accounted as dropped -- the difference went nowhere. {) / n/a / n/a |

### Biggest movers since the previous night

| row | was | now | change |
|---|---|---|---|
| articulations / no verdict | 447 | 0 | -447 |
| articulations / boxes | 465 | 18 | -447 |
| bars / held out | 861 | 699 | -162 |
| blue guessed / rests | 0 | 56 | +56 |
| blue guessed / total | 1,527 | 1,818 | +291 |
| export not written / bar_does_not_add_up | 1,973 | 1,662 | -311 |
| blue guessed / notes | 1,492 | 1,727 | +235 |
| blue guessed by rule / reconcile_duration | 201 | 225 | +24 |
| blue guessed by rule / fill_clef_gap | 170 | 189 | +19 |
| blue guessed by rule / collapse_bare_stem_by_bar | 86 | 100 | +14 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 3,558 (-1) | all notes written, none guessed |
| written with guesses | 963 (+14) | written; at least one note/dynamic is a guess (blue) |
| partial | 161 | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 699 (-162) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 679 (-12) | nothing read in this bar; padded and marked red |
| **total bars (parts x measures)** | 6,060 | |

- bars: in 6,060 = unread, empty 679, written plain 3,558, held out 699, partial 161, written with guesses 963 (sum 6,060) -> balanced
- check, partial bars: file vs exporter: file 161, exporter 161 -> agrees
- check, held-out bars (named + doubled-staff copies): file vs exporter: file 699, exporter 699 -> agrees
- check, unread-empty bars: file vs exporter: file 679, exporter 679 -> agrees
- check, unread-empty bars named by the exporter: file vs exporter: file 679, exporter 679 -> agrees

Bars with notes read off the page: 5,034 (+12). Tacet bars padded with rests (written, not unread): 347. Meter: 0 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 190, short_without_an_unread_symbol 408, nothing_before_or_after_the_gap 42.

Red marks written: 1539. Equation: empty 679 + held out 699 + partial 161 = 1539 (the partial bars carry 163 red bracketed gaps) -> balanced.

## 2. Symbols: what happens to each kind at each stage

GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.

### 2a. Per symbol kind, at glyph level (computed here from the record)

| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |
|---|---|---|---|---|---|---|---|---|
| noteheads: how long | 11,399 | 1,549 | 8,202 (+12) | 331 (-12) | 1,317 | 0 | 2,392 (+22) | balanced |
| noteheads: which pitch | 11,399 | 1,549 | 9,755 | 0 | 0 | 95 | 2,380 (+22) | balanced |
| rests | 2,873 +125 | 598 | 2,280 | 22 | 98 | 0 | 0 | balanced |
| accidentals | 1,508 | 0 | 648 | 0 | 860 | 0 | 0 | balanced |
| slurs | 1,225 | 5 | 1,213 | 0 | 7 | 0 | 0 | balanced |
| ties | 1,419 | 498 | 921 | 0 | 0 | 0 | 0 | balanced |
| articulations | 18 (-447) | 11 | 3 | 1 | 3 | 0 (-447) | 0 | balanced |
| dots | 601 | 0 | 459 | 0 | 142 | 0 | 0 | balanced |
| fermatas | 178 | 0 | 156 | 0 | 22 | 0 | 0 | balanced |
| ornaments | 3 | 0 | 2 | 0 | 1 | 0 | 0 | balanced |
| hairpins | 0 +5 | 0 | 5 | 0 | 0 | 0 | 0 | balanced |

Is-it-really-one refusals for every family, from the exporter's own `family_refusals` (kept / refused / abstained):

- ledger_is_not_a_ledger: kept 1,761, refused 5,919, abstained 21 (inside_the_staff 5199, on_a_staff_line 693, no_head_on_the_rung 25)
- accidental_is_not_an_accidental: kept 1,508, refused 0, abstained 0
- rest_is_not_a_rest: kept 2,275, refused 598, abstained 0 (rest_has_a_stem 120, rest_is_a_duplicate_box 104, rest_touches_two_staff_lines 98)
- arpeggiato_is_not_an_arpeggiato: kept 1,876, refused 21, abstained 0 (in_a_key_signature_slot 21)
- arc_is_not_an_arc: kept 2,141, refused 503, abstained 0 (ink_is_a_staff_line 502, in_a_key_signature_slot 1)
- dynamic_is_not_a_dynamic: kept 1,589, refused 0, abstained 0
- articulation_is_not_an_articulation: kept 7, refused 11, abstained 0 (ledger_between_staff_and_note 11)
- flag_is_not_a_flag: kept 252, refused 2, abstained 0 (in_a_key_signature_slot 2)
- keysig_marker_is_not_a_marker: kept 528, refused 0, abstained 0
- tuplet_marker_is_not_a_marker: kept 13, refused 0, abstained 0

Top reasons per kind (refused, narrowed, abstained):

- **noteheads: how long** (each detected notehead box: is it a real notehead, and what length is it): refused stacked_head_duplicate 448; refused clipped_fragment 342; refused too_narrow 258; abstained: owned_by_another_staff 1317; narrowed: beam_discounted_uncertain 244; narrowed: beams_ambiguous 54; narrowed: head_fill_from_ink 19
- **noteheads: which pitch** (the same boxes: which line or space, and so which note name): refused stacked_head_duplicate 448; refused clipped_fragment 342; refused too_narrow 258
- **rests** (each detected rest box: is it a real rest, and what length): refused rest_has_a_stem 120; refused rest_is_a_duplicate_box 104; refused rest_touches_two_staff_lines 98; abstained: rest_stands_where_no_rest_hangs 98; narrowed: rest_slot_contradicts_class 22
- **accidentals** (sharps/flats/naturals: which notehead they belong to): abstained: no_candidate 717; abstained: is_a_key_signature_marker 123; abstained: ambiguous_height 14; abstained: head_belongs_to_a_nearer_staff 6
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
| direction words (one verdict per inked cell; most say no word is there) | 0 | 5,377 | 0 | 0 | 0 | 5,376 (+5,376) | 0 | 1 | 0 (-5,376) | balanced |
| dynamic words (one verdict per inked cell (most say no dynamic); the boxes are single letters) | 1,589 | 5,377 | 0 | 0 | 0 | 5,342 (+5,342) | 17 | 18 | 0 (-5,342) | balanced |
| tuplet ratios (the 3 over a triplet) | 13 | 12 | 0 | 0 | 0 | 3 (+3) | 0 | 9 | 0 (-3) | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detector boxes | decided | abstained | written to the file | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 1,508 | 648 | 860 | 360 (+14) | n/a | emitted |
| articulation | 18 (-447) | 13 | 5 | 3 | n/a | emitted |
| clef | 513 | 328 | 14 | 0 | n/a | emitted |
| direction | 0 | 5,376 | 1 | 74 | n/a | emitted |
| dot | 601 | 459 | 142 | 346 | n/a | emitted |
| dynamic | 1,589 | 5,342 | 35 | 558 | 35 | emitted |
| fermata | 178 | 156 | 22 | 77 (+3) | n/a | emitted |
| key | 542 | 331 | 195 | 0 | n/a | emitted |
| note | 11,399 | 15,091 | 0 | 6,595 (+234) | 1727 | emitted |
| ornament | 3 | 2 | 1 | 0 (-1) | n/a | decided_but_unwritten |
| rest | 2,873 | 0 | 0 | 2,169 (+55) | 56 | abstained |
| slur | 1,225 | 1,055 | 0 | 184 (+3) | n/a | emitted |
| tie | 1,419 | 1,582 | 0 | 223 (+4) | n/a | emitted |
| time | 82 | 31 | 0 | 0 | n/a | emitted |
| tuplet | 13 | 3 | 9 | 0 | n/a | emitted |
| wedge | 0 | 5 | 0 | 0 | n/a | decided_but_unwritten |


(`rest` reads 'abstained' only because the exporter has no separate rest verdict; rests are read, see 2a. `decided` counts verdicts, which can exceed boxes where one box has several.)

- export: events in the log -> file: in 14,397 = written 8,345, not written (reasons below) 6,052 (sum 14,397) -> balanced
(Of the written events, 417 notes were doubled onto a condensed slot and 2 rests duplicated across voices; the exporter nets those out.)

Notes and rests not written, by reason (top 12):

- bar_does_not_add_up: 1,662 (-311)
- owned_by_another_staff: 1,331
- not_a_notehead:stacked_head_duplicate: 448
- not_a_notehead:clipped_fragment: 342
- duration_narrowed: 298 (-13)
- not_a_notehead:too_narrow: 258
- not_a_notehead:notehead_is_a_duplicate_box: 257
- mark_group_duplicate: 145
- not_a_rest:rest_has_a_stem: 120
- ink_is_a_whole_rest: 109
- not_a_rest:rest_is_a_duplicate_box: 104
- not_a_rest:rest_touches_two_staff_lines: 98

Two stages, one fact: the record's refusals (ADJUDICATE) against the exporter's drop reasons of the same name: 23 of 23 reasons agree exactly.

Every standing glyph verdict of the quantities above is in a row, on a refused box, or on a box of a kind no row covers: 9 of 9 quantities account for all their verdicts.
- pitch: 2,309 of 13,603 verdicts sit on boxes of another kind (e.g. a pitch computed for a rest box) -- listed, not hidden

Kept boxes that nothing was asked about (no verdict): noteheads: which pitch 95.

## 3. How sure are the guesses

Blue items written: **1,818 (+291)** (notes 1,727 (+235), rests 56 (+56), dynamics 35). By the rule that guessed:

- fill_part_key: 1,008 (+34) (a pitch read through a key signature that was inferred for the part)
- reconcile_duration: 225 (+24) (length chosen only because the bar then adds up)
- fill_clef_gap: 189 (+19) (a pitch read through a clef that was inferred)
- collapse_bare_stem_by_bar: 100 (+14) (a stem with no flag/beam seen, length chosen by the bar)
- collapse_narrowed_by_bar: 62 (+2) (length narrowed to a few candidates, one chosen by the bar)
- dynamic_with_an_unread_letter: 35 (a dynamic word with a letter that could not be read)
- collapse_arc_ink_not_beam: 5 
- collapse_duration_to_barline: 1 (length chosen to run to the barline)

Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the readable notes either side of an unread gap):

- onset_from_partial_bar_prefix: 68
- onset_from_partial_bar_suffix: 125

Of the guesses INFER made (record): 424 standing. Candidates it chose between: {'2': 219, '3': 5, '0': 199, '4': 1}. Evidence gap between the chosen candidate and the runner-up: {'gap 1': 194, 'tie': 31, 'one candidate': 199} ('tie' = the chosen value had no more support than another).
Durations that are guesses at glyph level: 2184; of those, settled by the bar's arithmetic alone (the weakest witness): 225.

**Refusals and how close they came** (2.106): 31792 refusals/narrowings in the record, 420 carry a margin, **31372 carry none** (rules not yet covered, or structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, since most rules declare no band). Biggest groups:

| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |
|---|---|---|---|---|---|---|---|---|
| unboxed_ink_is_a_rest | shape_cannot_tell | abstained | 185 | 185 | 62 | 61 | 62 | -0.009 at p16 sys1 staff7 cell5 glyph350000 |
| duration | head_fill_from_ink | narrowed | 136 | 113 | 46 | 22 | 68 | 0 at p5 sys0 staff4 cell15 glyph3 |
| unboxed_ink_is_a_rest | claimed_by_another_class | abstained | 82 | 81 | 28 | 26 | 28 | -0 at p16 sys1 staff3 cell7 glyph350000 |
| clef | margin_below_floor | narrowed | 10 | 0 | 7 | 0 | 3 | 0 at p4 sys0 staff8 |
| narrow_box_is_an_eighth_rest | shape_cannot_tell | abstained | 5 | 5 | 2 | 0 | 3 | -0.1 at p10 sys1 staff8 cell3 glyph3 |
| unboxed_ink_is_a_rest | head_beside_it | abstained | 2 | 2 | 1 | 0 | 1 | -0.13 at p5 sys0 staff6 cell5 glyph350000 |

## 4. Unknown and unread, in one place

- unread marks red: 1,539 (-13)
- staves held out unidentified: 0
- unidentified parts: 0
- noteheads owner not read: 8 (-1)
- noteheads no pitch: 95
- notes whose length stayed undecided (narrowed, abstained, chord): {'narrowed': 298, 'rest abstained': 98, 'chord undecided': 98}
- evidence the deciders asked for and did not find (record `adjudication.missing_evidence`, top 8): human_box_verdict 39,846, glyph_owner 24,643, rest 14,444, letter_look_cover 12,627, tuplet_ratio 12,595, aug_dot 11,525, head_line_cut 10,667, notehead_letter_ink 9,835

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 3,352 over 16 pages (about 210 per page). Previous: 3071.

Five worst pages: p15: 122 red + 193 blue; p4: 106 red + 184 blue; p14: 124 red + 156 blue; p6: 101 red + 142 blue; p2: 89 red + 147 blue.

Five worst staves (instrument, page): Viola p15: 13 red + 39 blue; Viola p4: 9 red + 41 blue; Viola p6: 9 red + 41 blue; Bassoon p16: 10 red + 39 blue; Bassoon p15: 11 red + 33 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Viola | 370 (-3) | 287 (+37) | 156 (-2) | 176 (-44) | 6 |
| Bassoon | 424 (-6) | 303 (+39) | 132 (-4) | 173 (-38) | 2 |
| Violin [P8] | 632 (-5) | 250 (+34) | 104 (-1) | 187 (-36) | 4 |
| Violin [P9] | 597 (-7) | 211 (+18) | 127 | 169 (-23) | 6 |
| Cello | 329 (-9) | 151 (+35) | 170 (-1) | 145 (-37) | 4 |
| Flute | 362 (-3) | 154 (+25) | 130 (-1) | 148 (-28) | 5 |
| Oboe | 356 (-1) | 146 (+22) | 124 (-1) | 185 (-23) | 1 |
| Contrabass | 322 (-2) | 101 (+6) | 128 (-1) | 26 (-3) | 0 |
| Clarinet | 579 (-1) | 75 (+35) | 146 (-1) | 198 (-36) | 3 |
| Horn | 328 (-16) | 54 (+24) | 113 (+3) | 124 (-23) | 7 |
| Trumpet | 355 | 30 (+11) | 102 (-2) | 63 (-15) | 1 |
| Timpani | 158 (-4) | 21 (+5) | 109 | 68 (-5) | 0 |

## 6. Detected, then dropped

Detector boxes whose class no family reads (never reach a decision): {'arpeggiato': 1897, 'stringsDownBow': 3, 'caesura': 3, 'segno': 1} (of 37,137 boxes).
Detected and unrepresented in the record: none. Decided but not written to the file: {'ornament': 3, 'wedge': 5}.
Ink rows no class explains (Q.INK): 5377.

## 7. The top reasons, with one place to look

(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)

- 1,317 x noteheads: how long: abstained: owned_by_another_staff -- e.g. p1 sys0 staff4 cell3 glyph1
- 717 x accidentals: abstained: no_candidate -- e.g. p1 sys0 staff2 cell6 glyph0
- 640 x bar held out: does not add up -- e.g. p1 sys0 staff0 cell3 (bar 4, part P1)
- 497 x ties: refused, ink_is_a_staff_line -- e.g. p1 sys0 staff1 cell7 glyph1
- 448 x noteheads: how long: refused, stacked_head_duplicate -- e.g. p1 sys0 staff3 cell7 glyph2
- 408 x bar stays held: short_without_an_unread_symbol -- e.g. p2 sys0 staff0 cell5 (bar 22, part P1)
- 342 x noteheads: how long: refused, clipped_fragment -- e.g. p1 sys0 staff3 cell3 glyph2
- 258 x noteheads: how long: refused, too_narrow -- e.g. p1 sys0 staff2 cell0 glyph9
- 257 x noteheads: how long: refused, notehead_is_a_duplicate_box -- e.g. p1 sys0 staff8 cell14 glyph5
- 244 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p1 sys0 staff7 cell1 glyph1

## 8. Regression guards

- judged: right 108, wrong 11, narrowed 4, abstained 1, not_found 13, unscored 97 (Sean's past answers on the tiles that fall on this record)  (previous: right 107, wrong 12, narrowed 4, abstained 1, not_found 13, unscored 97 (Sean's past answers on the tiles that fall on this record))
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

75 of 75 rows balance. No imbalance.


