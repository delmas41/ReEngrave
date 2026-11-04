# 2.261 — the 20261103-night regressions (STAGED; Sean 2026-11-04; LANDED ON, main a15a52cf9)

Filed by the manager from the lane and landing reports (a hook refuses report files from subagents).

## Why
Overnight 20261103-night vs 20261031-night, Litolff: 3 judged answers went right->wrong and notes reaching the file dipped 8914 -> 8894. A read-only trace (records only, no gathers) found three landings responsible: 2.254 hairpin reach (2 of 3 tiles), 2.252 tall-head split + the pitch rule (litolff_02 -- left to the 2.260b position follow-up), and 2.251's clef carry (27 notes unpitched).

## Fixes (all default ON)
1. **`OMR_HAIRPIN_NOT_A_BEAM`** (GATHER). Cause: the reach reader strips every vertical stroke >= 1.2 sp before it looks, so a beam between two stems is an isolated straight bar it cannot tell from a short hairpin. Rule: a reach find with a stem at both end columns of the raw ink is refused `beam_between_two_stems`. A detector-beam-box rule would have been wrong (12 of Brahms' 68 wedges sit on beam boxes). Lesson: a detector class box is not evidence of ink kind where two marks share ink -- test the structure.
2. **`OMR_WORD_RETRY_SPARES_HEADS`** (GATHER). Cause: 'faster', read only on the through-line retry, is a tempo word, so `claims.metronome_mark` took the first head as its metronome note and claimed the ink right of it. Rule: a retry-only word with no '= n' read takes no metronome note and claims no ink inside detector notehead boxes. Lesson: a second look that replaces a refusal is a weaker witness than the first.
3. **`OMR_CLEF_CARRY_STRONG_STOP`** (EVALUATE/EXPORT). Cause: `clef_in_force` stopped at any later candidate; 33 of 80 Litolff candidates are small detector clef boxes with no body score (a G box on an eighth rest, F boxes after a bass clef). Rule: such a candidate is counted and no longer stops the carry; body-witnessed F clefs (Sean 11-02: bar 111, Vc 346) still stop. Lesson: a same-gather control needs `readjudicate.py` (lane_report gather mode keeps OFF verdicts in a reused record).

## Measures
- Lane: fix 1 Litolff p3+p6 / Brahms p8+p19 -- one wedge lost (the false p3 one), Brahms 68/68 wedges kept; fix 2 -- the real dynamic f now claimed, one bar (staff p6/1/9 bar 25) now unread red instead of a chord missing a head; fix 3 Litolff p6+p14 notes +28, beams +14, accidentals +5, 'clef?' marks -14, Brahms p4+p5 unchanged. Judged right->wrong 0 on all.
- Landing gate: fast tier 9906 passed, 0 failed; real gather Litolff p3+p6 OFF vs ON: notes +31 -3, accidentals +5, beams +18 -2, blue +17, notes not written 625 -> 597; judged right->wrong 0, wrong->right 2 (consistent with the two target tiles; not looked up one by one).
- Sean's tiles (answers-2.261.json): 12/12, 0 written wrong (tile 6: OFF's quarter where Sean reads a half note is now unwritten, not wrong; tile 9's natural is printed).

## Open
Litolff p2/p4 beam-box wedges untested; litolff_02 (tie->slur via `_two_note_reading`) belongs to the 2.260b position-everywhere follow-up.
