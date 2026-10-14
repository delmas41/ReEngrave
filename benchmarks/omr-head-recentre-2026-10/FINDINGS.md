# ROADMAP 2.115 -- re-centre a part-boxed notehead before its inside is read (STAGED GATHER)

**CONVENTION ASSUMED:** a notehead is a roughly symmetric blob, so the vertical centroid of its ink (line rows and stem columns left out) is its centre; the detector's box is trusted sideways; a box whose interior already reads hollow needs no move. Sean 2026-10-13: *"many hollow noteheads have lines through the middle of them. It needs to be a certain amount of white on the inside."*
**WHAT WOULD FALSIFY IT:** a print-confirmed BLACK head whose re-centred reading drops into the hollow band; a head moved to another pitch step; a hollow head Sean calls black/not-a-note on the new tiles.
**NOT CONFIRMED:** the two cut-offs (size gate 0.9, minimum shift 0.15 sp) are measured on two plates (Brahms 317803 pdf 0, Litolff 984073 idx 1); they NARROW until Sean's tiles and another publisher. The A/B gather (`--through adjudicate`), `judged`, `check` are NOT yet run (waiting for the overnight lock and 2.114's gathers, see bottom).

## What it does (path: STAGED GATHER; LEGACY untouched)
`gather.recentre_part_boxed` (new, pure) + `gather.gather_notehead_ink` (one branch). Flag `OMR_RECENTRE_PART_BOXED`, **default OFF** (documented in `docs/flags-2026-09.md`). A head box is moved vertically onto its own ink when ALL hold: regular notehead; no 2.39b `Q.NOTEHEAD_RECENTRE` row and no 2.73 `Q.HEAD_LINE_CUT` row; min(width, height) ratio to the standard head < 0.9; the box as drawn does NOT already read hollow (min of raw / line-rows-out centre outside [0.2, 0.75]); ink centroid (stem columns = vertical runs > 1.7 sp and line rows left out, window +-0.7 sp, iterated to 0.01 sp) at least 0.15 and at most 0.6 sp from the box centre, converged. The reading (`ink_raw`, `ink_net`, `ink_off_line`) is then taken in a standard head box at the new centre. Taken or declined, the outcome and its signed margins are filed in `Q.NOTEHEAD_INK.detail.part_boxed` (`reason`: box_head_sized / already_reads_hollow / centred_enough / no_ink / not_converged / too_far; `size_margin`, `shift_margin`, `drawn_margin`).

