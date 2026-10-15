# Re-gather report: Brahms 1 mvt 1 (Breitkopf scan), 20261014-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Brahms 1 mvt 1 (Breitkopf scan), 20261013-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

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
- **pages**: 0-26
- **wall time**: 230 min (gather through INFER; exit 0) (previous: 201 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| parts in the file | 14 | 14 |
| staves named (staff rows over all systems) | 684 (not named: 7) | 684 (not named: 7) |
| staves held out (counted, not placed in a part) | 0 | 0 |
| meter, per system: read / carried / guessed / narrowed / abstained | 2 / 31 / 0 / 0 / 11 | 2 / 33 / 0 / 0 / 9 |
| key, per staff and system: read / carried / guessed / narrowed / abstained | 478 / 0 / 213 / 0 / 0 | 478 / 0 / 213 / 0 / 0 |
| clef, per staff and system: read / carried / guessed / narrowed / abstained | 690 / 0 / 1 / 0 / 0 | 690 / 0 / 1 / 0 / 0 |
| bars marked unread (red) | 2,315 (-191) | |
| MusicXML written | yes 6.8 MB | yes |
| LilyPond written / compiled / warnings | yes / yes / 124 | NO (tools.omr.staged.export.Unbalanced: lilypond: 32389 noteheads+rests in the log, 13818 written and 19021 accounted as dropped -- the difference went nowhere.) / n/a / n/a |

### Biggest movers since the previous night

| row | was | now | change |
|---|---|---|---|
| articulations / no verdict | 2,838 | 0 | -2,838 |
| blue guessed / rests | 9 | 675 | +666 |
| articulations / boxes | 4,101 | 1,263 | -2,838 |
| blue guessed / total | 1,034 | 3,263 | +2,229 |
| blue guessed / notes | 939 | 2,502 | +1,563 |
| bars / held out | 1,822 | 975 | -847 |
| export not written / bar_does_not_add_up | 6,192 | 4,098 | -2,094 |
| noteheads: which pitch / guessed at glyph level | 1,844 | 2,560 | +716 |
| noteheads: how long / guessed at glyph level | 1,844 | 2,560 | +716 |
| export slur / written | 384 | 532 | +148 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 3,860 (+7) | all notes written, none guessed |
| written with guesses | 813 (+188) | written; at least one note/dynamic is a guess (blue) |
| partial | 742 | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 975 (-847) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 598 (-85) | nothing read in this bar; padded and marked red |
| unread, repeated bar number | n/a | red mark on a bar whose number repeats (first/second ending): cannot be matched to the exporter's lists |
| **total bars (parts x measures)** | 6,988 | |

- bars: in 6,988 = written plain 3,860, written with guesses 813, partial 742, held out 975, unread, empty 598 (sum 6,988) -> balanced
- bar numbers that repeat inside a part (endings): [189, 190]; 28 bars sit on them. The exporter's held/partial lists are keyed by bar number, so they cannot tell the two apart.
- check, partial bars: file vs exporter: file 742, exporter 742 -> agrees
- check, held-out bars (named + doubled-staff copies): file vs exporter: file 975, exporter 975 -> agrees
- check, unread-empty bars: file vs exporter: file 598, exporter 598 -> agrees
- check, unread-empty bars named by the exporter: file vs exporter: file 598, exporter 598 -> agrees

Bars with notes read off the page: 6,073 (+86). Tacet bars padded with rests (written, not unread): 317. Meter: 1278 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 515, nothing_before_or_after_the_gap 241, short_without_an_unread_symbol 219.

Red marks written: 2315. Equation: empty 598 + held out 975 + partial 742 = 2315 (the partial bars carry 761 red bracketed gaps) -> balanced.

## 2. Symbols: what happens to each kind at each stage

GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.

### 2a. Per symbol kind, at glyph level (computed here from the record)

| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |
|---|---|---|---|---|---|---|---|---|
| noteheads: how long | 24,260 | 4,595 (-40) | 14,272 (+737) | 2,330 (-697) | 3,063 | 0 | 2,560 (+716) | balanced |
| noteheads: which pitch | 24,260 | 4,595 (-40) | 19,665 (+40) | 0 | 0 | 0 | 2,560 (+716) | balanced |
| rests | 8,129 +450 | 1,808 | 6,723 | 0 | 48 | 0 | 0 | balanced |
| accidentals | 6,544 | 0 | 4,435 (+6) | 0 | 2,109 (-6) | 0 | 0 | balanced |
| slurs | 3,148 | 84 | 3,044 | 0 | 20 | 0 | 0 | balanced |
| ties | 11,666 | 7,866 | 3,800 | 0 | 0 | 0 | 0 | balanced |
| articulations | 1,263 (-2,838) | 23 | 728 | 8 | 504 | 0 (-2,838) | 0 | balanced |
| dots | 9,674 | 0 | 9,063 | 0 | 611 | 0 | 0 | balanced |
| fermatas | 12 | 0 | 11 | 0 | 1 | 0 | 0 | balanced |
| ornaments | 24 | 0 | 10 | 0 | 14 | 0 | 0 | balanced |
| hairpins | 2 +276 | 0 | 274 | 0 | 4 | 0 | 0 | balanced |

Is-it-really-one refusals for every family, from the exporter's own `family_refusals` (kept / refused / abstained):

- ledger_is_not_a_ledger: kept 6,305, refused 1,500, abstained 20 (inside_the_staff 1212, on_a_staff_line 287, no_head_on_the_rung 1)
- accidental_is_not_an_accidental: kept 6,544, refused 0, abstained 0
- rest_is_not_a_rest: kept 6,321, refused 1,808, abstained 0 (rest_is_a_duplicate_box 863, rest_clipped_by_crop 544, rest_outside_its_staff 138)
- arpeggiato_is_not_an_arpeggiato: kept 839, refused 21, abstained 0 (in_a_key_signature_slot 21)
- arc_is_not_an_arc: kept 6,864, refused 7,950, abstained 0 (ink_is_a_staff_line 7944, in_a_key_signature_slot 6)
- dynamic_is_not_a_dynamic: kept 3,941, refused 0, abstained 0
- articulation_is_not_an_articulation: kept 1,238, refused 23, abstained 2 (ledger_between_staff_and_note 23)
- flag_is_not_a_flag: kept 3,033, refused 0, abstained 0
- keysig_marker_is_not_a_marker: kept 1,327, refused 0, abstained 0
- tuplet_marker_is_not_a_marker: kept 4, refused 0, abstained 0

Top reasons per kind (refused, narrowed, abstained):

- **noteheads: how long** (each detected notehead box: is it a real notehead, and what length is it): refused too_narrow 3407; refused clipped_fragment 593; refused stacked_head_duplicate 171; abstained: owned_by_another_staff 3063; narrowed: beam_discounted_uncertain 2173; narrowed: dot_seen_beside_a_plain_note 43; narrowed: beams_ambiguous 38
- **noteheads: which pitch** (the same boxes: which line or space, and so which note name): refused too_narrow 3407; refused clipped_fragment 593; refused stacked_head_duplicate 171
- **rests** (each detected rest box: is it a real rest, and what length): refused rest_is_a_duplicate_box 863; refused rest_clipped_by_crop 544; refused rest_outside_its_staff 138; abstained: rest_stands_where_no_rest_hangs 31; abstained: unreadable_rest 17
- **accidentals** (sharps/flats/naturals: which notehead they belong to): abstained: no_candidate 1790; abstained: is_a_key_signature_marker 283; abstained: ambiguous_height 32; abstained: head_belongs_to_a_nearer_staff 4
- **slurs** (curved lines read as slurs): refused ink_is_a_staff_line 82; refused in_a_key_signature_slot 2; abstained: same_pitch_accidental_unread 17; abstained: stack_slur_over_two_same_pitch_notes 3
- **ties** (curved lines read as ties): refused ink_is_a_staff_line 7862; refused in_a_key_signature_slot 4
- **articulations** (accents, tenuto, staccatissimo: which note): refused ledger_between_staff_and_note 23; abstained: no_notehead 424; abstained: owned_by_another_staff 32; abstained: stem_direction_unread 28; abstained: stem_contradicts_class_side 11
- **dots** (small dots: lengthening a note or marking it short (staccato)): abstained: dot_role_ambiguous 481; abstained: wedge_without_a_head 75; abstained: on_a_stroke 42; abstained: on_a_barline 8
- **fermatas** (fermatas: which note): abstained: no_carrier 1
- **ornaments** (trills, turns, tremolo): abstained: no_notehead 14
- **hairpins** (crescendo/diminuendo wedges): abstained: no_page_frame 2; abstained: no_anchor 2

### 2b. Readings that belong to a staff or system, not to one box

| reading | boxes | verdicts | read | carried | guessed (INFER) | decided (yes/no) | narrowed | abstained | other | balance |
|---|---|---|---|---|---|---|---|---|---|---|
| clefs (one per staff and system) | 1,102 | 691 | 690 | 0 | 1 | 0 | 0 | 0 | 0 | balanced |
| key signatures (one per staff and system) | 1,354 | 691 | 478 | 0 | 213 | 0 | 0 | 0 | 0 | balanced |
| meters (time signatures) (one per system) | 518 | 53 | 2 | 31 (-2) | 0 | 0 | 0 | 11 (+2) | 9 | balanced |
| instrument names (one per staff) | 0 | 691 | 684 | 0 | 0 | 0 | 0 | 7 | 0 | balanced |
| direction words (one verdict per inked cell; most say no word is there) | 0 | 6,685 | 0 | 0 | 0 | 6,682 (+6,682) | 0 | 3 | 0 (-6,682) | balanced |
| dynamic words (one verdict per inked cell (most say no dynamic); the boxes are single letters) | 3,941 | 6,685 | 0 | 0 | 0 | 6,599 (+6,599) | 23 | 63 | 0 (-6,599) | balanced |
| tuplet ratios (the 3 over a triplet) | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detector boxes | decided | abstained | written to the file | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 6,544 | 4,435 (+6) | 2,109 (-6) | 1,790 (+315) | n/a | emitted |
| articulation | 1,263 (-2,838) | 742 | 530 | 538 (+44) | n/a | emitted |
| clef | 1,102 | 691 | 1 | 0 | n/a | emitted |
| direction | 0 | 6,682 | 3 | 365 | n/a | emitted |
| dot | 9,674 | 9,063 | 611 | 1,996 | n/a | emitted |
| dynamic | 3,941 | 6,599 | 86 | 1,081 | 86 | emitted |
| fermata | 12 | 11 | 1 | 6 (+1) | n/a | emitted |
| key | 1,354 | 691 | 213 | 0 | n/a | emitted |
| note | 24,260 | 39,680 | 0 | 10,918 (+1,770) | 2502 | emitted |
| ornament | 24 | 10 | 14 | 7 (+2) | n/a | emitted |
| rest | 8,129 | 0 | 0 | 5,471 (+797) | 675 | abstained |
| slur | 3,148 | 2,589 | 0 | 532 (+148) | n/a | emitted |
| tie | 11,666 | 12,205 | 0 | 476 (+119) | n/a | emitted |
| time | 518 | 42 (-2) | 11 (+2) | 0 | n/a | emitted |
| tuplet | 4 | 0 | 4 | 0 | n/a | abstained |
| wedge | 2 | 274 | 4 | 69 (+12) | n/a | emitted |


(`rest` reads 'abstained' only because the exporter has no separate rest verdict; rests are read, see 2a. `decided` counts verdicts, which can exceed boxes where one box has several.)

- export: events in the log -> file: in 32,839 = written 16,367, not written (reasons below) 16,472 (sum 32,839) -> balanced
(Of the written events, 0 notes were doubled onto a condensed slot and 22 rests duplicated across voices; the exporter nets those out.)

Notes and rests not written, by reason (top 12):

- bar_does_not_add_up: 4,098 (-2,094)
- not_a_notehead:too_narrow: 3,315
- owned_by_another_staff: 3,059
- duration_narrowed: 2,324 (-697)
- not_a_rest:rest_is_a_duplicate_box: 863
- not_a_notehead:clipped_fragment: 593
- not_a_rest:rest_clipped_by_crop: 544
- unread_gap_in_partial_bar: 282
- chord_value_undecided: 213 (+1)
- not_a_notehead:stacked_head_duplicate: 171 (-40)
- not_a_rest:rest_outside_its_staff: 138
- not_a_notehead:notehead_is_a_duplicate_box: 115

Two stages, one fact: the record's refusals (ADJUDICATE) against the exporter's drop reasons of the same name: 25 of 25 reasons agree exactly.

Every standing glyph verdict of the quantities above is in a row, on a refused box, or on a box of a kind no row covers: 9 of 9 quantities account for all their verdicts.
- pitch: 11,592 of 35,852 verdicts sit on boxes of another kind (e.g. a pitch computed for a rest box) -- listed, not hidden

## 3. How sure are the guesses

Blue items written: **3,263 (+2,229)** (notes 2,502 (+1,563), rests 675 (+666), dynamics 86). By the rule that guessed:

- fill_part_key: 605 (+44) (a pitch read through a key signature that was inferred for the part)
- collapse_arc_ink_not_beam: 604 
- reconcile_duration: 323 (-36) (length chosen only because the bar then adds up)
- dynamic_with_an_unread_letter: 86 (a dynamic word with a letter that could not be read)
- collapse_bare_stem_by_bar: 29 (+2) (a stem with no flag/beam seen, length chosen by the bar)
- fill_clef_gap: 3 (a pitch read through a clef that was inferred)
- collapse_narrowed_by_bar: 1 (length narrowed to a few candidates, one chosen by the bar)

Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the readable notes either side of an unread gap):

