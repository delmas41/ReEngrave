# 2.309 rule wording audit -- DRAFT (scratch only; observations and suggestions, nothing changed)

STAGED throughout unless said. Read at origin/main 63f5236de plus the 2.306 and 2.305 lane branches.
The table is `INVENTORY.md` beside this file (124 classified rows + 6 template rows). It is a wide sample,
not a census: see "Not read" at the end.

## Cause and process lesson

**Cause.** The wording goes wrong at hand-offs, not at the source. Sean's own sentences are almost always at
the convention's level. The ROADMAP row for 2.306 said "a stem is the vertical stroke its head touches on the
engraving side"; the module docstring written from it said "its centre line within `EDGE_SP` of the head's
RIGHT edge". Each hand-off (Sean -> DECISIONS line -> page-facts -> CLAUDE short form -> lane brief ->
docstring -> constant) either adds a number, a box or a mechanism (too specific) or drops the limit (too
general). Nothing in the files says which sentence must travel unchanged.

**Process lesson.** We have a rule for where a NUMBER comes from ("a cut-off is a measurement") and a rule
for where a RULING applies ("every ruling carries its scope"), and no rule for the SENTENCE: who said it, at
what level, with what never. The registry (`docs/engraving-conventions.md`) already keeps Says / Numbers /
Measured here / Would be falsified by / Known exceptions in separate fields; page-facts, DECISIONS and the
docstrings do not.

## Counts (from INVENTORY.md)

| class | rows | cost verified in the text | cost inferred | no cost found |
|---|---|---|---|---|
| 1 worded as the convention, limit stated | 64 | - | - | - |
| 2 too specific | 22 | 15 | 2 | 5 |
| 3 too general | 16 | 7 | 1 | 7 (+1 n/a) |
| 4 evidence language in a rule | 8 | 0 | 1 | 7 |
| 5 rule language in a finding | 4 | 3 | 0 | 1 |
| 6 same rule, two wordings | 10 | 5 | 1 | 3 (+1 n/a) |

