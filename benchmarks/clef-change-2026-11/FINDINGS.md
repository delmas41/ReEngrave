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

## 2026-11-02 -- Sean's carry round-2 tile answers (2.251 step 2, `answers-r4-carry.json`)

Tiles `out/print/2.251-carry-tiles-r2/` (lane branch `lane-2.251-carry` head 8c2180033, seed 22514): the heads the carry newly STOPPED (written red "clef?", no pitch) after Litolff bar 111 (Fag) and Vc bar 346, plus the bar-111 mark. Scored against the key:

- **0 wrong written.** Nothing was written wrong; carry-caused right->wrong 0.
- **5 heads safely red but missed.** Tiles 3-5 (bar 111, Fag) and tiles 1 and 6 (Vc bar 346) are real notes read in F clef (tile 1 C4, the rest B). Stopping the carry was safe (a tenor carry would have been wrong), but each is a MISS: the clef was real and the note readable, so the ideal is READ.
- **1 clef confirmed, box too wide.** Tile 2: the bar-111 mark is a real F clef, so the candidate was right that a clef stands there, but its box includes the eighth note before the clef (the area was placed one space left of the body match).

What it says: the body-only witness (bar 111, 0.73) and dots plus body at 0.69 (bar 346) were both real F clefs on Sean's reading. That is evidence for promoting them, on one plate only (Litolff) -- a cut-off measured on one plate is a measurement, not a convention.

Open: (1) tile 2 box width -- the candidate's area must not take the preceding eighth note's ink; (2) the candidates are real clefs -- promotion to READ is not yet decided and needs another publisher before it lands as a rule.

## 2026-11-02 -- Sean's bar-38 tile answer (2.251 step 2, `answers-r5-bar38.json`)

Tile `out/print/2.251-carry-bar38/` (lane branch `lane-2.251-carry`, Litolff print witness on tree 0c6273724): the one right->wrong left in the witness, glyph/2/1/3/3/3, Litolff p2 s1 staff 3, bar 38, a 0.42 head box that carry ON pitches F3 under the read no-box bass clef (OFF: C4). Sean: "The orange box is a part of an G clef and a quarter rest that run into each other."; asked whether he meant an F clef, as on carry tile 10: "I meant F clef".

- **There is no note in the box.** It is F-clef ink fused with a quarter rest, so the witness's 1 right->wrong is not a real note. Real carry-caused right->wrong on Litolff: **0**.
- **New open item, not the carry's:** the quarter rest fused with the clef is read as a head in both arms -- the rest is lost and a false head stands in its place. An ink-claim question (Litolff MERGES).

## 2026-11-02 -- 2.251 step 2 LANDED: OMR_CLEF_CARRY default ON (Sean "Land now")

