# ROADMAP 2.128 -- a dot carries its staff position

2026-10-14, branch `lane-2.128-dot-position` (0038326e), not merged. Written by the manager from the lane's report
(the lane's Write tool refused this file).

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED
* ASSUMED: an augmentation dot stands in a space, never on a line; after a line-note it sits in the space above OR
  below; after a space-note, in that same space. A `docs/page-facts.md` line, not registered in `tools/omr/conventions.py`.
* Measured on Sean's Brahms p0 labels: after a line-note the dot is above 41x / below 19x; after a space-note in the same
  space 54 of 56; only 3 of 120 dots read as on a line (2 of them boundary noise).
* NOT CONFIRMED with Sean (asked 2026-10-14).

## What was built
* GATHER, always on: `Q.DOT_STAFF_POSITION`, filed by `gather.gather_dot_positions` on every `Q.AUG_DOT` glyph (staccato
  classes included), in `NOTEHEAD_STAFF_POSITION`'s unit (even step = line, odd = space) with step/on/margin/basis/staff/home.
  Measured LOCALLY: the five lines re-found within +-3 spaces of the dot's x (`measure_extractor._find_five_lines`) against
  the nearest staff; the bar grid as a stated fallback. Abstains `off_staff` (margin, side) or `no_staff_geometry`.
  Brahms pp.0-1: 195 of 207 dots filed, 194 from local ink.
* `staged.check` 193 -> 192 (diffed vs origin/main): only `staged.capture` moves (19 -> 18); KNOWN_GAPS `POSITION dot`
  closed because `dot_role` and `duration` now read the fact.
* Join behind `OMR_DOT_POSITION_JOIN` (default OFF): a dot on the wrong step is not that head's augmentation dot; a dot at
  exactly one head's dot step that the old box window missed is placed on that head (the old window admits only the dot
  ABOVE, so it misses below-line dots).

## Truth, Brahms p0, 131 dots, flag OFF -> ON
| | OFF | ON |
|---|--:|--:|
| dot on the right head | 106 | 110 |
| dot on another head | 17 | 18 |
| unplaced | 7 | 2 |
| non-truth boxes decided augmentation | 4 | 4 |
10 dot-role verdicts change on Brahms pp.0-1 (9 admitted, 1 vetoed); all 10 crops viewed: the 9 admitted dots sit beside
the note they were given to; the veto is a mark above the upper head of a second (not an augmentation dot).
Litolff pp.0-3: 0 changes (its truth page has no staccatos, so wrongly joined staccatos cannot be scored there).

## Tests
`tools/omr/tests/test_staged_dot_position_2_128.py`, 28 tests, RED first (stubbing the line finder or the flag turns 7
red). Fast tier 7954 passed, 11 skipped, 2 xfailed. `judged score` not run.

## Open
* The join does not compare a dot against heads owned by another staff (2.127's staccatos called augmentation).
* Heads more than 4 steps off the staff are unknown.
* Tiles for Sean: `out/print/2.128-review/dots-position-review.png` (12; hidden `_hidden/manifest.json`).
