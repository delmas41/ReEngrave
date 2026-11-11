# 2.286 — Note conservation, in minutes, on real pages (2026-11-10)

STAGED, EXPORT report only. Branch `lane-2.286-note-conservation` 823119fd4. No reader, verdict or flag changed.
Written by the manager from the lane report (the lane's Write tool was refused).

## Cause and process lesson

`export.to_musicxml` already raised `Unbalanced` when its counts disagreed, but only unit tests on one-staff fixtures
ever ran that balance. Nothing ran it on a real page, so three gaps went unseen: a head inside a red bar counted as
written and could not be located; an empty or unnamed reason would have passed; ink never boxed is outside the
balance by construction. Lesson: an invariant that is only ever run on constructed input has not been run.

## Command, input, time

    python3 -m tools.omr.staged.conservation [--plates] [--pages] [--ink] [--save DIR]

Reads the saved GATHER rows of the lane-report slices (`lane-report-slices-20261029-night`) and replays ADJUDICATE
through EXPORT on the tree's defaults. No detector, no OCR, never opens the whole-movement verdict file. Default
pages: Litolff 1,2 and Brahms 0,4. Run time: Litolff 33 s, Brahms 74 s (1:54 both; 3:07 with `--ink`).

## Result on main's defaults (2026-11-10, 2.284 ON)

Litolff 1,2 — read by ADJUDICATE 1264 (26 rests read off unboxed ink); written plain 712; written GUESSED (blue) 180;
inside red bars 71 (24 bars); inside a partial-bar gap 1; held bar 0; not written, named reasons, largest first:
88 `owned_by_another_staff`, 29 `clipped_fragment`, 25 `mark_group_duplicate`, 18 `duration_narrowed`, ...;
unaccounted 0 — invariant HOLDS. Ink never boxed: 905,632 of 2,845,326 px (31.8%) in `claim_readout`'s
unclaimed/debris bucket (ink, not a note count).

Brahms 0,4 — read 1970 (1 rest off unboxed ink); written plain 1292; GUESSED 93; inside red bars 72 (19 bars);
partial-bar gap 7 (4 bars); held bar 0; not written: 162 `owned_by_another_staff`, 99 `claimed_by:barline`,
32 `rest_clipped_by_crop`, 31 `duration_narrowed`, ...; unaccounted 0 — invariant HOLDS. Ink never boxed:
6,299,226 of 11,243,312 px (56.0%).

Every red, gap and held bar is located by (page, system, cell). Most "not written" rows are rejected boxes, not
lost notes; whether `owned_by_another_staff` (88 / 162) or `claimed_by:barline` (99) hides real notes needs a crop
look — this count cannot say.

## Controls (each fails where it must)

A head dropped with no reason raises `Unbalanced`; a head removed from the written count fails; an unnamed reason
fails; a held bar's heads miscounted as written (totals still balancing) fails the bar-vs-reason cross-check; a
red-bar head that cannot be located fails; on the real Litolff report, doctoring one lost head and one un-located
red bar each fail. 9 fast-tier tests + the slow real-page file.

## Byte-identical export

MusicXML saved with `--save` from the branch vs the same replay from a `git archive origin/main` tree: `cmp`
identical on both plates (Litolff 352,197 bytes, Brahms 456,439 bytes). Fast tier 10121 passed, 0 failed.
`check` TOTAL 229 (= main).

## Red-bar notes: Sean's ruling (2026-11-10)

"Keep reporting - My long-term goal is to get to a point where we're just fixing a few notes." Notes inside red bars are
reported on their own line, never folded into "written" or "lost" (DECISIONS 2026-11-10). The earlier assumption
("a red-bar head is written") is withdrawn as a headline; the three lines to read are plain, blue, and in red bars.

## Not verified

Only 2 pages per plate, on the 20261029-night slices (a saved gather: a GATHER change is not visible here).
