# ROADMAP 2.102 -- tuplets, meter signs, tremolo slashes (STAGED)

Sean's held-out tiles 6, 10, 11, 17 (2026-10-12; 2.101). Separate file from the 2.101
`FINDINGS.md` (not on main yet) to avoid an add/add conflict; fold in at landing.
Method: INFER-only replay (`p102_diff.py`) and ADJUDICATE re-run (`p102_readj.py`) over saved
records, base = the rule before 2.102 on the same record; the re-adjudication reproduces the
record exactly apart from the intended rows (Dvorak 1,101 of 1,111 same; Schumann 1,872 of 1,882;
Tchaikovsky 602 of 611). Records: held-out `*-arm2` (= main `f5f43143`) and the `20261011-night` pair.

## Causes
- Tile 6 (Dvorak 8 p4): a real triplet, but the record holds ZERO tuplet/fingering3 boxes; a marker
  check cannot see it. The arithmetic landed it as eighths.
- Tile 10 (Schumann 2 p3): NOT a tuplet. Six two-note columns (heads 3-13 px apart, ~115 wide) were
  grouped as 12 events; 12 eighths "landed" 6/4 where the print has six quarters.
- Tiles 11, 17: `adjudicate_notehead_is_not_a_notehead` had ALREADY refused both (`too_narrow`;
  `tremolo_slash_crosses_stem`); `adjudicate_duration` did not read that verdict and read the box's
  ring-vs-centre ink as a hollow head.

## Guards and what they remove (INFER bare-stem settlements)
| record | before | after | removed by |
|---|---|---|---|
| Dvorak 8 (4 pp) | 18 | 16 | tuplet_possible 2 (tile 6's bar) |
| Schumann 2 (4 pp) | 117 | 105 | simultaneous columns 12 (tile 10's bar) |
| Tchaikovsky 4 | 0 | 0 | |
| Litolff 20261011-night | 130 | 129 | simultaneous columns 1 (p11 `glyph/11/0/0/8/2`, tile 10 of the 2.102 set) |
| Brahms 20261011-night | 29 | 29 | none |
Sean's no-eighth-without-evidence rule then removes every remaining shortening: eighths settled
before = Dvorak 2, Schumann 12, Litolff 10, Brahms 0; eighths surviving = 0 on all (the evidence
test: the stem's own `levels_certain`/`levels_possible` >= the candidate's beam levels; none holds
one). The tuplet guard on Litolff's 13 markers / 3 decided ratios removes nothing there.

## (b) duration verdicts changed by `not_a_note_mark`
Dvorak 10 (tile 11 and 6 more meter-column boxes, 2 tremolo), Schumann 10 (tile 17 and 9 more:
tremolo 9, dynamic letter 1), Tchaikovsky 9 (3 dynamic letter 2, meter-column 7), Litolff 120
(tremolo 61, dynamic letter 53, meter column 11: all already-refused heads). Control: all other
verdicts identical. Caveat: Tchaikovsky tile 5 shows a `too_narrow` box that is a barline piece
sitting in a "meter column" because that plate's `timeSig*` boxes are not validated; the outcome
(not a note) is right, the reason word is only positional. The refused-head hollow gate was tried
(it narrowed 53 Litolff halves on duplicate/stacked refusals) and removed: out of scope.

## Tiles
`out/print/2.102-review/` (10, phone-sized; subject = blue brackets; readings in manifest.json only).
