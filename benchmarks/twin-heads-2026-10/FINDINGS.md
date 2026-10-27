# 2.212 -- one printed head, one measurement (STAGED GATHER; flag `OMR_TWIN_HEAD_MERGE`, default OFF)

Lane `lane-2.212-twin-heads`. Sean 2026-10-27 "Yes". Fence: GATHER head-position / fill reading
(`gather_notehead_positions`, `gather_notehead_ink`) + the new pure `twin_head.py`; ADJUDICATE untouched.

## 1. The cause, and what it teaches about our process

**Cause (STAGED, GATHER).** A notehead's staff position is `(box.y_center - top_y) / half_step`
(`gather.gather_notehead_positions`) -- a number read off the *detector's box*, not off the head's ink. The detector often
draws one printed head twice (`noteheadBlack*` + `noteheadHalf*`, or a head and a taller head-plus-stem box), the two boxes have
different centres, so they carry two different positions for one head. ADJUDICATE then *chooses* which box survives
(`notehead_precision._stacked_head_duplicate_refusal`, 2.42, from each box's own ink; `_notehead_is_a_duplicate_box`, 2.30, by
score) and the survivor's position is the written pitch. So a choice between boxes was deciding a pitch: anything that changes
the ink under one box (the eraser, 2.206d) flips the keeper and the pitch, with no reading of the head involved.

