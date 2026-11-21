# A notehead is measured on its own ink, not its box (ROADMAP 2.327), 2026-11-19/20

STAGED, GATHER + ADJUDICATE. Filed by the manager from the lane agent's report; branch
`lane-2.327-head-own-ink` 84a58ee22. Both changes built OFF. Crops `out/print/2.327-slash-guard/`.

## Cause, and what it teaches

Each of the three gates 2.326 named was replayed on marks Sean has judged, from both sides. TWO OF THE THREE
ARE GUARDING REAL CASES; the fault that wrote a judged half as a quarter was a fourth, hidden box measure.
- **Box size gate (a) -- kept.** Sean's sharp at the barline (`glyph/2/0/7/4/5`) reads on its own ink as one
  hollow head-sized mark (1.19 x 1.25 spaces, slit 0.33). On Litolff only width separates it from the 20
  judged halves (1.46 and up), and Brahms halves go down to 0.97 wide: no own-ink measure separates them on
  both plates. On Brahms, rests, a meter sign and "arco" also read hollow on their own ink.
- **Width cap (b) -- kept, boundary open.** Above 1.75 spaces the judged eighths `glyph/2/1/7/13/1`, `/3` and
  Sean's "1 beam" eighth `glyph/2/1/10/0/1` read hollow on the paper BETWEEN two black heads; the cap stops
  them but also refuses real heavy halves up to 2.03 wide (`glyph/6/1/5/11/1`, still written a quarter).
  Width alone cannot settle it.
- **The unknown guard -- the cause of the wrong half.** The 2.159 slash guard drops a hollow head when "ink
  crosses the stem", and that test reads the DETECTOR BOX. On `glyph/2/1/0/11/2` the box is wider than one
  head and takes in the ledger-line stubs crossing the stem: the half was written a quarter.
- **Trim below the head (c).** On 6 of the 11 Brahms solids the head's rows ran down into paper held between
  the stem and the next stroke (a row counted as head when its first and last ink are far apart, even from
  two strokes). The other 5 read hollow from one speck in a black head -- the same boundary as Sean's "slit
  closed to specks is still a half" -- left alone.

Lesson: before calling a gate "tuned to one plate", replay it on judged marks from both sides. A box measure
hidden inside another reader (the slash test) is the same fault as a box gate; the brief's three gates did
not cover it. (Manager: the 2.326 outcome named three gates from counts, not from replay.)

## What was built (both OFF)

- `OMR_SLASH_GUARD_OWN_INK` (`rhythm._head_ink_reads_hollow_unread_black`): a hollow one-head reading on a
  box that is not head-sized is stopped only where the stem's own stroke reader read a slash, or all three
  slash tests fire, or the ink crosses the stem AND sits on its shaft. Crossing alone no longer stops it.
  Sean's 2.159 Brahms slash (`glyph/16/1/10/0/7`) and the Litolff half have nearly the same crossing signal
  (8.8 vs 8.7 degrees); only "on the shaft" separates them, and that is still read on the box. The result
  stays blue (GUESSED); nothing becomes plain.
- `OMR_HEAD_OWN_ROWS` (`head_ink.trim_head`): the head's rows end where its rim does -- a top or bottom row
  with no ink across the head's middle is not the head's.
- `lane_report.GATHER_MODULES` gains `head_ink.py` (without it `--from auto` replayed the trim at ADJUDICATE
  and reported a clean zero).

Controls, `tools/omr/tests/test_head_own_ink_2_327.py`, 11 tests on real crops: the two wrong Litolff halves,
six judged blue Litolff halves, the sharp as the never (stays blue), the eighth between two black heads, the
Brahms slash (never a half). The two control tests fail on main's behaviour.

## Measures (shared `lane_report`, frozen sample)

Slash guard, `--from adjudicate` (neither arm matches the night's record; the tree moved, same in both arms):
- Litolff: notes +2, accidentals +1, note values ~1, blue +3, words -2. Brahms: nothing.
- Judged right->wrong 0 both plates; wrong->right 1 (the judged p2 half, now a blue half).
- The 2 new notes are unjudged: Litolff p4 `4/1/1/4`, newly written blue halves; by the agent's and the
  manager's eye, hollow heads on ledger lines above the staff (tiles 1, 2; tile 3 is the judged half).
- The words -2 are not traced.

Trim, `--from gather --cell-map master`:
- Litolff: notes +1, flags +1, pitches ~2, blue +3 / -1. Brahms: notes +3, accidentals +1, ties -4,
  articulations +1, blue +1 / -5, wedges +1, words +-1. Judged right->wrong 0.
- It ripples into other readers that use the trimmed head: two ties lost on a Brahms dotted-half chord, an
  eighth gained in beamed chords on Litolff p4, a pitch moved on Litolff p9; none judged. STAYS OFF.

Fast tier (serial): 10,927 passed, the one known failure; not re-run whole after a flag-doc fix.

## Open

`glyph/6/1/5/11/1` stays a quarter (no new cut); five Brahms solids still read hollow from a speck; ruling on
(c) means auditing every reader that uses the trim; the lane's runs peaked at ~14-16 GB against a 4 GB brief.
