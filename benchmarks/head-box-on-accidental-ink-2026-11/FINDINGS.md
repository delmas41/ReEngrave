# 2.347 — a head box on an accidental's ink is refused

State 2026-11-25: BUILT, flag OFF, NOT LANDED. Wrong on 1 of 12 notes it removes (Sean's tile below).

## The rule

STAGED, GATHER `notehead_precision`: a head box sitting on an accidental's ink is refused.
Flag `OMR_HEAD_BOX_ON_ACCIDENTAL_INK`, default OFF. Branch `origin/lane-2.347`, tip c105dee92.

## What changed in the file (replay, OFF vs ON, remaining pages of the frozen sample)

- 12 target notes leave the file; none enter.
- 4 more targets were already refused in both arms (no note either way).
- Judged right->wrong 0 on the tiles judged at that time (443 Litolff / 433 Brahms).

## Who says it's right

- Manager crop look at the 12 leaves: 11 are plainly a box on a sharp; 1 unclear
  (Litolff `glyph/10/1/9/0/5`).
- That one went to Sean. Question: "Is the ink in that box a notehead?"
  Sean, 2026-11-25: **"That is a notehead but the stem ink is broken"**.
- OURS: the rule refuses a real head here, so it is wrong on 1 of 12. The flag stays OFF.
  This mark is now a judged control for the rule (CLAUDE rule 7): the rule must keep it.

## Side effects, not looked at

- 7 "does not add up" words clear.
- Litolff p13: a neighbour F3 becomes F#3.
- Brahms p7 / p11: two wedges gained, one slur lost.

## Not measured

- Brahms p21: the replay of Brahms rows 17-21 stops with `UphillConsequence` in
  `reinstate_rest_between_staves` in BOTH arms — a separate, untraced fault.
- The 17 Brahms p6 control differences came from `OMR_BAR_SUM_SKIPS_REFUSED` landing on
  main, not from this rule.
- Nothing is measured on a whole movement.

## Evidence status

The raw replay records were deleted for disk space. The 12 crops are in
`out/print/2.347-leaves/`. The counts above rest on the lane agent's report and cannot be
re-derived without a new replay.

## Cause of the page-10 refusal (trace 2026-11-25, saved 20261123-night record, no page read)

The fault is upstream of this rule, in the 2.336 sharp reader that is ON in main.

- STAGED GATHER `page_accidental_ink.sharp_stacks` claimed page strokes 675 and 678 (stroke map:
  `head|head`) as one sharp: `claimed_area` obs:382073, `fused: sharp_stack`, area
  [621, 3466, 645, 3509], 1.46 sp wide by 2.61 sp tall.
- ADJUDICATE `notehead_precision._on_an_accidentals_ink` then refused the head box: it owns one
  sliver stroke, and the claim holds 0.88 of its ink. The rule decided correctly on what it was told.
- Why the reader passed the ink: its stem guard counts only a stroke of kind "vertical" (stroke 678
  is 1.60 sp long but kind "blob": the broken stem is merged into the head); a stem stub at the top
  passes the narrower-end test (about 0.30 sp against a 0.35 sp limit -- a raster ESTIMATE, not the
  reader's mask); `head_beside` has no barline guard and took a half note in the next bar.
- Both sides, measured on real marks: claim width 1.46 sp here against 1.04-1.27 sp on the 11 true
  sharps; height 2.61 sp against 2.74-3.24 sp. This rule's own measures do not separate them: held
  share 0.88 here, 0.539-0.913 on the true cases.
- On main today, flag OFF: boxes glyph/10/1/9/0/4 and /8 sit on the same claim and are refused.
  Not checked whether they are real notes.
- Who says: Sean's tile says box 5 is a notehead. "Two heads stacked a third apart" and the
  stem-stub mechanism are OURS, from a rough raster, not confirmed. The taper was looked at on 3 of
  the 11 true sharps only.
- Process lesson: a rule that refuses a box because another reader claimed its ink is only as good
  as that claim. Fix goes to the reader: ROADMAP 2.352.

## Open

ROADMAP 2.352 landed 2026-11-25 (below); 2.347 is to be re-measured now that the false claim is gone.

## Landed 2026-11-25: rounds 2-4 (ROADMAP 2.352, no flag)

Four grounds on which the sharp reader (STAGED GATHER `page_accidental_ink.sharp_stacks`) no longer claims a block of ink as a sharp:
1. Always the same bar (Sean: "Always same bar"): a sharp never takes its note from across a barline (reason `note_across_barline`).
2. The note is near, ink to ink: 2.5 sp (quarter rest 3.55 sp, true sharps <= 0.7 sp, unjudged <= 2.1 sp); no note beside is counted as `no_note_beside`.
3. Not narrower than about two-thirds of a sharp (the sf fragment measured 0.51); counted `too_narrow`.
4. A sharp is not two hollow heads: one window of paper, never three or more (Sean's tiles: Litolff p13 and p4 are "two half notes, a third apart").
Round 4 added the tie rule: where the ink gap ties between the two boxes of one note, the sharp goes to the note on the staff its own ink is printed on, else main's choice stands and is counted (`fused_stack:head_tie_kept_main`).

Both sides, from the ROADMAP row: 15 pages rebuilt from saved records: 12 judged sharps kept, 0 of 574 labelled/judged noteheads read as an accidental, 5 claims lost vs main (all five judged NOT sharps by Sean), none gained. Real page reads, main vs r4, Litolff p2/p4/p6/p12: the five judged non-sharps go, the p12 sharps stay, two sharps main lost to the same tie are gained (p2 G#4, p12 F#5; Sean: "There is a sharp in front of those notes").

Sean's nine tile answers: `out/print/2.352-declined/answers.json` `out/print/2.352-r2/answers.json`, `out/print/2.352-r3/answers.json`, `out/print/2.352-r4/answers.json` (answers by reference; the count is not re-tallied here), plus the earlier glyph/10/1/9/0/5 answer.

Lesson (list-order tie): round 3 lost two real sharps that only a real page read caught. The replay counted claims by ink box and could not see WHICH head got the sharp; a tie in the ink gap between the two boxes of one note was decided by list order. A replay that counts claims cannot test an assignment; read a real page.

Frozen sample, main vs r4 (16 pages): Brahms file unchanged; Litolff changes only on p2/p4/p10, all judged by Sean (a sharp gained on p2, false sharps gone on p4 and p10, one eighth gained on p10); no note and no real sharp lost; red bars equal (Litolff 126, Brahms 108); judged right->wrong 0, unwritten->wrong 0, no judged tile changed. Open: one half note written where Sean sees two (head reader, 2.351); numbers measured on two plates; not measured on a whole movement.
