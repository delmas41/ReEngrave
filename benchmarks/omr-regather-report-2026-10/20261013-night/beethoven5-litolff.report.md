# Re-gather report: Beethoven 5 mvt 1 (Litolff scan), 20261013-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Beethoven 5 mvt 1 (Litolff scan), 20261011-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

## 0. One screen

### Run

- **tree**: ca46eae4; the export, LilyPond and this report were re-run on tree d5ba473c (previous: cb73dde2)
- **landings since the previous night**:
  - 139 commits (merges left out); the newest 15:
  - ca46eae4 ROADMAP 2.114: claim the second (hollow-only) detector at GATHER; Sean's interior-white rule
  - 14cd2946 ROADMAP 2.113: claim the clutter count (measure before a remove-what's-known view)
  - a31a2cca ROADMAP 2.112: claim the test-set leakage audit (2.110 found TEST cells in training)
  - 2892eb71 hand_truth inventory: declare v24 (2.4b hollow4 TRAIN, single-family:hollow, not admitted) -- fixes test_every_label_version_on_disk_has_a_declared_tier
  - 4863f784 Docs: ROADMAP START HERE landing order, version_memory for 2.108
  - 6d9f9207 Rebuild judged-tiles index after merging main
  - d10affe3 2.108: Sean's answers on the blind tiles; FINDINGS, DECISIONS, ROADMAP
  - abec2a05 ROADMAP 2.111: park the plate's-own notehead template idea (Sean: keep the idea)
  - 753e5dd7 2.108: off-staff reach 6 spaces (Sean: go with 6); re-measure, blind tiles, DECISIONS line
  - bb0be121 ROADMAP 2.110: claim the training-scale check (Sean: start with the training size check)
  - ad26d0d1 ROADMAP START HERE: Sean wants to revisit 2.4b hollow heads next session; ideas to weigh (two detectors, complete cells, combined round, resolution)
  - 04592685 2.108: FINDINGS, ROADMAP row, version_memory
  - 6f6c71c9 2.108: staged reach reads the vertical band only (record STAFF_EXTENT is the detector span; it refused 14 real Brahms p1 heads); prune-off-staff; probes + tiles
  - e450e31a Docs: ROADMAP 2.107 landed, START HERE landing order, version_memory
  - db798ecc Rebuild judged-tiles index after merging main
- **flags/settings that differ from defaults**:
  - OMR_SURYA_KEEP_ALIVE=0
- **weights**: --weights auto (weight routing off)
- **pages**: 1-16
- **wall time**: 55 min (gather through INFER; exit 0) (previous: 52 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| parts in the file | 12 | 12 |
| staves named (staff rows over all systems) | 203 (not named: 128) | 200 (not named: 131) |
| staves held out (counted, not placed in a part) | 0 | 6 |
| meter, per system: read / carried / guessed / narrowed / abstained | 1 / 30 / 0 / 0 / 0 | 1 / 30 / 0 / 0 / 0 |
| key, per staff and system: read / carried / guessed / narrowed / abstained | 136 / 0 / 195 / 0 / 0 | 137 / 0 / 190 / 0 / 4 |
| clef, per staff and system: read / carried / guessed / narrowed / abstained | 317 / 0 / 11 / 3 / 0 | 317 / 0 / 11 / 3 / 0 |
| bars marked unread (red) | 1,552 (-172) | |
| MusicXML written | yes 3.8 MB | yes |
| LilyPond written / compiled / warnings | yes / yes / 25 | yes / yes / 30 |

### Biggest movers since the previous night

| row | was | now | change |
|---|---|---|---|
| rests / added without a box | 0 | 125 | +125 |
| bars / tacet bars padded with rests | 539 | 347 | -192 |
| export not written / bar_does_not_add_up | 2,498 | 1,673 | -825 |
| bars / held out | 1,044 | 705 | -339 |
| rests / refused total | 478 | 598 | +120 |
| bars / written plain | 4,336 | 3,559 | -777 |
| export rest / written | 1,876 | 2,168 | +292 |
| noteheads: how long / narrowed | 392 | 343 | -49 |
| export accidental / written | 314 | 358 | +44 |
| export not written / duration_narrowed | 354 | 311 | -43 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 3,559 (-777) | all notes written, none guessed |
| written with guesses | 949 | written; at least one note/dynamic is a guess (blue) |
| partial | 156 | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 705 (-339) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 691 (+11) | nothing read in this bar; padded and marked red |
| **total bars (parts x measures)** | 6,060 | |

- bars: in 6,060 = unread, empty 691, written plain 3,559, held out 705, partial 156, written with guesses 949 (sum 6,060) -> balanced
- check, partial bars: file vs exporter: file 156, exporter 156 -> agrees
- check, held-out bars (named + doubled-staff copies): file vs exporter: file 705, exporter 705 -> agrees
- check, unread-empty bars: file vs exporter: file 691, exporter 691 -> agrees

Bars with notes read off the page: 5,022 (+181). Tacet bars padded with rests (written, not unread): 347 (-192). Meter: 0 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 191, short_without_an_unread_symbol 412, nothing_before_or_after_the_gap 43.

Red marks written: 1552. Equation: empty 691 + held out 705 + partial 156 = 1552 (the partial bars carry 158 red bracketed gaps) -> balanced.

## 2. Symbols: what happens to each kind at each stage

GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.

### 2a. Per symbol kind, at glyph level (computed here from the record)

| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |
|---|---|---|---|---|---|---|---|---|
| noteheads: how long | 11,399 | 1,549 (+6) | 8,190 (+45) | 343 (-49) | 1,317 (-2) | 0 | 2,370 (+35) | balanced |
| noteheads: which pitch | 11,399 | 1,549 (+6) | 9,755 (-6) | 0 | 0 | 95 | 2,358 (+28) | balanced |
| rests | 2,873 +125 | 598 (+120) | 2,280 (+5) | 22 | 98 | 0 | 0 | balanced |
| accidentals | 1,508 | 0 | 648 | 0 | 860 | 0 | 0 | balanced |
| slurs | 1,225 | 5 | 1,213 | 0 | 7 | 0 | 0 | balanced |
| ties | 1,419 | 498 | 921 | 0 | 0 | 0 | 0 | balanced |
| articulations | 465 | 11 | 3 | 1 | 3 | 447 | 0 | balanced |
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

- **noteheads: how long** (each detected notehead box: is it a real notehead, and what length is it): refused stacked_head_duplicate 448; refused clipped_fragment 342; refused too_narrow 258; abstained: owned_by_another_staff 1317; narrowed: beam_discounted_uncertain 262; narrowed: beams_ambiguous 54; narrowed: head_fill_from_ink 18
- **noteheads: which pitch** (the same boxes: which line or space, and so which note name): refused stacked_head_duplicate 448; refused clipped_fragment 342; refused too_narrow 258
- **rests** (each detected rest box: is it a real rest, and what length): refused rest_has_a_stem 120; refused rest_is_a_duplicate_box 104; refused rest_touches_two_staff_lines 98; abstained: rest_stands_where_no_rest_hangs 98; narrowed: rest_slot_contradicts_class 22
- **accidentals** (sharps/flats/naturals: which notehead they belong to): abstained: no_candidate 717; abstained: is_a_key_signature_marker 123; abstained: ambiguous_height 14; abstained: head_belongs_to_a_nearer_staff 6
- **slurs** (curved lines read as slurs): refused ink_is_a_staff_line 5; abstained: same_pitch_accidental_unread 5; abstained: stack_slur_over_two_same_pitch_notes 2
- **ties** (curved lines read as ties): refused ink_is_a_staff_line 497; refused in_a_key_signature_slot 1
- **articulations** (staccato dots, accents, tenuto: which note): refused ledger_between_staff_and_note 11; abstained: no_notehead 3; narrowed: heads_about_equally_near 1
- **fermatas** (fermatas: which note): abstained: no_carrier 21; abstained: owned_by_another_staff 1
- **ornaments** (trills, turns, tremolo): abstained: no_notehead 1

### 2b. Readings that belong to a staff or system, not to one box

| reading | boxes | verdicts | read | carried | guessed (INFER) | decided (yes/no) | narrowed | abstained | other | balance |
|---|---|---|---|---|---|---|---|---|---|---|
| clefs (one per staff and system) | 513 | 331 | 317 | 0 | 11 | 0 | 3 | 0 | 0 | balanced |
| key signatures (one per staff and system) | 542 | 331 | 136 (-1) | 0 | 195 (+5) | 0 | 0 | 0 (-4) | 0 | balanced |
| meters (time signatures) (one per system) | 82 | 31 | 1 | 30 | 0 | 0 | 0 | 0 | 0 | balanced |
| instrument names (one per staff) | 0 | 331 | 203 (+3) | 0 | 0 | 0 | 0 | 128 (-3) | 0 | balanced |
| direction words (words like cresc., dolce, one per word) | 0 | 5,377 | 0 | 0 | 0 | 0 | 0 | 1 (+1) | 5,376 (-1) | balanced |
| dynamic words (p, f, sf ... letters spelled into a word; the boxes are the letters) | 1,589 | 5,377 | 0 | 0 | 0 | 0 | 17 (+2) | 18 | 5,342 (-2) | balanced |
| tuplet ratios (the 3 over a triplet) | 13 | 12 | 0 | 0 | 0 | 0 | 0 | 9 | 3 | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detector boxes | decided | abstained | written to the file | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 1,508 | 648 | 860 | 358 (+44) | n/a | emitted |
| articulation | 465 | 13 | 5 | 3 | n/a | emitted |
| clef | 513 | 328 | 14 | 0 | n/a | emitted |
| direction | 0 | 5,376 (-1) | 1 (+1) | 74 (+6) | n/a | emitted |
| dynamic | 1,589 (+16) | 5,342 (-2) | 35 (+2) | 558 (+47) | 35 | emitted |
| fermata | 178 | 156 | 22 | 77 (+3) | n/a | emitted |
| key | 542 | 331 (+4) | 195 (+1) | 0 | n/a | emitted |
| note | 11,399 | 15,091 (-9) | 0 | 6,573 (+791) | 1701 | emitted |
| ornament | 3 | 2 | 1 | 1 (+1) | n/a | emitted |
| rest | 2,873 | 0 | 0 | 2,168 (+292) | 54 | abstained |
| slur | 1,225 | 1,055 (-2) | 0 | 184 (+18) | n/a | emitted |
| tie | 1,419 | 1,582 (+2) | 0 | 219 (+4) | n/a | emitted |
| time | 82 | 31 | 0 | 0 | n/a | emitted |
| tuplet | 13 | 3 | 9 | 0 | n/a | emitted |
| wedge | 0 | 5 | 0 | 0 | n/a | decided_but_unwritten |


(`rest` reads 'abstained' only because the exporter has no separate rest verdict; rests are read, see 2a. `decided` counts verdicts, which can exceed boxes where one box has several.)

- export: events in the log -> file: in 14,397 = written 8,324, not written (reasons below) 6,073 (sum 14,397) -> balanced
(Of the written events, 415 notes were doubled onto a condensed slot and 2 rests duplicated across voices; the exporter nets those out.)

Notes and rests not written, by reason (top 12):

- bar_does_not_add_up: 1,673 (-825)
- owned_by_another_staff: 1,331 (-2)
- not_a_notehead:stacked_head_duplicate: 448 (-19)
- not_a_notehead:clipped_fragment: 342
- duration_narrowed: 311 (-43)
- not_a_notehead:too_narrow: 258
- not_a_notehead:notehead_is_a_duplicate_box: 257
- mark_group_duplicate: 145 (-1)
- not_a_rest:rest_has_a_stem: 120 (-1)
- ink_is_a_whole_rest: 109 (-1)
- not_a_rest:rest_is_a_duplicate_box: 104 (-2)
- not_a_rest:rest_touches_two_staff_lines: 98

Two stages, one fact: the record's refusals (ADJUDICATE) against the exporter's drop reasons of the same name: 23 of 23 reasons agree exactly.

Every standing glyph verdict of the quantities above is in a row, on a refused box, or on a box of a kind no row covers: 8 of 8 quantities account for all their verdicts.
- pitch: 2,309 of 13,603 verdicts sit on boxes of another kind (e.g. a pitch computed for a rest box) -- listed, not hidden

Kept boxes that nothing was asked about (no verdict): noteheads: which pitch 95; articulations 447.

## 3. How sure are the guesses

Blue items written: **1,790** (notes 1,701, rests 54, dynamics 35). By the rule that guessed:

- fill_part_key: 1,005 (a pitch read through a key signature that was inferred for the part)
- reconcile_duration: 212 (length chosen only because the bar then adds up)
- fill_clef_gap: 189 (a pitch read through a clef that was inferred)
- collapse_bare_stem_by_bar: 100 (a stem with no flag/beam seen, length chosen by the bar)
- collapse_narrowed_by_bar: 60 (length narrowed to a few candidates, one chosen by the bar)
- dynamic_with_an_unread_letter: 35 (a dynamic word with a letter that could not be read)
- collapse_duration_to_barline: 1 (length chosen to run to the barline)

Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the readable notes either side of an unread gap):

- onset_from_partial_bar_prefix: 65
- onset_from_partial_bar_suffix: 123

Of the guesses INFER made (record): 407 standing. Candidates it chose between: {'2': 203, '3': 4, '0': 199, '4': 1}. Evidence gap between the chosen candidate and the runner-up: {'gap 1': 177, 'tie': 31, 'one candidate': 199} ('tie' = the chosen value had no more support than another).
Durations that are guesses at glyph level: 2162; of those, settled by the bar's arithmetic alone (the weakest witness): 214.

**Refusals and how close they came** (2.106): 31768 refusals/narrowings in the record, 408 carry a margin, **31360 carry none** (rules not yet covered, or structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, since most rules declare no band). Biggest groups:

| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |
|---|---|---|---|---|---|---|---|---|
| unboxed_ink_is_a_rest | shape_cannot_tell | abstained | 185 | 185 | 59 | 65 | 61 | -0.009 at p16 sys1 staff7 cell5 glyph350000 |
| duration | head_fill_from_ink | narrowed | 124 | 101 | 41 | 65 | 18 | 0 at p5 sys0 staff4 cell15 glyph3 |
| unboxed_ink_is_a_rest | claimed_by_another_class | abstained | 82 | 81 | 27 | 29 | 26 | -0 at p16 sys1 staff3 cell7 glyph350000 |
| clef | margin_below_floor | narrowed | 10 | 0 | 7 | 0 | 3 | 0 at p4 sys0 staff8 |
| narrow_box_is_an_eighth_rest | shape_cannot_tell | abstained | 5 | 5 | 1 | 3 | 1 | -0.1 at p10 sys1 staff8 cell3 glyph3 |
| unboxed_ink_is_a_rest | head_beside_it | abstained | 2 | 2 | 0 | 2 | 0 | -0.13 at p5 sys0 staff6 cell5 glyph350000 |

## 4. Unknown and unread, in one place

- unread marks red: 1,552 (-172)
- staves held out unidentified: 0 (-6)
- unidentified parts: 0
- noteheads owner not read: 9
- noteheads no pitch: 95
- notes whose length stayed undecided (narrowed, abstained, chord): {'narrowed': 311, 'rest abstained': 98, 'chord undecided': 98}
- evidence the deciders asked for and did not find (record `adjudication.missing_evidence`, top 8): human_box_verdict 39,846, glyph_owner 24,643, rest 14,444, letter_look_cover 12,627, tuplet_ratio 12,595, aug_dot 11,525, head_line_cut 10,667, notehead_letter_ink 9,835

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 3,337 over 16 pages (about 209 per page). Previous: 1724.

Five worst pages: p15: 122 red + 193 blue; p4: 106 red + 184 blue; p14: 125 red + 155 blue; p6: 102 red + 141 blue; p2: 90 red + 147 blue.

Five worst staves (instrument, page): Viola p15: 13 red + 39 blue; Viola p4: 9 red + 41 blue; Viola p6: 9 red + 41 blue; Bassoon p16: 10 red + 39 blue; Bassoon p15: 11 red + 33 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Viola | 370 (-223) | 285 (+285) | 158 (-14) | 178 (-73) | 6 |
| Bassoon | 423 (-193) | 300 (+300) | 136 (-27) | 173 (-110) | 2 |
| Violin [P8] | 633 (-185) | 245 (+245) | 105 (-19) | 190 (-75) | 4 |
| Violin [P9] | 598 (-158) | 210 (+210) | 127 (-17) | 169 (-69) | 6 |
| Cello | 330 (-37) | 147 (+147) | 172 (+13) | 147 (-43) | 4 |
| Flute | 362 (-104) | 152 (+152) | 131 (-22) | 148 (-81) | 5 |
| Oboe | 356 (-65) | 145 (+145) | 125 (-18) | 185 (-87) | 1 |
| Contrabass | 323 (-13) | 98 (+98) | 129 (+14) | 26 (-15) | 0 |
| Clarinet | 578 (-20) | 72 (+72) | 147 (-11) | 199 (-56) | 3 |
| Horn | 336 (+7) | 50 (+50) | 111 (-24) | 124 (-78) | 3 |
| Trumpet | 351 (+19) | 30 (+30) | 104 (-16) | 66 (-66) | 1 |
| Timpani | 158 (+8) | 21 (+21) | 109 (-29) | 68 (-72) | 0 |

## 6. Detected, then dropped

Detector boxes whose class no family reads (never reach a decision): {'arpeggiato': 1897, 'stringsDownBow': 3, 'caesura': 3, 'segno': 1} (of 37,137 boxes).
Detected and unrepresented in the record: none. Decided but not written to the file: {'wedge': 5}.
Ink rows no class explains (Q.INK): 5377.

## 7. The top reasons, with one place to look

(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)

- 1,317 x noteheads: how long: abstained: owned_by_another_staff -- e.g. p1 sys0 staff4 cell3 glyph1
- 717 x accidentals: abstained: no_candidate -- e.g. p1 sys0 staff2 cell6 glyph0
- 646 x bar held out: does not add up -- e.g. p1 sys0 staff0 cell3 (bar 4, part P1)
- 497 x ties: refused, ink_is_a_staff_line -- e.g. p1 sys0 staff1 cell7 glyph1
- 448 x noteheads: how long: refused, stacked_head_duplicate -- e.g. p1 sys0 staff3 cell7 glyph2
- 412 x bar stays held: short_without_an_unread_symbol -- e.g. p2 sys0 staff0 cell5 (bar 22, part P1)
- 342 x noteheads: how long: refused, clipped_fragment -- e.g. p1 sys0 staff3 cell3 glyph2
- 262 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p1 sys0 staff7 cell1 glyph1
- 258 x noteheads: how long: refused, too_narrow -- e.g. p1 sys0 staff2 cell0 glyph9
- 257 x noteheads: how long: refused, notehead_is_a_duplicate_box -- e.g. p1 sys0 staff8 cell14 glyph5

## 8. Regression guards

- judged: right 107, wrong 12, narrowed 4, abstained 1, not_found 13, unscored 97 (Sean's past answers on the tiles that fall on this record)  (previous: right 99, wrong 12, narrowed 6, abstained 1, not_found 19, unscored 97 (Sean's past answers on the tiles that fall on this record))
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

71 of 71 rows balance. No imbalance.

- exporter's own `dot_role_balance` says balanced = False: {'population': 601, 'attached_augmentation': 15, 'written_staccato': 364, 'attached_staccato_before_hold_out': 410, 'not_placed': 241}

