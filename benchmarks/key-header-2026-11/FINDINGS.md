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