Landing gate (the carry also GATHERS -- the no-box F claim -- so a fresh `--through gather`, `OMR_CLEF_PAGEWIDE=1` in both arms, `OMR_CLEF_CARRY` 0 vs 1, master cell map, `OMR_SURYA_KEEP_ALIVE=0`; Litolff pages 2,4, Brahms pages 4,5; `claim_order` / `claim_readout` on each arm's gathered record; tree = lane-2.251-carry dab238375 + main):

| plate | clef/key/meter single-owner ink | ORDER-VIOLATION | SPLIT-ACROSS-CLAIM |
|---|---|---|---|
| Litolff OFF -> ON | 2.3% -> 2.4% | 0.45% -> 0.45% | 0.99% -> 1.03% |
| Brahms OFF -> ON | 1.7% -> 1.7% | 0.41% -> 0.41% | 0.70% -> 0.70% |

Gate (no ORDER-VIOLATION rise; SPLIT rise under 0.3 points) passed. The Litolff OFF arm reproduces step 1's ON line (0.45 / 0.99). Brahms ON equals OFF to the printed digits: the carry's no-box F reader finds nothing at >= 0.50 on Brahms (thick lines), so it adds no claims there.

Evidence: Litolff print witness right 148 -> 365, wrong 267 -> 13; carry-caused right->wrong 0 on real notes (the one box was F-clef ink plus a quarter rest -- Sean, 4f14003c4). Brahms pp. 4-5 right->wrong 0. Judged right->wrong 0, unwritten->wrong 0.

Clean ON-arm file line (Litolff frozen sample, lane tree dab238375, `out/lane-report/2.251-carry-r5-litolff`; OFF byte-identical to r4/r2, 0 OCR timeouts in the ON arm): notes -26, accidentals -1, flags -2, beams -8, slurs -4, pitches ~176, blue +10/-33, words +15 (the red "clef?" marks), clefs +19/-3, keys +19/-3; notes not written 2505 -> 2528. Judged right->wrong 0, right->gone 0, unwritten->wrong 0 (270 tiles). It equals round 2's line exactly, so the r3/r4 differences were OCR load.

Open: refused heads are still pitched; Brahms bass clefs are only ever candidates; no mid-bar `<clef>`; the Brahms frozen sample was not run; the bar-38 quarter rest fused with the clef is read as a head in both arms (an ink-claim question); the bar-111 and bar-346 candidates are real F clefs (Sean) and are not promoted.

## 2026-11-02: step 3 dot finder -- PARKED (Sean 'Park it')

Sean, 2026-11-02: "I don't think we should land the work that it has done, but I'm not ready to give up on it." Then: "Actually, I just saw that there's work done for it later. Park it. Document well." Parked, not dropped. Nothing of this is on main. Branch `lane-2.251-dots` (head 6d1708b40, kept, do not delete) carries the flag `OMR_CLEF_DOT_FUSED` (default OFF; it exists only on that branch) and the scan tools `benchmarks/clef-change-2026-11/dots_scan.py` and `dots_table.py`, which need that branch's code and so stay there. The lane's entry follows in full, copied from that branch at 6d1708b40; the parking notes after it were added at parking.

### The lane's entry (from branch lane-2.251-dots 6d1708b40)

**2026-11-02 -- 2.251 step 3: the F clef dot finder (lane-2.251-dots; STAGED; `OMR_CLEF_DOT_FUSED`, default OFF; RESULT: NO CLEAN GAP, do not turn ON)**

**Cause (corrects the test lane).** Bar 111's dots do NOT touch a head or a stem. They fuse with the staff LINE above and the F line below (a fat print): the column through each dot is 37-40 px (2.4 sp) of unbroken RAW ink, line + dot + line. `_dot_mask_runs` clears every column whose raw run is >= 1.8 sp as a stem, and `f_dot_pairs` rejects a dot whose centre column runs >= 1.5 sp; both counted the line ink, so the dots were cleared as a stroke (real stems on that window are 44-45 px). `/private/tmp/.../cl111.py` shows the per-column runs. **Process lesson:** a stroke test that measures a run in raw ink counts the staff lines as part of the stroke; the test lane read "components 0.06-0.6 sp" as head-and-stem shredding, but it is the line-fused column. Look at the column profile before naming a neighbour.

**Built (flag OFF).** `_stroke_columns`: a column is a stroke only where its ink also stands 1.3-1.7 sp above the top line or below the bottom line of the dot window (dots stand between the lines, a stem or barline runs on past them); blobs must fill 0.40 of their box; a pair carries its distance-transform `radius`; a pair seen from two overlapping windows keeps the whole copy (a window edge clipped a dot and the clipped copy was kept). Same flag in the boxed path (`_dot_mask`, `f_line`). Tests `test_clef_dots_fused_2_251.py` (8): a fused pair is seen (flag OFF it is shredded), a dot touching a stem is seen, a stem through the F line with no dots, a barline, one dot, dots a space apart, dots on the C-clef line are refused. 24 pass with the clef carry/pagewide tests.

**Result: bar 111 is now seen on dots, but dots + body does not read it.** `benchmarks/clef-change-2026-11/dots_scan.py` + `dots_table.py`: every dot pair on every staff after the header, scored by `f_body_match` (best score per place), flag OFF vs ON.
- Bar 111 (p4 s1 st3 c13): the dot pair is found (upper blob 0.51 x 0.51 sp, radius 0.18; OFF: no pair). Its dots+body score is **0.417**, not 0.73: the body-scan's 0.731 box (x 2336-2372) stands 17 px (1.1 sp) right of where these dots put the template, over the dots' own ink. The two witnesses do not agree on where the clef is.
- Litolff pp. 1-16, real F clefs (19 places): OFF min 0.678 (bar 115) excluding 111; ON min 0.417 (111), bar 38 falls 0.726 -> 0.575. Non-clef max: **OFF 0.606, ON 0.745** (0.745 at p8 s0 st5 c8; 0.729, 0.727, 0.718 are stem pieces: slanted strokes and beam ends crossing the F line, radius 0.06-0.09). With a radius floor of 0.17 (every real pair >= 0.174): ON non-clef max still 0.745, 0.658, 0.638. The READ cut 0.65 (and 0.50) falls inside the non-clef range: **no gap**.
- Brahms pp. 0-26: no place reaches 0.52 either arm (OFF non-clef max 0.482, ON 0.512; real boxed F pairs score 0.1 on dots+body: Brahms dots touch the body). Nothing to measure a gap against.
- Boxed F claims (step 1 `scan_page`, flag OFF vs ON): **Brahms loses two real boxed F changes** (p3 s1 st12, p5 s1 st3: the p5 stem-fused lower dot is the case the old stroke clear was written for) and gains two header claims; Litolff moves header F claims (lost p2 s1 st10, p8 s1 st10; new p6 s1 st11, p12 s1 st10, p13 s1 st3) and shifts the right edge of several change areas by 2 px. So the flag moves boxed reads, and the Brahms ones the wrong way.

**What it says.** The dot finder's cause is found and fixable (a line-fused dot is a dot), but seeing bar 111's dots adds no usable witness: a looser stroke test also lets stem pieces through as dots (non-clef max 0.606 -> 0.745) and the dots' own position disagrees with the body's best match, so the pair scores 0.42. Reading bar 111 needs the body and dots located TOGETHER (a joint fit of the clef's body and both dots at one position, after the heads are claimed -- ROADMAP 2.223), not a better dot finder. Flag stays OFF; nothing lands. No pipeline run and no tiles: there is nothing ON would newly and safely read (the newly READ at 0.65 under ON are non-clef places). Judged right->wrong was not measured because no code path changes with the flag unset.

**Prior work.** LEGACY read the dots in `clef_locator._has_f_clef_dots` (a worn dot is not round: the line stripper leaves a stub under it; its height bound was loosened and measured), and the 2026-08-31 veto lesson (memory `project_f_clef_dot_veto`: POSITION beats SHAPE, the veto was never shown the dots); `docs/ink-rules.md` has no F-dot row beyond the pagewide ones; page-facts has no dot-finder ruling.

### Parking notes (2026-11-02)

- **Cause, plainly.** Before looking for dots, the reader removes stems so they cannot be mistaken for dots. It decides "stem" one pixel column at a time, by the height of the unbroken black run alone (1.5-1.8 sp), and never by width or shape. At bar 111 the heavy print joins each dot to the staff line above and below it, so a column through a dot is line + dot + line, about 1.7 sp of solid black. That reads as a stem, and both dots are cleared before the dot search runs.
- **Correction.** The earlier test lane (`test-2.251-f-cutoff`) said the dots touch a head and a stem. The dot lane's column profiles show they fuse with the staff LINES. The day manager looked at the bar-111 crop (`out/print/2.251-carry-tiles-r2/tiles/02.png` in the carry lane's worktree) and saw the same: very thick lines, with the dots merged into them.
- **What the lane tried and why it failed.** A stroke now had to run 1.3-1.7 sp past a line, and a dot blob had to fill 40% of its box. The bar-111 dots were then found (radius 0.18), but: dots+body scored 0.417, because the body match sits 1.1 sp right of where the dots place it; the Litolff non-clef max rose 0.606 -> 0.745 (stem pieces and beam ends); bar 38 fell 0.726 -> 0.575; and two real boxed Brahms F changes were lost (p3 s1 st12, p5 s1 st3). There is no clean gap.
- **Process lesson.** A stroke test on raw ink counts the staff lines. Check a column's profile before blaming a neighbour.
- **Untested hypothesis (day manager, from one picture), for whoever resumes.** The bar-111 clef looks smaller than a normal clef, as a mid-staff change clef often is, so the body template may be fitted at the wrong scale. That would explain the 1.1 sp offset. First check: does a smaller-scale body match line up with the found dots at bars 111 and 38?
- **Where it resumes.** ROADMAP 2.223 (binding page-wide marks after the heads are read), the item the lane itself pointed at: a joint body+dots fit after the heads are claimed. Resumes under ROADMAP 2.223 (Sean confirmed 2026-11-03: 'Yes').
- **Branches.** `lane-2.251-dots` (keep; do not delete) and `test-2.251-f-cutoff` (head 96ddc830d; its test-only env overrides never land). Bar 111 stays red.

## 2026-11-02 -- F cut-off TEST (copied from origin/test-2.251-f-cutoff 96ddc830d; its test-only env overrides and scan scripts are NOT taken, the scripts need an uncommitted work-2.251 dir; STAGED; measurement, no default changed, nothing lands)

**Cause.** The F cut-offs were set on staves that already held a claimed change (and, for the dots+body pair, on the pairs the dot finder could see). Measured on EVERY staff, the body shape alone is a head-and-slur-on-the-F-line detector as much as a clef detector. **Process lesson:** a cut-off measured on the subset where the reader runs is not a cut-off for a reader that is then asked to run everywhere (CLAUDE rule 7: a rate from another population). Scripts: `fcut_scan.py`, `fcut_dots.py`; ink and boxes as the 2.251 count (20261029-night Litolff, 20261022-night Brahms boxes; master cell maps; Litolff pp. 1-16, Brahms pp. 0-26; step-1 claims with the carry off).

**(1) Dots+body READ 0.70 -> 0.65.** Every dot pair with a body match >= 0.40, every staff, after the header window.
- Litolff, pairs 0.60-0.70: 0.69 Vc 346 (p12 s0 st10 c7, real F, Sean tile 11); 0.69 p8 s1 st3 c0 (the boxed F clef at bar ~228, read already by its box); 0.68 bar 115 (p5 s0 st3 c2, real F per the encoding); 0.61 p8 s0 st5 c8 (bar ~214, a beamed head and accidental, not a clef; crop). Next below: 0.59 p11 s1 st8 c3, 0.57 p13, 0.56, 0.55 (all non-clef).
- **Litolff: non-clef max 0.61, real-clef min 0.68. Clean gap 0.07; 0.65 sits inside it.** Newly READ at 0.65: Vc 346 and bar 115, both real. Nothing else.
- **Brahms: no dot pair reaches 0.50; non-clef max 0.48; the only real clef found is a header F (0.80, p0).** The Brahms F changes are never found by dots+body (dots touch the body or the thick lines). 0.65 reads nothing there: it neither helps nor hurts on Brahms. The 0.70 was never tested against a Brahms real change.

**(2) Body alone (`f_body_scan`) on every staff.** Local maxima, scored as in gather.
- Litolff: real F clefs 1.00 (the templates), 0.77 Vc 411, 0.77 bar 38, **0.73 bar 111**, 0.69 Vc 346, 0.68 bar 115. Non-clef top 10: 0.70 p15 s1 st4 c6; 0.69 p2 s1 st7 c4; 0.68 p8 s1 st1 c0; 0.68 p15 s1 st4 c5; 0.65 p15 s1 st4 c12; 0.65 p2 s0 st9 c0; 0.65 p15 s1 st4 c13; 0.65 p10 s0 st7 c8; 0.64 p2 s0 st1 c1; 0.64 p15 s1 st2 c1 (crops: heads/slur-heads sitting on the F line; also 0.66 on the C clef of bar 110). **Bar 111's 0.73 clears the best non-clef (0.70) by 0.03 only: not a gap.** (The earlier "every place with no clef <= 0.55" was measured only right of a claimed change.)
- Brahms: real F changes on the print-checked pages score 0.52 (p1 s1 st3 c4), 0.54 (p3 s1 c1), 0.56 (p4 s1 c6), 0.69 (p5 s1 c0); boxed ones 0.72-0.80. On pp. 1, 3-5 the only unexplained place is 0.43 (p5 s1 st12 c1). Off those pages (my crop look, NOT print-checked): clef-looking hits 0.53-0.64 (p26 s0 st5 c2 0.64, p17 0.57, p22 0.57 ...), and head/stem blobs at 0.54 (p8 s0 st1 c9) and 0.49-0.52 (p14). **No clean gap on Brahms (real ~0.52, non-clef up to ~0.54).** The 0.73 is a Litolff number; on Brahms the clefs print smaller and score 0.52-0.57.

**Why bar 111's dots are lost (cause).** `f_dot_pairs` clears every horizontal run >= 1.2 sp and every column holding a vertical run >= `DOT_STROKE_CLEAR_SPACES` BEFORE it looks for dots. At bar 111 the dots touch the stem and head beside them, so that clearing cuts them into shreds (components 0.06-0.6 sp, none dot-sized after clearing; measured by `/d111.py` on p4 s1 st3). A dot fused to a head is not separable from the head by the dot finder's own size test. Could a looser test see it? A dot-sized disc (0.2 sp) on the F line +/- 0.5 sp right of the matched body: bar 111 fill 0.75 (best x); of 33 distinct non-F places with body >= 0.60, 29 have both discs >= 0.75 filled (19 fully). It fires on nearly every head cluster on the F line, so "dots even if touching" adds no witness: it reads the same ink as the body. A second witness for 111 must come from elsewhere (the encoding's bar content, a roster/range check on the notes, or the dots read after the heads are claimed -- ROADMAP 2.223's later page-wide step), not from a looser dot test.

**Pipeline check** (`lane_report`, flag via the TEST-ONLY env `OMR_TEST_F_READ`, carry ON, `--from gather --cell-map master`, `OMR_SURYA_KEEP_ALIVE=0`; Litolff pp. 4, 12; Brahms pp. 4, 5; NOT the frozen sample):
- READ 0.70 -> 0.65, Litolff: `words -6 | clefs +1`; 6 red `clef?` bars on the Vc (p12) gone, a written F clef at its bar; no note, pitch or red-bar change. Judged right->wrong 0, unwritten->wrong 0 (150 tiles).
- READ 0.70 -> 0.65, Brahms: no pair reaches 0.50 so the cut-off cannot reach it; the report still shows `accidentals +3 | ties -2 | pitches ~2 | blue +1 | words +1` -- not caused by the cut-off (no identity control run; the re-gather is not deterministic under load: 2230 s wall time). Judged right->wrong 0, unwritten->wrong 0 (175 tiles).
- SECOND ARM, labelled: body-only READ of >= 0.72 (TEST-ONLY `OMR_TEST_F_BODYREAD`, one witness, against CLAUDE §4), Litolff pp. 4, 12: `notes +10 | flags +2 | beams +8 | blue +4 | words -4 | clefs +1 -1 | keys +1 -1`; the bar-111 `clef?` mark gone, 10 eighths written after it (blue). Judged right->wrong 0 (150 tiles). `words -4` includes a `cresc.` lost on p12 (OCR under load, not the clef). Not a landing: 0.72 is Litolff-only and the non-clef max is 0.70.
- Tiles for Sean: `out/print/2.251-f-cutoff/tiles-bodyread-111/` (11 tiles, key `out/print/2.251-f-cutoff/key.json`, not shown), the new bar-111 heads and controls. The 0.65 arm's only new READ is Vc 346, already confirmed by Sean (tile 11); bar 115 stands on the encoding; no further tiles.

**What it says (not decided).** 0.65 for dots+body is supported on Litolff (gap 0.61 / 0.68) and untestable on Brahms (no real Brahms change reaches a pair): a narrowing, per CLAUDE §4. A body-only READ is not supported: Litolff gap 0.03, Brahms none.

## 2026-11-02 -- F dots+body READ 0.70 -> 0.65 LANDED (Sean "Do it")

Gate on main (0.70) vs this branch (0.65), fresh `--through gather`, PAGEWIDE and CARRY default ON, `OMR_SURYA_KEEP_ALIVE=0`, master cell map; Litolff pp. 2,4,12, Brahms pp. 4,5; `claim_order` / `claim_readout` per arm:

| plate | clef/key/meter single-owner ink | ORDER-VIOLATION | SPLIT-ACROSS-CLAIM |
|---|---|---|---|
| Litolff 0.70 -> 0.65 | 2.4% -> 2.4% | 0.43% -> 0.43% | 0.87% -> 0.87% |
| Brahms 0.70 -> 0.65 | 1.7% -> 1.7% | 0.41% -> 0.41% | 0.70% -> 0.70% |

Passed. The Litolff records do differ: main holds Vc bar 346 as a STRONG candidate, the new arm READS it (one more `f_body_template` claim, one fewer `f_body_below_read`); the claim is too small to move the readout digits. File line (`lane_report`, scratch tree with the test env override, not landed; Litolff pp. 4,12, Brahms pp. 4,5, not the frozen sample): Litolff `words -6 | clefs +1`; Brahms `accidentals +1 | pitches ~1 | blue +1` (not reachable by the cut-off: load noise). Judged right->wrong 0, unwritten->wrong 0. STRONG tier: empty at these cut-offs, constant kept. Scan scripts `fcut_scan.py` / `fcut_dots.py` NOT copied (they need the uncommitted `work-2.251` directory).
