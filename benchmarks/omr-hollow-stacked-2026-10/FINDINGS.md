# ROADMAP 2.132 -- hollow stacked heads

2026-10-14/15, branch `lane-2.132-hollow-stacked` (b0a916c5), flag `OMR_STACKED_HOLLOW_PAIR` default OFF. Written by the
manager from the lane's report (the lane's Write tool refused this file). Scripts/outputs: `probe/`, `out/`.

## Brief correction
The "bass clef" control `glyph/0/0/11/7/1` is the 8 of a printed 9/8, not a clef (crop `out/tile0_big.png`). The real
bass clef used as a control is `glyph/18/1/3/7/20`.

## What the hollow refusals are (Brahms 20261013-night)
27 hollow `stacked_head_duplicate` refusals: 21 rows = 19 chords of two real hollow half notes a third apart (Sean's
2.129 tile 9 is one); the rest are controls -- a numeral (the 9/8 '8'), a clef, two boxes 3.5 spaces apart, one ghost
box, one half+black pair.

## The test (page raster, staff-line rows left out, measured locally)
* Two slots a third apart, each a hollow head: centre ink <= 0.75, ring >= centre + 0.10 and ring >= 0.55; the best
  placement clear of the second by 0.10.
* A second source beside the hole test: ONE stem reaches both heads and runs >= 1.5 spaces past the pair. Real chords
  2.2-4.1 spaces; the numeral 0.15; the clef 0.13. The stem is the LONGEST reach among stems at either edge of the heads
  (taking the first overlapping stem refused real Litolff pairs).

## Measurements
* Truth Brahms pdf 0: no hollow pair a third apart in Sean's truth; its one hollow chord pair (q711/q712) is a single
  head boxed twice and stays one head. Record and MusicXML identical OFF vs ON on pdf 0 -> 0 false keeps.
  `judged` unchanged (Brahms 51/5/8/1/39, Litolff 56/8/2/1/62).
* A/B Brahms: 18 of 19 chords kept (+1 chord previously written twice at one pitch now two pitches). Notes written up on
  pages 3, 7, 8, 10, 12, 18, 21 (by 1/1/1/6/6/2/2); pages 0-1 and 25 unchanged. Still refused: `glyph/25/1/5/9` (its stem
  starts below the upper head). Tile 9's pair kept (B3/D4).
* A/B Litolff pp0-3: 7 groups kept, notes 819 -> 824 -- NOT confirmed (need Sean's tiles).
* Bars held: unchanged.
* Cost: a two-note chord makes tie pairing abstain (`more_than_one_pair`): ties 41 -> 38 (Litolff), 36 -> 33 (Brahms p10).
  The downstream tie rule abstaining on a chord, not fixed here.
* Tests: new tests red first (16 failed before the code); fast tier 8029 passed; `staged.check` 192.

## Open
* The stem-reach criterion is tight; pitch follows the slot grid; the Litolff chords need Sean's answers.
* Tiles: `out/print/2.132-review/` (15, hidden manifest): Brahms kept chords, Litolff kept chords, one refused chord,
  the numeral, the clef, a line-cut head. Sean's answers decide the default.
