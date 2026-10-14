# Re-gather report: Brahms 1 mvt 1 (Breitkopf scan), 20261013-night

Every number below is read off the saved record, the exporter's own report or the MusicXML (sources named in `tools/omr/staged/regather_report.py`). A figure in brackets such as `(+12)` is the change since the previous night (Brahms 1 mvt 1 (Breitkopf scan), 20261011-night). **IMBALANCE** marks a row whose parts do not add up to its total: a finding, not a typo.

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
- **pages**: 0-26
- **wall time**: 201 min (gather through INFER; exit 0) (previous: 182 min (gather through INFER; exit 0))

### Definition of done (one command, a whole movement, nothing invented)

| question | this night | previous |
|---|---|---|
| staves named | 684 (not named: 7) | 635 (not named: 56) |
| staves held out (counted, not placed in a part) | 0 | 1 |
| meter, per system: read / carried / guessed / narrowed / abstained | 2 / 33 / 0 / 0 / 9 | 2 / 30 / 0 / 0 / 13 |
| key, per staff and system: read / carried / guessed / narrowed / abstained | 478 / 0 / 213 / 0 / 0 | 478 / 0 / 212 / 0 / 1 |
| clef, per staff and system: read / carried / guessed / narrowed / abstained | 690 / 0 / 1 / 0 / 0 | 690 / 0 / 1 / 0 / 0 |
| bars marked unread (red) | 2,506 (-752) | |
| MusicXML written | yes 6.6 MB | yes |
| LilyPond written / compiled / warnings | yes / yes / 445 | yes / yes / 93 |

### Biggest movers since the previous night

| row | was | now | change |
|---|---|---|---|
| rests / added without a box | 0 | 450 | +450 |
| bars / held out does not add up | 2,553 | 1,057 | -1,496 |
| bars / held out | 2,552 | 1,057 | -1,495 |
| export not written / bar_does_not_add_up | 7,650 | 4,020 | -3,630 |
| export rest / written | 3,576 | 5,448 | +1,872 |
| export slur / written | 367 | 483 | +116 |
| bars / unread marks in file | 3,258 | 2,506 | -752 |
| export accidental / written | 1,319 | 1,695 | +376 |
| export tie / written | 311 | 392 | +81 |
| export note / written | 8,198 | 10,311 | +2,113 |

## 1. Bars

A bar is one measure of one part. Each bar of the file is in exactly one state.

| state | bars | plain words |
|---|---|---|
| written plain | 3,833 (-575) | all notes written, none guessed |
| written with guesses | 625 | written; at least one note/dynamic is a guess (blue) |
| partial | 765 | kept in part: readable notes written, the unreadable gap marked red (2.117) |
| held out | 1,057 (-1,495) | notes held back because the bar does not add up; red mark (not written) |
| unread, empty | 680 | nothing read in this bar; padded and marked red |
| **total bars (parts x measures)** | 6,960 | |

- bars: in 6,960 = written plain 3,833, written with guesses 625, partial 765, held out 1,057, unread, empty 680 (sum 6,960) -> balanced
- check, partial bars: file vs exporter: file 765, exporter 765 -> agrees
- check, held-out bars: file vs exporter: file 1057, exporter 1057 -> agrees
- check, unread-empty bars: file vs exporter: file 680, exporter 684 -> **IMBALANCE**

Bars with notes read off the page: 5,987 (+32). Tacet bars padded with rests (written, not unread): 317 (-11). Meter: 979 bars judged on a carried meter, 0 with notes and no meter.

Bars that could have been partial but stay held, by reason: voice_overfull 490, nothing_before_or_after_the_gap 370, short_without_an_unread_symbol 197.

Red marks written: 2506. Equation: empty 684 + held out 1057 + partial 765 = 2506 -> balanced.

## 2. Symbols: what happens to each kind at each stage

GATHER finds boxes. ADJUDICATE asks 'is it really one of these?' (refused) and then 'what does it mean?' (decided / narrowed to a few candidates / abstained). EVALUATE and INFER may settle the ones ADJUDICATE could not (INFER settlements are GUESSES, written blue). EXPORT writes or drops.

### 2a. Per symbol kind, at glyph level (computed here from the record)