- onset_from_partial_bar_prefix: 812
- onset_from_partial_bar_suffix: 800

Of the guesses INFER made (record): 1034 standing. Candidates it chose between: {'3': 1, '0': 213, '2': 820}. Evidence gap between the chosen candidate and the runner-up: {'tie': 1, 'one candidate': 213, 'gap 1': 820} ('tie' = the chosen value had no more support than another).
Durations that are guesses at glyph level: 2249; of those, settled by the bar's arithmetic alone (the weakest witness): 345.

**Refusals and how close they came** (2.106): 76416 refusals/narrowings in the record, 712 carry a margin, **75704 carry none** (rules not yet covered, or structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, since most rules declare no band). Biggest groups:

| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |
|---|---|---|---|---|---|---|---|---|
| unboxed_ink_is_a_rest | claimed_by_another_class | abstained | 239 | 239 | 80 | 79 | 80 | -0.003 at p21 sys1 staff4 cell4 glyph350000 |
| duration | head_fill_from_ink | narrowed | 236 | 232 | 79 | 57 | 100 | 0 at p3 sys0 staff2 cell2 glyph22 |
| unboxed_ink_is_a_rest | shape_cannot_tell | abstained | 224 | 224 | 75 | 73 | 76 | -0.001 at p9 sys1 staff0 cell8 glyph350001 |
| narrow_box_is_an_eighth_rest | shape_cannot_tell | abstained | 12 | 12 | 4 | 3 | 5 | -0.016 at p9 sys0 staff8 cell8 glyph18 |
| clef | margin_below_floor | narrowed | 1 | 0 | 1 | 0 | 0 | 0 at p8 sys1 staff3 |

