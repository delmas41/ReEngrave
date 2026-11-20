# A unison in a two-voice bar, printed once and kept for both parts (ROADMAP 2.323), 2026-11-19

STAGED, EXPORT. Filed by the manager from the lane agent's report; branch `lane-2.323-unison-both-parts`
292ea909f (checked: on origin, 6 files, export.py/lilypond.py/lane_report.py + tests). Flag
`OMR_UNISON_KEPT_FOR_BOTH`, built OFF, NOT on main.

## Cause, and what it teaches

The 2.314 r5 writer had already decided that a lone mark in a two-voice bar speaks for both players, but wrote
it as `<forward>` in the other voice -- which says "this player prints nothing here" and a part extraction
reads as silence. The decision was encoded as an absence. Lesson: an encoding must carry the decided fact,
not its printing consequence. Second lesson (the agent's first run): sample slices that drop Litolff page 1
lose the meter and show zero effect -- context pages ride along.

## Built (flag ON)

The other voice carries the same note/rest/chord across the lone mark's stretch, written
`print-object="no" print-spacing="no"`; keeps pitch, value, dots, tuplet, ties (a tie stays only if its
partner is in the same voice); no slur, beam, articulation or accidental. Our `.ly` is byte-identical ON vs
OFF (the copy is a skip), so the engraved PDF is unchanged. Silence before a mark stays a forward.

## Measures (`lane_report`, `--from adjudicate`, 20261117-night, frozen sample)

| | Litolff | Brahms |
|---|---|---|
| printed notes and rests gained / lost | 0 / 0 (5695 paired) | 0 / 0 (6747 paired) |
| not-printed copies added | 52 | 32 |
| forwards | 198 -> 148 | 116 -> 87 |
| red bars | 158 -> 158 | 137 -> 137 |
| judged right -> wrong | 0 | 0 |

Control line: neither arm reproduces the overnight record (tree drift, identical in both arms); OFF is
byte-identical to an `origin/main` export on Litolff p1, 2, 4 and Brahms p0, 4, 5. Forwards left outside
unread bars: 1 per plate (a voice that has ended while the other's longer note still sounds). Fast tier
10933 passed, 1 failed (`test_far_head_note_first_2026_10_05 ... [ledgers1-204]`, fails the same on main).

## Controls

17 tests, fixtures cut from the record's real events; with the flag forced off 5 fail + 1 error. Sean's named
bars are NOT written as two voices by the record (bassoon 81 one voice; 82 declined, a glyph not written;
horn 91 declined, its dot not read; horn 93 one voice, D untied), so the controls are bassoon bar 80 and horn
bar 92 (his tile 4). No copy on the sample carries a tie; the tie tests set tie flags on a real event.

## Open before the flag can go ON

1. Chords: a chord on one stem is copied whole, so both players get both notes. Bassoon bar 80 (two notes, one
   stem, two ties) looks like one note each. Sean's rule says "a single note or a single rest". With Sean.
2. Solo markings: nothing reads "1.", "2.", "Solo" (the direction lexicon does not carry them), so the zero
   found in the 49 copy bars is blindness, not evidence. "a 2" is read 18 times on the Brahms sample.
3. Other engravers: Verovio flips a stem where the hidden copy sits; `musicxml2ly` ignores `print-object` and
   would draw the copies. Our own PDF is unaffected.
Not run on a whole movement. Crops and renders: `out/print/2.323-unison/`.

## Round 2 (2026-11-19): the unison rule goes by the staff's instrument

Branch `lane-2.323-unison-both-parts` f205c8167, flag still OFF, main merged in. STAGED, EXPORT only.

**Cause and lesson.** Round 1 copied every lone chord whole to both players. Sean's rulings the same day
("One note each"; strings keep the chord; timpani, harp and piano are one player per staff) make it depend on
whether the instrument can sound several notes at once, and the record already names the instrument of every
staff. Lesson: take the instrument from the identity layer (the part's name, what `<part-name>` writes), never
from the chord's shape -- and from the PART's name, not the single run's: the first version read the run's own
name and sent 15 copies on Litolff to "not known".

**What it does.** Woodwind and brass: a two-note chord stays printed; the other voice gets a not-printed copy of
only its own note (printed in voice 1 -> lower note to voice 2; printed in voice 2 -> upper note to voice 1). A
chord of three or more notes is left as flag OFF writes it and counted. Strings: the whole chord is copied.
Timpani, harp, piano, and a staff whose instrument is not known: written as flag OFF, each under its own counter.
Brass taking the woodwind rule is OUR reading; Sean named the woodwinds and the strings.

**Controls (real pixels, each fails on the wrong code).** Brahms bassoon bar 80 chord: copy is the upper note
only (round 1's code gives both). Litolff p16 cello bar 256, C2+G2 double stop: kept whole as a string, lower
only when the same events are run as wind. Three-plus chords, one-player staves and not-known staves do not
occur on the sample: unit tests with the family set by the test only.

**Measures (shared `lane_report --from adjudicate`, 20261117-night, frozen sample).**
- Litolff: printed gained/lost 0/0; 52 not-printed copies (rest 33, note 16, whole string chord 2 counted
  whole-file); bars with a copy wind 34, string 8; `<forward>` 198 -> 148; red bars 158 -> 158; judged
  right->wrong 0.
- Brahms: printed gained/lost 0/0; 29 copies (rest 16, note 10, lower-of-chord 1, upper-of-chord 2); bars wind 9,
  string 2; `<forward>` 116 -> 87; red bars 137 -> 137; judged right->wrong 0; `.ly` byte-identical ON vs OFF.
- Fast tier 10943 passed, 1 failed (the known `test_far_head_note_first_2026_10_05 [ledgers1-204]`).
- Control line: neither arm reproduces the overnight record; the tree has moved, identically in both arms.

**Solo look (an agent's look and the manager's, not a reader; `out/print/2.323-solo-look/`, 39 Litolff + 11
Brahms tiles of every bar that gets a copy).** No "1.", "2." or "Solo" seen inside any bar. Brahms tile 1
(page 4, clarinets) has a printed "a 2" in the bar: that says both play, which agrees with the copy. Litolff
tiles 20 and 25: the "l." in the left margin is the tail of the staff label ("Cl.", "Fl."), manager's look.
Limit: coarse scans; still no reader for a solo marking.

**Open.** (1) Nothing in the file says which printed head of a two-note wind chord belongs to which player; a
part extraction reading the printed voice still sees both heads. Belongs with part extraction. (2) No solo
marking reader. (3) Other engravers (Verovio, `musicxml2ly`) as in round 1. (4) Not run on a whole movement.
