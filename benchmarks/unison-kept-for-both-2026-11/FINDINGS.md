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
