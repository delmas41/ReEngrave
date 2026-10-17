# Re-gather report: Brahms 1 mvt 1 (Breitkopf scan), 20261016-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Brahms 1 mvt 1 (Breitkopf scan), 20261014-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

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
- **pages**: 0-26
- **wall time**: 243 min (gather through INFER; exit 0) (previous: 230 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| parts in the file | 14 | 14 |
| staves named (staff rows over all systems) | 684 (not named: 7) | 684 (not named: 7) |
| staves held out (counted, not placed in a part) | 0 | 0 |
| meter, per system: read / carried / guessed / narrowed / abstained | 2 / 41 / 0 / 0 / 6 | 2 / 31 / 0 / 0 / 11 |
| key, per staff and system: read / carried / guessed / narrowed / abstained | 478 / 0 / 213 / 0 / 0 | 478 / 0 / 213 / 0 / 0 |
| clef, per staff and system: read / carried / guessed / narrowed / abstained | 690 / 0 / 1 / 0 / 0 | 690 / 0 / 1 / 0 / 0 |
| bars marked unread (red) | 1,823 (-492) | |
| MusicXML written | yes 6.6 MB | yes |
| LilyPond written / compiled / warnings | yes / yes / 143 | yes / yes / 124 |

### Biggest movers since the previous night

| row | was | now | change |
|---|---|---|---|
| blue guessed by rule / collapse_arc_ink_not_beam | 604 | 8 | -596 |
| export not written / duration_narrowed | 2,324 | 1,242 | -1,082 |
| noteheads: how long / narrowed | 2,330 | 1,249 | -1,081 |
| bars / unread empty padded | 598 | 393 | -205 |
| bars / unread, empty | 598 | 393 | -205 |
| noteheads: how long / guessed at glyph level | 2,560 | 1,771 | -789 |
| noteheads: which pitch / guessed at glyph level | 2,560 | 1,771 | -789 |
| export tie / written | 476 | 656 | +180 |
| blue guessed / rests | 675 | 528 | -147 |
| bars / unread marks in file | 2,315 | 1,823 | -492 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 4,577 (+717) | all notes written, none guessed |
| written with guesses | 673 (-140) | written; at least one note/dynamic is a guess (blue) |
| partial | 586 (-156) | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 844 (-131) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 393 (-205) | nothing read in this bar; padded and marked red |
| **total bars (parts x measures)** | 7,073 (+85) | |

- bars: in 7,073 = written plain 4,577, partial 586, held out 844, written with guesses 673, unread, empty 393 (sum 7,073) -> balanced
- bar numbers that repeat inside a part (endings): [189, 190]; 28 bars sit on them. The exporter's held/partial lists are keyed by bar number, so they cannot tell the two apart.
- check, partial bars: file vs exporter: file 586, exporter 586 -> agrees
- check, held-out bars (named + doubled-staff copies): file vs exporter: file 844, exporter 844 -> agrees
- check, unread-empty bars: file vs exporter: file 393, exporter 393 -> agrees
- check, unread-empty bars named by the exporter: file vs exporter: file 393, exporter 393 -> agrees

Bars with notes read off the page: 6,278 (+205). Tacet bars padded with rests (written, not unread): 402 (+85). Meter: 710 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 435, short_without_an_unread_symbol 265, nothing_before_or_after_the_gap 144.

Red marks written: 1823. Equation: empty 393 + held out 844 + partial 586 = 1823 (the partial bars carry 605 red bracketed gaps) -> balanced.

## 2. Symbols: what happens to each kind at each stage

GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.

### 2a. Per symbol kind, at glyph level (computed here from the record)

| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |
|---|---|---|---|---|---|---|---|---|
| noteheads: how long | 24,260 | 4,700 (+105) | 15,249 (+977) | 1,249 (-1,081) | 3,062 (-1) | 0 | 1,771 (-789) | balanced |
| noteheads: which pitch | 24,260 | 4,700 (+105) | 19,560 (-105) | 0 | 0 | 0 | 1,771 (-789) | balanced |
| rests | 8,129 +455 | 1,920 (+112) | 6,616 (-107) | 0 | 48 | 0 | 0 | balanced |
| accidentals | 6,544 | 0 | 4,435 | 0 | 2,109 | 0 | 0 | balanced |
| slurs | 3,148 | 84 | 3,044 | 0 | 20 | 0 | 0 | balanced |
| ties | 11,666 | 7,866 | 3,800 | 0 | 0 | 0 | 0 | balanced |
| articulations | 1,474 (+211) | 23 | 868 (+140) | 8 | 575 (+71) | 0 | 0 | balanced |
| dots | 9,740 (+66) | 0 | 9,126 (+63) | 0 | 614 (+3) | 0 | 0 | balanced |
| fermatas | 12 | 0 | 11 | 0 | 1 | 0 | 0 | balanced |
| ornaments | 24 | 0 | 10 | 0 | 14 | 0 | 0 | balanced |
| hairpins | 2 +276 | 0 | 274 | 0 | 4 | 0 | 0 | balanced |

Is-it-really-one refusals for every family, from the exporter's own `family_refusals` (kept / refused / abstained):

- ledger_is_not_a_ledger: kept 6,305, refused 1,500, abstained 20 (inside_the_staff 1212, on_a_staff_line 287, no_head_on_the_rung 1)
- accidental_is_not_an_accidental: kept 6,544, refused 0, abstained 0
- rest_is_not_a_rest: kept 6,209, refused 1,920, abstained 0 (rest_is_a_duplicate_box 863, rest_clipped_by_crop 544, rest_outside_its_staff 138)
- arpeggiato_is_not_an_arpeggiato: kept 839, refused 21, abstained 0 (in_a_key_signature_slot 21)
- arc_is_not_an_arc: kept 6,864, refused 7,950, abstained 0 (ink_is_a_staff_line 7944, in_a_key_signature_slot 6)
- dynamic_is_not_a_dynamic: kept 3,941, refused 0, abstained 0
- articulation_is_not_an_articulation: kept 1,449, refused 23, abstained 2 (ledger_between_staff_and_note 23)
- flag_is_not_a_flag: kept 3,033, refused 0, abstained 0
- keysig_marker_is_not_a_marker: kept 1,327, refused 0, abstained 0
- tuplet_marker_is_not_a_marker: kept 4, refused 0, abstained 0

Top reasons per kind (refused, narrowed, abstained):

- **noteheads: how long** (each detected notehead box: is it a real notehead, and what length is it): refused too_narrow 3407; refused clipped_fragment 593; refused stacked_head_duplicate 167; abstained: owned_by_another_staff 3062; narrowed: beam_discounted_uncertain 1024; narrowed: beams_ambiguous 105; narrowed: dot_seen_beside_a_plain_note 38
- **noteheads: which pitch** (the same boxes: which line or space, and so which note name): refused too_narrow 3407; refused clipped_fragment 593; refused stacked_head_duplicate 167
- **rests** (each detected rest box: is it a real rest, and what length): refused rest_is_a_duplicate_box 863; refused rest_clipped_by_crop 544; refused rest_outside_its_staff 138; abstained: rest_stands_where_no_rest_hangs 31; abstained: unreadable_rest 17
- **accidentals** (sharps/flats/naturals: which notehead they belong to): abstained: no_candidate 1790; abstained: is_a_key_signature_marker 283; abstained: ambiguous_height 32; abstained: head_belongs_to_a_nearer_staff 4
- **slurs** (curved lines read as slurs): refused ink_is_a_staff_line 82; refused in_a_key_signature_slot 2; abstained: same_pitch_accidental_unread 17; abstained: stack_slur_over_two_same_pitch_notes 3
- **ties** (curved lines read as ties): refused ink_is_a_staff_line 7862; refused in_a_key_signature_slot 4
- **articulations** (accents, tenuto, staccatissimo: which note): refused ledger_between_staff_and_note 23; abstained: no_notehead 483; abstained: owned_by_another_staff 35; abstained: stem_direction_unread 29; abstained: stem_contradicts_class_side 19
- **dots** (small dots: lengthening a note or marking it short (staccato)): abstained: dot_role_ambiguous 482; abstained: wedge_without_a_head 77; abstained: on_a_stroke 42; abstained: on_a_barline 8
- **fermatas** (fermatas: which note): abstained: no_carrier 1
- **ornaments** (trills, turns, tremolo): abstained: no_notehead 14
- **hairpins** (crescendo/diminuendo wedges): abstained: no_page_frame 2; abstained: no_anchor 2

### 2b. Readings that belong to a staff or system, not to one box

| reading | boxes | verdicts | read | carried | guessed (INFER) | decided (yes/no) | narrowed | abstained | other | balance |
|---|---|---|---|---|---|---|---|---|---|---|
| clefs (one per staff and system) | 1,102 | 691 | 690 | 0 | 1 | 0 | 0 | 0 | 0 | balanced |
| key signatures (one per staff and system) | 1,354 | 691 | 478 | 0 | 213 | 0 | 0 | 0 | 0 | balanced |
| meters (time signatures) (one per system) | 518 | 53 | 2 | 41 (+10) | 0 | 0 | 0 | 6 (-5) | 4 (-5) | balanced |
| instrument names (one per staff) | 0 | 691 | 684 | 0 | 0 | 0 | 0 | 7 | 0 | balanced |
| direction words (one verdict per inked cell; most say no word is there) | 0 | 6,685 | 0 | 0 | 0 | 6,682 | 0 | 3 | 0 | balanced |
| dynamic words (one verdict per inked cell (most say no dynamic); the boxes are single letters) | 3,941 | 6,685 | 0 | 0 | 0 | 6,606 (+7) | 18 (-5) | 61 (-2) | 0 | balanced |
| tuplet ratios (the 3 over a triplet) | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detector boxes | decided | abstained | written to the file | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 6,544 | 4,435 | 2,109 | 2,014 (+224) | n/a | emitted |
| articulation | 1,474 (+211) | 882 (+140) | 601 (+71) | 645 (+107) | n/a | emitted |
| clef | 1,102 | 691 | 1 | 0 | n/a | emitted |
| direction | 0 | 6,682 | 3 | 366 (+1) | n/a | emitted |
| dot | 9,740 (+66) | 9,126 (+63) | 614 (+3) | 2,104 (+108) | n/a | emitted |
| dynamic | 3,941 | 6,606 (+7) | 79 (-7) | 1,074 (-7) | 79 | emitted |
| fermata | 12 | 11 | 1 | 6 | n/a | emitted |
| key | 1,354 | 691 | 213 | 0 | n/a | emitted |
| note | 24,260 | 39,789 (+109) | 0 | 12,152 (+1,234) | 2009 | emitted |
| ornament | 24 | 10 | 14 | 8 (+1) | n/a | emitted |
| rest | 8,129 | 0 | 0 | 5,725 (+254) | 528 | abstained |
| slur | 3,148 | 2,589 | 0 | 623 (+91) | n/a | emitted |
| tie | 11,666 | 12,205 | 0 | 656 (+180) | n/a | emitted |
| time | 518 | 47 (+5) | 6 (-5) | 0 | n/a | emitted |
| tuplet | 4 | 0 | 4 | 0 | n/a | abstained |
| wedge | 2 | 274 | 4 | 122 (+53) | n/a | emitted |


(`rest` reads 'abstained' only because the exporter has no separate rest verdict; rests are read, see 2a. `decided` counts verdicts, which can exceed boxes where one box has several.)

- export: events in the log -> file: in 32,844 = written 17,847, not written (reasons below) 14,997 (sum 32,844) -> balanced
(Of the written events, 0 notes were doubled onto a condensed slot and 30 rests duplicated across voices; the exporter nets those out.)

Notes and rests not written, by reason (top 12):

- bar_does_not_add_up: 3,549 (-549)
- not_a_notehead:too_narrow: 3,315
- owned_by_another_staff: 3,055 (-4)
- duration_narrowed: 1,242 (-1,082)
- not_a_rest:rest_is_a_duplicate_box: 863
- not_a_notehead:clipped_fragment: 593
- not_a_rest:rest_clipped_by_crop: 544
- unread_gap_in_partial_bar: 233 (-49)
- chord_value_undecided: 211 (-2)
- not_a_notehead:stacked_head_duplicate: 167 (-4)
- not_a_notehead:tremolo_slash_crosses_stem: 160 (+48)
- not_a_rest:rest_outside_its_staff: 138

Two stages, one fact: the record's refusals (ADJUDICATE) against the exporter's drop reasons of the same name: 28 of 28 reasons agree exactly.

Every standing glyph verdict of the quantities above is in a row, on a refused box, or on a box of a kind no row covers: 9 of 9 quantities account for all their verdicts.
- pitch: 11,701 of 35,961 verdicts sit on boxes of another kind (e.g. a pitch computed for a rest box) -- listed, not hidden

## 3. How sure are the guesses

Blue items written: **2,616 (-647)** (notes 2,009 (-493), rests 528 (-147), dynamics 79 (-7)). By the rule that guessed:

- fill_part_key: 700 (+95) (a pitch read through a key signature that was inferred for the part)
- reconcile_duration: 283 (-40) (length chosen only because the bar then adds up)
- dynamic_with_an_unread_letter: 79 (-7) (a dynamic word with a letter that could not be read)
- collapse_narrowed_by_bar: 54 (+53) (length narrowed to a few candidates, one chosen by the bar)
- collapse_bare_stem_by_bar: 14 (-15) (a stem with no flag/beam seen, length chosen by the bar)
- collapse_arc_ink_not_beam: 8 (-596) 
- fill_clef_gap: 4 (+1) (a pitch read through a clef that was inferred)

Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the readable notes either side of an unread gap):

