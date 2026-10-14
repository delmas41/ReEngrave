# Re-gather report: Beethoven 5 mvt 1 (Litolff scan), 20261013-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Beethoven 5 mvt 1 (Litolff scan), 20261011-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

## 0. One screen

### Run

- **tree**: ca46eae4 (previous: cb73dde2)
- **landings since the previous night**:
  - ca46eae4 ROADMAP 2.114: claim the second (hollow-only) detector at GATHER; Sean's interior-white rule
  - 14cd2946 ROADMAP 2.113: claim the clutter count (measure before a remove-what's-known view)
  - a31a2cca ROADMAP 2.112: claim the test-set leakage audit (2.110 found TEST cells in training)
  - 2892eb71 hand_truth inventory: declare v24 (2.4b hollow4 TRAIN, single-family:hollow, not admitted) -- fixes test_every_label_version_on_disk_has_a_declared_tier
  - 4863f784 Docs: ROADMAP START HERE landing order, version_memory for 2.108
  - 36f4a4cf Land 2.108 a music glyph more than 6 staff spaces from any staff is not music; kept out of the labelling pre-fill (lane-2.108-off-staff-glyphs 6d9f9207) (Sean: "yes")
  - 6d9f9207 Rebuild judged-tiles index after merging main
  - b0fd2e09 Merge origin/main into lane-2.108
  - d10affe3 2.108: Sean's answers on the blind tiles; FINDINGS, DECISIONS, ROADMAP
  - abec2a05 ROADMAP 2.111: park the plate's-own notehead template idea (Sean: keep the idea)
  - 753e5dd7 2.108: off-staff reach 6 spaces (Sean: go with 6); re-measure, blind tiles, DECISIONS line
  - bb0be121 ROADMAP 2.110: claim the training-scale check (Sean: start with the training size check)
  - ad26d0d1 ROADMAP START HERE: Sean wants to revisit 2.4b hollow heads next session; ideas to weigh (two detectors, complete cells, combined round, resolution)
  - 04592685 2.108: FINDINGS, ROADMAP row, version_memory
  - 6f6c71c9 2.108: staged reach reads the vertical band only (record STAFF_EXTENT is the detector span; it refused 14 real Brahms p1 heads); prune-off-staff; probes + tiles
  - 59dd07d4 Land 2.107 dynamic letters read from the ink against the terms library; an unsure dynamic is written blue "dyn." (lane-2.107-dynamic-letters e450e31a) (Sean: "land with blue dyn only")
  - e450e31a Docs: ROADMAP 2.107 landed, START HERE landing order, version_memory
  - db798ecc Rebuild judged-tiles index after merging main
  - 8ef0ee1e Land 2.4b records: hollow-head labels (Litolff p1 TEST + 100-cell TRAIN, v24) and the killed retraining A/B; production weights unchanged (lane-2.4b-hollow 5e0e7f56)
  - 5e0e7f56 Merge origin/main into lane-2.4b-hollow; ROADMAP 2.4b KILLED, 2.5 unblocked
  - 9fea5569 2.4b: BN-frozen fine-tune (v24 + control) -- same class deletion, worse; 2.4b closed as killed. FINDINGS, ROADMAP, version_memory.
  - 595c6373 1.7 hand truth: Sean finished Brahms 317803 pdf 0 (1,352 -> 1,566 boxes; remaining cells are words only)
  - 659c84a4 Merge origin/main into lane-2.107-dynamic-letters
  - 437b32e9 2.107: ink pick OFF by default (OMR_DYNAMIC_INK_PICK); narrowed dynamic exports only blue dyn. (Sean: "land with blue dyn only"); ROADMAP 2.109 opened
  - 5ac5b06a 2.108: off_staff_glyph (STAGED notehead decider) + hand-truth pre-fill never queues a pitch glyph with no staff near; RED-first tests
  - 39af6bd9 2.107: Sean's answers; tile 8 fixed; a narrowed dynamic is written blue as the ink's closest guess
  - 96df14ed ROADMAP 2.108 opened: music glyphs far from any staff (title text) are not music (Sean)
  - ec782bab 2.4b re-assembly: reverse graft (arms A/B/C, v24 + control) KILLED -- class rows restore nothing; damage is in BN stats/conv weights. FINDINGS, ROADMAP, version_memory.
  - 47a113a8 ROADMAP START HERE after 2026-10-13: landed, Sean's rules, in flight (2.107, 2.4b re-assembly), next; version_memory
  - 057565e7 Docs: ROADMAP 2.105 landed (sf moved to 2.107), START HERE landing order, version_memory
  - 20112bd5 Land 2.105 a barline is not a rest; twin boxes keep one plausible head and never a beam (lane-2.105-not-a-note b2d55319) (Sean: "land 2.105")
  - b2d55319 2.105: rest_is_a_barline and the widened is_a_beam_piece file their 2.106 margins; rebuild judged index
  - 486d4983 Merge remote-tracking branch 'origin/main' into lane-2.107-dynamic-letters
  - 6fa0b0d3 DECISIONS: a narrowed dynamic is written as its best candidate by the ink, in blue; 'dyn.' only where the ink favours none (Sean)
  - cb5f42a7 DECISIONS: a narrowed dynamic is written as 'dyn.' in blue with its candidates, never picked by frequency (Sean)
  - aa27c1df 2.4b re-assembly: reverse-graft builder (fine-tune + production class rows), per-class counter, A/B runner
  - 2a465417 Merge origin/main into lane-2.105-not-a-note
  - 92d415e1 2.107: FINDINGS, ROADMAP row, version_memory, 11 blind tiles, reach probes
  - d93b371e 2.107: read the dynamic letters the detector never boxed (second look, library-checked)
  - 416d2f71 2.4b: hollow-head run result -- graft KILLED (0 points at shift 0, -12 at 0.9); raw fine-tune 91.5% but deletes beams/ledgers. FINDINGS, ROADMAP row, version_memory.
  - ... and 149 more
- **flags/settings that differ from defaults**:
  - OMR_SURYA_KEEP_ALIVE=0
- **weights**: --weights auto (weight routing off)
- **pages**: 1-16
- **wall time**: 55 min (gather through INFER; exit 0) (previous: 52 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| staves named | 203 (not named: 128) | 200 (not named: 131) |
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
| bars / held out | 988 | 646 | -342 |
| export not written / bar_does_not_add_up | 2,498 | 1,673 | -825 |
| bars / held out does not add up | 1,044 | 705 | -339 |
| bars / written plain | 5,072 | 3,559 | -1,513 |
| rests / refused total | 478 | 598 | +120 |
| export rest / written | 1,876 | 2,168 | +292 |
| noteheads: how long / narrowed | 392 | 343 | -49 |
| export accidental / written | 314 | 358 | +44 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 3,559 (-1,513) | all notes written, none guessed |
| written with guesses | 949 | written; at least one note/dynamic is a guess (blue) |
| partial | 156 | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 646 (-342) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 750 | nothing read in this bar; padded and marked red |
| **total bars (parts x measures)** | 6,060 | |

- bars: in 6,060 = unread, empty 750, written plain 3,559, held out 646, partial 156, written with guesses 949 (sum 6,060) -> balanced
- check, partial bars: file vs exporter: file 156, exporter 156 -> agrees
- check, held-out bars: file vs exporter: file 646, exporter 705 -> **IMBALANCE**
- check, unread-empty bars: file vs exporter: file 750, exporter 691 -> **IMBALANCE**

Bars with notes read off the page: 5,022 (+181). Tacet bars padded with rests (written, not unread): 347 (-192). Meter: 0 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 191, short_without_an_unread_symbol 412, nothing_before_or_after_the_gap 43.

Red marks written: 1552. Equation: empty 691 + held out 705 + partial 156 = 1552 -> balanced.

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

| reading | verdicts | read | carried | guessed (INFER) | narrowed | abstained | other | balance |
|---|---|---|---|---|---|---|---|---|
| clefs (one per staff and system) | 331 | 317 | 0 | 11 | 3 | 0 | 0 | balanced |
| key signatures (one per staff and system) | 331 | 136 (-1) | 0 | 195 (+5) | 0 | 0 (-4) | 0 | balanced |
| meters (time signatures) (one per system) | 31 | 1 | 30 | 0 | 0 | 0 | 0 | balanced |
| instrument names (one per staff) | 331 | 203 (+3) | 0 | 0 | 0 | 128 (-3) | 0 | balanced |
| direction words (words like cresc., dolce, one per word) | 5377 | 0 | 0 | 0 | 0 | 1 (+1) | 5,376 (-1) | balanced |
| dynamic words (p, f, sf ... letters spelled into a word; the boxes are the letters) | 5377 | 0 | 0 | 0 | 17 (+2) | 18 | 5,342 (-2) | balanced |
| tuplet ratios (the 3 over a triplet) | 12 | 0 | 0 | 0 | 0 | 9 | 3 | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detected | decided | abstained | written | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 3,016 | 648 | 860 | 358 (+44) | n/a | emitted |
| articulation | 465 | 13 | 5 | 3 | n/a | emitted |
| clef | 513 | 328 | 14 | 0 | n/a | emitted |
| direction | 75 (+5) | 5,376 (-1) | 1 (+1) | 74 (+6) | n/a | emitted |
| dynamic | 1,605 (+32) | 5,342 (-2) | 35 (+2) | 558 (+47) | 35 | emitted |
| fermata | 178 | 156 | 22 | 77 (+3) | n/a | emitted |
| key | 542 | 331 (+4) | 195 (+1) | 0 | n/a | emitted |
| note | 11,399 | 15,091 (-9) | 0 | 6,573 (+791) | 1701 | emitted |
| ornament | 3 | 2 | 1 | 1 (+1) | n/a | emitted |
| rest | 2,873 | 0 | 0 | 2,168 (+292) | 54 | abstained |
| slur | 1,225 | 1,055 (-2) | 0 | 184 (+18) | n/a | emitted |
| tie | 1,419 | 1,582 (+2) | 0 | 219 (+4) | n/a | emitted |
| time | 82 | 31 | 0 | 0 | n/a | emitted |
| tuplet | 13 | 3 | 9 | 0 | n/a | emitted |
| wedge | 5 | 5 | 0 | 0 | n/a | decided_but_unwritten |

- export: events in the log -> file: in 14,689 = written 8,324, not written (reasons below) 6,073 (sum 14,397) -> **IMBALANCE +292**

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

Does the record's refusal count match the exporter's drop count? (two stages, one fact)

- not_a_notehead:belongs_to_a_nearer_staff: record 41, exporter 41 -> agrees
- not_a_notehead:clipped_fragment: record 342, exporter 342 -> agrees
- not_a_notehead:head_cut_piece: record 17, exporter 17 -> agrees
- not_a_notehead:is_a_beam_piece: record 19, exporter 19 -> agrees
- not_a_notehead:is_a_clef: record 30, exporter 30 -> agrees
- not_a_notehead:notehead_in_a_key_signature_slot: record 12, exporter 12 -> agrees
- not_a_notehead:notehead_is_a_duplicate_box: record 257, exporter 257 -> agrees
- not_a_notehead:on_a_dynamic_letter: record 64, exporter 64 -> agrees
- not_a_notehead:stacked_head_duplicate: record 448, exporter 448 -> agrees
- not_a_notehead:too_narrow: record 258, exporter 258 -> agrees
- not_a_notehead:tremolo_slash_crosses_stem: record 61, exporter 61 -> agrees
- not_a_rest:rest_clipped_by_crop: record 75, exporter 75 -> agrees
- not_a_rest:rest_has_a_stem: record 120, exporter 120 -> agrees
- not_a_rest:rest_in_a_key_signature_slot: record 23, exporter 23 -> agrees
- not_a_rest:rest_is_a_barline: record 90, exporter 90 -> agrees
- not_a_rest:rest_is_a_duplicate_box: record 104, exporter 104 -> agrees
- not_a_rest:rest_is_a_meter_digit: record 8, exporter 8 -> agrees
- not_a_rest:rest_is_a_slashed_stem: record 1, exporter 1 -> agrees
- not_a_rest:rest_off_center: record 58, exporter 58 -> agrees
- not_a_rest:rest_on_a_dynamic_letter: record 2, exporter 2 -> agrees
- not_a_rest:rest_outside_its_staff: record 7, exporter 7 -> agrees
- not_a_rest:rest_overlaps_a_notehead: record 12, exporter 12 -> agrees
- not_a_rest:rest_touches_two_staff_lines: record 98, exporter 98 -> agrees

Glyph verdicts counted by the funnels against all standing glyph verdicts of that quantity (the gap is verdicts on refused boxes or subjects no row lists):


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
- notes whose length is undecided: [311, 98, 98]
- adjudication missing evidence: {'accidental_staff_position': 433, 'arc_box': 6959, 'aug_dot': 11525, 'beam_stem_join': 411, 'beam_stroke_ink': 3968, 'cell_box': 189, 'cell_staff_space': 35, 'clef_position': 40, 'clef_seed': 331, 'dot_stroke_ink': 447, 'dynamic_band_position': 33, 'event': 243, 'far_head_owner_ledger': 5098, 'flag': 8885, 'glyph_band_distance': 6884, 'glyph_box': 915, 'glyph_ladder': 4838, 'glyph_owner': 24643, 'head_line_cut': 10667, 'head_stem_reach': 6254, 'human_box_verdict': 39846, 'keysig_clef_fit': 375, 'keysig_marker_is_not_a_marker': 123, 'keysig_template_fit': 143, 'ledger_owner_density': 4838, 'letter_look_cover': 12627, 'meter_ocr': 4, 'meter_ocr_at_bar': 31, 'notehead_class': 3974, 'notehead_letter_ink': 9835, 'notehead_position': 976, 'notehead_staff_position': 5224, 'notehead_stem_cross_ink': 5671, 'rest': 14444, 'stacked_head_fit': 6606, 'stem_slash': 2447, 'tuplet_ratio': 12595}

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 3,337 over 16 pages (about 209 per page). Previous: 0.

Five worst pages: p15: 122 red + 193 blue; p4: 106 red + 184 blue; p14: 125 red + 155 blue; p6: 102 red + 141 blue; p2: 90 red + 147 blue.

Five worst staves (instrument, page): Violin p4: 13 red + 70 blue; Violin p14: 13 red + 64 blue; Violin p2: 14 red + 53 blue; Violin p15: 17 red + 44 blue; Violin p5: 28 red + 32 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Violin | 1,231 (-343) | 455 (+455) | 232 (+232) | 359 (-144) | 10 |
| Viola | 370 (-223) | 285 (+285) | 158 (+158) | 178 (-73) | 6 |
| Bassoon | 423 (-193) | 300 (+300) | 136 (+136) | 173 (-110) | 2 |
| Cello | 330 (-37) | 147 (+147) | 172 (+172) | 147 (-43) | 4 |
| Flute | 362 (-104) | 152 (+152) | 131 (+131) | 148 (-81) | 5 |
| Oboe | 356 (-65) | 145 (+145) | 125 (+125) | 185 (-87) | 1 |
| Contrabass | 323 (-13) | 98 (+98) | 129 (+129) | 26 (-15) | 0 |
| Clarinet | 578 (-20) | 72 (+72) | 147 (+147) | 199 (-56) | 3 |
| Horn | 336 (+7) | 50 (+50) | 111 (+111) | 124 (-78) | 3 |
| Trumpet | 351 (+19) | 30 (+30) | 104 (+104) | 66 (-66) | 1 |
| Timpani | 158 (+8) | 21 (+21) | 109 (+109) | 68 (-72) | 0 |

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
- 448 x noteheads: which pitch: refused, stacked_head_duplicate -- e.g. p1 sys0 staff3 cell7 glyph2
- 412 x bar stays held: short_without_an_unread_symbol -- e.g. p2 sys0 staff0 cell5 (bar 22, part P1)
- 342 x noteheads: how long: refused, clipped_fragment -- e.g. p1 sys0 staff3 cell3 glyph2
- 342 x noteheads: which pitch: refused, clipped_fragment -- e.g. p1 sys0 staff3 cell3 glyph2
- 262 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p1 sys0 staff7 cell1 glyph1

## 8. Regression guards

- judged: doc_unresolved 234, not_found 13, unscored 97, other_doc 213, narrowed 4, right 107, wrong 12, abstained 1  (previous: doc_unresolved 234, not_found 19, unscored 97, other_doc 213, wrong 12, right 99, narrowed 6, abstained 1)
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

18 of 19 rows balance. **Imbalances:**

- export: events in the log -> file: in 14,689 = written 8,324, not written (reasons below) 6,073 (sum 14,397) -> **IMBALANCE +292**
- exporter's own `dot_role_balance` says balanced = False: {'population': 601, 'attached_augmentation': 15, 'written_staccato': 364, 'attached_staccato_before_hold_out': 410, 'not_placed': 241}

