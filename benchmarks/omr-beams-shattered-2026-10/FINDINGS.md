# ROADMAP 2.170 -- beams on the shattering plate (STAGED GATHER+ADJUDICATE; flag `OMR_BEAM_REFUSED_OFF_THE_TIP`, default OFF)

Records: 20261018-night (main 2bb43b85, through infer). Code: this branch off main 7f668d66. Probes: `probe/`.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED

1. **A beam joins every stem it spans AT THE STEM'S END** (Gould, *Behind Bars*, "Beams"; omr-beam-confirm-2026-10 §9.2; Sean
   2026-10-16 "the stem tip decides beamed or not", 2.146 tiles 33/33 + hand truth 41/41). So a stroke that stands nowhere near
   a note's own stem end is not that note's beam, whatever else it is (slur, hairpin, staff line, a neighbour's beam).
   **Falsified by** a note the rule decides unbeamed that Sean reads as beamed (a tile below), or a beam whose ink reaches the stem
   while no stroke row of either reader stands at the tip (the readers' fault, but the rule would then write it wrong).
2. **A note with no beam and no flag at its stem is its head's value** -- the pipeline already reads every unmarked head this way
   (`head_and_marks`), with the flag window as the only guard. This lane makes a head whose every nearby stroke was REFUSED go
   the same way. **Falsified by** a changed note carrying a flag the detector never boxed and the tip window could not read.
   **NOT CONFIRMED** for this population: the 2.146 rule demanded the flag window read clean; here it is unread. Tiles below.
3. The two zone sizes (stem x +- 0.3 space, tip +- 0.6 space) are 2.81's (`BARE_STEM_ACROSS_SPACES`, `BARE_STEM_TIP_SPACES`),
   set before this lane and not refitted. They only NARROW what the rule may touch (a stroke inside the zone keeps the narrowing).

## 1. Brief from the tree (rule 1)

* 2.38 (`Q.BEAM_STEM_JOIN`, the stem-to-beam ink join) and 2.38b/c: merged. 2.146: research + `OMR_STEM_TIP_DECIDES_BEAM` ON
  (clean tip = run reader no run + flag window clean -> no beam; "a beam at the tip" branch REMOVED after tile 13).
  2.153 `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` parked OFF. 2.155 `OMR_STEM_AT_BAR_EDGE` ON (a stem refused at the cell edge).
  2.169 `OMR_STEM_PAIR_AT_HEAD` ON (in these records). 2.121 §1: on Brahms p0, 51 of 52 `beam_discounted_uncertain` were BARE
  stems beside a refused slur/tie box. 2.146 §9.5: of 81 still narrowed, 48 had no own CV stem, 26 had the flag window unread.
* Refuted/withdrawn: the "a beam run at the tip decides n levels" branch (2.146 tile 13). Nothing on "shattered" beams was built.

## 2. The causes, counted (20261018-night; `extract_2_170.py`, `cells_2_170.py`, `causes_2_170.py`, `tips_2_170.py`)

Population: every first `adjudicate_duration` verdict NARROWED `beam_discounted_uncertain` or `beams_ambiguous`
(Litolff 455 + 93 = 548; Brahms 2,250 + 143 = 2,393). Standing after EVALUATE/INFER: still narrowed Litolff 361, Brahms 1,850.
First cause per head, from the cell's own rows (own stem = a CV stem box overlapping the head box; "beam ink at the tip" = a
stroke whose ink row reads >= 1.75 lines thick, covering the stem's x, within 0.5 space of its far end):

| cause | Litolff | Brahms | what my eyes saw (ours, not evidence) |
|---|--:|--:|---|
| (d) **no beam ink at the stem tip** -- the refused strokes are slurs, hairpins, staff lines, text or a neighbour's beam, and the note is unbeamed | **279** | **1,319** | Brahms 16 sampled: 14 unbeamed quarters / dotted quarters / chord members, 1 a bass clef boxed as heads, 1 a tremolo chord; Litolff 7 sampled: 6 quarters, 1 unclear (possible flag) |
| (b) no own CV stem found | 191 | 933 | Brahms 11 sampled: **9 not notes** (slivers boxed at barlines, a rest), 2 real; Litolff mixed |
| (c) beam ink at the tip counted, but left a range / refused (`not_straight`, `no_stem_at_ends`, arc ...) | 68 | 124 | Brahms 3 sampled: all real beams (2 refused `not_straight` on a sloped beam fused with a slur; 1 sixteenths) |
| (a) **shattered**: the only beam ink at the tip is a detector box `_kept_beams` dropped for a shorter CV piece, or a CV piece stopping short of the stem | 10 | 17 | Brahms 1, Litolff 1 sampled: both real eighths |

Why the 2.146 rule did not decide the (d) heads: the tip's beam-run reader read NO run on almost all of them (Brahms ~1,150 of
1,309), but the FLAG window abstained: `ink_not_flag_shaped` 336, `head_at_this_end` 266, `crosses_both_sides` 176, `runs_on` 163,
`occupied` 74 (Brahms; Litolff the same order). A slur or hairpin crossing near the tip is exactly what makes that window say
"cannot tell". So on both plates the narrowing is not a beam the reader cannot tie to a stem: it is an unbeamed note held
narrowed by strokes it correctly refused. The shattered beam the brief named is real but small (27 heads over both plates).

**The fix targets (d)**, the biggest real-note cause. (b) is mostly not notes and is left alone (deciding them would write
non-notes); (a) is guarded, not fixed: the rule's zone test sees the dropped detector box at the tip and keeps the narrowing.

## 3. The fix (STAGED ADJUDICATE, `rhythm.adjudicate_duration`; flag `OMR_BEAM_REFUSED_OFF_THE_TIP`, default OFF)

Functions changed, all inside the lane's fence (the `beam_discounted_uncertain` branch): new `beam_refused_off_the_tip_enabled`,
new `_no_beam_at_the_stem_tip`, and one guard in front of the `beam_discounted_uncertain` narrowing. No GATHER change; nothing in
`reconcile_duration`, `bar_length.py`, the bar-sum/INFER solvers or EXPORT was touched (2.165's fence).

Same population as 2.146 (every stroke over a stemmed head refused; no flag box; not hollow; no hook at the tip). The narrowing
is skipped -- the head then goes through the rest of `adjudicate_duration` exactly as an unmarked head does (the flag window,
the head-fill readers, the head's own value) -- only when ALL hold:
* the tip's own beam-run reader (`Q.BEAM_STEM_LEVELS`, 2.140) READ the tip and found no run on either side;
* the flag window at the tip filed no observation and only `ink_not_flag_shaped` abstentions (the one cannot-tell that also says
  no ink runs off the tip: a beam leaving right reads `runs_on`, left or both ways `crosses_both_sides`, a box `occupied`);
* no `Q.BEAM_STROKE` box of EITHER reader -- kept, refused, or a detector box `_kept_beams` dropped for a CV piece -- stands at
  EITHER end of the stem (2.81's zone). This is what keeps the shattered beams (cause a) narrowed.

**Round 1 (built without the last two clauses' strictness: any flag-window reason, the side's tip only) was WRONG on Litolff**
(whole-record replay, `out/compare_litolff_r1_first_build.txt`): 126 heads touched, 75 values changed, and my look at the 17
in newly held bars / decided moves found beamed eighths decided as quarters -- p2 sys1 st5 c13 g0/g4 (a short beam between two
close stems that no stroke row of either reader holds and the run reader's 1.6-space reach misses: the window read `runs_on`
/ `head_at_this_end`), p6 sys0 st2 c8 g1 (a chord head mid-stem read 'up' while its beam stood at the bottom). Both clauses were
added for those; tests pin each (11 tests; mutations: zone test removed -> the dropped-box control fails; one end only -> the
head-end control fails; any reason accepted -> the `runs_on`/`no row` controls fail).

## 4. Measured ON THE EXPORTED FILE (whole-record replay through ADJUDICATE..INFER..EXPORT, `replay_2_170.py`, adapted from 2.165's)

Control: the OFF arm reproduces the stored night verdicts exactly -- Litolff first `adjudicate_duration` 0 of 14,272 differ, live
(outcome, written) 0 of 14,404; Brahms p0-8 0 of 10,545 / 0 of 10,634.

| | Litolff (whole movement) OFF -> ON | Brahms pages 0-8 (contiguous from the movement start) OFF -> ON |
|---|---|---|
| notes written in the file (`written.notes`) | 6,626 -> **6,639** (+13) | 3,543 -> **3,591** (+48) |
| `<note>` elements in the MusicXML | 9,143 -> 9,156 | 5,626 -> 5,675 |
| narrowed live duration verdicts (non-rest) | 528 -> 511 | 774 -> 730 |
| not written as `duration_narrowed` | 259 -> 243 | 374 -> 331 |
| bars held out (sum does not add up) | 564 -> 567 (0 released, 3 newly held) | 274 -> 269 (8 released, 3 newly held) |
| heads the rule touched / values changed | 40 / 17 (all narrowed -> quarter) | 50 / 44 (narrowed -> quarter 23, -> dotted quarter 21) |
| values changed that stand in a held bar (not in the file) | 3 | 6 |

**Brahms whole movement: not run.** The 2.165 lane held one or two Brahms replays on the box all afternoon; my whole-record run
waits behind them (`probe/run_brahms_2_170.sh`, unattended) and its numbers are NOT in this table. The p0-8 slice reaches 50 of
the rule's ~330 static Brahms heads (`static_reach_2_170.py`: 331 Brahms / 68 Litolff before the replay).

**Sean's judged tiles** (`python3 -m tools.omr.staged.judged score` on each arm's mini record): Litolff right/wrong/narrowed
156/30/7 -> 157/30/6 -- one tile moves, 2.81-phase2 tile 10 (`glyph/2/1/4/1/0`, Sean "4") narrowed -> right. Brahms p0-8
90/11/5 -> 92/11/3 -- 2.81-phase2 tile 2 (`glyph/1/0/3/6/0`, "4") and 2.81 tile 13 (`glyph/2/0/9/4/1`, "quarter") narrowed ->
right. **No judged tile goes right -> wrong or right -> narrowed on either plate.** (Only ~30 Brahms / 7 Litolff judged subjects
sit in the narrowed-beam population at all, so this is a small witness.)

My look at every Litolff change of round 2 (17) and 16 Brahms static-reach heads (ours, not evidence): all unbeamed, no flag
seen; tile 2 below is the one I doubt -- its head looks HOLLOW (a half read black by the head-fill reader), written quarter
where it was narrowed before. That is 2.146's known cost of deciding (another reader's error carried into a plain note).

## 5. Blind tiles for Sean: `out/print/2.170-review/` (12 tiles; key kept apart in `out/2.170/tiles-key.json`, as 2.169 did)

Cut and keyed in ONE run of `tiles_2_170.py` (seed 2170, asserted one key row per PNG, same numbering). 10 changed notes (5
Brahms from the p0-8 replay, 5 Litolff), none already judged, + 2 controls (a decided quarter and a decided eighth the rule
never touched -- they can fail: our reading may be wrong). One blue box on the note, nothing else of ours; README says blue = the
note asked about. Question: "What is the written value of the note in the blue box?" answers.json `{}`.

## 6. Limits and what is left

* The flag-window clause is the only guard against a flag the detector never boxed; `ink_not_flag_shaped` is still a
  cannot-tell to the 2.83 reader. The tiles test it. A cut-off was not tuned here: every number is an existing reader's.
* Not fixed: (b) heads with no own stem (mostly not notes on Brahms -- a notehead-gate question, not a beam one); (c) real beams
  refused `not_straight` where a slur fuses to a sloped beam (Brahms p3/p4); (a) the shattered beam (27 heads both plates: the
  detector box that reaches the stem is dropped for a shorter CV piece -- `_kept_beams` keeps the CV stroke whenever the two
  overlap in x). (a) is the brief's hypothesis and is the smallest cause.
* The beam-run reader misses a short beam between two close stems (reach >= 1.6 spaces; Litolff p2): a GATHER fault worth its
  own item if Sean wants beams between close stems read.

## 7. Gates

Fast tier (`pytest -m "not slow" tools/omr/tests -q`, serial, this tree): **8,512 passed, 12 skipped, 2 xfailed, 0 failed**.
Lane tests: `tools/omr/tests/test_staged_beam_refused_off_the_tip_2_170.py` (11) + 2.146's and 2.81's suites unchanged (48 pass).
`python3 -m tools.omr.staged.check`: open=193; no finding names this change (the flag, the function or the reason).

## 8. Sean's 12 answers (2026-10-19, `out/print/2.170-review/answers.json`, recorded at 986d703b) and the two additions he approved

Verbatim: *"1.4 2.2 3.4 4 repeat sign dot 5-7.4 8.8 9.4 10-12. Dot 4"*. Of the 10 changed notes 9 right; **tile 2 is a HALF**
(Litolff p5 sys1 st1 c9 g7) that the rule wrote plain as a quarter. Control 4 (`glyph/5/0/5/11/2`, decided quarter on main) is a
repeat-sign dot boxed as a head -- not this lane's (the notehead gate); recorded here only. Control 8 right.
The first manifest named its subjects in a form `judged build` does not read, so the 12 answers indexed with no subject;
`probe/fix_manifest_2_170.py` rewrote it as a `tiles` list (no role) and the index was rebuilt. The indexer has no comparator for
numeric answers, so `probe/score_tiles_2_170.py` scores them per arm.

### 8.1 Addition 1 -- head-fill guard (in `adjudicate_duration`, the rule's own guard)
The rule decides only where 2.148's first-step fill reading SETTLED `black` on a head-sized box. **That alone does not keep
tile 2 narrowed**: its fill reading IS settled black (interior white 0.0 of 60 rows, centre window ink 1.0 on both rasters) --
the box is a `yolo_rescue_lowconf` box (score 0.19, witness `accidental_right`) whose ink reads solid, though the print shows a
hollow head. So the guard also asks that the head's box be the production detector's own (READERS.DETECTOR), never only the
low-confidence rescue. This second clause is mine, beyond the wording Sean approved -- flagged here for him. Tests: no fill row,
an undecided fill (0.15), a rescue box -> each keeps the narrowing.
Effect: Litolff heads the rule touches 40 -> 39 (tile 2 now NARROWED, `beam_discounted_uncertain`); Brahms p0-8 50 -> 48.

### 8.2 Addition 2 -- `OMR_BEAM_NOT_ON_SYSTEM_ARC` (default OFF; Sean: "beams cannot have an arc")
`_strokes_on_a_system_arc`: a beam stroke whose INK lies on a 2.166 traced system arc -- the detector `beam` boxes 2.166 itself
measured `stroke_only` (ink off the traced stroke < 0.06 sq spaces, pixel-measured in GATHER on the page raster, and overlapping
the arc's own boxes), matched to their `Q.BEAM_STROKE` row by the identical box, and any CV stroke wholly inside one. Used twice:
(a) refused `on_system_arc` first in `_not_a_beam_by_ink`; (b) such a stroke no longer blocks the off-the-tip rule's zone test.
A beam fused to a slur's tail is not `stroke_only` (its box holds beam ink off the trace), so it is never refused -- but the record
keeps only the box-level measurement (2.166 files the arc's ends, not its traced pixels), so "refuse only the part on the arc"
cannot be done without a GATHER change and a re-gather: the fused box is left whole instead.
Reach: 209 Litolff / 633 Brahms `stroke_only` beam boxes, all 842 match a detector stroke row; no CV stroke lies inside one.
**On its own it settles 0 notes on both plates** (arc arm: 0 refusals, 0 values changed, file identical): 191 / 584 of those boxes
are candidates, but every one is already discounted earlier by 2.25b's `_not_a_decided_arc` (a stroke inside a DECIDED slur/tie's
box) or 18 / 49 dropped by `_kept_beams`. As the rule's second witness it adds 3 Litolff heads (2 values in the file: Litolff
6,639 -> 6,641 notes), 0 Brahms p0-8.

### 8.3 Round 3 on the exported file (`out/compare_*_r3.txt`; arms off / tip / arc / both; control 0 differ on both plates)

| | Litolff whole movement | Brahms pages 0-8 (whole movement: the box held two 2.165 Brahms replays again -- not run) |
|---|---|---|
| file notes off -> tip -> arc -> both | 6,626 -> 6,639 -> 6,626 -> 6,641 | 3,543 -> 3,591 -> 3,543 -> 3,591 |
| narrowed live verdicts off -> both | 528 -> 510 | 774 -> 731 |
| values changed off -> both | 18 (17 by the rule, 1 knock-on; all narrowed -> quarter) | 43 (37 by the rule: 19 quarter, 18 dotted quarter; 6 knock-on) |
| held bars off -> both | 564 -> 567 (0 released, 3 newly held) | 274 -> 269 (8 released, 3 newly held) |

**Judged** (both arm vs off): Litolff 2.81-phase2 tile 10 narrowed -> right; Brahms p0-8 2.81-phase2 tile 2 and 2.81 tile 13
narrowed -> right; **0 right -> wrong anywhere**. Sean's 2.170 tiles under `both`: Litolff 4 right, tile 2 narrowed (not wrong),
control 4 not a note (ours decided quarter -- main's error); Brahms 6 of 6 right (incl. control 8). 0 wrong.

### 8.4 Tiles 2: `out/print/2.170-review-2/` (3 tiles; key `out/2.170/tiles-key-2.json`)
The arc witness changes ONE unjudged note in the file (Litolff p9 sys0 st3 c10 g2, narrowed -> quarter, a chord under a slur
whose piece stood at the stem tip) -- 1 tile + 2 controls (decided eighths, Litolff and Brahms). Same rules: one blue box, one run,
asserted. answers.json `{}`.

Round 3 fast tier (this tree, serial): **8,520 passed, 12 skipped, 2 xfailed, 0 failed**; flag-doc tests re-run after the docs edit: 17 passed.
