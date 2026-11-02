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

## Round 3 (2026-11-01): a far head whose ledger count abstained is written GUESSED
Flag `OMR_FARHEAD_UNREAD_GUESSED` (own flag, allow-list, default OFF -- it moves no head and only marks, so it can land without r2's moves). Scripts and runs: `out/2.248-r3/` (count_fallback.py, owner_split.py, fallback_run.py, reowned_far.py, make_tiles.py).

**Cause and process lesson.** The fallback is EVALUATE `consequences.restate_pitch`: `adjudicate_notehead_position` (ADJUDICATE) correctly abstains, and `restate_pitch` then reads the geometry row (box centre) and writes a DECIDED pitch with nothing marking it a guess -- a "connection" that turned "cannot tell" into an answer (rule 8, section 4). A second copy: `move_glyph`'s `reowned` branch (band-distance geometry on the new staff) when that step is far. Lesson: a decision that abstains is only half the rule; read the consumer for what it does with the abstention.
- Written with the flag: the same pitch (nothing moves), blue (`#1F6FEB`), candidates = box-centre step and ink-centre step (`restate_pitch`), or geometry and ledger-toward-owner (`move_glyph`, only where no agreeing ledger count exists). `export.far_unread_guess_of`.
- Rule check: pitch of a far head is ledger-only (page-facts, 2.216 B): untouched; the ink centre is a candidate only (r1's mistake not repeated). In-staff heads: untouched.

**How often (frozen-sample slices of the 20261029-night record, whole-movement gather, document shape pool so no `no_page_shape`).** Far heads: Litolff read 1,017 / abstained 1,097 (52%); Brahms read 1,356 / abstained 1,280 (49%). Abstained by reason: Litolff count_does_not_fit 365, no_rungs 297, not_a_note 253, no_line_at_the_note_box 160; Brahms count_does_not_fit 489, not_a_note 400, no_rungs 208, no_line_at_the_note_box 176.
**Why it abstains so often (cause, not fixed here).** The own-staff count is a refutation more than a failure: of the abstained heads, 616 / 1,097 (Litolff) and 963 / 1,280 (Brahms) have a `far_head_owner_ledger` OBSERVATION toward ANOTHER staff -- the head sits between staves and belongs to the neighbour (crop look at 6 `no_rungs` Litolff heads: 4 are between-staves heads or cell-edge pieces, no ledgers exist toward the own staff). Another 253 / 400 are `not_a_note` (twins, barline, text) the reading refuses. The residual that is truly "nobody read it": Litolff 142 no_rungs + 67 count + 71 no_line + 183 not_a_note; Brahms 31 + 13 + 26 + 244 -- small. Ledger count itself: `count_does_not_fit` (gaps outside the min/max pitch band) is the biggest real reading failure and is what a ledger-reader lane should open from this table. Written effect on 2 pages (Litolff p6,10; Brahms p0,5): Litolff 314 pitch verdicts blue, 235 written (of 1,338 events), 96 with the box candidate only (ink not one head), 123 candidates agree, 16 differ; Brahms 5 verdicts, 1 written (the rest re-owned or refused). `move_glyph` reowned adds no written blue on these pages.

**Three measures, r3 flag, 2-page development subset (not the frozen sample; machine shared, one arm of each pair run once):** Litolff: file +235 blue marks, nothing else gained or lost, red bars 0 -> 0, judged right->wrong 0, unwritten->wrong 0. Brahms: +1 blue, red bars 43 -> 43, right->wrong 0, unwritten->wrong 0. The frozen 8-page sample was NOT run (time and swap); tiles below.
**r2 (`OMR_HEAD_INK_EXTENT`) 2-page subset: NOT CLEAN, a test artifact.** Litolff ON lost 97 notes / 39 rests / 15 beams and shows clefs +2 -1, keys +5 -4: the ON arm's OCR flipped clefs and keys (Surya timeouts under load, other lanes running), not the head moves (13 heads moved: L 9, B 4; written pitch differs on ~18 L / 1 B places). The one unwritten->wrong (2.181-review tile 4, glyph/6/0/8/8/9) sits on that clef flip. Re-measure r2 with the machine quiet (or clef/key held) before reading it; Brahms is clean (dots +1, pitches ~1, red bars 43 -> 44, right->wrong 0).
**Tiles:** `out/print/2.248-r3-tiles/` (12: 6 r2 in-staff moves, 6 far blue with differing candidates; key.json outside tiles/). Question: line (or ledger line) or space?
**Not done / report only:** twins read as heads (page-mark identity gap, item 3) untouched.

## 2026-11-02: round 4 -- why two r3 blue heads looked like "the wrong staff", and the far-head position faults

**Cause and process lesson.** The ledger-names-the-owner rule DID take over. r3 tiles 3 and 6 were never written: each was a cell-edge piece of the neighbour's head (7.5 / 6.5 px tall boxes, "the bottom half / top part of an eighth"), refused by ADJUDICATE (`notehead_is_not_a_notehead` = `clipped_fragment`), owner decided to staff 7 by the page owner (`page_owner`), and the WHOLE twin written on staff 7 (glyph/10/1/7/7/5 C4, glyph/6/1/7/8/2). r3's `make_tiles.py` drew from record PITCH VERDICTS, and EVALUATE `restate_pitch` still files one (marked far-unread) on a refused box. The same fault picked r2's "non-heads": tiles 1, 5 (tremolo, `tremolo_slash_crosses_stem`), 10 (rest, `too_narrow`) and 12 (narrowed `stem_end_ink_only`) were never written either; only tile 2 (F-clef piece, narrowed `claim_narrowed:clef`) is written, as a blue C4. 6 of r3's 12 tiles measured boxes nothing was written for -- the third tile-source fault in this lane (r1: the detector box; r3: a record verdict). Lesson: a tile is cut from the exported file's hosts and nothing else; a record row is not a written mark.
- Tiles 8 and 11 (one step high): a 2-page GATHER has no head-shape pool, so the ledger count abstains `no_page_shape`; the whole-movement record reads both -7 = Sean's "4th space above". The 2-page re-gather manufactured the abstention -- r3's Litolff "+235 blue" was mostly this (the whole-movement replay below: +25). Lesson: a reader that needs a document pool cannot be measured on a page-subset gather; replay the night slices.
- Real far-head POSITION faults on the whole-movement record (ledger reader, GATHER `ledger_grid.find_note_line`, written PLAIN): carry tile 12 (glyph/11/1/9/11/0, tenor Ab4 written B4) -- "on ledger 2 (through_the_box_middle)" on a STANDARD box beside a boxed flat, though ledger 1 visibly touches the head's lower edge (Sean 2026-10-06: a visible edge ledger beats a hidden middle rung). r3 tile 6's whole twin (glyph/6/1/7/8/2, Sean: on the 2nd ledger above) -- "space beyond ledger 1 (staff_side_edge)": the rung sits 4 px of white below the head's ink but inside the band's -0.40 sp tolerance; a stub at the head's middle shows ledger 2 through it. Opposite directions, both the on/space decision taken on box geometry. A cv_ledger cross-check was tried and DROPPED (crop look: 1-2 of its 6 Litolff contests real). Not fixed: a ledger-reader item.
- Found while tiling: `move_glyph`'s `reowned` branch writes the band GEOMETRY step on the new staff even where a ledger count toward that owner disagrees (r3 kept geometry, ledger as a candidate) -- against "a far head is placed by its ledger lines only".

**Built (r4, same flag `OMR_FARHEAD_UNREAD_GUESSED`, default OFF; c7b36e2f0).** (1) `move_glyph`: a re-owned far head whose ledger count toward the owner disagrees is placed by that count, plain (`reowned_by_ledger_reading`); none read -> blue. (2) `restate_pitch`: no far-unread guess on a box refused as a head (`head_extent.refused_as_head`). Tests: test_far_head_unread_guessed_2_248_r3.py 15 pass.

**Three measures (2-page subset Litolff 6,10 / Brahms 0,5, REPLAY of 20261029-night slices `--replay-gathered`; that gather has no ink-centre candidates, so blue far heads carry the box candidate alone).** Litolff: blue +25, nothing else; Brahms: blue +3; red bars unchanged; judged right->wrong 0, unwritten->wrong 0. No pitch moved by (1) on these pages. Control: neither arm reproduces the night record (17 L / 50 B duration verdicts, same in both arms: the tree moved since the night).
**Tiles** `out/print/2.248-r4-tiles/` (key.json outside tiles/): 12 blue far notes from the WRITTEN ON file (9 L, 3 B), each cropped down/up to its whole staff. Tiles 3, 4 look like an eighth's flag, not a head -- a non-head written as a blue far note.

### r4b (2026-11-02): r4 tiles 3, 4 were flags -- refused before any far-unread guess
**Cause.** Brahms p5 glyph/5/1/12/1/7 and 12/3/3: the detector boxed the FLAG of a down-stem eighth on the staff above as `noteheadBlackOnLine`, 1.5 x 2.2 / 2.6 sp, below its own staff. ADJUDICATE kept it (`notehead`): 2.245 tests a head box's WIDTH only; 2.220 head_ink abstained (`not_one_head`), and nothing reads that abstention. Its ink fills 0.50 / 0.42 of a filled head's window. With the flag OFF it is already written as a PLAIN eighth (an invented note); r3 only made it blue. Same family as DECISIONS 2026-10-31 (Brahms p5, a flag is not a note).
**Non-head count** (crop look at all 28 r4 blue notes): 2, both these flags; the other 26 are real heads (Litolff 25 / Brahms 1). A night-slice census of every tall, under-filled filled-class box: 4 kept non-heads (3 flags, 1 slur) plus 1 in-staff real half note (glyph/10/1/2/0/10, boxed with its stem), which the far-only rule leaves alone.
**Built** (de00f4b0a, same flag): `box_kind.far_box_not_a_filled_head` (2.245's own head shape: taller than `HEAD_BLOB_H_SP` max, filled class, ink under `HEAD_FILL_MIN`), consumed in `adjudicate_notehead_is_not_a_notehead` for FAR boxes only -> `taller_than_a_filled_head`. Fast tier 9,722 passed.
**Measures** (same replay): Litolff blue +25, nothing else. Brahms notes -3, flags -3, rests +2 (blue: the bar's real eighth rests, written now that the invented note is gone), blue +6, words +2 -1, red bars 43 -> 42; judged right->wrong 0, unwritten->wrong 0, wrong->right 1, invented->removed 1. Tiles re-cut: `out/print/2.248-r4-tiles/` (12 heads, no non-heads).

## 2026-11-02 -- landing check: the Litolff "pitches ~79" are re-gather noise, not the flag

The landing gate (fresh re-gather of the frozen sample, OFF vs ON) showed Litolff pitches ~79 and keys +1 -1. All 79 are accidental-only changes in part P2 (staff index 1), measures 3-170, under one key read: OFF read P2 m1 at fifths -3, ON at -1 (P1, P3, P4 read -1 in both arms). The OFF gather log has 3 `crop abandoned (surya ... 20.0s)` lines, ON has 0. Decisive test: the OFF arm's one saved gather re-adjudicated through export with the flag 0 and 1 -- 3928 notes each, pitch differences 0, identical key signatures, blue differs on 108 (the flag's intent). So the flag only marks; the key read on P2 moved with an OCR timeout. Open (not this lane): why a Surya timeout can change a KEY SIGNATURE read -- a header read that depends on OCR load is a second fault worth its own look.