| kind | boxes (+added) | refused | decided | narrowed | abstained | no verdict | of the decided: guessed | balance |
|---|---|---|---|---|---|---|---|---|
| noteheads: how long | 24,260 | 4,635 | 13,535 (+161) | 3,027 (-161) | 3,063 | 0 | 1,844 (+157) | balanced |
| noteheads: which pitch | 24,260 | 4,635 | 19,625 | 0 | 0 | 0 | 1,844 (+157) | balanced |
| rests | 8,129 +450 | 1,808 (+97) | 6,723 (+353) | 0 | 48 | 0 | 0 | balanced |
| accidentals | 6,544 | 0 | 4,429 (+2) | 0 | 2,115 (-2) | 0 | 0 | balanced |
| slurs | 3,148 | 84 (+2) | 3,044 (-2) | 0 | 20 | 0 | 0 | balanced |
| ties | 11,666 | 7,866 (+2) | 3,800 (-2) | 0 | 0 | 0 | 0 | balanced |
| articulations | 4,101 | 23 | 728 | 8 | 504 | 2,838 | 0 | balanced |
| fermatas | 12 | 0 | 11 | 0 | 1 | 0 | 0 | balanced |
| ornaments | 24 | 0 | 10 | 0 | 14 | 0 | 0 | balanced |
| hairpins | 2 +276 | 0 | 274 | 0 | 4 | 0 | 0 | balanced |

Top reasons per kind (refused, narrowed, abstained):

- **noteheads: how long** (each detected notehead box: is it a real notehead, and what length is it): refused too_narrow 3407; refused clipped_fragment 593; refused stacked_head_duplicate 211; abstained: owned_by_another_staff 3063; narrowed: beam_discounted_uncertain 2915; narrowed: beams_ambiguous 38; narrowed: beam_certain_not_joined 31
- **noteheads: which pitch** (the same boxes: which line or space, and so which note name): refused too_narrow 3407; refused clipped_fragment 593; refused stacked_head_duplicate 211
- **rests** (each detected rest box: is it a real rest, and what length): refused rest_is_a_duplicate_box 863; refused rest_clipped_by_crop 544; refused rest_outside_its_staff 138; abstained: rest_stands_where_no_rest_hangs 31; abstained: unreadable_rest 17
- **accidentals** (sharps/flats/naturals: which notehead they belong to): abstained: no_candidate 1796; abstained: is_a_key_signature_marker 283; abstained: ambiguous_height 32; abstained: head_belongs_to_a_nearer_staff 4
- **slurs** (curved lines read as slurs): refused ink_is_a_staff_line 82; refused in_a_key_signature_slot 2; abstained: same_pitch_accidental_unread 17; abstained: stack_slur_over_two_same_pitch_notes 3
- **ties** (curved lines read as ties): refused ink_is_a_staff_line 7862; refused in_a_key_signature_slot 4
- **articulations** (staccato dots, accents, tenuto: which note): refused ledger_between_staff_and_note 23; abstained: no_notehead 424; abstained: owned_by_another_staff 32; abstained: stem_direction_unread 28; abstained: stem_contradicts_class_side 11
- **fermatas** (fermatas: which note): abstained: no_carrier 1
- **ornaments** (trills, turns, tremolo): abstained: no_notehead 14
- **hairpins** (crescendo/diminuendo wedges): abstained: no_page_frame 2; abstained: no_anchor 2

### 2b. Readings that belong to a staff or system, not to one box

| reading | verdicts | read | carried | guessed (INFER) | narrowed | abstained | other | balance |
|---|---|---|---|---|---|---|---|---|
| clefs (one per staff and system) | 691 | 690 | 0 | 1 | 0 | 0 | 0 | balanced |
| key signatures (one per staff and system) | 691 | 478 | 0 | 213 (+1) | 0 | 0 (-1) | 0 | balanced |
| meters (time signatures) (one per system) | 53 | 2 | 33 (+3) | 0 | 0 | 9 (-4) | 9 (+1) | balanced |
| instrument names (one per staff) | 691 | 684 (+49) | 0 | 0 | 0 | 7 (-49) | 0 | balanced |
| direction words (words like cresc., dolce, one per word) | 6685 | 0 | 0 | 0 | 0 | 3 (+3) | 6,682 (-3) | balanced |
| dynamic words (p, f, sf ... letters spelled into a word; the boxes are the letters) | 6685 | 0 | 0 | 0 | 23 (-4) | 63 (+1) | 6,599 (+3) | balanced |
| tuplet ratios (the 3 over a triplet) | 4 | 0 | 0 | 0 | 0 | 4 | 0 | balanced |

### 2c. EXPORT: what reached the file (the exporter's own report)

