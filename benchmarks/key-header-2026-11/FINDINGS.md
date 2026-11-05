# 2.256 — The key is read from its header ink (STAGED; Sean "Open both", 2026-11-03)

Lane `lane-2.256-key-header` 2927c0734 (Sonnet). Flag `OMR_KEY_HEADER_INK`.
Written by the manager from the lane's report (a hook refuses report files from subagents).

## Why it was opened
Manager's blue-note census, 20261031-night Litolff frozen 9 pages: 718 of 1,265
blue notes (80/page, 57% of the check load) were blue only because their
staff-system's key was not read and INFER `fill_part_key` filled it (usually right).

## Cause and process lesson
Litolff prints the three key flats crushed together; the detector boxes only one
or two (the lowest has no box). 16 staves crop-checked: all show three flats. The
marker count reads 1-2 slots, the part check abstains the staff, INFER fills it
blue. The readers do not disagree -- the detector under-counts.

Counts (Litolff, 9 pages, 184 staves): 104 abstain -- 54 `disagrees_with_document`
(marker run read 1 slot on 21, 2 on 28, 3 on 5), 19 `disagrees_with_system`,
7 `needs_clef` (2.257), 9 `no_evidence`, 5 `disagrees_with_part`. Brahms p0, p5:
36/42 decided -- not a crushed-flat plate.

**Lesson:** GATHER's key object (2.187) already read the header ink once per
system (count 3) and filed each staff's own slot count on its `cv_key_object`
claim row; ADJUDICATE never read it (the count was already 3 on 17 of the 54).
A measurement filed for ink ownership is also a reading -- ask who consumes it.

## Fix
`tools/omr/staged/key_header_ink.py` + a branch in `header._staff_reading`:
a clean one-kind marker run is raised to the key object's own count when that is
higher and within the system count. The kind stays the detector's; it never
lowers a count or supplies a kind; the system and part checks still judge.

## Three measures (frozen Litolff 8 pages, merged tree, flag only)
- File: blue marks 1468 -> 1312 (-156); nothing else changed. Brahms p5: no change.
- 24 staves abstained -> decided -3 (all non-transposing; ten crop-checked);
  INFER key fills 104 -> 80.
- Judged right->wrong 0, unwritten->wrong 0 (149 changed places unjudged).

## Sean's tiles (2026-11-03; answers-r1.json)
"2. Is one flat all the other tiles are 3 flats. All easily visible."
Tiles 3-11 (changed, ON -3) right 9/9; controls 1 (-3) and 2 (-1) right;
tile 12 (staff/4/1/3, still abstained) is three clear flats we miss -- blue, not
wrong. 11/12 right, 0 wrong. Sean: "Land whatever is ready".

## Not established
- 28 staves whose key object counts 2 slots and 8 that count 1 stay blue (tile 12 is one).
- The Brahms control line does not reproduce the saved record (tree moved; same in both arms).

## 2.256b — key round 2: count the stems that survive (NOT landed; lane-2.256b-key-r2 11a2740ac)
Flag `OMR_KEY_OBJECT_COUNT` OFF. Filed by the manager from the lane report.
- **Cause:** the key object's whole-flat piece test (0.45-1.9 sp wide, 1.6-4.4 tall) fails on damaged
  ink -- Litolff breaks a flat's stem from its bowl or fuses 2-3 flats; Brahms shows 3 clean stems the
  object counts as 1-2. The stem survives (thin vertical run 2.0-3.9 sp). **Lesson:** a whole-glyph
  shape test is brittle on scans; count the stroke that survives at its fixed slot position.
- **Fix:** `key_object.flat_stems` counts stems in the fixed flat order for the clef, stem top in a
  measured window (-5.8..-1.2 steps) against the local staff; never lowers a count; nothing without a
  measured clef; kind stays the detector's. Raster-only: 55/75 Litolff, 24/56 Brahms `fill_part_key`
  staves rise to 3; ~20 per plate unreachable (no clef measured, kind misread natural, transposing staves).
- **Measures (2 pages per plate, OFF vs ON; NOT the frozen sample):** Litolff p2+p4 12 staves changed,
  pitches ~107 (natural -> flat), blue +34 -17, notes not written 645 -> 646 (one quarter lost at
  4/0/3/0); Brahms p14+p19 11 staves changed, notes +47 rests +38 ties +24, blue +10 -31, notes not
  written 1006 -> 921 (growth at 14/1/5, 14/1/7, 14/1/8 unexplained, unjudged). Judged right->wrong 0
  both plates. Fast tier 9903 passed, 0 failed.
- **Sean's tiles (answers-2.256b.json):** "tiles 6 and 10 have no accidentals, all the others have 3
  flats." ON 12/12 right (9 cases incl. 0->3 and 1->3, three-flat control, two none-read controls);
  OFF 3/12.
- **Not established:** blue by rule (is `fill_part_key` down?); frozen 8-page sample; sharps and
  > 3 flats; the Brahms churn's cause.

## 2.256b Brahms p14 growth -- explained (manager crop/file look, 2026-11-04)
- **Cause:** not new ink. With `OMR_KEY_OBJECT_COUNT` OFF, three p14 staves had no instrument: the exported file names them `Staff p14-s0-6`, `-9`, `-12` (64, 89, 133 notes), and bars of theirs were held out (notes not written 1006 -> 921). With it ON, their keys are read and the staves are named Horn (2nd horn staff), Violin (I) and Cello, giving the roster order Fl Ob Cl Bn CBn Hn Hn Tpt Timp Vn Vn Va Vc Cb, which is the printed order. The whole bars at 14/1/5, 14/1/7 and 14/1/8 are those staves' music now written. Part totals OFF 1770 -> ON 1855 notes. The per-part shifts (Violin parts 89+167 -> 112+190) are the routing that follows from the names. **Lesson:** a key read is also an identity witness; a "notes gained" row can be a staff named, not ink read.
- **Not established:** the newly written notes themselves are unjudged (46 notes, 38 rests, 24 ties in the unjudged list); none are in Sean's judged set. The roster order is a corroboration, not a tile.
