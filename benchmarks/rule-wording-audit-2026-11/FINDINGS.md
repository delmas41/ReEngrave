# 2.309 rule wording audit -- FINDINGS

A study (Fable lane, 2026-11-15). It changed nothing: no rule, page fact, DECISIONS line or code was
reworded. `INVENTORY.md` is its table of 124 rules; `STUDY.md` its full report. Everything below is an
observation or a SUGGESTION for Sean to rule on.

**Sean, 2026-11-15:** "It seems like there is a trick to only being specific when it is required - otherwise
being specific can get in the way." / "audit all our rules and see where our wording is too specific or too
general - or where we may be mixing evidence language with rule language."

**Cause.** The wording goes wrong at HAND-OFFS, not at the source. Sean -> DECISIONS -> page-facts -> CLAUDE
short form -> brief -> docstring -> constant: each step either adds a number, a box or a mechanism, or drops
the limit. (ROADMAP 2.306: "the vertical stroke its head touches on the engraving side"; the docstring
written from it: "its centre line within `EDGE_SP` of the head's RIGHT edge".)
**Lesson.** We have a rule for where a number comes from ("a cut-off is a measurement") and one for where a
ruling applies (its scope); none for the sentence itself -- who said it, at what level, with what never.

**Counts** (124 rules; a wide sample leaning to recent stem and arc work, not a census): worded as the
convention with its limit 64 (about 40 are Sean's sentences quoted); too specific 22 (cost verified 15); too
general 16 (cost verified 7); evidence language in a rule 8 (cost verified 0); rule language in a finding 4
(3); the same rule in two wordings 10 (5). Of the 22 too-specific: lanes 10, code 5, manager wording 5,
Sean's "Yes" to a question we worded 2 -- **Sean's own words 0**.

**(a) Sean's observation holds on this sample.** Over-specific wording is more common and costs more often.
The two failures are one failure in two steps: a rule stated with no limit fails, and a lane patches it with a
number or a box ("binds to the CLOSEST note, no fixed reach" bound a head 83 spaces away, then four reach
numbers; r1 "the whole collinear run" became r4's box test that stitched stems over blank paper).
Over-general rules were caught sooner (Sean's crops); over-specific rules pass their own controls.
**(b) Where specificity earns its place:** a boundary where two readings both fit, both named (higher note
right of the stem = a second, left = two voices); a scope; a number that comes from the notation (0.75 sp
between a second and a third); a cut-off with BOTH sides measured on real marks and a gap between
(`SIDE_MIN_SP` 0.25) -- unlike `EDGE_SP` 0.4 (one side only). The manager's hypothesis was right but missed:
the limit must be worded as a convention too ("never over blank paper" became "<= 0.3 sp on a box"); an
abstention is a decision (with no old reader beside the new, every decline is a mark not written); a box
standing in for the ink is one fault found four times; a "Yes" carries the asker's words; short forms drop
limits (CLAUDE section 5 "Stems: up -> right, down -> left" lost "reads only an isolated head"); and the
convention was sometimes already written and not read (registry L19, a second straddles the stem, predates
the r4 rule that refused it).
**(c) Generalising Sean's words.** Generalised beyond what he said: "binds to the CLOSEST note" from
"Closest note works"; "the ONLY far-head position witness" from "I lean towards just focusing on ledger
lines"; "read from POSITION" from "the same note to the same note". Kept too narrow: his r1 "a long stem on
a chord" built as gap exceptions; "through its touching mates". The good cases quote his words with what
they answered, label our reading ours, go up ONE level (tile -> that symbol's convention) and put it back to
him in a musician's words with the nearest case where it might not hold.
**(d) Code.** Reason strings mostly carry rule language and it matters (`no_stroke` was one bucket over five
causes and the manager guessed the wrong one). Rough count: 1,058 module-level numbers under
`tools/omr/staged`, 744 with no "measured / Sean / plate / convention" word beside them.

**Suggested, NOT adopted:** a short "How a rule is worded" addition to CLAUDE.md section 4 (five lines, and
a three-line variant) and ten rules to reword -- both in `STUDY.md`. Not read by the study: most of DECISIONS
beyond its newest 75 lines (search only), most of the registry and ink-rules, the rhythm/duration rules.