**Lesson.** A decision that picks among duplicates of one measurement is a measurement problem upstream. Where two readings of
one thing can disagree, the fix is to take ONE reading of the thing (here: the head's own ink) before anyone chooses; choosing
well between two wrong boxes is not the same as reading the head. (2.206d's "keeper flipped, pitch changed" was never an
eraser bug; the eraser only exposed that the pitch was a function of the keeper.)

## 2. How often (saved 2.206d records, frozen sample pages, no gather; `count_twins.py`)

Twin pair = a box ADJUDICATE refused as `stacked_head_duplicate` (2.42) or `notehead_is_a_duplicate_box` (2.30), with the box it
kept. "Pitch differs" = the two boxes' rounded staff positions differ (one half-step = a different written pitch).

| plate (8 pages) | notehead boxes | twin groups (pairs / triples+) | refused boxes (2.42 / 2.30) |
|---|---|---|---|
| Litolff | 5,795 | 326 (297 / 29) | 365 (247 / 118) |
| Brahms | 7,013 | 76 (73 / 3) | 83 (53 / 30) |

By the boxes' vertical centre distance `dy` (staff spaces), 2.42 pairs:

| plate | `dy` < 0.5 sp: pairs / pitch differs / class differs | 0.5-1.0 sp | >= 1.0 sp |
|---|---|---|---|
| Litolff | 159 / 58 (36 %) / 91 (57 %) | 39, every one a different pitch | 49, every one a different pitch |
| Brahms | 36 / 9 (25 %) / 10 (28 %) | 9 | 8 |

2.30 (same-mark, same class by construction): Litolff 118 pairs, pitch differs 16 (14 %); Brahms 30, 3.

Class pairs of the 247 / 53 2.42 pairs (refused -> kept): Litolff black->black 84, black->hollow 60, hollow->black 45,
hollow->hollow 58; Brahms 16 / 3 / 8 / 26. About 4 in 10 Litolff twins are a black box and a hollow box on one head.

Keeper flips under the eraser (2.206d OFF vs ON, same member set): Litolff 9 of 320 groups flipped, 6 changed the written pitch;
Brahms 4 of 75, 2 changed pitch.

**Looked at, not only counted (rule 7).** 12 crops with both boxes drawn (my look only, not tiles): the `dy` < 0.5 pairs are
one head boxed twice in every crop; the `dy` >= 1.0 pairs are two real heads (a third apart, a ledger line between them;
2.42's fit calls them one slot) or a head and a head+stem box. That is why the merge stops at 0.5 sp: the 88 Litolff / 17 Brahms
pairs beyond it are **not** merged here (they stay with the keeper rule; a different lane's question: some are lost chord heads).

## 3. The two heads Sean read (staff-eraser FINDINGS 13), through three estimators

Litolff p8 (glyph/8/1/6/3/1|3) Sean "A natural" = position 5; p16 (glyph/16/1/3/1/2|3) Sean "Eb" = position 0. Boxes: 4.80 /
4.04 and 0.54 / -0.22. Position of the head by: box mean 4.42 (wrong), 0.16 (right); ink centroid with stem and line rows left
out (`recentre_part_boxed`'s estimator) 4.10 (wrong, a black cap on the ring pulls it), 0.56 (wrong); the stacked fit's slot
4 and -1 (wrong, wrong); **the centre of the head's own hole(s)** 5.02 and 0.08 (right, right). On Sean's hand-labelled Brahms
page 0 (data/hand-truth, boxes confirmed by Sean; 5 twin groups matched): hole 3 of 4 hollow groups round to his position;
centroid 4 of 5 groups. Small numbers: the estimator is a measurement narrowed by two plates, so the flag stays OFF until his
tiles.

## 4. What the flag does

`OMR_TWIN_HEAD_MERGE=1`: in GATHER, notehead boxes whose centres are < 0.5 sp apart vertically and < 0.5 head widths sideways are
one head (a group is dropped whole if its centres span 0.6 sp or more). `twin_head.group_centre` places the head ONCE on the
page raster: the area-weighted centre of the enclosed holes in the group's union box (a hollow head; a line through it splits
the hole, both halves count), else the stem- and line-free ink centroid (a filled head); a group the ink cannot place is
declined (`twin_head_declined` on the row) and every box keeps its own position (cannot tell, rule 8). Every member then files
the SAME `Q.NOTEHEAD_STAFF_POSITION` (its own reading rides on the row as `detector_position_float`, the group on `twin_head`),
and `gather_notehead_ink` reads the fill of ONE standard head box at that centre for all of them -- the twins agree on the head's
fill, so ADJUDICATE's keeper choice can still pick a box but not change the written pitch, and the 2.73 class-by-ink step sees
one reading. Nothing in ADJUDICATE changed. Not merged: head-plus-stem boxes (their centre is half a stem off the head).

Measured on the 2-page fail-fast subset (Litolff 8, 16, Sean's two crops; Brahms 0, 12): 210 of 1,562 Litolff notehead
positions sit in merged groups (155 by hole, 55 by ink), 34 declined (20 no ink, 14 unstable); both of Sean's heads come out
right whichever box is kept.

## 5. Measured (lane_report, flag OFF vs ON, `--from gather`)

Fail-fast subset (Litolff 8,16; Brahms 0,12): notes written unchanged (0 lost, 0 gained), judged right->wrong 0. A first frozen run
(before the fix below) lost 5 Litolff notes: 2 black-only groups placed by a "hole" that was not a head's (moved a space, fill read
off the head) -> fixed (`hollow_possible`: black-only groups use the ink only; test added), 2 chord notes (glyph/6/1/0/10/7, 8)
below, 1 identical-verdict artefact.

**Frozen sample, final run** (`out/lane-report/2.212`):
- Litolff: notes +5 -2, **pitches ~42 changed**, ties +8 -10, blue +9 -8, accidentals +2 -1, fermatas +2 -1, flags +1, words -3;
  red bars 0 -> 0; notes not written 2566 -> 2563. Brahms: pitches ~1, dots +1, accidentals +1 -1, words +1 -1; red bars 166 -> 166.
- Judged answers (Sean's, 233 + 232 tiles on these pages): **right->wrong 0**, right->narrowed 0.
- Lost notes by reason (`lane_report lost-notes`): 2, both `decided:stem_value_follows -> narrowed:beam_discounted_uncertain`
  (Litolff p6, glyph/6/1/0/10/7, 8). Cause: the stem's top head is a Whole-class + Black-class twin; the shared fill now reads hollow
  for both, so 2.73's class-by-ink keeps the Whole box (decided `whole_class_on_a_stem`, half note, the same value) where OFF kept
  the Black box (`head_and_marks`); `stem_value_follows` shares a value only from the latter, so the two chord mates lose their
  shared half. Same music on the head, two notes narrowed: **2.210's code (stem_value / HEAD_STEM), not touched here.** 5 notes
  gained (not listed by reason).
- Print check of the 42 pitch changes by me is NOT a result (crops without a readable clef are ambiguous at ledger stacks, e.g. a
  black head on the first ledger line vs the space under it); the judge is Sean's tiles.

**Tiles** (`out/print/2.212/tiles/sheet.png`, key `out/print/2.212/key.json` outside the folder): 12 = 10 changed pitches (9 Litolff,
the 1 Brahms) + 2 unchanged notes; one orange box each, nothing drawn, the window at least +-9 sp tall / +-8 wide. Question: the
pitch of the head at the box. Not yet answered; flag stays OFF until they are.

## 6. Open / not done
- Head-plus-stem boxes and pairs >= 0.5 sp apart (88 Litolff / 17 Brahms 2.42 pairs) still choose pitch by keeper.
- Class of an indecisive-fill twin group is still the keeper's class (ADJUDICATE untouched).
- Estimator evidence is 2 Sean heads + 5 hand-labelled Brahms groups; widen with the tile answers.

## 7. Sean's tiles (2026-10-27)

He gave where the boxed head sits on the staff; pitch derived from the recorded clef of that staff (20261022-night slices;
tiles 8, 9, 12 from `clef_located`: alto, tenor, alto), accidentals ignored. Per tile (`out/print/2.212/answers.json`):
1 OFF right / ON wrong; 3, 4, 6, 7, 8, 9, 12 OFF wrong / ON right; 10 both wrong (Sean: a tremolo slash, not a note; box sits in
the second space from the bottom); 11 OFF right / ON wrong. Tiles 2 and 5 are unchanged controls (no pitch in the key; positions
recorded only). Of 10 pitch tiles: OFF right 2, ON right 7. **Right->wrong: 2** (tiles 1 and 11, Litolff p16 staves 0 and 2, G5->A5
and A5->G5: ON moves the head one step the wrong way at the staff top, the staff top / first ledger zone). Cause of those two is
not yet found; look there before landing. Clef doubt: tile 12's staff (Litolff p11 staff 7) holds only a `clef_glyph` clefG at
y=38 (a neighbour's), while `clef_located` says alto; with treble both arms would be wrong, with alto ON is right. Tile 8's staff
has no clef reading on its own page (alto carried from page 1 staff 9). Tile 10 is a mark to be withheld, not a pitch.
