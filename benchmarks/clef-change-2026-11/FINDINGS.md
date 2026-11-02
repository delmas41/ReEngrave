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
