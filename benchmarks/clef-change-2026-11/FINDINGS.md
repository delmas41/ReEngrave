# ROADMAP 2.251 -- a clef change inside a system (STAGED)

CONVENTION ASSUMED: a clef change is a clef glyph on ONE staff, at or just before a barline or before the first note it governs, often smaller than the header clef (many are full size on these plates). It holds until the next printed clef; a new system reprints it in its header.
WHAT WOULD FALSIFY IT: a cautionary clef that governs nothing, or a change that applies to more than one staff.
NOT CONFIRMED by Sean.

## 2026-11-01: cause and count (lane-2.251-clef-change aafba4088; nothing built)

Recorded by the manager from the lane's report: a hook refused the lane's own write of this file. The crops and counting scripts (`mxl_clefs.py`, `barmap.py`, `crops.py`, `sheet.py`, `boxes.py`, `cost.py`) are on the lane branch.

**Cause.** The pipeline has nowhere to put a clef change:
- `Q.CLEF` holds one clef per staff per system. No reader on either path looks for a clef past the header: `gather_clef` and the CV locator read cell 0 only.
- `claims.py` `CLEF_WINDOW_SPACES` deliberately narrows any clef box outside the first bar, so the change's ink has no claim.
- EVALUATE `restate_pitch` pitches every head on the staff from the one header clef.

The detector gap is second, and it is a Litolff C-clef problem:
- Mid-system F clefs: 13 of 15 are boxed `clefF`.
- Mid-system C clefs: 0 of 9 are boxed as a clef. They come out as heads, whole rests, double sharps or `arpeggiato` (2.245 r2 tile 9 was one).
- Brahms boxed both kinds (bar 76 `clefCTenor` 0.87; bar 89 `clefF`).

**Process lesson.** This gap was written down four times, each time as "outside the fence", and never got a ROADMAP row:
- the gather.py ~12940 comment;
- omr-staged-c-clef-2026-09 §11;
- omr-clef-gap §6;
- omr-clef-string-staves.

Our measures cannot see it: judged tiles carry no pitch, and the fault shifts a whole staff segment by one interval. Two rules follow:
- A "not my fence" finding gets a ROADMAP row the same day.
- A quantity's scope (one clef per staff per system) is a claim about the page and needs a print check.

**Count.** The reference MXL lists every change, `barmap.py` maps each bar to page/system/cell, and the print is cropped there with nothing of ours drawn. A change printed in a system's header is not counted, because that clef is read today.
- **Litolff: 32 confirmed inside a system.**
  - Bassoons, 27: bars 36, 38, 102, 107, 110, 111, 114, 115, 146, 159, 211, 228, 282, 303, 315, 319, 323, 346, 351, 387, 390, 396, 411, 470, 476, 483, 501. Bars 159, 228 and 303 are mid-cell-0, after the header.
  - Celli on their own `Vcl.` staff, 5: bars 94, 154, 331, 346, 411.
  - Header clefs, not counted: bars 83, 130, 274, 398.
- **Brahms: at least 7 confirmed** (bars 18, 20, 46, 50, 76, 89, 97) of about 50 that the encoding lists (bassoons 37, cello 7, viola 4, horns 2). Not every place was looked at: the bar map drifts by up to 5 bars on Brahms (516 vs 511), and sheets B-fag-2..6 were rendered but not read.
- Crops are in `out/print/2.251-count/` on the lane branch. `L-fag-0.png` was checked by the manager: tenor and bass changes in the bassoon lines at bars 36, 38, 102, 107, 110.

**Detector at each Litolff change:**
- `clefF` box: 94, 107, 154, 159, 228, 282, 315, 323, 476, 501.
- Bass clef with no clef box: 38 (heads), 111 (head + `keyFlat`).
- C clef, never boxed as a clef:
  - 36: `restWhole` + head;
  - 102: `arpeggiato` + 3.4 sp head;
  - 110: 5.0 sp-tall head + stem;
  - 146: double sharp;
  - 211: `restWhole` + 3 heads;
  - 303: double sharp + head;
  - 319: double sharp + half head;
  - 483: slur / half head / `dynamicF`;
  - 331 (Vc): `arpeggiato` + head.

**Cost.** On the 9 Litolff slice pages, 181 head boxes (score >= 0.5) sit after a missed change and before the next printed clef. Every one is pitched from the header clef (bass vs tenor: a fifth apart at one position). Brahms cost was not computed.

