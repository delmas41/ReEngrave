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

## Truth, Brahms p0, 131 dots, flag OFF -> ON (after the tile-1 fix, section below)
| | OFF | ON |
|---|--:|--:|
| dot on the right head | 106 | 111 |
| dot on another head | 17 | 18 |
| unplaced | 7 | 1 |
| non-truth boxes decided augmentation | 4 | 4 |
9 dot-role verdicts change on Brahms pp.0-1, ALL admissions, none vetoed; the crops of the 9 sit beside the note they were given to.
Litolff pp.0-3: 0 changes (its truth page has no staccatos, so wrongly joined staccatos cannot be scored there).

## Sean's tiles (2026-10-14: "3. No all the rest yes", then "1 is a dotted 4") -- `out/print/2.128-review/answers.json`
All 9 ADMITTED tiles truly dotted; controls right (3 plain: no; 9 dotted: yes). **Tile 1, the VETOED one, is a dotted quarter.**
* What happened (Brahms `glyph/0/0/3/1/6`, a dot above-right of the top-line head `.../1`, step -0.04, in a chord of seconds
  whose lower head has its own dot `.../8`): the dot was measured at step -1.69, i.e. 0.31 steps below the ledger line above
  its head -- IN the space above it -- and the first cut rounded it to the line at -2, margin 0.19 over the 0.1 floor, and
  vetoed it. With the flag OFF it is decided augmentation naming `.../1`, whose duration is narrowed {dotted 8th/quarter}
  (`beam_discounted_uncertain`). With the first cut ON the dot became unplaced and the head's narrowing lost its dotted
  candidates to {plain, plain x2} then {plain + dotted} from 2.127's reconcile: a real dot written plain-or-unknown.
* Fix (`aug_dot_join._dot_cell`, `DOT_LINE_BAND` 0.2 / `DOT_SPACE_BAND` 0.3): a space is the interval between two line
  centres; a dot is ON a line only within 0.2 steps of a line centre, IN a space beyond 0.3, and unclear between (unknown,
  never a veto, never an admission). Across the 120 truth dots the nearest to a line centre is this one, at 0.31; detected
  dot-class boxes lie as close as 0.004, so the veto still has teeth. RED test `TestTile1AReadingNearTheLineIsNotAVeto`
  from tile 1's real numbers; a control that a reading at 0.1 off the line still vetoes.
* The convention: Sean, 2026-10-14, **"Always in a space"** -- CONFIRMED (general scope), registered in
  `docs/engraving-conventions.md` and `docs/page-facts.md`. Above vs below a line note: Sean ruled "Yes" to the researched rule
  (above by default; below for the lower stems-down voice of two or the lower note of a second; PROVISIONAL for 19th-c.
  German plates). The registry's old "NEVER below" is replaced.
* Check of the rule on Brahms p.0 (61 line-note dots, Sean's labels; stem direction and chord membership from the record):
  41 above; the 19 first counted "below" split into 15 where ANOTHER head of the same chord column takes the dot at its
  standard place (the dot lies between a chord's two heads: the space above the lower one -- the nearest-head truth rule
  gave it to the upper) and 4 on single stems-down heads in a two-voice cell (`0/0/11/0/4`, `/0/9`, `/2/2`, `/5/8`: the lower
  voice, exactly the four the join admitted, all dotted per Sean). **0 single-voice single notes with a dot below: no
  contradictions, so no `below-contradictions.png`; the rule is confirmed on Brahms.**
* `DOT_BELOW_NOTE_MAX_SPACES = 0.25` is unchanged: the join places the four lower-voice dots by position (the flag), and
  moving the box window would change the default path.

## Tests
`tools/omr/tests/test_staged_dot_position_2_128.py`, 32 tests, RED first (stubbing the line finder or the flag turns 7
red). Fast tier 7954 passed, 11 skipped, 2 xfailed. `judged score` not run.

## Open
* The join does not compare a dot against heads owned by another staff (2.127's staccatos called augmentation).
* Heads more than 4 steps off the staff are unknown.
* Tiles for Sean: `out/print/2.128-review/dots-position-review.png` (12; hidden `_hidden/manifest.json`).
