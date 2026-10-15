# ROADMAP 2.130 -- dotted half notes read as a quarter or a whole (STAGED ADJUDICATE, `Q.DURATION`)

**CONVENTION ASSUMED (Sean, DECISIONS 2026-10-09, confirmed): "Whole notes never have stems"; "a hollow note with nothing on the stem is always a half"; "open noteheads are never beamed" (2.43).**
**WHAT WOULD FALSIFY IT:** a print whole note with a barline or a neighbour's stem flush against its box, made a half by this rule (Sean's blind tiles, `out/print/2.130-review/`).
**NOT CONFIRMED:** the stem window (centre within -0.25..+0.40 head widths of the head's near edge, >= 2 spaces long), the filled cut (every raster's centre >= 0.85) and the beamed-hollow cut (<= 0.80): measured on Brahms 317803 pp 6, 7, 10 and Litolff 984073 pp 0-3; they NARROW until Sean's tiles and another publisher.

Flag `OMR_OPEN_HEAD_ON_STEM`, **default OFF**. Records: gathered here on current main (`2ccfa621`, 2.115 + 2.127 ON), `--through adjudicate`, weights `deepscoresv2-yolov8l-hollow-graft-shift09-2026-09-04.pt`, Brahms pdf pages 0, 6, 7, 10 and Litolff pages 0-3 (the 20261013-night records predate nothing relevant but are 6.7 GB; the tile pages needed fresh records anyway). Scripts here: `gather_*.sh`, `replay.py` (re-decide the duration chain on a saved GATHER, flag via env), `rdiff.py`, `truth.py`, `diag.py`, `wholes.py`, `tr.py` (trace), `sheet.py` (crops), `make_tiles.py`.

## 1. Diagnosis (STAGED; Sean's three tiles, then every case the same rule touches)
| tile (Sean, 2.127) | head | detector class | stem | what main wrote | cause |
|---|---|---|---|---|---|
| 10 `glyph/7/1/3/10/17` | hollow, dot, stem down at its left | `noteheadWholeOnLine` (conf 0.29) | read (`head_stem` one_stem, flush left) | 4.0 | whole class + a stem read: `stem_value` applies "no whole has a stem" only on a SHARED stem (`lone_head`), so nothing refused the whole |
| 13 `glyph/6/1/0/5/23` | same | `noteheadWholeOnLine` (0.27) | read (flush left) | 4.0 | same |
| 9 `glyph/10/1/3/3/22` | hollow `noteheadHalfOnLine`, ink 0.68 (hollow), in a chord with a black eighth | Half | two stems (`two_stems`, voices) | 1.0 | the black eighth's FLAG (an up-stem in the same column) was attached to the hollow head: `levels = flag_levels`, half 2.0 / 2 = 1.0. An open head never carries a flag (2.43) but the flag was not tested against the class |

Not the hollow-read-black cause, in these three: all are hollow in the print and read hollow (ink 0.68-0.79).

**Counts on the pages looked at** (whole-class boxes with a decided stem, flag OFF -> ON; every one viewed on the print, `sheet.py`):
* Brahms pp 6, 7, 10: 20 whole-class heads with a read stem. 16 are hollow heads (most with a dot) -> decided half or dotted half (10 on p10: 4 were whole and 6 were a DOTTED WHOLE, a 6.0 nothing prints beside a stem; 3 on p7; 3 on p6); 2 are BLACK heads boxed whole (ink 0.95-1.0, `7/0/3/4/19`, `7/1/3/4/21`) -> NARROWED {quarter, half} (the old 4.0 was a wrong whole); 2 are Sean's tiles 10 and 13, already narrowed by 2.127 ({4.0, 6.0}) -> {2.0, 3.0}. One hollow dotted head whose stem is in the print but was NOT read (`10/1/13/7/1`, 6.0) is untouched: a stem-reader miss, not this rule.
* Brahms p 10 flag-on-hollow: 2 cases (tile 9 and `13/0/20`, a rest-shaped hollow mark with a flag) -> NARROWED {half first, flagged}.
* Not notes (pre-existing, value 4.0 -> 2.0, both wrong): Brahms p0 5 C-clef shapes boxed whole (`0/5/7/0-2`, `0/11/7/0-1`, two of them already `stacked_head_duplicate`/`duplicate_box`, dropped), Litolff idx 3 4 (`3/1/7/17/3,5` stacked duplicates, `3/1/2/17/6` a ledger-ish shape). They are the "wrongly made half" list (all were already wrong as a whole; none a real quarter or whole). Two eighth-rest shapes boxed whole (`7/0/1/6/24`, `7/1/10/6/3`) have no stem and are unchanged.