## 4. Unknown and unread, in one place

- unread marks red: 2,315 (-191)
- staves held out unidentified: 0
- unidentified parts: 0
- noteheads owner not read: 40
- notes whose length stayed undecided (narrowed, abstained, chord): {'narrowed': 2324, 'rest abstained': 48, 'chord undecided': 213}
- evidence the deciders asked for and did not find (record `adjudication.missing_evidence`, top 8): human_box_verdict 106,043, glyph_owner 81,430, rest 31,993, tuplet_ratio 27,936, letter_look_cover 26,960, notehead_staff_position 26,426, head_stem_reach 25,457, far_head_owner_ledger 23,297

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 5,577 over 27 pages (about 207 per page). Previous: 3502.

Five worst pages: p13: 160 red + 166 blue; p19: 109 red + 215 blue; p5: 102 red + 207 blue; p23: 112 red + 166 blue; p16: 110 red + 150 blue.

Five worst staves (instrument, page): Violin [P11] p19: 9 red + 39 blue; Viola p19: 10 red + 33 blue; Clarinet p16: 8 red + 33 blue; Cello p5: 11 red + 30 blue; Bassoon p13: 15 red + 24 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Bassoon | 835 (-32) | 352 (+259) | 207 (-18) | 473 (-245) | 29 |
| Clarinet | 597 (-35) | 329 (+263) | 215 (-19) | 356 (-270) | 34 |
| Cello | 683 (-53) | 303 (+179) | 225 (-4) | 458 (-158) | 20 |
| Oboe | 534 (-46) | 310 (+226) | 207 (-13) | 392 (-185) | 36 |
| Violin [P10] | 657 (-61) | 292 (+218) | 225 (-8) | 352 (-200) | 36 |
| Violin [P11] | 980 (-42) | 299 (+150) | 189 (-11) | 377 (-129) | 17 |
| Viola | 1,044 (-18) | 271 (+161) | 179 (-13) | 362 (-141) | 30 |
| Flute | 429 (-39) | 242 (+184) | 188 (-23) | 278 (-188) | 16 |
| Contrabass | 386 (-36) | 234 (+146) | 181 (-23) | 298 (-152) | 17 |
| Horn [P6] | 635 (-19) | 156 (+121) | 143 (-13) | 243 (-118) | 14 |
| Horn [P7] | 284 (-37) | 152 (+132) | 133 (-12) | 165 (-122) | 10 |
| Contrabassoon | 227 (-18) | 149 (+114) | 103 (-13) | 93 (-95) | 11 |
| Timpani | 206 | 34 (+32) | 83 (+1) | 172 (-63) | 9 |
| Trumpet | 244 (-23) | 54 (+44) | 56 (-3) | 79 (-28) | 3 |

