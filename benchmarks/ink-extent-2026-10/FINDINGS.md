# ROADMAP 2.248 -- every mark's size from its own ink (STAGED)

**STATUS (2026-11-01): r3 BUILT, NOT LANDED; r2 DOES NOT LAND.** Branch `lane-2.248-ink-extent` ee87ef423 (r3 flag `OMR_FARHEAD_UNREAD_GUESSED`, default OFF; r2 flag `OMR_HEAD_INK_EXTENT`, default OFF). The lane's full r3 entry is in this file ON THE LANE BRANCH; the summary and Sean's answers are here.

## 2026-11-01: round 3 -- a far head whose ledger count abstains is written blue, and Sean's tiles

**Cause (r3).** EVALUATE `consequences.restate_pitch` read the geometry row (the box centre) when ADJUDICATE `adjudicate_notehead_position` abstained on a far head's ledger count, and wrote a DECIDED, unmarked pitch -- "cannot tell" turned into an answer (rule 8, CLAUDE §4). A second copy sat in `move_glyph` (branch `reowned`). Process lesson: when a decision abstains, read what its consumers do with the abstention.

**Built (r3).** The head keeps its pitch but is written GUESSED (blue `#1F6FEB`) with two candidates (box-centre step, ink-centre step); the ink centre never places a far head (page-facts: ledger lines only). On the 2-page subset: Litolff +235 blue, Brahms +1, nothing else changed, judged right->wrong 0. Frozen sample not run.

**How often a far head's ledger count abstains** (20261029-night slices): Litolff 1,097 of 2,114, Brahms 1,280 of 2,636. Mostly refutations, not reading failures: 616 (L) / 963 (B) have a ledger reading toward ANOTHER staff (the head belongs to the neighbour), 253 / 400 are not notes (twins, barlines, text). The real reading failure is `count_does_not_fit` (L 365, B 489) -- where a ledger-reader lane should look.

**Sean's tiles** (`out/print/2.248-r3-tiles/` on the lane branch; answers verbatim and scored in `answers-r3.json`):
- r2 in-staff moves (1, 2, 4, 5, 10, 12): only 4 and 12 are noteheads. **1 and 5 are tremolo slashes, 2 part of an F clef, 10 an eighth rest.** Their ink centre differed from their box centre because they are not round heads. On the two real heads the ink centre was right (4: second space from the top; 12: second space from the bottom). r2 does not land: a non-head must be refused upstream, never re-pitched.
- r3 far heads written blue (3, 6, 7, 8, 9, 11): all six are real notes (3 and 6 boxed on only half the head).
  - 7 and 9: the written (box) candidate is right.
  - **3 and 6: the wrong staff.** 3 was keyed far above staff 8; Sean reads it on the ledger line BELOW staff 7. 6 was keyed far below staff 6; Sean reads the second ledger line ABOVE staff 7. Both candidates wrong on each. Page-facts already say the ledger lines name the owner; that rule did not take over here.
  - 8 and 11: Sean reads "the 4th space above the staff" (top head of a stacked chord). Counted up from the top line that is neither candidate; the tile is cropped above the staff so the ledger lines cannot be counted on it. UNRESOLVED until a taller crop shows the staff.

**Next (not started).** (a) Why do far heads that the ledger lines give to the neighbour stay on the wrong staff (tiles 3, 6)? (b) Refuse tremolo slashes, clef pieces and rests as heads before any move (tiles 1, 2, 5, 10). (c) A taller crop for tiles 8, 11. r3 alone could land as "mark, not move", but 2 of its 6 blue notes sit on the wrong staff, so it waits for (a).

**STATUS (2026-10-31 night): PARKED, NOT LANDED.** Branch `lane-2.248-ink-extent` at 868ee790b (r1 code fdd54c6c4, r2 code f04eb8630), flag `OMR_HEAD_INK_EXTENT` default OFF (allow-list). Sean: out of tonight's overnight, picked up next session. Resume steps at the end of this file.

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

## Sean's answers on the r1 tiles (2026-10-31; out/print/2.248-tiles/answers.json)
- Values: 1 eighth, 2 dotted quarter, 3-9 eighths, 11-12 eighths; tile 10 unanswered.
- "Every box was a good size for the notehead" -- the grown extent fits the head.
- Line or space on the seven moved notes: 1 line, 2 space, 6 space, 7 line, 9 space, 11 line, 12 line -> the INK centre was right on 1, 6, 9, 11, 12 (5/7), the BOX centre on 2, 7 (2/7).

