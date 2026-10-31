# ROADMAP 2.244 -- one test command (test tooling; no reading or output changed)

2026-10-30, branch `lane-2.244-one-test-command` (3b10107f1). Written by the manager from the lane's report (the lane's write here was refused by the hook).

## Cause and process lesson
Three lane-measuring steps rested on memory or luck: the sample `--tag` (a lane had to remember it; the default was 20261020-night), a glyph id (one gather's detector order, which drifts), and Sean having already looked at the place (changed places he never judged were invisible). Lesson: anything a lane must remember to make a comparison fair belongs in the tool, and the tool refuses when it cannot make it fair.

## Built
1. `lane_report.DEFAULT_TAG = 20261029-night` (`sample.json` record_tag too; pages and seed not re-drawn, `retagged` note); a tag with no record and no slice dir raises (`check_tag`).
2. `judged.score(..., by="place")` default: a tile with a `position` is found by (page, system, staff, cell) + an overlapping glyph box of the same kind; id only a tie-break; no mark at the place = `not_found`, never a key fall-back; tiles without a position keep the key and are counted apart. `--by key` is the old rule. `judged build --check` current at 1,997.
3. Unjudged changed places: listed per plate by kind (report + `DIR/unjudged.txt`); a tile covers a change only on the same page, overlapping box, same cell, and a question about that kind. `--unjudged-tiles N` (<= 12) cuts blind tiles with the existing cutter.
4. `python3 -m tools.omr.staged.one_test --flag A --flag B ... --out DIR`: arms base / only-FLAG / all on one tree, stages, cells, detector cache and OCR; three measures per arm, INTERACTIONS (all vs the union of singles), one blind sheet; a CONTROL line, any mismatch raises `ArmMismatch`; `--reuse` re-checks arms on disk.

## Measured
- Place vs id key, Litolff 20261029-night, 394 old tiles (none stored a `position`; tiles with a mark-sized page box were given the position their own key names): 146 scored by place (2 at another id), 247 stayed on the key (old galleries stored the 200-300 px tile window as page_box), 1 no mark. Right/wrong key 169/34, place 169/33; right->wrong 0. Three differences, each by place: 2.181-review tile 12 id drift (unscored both); 2.181-review tile 9 key pointed at a notehead, by place the rest (no comparator) -> not_found; 2.170-review tile 7 cell moved ~148 px -> not_found.
- Combined command, small real run (OMR_WHOLE_REST_PLAIN, OMR_RELOCATE_AT_EXPORT; Litolff p2, `--from adjudicate`, a development sample): one CONTROL line, 4 arms, judged right->wrong 0 every arm, interactions 0, 19 min on a loaded box. A saved arm edited to stage `gather` -> REFUSED with every control line.
- Controls (36 unit tests): planted id swap scored wrong by key, right by place; positioned tile with no mark -> not_found; stale tag raises; planted mismatch in stage/tree/cells/tag/pages/cache/OCR/record/plate refused.

## Open
No committed tile has a position yet (place matching matters from 2.231+ galleries); old galleries cannot be place-matched; combined run not yet exercised `--from gather`, `--cell-map master` or on Brahms; it needs the lanes merged into one tree (control line refuses mixed trees); changes with no page box (words, some dynamics) are neither listed nor tiled.
