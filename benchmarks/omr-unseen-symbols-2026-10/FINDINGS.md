# The symbols we cannot see -- FINDINGS (ROADMAP 2.179)

STAGED GATHER (+ the ADJUDICATE gates the new boxes meet). Branch `lane-2.179-unseen-symbols` off main `022bb99f5`. Flag `OMR_STEM_END_HEADS`
(default OFF). Code: `tools/omr/staged/stem_end_heads.py`, `gather.gather_stem_end_heads`, reader `READERS.RESCUE_STEM_HEAD`; tests
`tools/omr/tests/test_staged_stem_end_heads_2_179.py` (15). Probes `probe/` (`g1_regather.sh` the re-gathers, `e1_export.py` re-decide +
export + new-box fates, `c1_census.py` + `s1_sheets.py` the red-bar census and sheets, `labels/*.txt` my labels, `t1_tally.py`,
`o1_orphans.py`, `r1_rest_fates.py`, `v1_newboxes.py`, `b1_bar_diff.py`, `j1_judged_diff.py`, `n1_round_diff.py`, `d1_debug_cell.py`,
`t1_tiles.py`). Records and sheets are machine-local (scratchpad), not committed; every number below is re-made by those scripts.

**CONVENTION ASSUMED:** every stem carries a head at one end, on the side its direction gives (stem up -> stem at the head's right, head at
the bottom; down -> left, top); a rest never has a stem; a whole note has no stem. **WHAT WOULD FALSIFY IT:** Sean's tiles
(`out/print/2.179-review/`) showing that most new boxes are not heads. **NOT CONFIRMED:** the 0.05 floor and the windows (1.0 space along
the stem, 1.1 across, 0.6/1.1 "beside a seen head") were set on these two plates and may only NARROW. **Who says it's right:** every
"real/false" below is MY look at crops (ours, not evidence); Sean's tiles are unanswered.

## 1. The sample (main's defaults, 2.172 small view ON)
Re-gathered through adjudicate, one gather at a time (`g1_regather.sh`): Litolff pdf pages 1,6,10,13,16, Brahms 0,1,6,23,24 (the first page
of each movement for the meter/key carry, then the pages with the most red bars in the 20261018-night export). Exported with red bars
(`e1_export.py`): Litolff 219 red bars (197 distinct, 22 doubled-staff copies), Brahms 152. The OFF export of the branch equals the base
export exactly (notes, rests, red, add-up): the file-level control.

## 2. What is missing or wrong in every red bar (my look at every one; `labels/litolff.txt`, `labels/brahms.txt`; distinct bars)
a never boxed in its own family; b boxed in its family under 0.25; c boxed in the wrong class; d boxed right, dropped by a gate;
e seen but mis-valued; f other (fv two parts summed as one, fx a non-note or another staff's symbol counted, fs one bar cut in two cells
at a system end, fg a chord split into events, fu cannot tell). Main cause first; in brackets, bars where the cause appears at all.

| cause | Litolff (197) | Brahms (152) |
|---|--:|--:|
| a never boxed | 28 (31): mostly eighth rests; welded heads | 1 (1): a flag |
| b under the floor | 40 (44): welded black heads 21, half heads 8, rests 11 | 3 (3): dots |
| c wrong class | 13 (14): welded heads boxed restWhole (refused `rest_has_a_stem`); rests boxed as heads | 0 |
| d dropped by a gate | 3 (3) | 8 (35): eighth rests refused `rest_is_a_duplicate_box` where the box that outranked them was itself refused; `rest_stroke_into_a_head` |
| e seen, mis-valued | 9 (11): specks read as dots; beamed eighths as quarters | 30 (36): **24 a dot boxed beside its head, the head written undotted**; 6 flags/beams |
| fv two parts | 12 | **75 (80)**: a2/divisi winds on one staff (pages 23-24) |
| fx extra counted | 35 (39): key flats, clefs, sharps, sf hooks, another staff's heads | 34 (37): meter digits, the next staff's rests/heads, clefs |
| fs / fg / fu | 20 / 6 / 31 | 0 / 0 / 1 |

Detector-side (a+b+c) is 81 of 197 Litolff bars and 4 of 152 Brahms bars. `r1_rest_fates.py`, Brahms rests refused in red bars with no
kept rest on the ink: duplicate 37, clipped by crop 16 (mostly barline stacks), stroke into a head 14, outside staff 10, has a stem 7.

