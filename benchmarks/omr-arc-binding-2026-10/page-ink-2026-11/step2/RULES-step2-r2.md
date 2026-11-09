# 2.274 step 2 ROUND 2: pages and verdict rule, written and committed BEFORE any hold-out output is read (2026-11-09)

STAGED. Same flag (`OMR_PAGE_ARC_WRITE`, default OFF), same rule as step 2 (RULES-step2.md): only witnessed page-ink runs, each end bound to the closest note, one arc each. Round 2
fixes the three causes step 2's verdict named, each at its source, on develop pages first (FINDINGS "2.274 step 2 round 2"):
- (b) two arcs meeting at a note read as one run: the run is CUT at every bridged gap of 2.0 spaces or more (`page_arc_bind.GAP_SPLIT_SP`; whole-OFF runs: 1 of 370 has one), a stretch
  under 3.0 spaces is a tail and dropped, two longer stretches are two arcs each bound alone (`MIN_PIECE_SP`);
- (c) a chord end: the arc's side names the member in a two-member chord (cap = top head, cup = bottom head; page-facts "an arc is OVER its notes, of stacked arcs the nearer is the
  tie"); in a stack of three the end's height names a member only within 1.2 spaces of it, else the end abstains (`INNER_MEMBER_DY_SPACES`);
- (d) an end standing more than 3.0 spaces on the arc's own side of the head it bound to abstains (`END_BEYOND_HEAD_SPACES`): a nearer head was never boxed.
No constant is changed after the hold-out is read. A tile is never recut to hide a miss.

## Pages
- DEVELOP (looked at, fixed on): Brahms p0 (Sean's 153 hand arcs), p5; Litolff p4. Develop runs replay ONLY these pages (`cutslice.py`: a slice holding only the develop pages and, for
  Litolff, the opening page 1 as context; step 2's leak, a develop run that also computed the hold-out arms, is closed).
- HOLD-OUT NAMED BY THE LANE LEAD: Brahms p11, p20; Litolff p5, p13. HONEST NOTE: step 2's binder ran on them and its look sample and 12 tiles show some of their runs, so they are
  "seen" by step 2's behaviour; none was looked at for round 2 and no round-2 number on them has been read.
- NEW, used by NO 2.274 round (checked against RULES-r2/r3/r4/step1/step2 and FINDINGS; chosen by detector slur/tie BOX count alone among the unused spares, `r2/boxcount.py`,
  no reader run): Brahms p18 (672 boxes; spares 10: 569, 15: 522, 17: 554, 21: 494) and Litolff p15 (173; spares p7: 79, p14: 125).
- Gate pages (export byte-identical flag OFF vs main): Litolff p4, Brahms p5 (as step 2).
- The records: the saved `20261104-night` gathers cut to the pages (Brahms 0 as opening-page context, 11, 18, 20; Litolff 1 as context, 5, 13, 15), the step-1 rows filed by
  `build_inject.py` (same function as step 2), both arms re-adjudicated from the same slices, same tree, flag OFF vs ON. No re-gather.

## Verdict (hold-out + new pages, pooled; per page next to pooled) -- the SAME bars as step 2
GOOD (worth Sean switching on) only if ALL hold:
1. BINDING: in a seeded sample of 30 WRITTEN runs (all if fewer; seed 2749; 10 replaced, 10 new, 10 unchanged as available), by crop (the arc as the file writes it, a thin box on each
   bound head), start and stop are the right notes on at least 27 of 30 (90%). "Right" for an end that stops short = the closest note.
2. NOTHING LOST: of the OFF arcs a written run replaces, in a seeded 20: at most 2 were right and whole in OFF and are wrong or gone in ON. And the file loses NO arc that no written
   run overlaps.
3. JUDGED: Sean's judged answers going right -> wrong: 0 (`lane_report`; this control cannot fail for binding, so the file-level check is the Brahms p0 hand-arc score, right in OFF vs ON,
   which can: `truth_p0.py`).
4. GATES: export byte-identical flag OFF vs main on Litolff p4 and Brahms p5; fast tier green; `python3 -m tools.omr.staged.check` TOTAL no higher than 229.
5. SEAN'S 12 TILES (question "Does the arc start and end on the right notes?"): 11 of 12 right. Reported, not self-judged; the lane's own look is reported beside it.
Otherwise NOT GOOD, naming which criterion failed. Abstentions are counted by reason and, for each reason, what the old path writes for the mark (an abstained end keeps the OFF arc).

FROZEN: reader, binder, decision and export as of commit 47372e0a5 (round-2 code: gap cut GAP_SPLIT_SP 2.0 / MIN_PIECE_SP 3.0, chord member by side with INNER_MEMBER_DY_SPACES 1.2, END_BEYOND_HEAD_SPACES 3.0, HEAD_BEHIND_END_SPACES 1.6). Fixed from develop pages only (Brahms p0, p5; Litolff p4; develop-only slices): the develop result at freeze, flag ON vs step 2 on the same pages: Brahms p5 written 135 -> 138 (OFF-whole 94 -> 99, replaced 5 -> 2), p0 written 58 -> 57, Litolff p4 written 67 -> 58 (the 8 wrong ends seen on crops now abstain); Brahms p0 hand arcs 54 -> 55 right in ON (step 2 ON 54), 41 -> 40 written arcs matching no printed arc. Committed and pushed BEFORE the hold-out slices were built or read.
