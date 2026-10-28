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

## 9. 2.206c (2026-10-26, Sean "Yes"): the owner map does not cover the stem-tip ink; no reader change made

Main merged (2.205 ON, stroke map ON in both arms). Flags: `OMR_ERASER_FIX` + `OMR_METER_SLOT` + `OMR_REST_OWN_STROKE`; code unchanged, all OFF.
Fail-fast subset (Litolff 4, 9; Brahms 5, 14; `subset_2206c.json`, 1,547 s) then the full frozen sample (7,463 s, `out/lane-report/2.206c`).

**Cause (STAGED GATHER `stem_tip_window` / `stem_tip_ink`, then ADJUDICATE; the owner map has nothing to consult).**
- Tiles 1 and 7 (Brahms p14 `glyph/14/1/9/3/4`, `/2`): one stem. The Q.STEM finder box is a 4 px core (`[1247,321,4,499]`; the stem stroke is 0.245 sp = ~25 px thick; stem boxes under 10 px are 8 of 1,298 on these pages). The 2.18c window starts at the box's right edge, so it reads the stem's own right 18 px as flag density: 0.2 baseline, 0.274 OFF, 0.324 ON against the 0.30 cut-off. The shape reader abstains `ink_not_flag_shaped` in BOTH arms (area 0.163); ON only gets a `window` True. The slur's start is not in the window's ink at all. Owner coverage of the slur start: the strokes near it are blobs (0.5 and 0.68 sp, 0.25 sp thick, touching nothing but each other) that the slur box covers and `stroke_owner.shape_fit` refuses for the arc family (`blob` -> `no`, "an arc's box is mostly paper"); they are `refused_claims`, not owned. The stem stroke itself (fused with both heads) is unclaimed. So a consult of the owner changes none of tiles 1/7.
- Tile 4 (Brahms p5 `glyph/5/1/12/9/12`): the ON ink (area 0.158, arm 0.22 at 2.7 sp from the tip) is not a separate stroke: the stem stroke (box 31 px wide) holds it. No owner can own it; it is the kept line crossing fused into the stem.
- Not built: a consult flag. It would be a no-op on all three (rule 9). Two source fixes are open and are Sean's call: (a) the window's start x from the stem stroke's true edge, not the finder box (moves a reader's input, not its cut-off); (b) the arc family's claim of thin isolated fragments inside its own box (`shape_fit`, 2.205), which risks taking a real flag hook that lies under a slur box.

**Tile 5 (Brahms p0 `glyph/0/0/12/1/1`, a sixteenth; written an unmarked eighth ON).** Not a stem-tip reader. In BOTH arms `duration` decides 0.25 (two CV beam levels read) and `stem_value` (`stem_value_from_evidence`) then overrides it to 0.5: its members are G4 and `glyph/0/0/12/1/15`, a detector "notehead" of score 0.25 on the thick beam end at the stem's foot, which supplies the one level (`tip_member`). ON gains two real notes (`/1/4` E-flat 16th, `/1/5` dotted D4) that make the bar add up, so the bar sum "confirms" the wrong value and the blue flag goes. Cause: a low-score false head on beam ink is accepted as a stem member, and `stem_value_follows` overrides a head's own decided two-level read. Unfixed; a wrong value written plain.