## 3. Sean's question: are the wrong values what we cannot see?
**No. On Brahms the wrong values are marks we SEE and do not apply.** Of 30 Brahms bars whose main fault is a wrong value, 24 are an
augmentation dot the detector boxed (kept) beside its head while the head was written undotted (2.180's mechanism; 2.167e Q3 step 3);
6 are flags/beams read wrong. Only 4 Brahms red bars lose a mark under the floor or unboxed (3 dots, 1 flag). So the dots lane (2.180)
is the wrong-value lane; no third lane is needed for unseen marks. Two other Brahms causes are bigger than anything detector-side on these
pages and belong to no running lane: two parts on one staff summed as one (75 bars; 2.167c's random 45 found 3, so it is page-dependent:
these are tutti wind pages) and real eighth rests lost to the duplicate-box chain (35 bars; 2.167e Q2 named the function).

## 4. The fix: a stem that carries no head is a note we have not seen (`OMR_STEM_END_HEADS`)
The reader's principle (Sean 2026-10-19 "where it gets really crowded or hard to read. We look closer"; 2026-10-01 "if there are stems
then there are notes and the note heads will be connected to the stems"): a reader who sees a stem with nothing at its end looks again at
the end and reads the blot there as the head. Per cell: CV stems (the 2.55 call); a stem is an orphan when no head box stands at either
end, and is not one when it stands inside another mark's box (a Breitkopf quarter rest's body, a flat, a clef, a dynamic); for a cell
with an orphan the SAME detector is re-read at 0.05 and a head box (or a block rest box, re-read as the black head it is) at the orphan's
end, on the side the stem direction gives, is appended under its own reader; never a whole-class box, never one within about a space of a
head already seen, never one on a stronger box of another family. Production boxes are never changed; every new box meets every
ADJUDICATE gate. Round 1 (without the owner / whole / beside rules) wrote 6 Brahms false heads (quarter-rest curls, an f, a key flat);
round 2 is what the branch holds (`n1_round_diff.py`: it dropped 12 Litolff boxes, 6 written, of which about 4 were real).

## 5. On the exported file, OFF vs ON (round 2)
| | Litolff OFF | ON | Brahms OFF | ON |
|---|--:|--:|--:|--:|
| notes | 2703 | **2811** (+108) | 3012 | 3024 (+12) |
| rests | 459 | 458 | 1177 | 1184 |
| red bars | 219 | **190** | 152 | 152 |
| bars that add up | 1199 | **1261** (+62) | 813 | 811 |
| unread empty bars | 169 | 134 | 27 | 27 |
| partial unread bars | 226 | 193 | 100 | 102 |

Litolff: 37 bars stopped being red, 8 went red (mostly a bar that was unread and now holds one head, short; `b1_bar_diff.py`).
Brahms: 2 and 2. The +7 Brahms rests are not traced.

**New boxes** (`v1_newboxes.py`, every one looked at): Litolff 125 filed, 95 written; by my look about 91 real heads (welded black heads,
half heads in ledger chords, block "rests" with a stem), 1 false (a key flat at a bass clef), 3 unclear. Brahms 18 filed, 11 written:
8 real, 2 false (the curl of an f; a quarter rest's lower curl), 1 unclear. Not written (30 / 7) are mostly fragments the gates refused.

**Sean's judged tiles** (`judged score`, right/wrong/narrowed/abstained): Litolff 60/12/1/0 -> 60/14/1/0; Brahms 73/12/4/0 unchanged.
The Litolff change is ONE subject judged twice (2.88 tiles, `glyph/10/1/9/5/0`, "half"): the print has two half heads a second apart on
one stem; production boxed the upper, ON adds the lower; `stacked_head_duplicate` (2.42) fits ONE head slot to the pair and its ink rule
keeps the new box and refuses the production one. Both heads are real; the file writes one half in either arm. That gate, not the new box,
is wrong here (a production box overturned through it); recorded, not fixed (outside the fence).

**Cost:** gather wall Litolff 957 -> 1027 s for 5 pages (+7%), Brahms 1832 -> 1810 s (no visible cost: one extra detector call per cell
holding an orphan stem). Export unchanged.

## 6. Tiles
`out/print/2.179-review/` tile_01..12 + README ("what is the symbol in the blue box?"): 9 new written boxes (5 Litolff, 4 Brahms, seeded
2179) and 3 controls (production boxes: a black head 0.87, a half head 0.72, an eighth rest 0.86). Key: `probe/data/tiles_key.json`
(outside the tiles folder); one run of `t1_tiles.py make 2179`, `t1_tiles.py check` verifies names and sha256.

## Not done / caveats
- No default flipped. The labels and every real/false count are mine. The windows were set on these plates.
- Eighth rests never boxed (Litolff 21 bars) are untouched: no stem witnesses a rest.
- The Brahms duplicate-box rest chain (35 bars) and two parts on one staff (75) are the biggest Brahms causes; neither is this lane's.
