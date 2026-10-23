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
