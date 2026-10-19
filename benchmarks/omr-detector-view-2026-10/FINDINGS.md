# Detector views -- FINDINGS (ROADMAP 2.172)

STAGED GATHER. Flag `OMR_DETECTOR_VIEWS` (default OFF; sub-switches `_PARTS` = `views,aa,phase`, `_PHASES` = 3, `_WHICH` = `small,close`). Code: `tools/omr/staged/detector_views.py`, `YoloDetector.detect_view`, `gather.gather_detector_views`, reader `READERS.DETECTOR_VIEW`; tests `tools/omr/tests/test_staged_detector_views_2_172.py`. Probes `probe/2.172/` (`v1_bars` + `v2_analyse` on the 2.167d bars, `g1_regather.sh` / `g2_small.sh`, `c1_compare` OFF vs ON, `c2_sheet` my lookback sheets, `j1-j3` judged diff, `t1_tiles`). Weights: the routed production file `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`.

**CONVENTION ASSUMED:** a dot, flag or rest is better read from a SMALLER view than a notehead, and a welded black head from a LARGER one (2.171, two plates, one weights file). Sean's principle (2026-10-19): big picture first, look closer where it is crowded. **WHAT WOULD FALSIFY IT:** Sean's blind tiles (12 in `out/print/2.172-review/`, unanswered) showing that most of a view's new boxes are not the symbol of the family they were taken for; my own lookback sheets already falsify it for the `close` view (below). **NOT CONFIRMED:** the sizes 8 px and 22 px are measurements on Litolff and Brahms and may only NARROW (add a candidate behind every existing gate); every "real" count below is MY look at crops (`out/print/2.172-lookback/`), ours, not evidence (rule 7). "Closer view per cell keyed to local crowding" is NOT built: any crowding cut would be fitted on our two plates.