**Prior work.**
- LEGACY `clef_correction.veto_implausible_clef_changes`: a per-staff carry with a veto table (Violin treble->bass, Viola alto->bass), on READ identity only. Bassoon and cello changes pass it.
- LEGACY export `_first_clef_bearing_measure`: writes one clef per staff, because a per-measure clef that was only carried, not read, writes false changes. A carried clef must stay distinguishable from a read one.
- groups.py ~852: "A CLEF CHANGE IS REAL MUSIC". A minority clef is only suspicious, never vetoed.
- `clef_geometry` / `clef_locator`: the readers to reuse for which clef.
- claims.py 2.144/2.181: a clef box at a later bar was narrowed on purpose, because of real eighths and rests inside false `clef*` boxes. A box alone must not claim; it needs a second witness from geometry, size and staff position.
- ink-rules clef rows (`is_a_clef`, `claimed_by:clef`, `fill_clef_gap`) are header-only. page-facts §5, page-facts and DECISIONS have no ruling on clef changes.

**Open design question (to Sean).** Carrying a change to the following notes means `restate_pitch` (EVALUATE) reads the clef in force at each head's x. That needs a new gathered quantity (change, x, kind) and an adjudicator that reuses the clef readers. A change that is seen but whose kind cannot be read marks the heads after it red until the next printed clef. Every test is GATHER + ADJUDICATE only (Sean 2026-09-30), so: does 2.251 include the EVALUATE carry, or stop at "claimed, kind read, heads after it marked unread"?

## 2026-11-01: build round 1 (lane-2.251-clef-change 3254ce233; both flags default OFF)

Recorded by the manager from the lane's report (a hook refuses the lane's own write here). Scripts `pitchwit.py`, `tiles.py`, `scan.py`, `ftest.py`, `inspect_rec.py` and logs in `results/` are on the lane branch.

**Step 1, `OMR_CLEF_PAGEWIDE` (STAGED GATHER `gather_clef_pagewide`, `clef_pagewide.py`).**
- C clef: two witnesses with no detector box -- a thick bar (0.45-1.3 sp wide, unbroken >= 3 sp, stops near the staff) and two mirrored bowls; kind from the header locator's symmetry axis snapped to the line at the clef's own x. Kind read only as alto or tenor; otherwise claimed with kind unread.
- F clef: a clef-sized `clefF` box plus a dot pair straddling line 4. The looser dot test passed a false `clefF` box over a half note on Brahms p25.
- A G clef inside a system is never claimed (no second witness built).
- Off-line over all 16 Litolff pages: 18 C clefs inside a system, no false positives once the bowl fill floor was 0.3 (before: a meter digit p1, a bar fragment p5).

Subset (Litolff 2,4; Brahms 4,5), not the frozen sample:
- Litolff p4: claimed bar 36 tenor, 102 C kind unread, 110 tenor, 107 bass. Missed: 38 and 111 bass (no box), 94 cello F (dots name no line).
- Brahms: 3 C changes claimed; 3 bass clefs missed (thick staff lines break the dots).
- Litolff `claim_readout` clef/key/meter ink 2.2% -> 2.3%; ORDER-VIOLATION 0.46% -> 0.45%; SPLIT-ACROSS-CLAIM 0.77% -> 1.00% (wrong direction: new claims over C clefs the stroke map had already cut; open). Brahms readouts not run.
- File: Litolff notes -2, words +1; Brahms notes -4, rests -1, dots +-1. Judged right->wrong 0, unwritten->wrong 0 (188 and 174 tiles).

**Step 2, `OMR_CLEF_CARRY` (EVALUATE `restate_pitch`, EXPORT).**
- A head is pitched from the last clef printed before its x on its staff (`position_and_clef_change`); a system header resets it; after a change whose kind is unread the head gets no pitch.
- Litolff: notes -14 (p4 bars 103-106, after the bar-102 unread C clef), dropped and counted but NOT marked red (red bars 0 -> 0) -- breaks CLAUDE §4. Brahms: pitches ~71, clefs +5. Judged right->wrong 0 on both.
- Pitch witness (written pitch among the encoded bassoon pitches of that bar), re-pitched heads: Litolff ON 14 / OFF 16 of 53; Brahms ON 33 / OFF 21 of 92 (Brahms bar map drifts).