| family | detected | decided | abstained | written | of which guessed (blue) | exporter status |
|---|---|---|---|---|---|---|
| accidental | 13,088 | 4,429 (+2) | 2,115 (-2) | 1,695 (+376) | n/a | emitted |
| articulation | 4,101 | 742 | 530 | 523 (+100) | n/a | emitted |
| clef | 1,102 | 691 | 1 | 0 | n/a | emitted |
| direction | 368 (+28) | 6,682 (-3) | 3 (+3) | 365 (+26) | n/a | emitted |
| dynamic | 3,943 (+4) | 6,599 (+3) | 86 (-3) | 1,081 (+76) | 86 | emitted |
| fermata | 12 | 11 | 1 | 6 (+4) | n/a | emitted |
| key | 1,354 | 691 (+1) | 213 | 0 | n/a | emitted |
| note | 24,260 | 39,680 (-17) | 0 | 10,311 (+2,113) | 2077 | emitted |
| ornament | 24 | 10 | 14 | 6 (+2) | n/a | emitted |
| rest | 8,129 | 0 | 0 | 5,448 (+1,872) | 780 | abstained |
| slur | 3,148 | 2,589 | 0 | 483 (+116) | n/a | emitted |
| tie | 11,666 | 12,205 | 0 | 392 (+81) | n/a | emitted |
| time | 518 | 44 (+4) | 9 (-4) | 0 | n/a | emitted |
| tuplet | 4 | 0 | 4 | 0 | n/a | abstained |
| wedge | 278 | 274 | 4 | 67 (+20) | n/a | emitted |

- export: events in the log -> file: in 32,410 = written 15,738, not written (reasons below) 17,101 (sum 32,839) -> **IMBALANCE -429**

Notes and rests not written, by reason (top 12):

- bar_does_not_add_up: 4,020 (-3,630)
- not_a_notehead:too_narrow: 3,315 (+1)
- owned_by_another_staff: 3,059 (-1)
- duration_narrowed: 3,021 (-161)
- not_a_rest:rest_is_a_duplicate_box: 863 (-5)
- not_a_notehead:clipped_fragment: 593
- not_a_rest:rest_clipped_by_crop: 544 (-4)
- unread_gap_in_partial_bar: 252
- chord_value_undecided: 212 (-12)
- not_a_notehead:stacked_head_duplicate: 211 (-3)
- not_a_rest:rest_outside_its_staff: 138 (-1)
- not_a_notehead:notehead_is_a_duplicate_box: 115 (-2)

Does the record's refusal count match the exporter's drop count? (two stages, one fact)

- not_a_notehead:belongs_to_a_nearer_staff: record 53, exporter 53 -> agrees
- not_a_notehead:clipped_fragment: record 593, exporter 593 -> agrees
- not_a_notehead:head_cut_piece: record 13, exporter 13 -> agrees
- not_a_notehead:is_a_beam_piece: record 4, exporter 4 -> agrees
- not_a_notehead:is_a_clef: record 32, exporter 32 -> agrees
- not_a_notehead:is_a_dot: record 4, exporter 4 -> agrees
- not_a_notehead:is_a_meter_digit: record 30, exporter 30 -> agrees
- not_a_notehead:is_a_time_signature_digit: record 4, exporter 4 -> agrees
- not_a_notehead:notehead_in_a_key_signature_slot: record 2, exporter 2 -> agrees
- not_a_notehead:notehead_is_a_duplicate_box: record 115, exporter 115 -> agrees
- not_a_notehead:on_a_barline: record 6, exporter 6 -> agrees
- not_a_notehead:on_a_dynamic_letter: record 49, exporter 49 -> agrees
- not_a_notehead:stacked_head_duplicate: record 211, exporter 211 -> agrees
- not_a_notehead:too_narrow: record 3407, exporter 3315 -> **IMBALANCE -92**
- not_a_notehead:tremolo_slash_crosses_stem: record 112, exporter 112 -> agrees
- not_a_rest:rest_clipped_by_crop: record 544, exporter 544 -> agrees
- not_a_rest:rest_has_a_stem: record 45, exporter 45 -> agrees
- not_a_rest:rest_in_a_key_signature_slot: record 24, exporter 24 -> agrees
- not_a_rest:rest_is_a_barline: record 53, exporter 53 -> agrees
- not_a_rest:rest_is_a_duplicate_box: record 863, exporter 863 -> agrees
- not_a_rest:rest_is_a_meter_digit: record 30, exporter 30 -> agrees
- not_a_rest:rest_off_center: record 46, exporter 46 -> agrees
- not_a_rest:rest_outside_its_staff: record 138, exporter 138 -> agrees
- not_a_rest:rest_overlaps_a_notehead: record 19, exporter 19 -> agrees
- not_a_rest:rest_touches_two_staff_lines: record 46, exporter 46 -> agrees