## Why a new reader and not a bigger `RECENTRE_BOX_SIZE_GATE` (decided with numbers)
* 2.39b maximises window FILL (accept >= 0.55). A hollow head cannot win it: on Brahms pdf 0, 12 of 39 hollow production boxes decline `below_threshold`; tile 13 itself declines at fill 0.54 and the search lands +0.5 sp, the head is +0.3 sp (`explore.py`).
* Its row feeds four other readers (ledger owner, nearer staff, stem/beam mask, rung ink); widening the gate would move those. This reader moves only the window `Q.NOTEHEAD_INK` reads and files no `Q.NOTEHEAD_RECENTRE` row, so pitch (`Q.NOTEHEAD_STAFF_POSITION` does not read the recentre row) and ownership cannot change by construction; the A/B confirms it.
* Needs BOTH conditions: an offset alone is not safe (Brahms black boxes already on their head, centroid error 0.14 sp median vs the detector's 0.00), an undersized box alone is not an error. Cut-offs from `sweep.py` (`sweep_output.txt`, 20 grid points): gate 0.9 / shift 0.15 gains every hollow the grid ever gains (Brahms +4, Litolff truth +3), loses none, flips 0 of 381 Brahms black heads at ANY grid point, and moves 20 black heads where gate 1.0 would move 119.
* Locking x: a free (dx, dy) mean-shift wandered 0.5-0.9 sp sideways onto neighbours/stems on Brahms (`centroid_probe.py`); dy-only error vs Sean's truth-box centres: hollow 0.12 sp median.
* "Already reads hollow -> leave it": the first draft moved those too and lost 2 Brahms + 1 Litolff hollow reads (their as-drawn windows were hollow by luck: Sean's own truth boxes read 0.73-0.93 on those heads). With the condition: hollow lost 0.

## Truth measurement BEFORE wiring (page frame, 600 dpi, same function; `python3 benchmarks/omr-head-recentre-2026-10/measure_truth.py out.json`; rows in `truth_rows.json`)
Reads hollow = min(raw centre, line-rows-out centre) <= 0.75; black = both >= 0.85. Litolff = the 95 clean TEST cells (`leak_check.json`, 2.114's run of the 2.112 guard: 9 of 104 cells excluded; the 2.112 `leakage_guard.py` itself was not re-run here).
| page / population | heads | re-centred | hollow/between/black before | after |
|---|---|---|---|---|
| Brahms pdf 0, Sean's BLACK heads | 381 | 20 | 0/0/381 | 0/0/381 (black -> hollow 0) |
| Brahms pdf 0, Sean's HOLLOW heads | 39 | 6 | 32/6/1 | 36/2/1 (+4, lost 0) |
| Litolff idx 1, truth HOLLOW (production box on it) | 43 | 4 | 36/2/5 | 39/2/2 (+3, lost 0) |
| Litolff idx 1, other production boxes (unlabelled) | 96 | 7 | 3/2/91 | 5/3/88 |
Tile 13 (`glyph/1/0/9/11/1`): shift +0.26 sp (by eye 0.30), reading raw 1.00/off-line 1.00 -> 0.81/0.63, inside the hollow band. The two other Litolff hollow gains are the stacked `9/9/5` + `9/9/6` pair (0.93 -> 0.82/0.69). Brahms gains `5/1/16`, `5/2/16`, `6/2/8`, `6/2/14`. Of the 3 flips among the unlabelled Litolff boxes, 2 (`3/3/2`, `9/3/2`) are heads with a visible white slit on the crop (`inspect_crops.py`), 1 (`9/0/12`) goes to the between band; judge on Sean's tiles. All 20 moved Brahms black heads and the moved Litolff black ones read black afterwards (crop sheet checked).
Pitch step: not computed on page frame; by construction none (see above). Reported from the A/B below.

## Controls (rule 7)
RED-first: 10 of the 15 first tests fail on the old tree. `tools/omr/tests/test_staged_part_boxed_recentre_2_115.py` (17 tests): tile-13 geometry hollow after / black before; filled head with a line through it stays >= 0.85 on every raster; correctly sized box untouched; undersized-but-centred box no-op with a negative signed margin; blank paper declined; stem alone / stem on head do not drag the centre; already-hollow box keeps its reading; no `Q.NOTEHEAD_RECENTRE` row filed; restated cuts pinned equal to `rhythm`'s. Sean's black tiles 7, 11 (Brahms) and 16 (Litolff) are head-sized boxes (ratio >= 0.9), so the rule declines them (`box_head_sized`) -- on the truth page all 381 black heads read black after.

## Tiles for Sean
`out/print/2.115-recentre/` (12: 10 heads whose reading class changed on the truth pages + 2 black controls that were moved and stayed black; hidden `manifest.json`; red corner bracket on the head only). Built from the page-frame measurement; re-cut from the gather A/B when it exists.

## A/B in the real gather frame (`--through adjudicate`, flag OFF vs ON, tree `0fdc139f`, one page at a time; `ab_compare.py`, `ab_lit.json`, `ab_bra.json`)
Command: `python3 -m tools.omr.staged <pdf> --pages 1|0 --weights omr-weights/deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt --through adjudicate --no-surya --no-ocr --out runs/2.115/rec-{lit,bra}-{off,on2}.json` (records gitignored).
* **THE HEADLINE CASE IS NOT FIXED IN THE GATHER.** The page-frame result above does not carry over: the cell's canonical `binary` raster merges the head with its stem and the next staff line, and the ink centroid then depends on the window size (tile 13 in its real cell: shift 0.00 / 0.15 / 0.57 sp at windows 0.60 / 0.65 / 0.70; Sean's truth box says 0.27; `10/6/6` and `10/7/1` land right at 0.2-0.3 but spread 0.20-0.27). The first ON gather (no guard) moved 4 Litolff heads, tile 13 by +0.57 sp (too far; its read happened to fall hollow, 0.49) and it turned `10/6/6`'s reading from 0.76 to 0.90. That is why the rule now refuses an estimate that depends on the window (`unstable`, spread cut 0.1 sp, margin filed). With the guard: **Litolff ON: 0 heads moved** (candidates: centred_enough 11, no_ink 2, unstable 5, tile 13 among the unstable); **Brahms ON: 10 heads moved, all black-class, 0 verdict changes**, unstable 19.
* Identical control (OFF vs ON): every glyph (key, class, box, score) identical (751 / 1776); every observation of every quantity other than `notehead_ink` identical (4761 / 11699); duration verdict differences outside the moved heads 0; **pitch step changes 0 of 10 moved** (Litolff 0 of 0).
* `python3 -m tools.omr.staged.judged score REC --doc litolff|brahms`: ON and OFF records give the identical table (litolff TOTAL 3/0/0/0/106/73, brahms 16/1/10/1/68/96). `python3 -m tools.omr.staged.check`: open=192, status ok (not up). Fast tier at `c7790dc2`: 7787 passed, 11 skipped, 2 xfailed (the later commit only adds one guard, one test and a fixture).
* Net effect of the flag as it stands: no change to any hollow found, none lost, no verdict moved. **It is safe and inert on these two pages; it does not fix tile 13.** Do not land for the tile; nothing is gained to ask Sean about.

## Tiles
`out/print/2.115-recentre/` (12) were cut from the PAGE-frame measurement (what a stable centre would change on the hollow heads: 4 Brahms, 3 Litolff truth-hollow, 3 unlabelled, 2 black controls), NOT from the gather A/B, which changed no reading class. Useful to Sean as a question about those heads (is the hollow reading right?), not as a check on the flag.

## What would fix it (not built; needs a decision)
The centroid needs an uncontaminated raster or another locator: (a) read the head on the PAGE raster (the cell holds only the canonical binary; a cell-to-page map exists in the cell metadata) where the same rule is stable (+0.26 sp, 0 black flips of 381); (b) a hollow-aware locator that finds the head's two white slits (the hole, not the ink) and centres on them; (c) Sean boxes a few more part-boxed heads so the second detector's box (2.114) could carry the centre. Fast tier 7787 passed, 11 skipped, 2 xfailed (`c7790dc2`).

---

# ROUND 2 (2026-10-14) -- read the head off the PAGE raster (Sean's decision)

**CONVENTION ASSUMED:** same as round 1 (a head is a roughly symmetric blob; its vertical ink centre, line rows and stem columns left out, is its centre). **WHAT WOULD FALSIFY IT:** a print-black head read hollow after the move (see tile 2 below -- one candidate), a head moved to another step (0). **NOT CONFIRMED:** the window set, the size gate 0.9, the shift cut 0.15 sp and the spread cut 0.1 sp, all measured on two plates; Sean's tiles are not back.

## What changed (STAGED GATHER; LEGACY untouched; flag `OMR_RECENTRE_PART_BOXED` still default OFF)
* `gather.gather_notehead_ink(..., pws=None)`: the call site now passes `pws`. The part-boxed branch calls **`gather.recentre_part_boxed_on_page(cell, det, page_binary, space_canonical)`**, which maps the detection to page pixels with the existing `_page_box` (cell `bbox_page_px` + `upscale_factor`, the mapping `Q.GLYPH_BOX` files; page space = canonical space / upscale, as `gather_arc_ink` does) and runs the unchanged `recentre_part_boxed` on **`pws.page.binary`** (0 = ink, staff lines in -- the page raster `gather_arc_ink` already reads; it IS available at that point in GATHER). Line rows are the rows with ink past the head both sides at the head's own x, i.e. local by construction (2.73's definition). Where accepted, `ink_raw` and `ink_off_line` are read off the page raster at the standard head box at the moved centre (`detail.ink_frame = "page"`); `ink_net` stays the cell's erased raster at the same moved box. No page raster / mapping / staff unit: declined `no_page_raster`, **never read from the cell**. Nothing else moved (no `Q.NOTEHEAD_RECENTRE` row; fence respected).
* **Round 1's page-frame claim was wrong once the guard existed.** The "+0.26 sp, stable on the page" number was a single window (0.7) measured BEFORE the stability guard. On the real page raster tile 13's centroid is a function of the window too: shift -0.17 / -0.08 / 0.01 / 0.12 / 0.26 / 0.38 / 0.36 / 0.36 at half-window 0.5 / 0.55 / 0.6 / 0.65 / 0.7 / 0.75 / 0.8 / 0.9 sp (by eye 0.27-0.30). A window smaller than the head clips the ring asymmetrically once the line rows are out. With round 1's windows (0.6-0.75) and the guard, the page frame refuses tile 13 too (`unstable`, spread 0.374), Litolff truth moves 0 (`truth_guarded`, in this section's table below). The windows that contain a whole head (0.75-0.9) settle. So the one change beyond the brief: **`RECENTRE_PART_WINDOWS` = (0.75, 0.8, 0.85, 0.9), main 0.8** (was 0.6-0.75, main 0.7); guard and spread cut (0.1 sp) unchanged. Tile 13's centre lands 0.36 sp (eye 0.27-0.30; 0.06 sp low, reads 0.68 raw / 0.25 off-line, inside the hollow band). On the cell raster those same new windows would land it 0.41 sp (merged stem/line): the cell is not used.
* Window sweep (page frame, truth populations, `sweep_windows_r2.py`; guard on). Rows: windows, main, spread cut -> Brahms black moved/flips | Brahms hollow gained | Litolff truth-hollow gained | tile 13:
  (0.6,.65,.7,.75) 0.7 / 0.10: 8 / 0 | +2 | 0 | unstable (this is the round-1 setting + guard)
  (0.6,.65,.7,.75) 0.7 / 0.15: 8 / 0 | +4 | 0 | unstable
  (0.75,.8,.9,1.0) 0.8 / 0.10: 10 / 0 | +3 | +3 (+1 to between) | moved 0.36
  (0.75,.8,.9,1.0) 0.8 / 0.15: 15 / 0 | +4 | +3 (+1) | moved
  (0.7,.75,.8,.9) 0.8 / 0.10: 14 / 0 | +4 | +2 (+1) | unstable
  (0.7,.75,.8,.9) 0.8 / 0.15: 16 / 0 | +4 | +3 (+1) | moved
  **(0.75,.8,.85,.9) 0.8 / 0.10 (adopted): 19 / 0 | +4 | +3 (+1) | moved 0.36**
  (0.75,.8,.85,.9) 0.8 / 0.15: 21 / 0 | +4 | +3 (+1) | moved
  (0.8,.9,1.0) 0.9 / 0.10: 15 / **1 black->hollow** | +3 | +3 | moved
  (0.8,.9,1.0) 0.9 / 0.15: 21 / **1** | +4 | +3 | moved
  Chosen on the same truth pages it is reported on (so it is a measurement, not an out-of-sample test) and with the spread cut left at round 1's value; it narrows until Sean's tiles / another publisher.

