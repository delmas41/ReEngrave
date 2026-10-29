# Ink map step 6, FILL: measurements behind the plan (ROADMAP 2.220)

Plan: `docs/plan-2026-10-28-ink-map-step6-fill.md`. Source, one record and its own export (like with like): `2-202-beams-cause-1f79a5/out/lane-report/2.202f/work/*.on.*` (frozen sample, 8 pages/plate, main's defaults). Each count is labelled READER (reader vs reader on one box) or FILE (the written note vs the readers of its own box). Scripts here: extract/readers/classes/kinds/dist/filelevel/judged_fill.py (they read scratch extracts; re-run extract.py first).

## Cause
- The stroke map has no head: `map_strokes` claims verticals/horizontals first, so a hollow ring falls apart into lunes + rims; `hole_share` = 0.0 on all 766 written halves (538 Litolff / 228 Brahms), same as filled heads. Step 6's "derivable from the blob" was never measured. Process lesson: each ink-map step first measures its own field on the population it serves, on a saved record.
- Fill is read inside the detector's box: outside 1.1-1.9 x 0.9-1.8 sp, 2.148 files `fill null, not_head_sized` and the detector's black class is written unread (2.204 tile 1).

## Readers that decide fill today
GATHER: `gather_notehead_ink` (centre/ring windows on 3 rasters; `interior_white` slit; slit on the located box), `notehead_recentre.fill`, `stacked_head_fit` hollow branch, stroke-map `hole_share` (unread). ADJUDICATE: `_head_reads_hollow_first` (2.148) + located (2.159) / bridged (2.161) variants, `_head_is_open` -> `_ink_reads_decisively_hollow` (2.23), `_hollow_readings` / `_raw_reads_firmly_hollow` / `_hollow_margin` (2.88), `_reads_filled`, `notehead_precision._hollow_ink_reading` (twin keeper), plus the detector class.

READER disagreement where both decide: detector vs slit 7.6% Litolff / 1.7% Brahms; detector vs window 5.0 / 1.9; slit vs window 3.2 / 1.4. The window is silent on 692 / 301 boxes the slit reads.

## Failures at the file (written notes from head boxes: Litolff 3,739, Brahms 4,430)
- A. written black, ink hollow: 22 / 6 (26 / 6 counted through `not_head_sized` + fill null); 21 of 22 and 6 of 6 outside the head-size gate; 7 Litolff are slanted halves boxed 1.91-2.02 sp wide.
- B. written hollow, ink filled: 21 / 8; 15 / 7 are `stem_value_follows` (a black head takes a half from its stem-mate).
- X. slit and window disagree on a written note: 50 / 5; 40 Litolff written hollow (slit hollow, window filled), 26 with a staff line through the hole.
- Twins: 143 / 23 black+hollow pairs; today's keeper agrees with its ink 79/87 and 11/11 but flips when the ink changes (2.212).
- Not written though ink reads hollow: 616 / 283 -- twin written (140/32), refused not-a-notehead (218/177), other staff's owner (129/44): identity/ownership, out of scope.
- Fill unreadable by both ink readers: 9 / 7.

## Crops (not yet answered)
8 class-A tiles (6 Litolff, 2 Brahms) in the plan worktree `out/print/2.220-plan/` (key outside the tiles folder). Question for Sean: half note, filled note, or not a note?

## Sean's answers on the 8 class-A tiles (2026-10-28, `out/print/2.220-plan/answers.json`)
"1.2 2. part of ff 3. flag 4.2 5.2 6.4 but box also includes a good amount of a sharp 7-8. 2"
STAGED wrote all 8 filled (quarter/eighth). Tally: 5 wrong (tiles 1, 4, 5, 7, 8 are half notes), 1 right (tile 6, a quarter, but its box takes in a sharp), 2 INVENTED (tile 2 is part of an ff; tile 3 is a flag).
Observation: the 5 real halves have box widths 1.3-1.9 sp; the 3 that are not plain heads are larger (3.88 wide, 2.22 tall, 2.15 wide). So `not_head_sized` separates them partly, but a "larger box = hollow" rule would invent 2 notes and get 1 wrong of 8: size cannot decide fill; a box that is not head-sized is a question about identity (is it a head at all?) before fill.

## Milestone 1, rebuilt (2026-10-28, Sean "I think rebuild this way"): `Q.HEAD_INK` on the page raster, behind `OMR_FILL_FROM_STROKES` (OFF)
STAGED GATHER. `tools/omr/staged/head_ink.py` (pure) + `gather.gather_head_ink`. The stroke-map head mask (WIP 5ab6502d2) was STRIPPED: no change to `Q.STROKE` / `map_strokes`; heads claiming their ink first is deferred.
- Cause, restated: the reader asked fill of the DETECTOR's box. On the page raster the 2.148 slit on Sean's 8 detector boxes reads hollow on all 3 non-halves too (ff 0.50, flag 0.52, sharp-quarter 0.70; pinned as a control in `test_head_ink_2_220`). Head-hood has to come first.
- Mechanism: bare staff/ledger-line runs out at the head's own x (2.164's `_line_rows`/`_kept_rows`; a ledger = a row a 1.7 sp horizontal run crosses); the head = the run of head-tall columns (2.164's span) over the box core, rows whose ink spans half that run; line rows at the block's ends trimmed; `not_one_head` past 1.75 x 1.5 sp, under 0.6 sp, or where an accidental/key/flag/dynamic box centred on the trimmed head holds >= 25% of its ink; 2.148's `head_interior_white` (unchanged, cut 0.18) on the trimmed box. Stems are NOT cut (a vertical opening took the solid column through Litolff p2's merged stacked halves); fix C = clip a two-head column over a head-sized box to the box rows.
- READER, Sean's tiles (page raster, 600 dpi; `m1_measure.py`): 1, 4, 5, 7, 8 hollow (slit 0.36/0.42/0.64/0.36/0.62); 2 `not_one_head` (ff), 3 `not_one_head` (flag box on it), 6 filled (trimmed to the head, slit 0.0). 8/8.
- READER, written halves (2.202f ON record, decided written 2.0), Litolff 4+6 and Brahms 5+14: slit >= 0.18 on the trimmed head 203/217 (93.5%; Litolff 201/213, Brahms 2/4). Same halves, slit on the detector box on the page raster: 196/217 (90.3%). Below the 95% bar. The 14 misses (`m1_half_misses.png`) by eye are mostly not hollow heads: an f's hook, flats, filled heads written half (class B), a rest, solid tremolo/bar blocks; not confirmed -- needs Sean's look.
- CONTROL (can fail), written quarters same pages: value hollow 30/1098 (2.7%; Litolff 13/575, Brahms 17/523); slit >= 0.18 77/1098 (7.0%). Eighths: hollow 17/1232.
- Cost seen: `not_one_head` fires on 143 Litolff / 157 Brahms written quarters (most `too_small`: boxes 0.35-0.5 sp wide, by size not heads; not checked by eye).
- Fix D: tile 13 (2.115) trimmed centre moves <= 0.1 sp across slack 0.4-0.7 and the box slid 0-0.3 sp, and sits below the rim box (test).
- Height cut 1.5 sp is a measurement on our plates (Litolff halves trim to 1.38 tall median), so it may only narrow (CLAUDE §4).
- FILE vs FILE: real gather OFF vs ON (`OMR_FILL_FROM_STROKES` 0/1), same tree, detector cache, Litolff p4 and Brahms p5 (`python3 -m tools.omr.staged <pdf> --pages N --dpi 600 --weights auto --route-weights --musicxml ...`): both MusicXML files byte-identical (`cmp`); `head_ink` rows ON 1001 / 1246, OFF 0. In the real gather, tile 4 hollow (slit 0.42), tile 2 not_one_head, tile 3 not_one_head, matching the offline reader. Litolff p4: filled 589, hollow 105, not_one_head 290, readers_split 12; Brahms p5: 898 / 34 / 238 / 70.

## Milestone 1: Sean on the 14 "missed" halves (2026-10-28)
"None" of the 14 is a half note. Every miss is a note the file WRONGLY writes as a half; the reader was right. On these 4 pages the reader reads the hole on 203 of 203 real halves (assuming the 203 hits are real; not yet tiled), and milestone 2 can remove 14 wrong halves. The 95% bar is met once the denominator is real halves, not written halves (CLAUDE rule 7: who says it's right).
