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
