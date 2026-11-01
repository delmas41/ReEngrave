# ROADMAP 2.248 -- every mark's size from its own ink (STAGED)

2026-10-31, branch `lane-2.248-ink-extent` 654d54ffc (Opus), flag `OMR_HEAD_INK_EXTENT` default OFF. Written by the manager from the lane's report (the hook refused the lane's write). Scripts in this directory are on the branch.

## Cause and process lesson
- Sean's "box too small" heads were NOT a reading problem -- they were the box the TILE TOOL draws. All 9 head places he flagged (2.240-s4 tiles 1, 6, 7, 9; rules tiles 3, 4, 6, 7, 11) are cell-edge twins: the detector reads one staff's cell at a time, a head from the next staff pokes over the cell edge, and that cut-off piece (4-9 px tall) is boxed as a head. The same head is boxed whole in its own staff's cell, 9 of 9 (`trace_tiles.py`). The reading already refuses those pieces as notes (`clipped_fragment` / `notehead_is_a_duplicate_box`, `fate.py`); the 2.240 tile tool picked them because their owner verdict moved and drew the piece's detector box. 2.241 tile 9's box was a claim-readout box over a ledger line, not a head box.
- What the reading DOES take from the detector box is the head's staff position (its pitch): `gather_notehead_positions` uses the box centre; the 2.39 re-centre feeds only the ledger window; 2.73's line cut is the one exception. The fill (2.220 head_ink) and the claim already read the head's own ink.
- Lesson: a tile drawn from a detector box shows the detector, not the reading -- trace the place to the record (is this the head's only box, is it read?) before opening a lane on "the box is small" (the same lesson as 2.247's `cls`).

## How often
- Head boxes >= 0.25 sp short of the ink (2.220 trim): Litolff 8 frozen pages 1,356 of 5,807 (337 cell-edge twins); Brahms p0+p5 545 of 1,729 (63); p25 298 of 825 (41). Overstates "only box" cases: on Brahms the trim runs into touching chord-mates (lane's look: the box was right on 5 of 5 stacked chords).
- Ink centre rounds to a different position than the box centre (one-head ink touching no other head box): Litolff 540 of 5,166 (10%); Brahms p0+p5 108 of 1,483; p25 52 of 665.
- Twins read AS heads (not refused) on 2-page gathers: Litolff 38 of 96, Brahms 16 of 49.

## Built (`head_extent.py`, wired in `gather.gather_notehead_positions`, reach.py)
- `ink_extent`: grows the head from the box seed by re-feeding 2.220's `head_ink.trim_head` (not retuned) until it stops growing (<= 4 passes); used only where the ink is one head, <= 1.35 sp tall (two-plate cut-off, narrows only), contains the box's centre row, and overlaps no other head box in the cell by > 0.15 sp.
- `ink_position`: the position moves to the ink centre only where it rounds differently from the box centre; the row keeps `detector_position_float` and `from_head_ink`; never overrides 2.73's line-cut position. Claims, fill and 2.245's functions unchanged.
- Tests: test_head_extent_2_248.py (10). Fast tier 9,646 (+3 rule-page tests after regenerating ink-rules).

## Numbers
- 2-page gathers per plate (L p6,10 / B p0,5), flag OFF and ON, --through infer: all four exit 0.
- Positions moved ON: Litolff 97 of 1,642 (58 up one, 35 down one, 4 by two); Brahms 58 of 1,736. Size: L >= 1 step 16, 0.3-1 step 56, < 0.3 step 25; B 6 / 37 / 15. The < 0.3-step moves are flips at the rounding boundary (-2.50 -> -2.51; tiles 7, 9).
- Three measures (frozen sample, lane_report --from gather --cell-map master): RUNNING at the time of writing -- no judged right->wrong, red bar or unwritten number yet. Do not land before they are clean.

## Not done / next
- Twins read as heads (L 38, B 16 on 2 pages): the page-mark identity does not join a piece to its whole twin -- breaks "all ink accounted for once"; its own item.
- Flags and rests not tested (time box); rests already read their ink (2.150b rest_ink).
- Other tile tools (benchmarks/*/tiles.py) still draw the detector box.
- A minimum shift, if the boundary flips are judged wrong.

## Tiles
out/print/2.248-tiles (boxes drawn from the NEW extent): 3, 4, 5, 8, 10 are Sean's places grown from the same short box; 1, 2, 6, 7, 9, 11, 12 are written heads whose position moved.