**Cause of the Litolff loss.** Missed return clefs (bass clefs the detector never boxed, bars 38 and 111): the carry moves the error from "after a missed change" to "after a missed return".

**Process lesson.** A carry needs return-clef recall at least as high as change recall -- measure the returns before carrying.

**Before step 2 can land:** export marks the notes after an unread clef red; bass-clef recall rises (an F-clef shape reader with no box, Brahms dots) or the carry stops at any clef-shaped candidate; the frozen sample is run.

## 2026-11-01: Sean's step-1 tiles (answers-r1.json)

- Claims: 8 of 9 right (C clefs 1-4, 6, 7 -- including tile 6, the bar-102 C clef whose kind we left unread; F clefs 10, 12). Wrong: tile 5, a header G clef (Litolff p6 s0 staff 5) claimed as a C clef, kind unread -- the G clef's loops passed as bowls despite the spine filter. Sean: the box is "a little off" there and on tile 8.
- Refusals: 8 (G clef) and 9 (barline) right; 11 is a real F clef refused for broken dots (Brahms).
- Tile 10: the F-clef claim area also holds a quarter rest -- the claim must not take the rest's ink.
- Round 2: no C claim on a G clef (and none at a header where a READ G clef stands); trim the claim area to the clef's own ink; Brahms F-clef dots.
- Correction (Sean, same day): tile 5 is a C clef. Claims are right 9 of 9; round 2 is only the Brahms F-clef dots (tile 11) and the rest inside tile 10's claim area.
- Correction withdrawn (Sean, same day: "Sorry - 5 is a G clef"): claims right 8 of 9; round 2 also covers the G clef claimed as a C clef (tile 5).

## 2026-11-01: round 2 sent (Sean "Send clef lane back")

Same lane, same branch. Scope: (1) tile 5 -- no C claim on a G clef, and none where a READ header clef of another kind stands; (2) tile 10 -- trim each claim area to the clef's own ink (a rest inside it must stay unclaimed); (3) tile 11 -- a Brahms F-clef dot reader that survives thick staff lines, with the Brahms p25 false `clefF` over a half note kept as a failing twin; (4) why the box sat "a little off" on tiles 5 and 8; (5) if small, notes after an unread-kind clef MARKED red, not silently dropped. The carry (step 2) stays OFF. 12 new tiles in `out/print/2.251-r2-tiles/`.

## 2026-11-02: round 2 built (lane-2.251-clef-change 32c3f12c1; both flags still OFF)

Recorded by the manager from the lane's report.

**Cause of all three faults.** Each witness was set from one plate's numbers and one glyph's usual shape, never tested against the confusable neighbour: a G clef's spine and loops, a rest inside a detector box, Breitkopf's thick lines touching the dots. **Lesson:** a shape witness ships only with its twin test. Each fault is now a real-page twin test (slow tier, `tests/test_clef_pagewide_r2_pages.py`, 4 pass).

1. **Tile 5 (G claimed as C).** A small G clef's spine passes the thick-bar test and its loops fill the bowls. Fix: a G-tail witness (ink 0.6-1.6 sp below the bottom line beside the spine, fill >= 0.3, lines measured at the clef; Litolff header G 0.42-0.56, every C <= 0.15), and no C claim may overlap a clef-sized `clefG`/`clefF` box or a READ claim by >= 0.2. All 18 C clefs inside a system still pass; tile 5 is not claimed.
2. **Tile 10 (rest inside the F claim).** The `clefF` box already held the rest's right half, and the claim added 0.8 sp to the right. The F claim is now its body plus its dot pair; a C claim ends at the first gap > 0.35 sp. Claim and tiles use one area function.
3. **Tile 11 (Brahms F refused).** Thick lines and a stem fuse the dots. The dot window clears columns holding a raw run >= 1.8 sp; the witness is the dot pair straddling line 4 nearest the box's right edge (the old rightmost pair was a key flat's bowl on Brahms headers). Brahms bass readings 45 -> 61, Litolff 22 -> 40 (every Litolff in-system one at a print-confirmed bar). Both Brahms p25 false `clefF` boxes still refused.
4. **"Box a little off" (tiles 5, 8).** The claim's geometry (a C-shaped area on a G clef), not the drawing.

