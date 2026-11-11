# 2.280 r3 — Stems re-run on today's main (2026-11-10)

STAGED, measure only. Branch `lane-2.280-r3` 9a964a9fb. Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Cause and process lesson
Nothing that feeds the stem finder has moved since 11-08: no commit touches `line_detection.py`, `stem_value.py`,
`geometry.py` or `rhythm.py`, and a fresh gather gives the same stem rows head for head. 2.277 / 2.284 / 2.285 claim
ink; none feeds the finder or the head-to-stem join. And the premise was unsized: only 3.8-4.7% of read heads are
UNCERTAIN for value. Lesson: size the reasons a note is not plain against each other (the 2.286 account) before a lane
opens on one of them.
**Limit of that figure (found the same day by 2.291 + Sean's tiles):** it counts uncertain values only. A value
decided WRONG and written plain (a flagged eighth written as a quarter; a chord counted twice) is not in it and shows
up as a red bar.

## Counts
Real heads with no stem row: 4.2% Litolff p1-2, 3.4% Brahms p0,14 — every one `adjudicate_head_stem` abstaining
`no_stem`; on Brahms nearly all are heads of a second or chord whose stem is on the partner. Sean's Brahms p0 stem
labels confirm all 11 such heads. Of value-uncertain heads, first failure: no stem row 26-43%; stem but no beam/flag
read 19-30%; beam read, not bound 3-18%; value known, refused by chord/bar 10-36%.

## Proposed (neither built; ~1.5-2% of heads each)
1. The stem of a second or clump, read from the head pair (retires `OMR_HEAD_STEM_BRIDGE`, the contested-only
`Q.HEAD_STEM_REACH`; failed the 2.280 micro twice before 2.285 removed sharps-as-heads).
2. One page beam group owns its stems; a tip under an arc counts as clean (extends `OMR_PAGE_BEAMS` M4a into M4b).

## Sean's tiles
12 made (seed 2803), NOT sent, unanswered.
