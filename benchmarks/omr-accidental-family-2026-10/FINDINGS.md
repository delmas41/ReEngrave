# 2.201 -- one accidental family: the type from its own strokes, the role from position (OFF flag `OMR_ACCIDENTAL_FAMILY`, needs `OMR_STROKE_MAP`)

Path: STAGED GATHER (the extent, the type, the role evidence) + ADJUDICATE (`adjudicate_accidental_owner`) + EXPORT (the blue flag). LEGACY untouched.
Branch `lane-2.201-accidental-family` (built from `origin/lane-2.198-glyph-strokes`, main merged at 78a0144fe). Scripts in this directory; nothing here is a gather
record (those are not committed).

## 1. Cause (rule 3), measured: the box is NOT usually cut; the CLASS is wrong and the ink says the type plainly
Sean's reading of the 2.203 tiles (DECISIONS 2026-10-23) was that the detector box stops short of a natural's lower stroke, so what is inside reads as a flat.
I measured it on the 58 answered tiles that map to a box (`truth_tiles.py`: 2.186b, 2.190, 2.193, 2.199b, 2.203; 45 naturals, 9 flats, 3 sharps, 1 "none";
tile boxes are the NOTE for the first four sets and the ACCIDENTAL for 2.203; the 2.203 tile boxes equal the detector's boxes to 2 px, checked), by running the
production detector (+2.186 merge, 2.193 candidates) on each tile's own cell and the stroke map on the same cell (`det_cut.py`, `eval_family.py`; no gather).
Biased sample: every tile was drawn from a lane's CHANGED or WRONG symbols, not at random.

| | n | detector's class is the printed type | box cuts the mark's own stroke by >= 0.5 sp | by >= 0.25 sp | the strokes' type (below) right / unclear / wrong |
|---|---|---|---|---|---|
| natural | 45 | 13 (29%) | 2 | 6 | 43 / 2 / 0 |
| flat | 9 | 9 | 0 | 0 | 8 / 1 / 0 |
| sharp | 3 | 3 | 0 | 0 | 3 / 0 / 0 |
| none | 1 | 0 | 0 | 0 | 0 / 1 / 0 |
| all | 58 | 25 (43%) | 2 (3%) | 6 (10%) | 54 (93%) / 4 / **0** |
(by plate: Brahms 48 tiles, strokes right 46, detector right 21; Litolff 10 tiles, strokes right 8, detector right 4.) The box holds BOTH of a natural's stems
(each 0.9-1.0 inside the box) in 52 of 58 tiles; the cuts are all naturals, none longer than 1.4 spaces. I crop-checked 20 of them myself (my look, rule 7;
`crops_family.py`, sheet kept in the scratchpad, not committed): every natural box holds the whole natural, the orange (detector) and blue (grown) boxes differ by
a few pixels except on the cut ones; the unclear four are a merged Litolff stroke, a flat in clutter, and two I would not call.

The ink separates the three types by ONE measured thing, the **stem stagger** (`accidental_family.read_type`): a natural is two stems of which the RIGHT one stands
LOWER (its top 0.69-1.69 spaces below the left one's, bottom 0.0-1.0; 43 of 45); a sharp is two stems side by side (the right one level or a little higher:
-0.19 .. +0.06); a flat is ONE stem in the left of the mark with its bowl at the lower right. This is 2.190's stem-strength idea (a stem in a corner window) applied to
the FULL strokes instead of two corner windows of a box.

**Held-out check (not used to set any cut-off): Sean's 142 hand boxes on Brahms pp.0-3** (2.197 truth, `data/truth_brahms.json`, type = his label; box = his hand box;
`eval_hand_boxes.py`): in-bar naturals 53/53, flats 22/24, sharps 13/14, key flats 48/51; 136 of 142 right (96%), 5 abstain (unclear), **1 differs from the label and
the print says the label is wrong** (a hand box labelled `accidentalFlat`, prefill-confirmed, is plainly a natural: two stems and a square; my crop, `data/hand_boxes_result.json`).
Caveat: 63 of the 142 are `prefill-confirmed` (the detector proposed the box), so their EXTENT is the detector's; the TYPE is Sean's.

**Lesson.** A hypothesis read off a tile image ("the box cuts off the lower stroke") was written into DECISIONS as a cause before anybody measured the box against the
ink: the box is whole in 97% of these tiles and the 3% that are cut are real but are not why 29% of naturals read right. Rule 7 applies to a cause stated from a picture
as much as to a count. The useful finding is the reverse of the premise: the strokes are INSIDE the box and a one-number test over them (the stagger) reads the type; the
extent growth is a small, correct addition for the cut ones, not the main fix.

