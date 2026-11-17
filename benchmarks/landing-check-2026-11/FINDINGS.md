# Landing check: did 2.305 / 2.306 r14 make Litolff refuse more note values? (ROADMAP 2.313) -- 2026-11-17

STAGED. Written by the manager from the lane's report (branch `lane-2.313-litolff-refusals`, 65d9863cf).

## Cause and process lesson

The 162 -> 191 was not real. `lane_report --from gather` and `one_test` gathered the frozen sample pages WITHOUT
Litolff page 1, and Litolff prints its staff names, meter and key on page 1 only. Without it the meter is
abstained, every head is `staff_not_identified`, there are 0 red bars, and notes narrowed to {eighth, quarter}
stay refused. Lesson: read a record's provenance (tree, flags, stages, pages) before comparing two runs.

The two records compared by the 2.311 beam small test were not a like-for-like pair: `lit-a` was gathered on
16b4537e6 (before both landings) with pages 1, 2, 4, 6, 8, 9, 10, 11, 16; `lr/work` on 7d45333aa (no r14 rules),
arc flags forced off, no page 1. Both counts were all refused heads, not red-bar-filtered.

## Four arms, like with like (Litolff p1, p11, p16; today's main; flags only; r14 OFF = its two commits reverse-applied)

- Red bars 58 and refused heads 30 (27 in red bars) in ALL four arms; identical to old `lit-a` on the same pages.
- Arcs ON: ties +6 -10, slurs +19 -43; nothing else changed. r14: nothing changed on these pages.
- Brahms p0: arcs ties +8 -4, slurs +5 -61; r14 flags +16, beams -17, red bars 4 -> 3, one note eighth -> quarter
  in a bar that then adds up.
- Judged right -> wrong: 0 on both plates (Litolff 185 tiles, Brahms p0 202).
- Control: the re-adjudicated arm equals the product run.

## Fix (tool only)

`lane_report` and `one_test` now pass `loaded_pages` to `gather_one`, so a sample gather carries the pages that
hold the names, meter and key. Counting unchanged. New test fails on the old line.

## Not done

The full 191 was not re-created (p11 matches exactly; p16 by the same mechanism). The 17 notes refused only
without page 1 were not crop-checked. Only Brahms p0 was re-run on Brahms.