Bars after an unread-kind clef now carry a red "clef?" (`unread_clef_bars`; Litolff p4: 5 bars after bar 102).

Subset (Litolff 2,4; Brahms 4,5): PAGEWIDE only -- Litolff notes -2, words +1; Brahms notes -4, rests -1, dots +-1. Both flags -- Litolff notes -14, pitches ~16, words +9 (5 red "clef?"), clefs +2; Brahms pitches ~69, clefs +6. Judged right->wrong 0 and unwritten->wrong 0 on every arm. Fast tier 9674 passed. Not run: claim_readout / claim_order, the frozen sample. The carry is unchanged (pitch witness Litolff 14 vs 16 of 53; Brahms 33 vs 21 of 92): bass clefs with no detector box (Litolff bars 38, 111) need a reader before it can land.

Tiles: `out/print/2.251-r2-tiles/` (seed 22512) -- round-1 places 5, 10, 11 as handled now, plus 9 fresh (4 C inside a system, 2 Litolff F, Brahms F bar 97, 2 near-misses, 1 header control).
- Sean's round-2 tiles (2026-11-02, `answers-r2.json`): **12 of 12 right** -- 9 claims (C 3, 9, 11, 12; F 4-7, 10) and 3 refusals (G clefs 1, 2; barline 8). The round-1 faults hold fixed at their places (tile 1 = r1 5, tile 4 = r1 11, tile 5 = r1 10).

## 2026-11-02 -- landing gate: claim readouts on the round-2 code, flag OFF vs ON (2-page subset, saved-nothing: fresh `--through gather`)

