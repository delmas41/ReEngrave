# ROADMAP 2.85: repeats and 1st/2nd endings, numbered the print's way

Branch `lane-2.85-repeats-voltas`, off origin/main `26cb57c6`. Path: **STAGED**
throughout (GATHER readers, two ADJUDICATE decisions, EXPORT numbering).

**Convention** (Sean, 2026-10-11, DECISIONS): the 2nd ending reuses the 1st
ending's bar numbers. The print confirms it: Breitkopf 317803 prints 188 at
pdf p10 system 1 and 194 at p11 system 0. That system has 1 + 2 + 5 bars, so
the two 1st-ending bars are not counted.

## 1. Census: what was already there

| | Brahms p10–11 | both movements (43 pages) |
|---|---|---|
| detector volta/ending class | none in the 208 classes | — |
| detector on the p10 brackets | 1st stroke boxed as `ottavaBracket`, in one cell only (the cell crop clips the stroke); 2nd stroke boxed as `staff`; **no numeral fired** | — |
| detector `repeatDot` | 2 boxes, both spurious; **0 of the 28 real dots** of the backward repeat | — |
| GATHER quantity for any of it | none (`gather_coverage`: `"repeat": None`) | — |

So both readers had to be built in CV.

## 2. The readers (GATHER)

**`volta_bracket.find_brackets`, the bracket reader (`Q.VOLTA_BRACKET`, filed on the system).** It looks for a long, thin, straight stroke above the system's top staff with a vertical hook at its left end.
- **First cut:** 108 candidates over 43 pages. Two were real (Brahms p10 s1); the other 106 were beams with stems, ledger lines with stems, and on Litolff an undetected staff line plus barlines.
- **Two shape rules, both measured:** a hook must stop at least 0.5 spaces above the staff (a stem runs on into it), and the stroke must be at least 6 spaces long (the 106 false hits were 1.8–5.9 spaces long; the real brackets 30.6 and 37.6).
- **After the rules:** exactly the 2 real brackets, and no Litolff hits. Beethoven 5 i prints no endings, so that is correct.
- **Hooks on the real brackets:** 2.87 and 2.73 spaces on the 1st ending (closed); 2.80 on the 2nd ending's left end and none on its right (open).

**`gather_volta_numerals`, the numeral reader (`Q.VOLTA_NUMERAL`).** It reads the bracket's rows, so it must run after the bracket reader (a forced GATHER edge).
- **Tesseract fails on this plate.** It reads the bold Breitkopf "1" as "4" every time we asked: the ending "1." as "4." (confidence 83), and the 2.13 bar numbers 179/188/194/421 as 479/488/494/424 (§5).
- **Surya reads both** "1." and "2." on a crop padded 60 px and scaled 2×, with a token cap of 16. A cap of 8 read nothing; an unpadded crop read nothing. Repeat runs gave the same answer.
- **So Surya is the reader, Tesseract only the fallback** when Surya can't run (a `--no-surya` run). A "4." from Tesseract then makes the ending decision abstain. It never becomes a "1".

**`repeat_dots.find_pair`, the repeat-dot reader (`Q.REPEAT_DOTS`).** It looks for two dots in spaces 2 and 3 beside each barline the measure extractor cut, one staff at a time.
- **Brahms p10:** dots found on 11 of 14 staves at the double barline, and at no other barline on the page.
- **Both movements:** the only edges that reach the staff vote are that repeat and the exposition's forward repeat at p3 s0 (8 of 14 staves; the reference encoding has its `forward` repeat at bar 40). Two single-staff hits fall below the floor.
- **Litolff's exposition repeat is MISSED** (p5 s0). The dots touch the heavy staff lines (the merging plate), so they are one ink component with the staff.
  - **Erasing the staff lines inside the window was tried and refused.** It took the edges passing the vote from 2 (both real) to 69, almost all of them key-signature flats just right of a system's first barline.
  - A miss writes nothing. A false repeat would write `:||` into the file.

## 3. ADJUDICATE (`adjudicators/repeats.py`)

**`adjudicate_repeat_barlines`** decides a barline is a repeat when at least half the system's staves (and at least 2) carry a dot pair there. Dots on the left of the barline mean a backward repeat; on the right, a forward repeat.

**`adjudicate_endings`** treats a bracket as an ending when:
- it has a left hook,
- both of its ends sit within 0.75 spaces of a barline on the top staff, and
- its numeral reads as one digit.

It decides only when a "1." is followed in the very next bar by a "2.". Otherwise it abstains with a named reason:
- `numeral_unread`
- `numeral_readers_disagree`
- `span_not_at_barlines`
- `no_first_and_second_ending`
- `endings_not_adjacent`

⚠️ **One system only.** An ending broken across a system or page break abstains, and the bars stay counted straight through. Joining an ending across systems is not built here.

Over the whole Brahms movement exactly three verdicts are DECIDED:
- the forward repeat at p3 s0,
- the backward repeat at p10 s1,
- the endings at p10 s1: 1st ending = cells 1–2 (closed), 2nd ending = cell 3 (open). This matches the reference encoding, whose 2nd ending is one bar marked `discontinue`.

## 4. EXPORT