- onset_from_partial_bar_prefix: 804 (-8)
- onset_from_partial_bar_suffix: 670 (-130)

Of the guesses INFER made (record): 294 standing. Candidates it chose between: {'3': 1, '0': 213, '2': 80}. Evidence gap between the chosen candidate and the runner-up: {'tie': 1, 'one candidate': 213, 'gap 1': 80} ('tie' = the chosen value had no more support than another).
Durations that are guesses at glyph level: 1523; of those, settled by the bar's arithmetic alone (the weakest witness): 283.

**Refusals and how close they came** (2.106): 81111 refusals/narrowings in the record, 707 carry a margin, **80404 carry none** (rules not yet covered, or structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, since most rules declare no band). Biggest groups:

| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |
|---|---|---|---|---|---|---|---|---|
| unboxed_ink_is_a_rest | claimed_by_another_class | abstained | 239 | 239 | 80 | 79 | 80 | -0.003 at p21 sys1 staff4 cell4 glyph350000 |
| duration | head_fill_from_ink | narrowed | 231 | 227 | 78 | 57 | 96 | 0 at p3 sys0 staff2 cell2 glyph22 |
| unboxed_ink_is_a_rest | shape_cannot_tell | abstained | 224 | 224 | 75 | 73 | 76 | -0.001 at p9 sys1 staff0 cell8 glyph350001 |
| narrow_box_is_an_eighth_rest | shape_cannot_tell | abstained | 12 | 12 | 4 | 3 | 5 | -0.016 at p9 sys0 staff8 cell8 glyph18 |
| clef | margin_below_floor | narrowed | 1 | 0 | 1 | 0 | 0 | 0 at p8 sys1 staff3 |