## Truth measurement (page frame, `measure_truth.py`, rows `truth_rows_r2.json`; hollow = min(raw, off-line centre) <= 0.75, black = both >= 0.85; Litolff = the 95 clean TEST cells of 2.114's run of the 2.112 guard, 9 of 104 excluded; the 2.112 `leakage_guard.py` itself not re-run)
| population | heads | re-centred | before hollow/between/black | after |
|---|---|---|---|---|
| Brahms pdf 0, Sean's BLACK heads | 381 | 19 | 0/0/381 | 0/0/381 (black -> hollow 0) |
| Brahms pdf 0, Sean's HOLLOW heads | 39 | 6 | 32/6/1 | 36/2/1 (+4, lost 0) |
| Litolff idx 1, truth HOLLOW | 43 | 4 | 36/2/5 | 39/3/1 (+3 hollow, 1 black->between, lost 0) |
| Litolff idx 1, other production boxes (unlabelled) | 96 | 6 | 3/2/91 | 5/2/89 (black->hollow 2) |
Same function round 1 used; round 1 (no guard, windows 0.6-0.75) read: Brahms black 20 moved / 0 flips, hollow 32->36, Litolff truth 36->39. Round 1 windows + guard, same pages (this session): Brahms black 8 / 0, hollow 32->34, **Litolff truth 36->36 (0 moved)**.