`_EndingPlan` (in `export.py`) changes bar numbers and nothing else:
- **Numbering:** every bar from the 2nd ending's first bar on is numbered `k` lower, `k` being the 1st ending's length, and every later system carries the rewind. It applies only under the document-wide numbering scheme; if that numbering was refused, the plan renumbers nothing.
- **Marks written:** `<ending number="1" type="start|stop">`, `<repeat direction="backward">` with `light-heavy`, `<ending number="2" … "discontinue">` when the bracket is open, and `heavy-light` + `forward` for a forward repeat. They are written on every part, tacet padding included.
- **Accounting:** the notehead equality is unaffected (`unaccounted: []` on both arms).
- **The 2.13 check:** `_printed_bar_number_check` now compares the printed numeral against the number the file actually writes.

## 5. Measurement: base vs arm, one record, one tree

- **Record:** `brahms1-breitkopf-mvt1-whole-20261010-night.record.json` (through INFER, main `26fdb4d0`).
- **Base:** that record exported as it is by this branch's code. The plan is inert with no verdicts; that is the control.
- **Arm:** the same record plus the 2.85 rows and verdicts, read fresh off the same 27 pages at 600 dpi.
  - The staff-0 cell count matched the record on every system (0 mismatches).
  - The new readers file only new quantities, which only the two new decisions read. So injecting them is equivalent to a re-gather for every other row.
- **Script:** the scratch `ab.py` (not committed).

Printed numeral against the number on the system's first bar (`delta = printed − file`), for the readable numerals after the endings:

| system | printed | base | arm |
|---|---|---|---|
| 11/1 | 205 | −2 | **0** |
| 14/1 | 273 | −3 | **−1** |
| 21/0 | 389 | −3 | **−1** |
| 21/1 | 398 | −3 | **−1** |
| 22/0 | 409 | −3 | **−1** |
| 24/0 | 454 | −3 | **−1** |
| 24/1 | 463 | −3 | **−1** |
| 26/0 | 493 | −2 | **0** |

- **As predicted, the drift drops by 2.** The −1 left from p13 on is 2.86's (the courtesy key signature after p11 s1 counted as a bar).
- **Check agree goes from 7 to 8.**
- **22/1's base "agree" is false.** Tesseract read 421 as "424". The arithmetic from 22/0 (409 + 12 bars) says 421.
- **Systems before p10 s1 are unchanged** in both arms.
- **The 2.13 reader's Tesseract misreads 1 as 4 throughout this plate** (479/488/494/449 for 179/188/194/149). That belongs to a separate item; it is not fixed here.

**What the file reads now:** …187, 188, [189, 190 — 1st ending, `:||`], [189 — 2nd ending], 190 … 194. All 14 parts carry the marks.

## 6. Open question for Sean: duplicate measure numbers

The print's way writes `number="189"` and `number="190"` twice in each part.
- **Verovio** loads the file but adds 24 warning lines (12 of them "slur/tie … is not encoded in the measure of its start"). Base has 49 lines, arm 73.
- **Giving the 1st-ending bars unique tokens** (`189a`, `190a`) brings it back to 49, identical to base.
- **The gradus reference encoding** counts straight through instead (2nd ending = 191).
- **As built:** the literal rule, duplicates and all. Sean, 2026-10-11 (tile 5): *"I want the same numbers as the original"*, so the duplicates stay; Verovio's warnings are a known cost.

## 7. Blind tiles: `out/print/2.85-review/`

Five tiles. The questions are in `QUESTIONS.md`. Nothing of ours is drawn on them.
- **Key (do not show Sean):**
  - 1 = 1st-ending bracket (p10 s1)
  - 3 = 2nd-ending bracket (p10 s1)
  - 2 = backward repeat (p10 s1)
  - 4 = forward repeat (p3 s0)
  - 5 = **CONTROL**: a plain double barline (p11 s1, before the key change), with dotted notes beside it. It must be answered "no repeat".
- **Answers** (Sean, blind, 2026-10-11; `answers.json`): **4 of 5 agree.**
  - Tile 2: repeat sign, dots on the left. Agrees.
  - Tile 3: 2nd ending, 1 bar of it. Agrees.
  - Tile 4: dots on the right. Agrees.
  - Tile 5, the control: *"a double barline"*, so not a repeat. Agrees. He added *"we need to figure out the barline because I want the same numbers as the original"*: that is 2.86's tail, and the answer to §6 is to keep the print's numbers.
  - Tile 1: *"1 bar of a first ending"*. **Ours says 2 bars.** On the tile the bracket spans a barline. The reference encoding (189–190) and the printed numbers (188 → 194 with 5 second-ending bars) both need 2. Asked again with the barline marked (`tile_01_question.png`); not changed until he answers.

## 8. Tests and checks

- **`tools/omr/tests/test_staged_repeats_endings.py`:** 25 tests. Each reader and each decision has a positive control and a refusal case in the same class: a beam with stems is not a bracket; a "4." is not a 1st ending; one dot is not a repeat; 2 of 14 staves is not a repeat.
- **RED on origin/main:** the two EXPORT tests failed there (numbers came out 1–6, no marks). The controls passed.
- **The synthetic dot test caught a real bug:** a negative slice bound in the line-erasure variant.
- **`python3 -m tools.omr.staged.check`:** the arm's first pass added 10 open findings (192 → 202):
  - 7 unresolved gather subjects, a subject passed through a tuple;
  - 2 decisions whose recorded fields no test asserted;
  - 1 reason computed at run time.
  All three were fixed, and wiring, brakes and health are back at their base counts.
