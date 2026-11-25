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

## Open

Why the rule takes the Litolff p10 head: cause not found. Unchecked guess (OURS): the broken
stem leaves the head with nothing marking it as a note, and the sharp's ink beside it claims it.
