# ROADMAP 2.102 -- tuplets, meter signs, tremolo slashes (STAGED)

See also: FINDINGS.md (the 2.101 held-out check and Sean's 17 tile answers).

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

## Brahms (Breitkopf, night 20261011) -- added after the run finished
Re-adjudication: 32,389 duration verdicts, 31,434 same, 955 -> `abstained not_a_note_mark`
(`too_narrow` in a "meter column" 798, tremolo slash 112, dynamic letter 45). All 955 were ALREADY
refused as noteheads (not exported). The 798 are mostly barline pieces on a SHATTERING plate that
sit in the column of mis-detected `timeSig*` boxes: the outcome (not a note) is right but the
`meter_sign_column` word is positional only, and the count is large. Not run: the hand-truth scorer
on Brahms pdf 0.

## Sean's answers on the 11 tiles (2026-10-13) -- 11 of 11 right
Verbatim: *"1. C meter 2. 4 rest 3. Barline ink 4. 2 5. 4 6. Part of a barline 7. Trem slashes 8. 4 tuplet 9. 4 10. Part of a barline 11. Part of a barline"*
(`out/print/2.102-review/answers.json`, each tile with our reading and a verdict).
- Refusals right (not a note): 1 (C meter), 3, 6, 10, 11 (barline pieces / ink), 7 (tremolo slashes). Tile 2, labelled
  tremolo, is a quarter REST: "not a note" is right, the reason word `tremolo` is wrong for that mark.
- 5, 8, 9 were eighths settled by bar arithmetic and are QUARTERS (8 in a tuplet). Narrowing them was right; tile 9, the one
  Litolff "cost" in the numbers above, was a WRONG eighth, so that cost was a correction.
- Control 4 (unrefused hollow head still read as a half): right (a half).
- Caveats: the reason words are positional (3, 6, 10, 11 are barline pieces in a "meter column", not meter signs); tile 11 has
  no entry in `manifest.json`, so its `our_reading` is null in `answers.json`.

## Hand-truth gate, Brahms 317803 pdf 0 (ADJUDICATE only, origin/main 21ddeb21 vs this branch)
Both trees re-adjudicate page 0's rows from the night-20261011 record (so the base is today's origin/main tree, not recorded
verdicts). The hand-truth page carries NO durations (the scorer files standing only), so right/wrong cannot be scored; what can be
said: 507 duration verdicts, base decided 422 / narrowed 75 / abstained 10 -> arm decided 421 / narrowed 73 / abstained 13.
Exactly 3 verdicts differ, all to `abstained not_a_note_mark` (2 were narrowed `beam_discounted_uncertain`, 1 was decided
`head_and_marks`). No verdict became decided or changed value, so no wrong can be added. Whether those 3 boxes are non-notes is
not crop-checked here.

## Revision 2026-10-13 (Sean: a tuplet exists only where its 3/bracket is SEEN)
The hidden-3:2 inference is gone. `solve_bare_stem_bar` declines a bar only where a tuplet marker is
seen and no ratio was decided (the members are then unscaled); a decided ratio sums as usual; three
unread stems never imply a triplet. Final settlements (all written quarters, none eighth; Brahms'
1.5 are dotted): Dvorak 16, Schumann 105, Tchaikovsky 0, Litolff 120, Brahms 29. Tile 6's Dvorak
bar (no marker detected anywhere on the record): plain sum forces eighths, refused for lack of stroke
evidence, so all 4 stems stay narrowed (0 settled). Its quarter reading comes from the shape (no
flag/beam read), not from arithmetic.
