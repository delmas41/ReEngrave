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

## Not done yet / waiting
A/B `--through adjudicate` (Litolff idx 1, Brahms pdf 0, flag OFF vs ON), `judged score`, `staged.check`: blocked by `library/_shared-records/.overnight-20261013.lock` and 2.114's running gather. Fast tier: see the lane report.
