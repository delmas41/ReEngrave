# 2.129 -- stacked chord heads counted as one (STAGED GATHER stack fit, read by ADJUDICATE)

Sean, 2026-10-14: "yes start the stacked chord heads". Fix: `OMR_STACKED_SECOND_HEAD`, default OFF, until Sean sees `out/print/2.129-review/`.
Truth: Sean's Brahms 317803 pdf 0 (every head boxed, 382 heads). Record: `brahms1-breitkopf-mvt1-whole-20261013-night`. Scripts in `probe/` (paths are scratch-local).

## What the 2.119 brief had slightly wrong
The twins are NOT "a step apart". They are heads a THIRD apart (1.0 staff space, 2 half-steps) on the SAME side of one stem, so they touch and the ink is one tall blob. (A second is on opposite sides of the stem and never forms a group.) `out/diagnosis_sheet.png`: green = Sean's heads, blue = box kept, red = box refused `stacked_head_duplicate`, panels A-E the five twins, F a true duplicate, G a written third.

## Step 1: diagnosis (Brahms pdf 0)
91 chord pairs on Sean's truth have heads within 1.5 spaces (`out/chords.json`). All are same-stem thirds; 85 fit as k=2 and are written. The 7 `stacked_head_duplicate` refusals on pdf 0 are:
| n | what | verdict |
|--:|---|---|
| 5 | the second head of a third (the 5 twins) | WRONG refusal, the whole loss |
| 1 | `glyph/0/0/0/4/15`, one head boxed twice (both boxes on Sean's head q98) | right |
| 1 | `glyph/0/0/11/7/1`, a box on no head (ink column 0.7 spaces) | right |

Cause, ranked: (1) the fit's MEAN gate. Slot scores of twin 1 are 1.00 / 1.00 / 0.86: the middle slot saturates on the blob and the lower head's own slot loses its centre to staff-line removal, so the pair's mean (0.93) is 0.068 under the lone best (1.00) and "adding it cost explanatory power" (margin 0.05) turns it away. 5 of 5 twins have mean gap -0.057 to -0.095 and a second slot that holds real ink (fill gap +0.41 to +0.49). So the fit calls k=1, both boxes map to slot 0, and the lower-ink box is refused. (2) Not the blob height, not the window, not the stem side (all five are right-side groups with the stem on the left): the stem side and window are fine. A mean over saturated ink is no witness for two heads that touch.

The 211 refusals page-wide (Brahms, all 26 pages; boxes and the keeper's box from the record, ink from the page raster, spaces from each box's own `height_spaces`; geometry classes, not truth, except pdf 0):
| n | geometry | reading |
|--:|---|---|
| 108 | the two boxes <0.5 space apart | one head boxed twice: true duplicates |
| 56 | >=0.85 space apart AND the ink column is >=1.8 spaces tall | two heads: second heads wrongly refused (pdf 0: 5, each confirmed by Sean's truth) |
| 24 | >=0.85 space apart, column <1.8 | a ghost box beside one head: right |
| 23 | 0.5-0.85 apart | unsettled |

So about 108 of 211 are true duplicates and about 56 are real second heads lost; the 56 is a proxy off the page raster, confirmed only on pdf 0 (5 of 5, 0 false). Litolff pdf 0-3: 64 refusals, none changed by the fix.

## Step 2: the fix (STAGED GATHER `gather_stacked_head_fit` -> `fit_stacked_head_count`; ADJUDICATE untouched except a record line)
Where the mean test is the ONLY test that fails and the pair is a third, the fit asks three independent things, and all must hold:
1. the detector's own lowest and highest box of the group stand >= 1.5 half-steps apart and each is within one half-step of its slot (`_stacked_slots_have_boxes`): the fit never adds a head the detector did not box at a second head's place. One head boxed twice is 0.4 apart.
2. each slot holds >= 0.75 ink (`STACKED_BLOB_MIN_SLOT_FILL`; the twins' weaker slot reads 0.81-0.89).
3. the ink column through the heads' middle (`stacked_blob_height_spaces`: +-0.28 space of x, rows >= 0.3 ink, gaps up to 0.2 space bridged, local to the heads' x) is >= 0.8 x (gap/2 + 1) = 1.6 spaces.
Filled heads only (`noteheadBlack*`): the test reads a solid column, and a Litolff tremolo slash boxed beside a half note read 1.78 spaces of ink in the first draft and was kept as a second half note (caught in the one-page A/B, Litolff pdf 2).
When the blob test fails the refusal keeps `detail.near_miss` {pair, blob height, needed, mean gap, fill gap} on the fit row and `stacked_head_signal.near_miss` on the verdict (2.106). A true duplicate stays refused (1 fails), a box on blank paper stays refused (2 fails).

Calibration was wrong once and that is the lesson: the blob measured on the page raster read 2.17-2.25 for the twins, the cell raster (staff lines removed) reads 1.74-2.23, so a 1.8 cut, set on the page, kept 2 of 5. And a head with a ledger line, boxed twice, read 1.76 in the cell (Brahms pdf 1, `glyph/1/0/0/4/33`) -- the same number as a twin. The blob alone cannot separate them; the boxes' spread (0.38 and 0.40 vs 1.89-2.12) does, so the blob is the second witness.

## Step 3: measured (this tree, flag OFF vs ON, `--weights auto --no-surya --no-ocr`, through EXPORT)
Truth, Brahms pdf 0 (`probe/ab.py`):
| | OFF | ON |
|---|--:|--:|
| of Sean's 382 heads, with a surviving box | 376 | **381** |
| second heads kept (twins recovered) | 0 of 5 | **5 of 5** |
| heads lost | | 0 |
| true duplicates wrongly kept (a head with 2 surviving boxes, new) | 1 (the pre-existing 4/10+4/15 pair, same either way) | 0 new |
| `stacked_head_duplicate` refusals | 7 | 2 (the two right ones) |
Export, pages 0-1: written notes 649 -> 653, guessed 104 -> 105, bars held out 59 -> 59, noteheads inside held bars 403 -> 404. Litolff pages 0-3: nothing changes (817 / 817 written, 59 / 59 held, 64 / 64 refusals, 4 near-miss rows recorded, 0 kept). The cascade the 2.119 study predicted did NOT show on these two pages: the 4 recovered notes did not release a held bar (the bars stay held for `voice_overfull` and other reasons); the recovery is the 5 notes, not a bar count. `judged score` unchanged both docs (Brahms TOTAL right 51 / wrong 5 / narrowed 8 / abstained 1 / not_found 39 / unscored 102; Litolff 56 / 8 / 2 / 1 / 62 / 91). `staged.check` open 193 = main 193. Fast tier on the final tree: 7,943 passed, 11 skipped, 2 xfailed, 0 failed (the first draft's one failure was a flag-table cell the doc/predicate test reads by its first token, fixed); the new test file has 16 tests, RED-first (11 of 14 failed on the unpatched tree, the 3 passing were the OFF controls).

## Tiles for Sean (`out/print/2.129-review/`, sheets 1-3, 15 tiles)
Question: how many noteheads are in the red corners? (1 / 2 / other). A fixed-size red corner bracket only. 13 tiles are the proxy class above (Brahms, 11+ pages, black heads, boxes >= 0.85 space apart and a >= 1.8 space column), 2 are controls (one head boxed twice, expect 1; a ghost box beside one head, expect 1). Manifest hidden in `_hidden/`. These are the proxy, not exactly what the shipped rule keeps; Sean's answers decide the default.

## Open
- Hollow second heads (half notes a third apart on one stem) are not touched: the blob test is for filled heads (the 23 + any hollow among the 211).
- The 23 refusals 0.5-0.85 space apart are not settled by this item.
- Default stays OFF until the tiles come back; the cascade (bars released) needs the other four 2.119 splits (A, B, D) fixed too.

## Sean's answers (2026-10-14) and what they changed
Tiles 1-5, 7, 8, 10, 11, 13-15: two heads (13 of 13 proxy tiles minus tile 6). Tile 12 (one head boxed twice): one, correct. Tile 6: two tremolo slashes, not heads. Tile 9 (my "ghost" control): a real second head. Recorded in `out/print/2.129-review/answers.json`.
- Tile 6 (`glyph/16/0/10/7/6`, a head with a tremolo slash below, a 3.2-space blob): the geometry proxy would keep it; the SHIPPED rule does not. Gathered with the flag ON on the final tree: the slash box is still refused `stacked_head_duplicate`, fit k=1, no `second_head_by` (its slot holds a thin diagonal stroke, ink 0.76 on the fit row, the pair never reaches the blob test). The slash is not turned into a note. A synthetic guard test (head + thin diagonal below) pins it; the proxy count was optimistic there, the rule is not.
- Tile 9 (`glyph/21/1/3/7/6`, two hollow half notes a third apart): refused, and wrongly. Why: the fit read k=1 (hollow slots score 0.70/0.98, the mean test fails exactly as for filled heads) and the blob test is defined for FILLED heads only (added because a Litolff tremolo slash boxed as a half note was kept), so hollow groups never reach it. My control label came from the page-raster blob (0.95), which is not a measure for hollow heads. Not fixed by keeping it: of 27 hollow refusals >= 0.75 space apart on the movement, 19 have both boxes decisively hollow like tile 9, but so does `glyph/0/0/11/7/1` on pdf 0 -- the two halves of a bass clef, 1.0 space apart, both decisively hollow (centre 0.09 / 0.10, ring 0.71 / 0.62), no head in Sean's truth -- so a "two holes" test cannot yet be told from a clef. The rule says no cut-off tuned on one case may decide; the clef is the control that can fail it. The hollow group's fit row now carries `near_miss.not_tested = "hollow-class group"` and the verdict repeats it (2.106); a hollow tile set (the ~19, with the clef) is the next question for Sean. Test: `test_a_refused_hollow_pair_says_it_was_not_tested`.
- The tile-9 error is also a hole in the page-raster proxy: the proxy's "two heads" count (56) is for black heads; hollow second heads are a separate, still-refused class (`probe/hollow_scan.py`, `out/hollow_scan.json`).

## 2026-10-30 ROADMAP 2.232 -- a stacked HOLLOW third read as ONE head (lane-2.232-stacked-head), flag `OMR_STACKED_HEAD_STEP_APART` OFF
STAGED, GATHER (`gather_stacked_head_fit`) + ADJUDICATE (`_stacked_head_duplicate_refusal`).

**CONVENTION ASSUMED:** heads on one stem and one SIDE are never a second (a second goes on the other side, DECISIONS 2026-09-30 / 10-26), so two same-side head boxes whose centres stand 0.75 sp (the midpoint of a second and a third, the existing `NOTEHEAD_SAME_SIDE_MAX_DY_STAFF_SPACES`) or more apart are two heads; one head boxed twice puts both centres within ~0.35 sp. **WHAT WOULD FALSIFY IT:** a plate whose detector boxes one head twice more than 0.75 sp apart (a stem-plus-head box is already out: only plausible head boxes are compared), or a chord of a third drawn on one side that the cut calls one head. **NOT CONFIRMED:** the 0.75 sp cut and the 0.05 near-tie margin are measured on Litolff (and read on Brahms), not confirmed on a third publisher.

**Cause (answer to "mid read or refused later?").** GATHER, mid read. The detector boxed both heads. `fit_stacked_head_count` scores a head template at every half-step slot and at k=1 names the best slot. Two touching hollow heads a third apart leave a ring of ink at the slot BETWEEN them too, and the template's `max(centre, ring)` there beats either real head: Litolff p3 `glyph/3/0/4/3/12/13`, slots 1/2/3 scored 0.68/0.87/0.77 (eraser raster; 10-22: 0.43/0.79/-: the weaker slot sat inside the margin band, so the fit abstained `ambiguous`). The k=2 test then needs the mean not to fall by 0.05: 0.775 vs 0.87 is -0.095, so "clearly not a real additional head", k=1 at slot 2. The model is the fault: `observed` (the boxes' positions, 3.24 and 0.88) only broke exact ties, so the one head it chose stood on NO box, 1.12 and 1.24 half-steps from both. The blob test that rescues filled thirds (2.129) is built for solid columns and does not run on a hollow group (the fit even files `near_miss: not_tested`), and the page-raster hollow pair test (2.132) is parked. ADJUDICATE only acted on the measurement. OMR_ERASER_FIX did not cause it, it moved a slot score across a margin the fit has no business deciding on.
**Process lesson.** A known hole (2.129 tile 9, 2.132: "hollow thirds are refused") was parked behind a control (the 8 of 9/8) instead of being made to ABSTAIN where the fit cannot test; a quantity that says "not tested" must not be allowed to decide. The abstention is the cheap, safe half; the positive test (2.132) can come later.

**Distribution (rule 7: measured, not assumed).** Litolff 20261029-night sample pages: 189 k=1 groups with 2+ boxes, 141 hollow, 48 filled. Distance of the fit's slot from the NEAREST box (half-steps): filled 0.0-0.5 for all 48; hollow >= 1.0 for 22 of 141 (also three at 1.5-1.75). Brahms 20261020 sample slices: hollow 23 of 60 at >= 1.0, filled 1 of 77 (1.5). A head boxed twice sits within 0.5 of a box. The guard is: hollow group, k=1, boxes span no more than 3.0 half-steps (a pair; 2.132's domain), slot >= 1.0 from every box -> abstain `ambiguous`, margin = 1.0 - distance (signed), `head_on_no_box` recording slot, box positions, distance. Hollow-only because filled groups have the blob witness.
**Near-tie margin (0.05).** The keeper's ink lead is a guess below the amount the SAME box's ink moves when the raster is re-read: matched 5,870 Litolff boxes between 10-22 and 10-29: median 0.0, 90th pct 0.011, 95th 0.064, 6.0% move > 0.05 (8.7% > 0.02). 0.05 = `STACKED_HEAD_FIT_MARGIN`'s discipline, so one stated margin, not two. A lead < 0.05 refuses neither box and records `near_tie` {keeper, lead, signed margin}. The step-apart filter in ADJUDICATE (0.75 sp, plausible head boxes only) is the second guard for a fit that commits k=1 with a slot on one of two boxes a third apart.

**Control that can fail.** The OFF arm re-gathered through the master cell map (cm-54ccb4729528) reproduces the overnight at the three places: /12,/13 fit [1,0,2.0], place 1 [1,0,0.0], place 3 [1,0,7.0]; ON: places 1 and 2 abstain `ambiguous` (-0.22, -0.12), both boxes decided `notehead`; place 3 (a 3.29 sp box over head and stem, filled) is still refused and the file is right.

**The three measures** (`lane_report --flag OMR_STACKED_HEAD_STEP_APART --cell-map master`, Litolff pages 2,3,4,6,8,9,10,11,16 = the frozen sample plus p3, record 20261029-night; NOT the frozen sample, p3 added for the judged place): file: notes +33 -2, accidentals +6 -8, flags +1, ties +7 -23 ~1, articulations +1 -3, fermatas +1 -3, note values ~2, pitches ~17, blue marks +16 -6; red bars 0 -> 0; `stacked_head_duplicate` refusals 272 -> 96, fit abstentions 7 -> 43 (36 `head_on_no_box`). The 33 gained notes are 30 halves, 2 quarters, 1 eighth; of the 6 gained-note tiles looked at (2,3,4,7,8,11) 5 show a hollow chord of a third; tile 4 (p2) is not clear to me -- Sean's eye. The 2 "lost" halves (p2 m1 C4, p8 m142 C4 at onset 0) are the same pitch at the same place ON (box swapped / a doubled write OFF), not a vanished head: tiles 5 and 6. Judged right->wrong 0, wrong->right 9. Tiles: `out/print/2.232-tiles/` (12, one orange box, key `out/print/2.232-key/key.json` outside); includes p3 `/12` and place 1.
Not isolated: how much of the 272 -> 96 is the fit abstention vs the ADJUDICATE parts (one flag); all gained notes were crop-checked as chords, so no doubled twin is visible in the sample I looked at (not counted over all 33). Cost on ties: -23 +7: a chord of two notes makes the tie pairing ambiguous (the same cost 2.132 recorded).
**Brahms** (frozen sample, pages 0,4,5,8,12,14,19,25, master cm-2d494f8fc055, re-gathered both arms, `out/lane-report/2.232-brahms/`): notes +8 -3, accidentals +4 -6, dots +7 -4, ties -16, pitches ~4, note values ~1, blue marks +2 -7, words +3 -6 (words/dots/accidentals are not touched by this flag: re-gather noise, the OFF arm is not checked against a saved record in re-gather mode), red bars 166 -> 167. Judged right->wrong 0, wrong->right 0 (245 judged tiles on these pages). Effect small, as the Brahms distribution predicts (hollow groups 60 vs Litolff 141). The one extra red bar is not examined.
