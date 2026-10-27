# ROADMAP 2.206 -- the staff-line eraser cuts into marks that sit on a line

Path: SHARED GATHER (`tools/omr/staff_line_removal.py`), read by STAGED (`pipeline.prepare_pages`, `staff_header.extract_header_cell`)
and LEGACY (`transcribe.py`, `run_pipeline.py`). Flag `OMR_ERASER_FIX`, default OFF (LEGACY unchanged). Branch `lane-2.206-staff-eraser`.

## Cause first (rule 3), and the process lesson

**The walk's bound and the test it bounds were two different numbers.** `_vertical_runs_through(ink, y, max_search=cap)` walks
`cap + 2` rows each side of the anchor, and `cap` is the THICKNESS cap (`MAX_LINE_THICKNESS_SPACES` 0.35 sp = 35 px at the canonical
100 px/sp). The run it returns is compared with `crossing_cut = max(min(2 x thickness, 0.45 sp), thickness + 1)`. When the cut is taller
than the walk can see past, a run that CONTINUES past the bound on one side reads as (bound + the other side) and can fall under the cut:
the column is erased, top to bottom of the truncated run -- up to 0.37 sp of whatever hangs from or stands on the line. The docstring says
"a run longer than that is a crossing symbol and its exact extent does not matter -- only that it is too tall": true only while the cut is
no taller than the walk. The 0.45 sp cap (`MAX_ERASABLE_RUN_SPACES`, commit 2a12ac501, "insurance against a case the corpus does not
contain") is what made the cut taller than the walk; the beam test it came with centres the beam ON the line, so the hanging case
(beam flush with the line's edge) was never tested.

It is NOT a dpi or pixel-unit problem: cells are canonicalised to ~100 px/sp, every constant is in staff spaces. It is plate-dependent
through LINE THICKNESS: the bug can fire only when the cut exceeds the walk + 1 (cut >= 39 px), i.e. lines thicker than ~0.19 sp. Both
acceptance plates qualify (measured median thickness Litolff 0.26 sp, Brahms 0.25 sp; cut 0.45 on both). And it fires only where the
ANCHOR (the ink row nearest Phase 1's nominal straight-line y) sits within ~7 px of the line's edge AWAY from the mark ("6 up, 37 down"
on 2.202b's p16 tile) -- Phase 1 fits one y per line while a fat printed line drifts, so this is common but patchy, which is why the
damage looked random (and why the first synthetic tests, with the nominal y at the line centre, did NOT reproduce it: their controls
caught that).

**Process lessons.** (1) A bound and the comparison it serves must be one derived quantity (`walk_for_cut`), never two constants that
drift apart; a later "insurance" constant moved one and not the other. (2) A test must put the subject where the page puts it (flush
with a line's edge, nominal y off-centre), not centred; the controls that fail when the fix is removed are what showed the first tests
were blind. (3) Fifteen readers already carried workarounds for "the erase thins / splits ink" (2.202b's `_restored_thickness`,
`beam_stroke_ink` reading `cell.image` "34 px erased vs 49 px", split eighth rests, `STEM_TIP_HOOKS_CLOSE_SPACES` healing "thin
stripes", `HEAD_STEM_GAP_SPACES` "a staff line erased or thinned", ...): each lane saw the symptom downstream and compensated locally;
nobody opened the eraser. The symptom recurring in many readers is the sign the cause is upstream and shared.

## 1. The problem, measured (read-only, no gather)

Tools: `extract_boxes.py` (detector boxes from the 2.202m OFF records -- the detector reads the UNERASED cell, so its boxes do not
depend on the eraser), `reach.py` (re-runs the eraser per cell, asserted byte-equal to the real `image_no_staff` on every cell; then
the variants), `summarize.py`, `specks.py`, `crops.py` + `sheet.py`. Frozen sample, 8 + 8 pages, 2,707 + 2,034 cells. Results in
`results/` (`summary_*.txt`, `specks_*.json`; the per-box `reach_*.json`, 10-15 MB, are not committed -- re-run `reach.py PLATE
results/boxes_PLATE.json OUT.json`).

**Mechanism count (model-free): columns the eraser erased although its walk was truncated** -- each one takes up to 0.37 sp of a mark:
Litolff 159,313 of 12.4 M line columns (1.28%), Brahms 153,744 of 16.6 M (0.93%).

**Ink a mark loses ("overcut")**: erased ink lying outside the line's own band (centre and height of the run in pure-line columns,
running median +-0.5 sp; band = +- half height + 2 px), in pieces >= 0.08 sp tall and >= 0.01 sp^2, attributed to every detector box
containing it. Per class, boxes losing ink / pixels lost, main -> reach (the chosen fix):

| class | Litolff boxes | lose ink main -> fix | lost px main -> fix | Brahms boxes | lose ink main -> fix | lost px main -> fix |
|---|---|---|---|---|---|---|
| beam | 1390 | 118 -> 83 | 83k -> 27k | 3359 | 419 -> 292 | 301k -> 121k |
| black head on a line | 2417 | 396 -> 299 | 70k -> 25k | 2955 | 231 -> 110 | 44k -> 10k |
| black head in a space | 2257 | 546 -> 181 | 338k -> 15k | 3606 | **908 -> 13** | **906k -> 1.5k** |
| half / whole head | 823 | 351 -> 160 | 187k -> 35k | 415 | 182 -> 112 | 105k -> 33k |
| whole / half rest | 883 | 407 -> 238 | 267k -> 24k | 632 | 232 -> 15 | 262k -> 1.1k |
| quarter rest | 469 | 340 -> 260 | 222k -> 47k | 515 | 279 -> 220 | 118k -> 37k |
| eighth / 16th rest | 149 | 87 -> 60 | 30k -> 9k | 1306 | 714 -> 252 | 330k -> 36k |
| flag | 141 | 59 -> 39 | 29k -> 8k | 938 | 499 -> 248 | 232k -> 57k |
| tie / slur | 1337 | 348 -> 288 | 235k -> 99k | 4630 | 1418 -> 1095 | 845k -> 380k |
| accidental / key | 960 | 386 -> 266 | 167k -> 51k | 2459 | 845 -> 536 | 296k -> 111k |
| dot / staccato | 218 | 18 -> 7 | 10k -> 1k | 3384 | 85 -> 16 | 30k -> 2k |
| ledger line | 3762 | 211 -> 181 | 17k -> 14k | 2313 | 40 -> 12 | 5k -> 0.6k |
| clef | 268 | 172 -> 147 | 301k -> 44k | 297 | 197 -> 172 | 127k -> 38k |
| dynamic / text | 1127 | 113 -> 49 | 82k -> 12k | 1172 | 58 -> 33 | 25k -> 6k |
| time signature | 36 | 14 -> 10 | 5k -> 3k | 158 | 65 -> 58 | 25k -> 13k |
| all (incl. unboxed) | | | 3.06 M -> 0.91 M | | | 3.29 M -> 0.76 M |

The "boxes losing ink" counts are an UPPER bound: my crop look (below) found ~1 in 5 flagged boxes is only the line's own fillet where it
meets a stem/barline (line ink my band model calls mark ink). Pixels lost is the steadier figure. Typical depth of the loss: 0.16-0.20 sp.

**What remains after the walk fix is a second, smaller mechanism -- the cut window.** A column whose WHOLE run is no taller than the cut
(0.45 sp) is erased whole, so a mark that adds <= cut - thickness (~0.2 sp) to the line in that column loses it: a flat's bowl, a rest's
corner, a half note's thin edge tangent to a line, the end of a tie. And a third, inherent one: a thin stroke lying INSIDE the line band
(a tie or slur running along a line) is lost by any vertical-run eraser.

**Line ink kept that should go:** with the fix, the line is kept in the columns a hanging mark covers (as it always was under a crossing
mark): line-row ink cleared on the 2-page subset 81.2% -> 80.4% (Litolff), 87.2% -> 86.1% (Brahms). Residue of a locally thick line
(> cut with nothing crossing) is unchanged by the fix.

**Crop look (MY look, not Sean's -- rule 7; `out/print/2.206-eraser-look/`, left to right: print | main | fix | band; black kept, grey
erased in the line band, RED erased outside it, BLUE line kept with nothing crossing).** 32 boxes (25 Litolff, 7 Brahms, seeded
2206 from boxes main flags): 20 are real damage main does and the fix undoes (heads in a space with their top 0.17-0.2 sp shaved, whole rests
cut to a strip, a quarter rest cut in three, an eighth rest's blob chewed, clef bodies, a dynamic `f`'s top, beams thinned, the lower
corner of a natural); 6 are the cut window, still lost with the fix (flat bowl, eighth-rest corners, a half note's thin edge, a quarter
rest's tip, a tie's end); 6 are false flags of my measure (stem/barline fillets, a line bump). No crop showed the fix keeping something
that is not a mark, beyond the line segment under the hanging mark.

## 2. Which readers consume the erased raster (and whose cut-offs may move)

The detector never sees it (`yolo_detector` reads `cell.image`; `pipeline.py` "NEVER ERASE FOR THE DETECTOR"). STAGED default-ON
readers of `image_no_staff` (~22): `_ink_components` (Q.INK, CELL_INK_PIECES, NARROW_BOX_SHAPE, UNBOXED_REST_SHAPE, EMPTY_BAR_REST_SEARCH),
`line_detection.detect_stems/detect_beams` (Q.STEM, Q.BEAM_STROKE; silent fallback), stem-tip / flag ink (Q.STEM_TIP_INK), stem slashes,
dot-stroke ink, mark shape (dot vs staccatissimo), wedge rescue gate, beam-stem join, ledger rung ink / owner density / ink under,
notehead recentre (moves head positions), notehead ink `ink_net` (fill), stacked-head fit, head-stem cross ink, rest-ink contact,
accidental shape, system arcs (composite ink), and on the ERASED HEADER CROPS (`staff_header` erases them itself) the clef locator, the
key-signature template and the meter templates. Cut-offs a comment says were tuned ON the erased raster, which the fix may move:
`STEM_TIP_INK_*` (flags), `STEM_TIP_FRAG_GAP_SPACES` 0.35, `STEM_TIP_HOOKS_CLOSE_SPACES` 0.06 ("healing of the staff-erase's thin
stripes"), `HEAD_STEM_GAP_SPACES` 0.30, `INK_PIECE_MIN_AREA_SP2` 0.10, `UNBOXED_REST_WIDTH/HEIGHT_SPACES`, `RECENTRE_*`,
`STACKED_HEAD_MIN_SLOT_FILL` 0.4, `LEDGER_RUNG_INK_*`, `accidental_shape` windows, `BEAM_STEM_JOIN_GAP_TOLERANCE_THICKNESS_MULT`, the
split-eighth-rest joining. Readers already reading the UNERASED raster (CV_BEAM_SHAPE, CV_BEAM_LEVELS, CV_HEAD_LINE_CUT, head-stem reach,
`ink_raw`) do not move. 2.202b's `stroke_map._restored_thickness` compensates this exact bug and becomes partly redundant with the fix.

## 3. Candidate fixes, and the choice

| | design | evidence on the sample | cost |
|---|---|---|---|
| **A (chosen)** | the walk reaches past the cut: `max_search = max(cap, ceil(cut))` (`walk_for_cut`); a column is erased iff its WHOLE run is no taller than the cut -- the rule the module always stated | lost mark ink 3.06 M -> 0.91 M px (Litolff), 3.29 M -> 0.76 M (Brahms); heads in a space and whole rests almost fully restored; new specks on the 2-page subset 0 -> 0 (Lit), 228 -> 209 (Bra); pieces +8 / +8 | no new constant; inert where lines are thin (twins: byte-identical below ~0.19 sp); keeps the line segment under a hanging mark (line cleared -0.8 / -1.1 pt) |
| B | A + where a run is under the cut but taller than the line's LOCAL height, erase only the line's band rows (line path modelled from pure-line columns, running median) | closes the cut window (lost px -> 0.01 M by its own measure, which is CIRCULAR: it erases by the model it is scored against); the independent measure: **new specks 0 -> 4,659 (Lit), 209 -> 8,645 (Bra) on 2+2 pages** -- the line's ragged edges left beside every stem and mark | three new tuned constants (pad 2 px, pure factor 1.5, window 0.5 sp) on our two plates = may only narrow (CLAUDE §4); specks feed every component reader |
| C | reconstruct / own the line under marks (keep ink where a non-line stroke continues across the line, by stroke direction) | not built: it is the shared ink map's ownership step (2.194/2.205) arriving at the eraser, and the only design that also rescues the inherent case (a tie along a line) | a new reader; belongs to the ink-map plan |
| D | thresholds per dpi / per publisher | refuted: everything is already in staff spaces at a canonical 100 px/sp | -- |

A is chosen: it removes ~70-77% of the lost mark ink with zero new constants and no new specks, it is exactly the module's documented
rule, and it cannot fire where the bug cannot. B is NOT shipped: its gain is the cut window (~0.2 sp corners) and it pays with
thousands of fragments; the cut window is better closed by C (ownership) later. Tests: `tools/omr/tests/test_staff_eraser_fix_2_206.py`
(23: flag parsing, the `walk_for_cut` contract, three hanging/standing marks and a head in a space with OFF controls, thin-line twins
byte-identical at three anchor offsets, bare fat lines still erased, a mark under the cut erased both ways, a stem + centred beam unchanged,
ON == the unbounded rule on a busy cell; with `walk_for_cut` mutated back to `cap`, 8 fail).

## 4. The three measures

**NOT RUN -- blocked on the box.** 2.204 and then 2.201 gathered until 02:27; after that the box was idle but the disk stayed at 13 GB free,
under the lane's 15 GB floor, for 20 minutes. Fast tier on the branch (flag OFF): 8,922 passed, 12 skipped, 2 xfailed, 0 failed.

The fail-fast run, when the disk allows (same 2-page subset 2.204 used: Litolff 4, 11; Brahms 5, 14):

    LANE_REPORT_SAMPLE=<file with plates.litolff.pages [4, 11], plates.brahms.pages [5, 14]> \
      python3 -m tools.omr.staged.lane_report --flag OMR_ERASER_FIX --from gather --workers 2 --out out/lane-report/2.206s

then, only if notes-not-written does not jump and judged right->wrong is 0, the frozen sample (`--out out/lane-report/2.206`).

⚠️ **`--from gather` MUST be passed.** `lane_report.acts_in_gather` counts a flag as GATHER only when its home is a module under
`staged/` in `GATHER_MODULES`; `OMR_ERASER_FIX` lives in the SHARED `tools/omr/staff_line_removal.py`, so `--from auto` would replay the
saved GATHER rows from ADJUDICATE and report "nothing changed" by construction. That is a hole in the shared command (any shared
GATHER-side reader -- the eraser, `line_detection`, `measure_extractor` -- would hit it), worth a one-line fix there (its own item).

What to expect, from Part 1: most changes in readers of `image_no_staff` -- notehead fill / recentre on heads in a space (Brahms 908
boxes), rests read by ink components (whole rests, eighth rests), stem-tip flag ink, accidental shape, the clef / key / meter templates on
the erased header crops. Tile question to fit what changes (draft): for notes/rests gained or changed, "What is the note or rest value
at the orange box?"; if clef/key/meter move, a separate plain question.

## 5. Fail-fast subset (2026-10-26): STOPPED on one judged right->wrong. The cause is a key on a duplicate box, not a change in the file

Main merged at 4b79e9103. Fast tier, flag OFF: 8,989 passed, 12 skipped, 2 xfailed, 0 failed. Subset command as in §4
(`subset_sample.json`, `--from gather --workers 2`, 1,403 s). The report is in `results/subset/report.txt` and `report.json`.

    litolff [4, 11]  notes +4 -1 | beams -1 ~1 | ties +2 | note values ~1 | pitches ~27 | blue +18 | words +1 | clefs +1 -3 | keys -2
                     red bars 0 -> 0 | notes not written 559 -> 556 | judged (136): right->wrong 1, wrong->right 0
    brahms  [5, 14]  notes +2 -6 | rests -1 | accidentals +1 -1 | dots +1 -3 | blue +1 -1 | dynamics +1 | words -1
                     red bars 0 -> 0 | notes not written 1171 -> 1178 | judged (167): right->wrong 0

**The one right->wrong.** Tile 2.83-fix-review `tile_05`, Litolff pdf 4, part P8, bar 8. Sean's answer is "4", a quarter. The key is
`glyph/4/0/7/7/10`. On the print (`out/print/2.83-fix-review/tile_05.png`) there is ONE black head in the bottom space, with a stem up.
The detector drew TWO boxes on it:
- `/2`: the head, page y 1514-1535, 0.9 sp tall.
- `/10`: head plus stem, page y 1483-1535, 3.29 sp tall, at the same x (652 vs 653 in the cell).

The note in the file is `/2`. It is written as a quarter F4 in BOTH arms (`symbols.json`, rg `glyph/4/0/7/7/2`), so the file does not
change at this note. `/10` was never written in either arm: in OFF it was narrowed, and then given a value by `share_stem_value`.

With the flag ON, the eraser keeps the head's ink where it crosses the line. On `/10`, `notehead_ink` ink_net at the center goes
0.02 -> 0.27. `cv_stacked_head_fit` was ambiguous in OFF; in ON it decides one head at slot 7 for both `/2` and `/10`. ADJUDICATE then
refuses `/10` as `stacked_head_duplicate` of `/2`. That is what the print shows: one head on that stem.

The judged scorer counts a refusal of a keyed head as wrong, so it reports right->wrong 1. The tile's answer was about the NOTE, and the
note is still a quarter. No threshold was touched.

**Process lesson.** A judged answer keyed on a detector box id stops being a judgment of the note once a twin box exists. A reader that
correctly de-duplicates the twin then reads as a regression. A judged answer should resolve to the WRITTEN note at its place, not to the
box id it was first shown on. That would be a fix to `tools.omr.staged.judged` (its own item, not this lane).

**Not yet explained.** The file moves far less than Part 1 predicted ("about 22 readers"): on the subset it is single-digit notes, plus
Litolff pitches ~27, clefs +1 -3 and keys -2. The clef and key moves need a crop look before the full sample.

Stopped here, as the lane brief says. The full frozen sample and the 12 tiles were NOT run; that waits on a ruling about this tile.

### 5b. Coordinator ruling and the clef/key crop check (2026-10-26)

**Ruling.** `tile_05` counts as a key artifact (twin box refused as `stacked_head_duplicate`; the written note is a quarter F4 in both arms).
The scorer fix is its own item, not this lane.

**Litolff clef +1 -3, keys -2.** There are two reading changes. One crop per staff is in `out/print/2.206-eraser/clef-check/`.
- p4 system 1 staff 10, "Bassi" (P11, m16). OFF: `cv_locator` read tenor, decided. ON: ADJUDICATE narrowed it
  (`margin_below_floor`), and INFER `fill_clef_gap` gave bass (`clef_from_other_systems`, labelled). **Print: bass clef, so ON is right.**
  This one move removes three items from the file: OFF's C4 at m16, its key restatement at m16, and the F4 plus key restated at m31.
- p11 system 1 staff 5, "Tp." (Timpani, P6, m49). OFF: tenor. ON: bass. **Print: bass clef, so ON is right.**
- Keys -2: both are the key restatements that went out with the removed OFF clef changes. The value is fifths -2, unchanged. Nothing is
  read differently. (That value is already wrong on the print, Eb major = -3, but it is the same in both arms.)

Every move is right on the print, so the full frozen sample runs.

## 6. Full frozen sample (2026-10-26): STOPPED. The fix is right at the eraser, but readers downstream had their cut-offs set on the cut ink

`--from gather --workers 2`, frozen sample, 7,435 s. The report is in `results/full/report.txt` and `report.json`.

    litolff  notes +18 -164 | rests +30 -14 | accidentals -8 | flags +110 -19 | beams +4 -185 ~6 | ties +8 -4 | slurs -2 | artic -5
             note values ~508 | pitches ~17 | blue +516 -34 | words +1589 -3 | clefs +16 -6 | keys +17 -7 | meters +12
             red bars 0 -> 1289 | notes not written 2563 -> 2717
             judged (233): right->wrong 1 real (+1 twin-box artifact, tile_05, §5) | wrong->right 3
    brahms   notes +13 -17 | rests +1 -2 | accidentals +4 -6 | dots +9 -9 | flags +1 -3 | beams +5 -4 ~3 | ties +2 -4 | artic +2 -3
             note values ~3 | blue +20 -15 | dynamics +1 | words +13 -9
             red bars 166 -> 166 | notes not written 3202 -> 3209 | judged (232): right->wrong 0

**Failure 1 (the red bars): a false common-time meter on Litolff p2 system 1.** The ON file has a 4/4 change at m18 in all 12 parts.
Every later bar of the sample is then the wrong length, which gives 1,289 red bars, and the cascade accounts for most of the Litolff
lines above. On the print (`out/print/2.206-eraser/meter-check/p2_s1_staff8.png`) the header holds a treble clef and three flats, and
NO meter.

The template reader (`time_signature_locator`, NCC, floor 0.5) scores "C" on that non-meter header ink:
- OFF: 0.4927, under the floor.
- ON: 0.5317, over it.

The same thing happens on 10 staves across pp 2, 9, 10, 11 and 16 (one, p16 s0 st6, goes the other way). On p2 s1, `adjudicate_meter`
votes the system to 4/4 (`voted`). The eraser now keeps the flats' and clef's ink where they cross a line, and that ink is what the "C"
template matches. The reader was already 0.007 under its floor on ink that is not a meter.

**Failure 2 (the real right->wrong): 2.145-review tile 10, `glyph/9/0/7/3/6`, Litolff p9.** Sean's answer: an eighth rest. OFF:
refused as a notehead (`is_a_rest_shape`). ADJUDICATE read the ink component as an eighth rest (`rest8th_head_ink`):
`max_column_share` 0.90, height 2.0 sp. ON: the same component, with the line crossings kept, measures `max_column_share` 0.776 and
height 2.32 sp. The eighth-rest reader no longer fires, so the box is kept as a quarter notehead.

**Cause.** Fix A does what it says: the eraser keeps the ink it used to cut. But the readers of `image_no_staff` had their bands and
floors set on the CUT image. The meter template's 0.5 floor and the eighth-rest column-share band were both measured on ink the eraser
had been eroding. Restore the ink and their inputs change underneath them. One sits 0.007 under its floor on a non-meter; the other sits
just inside a band. No threshold was touched in this lane.

**Process lesson.** Fixing a SHARED upstream image moves the input of every reader that was tuned on the old image. Before running the
sample, such a lane must list each consumer's cut-offs and how close the OFF readings sit to them. The meter reader at 0.4927 against
0.5 was visible in the OFF record. "Who says it's right" applies to the downstream thresholds too: they were measured, on the eroded
image.

**Tiles.** lane_report drew 12 (`out/lane-report/2.206/tiles/`), but they were NOT sent. Their change draws come from a Litolff file
dominated by a meter cascade that the print already rules out.

**What it would take.** Not a threshold change here. Either re-measure the meter template's floor and the rest-shape bands on the
corrected image (their own items, with Sean's tiles), or run the corrected walk only for the readers that wanted it (2.202b's beam on a
line). The choice is Sean's.

## 7. 2.206b (2026-10-26, Sean "2. A"): the two downstream readers re-measured; the frozen sample is clean

Flags run together, all OFF by default: `OMR_ERASER_FIX` + `OMR_METER_SLOT` + `OMR_REST_OWN_STROKE`; `--from gather`; report in
`results/full/report_2206b.txt|json`; fail-fast subset (Litolff 2,9; Brahms 5,14) was clean first.

**Cause (a), meter, STAGED `gather_meter` (LEGACY `transcribe` unchanged).** The template slid over the WHOLE 16 sp header cell. On Litolff p2
the "C" matches were (i) the instrument LABEL ("Cl.", "Cor.") at x 0.2-1.0 sp, left of the barline and clef -- already scoring 0.51-0.58 with
the eraser fix OFF -- and (ii) the three FLATS at 12.6 sp, ink the clef/key already own. The eraser fix only pushed one over the 0.5 floor.
No threshold moved: `key_signature_template.claimed_header_edge` (clef template, then the chain of accidental matches, gap <= 2 sp, the
key run's own ladder) gives the x the clef+key ink ends; `locate_time_signature(x_min_canonical=)` searches right of it only; no clef found
= no bound (as before). Eraser ON: false reads Litolff p2/p10/p9/p11/p16 7/5/5/6/5 -> 0/0/1/1/1; real meters keep reading (Litolff p1 12/12,
Brahms p1 14/14, with 0.3-0.5 sp between the claimed edge and the meter's left edge on Brahms: a margin to watch on other publishers).

**Cause (b), rest, STAGED `head_rest_shape.read_head_ink`. FINDINGS 6's diagnosis was wrong.** On the corrected image the eighth-rest SHAPE
measures still pass (h 2.32 in 1.5-2.5, column share 0.78 <= 0.92, step 3.86, mass_y 0.41, left bins 0.56). What changed is the STEM finder:
with the line crossings kept it finds a "stem" `[207,479,32,232]` (min stem height is 2.0 sp) -- the rest's own diagonal, exactly the ink's
height -- and the reader's veto ("a rest owns no stem", rule 8) fires: `no_head_refused_on_the_ink`. Fix: a stem lying inside the ink's
columns and spanning its whole height (slack 0.2 sp = about half a head, which a real stem leaves sticking out) is the ink's own stroke.
The 0.2 is tuned on our two plates: it may only narrow. **Lesson:** a band measured on the old image was not what broke; print the actual
veto before re-measuring a band. Other movers in the 2.206 OFF/ON verdicts: `stacked_head_duplicate` (29 flips each way on Litolff),
unboxed-rest clusters re-keyed; no other single cut-off stood out (not a margin audit of the OFF records).

**The three measures (frozen sample, 8 + 8 pages).**
1. File: litolff notes +16 -16 | rests +5 -2 | accidentals -1 | flags +1 -2 | beams +4 -3 ~6 | ties +8 -2 | note values ~4 | pitches ~16 | blue +47 -4 |
   words +4 -5 | clefs -6 | keys +1 -7 | red bars 0 -> 0 | notes not written 2563 -> 2566.
   brahms notes +13 -16 | rests +1 -2 | accidentals +4 -6 | dots +9 -8 | flags +1 -3 | beams +5 -4 ~3 | ties +2 -4 | artic +2 -3 | blue +20 -15 |
   dynamics +1 | words +13 -9 | red bars 166 -> 166 | notes not written 3202 -> 3208. (Against FINDINGS 6: Litolff red bars 1289 -> 0.)
2. Tiles: 12 (9 changes, 3 controls) in `out/print/2.206b/tiles/sheet.png`, key `out/print/2.206b/key.json`. NOT YET SENT to Sean.
3. Judged right->wrong: litolff 1 of 233 = `tile_05` `glyph/4/0/7/7/10`, the known twin-box KEY artifact of FINDINGS 5 (written note unchanged;
   ruled an artifact there); wrong->right 3. brahms 0 of 232. Real right->wrong: 0. The 2.145 tile-10 eighth rest is no longer in the list.
   Control `OFF == record` is not available in re-gather mode (NOT CHECKED).

Flags stay OFF; not merged. Open for Sean: the tiles, then turning the three flags on together.

## 8. 2.206b tiles (Sean, 2026-10-26): four real notes lost, and why

**Tile score.** Good: 2 (half gained), 6 (a "dot" that is a tremolo slash), 10 ("words" on an eighth), 11 (beam on an eighth). BAD: 1 and 7 (Brahms p14
`glyph/14/1/9/3/4` and `/2`, dotted quarters), 4 (p5 `glyph/5/1/12/9/12`, quarter), 5 (p0 `glyph/0/0/12/1/1`, sixteenth). Tile 9 (Litolff p11 `glyph/11/1/10/11/2`) is
an improvement: OFF reads the key `-2` by markers (A3, unmarked); ON abstains `disagrees_with_part` and INFER fills `-3` (A-flat 3, blue). The print's bass key
shows three flats (agent look at the key crop; the print is the witness, not Sean's answer -- he answered the duration). Controls 3 and 8 match; tile 12's box
sits on an eighth rest, not the "cresc." word the key names (key and tile disagree, not scored). Answers: `out/print/2.206b/answers.json`.

**Cause (STAGED, ADJUDICATE; the eraser itself, not `OMR_METER_SLOT` or `OMR_REST_OWN_STROKE`).** The 2.206 eraser-only run reproduces all three
refusals (OFF decided -> ON narrowed). Tiles 1, 4, 7 are one mechanism: the stem-tip reader (`Q.STEM_TIP_INK`, `rhythm.py::_stem_tip_flag_ink`) now finds ink at the
stem's own tip that the OFF image did not show. Tile 1/7: the window's right-hand ink goes 0.215 -> 0.240 (window 0.274 -> 0.324), `window_found` false -> true,
a row `value True, hooks_reason too_little_ink`; the decider turns `head_and_marks` (dotted quarter) into `flag_ink_unread`. The ink is the slur's start at the
stem top (visible in the tile), read as a hook. Tile 4: the stem's lower tip goes from "empty" (area 0.0) to `ink_not_flag_shaped` (area 0.158), a stub where the stem
meets the staff line; `stem_tip_reads_no_beam` becomes `beam_discounted_uncertain`. Both are a cut-off crossed by a few hundredths, and both refusals are
right by rule 8 ("cannot tell") -- the notes are real and were read right before. Tile 5 is a different mechanism: its verdicts are identical in both arms
(`duration` 0.25 decided, `stem_value` 0.5 shared); ON beams two more heads onto the stem (D4, E-flat 16th) so the eighth, wrong in both (Sean: sixteenth),
is written unmarked instead of blue. That is worse by CLAUDE.md section 4 (a wrong value unmarked) and has its own cause: the second beam level at the stem end is missed.

**Process lesson.** The 2.206b re-measure fixed two readers whose cut-offs sat on the cut ink; the stem-tip window is a third, and it was not in the list because
it never produces a refusal in the OFF record -- it only abstains. Re-measuring cut-offs one reader at a time finds them only when a tile points at one: a
before/after of every verdict reason on the notes lost (this section's count) would have named it without waiting for Sean.

**Count (the saved 2.206b full-run symbol files, notes present OFF and absent ON by `rg`; the report's paired -16/-16 differs from 18/21 here because it pairs by place).**
Brahms 18 lost: 9 have the ON duration narrowed by the stem-tip/beam-ink family (`flag_ink_unread` 2, `beam_discounted_uncertain` 4, `beams_ambiguous` 3;
tiles 1, 4, 7 are in it); 4 `stacked_head_duplicate`; 2 tremolo slash (`not_a_note_mark`, right); 3 decided in both arms and dropped at export (tile 5 type).
Litolff 21 lost: only 2 are this mechanism (`beam_discounted_uncertain`); 8 `stacked_head_duplicate`, 4 `is_a_rest_shape`, 1 `is_a_beam_piece`, 3 decided in both
arms, 3 with no ON duration verdict. So the stem-tip mechanism is a Brahms problem (9 of 18); Litolff's losses are other vetoes that the ink change moved.
Not yet printed: whether the Litolff `stacked_head_duplicate` / `is_a_rest_shape` losses are real notes (no tiles). Flags stay OFF.