## A/B in the real gather (`--through adjudicate`, tree `7f7a647c`, flag OFF vs ON, fresh OFF and ON for each page, one page at a time, `ab_compare.py`; `r2_ab_lit.json`, `r2_ab_bra.json`; records in gitignored `runs/2.115/r2-*.json`)
Command as round 1 (weights `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, `--pages 1` Litolff 984073 / `--pages 0` Brahms 317803, `--no-surya --no-ocr`).
| | heads moved | `ink` reading numbers changed | reading class changed | pitch-step changes | duration verdict changes | everything else |
|---|---|---|---|---|---|---|
| Litolff 984073 idx 1 | 3 (was 0) | 3 | 3 (black->hollow 1, black->between 1, between->hollow 1) | 0 | 1 (tile 13) | 751/751 glyphs and 4761/4761 other observations identical; 0 other duration verdict differences |
| Brahms 317803 pdf 0 | 20 (was 10) | 20 | 1 (black->hollow: `glyph/0/0/4/4/7`, unlabelled; 19 black stay black, all 17 of Sean's labelled heads among them) | 0 | 0 | 1776/1776 glyphs and 11699/11699 other observations identical; 0 other differences |
* **Tile 13 in the REAL gather (`glyph/1/0/9/11/1`): OFF** raw 1.00 / net 1.00 / off-line 1.00, duration DECIDED quarter (1 beat, `head_and_marks`). **ON** shift +0.361 sp, raw 0.68 / net 0.71 / off-line 0.25, duration **narrowed** (`head_fill_from_ink`: half 2.0 / quarter 1.0 / whole 4.0 beats, none chosen) -- the reader no longer states a quarter on a hollow head, it says it cannot tell. `ink_frame: page`.
* The other two Litolff moves: `10/7/1` (halfInSpace, 0.99 -> raw 0.91 / off-line 0.81, still decided half), `3/7/2` (halfOnLine, 0.90/0.78 -> 0.89/0.75, still decided half): reading closer to Sean's hollow band, no verdict change.
* **One surprise, shown not hidden: `glyph/0/0/4/4/7` (Brahms, unlabelled, `noteheadBlackOnLine`, moved -0.25 sp) reads 1.00 OFF and 0.66 ON, and on the printed crop (tile 2) it looks black.** Both verdicts are `abstained not_a_note_mark`, so nothing downstream changed, but it is a black-looking head read hollow after the move: the rule can still mis-centre a small slanted black head and the standard box then holds white. 0 of Sean's 381 labelled black heads did this; 1 of 3 moved unlabelled Brahms heads did. Tile 2 settles whether it is a real failure; do not turn the flag on before the tiles.
* `judged score` (litolff TOTAL 3/0/0/0/106/73; brahms 16/1/10/1/68/96): OFF and ON identical, and identical to round 1's. `python3 -m tools.omr.staged.check`: open=192 status ok (round 1: 192; not up).
* Declined reasons (ON): Litolff centred_enough 11, no_ink 3, already_reads_hollow 2; Brahms centred_enough 39, unstable 21, no_ink 12, too_far 3, already_reads_hollow 3.

## Tests (`tools/omr/tests/test_staged_part_boxed_recentre_2_115.py`, 25)
RED first: on the round-1 tree (`gather_notehead_ink` without `pws`, round-1 windows) 13 of the 24 then-existing/new tests failed (the wired ones all, `TypeError` on `pws`, plus the real-cell ones). New real fixtures: `data_part_boxed_tile13_cell.npz` (the page crop of tile 13 at 600 dpi from `render_page(...).binary` + the cell's real merged raster + the cell's mapping), `data_part_boxed_black_tiles.npz` (page crops of Sean's black tiles 7, 11 Brahms and 16 Litolff). Pinned: tile 13 flag OFF black; flag ON re-centres off the page, `part_boxed.frame == "page"`, off-line centre in [0.2, 0.75]; round 1's windows on the real cell raster AND on the real page crop still refuse `unstable` (the guard bites where it should); no page raster declines `no_page_raster` and reads black as before; Sean's tiles 7/11/16 ON == OFF exactly (head-sized boxes, never moved; 7 and 11 read 1.00; tile 16, a black head with a line through it, reads 0.78 raw / 0.875 off-line on the page, with the flag off too); a centred head-sized box is a no-op; flag OFF identical. Fast tier at the code commit: 7795 passed, 11 skipped, 2 xfailed.

## Tiles for Sean
`out/print/2.115-round2/` (6; replaces round 1's page-frame `out/print/2.115-recentre/`, removed): the 4 heads whose reading class changed in the real gather A/B (3 Litolff, 1 Brahms) + 2 controls (Brahms black heads that were moved and stayed black). Nothing drawn but a small red corner bracket; "hollow or black? (or: not a note)"; hidden `manifest.json`. Fewer than the cap of 15 because the gather moves only 23 heads in all and only 4 change class. Lane 2.114's tiles not re-asked.

## Sean's answers on the 6 round-2 tiles (2026-10-14; `out/print/2.115-round2/answers.json`, checked against `manifest.json`)
Sean: "1.2 2. Slash trem 3. Dot 8 4.2 5.8 6.2" = 1 hollow (half), 2 not a note (tremolo slash), 3 black (dotted eighth), 4 hollow (half), 5 black (eighth), 6 hollow (half).
* **Controls 3 and 5 (moved, stayed black): right** (black).
* **Changed heads 1, 4, 6 all moved toward Sean's answer**: 1 (`10/7/1`) black->between (he says hollow); 4 (`9/11/1`, old tile 13) black->hollow; 6 (`3/7/2`) between->hollow.
* **Tile 2 (`glyph/0/0/4/4/7`, the "surprise") is a tremolo slash that production boxes as a head**: not a note either way; it was already refused as `not_a_note_mark` downstream, so nothing it does matters. The black-looking-read-hollow worry is closed: it was never a head.
* Landed ON by Sean's word, "Land 2.115 on" (2026-10-14). Caveat: the windows (0.9 box test, guard) were chosen on the same two pages (Litolff 984073 idx 1, Brahms 317803 pdf 0) the tiles come from; another publisher is untested.
