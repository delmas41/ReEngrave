# 2.307 page and zoom -- FINDINGS

Plan: `docs/plan-2026-11-13-page-and-zoom.md`. STAGED. Measurement only; no default changed.
Branch `lane-2.307-page-and-zoom-test` cc520425e (scripts and `results/` are on the branch).

## Round 1 (2026-11-13): the two measurements

**Answer.** Partly. Showing readers marks by owner (change A) is safe and changes almost nothing in TODAY's
file. The detector through the whole STAFF ROW did about as well as cells on Sean's Brahms p0 with fewer
extra boxes and 2-3x faster; the SLIDING BAND did worse. Row vs cells disagree on 15-18% of filled heads on
the other 7 pages and nobody has judged which is right.

**Cause and lesson.** The cost of copies has mostly been absorbed already, one reader at a time (447 of 470
Litolff and 487 of 542 Brahms copies were already turned away by the duration reader). One filter protects the
NEXT reader that makes something more correct (what bit 2.306 r1); it does not improve today's file. A
family-blind filter is wrong: arcs, articulations and dynamics are written through their own owner decisions.
The cell edge does show in the data: Brahms boxes only cells find sit at a barline 33-44% of the time, against
1% for boxes both ways find (the lane's crop look: ~15 of 20 are slivers on the barline -- a lead only).

### T1 what the cell costs
- Copies (decided owner is another staff), frozen pages: Litolff 551 (filled 359, hollow 107, whole 3,
  accidentals 81, rests 1); Brahms 653 (489, 29, 10, 111, 14). Of the 13 readers 2.306 r3 listed, seven are
  handed copies (`adjudicate_stem_value`, `adjudicate_head_stem`, `adjudicate_unison_voices` 469 / 528;
  `_second_evidence` 551 / 653; `_direction_from_a_beam_mate` 479 / 598; `_flag_direction`, `_own_stem_side`
  20 / 30); EXPORT's three get none.
- Detector boxes touching a cell edge (Litolff / Brahms): filled heads 300 of 2,636 / 418 of 2,814; hollow
  92 of 599 / 17 of 184; accidentals 168 of 452 / 143 of 772; rests 42 of 656 / 88 of 988; **arcs 552 of 879 /
  1,590 of 2,141; beams 251 of 468 / 764 of 1,529**; ledger lines 1,100 of 2,678 / 49 of 922.
- Known unboxed heads at edges: NOT determined. None of Sean's 411 Brahms p0 heads lacks a box today; the
  2.305 tile 8 chord sits 1.4 sp from its cell's left edge in the padding band, the missing head's place is in
  no record.
- Prototype `OMR_PAGE_OWNED_VIEW` (OFF; `staged/owned_view.py`): after ownership is decided, a reader that
  LISTS marks is not handed another staff's head, rest or accidental (asking by name still works). Two
  places, not one -- ADJUDICATE/EVALUATE/INFER share the in-memory record, EXPORT builds its own index.
  OFF vs ON on the 2.305 saved gathers: Litolff rests +4 -3, ties +4, slurs +6 -2, red bars 0 -> 0 (84 -> 84
  by red in the file); Brahms notes +3, rests +4 -7, ties +4, slurs +8 -1, articulations +12, red bars
  64 -> 63. Judged right->wrong 0, unwritten->wrong 0. check 228. One bar worse (Brahms p20 part 2 bar 46:
  with the copy hidden the voice reader splits the bar; not traced). Round 1 of the filter hid every family
  and lost slurs -50 / -93, articulations -42 / -47, dynamics -12 / -15.

### T2 the detector through cells, the staff row, sliding bands
Production detector, routed weights, 16 px per staff space. Brahms p0 vs Sean's labels (found / missed / not
his); his labels were prefilled from a cell run, so cells are favoured by construction:
filled heads (378): cells 378/0/37, row 377/1/15, band 377/1/59; hollow (33): 33/0/5, 33/0/8, 31/2/6;
whole (0): 0/0/19, 0/0/0, 0/0/24; rests (16): 16/0/4, 15/1/1, 15/1/7; accidentals (41): 41/0/9, 41/0/4,
41/0/15; flags (42): 39/3/3, 42/0/3, 42/0/6; dots (131): 130/1/4, 130/1/4, 131/0/10; clefs (15): 15/0/2,
15/0/4, 15/0/0.
All pages vs cells by place (both / only cells / only this way): filled heads Brahms row 2046/378/20, band
2308/243/359; Litolff row 1841/405/87, band 2305/198/624. Rests Brahms row 765/131/87; Litolff row
445/201/106. Accidentals Brahms row 581/84/98; Litolff row 300/92/137.
Boxes only this way finds, per page: row ~100 (B) / ~180 (L); band ~245 / ~380 (includes same mark under
another family). Sean's judged marks on these pages (21): his 11 heads and 1 rest are boxed every way; of 9
he called not-a-note cells box 1, row 0, band 1. Time per page: cells 16-27 s, row 5-11 s, band 17-44 s.

### Against plan section 6
- T1: the filter moves little and costs nothing judged = "copies are not the main cost TODAY". Change A
  stands as protection, not as a gain.
- T2 band: falsified (more false boxes, two hollow heads missed on p0).
- T2 row: not falsified on p0; UNRESOLVED elsewhere -- the 378 / 405 filled heads only cells find are the
  question, and need Sean's tiles.

### Not measured
Who is right in the row-vs-cells disagreements; T2 used fresh-cut cells without box splitting or rescues;
replays ran on the 2.305 gathers, not the standard frozen sample; full fast tier not run
(`test_staged_export.py` fails 3, the same 3 as origin/main).