## 2. What was built (STAGED; flag `OMR_ACCIDENTAL_FAMILY`, default OFF, needs `OMR_STROKE_MAP`)
- `staged/accidental_family.py` (pure): `members_and_extent` (the mark's strokes; the box grown along a vertical stroke it partly covers, 0.5-3.7 sp long, never one touching a
  head-owned stroke, mark <= 3.9 sp; a vertical it may not claim makes the type `unclear`, never "flat"), `read_type` (stem stagger; cut-offs natural >= 0.45 sp, sharp <= 0.2 sp, in
  between unclear; measured on the 58 tiles, held out on the 142 hand boxes; NOT CONFIRMED beyond Litolff and Breitkopf, may only narrow), `guess_of` (blue wherever the strokes
  changed the detector's type, the detector offered two, the label was `key*`, or the type is unclear; agreement with ONE detector class stays READ as on main; nothing is ever READ, `READ_MARGIN` None).
- GATHER `gather_accidental_family` (after `gather_glyph_strokes`): both series (`accidental*` and `key*`) as one family; the detector label stays on the row as `detector_class`.
  `gather_accidental_positions` uses the family type, its anchor on the grown box and files a row for `key*` boxes too (**subsumes** "key-class boxes after bar 1 get no accidental row").
  `_gather_keysig_markers` takes the marker shape from the type and leaves out a mark directly left of a head at its height (**subsumes** the bar-1 in-bar accidentals pulled into the key run);
  a mark followed by a meter box, or a "head" sitting on a meter digit, never counts (found in a pre-check: Brahms p0's third key flat had a head box on the 6/8's 8).
  Pre-check on 2.202's gathered records: of 325 (Litolff) / 499 (Brahms) marker rows the test removes 2 / 39, all accidental-class at x far past the signature, 0 key-class.
- ADJUDICATE `adjudicate_accidental_owner`: a clear family type replaces 2.190's corner check; an unclear one leaves the detector's candidates and 2.190 to stand. Ownership first
  (2.186 `glyph_owner`: the copy a neighbouring crop boxed owns nothing) is REUSED unchanged -- 2.203's count found the no-twin case nearly empty (3 of 883), so it was not rebuilt.
- EXPORT `one_ink_guess_of`: rule `accidental_family`. Not subsumed: 2.199's anchor shift (the family anchor makes it moot; 2.199 itself was not touched).
- Tests `tools/omr/tests/test_accidental_family_2_201.py` (28): twins (natural/sharp/flat, agree vs differ, key-label vs accidental-label, flag off), controls that fail (level natural reads sharp, mirrored is
  not natural, a cut box without growth is not natural, a stem fused to a note stem / owned by a head is not followed, a head three spaces off is not in-bar). Staged fast subset: 4,498 passed, 0 failed.
  `check`: TOTAL 202 (2.198 left 203), `accidental_family.py` registered in `reach.STAGE_OF_FILE`.

## 3. The three measures (lane report, frozen sample, `--from gather`, both arms GATHERED with `OMR_STROKE_MAP=1`; OFF = this tree with the flag off = main + the producer-only stroke map)
- Exported file: Litolff accidentals +6 -1 ~19, ties +2, blue marks +136 -283, keys +24 -11, clefs +17 -3, pitches ~295; Brahms accidentals +23 -14 ~68, ties -6, blue marks +117 -21, keys -5, meters -8, clefs -8.
  red bars 0->0 / 166->166; notes not written unchanged. **Not clean**: the keys, clefs, meters and Litolff blue-mark movements are not accidental movements I can explain -- the OFF arm was not shown to reproduce the saved
  record (re-gather mode: "NOT CHECKED"), and `OFF == main` was argued from the code (every new path is gated on `d.accidental_family`, set only with the flag) and the 28 tests, not byte-compared (owed: a one-page
  `cmp` of main vs flag-off, and an OFF-vs-OFF control). Treat the keys/clefs/meters/blue-mark deltas as UNEXPLAINED until that control runs.
- Judged (Sean's earlier answers on these pages): right->wrong 0 / 0 (233 / 232 tiles).
- His accidental tiles (`data/before_after.json`; 49 of 59 are on counted pages; OFF already has 2.186/2.190/2.193 ON): **OFF 39 right, ON 46 right, 0 right->wrong.** Fixed: 2.186b #4, 2.190 #6, #9, 2.193 #10, 2.199b #3, #5, #10 (naturals
  written sharp / flat / none, now natural, blue). Still wrong: 2.199b #2, #7 (flats written none, both arms), #8 (no note written). The 10 tiles on pages outside the sample (all of 2.203 but #1, #12) are not counted.
  Caveat: the cut-offs were set looking at these same tiles; the held-out 142 hand boxes (96% right, 0 confident wrong) are the independent check.
- Blue: ON writes more naturals blue (they were READ flat before); several flats are now blue (2.199b #12, 2.203 #12) where the detector's label or candidates doubted -- by rule, not a regression in value.
- Fresh blind tiles: `out/print/2.201-accidental-family/` (`tiles/sheet.png`, `key.json` outside), 12 = 9 changes (drawn by plate/side in proportion: Brahms changed 5, gained 2, lost 1; Litolff changed 1) + 3 unchanged controls,
  orange box on the accidental's own detector box, the note in the crop, no two on one ink. Question: "Which accidental is printed directly in front of the note at the orange box (or in the box): sharp, flat, natural, or none?"
  (the brief's wording says "boxed note" but asks for the box on the accidental; I put the box on the accidental and reworded). Awaiting Sean.

## 4. After Sean's tiles (6/9 ON vs 1/9 OFF, controls 3/3; DECISIONS 2026-10-25): controls and the three misses
**Controls** (one page per plate, Litolff p8 and Brahms p19, full pipeline to MusicXML, same detector cache, `PYTHONHASHSEED=0`, one gather at a time, box free):
main (`0328bf1f9`, no code change since 78a0144fe) vs this branch flag OFF: **`cmp` byte-identical on both plates (MusicXML and coverage JSON)**; flag OFF twice: **byte-identical** (gather noise 0; 2.202's control said the same on Litolff).
So every difference in section 3 is this flag's, not noise.
**The key / clef / meter moves** were mine: the head test (`head_right`) took a mark out of the key run when a head stood within a space of it at its height. On Litolff it removed 4 genuine key flats
(x 517-730: the first or last flat of a mid-piece signature, no meter after it) and 59 of 126 staves' key verdicts moved (`natural_markers` 0->3, `mixed_marker_kinds` 5->6, some `markers` -> `disagrees_with_part`); the exported keys went -3 -> -1 on three staves.
On Brahms it removed 28 far-right bar-1 accidentals (right) but the same test moved key verdicts on 16 staves and a whole part (P9) lost its key/clef/meter entries. **Fixed by removing the use**: `head_right` is recorded, never drops a marker
(`_family_in_bar` False; test). Re-run of the two pages with the fix: Brahms p19 accidentals sharp 54->49, natural 97->120, flat 83->75, **keys / clefs / meters identical to OFF**; Litolff p8 accidentals natural 27->32, sharp 5->6, flat 22->20, clefs equal, one key entry -2 -> -1 (not traced). The bar-1-accidentals-in-the-key-run claim is therefore NOT subsumed; the head test cannot tell a mid-piece key flat from an in-bar one.
The blue-mark counts (Litolff +136 -283, Brahms +117 -21) were not separately explained: blue is by rule wherever the strokes changed the detector's type or the detector doubted it, and by 2.186's merge before.
**Tile 9 (Brahms sharp read flat, a regression):** the sharp's right stem is fused to the natural printed above it into one stroke longer than any accidental stem; it was a covered stroke, silently dropped from the stems, and the left stem plus a bar read as "one stem with a bowl" = flat. A covered vertical longer than 3.7 sp now counts as refused, so the type is `unclear` (rule 8). Checked on the tile's ink: now `unclear`.
**Tile 11 (a natural written with no accidental):** the natural itself was read natural, but the flat printed beside it (also owning the same head) read "sharp" with its right stem 1.2-1.4 sp HIGHER than the left (grown into the natural's stem); two glyphs of different alteration on one head write nothing (2.186). A sharp's stagger was only bounded above; now a right stem more than 0.45 sp higher is `unclear` (measured sharps: -0.19 .. +0.06). Checked: that box now `unclear`, falls back to the detector's own class as OFF does.
**Tile 2 (Litolff natural read flat; OFF read sharp):** NOT fixed. The family row shows ONE stem 1.8 sp long and a bowl piece, no second vertical found (no refused stroke either): the natural's lower stem is fused into the head's blob or cut by the box, so what is left is a stem and a square, which is a flat. No cut-off separates it (hand-box flats go down to 1.94 sp of stem) and I would not invent one.
Held-out hand boxes after both fixes: 136/142 right, 5 unclear, 1 label the print contradicts (unchanged); the 58 answered tiles: 54 right, 4 unclear, 0 wrong (unchanged). Tests 51 pass (family + key-marker files); staged subset was 4,498 pass before these two changes.

## 5. Fresh measure after the fixes (frozen sample, `out/lane-report/2.201b`; fast 2-page check `2.201-fast` first, clean)
Fast check (Litolff 10,16 / Brahms 4,12, where the moves were seen): accidentals +1 -1 ~2 / +3 ~21, no key, clef or meter move, judged right->wrong 0 / 0.
Full sample: Litolff accidentals +4 -1 ~19, pitches ~42, blue +148 -22, clefs +1, keys +2 -1; Brahms accidentals +22 -3 ~66, ties -6, pitches ~103, blue +130 -17, **no key / clef / meter move**; red bars unchanged (0->0, 166->166); notes not written unchanged.
Judged right->wrong **0 / 0** (233 / 232). The remaining Litolff key/clef move is one part (P9): a key entry -2 -> -3 at bar 18 (the movement's own key is -3) and one extra key + clef entry at bar 33; not traced further. Brahms ties -6 appears in both full runs and the fast run and is not a key/clef/meter move; it follows the pitch changes (a tie needs the same pitch) but I did not trace it.
Sean's earlier accidental tiles on counted pages: 47 counted, **OFF 37 right, ON 44 right**, none right->wrong. Fresh blind tiles: `out/print/2.201b-accidental-family/` (12: 9 changes, 3 controls; the box on the accidental).