**Step 2, every lost note by reason (full sample, `lost_notes.py`).** Brahms 18 lost: 9 the stem-tip/beam family (`flag_ink_unread` 2, `beam_discounted_uncertain` 4, `beams_ambiguous` 3), 3 `stem_value lone_head -> not_a_member`, 1 `lone_head` from `no_stem`, 2 `not_a_note_mark`, 1 `stem_agrees -> not_a_member`, 2 dropped after identical verdicts. Litolff 21 lost: `stem_value lone_head -> not_a_member` 8 (the top group), identical verdicts 5, `stem_agrees -> not_a_member` 2, `beam_discounted_uncertain` 2, no ON verdicts 3, 1 `lone_head -> decided`. Crops of the Litolff top group (agent look, not Sean's): 5 of 8 look like eighth rests the OFF arm wrote as notes (their loss is the rest fix working); 3 look like real hollow heads (`glyph/16/0/8/0/8`, `glyph/6/1/11/9/0`, `glyph/8/1/6/3/3`). Needs tiles before it is a count.

**Three measures (same as section 7: owner ON changed nothing).** File: litolff notes +16 -16, rests +5 -2, ties +8 -2, blue +47 -4, red bars 0 -> 0, notes not written 2563 -> 2566; brahms notes +13 -16, dots +9 -8, blue +20 -15, red bars 166 -> 166, notes not written 3202 -> 3208. Tiles: `out/print/2.206c/tiles/sheet.png`, key `out/print/2.206c/key.json`. Judged right->wrong: litolff 1 (`tile_05` `glyph/4/0/7/7/10`, the twin-box artifact ruled in section 5), brahms 0; real 0.

**Process lesson.** "Consult the owner" presumes the owner map covers the ink; before building the consumer, print the strokes in the reader's window with their owner state. Two of three cases had no owned stroke there, and the third case's cause was the finder's stem width, upstream of both.

## 10. 2.206d (2026-10-27, Sean "Yes" 2026-10-26): the tip window starts at the stem's stroke; `OMR_STEM_TIP_TRUE_EDGE` (OFF)

**Cause (STAGED GATHER, `_observe_stem_tip_ink`).** The finder says WHICH stroke a stem is; it was also trusted for how wide. 133 of 4,336 Brahms stem boxes are under 10 px
(Litolff 31 of 4,258) on stems whose stroke is ~25 px; the 2.18c window started at that core's edge and counted the stem's own side. Fix (flag-gated, OFF): `stroke_map.stem_true_edges`
reads the stem stroke's width from its mask on the rows 1.5 sp away from either end (L7), refused above 0.7 sp (fused); the window starts at `min(core, stroke)` edges. Tile 4 is a
different case: its finder box equals the stroke (29 px); the ON ink is a kept line crossing fused into the stem 2.7 sp from the tip. Rule (L15, one in the same flag): ink that first
touches the stem beyond 1.6 sp (the reader's own widest root) over a clean tip is not a stroke that starts at the tip -> `found False`, `why root_beyond_tip`. Crop look at 12 of the
~130 `ink_not_flag_shaped` rows with t_first > 1.6 on the subset: 12 of 12 the far end of a stem with a staff or ledger line crossing 2.8-3.3 sp back, no flag (agent look, not Sean's).
**Process lesson.** A finder box is a location, not a measurement of the thing; every reader that took x0/x1 from it inherited the core. Per-plate stem thickness (idea, not built): stroke
thickness is quantised to 1/16 sp; page medians differ by one step (Brahms 0.19-0.25, Litolff 0.25-0.31) and p10-p90 within a page spans two steps, so a per-page constant is good to about
+-6 px, worse than the per-stem measurement.

**Lost notes by reason (full sample, ON all four flags, `lost_notes.py`).** Brahms 14 lost (was 18): beams_ambiguous 3 (p4 `glyph/4/1/13/5/*`), beam_discounted 2, stem_value
lone_head -> not_a_member 3, two decided notes read as not_a_note_mark 2, identical 2, other 2. Tiles 1, 7 (p14) and 4 (p5) are kept (were lost). Litolff 21 lost, unchanged: the
8-note `stem_value lone_head -> not_a_member` group is on `out/print/2.206d-lost/sheet.png` (key `benchmarks/staff-eraser-2026-10/results/2.206d-lost-key.json`), answers pending.

**Three measures (frozen sample, all four flags ON vs OFF).** File: litolff notes +25 -16, rests +5 -2, ties +8 -2, blue +50 -4, red bars 0 -> 0, notes not written 2566 -> 2560;
brahms notes +50 -12, dots +36 -5, ties +30 -4, slurs +8, blue +21 -52, words +10 -33, wedges +3, red bars 165 -> 164, notes not written 3203 -> 3168. Tiles `out/print/2.206d/tiles/sheet.png`,
key `out/print/2.206d/key.json`. Judged right->wrong: litolff 1 (`tile_05` `glyph/4/0/7/7/10`, the known twin-box artifact, same as 2.206c), brahms 0.
The Brahms gain (+50 notes against +13 at 2.206c) is not yet looked at: the tiles are the check. Fast tier: 3 failures, none new in kind (two flag-doc tables name the OFF branch flags, one judged-index).

## 11. 2.206d answers (2026-10-27, Sean): tiles and the lost-note sheet

Answers: `out/print/2.206d/answers.json` (his 9-20 = tiles 1-12), `out/print/2.206d-lost/answers.json` (his 1-8). Flags all four ON vs OFF.

**12 tiles.** Good 3 (1 litolff eighth gained, 5 dotted quarter gained, 8 eighth gained); right->wrong 1 (tile 9 brahms p19 `glyph/19/0/13/0/8`: Sean "dot 8", OFF dotted eighth, ON dotted 16th `begin/begin`);
controls 3 match (7, 10, 12); neutral 5: 2 (eighth rest both arms, ON drops the blue), 11 (eighth both arms, ON adds blue), 6 (dotted quarter both arms, the gained tie not judged), 3 (Sean: eighth; OFF wrote a
wrong quarter, ON writes no note there, the 'does not add up' words are gone), 4 (undecidable). **Crop defect:** tiles 4 and 7 cut the stem short ("can't see the bottom of the stem", "stem is cut off"); the crop
padding at the stem foot is too tight, so those two answers carry no weight (7 matches anyway). The one right->wrong (beam 9) is the new count to look at before any flip: ON reads a second beam level on a dotted eighth.

**Lost sheet (litolff `stem_value lone_head -> not_a_member`).** Real half notes 4 (1, 2, 4, 7); correctly dropped 4 (3, 5, 6, 8: "part of a 4 rest"), so the rest fix is working on those.
**The 4 half notes are not lost.** Cause (STAGED ADJUDICATE `notehead_is_not_a_notehead`): the stem exists in both arms (same stem box, `head_stem one_stem`, `duration` half decided in both). The head's verdict flips
False -> True `stacked_head_duplicate` ON; the glyph has two candidate boxes at one slot (`candidates_at_slot` 2, `shape_contenders` 2; two with margins -0.003..-0.026, two hollow-class with no margin), the ON arm chooses the
other box as the head, and this one becomes the duplicate, so `stem_value` abstains `not_a_member` (a consequence, not the cause). Neither the eraser cut the hollow head nor the stem: ON exports a half note from the twin box
(`glyph/16/0/8/0/9` G4, `glyph/6/1/11/9/2` B-12, same pitch as OFF; `glyph/16/1/3/1/3` E-14 vs OFF D4, `glyph/8/1/6/3/1` A4 vs OFF B4) at the same place. So the "lost" count is an identity swap between twin boxes, with the
twin's own pitch: two of four (tiles 4, 7) change pitch (D4 -> E, B4 -> A4), unjudged; a print check of those two pitches is the open question. **Process lesson:** a lost-by-rg list counts identity, not music; match
lost notes to gained notes by position before calling any a loss.

## 12. 2.206d tile 9 (Brahms p19 `glyph/19/0/13/0/8`): why ON reads a dotted 16th (2026-10-27)

**Cause (STAGED, GATHER `line_detection.detect_beams` -> ADJUDICATE `rhythm._beam_levels`; the eraser is the trigger, not the culprit).** One flag only: with each of the four flags ON alone on p19
(`--from gather`, p19 + context page 0), `OMR_ERASER_FIX` alone gives `16th begin/begin`; `OMR_METER_SLOT`, `OMR_REST_OWN_STROKE`, `OMR_STEM_TIP_TRUE_EDGE` each give `eighth begin` = OFF. Not the tip window, not a remnant.
Mechanism, from the records (cell `cell/19/0/13/0`, stem x 1310, head centre x 1353): in a dotted-eighth + 16ths group the primary beam starts at the dotted eighth's stem (x 1309) and the secondary starts at the first 16th's stem (x 1532).
OFF: the overcut eraser (§Cause) bites the lower edge of the primary beam's left section (staff line y 374; a comb of white slits, `out/print/2.206f-beam/cell_crops.png` panel 2), the component breaks, and the finder emits
two strokes with their own x extents: primary `[1318,395,602,59]`, secondary `[1532,342,385,57]`. ON: the beam is whole (1,890 px kept, red in panel 4), primary and secondary are ONE connected component; `_stacked_bar_bands` splits it into two y bands, and `_emit`
gives EVERY band the component's full x extent: both strokes `[1309, .., 611, ..]`. `_beam_levels` counts strokes whose box covers the head's column (the `OMR_BEAM_LEVEL_NEEDS_A_JOINED_STEM` test is OFF): 2 covers the head at 1353, level 2. The stem's own reader
`beam_stem_levels` (stem 1310, bottom, right) says ONE level in both arms and is not consulted; `beam_stem_join` joins the dotted eighth to the primary only (the upper stroke has no join row), same in both arms. The neighbour (first 16th, `glyph/19/0/13/0/5`)
also moves `continue/begin` -> `continue/continue` (same stroke): one mechanism, two notes. So OFF was right by accident: an overcut separated what a shared-x band split cannot.

**How many others.** Value changes ON vs OFF on the full sample (`out/lane-report/2.206d/work` symbols): litolff 12 notes change type or beam state, none gains a level by value (3 lose one: p2, p6 x2; p9 gains the first beam, right); brahms 8, of which exactly 1 value gain
of a level (this note) and 1 beam-state change on its neighbour. Stroke records (cv_lines `beam_stroke`, ON vs OFF, ON stroke with the same right end and x0 >30 px further left): litolff 4 cells, brahms 7 cells (12 strokes). Crop look at 6 of the brahms cells
(`out/print/2.206f-beam/widen.png`, OFF blue / ON red on the original ink; agent look, not Sean's): the same shape in 4 (p19 `0/13/0`, p4 `1/13/5`, p12 `1/10/0`, p0 `0/0/12/1`: a secondary or short bar drawn the full component length from the left, where the real bar starts later), the box merely equal in 2 (p5, p19 `0/3/0`).
Only p19 `0/13/0` turned a decided value wrong; the others show as lost/changed beam state, unjudged.

**Process lesson.** A stroke finder that splits a component into stacked bars must give each bar its own x extent: the stroke's x is the evidence `_beam_levels` counts by, and a bar that does not exist at a stem's column cannot be a level there. A correct upstream change (whole beam) exposed a
latent downstream assumption that had been satisfied by damage; "ON worse on one tile" can be the old arm right for the wrong reason. Check the finder's output geometry before any reader cut-off.

**Proposed fix (not built).** In `detect_beams._emit`, trim each stacked band's x extent to the columns where THAT band's rows carry ink (coverage >= `BEAM_RESCUE_BAND_COVER` over a one-thickness run, ends rounded to the nearest stem if any), so a secondary bar starts at the 16th's stem and a primary at the dotted eighth's;
flag-gated (new flag, GATHER, OFF), same OFF/ON frozen-sample report, tiles on the 4 shapes above. Alternative at ADJUDICATE (`_beam_levels` consulting `beam_stem_levels` as a second witness) is rejected first: the same ink read twice is not a second witness.

## 13. 2.206e pitch sheet answers (Sean, 2026-10-27)

Crop 1 (litolff p16 P4 bar 240) "Eb"; crop 2 (litolff p8 P8 bar 115) "A natural". Both match eraser ON (E-flat4 vs OFF D4; A4 vs OFF B-flat4 blue): the keeper the eraser path picks from the twin boxes is right on both pitches. Answers `out/print/2.206e-pitch/answers.json`.

## 14. 2.213 (2026-10-27, Sean "Yes"): a beam bar's x extent from its own ink; `OMR_BEAM_OWN_EXTENT` (OFF)

**CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED.** Assumed: a secondary beam spans only the notes it serves, so its ink starts and stops at their stems. Falsified by a print where a secondary bar is drawn
from a stem that has no second flag/beam. Not confirmed by Sean beyond the tile 9 answer ("Dot 8"). The tiles on the cells below are the check.

**Cause and lesson** are §12 (GATHER `detect_beams._emit` gave every stacked band the component's x extent; the eraser fix only exposed it). Fix (STAGED GATHER, shared `line_detection`): per band, a column belongs to the bar where the bar has a vertical
run at least 0.6 of its median thickness (`_bar_own_extents`); the box is the first..last such column. Single-bar components and unmeasurable bands are untouched (full extent). Test
`test_line_detection_beam_own_extent_2_213.py` fails OFF (secondary starts at the first stem), passes ON. Limits: a stack whose secondary is under half the component's width reads one bar (`_stacked_bar_bands` median), so is not trimmed; ink bleed joining the two
bars is given to the primary, so a secondary starts where the two are separate again.

**Three measures** (frozen sample, four eraser-path flags ON in BOTH arms, only `OMR_BEAM_OWN_EXTENT` differs; `results/2.213-report.txt`). File: litolff NOTHING changed (5,038 paired); brahms notes -1, flags +3, beams -4 ~2, slurs +1 -1, note values ~2, blue +1,
dynamics +2 -2, words +5 -3, red bars 164 -> 162, notes not written 3168 -> 3169. Judged right->wrong 0 (litolff 233 judged tiles, brahms 232). Tiles `out/print/2.213/tiles/sheet.png` (12, taller/wider via `recrop_tiles.py`), key `results/2.213-key.json`.
Tile 9 of 2.206d (`glyph/19/0/13/0/8`) is now an eighth, begin (OFF-arm dotted 16th gone), its neighbour `13/0/5` `continue/begin`.
**Lost notes (1):** Brahms p19 `glyph/19/0/12/0/5`, 16th C4: `duration` decided `head_and_marks` -> narrowed `beam_certain_not_joined`; the dotted-eighth beside it (`12/0/21`) goes 16th -> eighth: the same shape as tile 9 on the next staff, so the lost note is the neighbour's
second-level evidence now missing. Marked, not wrong. **Unexplained:** words/dynamics +/- (tiles 1-3, 11) on Brahms p14, p19 are not beam readings; ink the beam bar no longer claims or gather noise -- the tiles decide.
**Proposal only (not built):** `beam_stem_levels` (the stem's own reading) disagreeing with `rhythm._beam_levels` should NOT be a second witness for the level: both read the same raster ink. It could be a refusal-with-margin (record the disagreement, narrow rather than decide), which is a 2.153-family change for its own item.

## 15. 2.213 tile answers (Sean, 2026-10-27)

Answers `out/print/2.213/answers.json`, key `results/2.213-key.json`. Values read from the lane-report records (`out/lane-report/2.213/work`, ON = `OMR_BEAM_OWN_EXTENT=1`).

| tile | Sean | OFF -> ON written | verdict |
|---|---|---|---|
| 7 `glyph/19/0/12/0/21` | Dot 8 | dotted 16th -> dotted eighth (dot, flag eighth, blue) | good |
| 10 `13/0/8` | Dot 8 | dotted 16th -> dotted eighth | good (the 2.206d tile 9 right->wrong is repaired) |
| 5 `12/0/5` | 16 | plain 16th -> NOT WRITTEN: duration narrowed `beam_certain_not_joined`, candidates eighth (0.5, 1 beam) and 16th (0.25, 2 beams), both support 1.0, no margin; not written blue | right->gone (BAD, marked not wrong) |
| 8 `13/0/5` | 16 | 16th -> 16th, beam sub continue/continue -> continue/begin | value unchanged, matches |
| 4 | 16 | 16th both (beam -> flag) | unchanged, matches |
| 6, 12 | 8, 8 | eighth both | controls match |
| 1, 2, 3, 9, 11 | Dot 4, 4, 4 rest, Dot 4, Dot 4 | host note identical both arms, all match except 3 | not judged |

Score: 2 good, 1 right->gone, 0 right->wrong, 2 controls match. Judged right->wrong stays 0 but tile 5 is the neighbour-staff loss already named in 14: the dotted-eighth fix on `12/0/21` removes the second-level beam evidence for `12/0/5`, whose own stem now shows a certain conflict (`certain_conflicts` 1, `levels_certain` 2).

**Tile-maker defect (named, not fixed):** for words and dynamics the changed symbol is a bar-level mark with no ink of its own; `tools/omr/staged/lane_report.py` `place()` (lines 340-345, via `boxes[rg]`, called for the text kinds at 367-376) gives it the HOST note's box, and `benchmarks/staff-eraser-2026-10/recrop_tiles.py` draws that box (`b = [it["box"]...]`), so the orange box sat on a note and Sean answered the note. "does not add up: ..." words are our own bar-check annotation (`export.py` `RED_BAR_WORD_PREFIX`, 2.173), not print text, so no tile of them can be answered from the page. Tile 3: both arms write a quarter note (`glyph/14/1/0/0/5`) where Sean reads a quarter rest, pre-existing and not 2.213.

## 16. 2.213b (2026-10-27): tile 5 `glyph/19/0/12/0/5` lost with `OMR_BEAM_OWN_EXTENT` ON; the trim stopped short of the stem

**Cause and process lesson (STAGED GATHER, `line_detection._bar_own_extents`).** Records, cell `cell/19/0/12/0` (cv_lines `beam_stroke`, OFF vs ON): OFF both bars `[1305,..,624]`; ON primary `[1305,..,621]`, secondary `[1580,522,346,61]`. The first 16th's stem is at x 1545-1556, so the
secondary began 35 px (3 stem widths) short of the stem it serves, and `rhythm._beam_levels` / the stem's join no longer agreed (`beam_certain_not_joined`, candidates eighth/16th, no margin, not written). Hypothesis (thin tapered end cut by the 0.6 x median rule) was WRONG: the run profile of the
component (dump of the labelled mask, `out/print/2.213b/dump_1305_476_0.npz`) shows the secondary at full thickness (38-39 px, median 39); instead x 1545-1580 is ONE merged run of 73-82 px (primary + secondary + bleed at the stem's foot, no white between), which the finder gives to the nearer-centre bar
(the primary), so the secondary "starts" where the bars part again (1585). Lesson: a per-bar extent derived from runs is blind exactly where bars touch, and bars touch exactly at stems; the stem is the second witness (a different ink: the stem finder), a threshold on thickness was not the axis. The 2.213
fix removed one defect (extent too long) and exposed its mirror (too short); both come from reading a bar's end off a mask where it is merged.
**Fix (same flag, `_emit`'s trim only).** Walk each bar's end outward across the columns bridged over its own centre (one run covering two bars' centres); if an anchor stem stands inside that bridged stretch the end is the stem's near edge; no stem in the bridge, no extension (the 2.213 fixture bleed,
tile 9, is unchanged). On the cell: secondary `[1545,..]`. Tests `test_line_detection_beam_own_extent_2_213.py`: the tile 9 test passes unchanged; new test for tile 5 (fixture fails at 461 without the extension, passes at 301 with it).
**Three measures** (frozen sample, same arms as §14; `results/2.213b-report.txt`). File: litolff NOTHING changed (5,038 paired); brahms notes 0 (6,555 paired, was -1), beams ~4, note values ~2, blue -1, words -2; notes not written 3168 -> 3168 (was +1), red bars 164 -> 162. The lost note is back (p19 `12/0/5` 16th C4 written, ON =
OFF); `12/0/21` and `13/0/8` still dotted 16th -> dotted eighth (both Sean "Dot 8"). Judged right->wrong 0 (litolff 233, brahms 232), right->gone 0. Words/dynamics diffs of §14 are gone. Tiles `out/print/2.213b/tiles/sheet.png` (12: 4 changes on note/beam/flag/value, 8 controls; only 3 changed value/beam symbols exist
on the sample, so the sheet is mostly controls), key `results/2.213b-key.json`, made by `tiles_2213b.py` (lane_report's diff and picker, words/dynamics excluded). Other ON-vs-OFF lost-level changes on the sample: none (no new `beam_certain_not_joined`).

**Sean's tiles (2026-10-27, `out/print/2.213b/answers.json`).** 12 of 12 match the ON (`OMR_BEAM_OWN_EXTENT=1`) written value, checked against the lane-report records: tiles 1 and 4 (`12/0/21`, `13/0/8`) "Dot 8", OFF dotted 16th wrong, ON dotted eighth right (2 good); tile 5 `12/0/5` "16", 16th both arms, so the note lost in 2.213 is written again; tile 2 `13/0/5` "18" (typo; Sean confirmed 16) 16th both arms, only the beam sub changed; controls 3, 6, 7-8, 9, 10, 11, 12 ("8", "8", "8", "Dot 4", "2", "Dot 4", "4") all equal what is written, the dot present on both dotted quarters (9, 11). Judged right->wrong 0, right->gone 0.

## 17. Eraser path, all five flags ON vs main defaults (2026-10-27, Sean approved)

Run: `python3 -m tools.omr.staged.lane_report --flag OMR_ERASER_FIX --flag OMR_METER_SLOT --flag OMR_REST_OWN_STROKE --flag OMR_STEM_TIP_TRUE_EDGE --flag OMR_BEAM_OWN_EXTENT --from gather --workers 2 --out out/lane-report/eraser-path` (the tool takes repeated `--flag`, each OFF=0 / ON=1; both arms re-gathered through the detector cache, 7,281 s; on main merged at 04eef97c1). Report `results/eraser-path-report.txt`. Control gap: re-gather mode has no saved verdicts, so OFF==record is NOT CHECKED.

**1. File changes (frozen sample).** litolff (5,026 -> 5,038 notes+rests, 5,013 paired): notes +24 -15, rests +5 -2, accidentals +2 -1, flags -2, beams +5 -4 ~7, ties +8 -2, slurs +3 -1, note values ~5, pitches ~18, blue +50 -4, words +4 -8, clefs -6, keys +1 -7; red bars 0 -> 0; notes not written 2566 -> 2560. brahms (6,518 -> 6,555, 6,505 paired): notes +48 -10, rests +2 -3, accidentals +13 -4, dots +34 -3, flags +3 -3, beams +4 -4 ~3, ties +30 -4, slurs +8, articulations +3 -3, note values ~3, pitches ~2, blue +23 -50, dynamics +1, wedges +3, words +9 -32; red bars 166 -> 163; notes not written 3203 -> 3168.
**2. Judged.** right->wrong 0 and right->narrowed/gone 0 on both plates (litolff 233, brahms 232 judged tiles on these pages); wrong->right 3 (litolff). Not separated by flag: one combined arm, so a flag's own share needs the per-flag reports (§10-16).
**3. Blind tiles.** `out/print/eraser-path/tiles/sheet.png`, key `out/print/eraser-path/key.json` (copy `results/eraser-path-key.json`), made by `tiles_eraser_path.py` (the 2.213b script, note/rest/beam/flag/value/pitch/dot kinds only; words and dynamics excluded because lane_report boxes them on the host note): 9 changed (4 notes gained, 2 dots, 1 beam, 1 pitch G3 -> C3, 1 rest) and 3 controls. Unanswered.
