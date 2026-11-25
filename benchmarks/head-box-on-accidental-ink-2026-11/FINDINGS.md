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

ROADMAP 2.352 (the sharp reader's claim); this rule waits on it.