Glyph verdicts counted by the funnels against all standing glyph verdicts of that quantity (the gap is verdicts on refused boxes or subjects no row lists):


## 3. How sure are the guesses

Blue items written: **2,943** (notes 2,077, rests 780, dynamics 86). By the rule that guessed:

- fill_part_key: 607 (a pitch read through a key signature that was inferred for the part)
- reconcile_duration: 379 (length chosen only because the bar then adds up)
- dynamic_with_an_unread_letter: 86 (a dynamic word with a letter that could not be read)
- collapse_bare_stem_by_bar: 29 (a stem with no flag/beam seen, length chosen by the bar)
- fill_clef_gap: 3 (a pitch read through a clef that was inferred)
- collapse_narrowed_by_bar: 1 (length narrowed to a few candidates, one chosen by the bar)

Blue notes kept in partial bars (2.117), apart from the guesses above (their onset follows from the readable notes either side of an unread gap):

- onset_from_partial_bar_prefix: 867
- onset_from_partial_bar_suffix: 971

Of the guesses INFER made (record): 244 standing. Candidates it chose between: {'3': 1, '0': 213, '2': 30}. Evidence gap between the chosen candidate and the runner-up: {'tie': 1, 'one candidate': 213, 'gap 1': 30} ('tie' = the chosen value had no more support than another).
Durations that are guesses at glyph level: 1511; of those, settled by the bar's arithmetic alone (the weakest witness): 392.

**Refusals and how close they came** (2.106): 76364 refusals/narrowings in the record, 667 carry a margin, **75697 carry none** (rules not yet covered, or structural refusals). Near / middle / far are the lowest, middle and top third of that rule's own distance from its cut (a relative band, since most rules declare no band). Biggest groups:

| rule | reason | outcome | n | short of the cut | near | middle | far | closest call |
|---|---|---|---|---|---|---|---|---|
| unboxed_ink_is_a_rest | claimed_by_another_class | abstained | 239 | 239 | 78 | 82 | 79 | -0.003 at p21 sys1 staff4 cell4 glyph350000 |
| unboxed_ink_is_a_rest | shape_cannot_tell | abstained | 224 | 224 | 73 | 77 | 74 | -0.001 at p9 sys1 staff0 cell8 glyph350001 |
| duration | head_fill_from_ink | narrowed | 191 | 187 | 59 | 69 | 63 | 0 at p3 sys0 staff2 cell2 glyph22 |
| narrow_box_is_an_eighth_rest | shape_cannot_tell | abstained | 12 | 12 | 4 | 5 | 3 | -0.016 at p9 sys0 staff8 cell8 glyph18 |
| clef | margin_below_floor | narrowed | 1 | 0 | 1 | 0 | 0 | 0 at p8 sys1 staff3 |

## 4. Unknown and unread, in one place

- unread marks red: 2,506 (-752)
- staves held out unidentified: 0 (-1)
- unidentified parts: 0
- noteheads owner not read: 40
- notes whose length is undecided: [3021, 48, 212]
- adjudication missing evidence: {'accidental_staff_position': 1526, 'arc_box': 4712, 'aug_dot': 9991, 'beam_stem_join': 2950, 'beam_stroke_ink': 5350, 'cell_box': 920, 'cell_staff_space': 2, 'clef_position': 19, 'clef_seed': 691, 'dot_stroke_ink': 2838, 'dynamic_band_position': 193, 'event': 145, 'far_head_owner_ledger': 23297, 'flag': 13289, 'glyph_band_distance': 14162, 'glyph_box': 2536, 'glyph_ladder': 22675, 'glyph_owner': 81426, 'head_line_cut': 20097, 'head_stem_reach': 25457, 'human_box_verdict': 106043, 'keysig_clef_fit': 844, 'keysig_marker_is_not_a_marker': 312, 'keysig_template_fit': 368, 'ledger_owner_density': 22675, 'letter_look_cover': 26920, 'meter_ocr': 27, 'meter_ocr_at_bar': 44, 'notehead_class': 4493, 'notehead_letter_ink': 19664, 'notehead_position': 3307, 'notehead_staff_position': 25273, 'notehead_stem_cross_ink': 14268, 'rest': 31993, 'stacked_head_fit': 12524, 'staff_lines': 2, 'staff_spacing': 2, 'stem_slash': 2606, 'tuplet_ratio': 27936}

