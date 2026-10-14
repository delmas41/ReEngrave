# 2.116 -- STAGED LilyPond export raised `Unbalanced` on the 20261013-night records

Path: STAGED (`tools/omr/staged/lilypond.py::to_lilypond`). LEGACY untouched.

## Cause
`staged.export.to_musicxml`'s accounting equality is
`events_in_log + unboxed_rests_placed == written + dropped` (ROADMAP 2.99 added the
first extra term: a rest read off unboxed ink is written, but no detector row
announced it). The LilyPond twin kept the old `events_in_log == written + dropped`.
Any record holding a decided unboxed rest therefore over-accounted and raised.
Introduced by `8b69501f` (WIP 2.99; after cb73dde2, ancestor of ca46eae4).
It was not 2.103/2.107/2.97/2.102/2.105 and not a dropped note: nothing was dropped
silently, the equality's left side was missing a term. `20261011-night` records predate
the 2.99 gather (no unboxed rests), so they balance.

## Record vs code (no gather; `nice -n 10`, tree ca46eae4 worktree, read only)
- 20261011-night record, CURRENT exporter: `to_lilypond` balanced (14272 = 7385 + 6887).
  So the CODE is not what changed -- the new RECORD carries the new fact.
- 20261013-night record, ca46eae4: Litolff `14272 in log, 8059 written, 6338 dropped`
  = 14397, over by 125; Brahms `32389, 13818, 19021` = 32839, over by 450.
- After the fix `balance.unboxed_rests_placed` = 125 and 450 (the exact overshoot):
  Litolff 14272+125 = 8059+6338; Brahms 32389+450 = 13818+19021. A bisect was not
  needed: the mechanism is proven by the 20261011 record exporting and the overshoot
  equalling the unboxed count.

## Fix
`lilypond.to_lilypond`: read `provenance["unboxed_rests_placed"]` (the same field
`to_musicxml` reads), add it to the log side, report it in `balance`.
Nothing suppressed; the unboxed rests are written (`r8`, see test).

## Tests
- RED-first fragment: `test_staged_unboxed_rest_2_99.py::...test_the_lilypond_twin_balances_with_an_unboxed_rest_RED`
  (failed `2 in the log, 3 written, 0 dropped`; passes; control without the rest passes).
- Whole movement (slow, machine-local, skips if absent): `test_staged_lilypond_whole_movement_2_116.py`
  both overnight records balanced with exactly 125 / 450; Litolff compiled by `lilypond`.

## Result, 20261013-night records, fixed exporter (`python3 -m tools.omr.staged.lilypond REC --out X.ly`)
| movement | in log | written | not written | unboxed placed | guessed (blue) | PDF |
|---|---|---|---|---|---|---|
| beethoven5-litolff | 14272 | 8059 | 6338 | 125 | 1492 | 48 pages, 0 compile errors, 27 warnings |
| brahms1-breitkopf | 32389 | 13818 | 19021 | 450 | 948 | 17 pages, 0 compile errors, 419 warnings |

Time: Litolff .ly 18 s + lilypond 38 s; Brahms .ly ~60 s + lilypond 21 s.
Pages for Sean: `out/print/2.116-lily-export/` (Litolff p8, Brahms p12).
Legend: BLUE = GUESSED symbol (written AND flagged, 2.103); RED rest with "unread" =
a bar the reader could not read, nothing invented; black = READ.

Fast tier: `pytest -m "not slow" tools/omr/tests -q` = 7771 passed, 11 skipped, 2 xfailed.
Slow whole-movement file: 3 passed (115 s).
