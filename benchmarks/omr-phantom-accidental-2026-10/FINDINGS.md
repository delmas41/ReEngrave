# 2.192 -- phantom accidentals on rests (STAGED GATHER -> ADJUDICATE; flag `OMR_ACCIDENTAL_ON_A_REST`, default OFF)

Read-only cause work on the 20261020-night whole-movement records via the 2.185 extracts (boxes + standing verdicts); crops are my own
checks (rule 7), not Sean's answers. Scripts here: `cause.py` (census), `crops.py` (my crops).

## Cause (rule 3), PRODUCTION detector pass + no rule compares the two families
1. WHO MAKES THE BOX: the production per-cell detector (reader `detector`, no view/source tag on any of the 379 Brahms / 79 Litolff
   `accidentalDoubleSharp` boxes) boxes an eighth rest's bulb-and-stem as `accidentalDoubleSharp` (scores seen 0.25-0.74).
   The 2.172 small view is NOT the source of the accidental: where the view recovers the rest (91 of 206 Brahms cases the kept rest box is
   `detector_view`), it leaves the weaker wrong-class production box beside it.
2. OVERLAP: the accidental box and the rest box are one ink -- IoU >= 0.5, same cell (every one of the 209 Brahms and 15 Litolff boxes counted below), usually 0.8-0.9.
   10 of 10 random crops of these were an eighth rest (Brahms).
3. WHO DECIDES: nobody. 2.186 merges only within a family (correctly); `adjudicate_rest_is_not_a_rest` and
   `adjudicate_accidental_is_not_an_accidental` each look only at their own family, so both boxes stand DECIDED-kept
   (the rest kept in 208 of 209 Brahms, 13 of 15 Litolff; the accidental kept in all). `adjudicate_accidental_owner` then gives the accidental the nearest head to its RIGHT at
   its height (the next note) -- a rest's ink always has one -- and `apply_printed_accidental` writes `##` on it.
## Counts (whole movement, 20261020-night)
| | Brahms | Litolff |
|---|---:|---:|
| `accidentalDoubleSharp` boxes | 379 | 79 |
| of them on a KEPT rest box (IoU >= .5) | 209 (207 rest8th, 2 restQuarter) | 15 |
| of them owning a head and written `##` (on a rest box / no rest box) | 22 / 23 | 5 / 15 |
| no rest box within IoU .1 | 165 | 64 |
Of the 165 Brahms double-sharps with no rest box, a 10-crop look: 4 an eighth rest whose own box is missing, 4 a tiny speck (a dot or stem
fragment), 2 a sharp misclassed. Litolff 10 crops: ~5 eighth rests (blurred plate), 2 specks, 3 unreadable. The rest-with-no-box share (~40%)
is NOT reached by this lane (no kept rest box to contest; needs an unboxed-rest reader -- `unboxed_ink_is_a_rest` exists) and is left open.
Other accidental classes touching a kept rest box (Brahms 51 at IoU >= .3): in the crops mostly REAL naturals/sharps/flats (and key flats)
with a wrong-class rest box beside them, 2 of 14 true rests -- so the overlap alone must never refuse them; the SHAPE decides.
Process lesson: the 2.185 "47 phantom" figure counted applied `##` heads; the contested population is 4-5x larger (210) because most never own a
head, and the larger unreached part (165) has NO rest box to contest -- a count of harm is not a count of cause.

## The fix (flag OFF)
`adjudicate_accidental_owner`: an accidental box whose IoU with a KEPT rest box (verdict `rest_is_not_a_rest` not DECIDED True) in its own cell is >= 0.5
abstains `on_a_rest` (owns no head; the note keeps its key/bar alteration; rest untouched; the refusal records rest, IoU, measured shape, why) UNLESS
the 2.190 shape reader reads its own ink clearly accidental-shaped AND of the shape its class names (double sharp -> sharp, double flat -> flat).
Unread / unclear / mismatch = not applied (rule 8). The head-side test ("left of it, at its step") is the owner rule that already follows.
Not done: writing the refused case BLUE on the note (the refusal is counted in the record; an exporter hook is a separate wiring change).

## Measures (docs/measuring.md §0), frozen sample, ADJUDICATE replay of slices carrying the 2.190 shapes (`build_slices_2_190.py`), flag OFF vs ON
Final run (single-class accidentals exempt, see below), `lane_report --tag out/slices192`:
1. WHAT CHANGED IN THE FILE. Litolff: accidentals -3, pitches ~7. Brahms: accidentals -8 +3 (the +3 are the KEY flat the note keeps once the phantom
   `##` is gone), ties +2, pitches ~15, blue marks +1. Red bars 266->266 / 166->166, notes not written unchanged. 14 notes change in all; all 11
   removed `##` are on an eighth rest (my crops of the 9 tiled: 9 of 9 eighth rests).
2. WERE THEY RIGHT: Sean's tiles `out/print/2.192-phantom-accidental/tiles/sheet.png` (key `key.json`, outside the folder): 9 changes (Brahms 7,
   Litolff 2, seed 2192), 2 controls the flag leaves alone (a rest whose ink the shape reader reads as a sharp), 1 plain natural. Question: "What is in
   the orange box: a rest, an accidental (which one), or both?" NOT YET ANSWERED.
3. SEAN'S JUDGED ANSWERS RIGHT->WRONG: 0 (Litolff 254 tiles, Brahms 232).
Reach, from the sample's contested pairs (IoU >= .5 with a kept rest, `sample_contest.py`): Brahms 68 double sharps (+3 single class), Litolff 9 (+1).
Of the 68 Brahms: 12 read clearly `sharp` (the rest's bulb+stem reads as a sharp) and are NOT refused -- still phantoms; 5 read natural and 6 flat
(refused); 45 unclear (refused, rule 8). Only 11-12 of the ~77 contested change the file, because most never own a head.
FIRST RUN FAILED A TWIN: with every class covered, one REAL flat touching a rest box (shape read `sharp`; its stem reaches the top) lost its accidental
(tile 7 of that run). The refusal is now confined to the double classes (`ON_REST_CLASSES`) and a test pins it. The cut-offs are a measurement on two plates.
Open: (a) 12 of 68 rest inks that read `sharp` stay phantoms -- a rest-shape reader (not the accidental shape reader) is the next lever; (b) the
no-rest-box 165 / 64 rest inks; (c) the refused case is counted in the record (`on_a_rest`), not yet written blue on the note.