## 4. Unknown and unread, in one place

- unread marks red: 1,823 (-492)
- staves held out unidentified: 0
- unidentified parts: 0
- noteheads owner not read: 40
- notes whose length stayed undecided (narrowed, abstained, chord): {'narrowed': 1242, 'rest abstained': 48, 'chord undecided': 211}
- evidence the deciders asked for and did not find (record `adjudication.missing_evidence`, top 8): human_box_verdict 106,476, glyph_owner 81,631, rest 33,603, tuplet_ratio 27,888, letter_look_cover 26,852, notehead_staff_position 26,648, head_stem_reach 25,675, far_head_owner_ledger 23,519

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 4,444 over 27 pages (about 165 per page). Previous: 5577.

Five worst pages: p19: 90 red + 181 blue; p5: 80 red + 162 blue; p6: 92 red + 149 blue; p13: 93 red + 140 blue; p24: 73 red + 155 blue.

Five worst staves (instrument, page): Violin [P11] p19: 8 red + 42 blue; Clarinet p16: 7 red + 31 blue; Oboe p5: 3 red + 31 blue; Cello p5: 11 red + 23 blue; Cello p6: 9 red + 25 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Bassoon | 1,031 (+196) | 278 (-74) | 166 (-41) | 420 (-53) | 26 |
| Cello | 813 (+130) | 263 (-40) | 175 (-50) | 426 (-32) | 18 |
| Violin [P11] | 1,108 (+128) | 298 (-1) | 134 (-55) | 295 (-82) | 23 |
| Violin [P10] | 819 (+162) | 247 (-45) | 168 (-57) | 276 (-76) | 30 |
| Clarinet | 851 (+254) | 230 (-99) | 167 (-48) | 349 (-7) | 27 |
| Oboe | 761 (+227) | 237 (-73) | 159 (-48) | 337 (-55) | 30 |
| Flute | 541 (+112) | 198 (-44) | 170 (-18) | 274 (-4) | 15 |
| Viola | 1,196 (+152) | 225 (-46) | 135 (-44) | 299 (-63) | 26 |
| Contrabass | 487 (+101) | 196 (-38) | 147 (-34) | 260 (-38) | 13 |
| Horn [P6] | 787 (+152) | 98 (-58) | 113 (-30) | 208 (-35) | 5 |
| Horn [P7] | 376 (+92) | 88 (-64) | 116 (-17) | 153 (-12) | 9 |
| Contrabassoon | 312 (+85) | 114 (-35) | 74 (-29) | 75 (-18) | 5 |
| Timpani | 252 (+46) | 35 (+1) | 69 (-14) | 96 (-76) | 6 |
| Trumpet | 281 (+37) | 30 (-24) | 49 (-7) | 81 (+2) | 0 |