## 6. Detected, then dropped

Detector boxes whose class no family reads (never reach a decision): {'arpeggiato': 860, 'caesura': 36, 'ottavaBracket': 10, 'segno': 1} (of 98,663 boxes).
Detected and unrepresented in the record: none. Decided but not written to the file: none.
Ink rows no class explains (Q.INK): 6685.

## 7. The top reasons, with one place to look

(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)

- 7,862 x ties: refused, ink_is_a_staff_line -- e.g. p0 sys0 staff0 cell0 glyph25
- 3,407 x noteheads: how long: refused, too_narrow -- e.g. p0 sys0 staff0 cell4 glyph16
- 3,063 x noteheads: how long: abstained: owned_by_another_staff -- e.g. p0 sys0 staff0 cell6 glyph20
- 2,173 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p0 sys0 staff0 cell2 glyph4
- 1,790 x accidentals: abstained: no_candidate -- e.g. p0 sys0 staff1 cell1 glyph18
- 975 x bar held out: does not add up -- e.g. p1 sys0 staff0 cell0 (bar 8, part P1)
- 863 x rests: refused, rest_is_a_duplicate_box -- e.g. p0 sys0 staff7 cell0 glyph21
- 593 x noteheads: how long: refused, clipped_fragment -- e.g. p0 sys0 staff1 cell0 glyph18
- 544 x rests: refused, rest_clipped_by_crop -- e.g. p1 sys0 staff0 cell1 glyph21
- 515 x bar stays held: voice_overfull -- e.g. p1 sys0 staff0 cell0 (bar 8, part P1)

## 8. Regression guards

- judged: right 70, wrong 10, narrowed 18, abstained 1, not_found 7, unscored 133 (Sean's past answers on the tiles that fall on this record)  (previous: right 66, wrong 10, narrowed 22, abstained 1, not_found 7, unscored 133 (Sean's past answers on the tiles that fall on this record))
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

76 of 77 rows balance. **Imbalances:**

- refusal vs exporter drop: not_a_notehead:too_narrow: in 3,407 = exporter dropped 3,315 (sum 3,315) -> **IMBALANCE +92**