## 5. Where the fixing time goes

Cleanup proxy = red (unread) + blue (guessed) items in the MusicXML: 5,421 over 27 pages (about 201 per page). Previous: 0.

Five worst pages: p5: 112 red + 206 blue; p19: 109 red + 185 blue; p13: 149 red + 142 blue; p23: 124 red + 152 blue; p6: 109 red + 142 blue.

Five worst staves (instrument, page): Violin p19: 15 red + 54 blue; Violin p3: 20 red + 36 blue; Violin p5: 21 red + 33 blue; Violin p13: 19 red + 34 blue; Horn p8: 24 red + 24 blue.

Per instrument (part):

| instrument | notes plain | notes guessed | unread marks | events held out | rows in unread gaps |
|---|---|---|---|---|---|
| Violin | 1,641 (-206) | 519 (+519) | 433 (+433) | 721 (-500) | 41 |
| Horn | 870 (+33) | 263 (+263) | 301 (+301) | 420 (-481) | 20 |
| Clarinet | 533 (-30) | 318 (+318) | 236 (+236) | 335 (-423) | 38 |
| Bassoon | 790 (-47) | 304 (+304) | 227 (+227) | 487 (-395) | 19 |
| Cello | 683 (-143) | 282 (+282) | 232 (+232) | 446 (-212) | 18 |
| Oboe | 501 (-77) | 283 (+283) | 221 (+221) | 342 (-366) | 34 |
| Viola | 1,035 (-78) | 232 (+232) | 196 (+196) | 352 (-222) | 30 |
| Contrabass | 350 (-122) | 224 (+224) | 203 (+203) | 293 (-266) | 17 |
| Flute | 384 (-61) | 212 (+212) | 209 (+209) | 290 (-303) | 20 |
| Contrabassoon | 224 (-42) | 121 (+121) | 116 (+116) | 94 (-157) | 6 |
| Timpani | 200 (+31) | 40 (+40) | 82 (+82) | 169 (-173) | 9 |
| Trumpet | 241 (+7) | 46 (+46) | 59 (+59) | 71 (-132) | 0 |

## 6. Detected, then dropped

Detector boxes whose class no family reads (never reach a decision): {'arpeggiato': 860, 'caesura': 36, 'ottavaBracket': 10, 'segno': 1} (of 98,663 boxes).
Detected and unrepresented in the record: none. Decided but not written to the file: none.
Ink rows no class explains (Q.INK): 6685.

## 7. The top reasons, with one place to look

(Addresses: page / system / staff within the system / bar within the system / glyph. A crop can be cut from any of these on request.)

- 7,862 x ties: refused, ink_is_a_staff_line -- e.g. p0 sys0 staff0 cell0 glyph25
- 3,407 x noteheads: how long: refused, too_narrow -- e.g. p0 sys0 staff0 cell4 glyph16
- 3,407 x noteheads: which pitch: refused, too_narrow -- e.g. p0 sys0 staff0 cell4 glyph16
- 3,063 x noteheads: how long: abstained: owned_by_another_staff -- e.g. p0 sys0 staff0 cell6 glyph20
- 2,915 x noteheads: how long: narrowed: beam_discounted_uncertain -- e.g. p0 sys0 staff0 cell2 glyph4
- 1,796 x accidentals: abstained: no_candidate -- e.g. p0 sys0 staff1 cell1 glyph18
- 1,057 x bar held out: does not add up -- e.g. p1 sys0 staff0 cell0 (bar 8, part P1)
- 863 x rests: refused, rest_is_a_duplicate_box -- e.g. p0 sys0 staff7 cell0 glyph21
- 593 x noteheads: how long: refused, clipped_fragment -- e.g. p0 sys0 staff1 cell0 glyph18
- 593 x noteheads: which pitch: refused, clipped_fragment -- e.g. p0 sys0 staff1 cell0 glyph18

## 8. Regression guards

- judged: doc_unresolved 235, other_doc 207, unscored 133, not_found 7, right 66, wrong 10, narrowed 22, abstained 1  (previous: doc_unresolved 235, other_doc 207, unscored 133, not_found 10, right 63, wrong 10, narrowed 22, abstained 1)
- check open: 192 open findings (tree-level, same for both movements)

## 9. Balance ledger (every row that must add up)

18 of 19 rows balance. **Imbalances:**

- export: events in the log -> file: in 32,410 = written 15,738, not written (reasons below) 17,101 (sum 32,839) -> **IMBALANCE -429**