## 6. Detected, then dropped

Detector boxes whose class no family reads (never reach a decision): {'arpeggiato': 860, 'caesura': 36, 'ottavaBracket': 10, 'segno': 1} (of 98,940 boxes).
Detected and unrepresented in the record: none. Decided but not written to the file: none.
Ink rows no class explains (Q.INK): 6685.

## 7. The top reasons, with one place to look

(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)

- 7,862 x ties: refused, ink_is_a_staff_line -- e.g. p0 sys0 staff0 cell0 glyph25
- 3,407 x noteheads: how long: refused, too_narrow -- e.g. p0 sys0 staff0 cell4 glyph16
- 3,062 x noteheads: how long: abstained: owned_by_another_staff -- e.g. p0 sys0 staff0 cell6 glyph20
- 1,790 x accidentals: abstained: no_candidate -- e.g. p0 sys0 staff1 cell1 glyph18
- 1,024 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p0 sys0 staff0 cell2 glyph4
- 863 x rests: refused, rest_is_a_duplicate_box -- e.g. p0 sys0 staff7 cell0 glyph21
- 844 x bar held out: does not add up -- e.g. p1 sys0 staff0 cell0 (bar 8, part P1)
- 593 x noteheads: how long: refused, clipped_fragment -- e.g. p0 sys0 staff1 cell0 glyph18
- 544 x rests: refused, rest_clipped_by_crop -- e.g. p1 sys0 staff0 cell1 glyph21
- 483 x articulations: abstained: no_notehead -- e.g. p1 sys0 staff2 cell4 glyph9

## 8. Regression guards

- judged: right 101, wrong 14, narrowed 9, not_found 7, unscored 182 (Sean's past answers on the tiles that fall on this record)  (previous: right 77, wrong 27, narrowed 20, not_found 7, unscored 182 (Sean's past answers on the tiles that fall on this record))
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

80 of 80 rows balance. No imbalance.