**Truth (halves and dotted halves written right / blue-with-the-right-candidate / wrong), before = after:**
| set | halves | right | blue (has the right value) | wrong | note |
|---|---|---|---|---|---|
| Brahms pdf 0 (Sean's `noteheadHalf*`, 33; dotted by a level dot within 0.9 sp) | 33 | 29 | 3 | 1 | all 33 are Half class with a read stem: the cause above never occurs on page 0. The 1 wrong is a dotted half written plain (`0/5/6/13`, 2.127's dot role), not a head value |
| Litolff idx 1 clean TEST cells (59 truth halves; 50 have a production box) | 50 | 36 | 1 | 2 quarters + 2 abstained + 10 no box | the 2 quarters are the other cause: `1/0/3/15/1` black class on a unison two-voice box (interior 0.69, `head_and_marks` quarter) and `1/0/9/3/5` a 1.66 x 1.59 sp cluster box reading 0.94. NOT fixed here (see 4) |
The truth pages hold none of the 3 tiles' cause, so truth cannot move; the effect is on pages 6, 7, 10 and the Litolff cluster pages.

## 2. Fix (`rhythm.adjudicate_duration`; helpers `open_head_on_stem_enabled`, `_stem_flush_to_head`, `_reads_filled`, `_min_center`)
One block, before the beam-conflict narrowings, for `open_by_class` heads only:
* **Whole class + a stem flush at its side** (not a barline across the middle, >= 2 spaces): ink not filled -> DECIDED half (`whole_class_on_a_stem`; dots add as before; margin recorded). A beam stroke joined to the stem additionally needs the weakest raster <= 0.80. Ink filled on every raster -> NARROWED {quarter, half}, equal support (`whole_class_filled_on_a_stem`).
* **A flag attached to an open-class head** -> NARROWED, the open value first (`open_head_flag_contradiction`), the flagged levels kept as candidates.
Never reads the bar sum; a head whose stem is not read keeps its class (a real whole note has none). Declared reasons added to `adjudicate_duration`. EVALUATE/INFER untouched.

## 3. Measured (replay of the duration chain on the saved GATHER, flag OFF vs ON; and a real gather ON for Brahms p0 and Litolff 0-3)
| page | duration verdicts changed | decided half/dotted half (was whole) | narrowed {quarter, half} (was whole) | narrowed {half-first} (flag case) | candidates shifted by 2.127 narrowing |
|---|---|---|---|---|---|
| Brahms p0 | 5 | 5 (non-notes) | 0 | 0 | 0 |
| Brahms p6 | 4 | 3 | 0 | 0 | 1 (tile 13) |
| Brahms p7 | 6 | 3 | 2 | 0 | 1 (tile 10) |
| Brahms p10 | 12 | 10 (4 whole, 6 dotted whole) | 0 | 1 | 1 (tile 9) |
| Litolff 0-3 | 4 | 3 (non-notes) | 1 | 0 | 0 |
Real gather ON vs OFF (Brahms p0, Litolff 0-3): glyph sets identical (1776 / 5347), duration verdicts changed 5 / 4 = the replay's; everything else identical. Quarters or wholes wrongly made half: 0 real notes; the 8 non-note boxes above (already wrong). `judged score` ON = OFF (litolff TOTAL 47/10/9/1/62/91, brahms 19/3/11/1/68/97); `check` open=193 (not up).

## 4. Not fixed, ranked
1. Black class on a hollow head read quarter (Litolff truth 2 of 50): interior 0.69 and 0.94 on cluster or two-voice boxes. 2.88's firm-hollow cut declines them; a narrowing of any black-class head whose weakest raster is <= 0.75 would catch them, but Brahms black heads show 0/381 there only after 2.115 and Litolff unlabelled boxes are unjudged: needs Sean's tiles of those two first.
2. Hollow whole-class head, stem missed by the stem reader (`10/1/13/7/1`, dotted whole 6.0).
3. C-clef / rest shapes boxed as whole noteheads (not this rule).

## 5. Tests, tiles
`tools/omr/tests/test_staged_open_head_on_stem_2_130.py` (13): RED first on the unchanged tree: the 5 flag-ON tests fail (whole -> half, right-side stem, filled narrows, one dark raster among hollow, flag on a half), the 8 controls pass on both (flag OFF old whole; real whole without a stem stays whole; stem through the middle; short stroke; half with a stem; black quarter; black eighth keeps its flag; ...). `out/print/2.130-review/values-review.png` (15: Sean's 3 tiles, 10 changed, 2 controls: a black head on a stem, a hollow chord head; hidden `_hidden/manifest.json`).

## 6. Sean's 15 tiles, answered (2026-10-14) and landed ON
Sean: "1-2. Dot half 3. Dot half and a quarter 4. Dot half's 5-8 dot half 9. Dot quarter 10. Flat Acc 11-14 dot half 15. Dot quarter", then "3 is just a quarter". Recorded in `out/print/2.130-review/answers.json`; scored against `_hidden/manifest.json` (flag ON output, the replay of this section's lane):

- The rule never leaves a stemmed head a whole (no tile reads 4.0/6.0 any more).
- Exact: 2, 5, 13 (dotted half 3.0), control 3 (quarter 1.0). Blue set including the truth: 6, 7 {2,3}, 8 {1,1.5,2,3}.
- Still wrong, all for a MISSING DOT: 1, 11, 12, 14 decided plain half 2.0 (truth 3.0); 4 (control, a half written plain, truth dotted half 2.0 vs 3.0); 9 and 15 blue {1,2} without the dotted 1.5.
- 10: not a note -- a flat accidental boxed as a head (follow-up).
Landed ON with 2.128 (dot position join) already ON; the re-check of the missing dots follows in section 7.