## What was built
1. **Per-family view.** Besides the untouched production view (16 px staff space), the same model sees each cell at EXACTLY 8 px (`small`: dots, flags, rests; anti-aliased) and 22 px (`close`: black heads). The resize ratio is `staff_space / canonical space`, no `round32` of a per-crop `imgsz` (2.171 section 10, item 1). Only the families a view is for are taken.
2. **Anti-aliased down-sample** (`cv2.INTER_AREA`) for the small view; the close view keeps the bilinear resize.
3. **Phase median.** Each view is read at 3 sub-pixel phases of the network grid (one batch, one forward pass); a box is kept where the MEDIAN confidence over phases (a phase with no box = 0) clears the production floor 0.25; the recorded score is that median.
4. **Family-aware merge.** A view box is dropped where a production box of the SAME family stands on it, or a production box of another family stands there with confidence >= its own, or another view's stronger box does. Production boxes are never moved, changed or dropped. Kept boxes are appended to the cell's `detections` (the rescue's pattern) under `READERS.DETECTOR_VIEW` with view, size, phases found and per-phase confs, and then meet every ADJUDICATE gate like any glyph; refused near-misses (`production_stronger`, `view_stronger`) are filed as abstentions.

## Controls
- **(a) OFF = production.** The production call reproduces the 20261018-night record's detector boxes on the 2.167d bars: Litolff 433 of 433, Brahms 859 of 859 (class, conf within 0.01, IoU > 0.8). It can fail: with `imgsz` + 32 it reproduces 5 of 83 (first 10 Litolff bars). OFF is byte-identical by construction (one gated call in `gather()`; flag unset runs nothing else); I did not diff an OFF record against a pre-change record.
- **(c) Kept symbols dropped = 0**, checked on the re-gathered records, not only by construction: every production (reader `detector`) glyph box of the OFF record is in the ON records with the same class, box and score: Litolff 9,819 of 9,819, Brahms 12,892 of 12,892, in every arm. The 44 + 80 kept subjects of 2.171 are each still carried by an untouched production box.

## Cost
- Detector call, 90 bars: production 3.3 s (Litolff) / 4.2 s (Brahms); views add 15.4 / 23.1 s -> **5.7x / 6.5x** the detector call with both views x 3 phases (one phase = 3.0x; no phase and no aa = 2.9x). Phases are batched, so 3 phases cost about 2x one phase.
- Whole small re-gather incl. export (5 Litolff pages 1-5 / 4 Brahms pages 0-3, wall, machine shared with two replay lanes): OFF 673 s / 1365 s; ON both views 1190 s / 1792 s (**1.77x / 1.31x**; 238 / 448 s per page); ON `small` view only 792 s / 1455 s (**1.18x / 1.07x**; 158 / 364 s per page). A whole movement stays overnight (OFF: 32 min for 16 Litolff pages).

## (b) The lost symbols (2.167d/2.171 A/B/C items located: Litolff 17, Brahms 20; same bars, product code, `probe/2.172/data/analysis.txt`)
Found = a KEPT view box of the wanted family on the symbol (IoU > 0.3, or x-near for a never-boxed region), after the merge.

| arm | Litolff | Brahms |
|---|---|---|
| full (both views, aa, 3 phases) | 6 of 17: black head 4 of 9, rest 2 of 7, flag 0 of 1 | 7 of 20: dot 2 of 8, flag 3 of 9, rest 2 of 3 |
| no aa | 5 | 8 |
| one phase | 6 | 8 |
| bare (no aa, one phase) | 5 | 7 |
| by cause (full) | A 0/2, B 4/7, C 2/8 | A 1/3, B 4/14, C 2/3 |

The `small` view alone is all of Brahms' 7 and Litolff's rests 2 of 7 (the 4 heads are the close view). Refused by the merge although a view saw it: 5 (Litolff) and 5 (Brahms) lost symbols, all `production_stronger` (production boxed the ink in another class with at least that confidence: the "head called a rest" case). For comparison 2.171's single-run lifts at 16 px were 13 of 17 Brahms at x0.5 and 8 of 9 Litolff heads at x1.4; this lane finds fewer because the median asks 2 of 3 phases, the merge refuses ink production already boxed, and the match is on the final box. The 2.167d double-width pass found 16 of 36; this finds 13 of 37 with fewer new boxes (21 / 56 new boxes on the 45 + 45 bars against 33 / 25 for the wide pass). Small n; read as a direction. Of the new boxes only 6 (Litolff) and 7 (Brahms) sit on a located lost symbol; the rest are new and judged below.

## (d) New boxes and how many are real (MY look, `out/print/2.172-lookback/`, random samples from the re-gathered pages, NOT blind, NOT evidence)
New view boxes in the ON arm: Litolff 388 (close head 337, small rest 32, flag 11, dot 8), Brahms 354 (close head 242, small flag 37, rest 39, dot 36).

| view / family | Litolff real | Brahms real |
|---|---|---|
| small / rest | about 10 of 12 (quarter and whole/half rests) | about 11 of 12 (8th, quarter, whole rests) |
| small / flag | about 3 of 11 (beam ends, slivers) | about 11 of 12 |
| small / dot | 0 of 8 (4 px dots; dots of "cresc." and other ink) | about 7 of 12 (the rest are repeat-sign dots and letter dots) |
| close / black head | about 6 of 15 (the rest: barline and stem slivers, a quarter rest called a head) | about 1 of 12 (clef parts, barline slivers) |

**On clean bars:** the new boxes land in 299 (Litolff) and 193 (Brahms) bars of the re-gathered pages, mostly bars the OFF file did not hold out (the close view alone puts a box in nearly every Litolff bar); the false ones there are the barline/stem slivers above. Clean bars were not separately sampled; the table is the sample.

## (e)(f) Re-gathered pages and the exported file (flag OFF vs ON, one run at a time; Litolff pdf pages 1-5, Brahms 0-3; run through the whole pipeline with `--musicxml`, the record carries GATHER + ADJUDICATE)
| | notes in file | rests | unread bars | held-out bars | red-marked bars | unboxed rests placed (CV) | duration-narrowed notes the file lacks |
|---|--:|--:|--:|--:|--:|--:|--:|
| Litolff OFF | 1655 | 837 | 169 | 146 | 362 | 47 | none listed |
| Litolff ON full | 1790 (+135) | 855 | 152 | 127 | 325 | 27 | none listed |
| Litolff ON small only | 1668 (+13) | 856 (+19) | 162 | 140 | 349 | not read | none listed |
| Brahms OFF | 1554 | 614 | 33 | 103 | 185 | 22 | 138 |
| Brahms ON full | 1582 (+28) | 627 | 29 | 96 | 173 | 3 | 133 |
| Brahms ON small only | 1581 (+27) | 626 (+12) | 30 | 95 | 170 | not read | not read |

**Reading it.** The small view carries the lane's value: Litolff +19 rests and held bars 146 -> 140; Brahms +27 notes and +12 rests, held 103 -> 95 (flags and dots lift held notes; the CV unboxed-rest placements fall from 22 to 3 because the detector now boxes those rests itself). The close view adds +122 Litolff "notes", well under half real heads by my look, and turns at least one real quarter rest into a quarter NOTE (Litolff 2/0/6/3, Sean's `2.99-review` tile 12: a `noteheadBlackOnLine` 0.46 view box lies on the rest's ink and the CV unboxed-rest reading stands down as "already read as a glyph"): a guess written over a correct reading. **The `close` view should not ship on these two plates.** The `small` view is the candidate, by family: rests on both plates, flags and dots on Brahms only.

Sean's judged tiles on these pages (`python3 -m tools.omr.staged.judged score`; right / wrong / narrowed / abstained): Litolff OFF 72 / 14 / 3 / 1, ON full 71 / 17 / 3 / 4, ON small 70 / 16 / 3 / 1; Brahms OFF 74 / 9 / 5 / 0, ON full 71 / 12 / 5 / 0, ON small 71 / 12 / 5 / 0. Every changed item is a rest Sean judged ("4 rest" / "8 rest"): 6 in the full arm, 5 in the small arm. I traced each (`probe/2.172/j3_moved.py`, `j2_why.py`). In the small arm all 5 are the same rest now carried by a new view box with the rest class and the same duration (view `restQuarter` / `rest8th`, IoU 0.86-0.92 with the old unboxed-rest subject, duration decided 1.0 / 0.5): the scorer matches by glyph key (its own docstring), so the moved subject reads "wrong". A keying artifact, not a changed reading. In the full arm 4 of 6 are that; the 2 true regressions are the close view's (Litolff 2/0/6/3 above, and 1/0/7/0 where a head box over part of an eighth rest makes the CV reading abstain).

## Not done / caveats
- Sean's 12 blind tiles are unanswered (`out/print/2.172-review/`; the key, `probe/2.172/data/tiles_key.json`, is not with the tiles; tiles and key came from one run and `t1_tiles.py --check` verifies names and sha256). Every "real" count above is my look. The blank control sits on a barline edge in a staff gap (answer: barline / nothing).
- No default flips; no per-plate switch. The size per family was fitted on two plates and one weights file.
- The close view's false boxes (barline and stem slivers, a rest called a head) pass the adjudicators; refusing them is a different lane's gate. The small view's false dots (letters of "cresc.", repeat dots) likewise.
- The judged scorer keys by glyph index; a view box that duplicates a CV reading moves the verdict to a new glyph. A lane that lands the small view should re-key the scorer by box overlap before reading judged numbers.