By who worded it (hand count; the script's source column is rough):

- **Too specific (22):** lanes 10, code 5, manager's build wording or paraphrase 5, Sean's "Yes" to a
  question we worded 2. **Sean's own words: 0.**
- **Too general (16):** our reading of Sean's words 4 (PF02, PF23, PF47, C15), manager 3 (C10, PF03, PF38),
  lanes 3, code 2, Sean's "Yes" to ours 1, Sean's own words 2 (D11 "The machine can prob handle 2 tests";
  C22), a rule that is missing 1 (X01).
- **Worded well (64):** about 40 are Sean's sentences quoted; 10 manager, 4 lanes, 3 code, 3 literature.

## (a) Is Sean's observation true here?

Yes, on this sample. Over-specific wording is more common (22 rows against 16) and costs more often (15
verified costs against 7). Two things sharpen it:

1. **It is never his wording that is too specific.** Every one of the 22 is ours: a lane's cut-off, a
   docstring, a build clause, or a question we put to him in our own mechanism's terms.
2. **The two failures are one failure in two steps.** A rule is first stated too generally, with no limit;
   it fails; a lane then patches it with a number or a box, and it becomes too specific. "It binds to the
   CLOSEST note ... no fixed reach cut-off" (PF23) bound a head 83 spaces away, and the lane added four reach
   numbers. "One stem must be the whole collinear run" (r1) became "a head on ONE side of the stem ... never
   heads on both sides" with a box test (r4), which stitched stems over blank paper and cut tile 3's second.
   The missing piece each time was the limit said as a convention ("a note the arc could belong to"; "never
   over blank paper; a second straddles its stem").

Over-general rules were usually caught sooner and cheaper: Sean's crops stopped D16 and D18 before landing.
Over-specific rules pass their own controls and are found only by tiles after gathers (2.306 took r4 to r10).

What did NOT show a cost: evidence language inside rules (class 4: 0 of 8 verified). It makes page-facts
long and hides the convention (PF45 is the one inferred case, 2.248), but the costly mixing runs the other
way: a mechanism or number inside the rule (class 2), and a count or one-case reading stated as fact
(class 5: 2.196's "20%", the three 10-20 counts that "cost the whole 2.182 lane").

## (b) Where does specificity earn its place? Is the manager's hypothesis right?

It earns its place in four spots, all in the inventory:

- **A boundary between two readings that both fit**, with both named: higher note right of the stem = a
  second, left = two voices (PF17); two heads that disagree vs three with one dissenter (PF08); the one
  condition under which the bar may lengthen a note (C09, D22 -- Sean: "except under 1 very specific
  condition ... it could easily start making up durations"); a wedge longer than one note (PF33); the
  both-sides stub test "ONLY to a line THROUGH a head" (PF48).
- **A scope**: "scope: the natural sign in the engraved font of both acceptance plates ... flats and sharps
  are not covered by this ruling" (PF30); "every beam lies within one bar ... scope: both acceptance plates"
  (PF31).
- **A number that comes from the notation, not from a plate**: 0.75 sp as the midpoint between a second
  (0.5) and a third (1.0) (R06, K06).
- **A cut-off with both sides measured on real marks and a gap between**: `SIDE_MIN_SP = 0.25`, whole rests
  0.00-0.12 against noteheads on a line 0.44-0.50 (K11). Compare `EDGE_SP = 0.4`: one side only, a 5-95%
  range of our own earlier reading (K03).

The hypothesis is **right but incomplete**. What it misses:

1. **The limit must be worded as a convention too.** "Specifics belong in the limits" is where it went
   wrong: the limit "never over blank paper" was written as "<= 0.3 sp blank" on a box (K05), and tile 5
   still has "~0.44 sp of blank -- the head's BOX covers the gap, its ink does not".
2. **An abstention is a decision.** CLAUDE §4 says a tuned number "may only NARROW"; page_stems.py quotes
   that ("THE CUT-OFFS ARE MEASUREMENTS, so they only NARROW") beside the 0.4 that left 214 / 49 real heads
   without a stem. 19 constants carry "only narrows / only declines". With no old reader beside the new one
   (Sean 11-13), every decline is a mark not written.
3. **What is measured, not only how it is worded.** Four costs are the same fault -- a box standing in for
   the ink (X01: the half-the-ink-in-the-box share Sean called "arbitrary" on 10-30; the 2.290 height cut;
   0.4 sp of the box edge; a box touching a gap). "A detector box ... is only a witness, never the mark"
   exists for arcs only.
4. **The level of the question.** A "Yes" carries the asker's words. "Should its stem be filed only with
   the staff the note belongs to, and never as a copy in the neighbouring staff's cell?" is now a page fact
   with "padded crop", "filed" and "cell" in it (PF11).
5. **Short forms drop limits.** CLAUDE §5 "Stems: up -> right, down -> left" has lost page-facts' "reads
   only an isolated head" (C12); "the ledger lines decide" has lost "for now" and its two-plate scope (C15).
6. **The convention was sometimes already written down and not read.** Registry L19 (a second straddles the
   stem, higher note right) and Sean's 10-26 answer both predate the r4 rule that refused it (R02, D02).

## (c) Generalising Sean's words without putting words in his mouth

Generalised beyond what he said: "a gap of ~two spacings means a missed ledger" from "It would never leave
one out" -- corrected the same day (D15); "it binds to the CLOSEST note" from "Closest note works" (PF23);
"the hole was never used" from "The red is almost always right and better" on one sheet, stale for a month
(PF49); "the ONLY far-head position witness" from "I lean towards just focusing on ledger lines" (PF47);
"expects a whole rest" from "notes or rests" (PF02); "Proximity proves nothing" from two tile answers (PF03);
the grace-note slash, which he withdrew: "I was guessing" (PF15); "read from POSITION" from "the same note to
the same note" (PF28).

Kept too narrow: his r1 "7 is a long stem on a chord" was built as gap-bridging exceptions, not as the
convention he had already given on 10-26 ("a note above sharing the same stem") (D02); the 11-15 build
clause (D01); twice he had to ask for the general rule himself -- 11-10 "Make sure the fix is not just
specific to this rule but is universal enough", 11-11 "I want a fix for future issues not something just
specific to this scenario".

What the good cases have in common (D17, D08, PF18, PF15):

- **His words are quoted with what they answered** (the question, or the tile).
- **Our reading is labelled ours**: "RULE (manager's reading, to confirm in the next session)"; "(manager's
  reading of the scope; Sean named arcs)".
- **It goes up one level only**: from the tile to that symbol's convention, never to a method or a number.
- **It is put back to him as a musician's question that includes the nearest case where it might not hold.**
  That is how the limit arrives in his words: "Always when it is 2 voices. Obviously chords are not always
  multiple voices."; "yes, one stem one value, no exceptions".
- **Words like "works", "almost always", "I lean towards", "for now" are kept**, because they are the scope.

## (d) Code: reason strings and constants

- **Reason strings carry rule language, and it matters.** About 276 distinct strings; roughly 8% name a size
  or distance. `whole_rest_means_the_bar`, `straddles_a_stem`, `two_voices_upper_takes_up` say which
  convention fired. They are the keys of ink-rules, of the lane report's losses-by-reason and of the tests,
  so a string named for a mechanism hides the cause: `no_stroke` ("no free vertical at the head's stem
  side", 214 / 49) was one bucket over five causes, and the manager guessed the wrong one ("not 'stems fused
  into heads' as the manager had guessed", FINDINGS r9).
- **Constants and their comments carry evidence language, which is where evidence belongs** ("Litolff p5
  run 104: 1.44 sp out"). The fault is one line up: the docstring's WHAT sentence -- the definition -- was
  written with the constants in it (K02). Rough script count: 1,058 module-level numbers under
  `tools/omr/staged`, 744 with no "measured / Sean / plate / convention" word beside them, 35 marked NOT
  CONFIRMED.
- So: convention in the docstring's first sentence and in the reason string; number, plate and tile in the
  constant's comment, saying both sides of the boundary.

## Recommendation 1 -- proposed CLAUDE.md addition (for Sean to rule on; not applied)

**Where:** §4, straight after the "How inference decides" bullets (it sits beside "A convention is a prior;
a cut-off is a measurement").

```
**How a rule is worded** (Sean, 2026-11-15: *"there is a trick to only being specific when it is required"*):

- **Say the rule as a musician would; the number stands beside it, never in it.** "The stem touches its
  head", not "within 0.4 sp of the box edge". The same sentence travels unchanged from ROADMAP row to brief,
  docstring, reason word and control.
- **Be specific only at a boundary** -- where two readings both fit -- and name both (higher note right of
  the stem: a second; left: two voices).
- **Every rule states its never, in the same plain words** ("never over blank paper"). A number that refuses
  or abstains is a decision too: it needs both sides of its boundary measured on marks Sean has judged.
- **Measure the mark, not its box**: a box or oval is where to look.
- **Sean's words are quoted with what they answered; our reading is labelled ours**, goes up one level only
  (tile -> that symbol's convention) and is put back to him in a musician's words before it is a page fact.
  The cases that exposed a fault are evidence, never the rule.
```

Line by line, the case each would have prevented:

| line | case |
|---|---|
| musician's sentence; number beside it; travels unchanged | K01 -> K02 / K03: "touches" became "within 0.4 sp of the box edge"; ten real stems refused (r10) |
| specific only at a boundary, both named | D02: "never heads on both sides" lost tile 3's second (r7); and it protects C09 / PF17 from being "simplified" |
| the never in plain words; a refusing number is a decision | K05 / D03: stems stitched over blank paper (r6), tile 5's 0.44 sp (r8); C10; PF23's 83-space binding |
| the mark, not its box | X01: the 10-30 box share, the 2.290 height cut, K02, D03 |
| his words quoted, our reading labelled, one level up, put back to him; cases are evidence | D01 / K08 "through its touching mates"; D15; PF49; PF28 (two ties written as slurs, 2.305 r4) |

**Three-line variant:**

```
**How a rule is worded** (Sean, 2026-11-15): say it as a musician would, with its *never* in the same plain
words; numbers, boxes, plates and the cases that exposed a fault stand beside the rule as evidence. Be
specific only where two readings both fit, and name both. Sean's words are quoted with what they answered;
our reading of them is labelled ours until he confirms it.
```

## Recommendation 2 -- the ten rules most worth rewording (proposals only; Sean's quotes untouched)

Ranked by verified cost. Each: CONVENTION / LIMIT / EVIDENCE.

1. **The stem definition** (page_stems.py module doc and r11 doc; DECISIONS 11-15 build clause).
   CONVENTION: a stem is the vertical stroke its head touches on the engraving side (up right, down left);
   every head on one stem shares it (page-facts; Sean 10-26: "there is a note above sharing the same stem").
   LIMIT: never across blank paper; never a stroke an earlier mark owns; where a stroke could be two heads'
   stems each way, abstain. EVIDENCE (beside it): the r10 counts, his r10 tiles, every sp number.
2. **CLAUDE §4, the cut-off line.** Keep "A convention is a prior; a cut-off is a measurement" and add the
   limit: "a number that refuses or abstains is a decision too -- it needs both sides of its boundary
   measured on marks Sean has judged". EVIDENCE: 2.306 r9-r10.
3. **"It binds to the CLOSEST note"** (page-facts §1). CONVENTION: an arc ends at a note; Sean: "Often arcs
   stop short. Closest note works". LIMIT: closest among the heads that were read on the arc's own staff;
   where the head the ink points at was not read, or two are about equally near, abstain and count.
   EVIDENCE: the 304 Litolff ends; the reach numbers in page_arc_bind.py are measurements (and the DECISIONS
   clause "no fixed reach cut-off" should say they may only be measurements).
4. **"A resolved contest DROPS the loser -- it never relocates it"** (page-facts §3). LIMIT missing, from
   Sean 10-06: "All note heads should be found and written on their staff." -- a head is dropped only where
   its owner's copy is written. EVIDENCE: 2.289 r1 tiles 3, 4, 7, 8.
5. **"Same pitch is read from POSITION"** (page-facts §1). CONVENTION (Sean): "a tie only ever happens
   between 2 adjacent notes of the same pitch". HOW WE READ IT (ours): the same staff position under the
   same clef on one staff. LIMIT: across a system break or a clef change position alone is not pitch; an
   unread pitch is doubt, never a different pitch. EVIDENCE: his tiles 2, 3, 9; 2.305 r4 tiles 4, 5.
6. **CLAUDE §5 "Stems: up -> right, down -> left."** Add the limit page-facts already has: "for a lone head;
   in a chord the stem runs through its notes and a second straddles it".
7. **Stacked arcs** (CLAUDE §5, page-facts §1, registry C42). One wording, his: "When there are multiple
   arcs the tie is always closer to the staff than the slur." Say that "nearer the noteheads" is our reading
   of two tiles and differs for notes off the staff; LIMIT: a prior for the kind, never a gate (registry:
   19 of 73 wrong if promoted).
8. **The hollow-head position bullet** (page-facts §3 and §5). CONVENTION / SCOPE / EVIDENCE as three
   sentences; move the supersession history to DECISIONS; §5's "REJECTED 2.50 hole-centre" no longer true
   as written.
9. **The ledger-owner bullet** (page-facts §3). CONVENTION: a far note's ledger lines run toward its own
   staff, so they name the owner (Sean 09-28). LIMIT: nearness never overrides them; stem and ledger
   disagreeing -> ledger, "for now", Litolff + Brahms. EVIDENCE: the tile counts and flag names, after.
10. **"A stem belongs to its note's own staff only"** (page-facts §1, 11-13). CONVENTION: a stem belongs to
    its note, and so to its note's staff (Sean: "Yes", to our question, quoted). LIMIT: another staff's
    view of that head carries no stem. HOW (ours, will change with 2.307): cells, crops, filing.

Also worth a look: the 0.5 box share (D09), "A bar with no notes expects a whole rest" (PF02), "Proximity
proves nothing" (PF03), the class list in the key slots (PF36).

## Recommendation 3 -- what in the templates invites the mixing

- **DECISIONS line format** (`who · the decision · because · (pointer)`): one "who" covers his quote, our
  reading, the counts and a build clause. Suggest the line say which part is whose: `Sean said "..." (to:
  the question / tile) · we read it as ... · build ...`. The header already says the measurement lives in
  FINDINGS; recent lines carry it anyway.
- **CLAUDE §6 "ask him one plain question"**: add "in a musician's words, not the mechanism's" -- the answer
  becomes the rule.
- **CLAUDE rule 3 "opens with the cause and the process lesson"**: each round writes a general lesson from
  one round's cases. Keep it, but a lesson is a finding until it is a DECISIONS line (rule 9 already says
  where general lessons go).
- **`CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED`**: used only when Sean cannot be asked,
  and has no slot for the LIMIT or for which numbers are measurements. The registry's fields (Says /
  Numbers / Measured here / Would be falsified by / Known exceptions) are the fuller form.
- **measuring.md §0**: the three measures never look at the wording. A lane report could carry one line:
  the rule as worded, and the convention sentence it rests on (page-facts or DECISIONS).
- **page-facts header**: "Every ruling carries its scope" -- and, by the same logic, its words apart from
  ours, and its never.
- **CLAUDE §6 "Name the rule that owns the value"** already makes the brief name the rule; it does not make
  the build carry the rule's sentence.

## Not read, or not verified

- DECISIONS: lines 1-75 read closely; the other ~1,100 lines only by search. Older overturned wordings are
  certainly missing from the inventory.
- Registry: structure, the refuted list and about 8 of 114 entries.
- ink-rules: summary and about 40 rows of the table.
- Code: page_stems.py and page_arc_bind.py headers and constants; key_object.py and ink_attachment.py
  constants; NOT read: adjudicators/ownership.py on the 2.305 branch, the rhythm / duration rules,
  staged-internals beyond a search. Counts in (d) come from a rough script over comments.
- Benchmarks: only page-ledger-2026-11 (2.306 rounds 4-10) and a search of arcs-combined; costs for other
  rows come from DECISIONS lines, not from their FINDINGS.
- The prompting case's first half ("Sean caught it by asking about long stems on spread chords") is from the
  lane brief; I did not find it in the files.
- Inferred, not verified: that the wording (rather than the mechanism alone) caused PF44's losses, PF45's
  part in 2.248, PF04's lane, K09's cost.
- The inventory leans toward recent stem and arc work, which is where this audit started; the 22 : 16
  ratio should be read with that in mind.