Litolff pages 2,4 and Brahms pages 4,5, `claim_order` / `claim_readout` on a fresh GATHER with `OMR_CLEF_PAGEWIDE` 0 vs 1 (the Litolff OFF arm reproduces round 1's base exactly: ORDER-VIOLATION 0.46, SPLIT 0.77).

| plate | clef/key/meter single-owner ink | ORDER-VIOLATION | SPLIT-ACROSS-CLAIM |
|---|---|---|---|
| Litolff OFF -> ON | 2.2% -> 2.3% (register-claimed 3.1 -> 3.4) | 0.46% -> 0.45% | 0.77% -> 0.99% |
| Brahms OFF -> ON | 1.7% -> 1.7% (register-claimed 2.6 -> 2.7) | 0.41% -> 0.41% | 0.59% -> 0.70% |

Gate (no ORDER-VIOLATION rise; SPLIT-ACROSS-CLAIM under +0.3 points) passed; step 1 landed ON, carry stays OFF. The SPLIT rise is the new claims over C clefs the stroke map had already cut (SPLIT by owner clef_key_meter: Litolff 0.47 -> 0.65, Brahms 0.16 -> 0.25).

## 2026-11-02: the carry, built (lane-2.251-carry; OMR_CLEF_CARRY still default OFF)

**Cause.** The carry is only as good as recall of the RETURN clef. Step 1 claims C clefs by shape, but bass clefs only by a detector box plus dots. A missed return turns every head from it to the system's end wrong. **Process lesson:** before a carry, measure change recall AND return recall, and count the returns separately -- a carry multiplies whichever one is lower.

**Count** (step 1's own functions re-run off-line on whole pages: cell-map staves, the gather's binary, the 20261031 / 20261029 night records' detector boxes; `scan_claims.py`, `recall.py`):
- Litolff, 32 encoded changes: 28 claimed. All 13 C changes were claimed (bars 102 and 319 with kind unread). 5 of 19 F changes were missed: 38, 111, 115 (no box), Vc 346 (box refused, dots), Vc 411 (0.7 sp box). Of the 8 C changes whose return falls inside the system, 3 returns were missed (38, 111, 115). Two print changes the encoding lacks (p5 s0 bars 126 C, 129 F) were both claimed. No false claims; two cautionary clefs at a system's end (p5 s0 Vc, p9 s1 Fag).
- Brahms, 6 bassoon systems on pp. 1, 3-5 (print-checked): 12 changes. C clefs: 5 of 6 claimed. F clefs: 1 of 6 claimed (box refused for dots: p1 s1 c4, p3 s1 c1, p4 s1 c6, p5 s1 c0; no box: p3 s0 c6). 3 of 4 in-system returns missed.

**Built.**
- (a) An F clef with no box (`clef_pagewide.f_dot_pairs` / `f_templates` / `f_nobox`; gather under OMR_CLEF_CARRY, so step 1 alone is unchanged). Two witnesses: a dot pair straddling line 4, read window-independently (long horizontal runs and long vertical strokes cleared), AND the page's own F body (a read F clef of the same page) laid where the dots put it. Score = cover - extra. READ at >= 0.70; a clef-shaped candidate at >= 0.50.
  - Measured on Litolff pp. 1-16: every non-clef pair scores <= 0.61. Real ones: bar 38 0.73, Vc 411 0.77 (both read); Vc 346 0.69 and bar 115 0.68 (candidates). Bar 111 is not found (its dots are fused with heads).
  - Brahms: nothing reaches 0.50 (thick lines; the changes are smaller than the header clef). A cut-off on one plate: Sean's tiles judge it.
  - C-clef bowls cut by the lines pass as a dot pair, so no read or candidate may stand inside a claimed clef.
- (b) The carry stops (rule 8). Every step-1 near-miss is filed `candidate` (C bar near-miss, refused clef-sized box, below-read F body, a `clef*` box >= 0.5 that is too small for a claim). A candidate after a change whose kind differs from the header's makes the heads after it unread (no pitch, red "clef?"). Where the header's kind is in force it changes nothing. `move_glyph` pitches a moved head from the clef in force too.
- (c) The written `<clef>` stands at the change's bar, or the next bar when no head of that bar cites it. Every written clef is a READ claim, never a carried per-measure value. Mid-bar `<clef>` is NOT built.
- Tried and reverted: governing from the clef's right edge. 12 heads right after a C clef went right->wrong, because a C claim's area runs into the heads it touches.

**Print witness** (`clefwit.py`): the pitch the PRINT's clef gives each head's decided position, on the staves checked by hand. Heads after a clef inside the system, OFF -> ON:
- Litolff frozen sample: right 149 -> 364, wrong 266 -> 22, unread 7 -> 36. Transitions: wrong->right 225, right->wrong 10, wrong->unread 29.
  - 9 of the 10 right->wrong are bar 111: a missed return with no witness, F body and dots fused with heads.
  - The 10th is a 0.42 head box on the bar-38 clef's own ink.
- Brahms pp. 4-5: right 25 -> 88, wrong 82 -> 5, unread 0 -> 14. Transitions: wrong->right 77, right->wrong 0, right->unread 14 (bar 76's refused F box stops the carry: (b) working).

**Three measures** (lane_report, `--flag OMR_CLEF_CARRY`, PAGEWIDE on in both arms):
- Litolff frozen sample: notes -16, pitches ~186, words +12, clefs +19 -3. Judged right->wrong 0, unwritten->wrong 0 (270 tiles).
- Brahms 4, 5 (a subset; a Brahms page gather takes ~30 min per arm): notes -14, pitches ~55, clefs +6, flags -10, articulations -9 (carried on the unread notes). Judged right->wrong 0, unwritten->wrong 0 (175 tiles).

**Tiles:** `out/print/2.251-carry-tiles/` (seed 22513). 9 re-pitched heads and 3 clef tiles (Vc 411 and bar 38 read; Vc 346 candidate).

**Not done:**
- Bar 111.
- Brahms bass clefs (no read; candidates only).
- Mid-bar `<clef>`.
- A false head on clef ink is still pitched (an ink-claim question).
- Brahms frozen sample not run.

## 2026-11-02 -- Sean's carry tile answers (2.251 step 2, `answers-r3-carry.json`)

The carry round itself (OMR_CLEF_CARRY, seed 22513) is on branch `lane-2.251-carry` head 101e92cf7; its FINDINGS round lives on that branch until it lands. Sean's 12 blind tiles (heads the carry re-pitched, one per bar, plus no-box F clef reads), scored against the key:

- **10 right.** Tiles 1 and 10 (no-box F clef READ as bass). Tiles 2-9: the carry-ON pitch matches Sean's note and clef (G4 tenor, G3 bass, C3 bass, B3 tenor, D4 tenor, D3 bass, D4 bass, A2 bass); OFF was wrong on each.
- **1 miss (unread).** Tile 11: Sean says F clef; we only made it a CANDIDATE (body 0.69 < 0.70 read cut-off), so its notes go red. Not wrong -- but it is evidence 0.69 is a real clef and the cut-off, measured on one plate, is a measurement not a convention.
- **1 wrong.** Tile 12: Sean reads tenor clef, second space above the staff, Ab4. ON wrote B4, OFF E4. The clef kind is right; the head's staff POSITION is one step high (far head above the staff, where ledger lines own the position per page-facts) -- a position-reading fault, not the carry. wrong->wrong.
- **Carry-caused right->wrong on these tiles: 0.**

Open: (1) bar 111, 9 of 10 Litolff heads right->wrong in the lane's pitch witness, not yet explained; (2) tile 11 cut-off (0.69 vs 0.70); (3) tile 12 far-head position.

## 2026-11-02: carry round 2 (Sean: "fix bar 111 so the carry is never worse"; lane-2.251-carry, OMR_CLEF_CARRY still OFF)

**Cause, bar 111.** The return bass clef's dots touch the heads beside them, so no dot pair is seen. The detector drew only heads, flags and a 5-sp-wide 0.07 "head" on it, so nothing stopped the tenor carry.

**Decision: a candidate, not READ.** The page's own F body still matches it, slid along the staff with no dots (`f_body_scan`), at 0.73. A body alone is one witness. So it becomes a candidate that stops the carry: the heads go red "clef?", and the clef is not read.
- Measured on Litolff pp. 1-16, on staves holding a claimed change, right of it: every place with no clef scores <= 0.55. The real F clefs score 0.68-1.0.
- Candidate cut 0.60. The candidate stands a space left of the matched body, because a head box on the clef's own blob stood left of the match.

**Vc bar 346** (Sean's carry tile 11: a real F clef, body 0.69).
- READ stays at 0.70. Every non-clef dot pair on Litolff scored <= 0.61, measured on one plate, so it narrows and does not decide.
- New: a STRONG candidate (dot pair AND body >= 0.65, below READ) stops the clef in force, the header's included, unless that clef is an F clef. The Vc heads after bar 346 go red instead of being pitched tenor. Not on the frozen sample (p12).

**The bar-38 false head.** A 0.42 head box sat on the clef's own blob, and a "stem" was drawn on the clef's curve. The no-box F claim now spans the clef's height (top line - 0.3 sp to + 3.6 sp) and a space left of the body. The consult now refuses that head (`notehead_is_not_a_notehead`, `claimed_by:clef`), so it is not written. Its pitch verdict still stands: `restate_pitch` pitches refused heads too. That rule predates this lane and is not changed here.

**Sean's tile 12** (p11 s1 Vc cell 11). A far head one step high (A4 written B4): a position reading, owned by page-facts (a far head is placed by its ledger lines only). Not the carry; not fixed here.

**Print witness** (heads after a clef inside the system, OFF -> ON):
- Litolff frozen sample: right 149 -> 364, wrong 266 -> 13, unread 7 -> 45. Transitions: wrong->right 225, right->unread 9 (bar 111, now red), right->wrong 1. The 1 is the bar-38 clef-ink head: refused as a note, so not written, but it still carries a pitch.
- Brahms pp. 4-5: right->wrong 0, wrong->right 77, right->unread 14 (bar 76).

**Three measures** (`lane_report --flag OMR_CLEF_CARRY`, PAGEWIDE on by default):
- Litolff frozen sample, round-2 tree (before the bar-38 claim height and the candidate shift): notes -26, beams -8, pitches ~176, words +15, clefs +19 -3. Judged right->wrong 0, unwritten->wrong 0 (270 tiles).
- The final-tree run (`2.251-carry-r3-litolff`) also reports judged right->wrong 0 and unwritten->wrong 0. Its file line is NOT a measure of the carry: OCR crops timed out under machine load (3 in OFF, 1 in ON). Staff names moved between arms, and its OFF export differs from the round-2 OFF on 9 parts with identical carry-off code. Re-run it when the box is quiet.
- Brahms pp. 4-5: notes -14, pitches ~57, clefs +6, flags -10, articulations -9. Judged right->wrong 0, unwritten->wrong 0 (175 tiles).
- Brahms frozen sample: NOT run. At ~7 min a page an arm, it would take about 2 h.

**Tiles:** `out/print/2.251-carry-tiles-r2/` (seed 22514). The bar-111 mark, 3 heads after it, 2 Vc heads after bar 346; all written red.