## The rule r1 broke (Sean's question "how did we miss this rule?")
All seven moved notes are OUTSIDE the staff (positions -2..-7 above, 13..16 below). page-facts (§3, ~lines 236-256) and DECISIONS 2026-10-27: a head outside the staff is placed ONLY by counting its own printed ledger lines -- never by a centre measured against a grid extended past the outer line (hand-drawn ledgers: Litolff rungs sit ~0.27 sp further out). r1 moved far heads by an ink centre on that extended grid. Missed three times: the manager's brief framed the lane as SIZE and never named the rule that owns PITCH; the lane did not check whether moved heads were inside or outside the staff; the manager sent Sean line/space tiles without grepping page-facts first. Lesson -> CLAUDE.md §6 "Name the rule that owns the value" (Sean, 2026-10-31).

## Why tiles 2 and 7 failed (the two the ink got wrong)
- Tile 2 (Brahms p5 glyph/5/0/1/5/20, head in the space above a short ledger): the grown extent took a 54 px ledger stub (rows 981-987, 2-7 px past both sides of the head) as head ink, pulling the centre onto the line. With the stub stripped the ink centre still reads ~15.6-15.8 (a line) -- the extended grid itself is off there, which is exactly why far heads are ledger-only.
- Tile 7 (Litolff p6 glyph/6/1/0/5/4): box -2.50, ink -2.51 -- both centres on the half-way boundary; ink rows 1969-1973 run past the head's left side, possibly a ledger through it (Sean: line). Neither centre can decide a boundary.

## The ledger count on those seven (the finding that matters most)
The far-head ledger count ABSTAINS on all seven: Brahms tiles 1, 2, 9 `ledger_not_read` (tile 2 `count_does_not_fit`, gaps 3.37 sp); Litolff tiles 6, 7, 11, 12 `no_page_shape` (a 2-page gather never fills the head-shape pool of 8; a whole-movement gather does, from about page 16 on Litolff). Where it abstains, the WRITTEN pitch falls back PLAIN to the box centre on the extended grid (or `move_glyph` for re-owned heads) -- right on 2 of 7 here. That breaks CLAUDE §5 ("no rungs either way is OUR failure -- abstain and count it") and §4 (nothing uncertain written unmarked).

## Round 2 (f04eb8630; built, NOT measured on the frozen sample)
- The ink centre moves a head only when BOTH the box and the ink position are in -1..9 (inside the staff or its first space outside); far heads are never moved.
- No move when the ink centre is within 0.15 step of the half-way point.
- Ledger stub out of the grown extent: a row in the outer 30% of the extent whose ink run through the head's centre column reaches past both sides of the head's widest middle rows and is >= 0.15 sp wider is a line row and is stripped (>= 0.6 sp of head must stay); the columns are cut back to the head's. A ledger through the middle is never stripped.
- Tests: test_head_extent_2_248.py 14 pass (+ positions, 2.73, ink-rules: 99). Full fast tier NOT re-run after r2 (last full run before r2: 9,646).
- 2-page gathers, r2 ON (Litolff p6,10 / Brahms p0,5): all exit 0. Litolff 9 positions moved (r1 97, 75 of them far), all inside the staff, all 0.3-1 step; written pitch differs from OFF in 6 of 1,071. Brahms 4 moved, all inside; 1 written pitch differs.
- The three measures for r2 do NOT exist: the frozen-sample lane_report was stopped part-way (Brahms ON arm) so the machine is idle for the overnight; Litolff's ON arm had been gathered with r1 code.

## Open items
1. Far heads whose ledger count abstains are written plain from the box centre -> write them GUESSED (blue) with box- and ink-centre positions as candidates (a separate fix, outside head_extent; the bigger win).
2. Twins read as heads: cell-edge pieces of a neighbouring staff's head written as notes (Litolff 38 of 96, Brahms 16 of 49 on 2 pages) -- the page-mark identity does not join a piece to its whole twin (mark_group size 1). Breaks "all ink accounted for once".
3. Flags and rests not examined (rests already read their ink, 2.150b rest_ink).
4. Other tile tools (benchmarks/*/tiles.py) still draw the detector box -- the source of today's false "box too small" tiles.

## Resume steps (next session)
1. `git merge origin/main` into lane-2.248-ink-extent (never rebase).
2. Build open item 1 (behind its own flag or inside 2.248's, by Sean's say), with tests.
3. Full fast tier (no -n) + one real 2-page gather per plate ON (exit 0).
4. Three measures: `OMR_SURYA_KEEP_ALIVE=0 python3 -m tools.omr.staged.lane_report --flag OMR_HEAD_INK_EXTENT --from gather --cell-map master --workers 2 --unjudged-tiles 12 --tag <private> --out out/2.248/lane` (both plates, both arms with the final code; no other lane running -- Surya timeouts under load move clefs/keys).
5. 12 tiles on the in-staff moves (line or space?) for Sean; land on his answers (judged right->wrong 0).
