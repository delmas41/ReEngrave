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

PENDING (the box was busy with 2.204's gather and < 15 GB free when Part 1-3 were done).
