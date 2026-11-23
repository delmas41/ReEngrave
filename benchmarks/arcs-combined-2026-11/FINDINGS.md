# Arcs: the page binding pass (ROADMAP 2.298, 2.305)

STAGED. Sean's answers are under `answers/`. 2.298's own numbers are in its ROADMAP row.

## 2.305 r1 — arc binding, job 2 only (2026-11-12)

Branch `lane-2.305-arc-binding` 0bdfd5e (lane-arcs-combined + main). Flags `OMR_PAGE_ARC_WRITE`,
`OMR_ARC_MEETING_AT_HEAD` stay OFF; the OFF file is byte-identical. NOT landed. Counts are the lane's; every
crop look is the lane's and is a lead. Pages: Litolff p5/8/13/15, Brahms p0/11/18/20 (not the frozen sample).

**Cause.** On Brahms p0 every one of Sean's 18 arcs missing from the file has a page-ink run fitting both ends:
the ink was read (job 1 passed) and the binder declined (job 2). But it declines mostly for reasons outside
itself: (1) the head was never boxed -- 2.290 gives the binder NO new heads (it folds twin boxes and claims head
ink; ink-only heads are census rows behind `OMR_PAGE_HEADS`, OFF), so 0 of 2.298's 4 unboxed-head abstentions
now bind; (2) ties across a system break (5 of the 18); (3) ties meeting at a head refused as
`continues_in_another_curve` even with `OMR_ARC_MEETING_AT_HEAD` on (not diagnosed); (4) the binder had no
"arc is OVER its notes" test, so a box owner or nearest-staff row could hand it a staff on the ink's far side.
**Process lesson:** an abstention must record WHOSE it is (no head there / staff came from a box / the binder's
own rule) so the next round goes to the right stage. 2.298 and the manager both assumed the notehead landing
would supply the missing heads; it does not.

**Two binders for one rule (not ended by this round).** 2.223 `OMR_ARC_BIND_PAGEWIDE` (ON) binds each detector
arc BOX's traced curve; the page pass (OFF) binds each page-ink RUN. Export uses the page pass only where every
run a box witnesses is written; an abstained run falls back to 2.223 or older `_flank_search` /
`_two_note_reading`. On p0 that fallback writes 15 of the 16 file arcs that match none of Sean's.

**Step 0 (both arc flags ON).** Litolff: 294 witnessed runs, 174 written, 120 abstained (end unbound 66 --
far beyond its head 41, far from any head 14, continues in another curve 11, two equal columns 7; system edge
18; step conflict 14; step unread 14; heads between 6). Brahms: 400 / 281 / 119 (system edge 53; end unbound 39
-- far beyond 27, continues 15; heads between 13; accidental printed or unread 10). Brahms p0 vs Sean's 98
arcs: OFF 74 right, ON 80, right->wrong 0; the 18 missing are all job 2 (8 end unbound, 5 system edge, 2 step
conflict, 1 accidental unknown, 1 heads between, 1 on other notes). Job-1 failures listed, not fixed: Litolff
p5 run 97 (two ties read as one, his r2 tile 7), Brahms p18 run 41 (beams, tile 8), Litolff p15 run 4 (ink is
the lower slur, bound to the top staff's notes; his r2 tile 9, which he judged by notes as right).

**Built.** (a) an end whose head is on the far side of the ink by > 2.0 sp abstains (`head_on_the_arcs_far_side`;
stem tips exempt); (b) if both ends fail (a), one rebind on the neighbouring staff the arc's side names;
(c) two boxes of one 2.290 head are one chord member; (d) a page-pass slur end on an unwritten twin box moves
to the written box. Controls from real rows (`test_arc_binding_far_side_2_305.py`): Litolff p13 run 31 on both
staves and r2 tile 9; each fails before the change. No control for (c)/(d). Reverted: twins as one candidate at
the ink centre; the written box as step source (turned a printed tie, Litolff p5 run 89, into a slur).

**File change, OFF vs ON (lane_report):**
litolff p5/8/13/15: ties +8 -2 | slurs +12 -36 | pitches ~2 | red bars 0 -> 0 | judged right->wrong 0
brahms p0/11/18/20: ties +8 -2 | slurs +32 -91 ~1 | pitches ~2 | red bars 64 -> 64 | judged right->wrong 0

**Gates.** judged score identical OFF/ON (Litolff 22/2, Brahms 50/7); judged_claims 0 contradictions (cannot
move: no GATHER claim changes); check 217; fast tier OFF 10,670 / 0; ON 10,668 (the 2 are default-off pins).

**Open.** The large slur loss (-36, -91) is mostly unjudged; Litolff p8 m69-70 unison tie still unwritten
(`step_conflict` on one of the unison's two boxes); cross-system ties not built; ending the old fallback would
remove arcs and its cost is not counted. To retire on landing (named only): 2.223 per-box `_page_binding` /
`paired_by_page_binding`, `_flank_search`, `_two_note_reading`, `_stack_reading`, 2.166 `paired_by_system_arc`,
export `_paired_spans` box merge, `_anchored_slur_spans`, `_page_bound_slurs`, 2.271 `_edge_curves`.
Tiles: out/print-from-worktrees/2.305-r1 (12: 9 slurs, 3 ties).

## 2.305 round 2 (2026-11-12) -- built OFF, `lane-2.305-arc-binding` 6082f24e4; Sean's r2 tiles not yet answered

STAGED. Sean's r1 tiles: 8 of 12, every fault an arc written as a SLUR (answers/answers-2.305-r1.json).

**Cause.** Each r1 fault was a slur written plain on evidence that was not there.
- Tiles 9, 11 (ties written as slurs): one head's POSITION is misread upstream (Litolff p15 `15/1/9/18/4`, a
  16 px box at confidence 0.05, position 7.50 on the rounding line; Litolff p5 `5/0/2/13/7` read 0.76 of a step
  off its unison partner). The binder decided "different pitch" from the two rounded steps and never asked
  whether the measured positions were far enough apart to be two positions (page-facts gap 0.168-0.435 sp).
  The pitch misreads are upstream faults, reported, NOT fixed here.
- Tile 8 (two ties as one slur, a note too far): one traced run covered two ties meeting at a head and nothing
  cut a run where its ink dips onto a head; the traced end also ran past its note to the next chord.
- Tile 5 (no arc between the notes): written by the OLD fallback, not the page pass -- a detector box starting
  at the cell's left edge where there is no arc ink; legacy pairing took the first head under the box.
- Litolff p8 m69-70 unison tie: box-centre geometry disagreed with positions that read the same (0.00 / 0.08).

**Process lesson.** When an upstream reading is a guess, the kind built on it is a guess too: a binder must
say "cannot tell" in its inputs' own terms. The lane's own crop look was wrong again (r1 tile 3).

**Size.** Slurs written with both ends at the same written position on one staff, 8 pages: Litolff 8,
Brahms 9 -- all 17 from the OLD fallback path, 0 from the page pass. That bucket is untouched.

**Built (page pass only, flags OFF).** (1) positions decide same/different: same step within 0.25 sp = same
(writes the p8 m69-70 tie on voice 1); steps differ but positions < 0.435 sp apart = kind unread, nothing
written (`page_arc_runs_kind_unread_nothing_written`); (2) a run that dips onto a head between its ends is cut
there; (3) an end binds the head its ink lands on (outer quarter of the run only, and only when it does not
already sit over its closest head -- both limits from the lane's own regressions, incl. Sean's P247); (4) a box
cut at its cell edge is measured by its inked width. Controls from real rows:
`tools/omr/tests/test_arc_binding_r2_2_305.py` (tiles 8 and 5; none for (1)).

**File change, OFF vs ON** (re-adjudicated from the saved 2305 gathers):
Litolff ties +18, slurs +7 -37; Brahms ties +8 -2, slurs +32 -99. Judged right->wrong 0; judged_claims 0
contradictions; Brahms p0 vs Sean's 98 arcs 74 -> 80 right; check 217; fast tier flags OFF 10,684 / 0
(NOT re-run with the arc flags ON).

**Open.** The removed slurs (37, 99) are judged only by the 4 removal tiles in r2; the 17 fallback
same-position slurs; the upstream position misreads behind r1 tiles 9, 11; cross-system ties; Brahms p18 run 80
doubtful by the lane's look (lead only). Tiles: out/print-from-worktrees/2.305-r2 (12: 4 r1 faults redrawn,
4 removed slurs boxed on the old ends, 4 new).

## 2.305 round 3 (2026-11-13) -- gate numbers with both arc flags ON; `lane-2.305-arc-binding` eb59ce438; NOT landed

STAGED. Sean's r2 tiles (answers/answers-2.305-r2.json): 8 right, 3 real ties unwritten (5, 8, 9), 1 written
wrong (10); all 4 removed OFF slurs were ties on the page.

**Tile 10, cause.** A cut run left its detector boxes counted twice: the boxes witness both the written piece
(the tie `3/1`->`4/3`) and the abstained piece, and a box shared between a written and an abstained run was
kept (`shared_kept`), so the old 2.223 slur was written on top of the tie, one note late. Lesson: "read and
claimed once" must hold per BOX, not per run.
**Rule as briefed, measured and REJECTED:** "a box of any run the pass bound or abstained on writes nothing
through the fallback" removes 43 fallback arcs per plate and takes 11 of Sean's 98 Brahms p0 arcs right ->
not right (80 -> 69). Many abstentions are honest and the fallback arc there is right.
**Rule built:** a box that witnesses a WRITTEN run (or a run bound at both heads with kind unread) writes
nothing through the fallback; a box witnessing only abstained runs keeps its old arc. Removes exactly 1 arc on
the 8 pages (this slur). Control from the real run-76 rows: `test_arc_binding_r2_2_305.py::TestInkIsClaimedOnce`.
**Tile 8, cause (upstream):** the tie's left note, the lower chord member, has no detector box; the only
candidate head is 2.89 sp beyond the arc's end and is rightly declined.

**Gate, both flags ON** (`OMR_PAGE_ARC_WRITE`, `OMR_ARC_MEETING_AT_HEAD`; re-adjudicated saved gathers, 8 pages):
Litolff ties +18, slurs +7 -39; Brahms ties +8 -2, slurs +32 -99; judged right->wrong 0 on both; judged_claims
0 contradictions; Brahms p0 vs Sean's 98: 74 -> 80 right, right->not right 0, written arcs matching none of
his 31 -> 14; check 217; whole fast tier flags ON 10,683 passed / 2 failed, both default-off pins
(`test_page_arcs_2_274.py::test_flag_is_off_by_default`,
`test_staged_page_arc_binding_2_274_step2.py::...::test_the_decision_files_nothing_with_the_flag_off`).
Flags-OFF tier not re-run after the r3 change (r2: 10,684 / 0).

**Open.** The old fallback is NOT retired: it writes the 17 same-position slurs and every abstained run's
arc; retiring it now costs ~43 arcs per plate incl. 11 of Sean's right p0 arcs, so it waits until the binder
abstains less (unboxed heads, position misreads, cross-system ties). Unwritten ties: r2 tiles 5, 9 (position
misreads), 8 (unboxed head); the down-voice tie at the Litolff p8 unison.

## 2.305 size of "an arc ends at the notes standing at that point" (2026-11-13) -- measurement only, 47eaf4a18

STAGED. Sean's proposed rule (2026-11-13): "if there are any notes in a chord at the same point where an arc
ends then that is where it should end"; the anchor is the x place, no beats. Sized on the r3 replays (both arc
flags ON, 8 pages), script `end_columns_2305.py`. A column = heads with centres within half a head-width; an
end reaches a column within one head-width (both the lane's choices, not page-facts).

Abstained runs: Litolff 120, Brahms 122. Unbound ends by what stands at that x: exactly one column 50 / 46;
two or more 22 / 6; no note 14 / 9; system edge 18 / 53. Ends that ARE bound but whose kind (or other end)
was refused: 82 / 130 (Litolff: step unread 28, step conflict 16, heads between 14, other end at system edge
14, positions in the gap 8; Brahms: other end at system edge 45, other end unbound 29, heads between 26,
accidental printed 14, step conflict 6, accidental unknown 6).

**What the rule would add.** Runs with both ends resolving: Litolff 37, Brahms 26 -- but 20 / 17 are already
in the file as the same pair (from the old fallback), 6 / 4 as a different pair, and only **11 / 5 are not
written at all**. Against Sean's 98 Brahms p0 arcs: of his 18 missing, at most **3** distinct arcs would be
fixed; 5 are ties running off the system, the rest are kind refusals with both ends already bound.
**Reading.** "Which note" is NOT the main reason the page pass declines. The two large buckets are arcs at a
system edge (18 / 53 ends, plus 14 / 45 partners) and bound arcs whose KIND is refused (step unread / step
conflict / heads between / accidentals). The manager's simple account to Sean ("the note isn't there to
attach to") overstated that bucket.
Not determined: head-shaped ink with no box at the no-note ends (`OMR_PAGE_HEADS` is OFF in these gathers);
nobody has looked at the 16 new arcs.

## 2.305 round 4 (2026-11-13) -- arcs across a system break; built OFF, `lane-2.305-arc-binding` 2fc7e709b

STAGED. Convention confirmed by Sean 2026-11-13 ("Correct"; page-facts): an arc off the right end of a system
continues at the left of the same instrument's staff on the next system or page; one arc; same pitch = tie.

**Cause.** No new binder was needed: the page pass already hands its system-edge halves to the 2.271 join,
which pairs by part (staff identity). Within a page it works. **The system-edge bucket in the earlier count
was mostly a SAMPLING artifact**: the frozen sample holds single pages, so a half at a page break has no
partner page in the record (Brahms 14 right + 14 left, Litolff 5 + 7 of 23 + 22 / 7 + 7 halves).
**The real fault:** the join took "the next run of the part" as the next system with no check that the two
are next to each other; in a record holding only p0 and p11 it wrote a slur from Brahms p0 to p11.
**Lesson.** A join across a break must check physical adjacency, not list order; a sampled record makes
non-adjacent pages look adjacent -- and a count taken on single-page samples cannot size anything that
crosses a page.
**Fix.** A join is written only to the same page's next system or the next page's first system; otherwise
`arc_across_systems_partner_page_not_in_record`, nothing written. Control from the real halves:
`test_arc_across_pages_2_305.py` (fails on the r3 tree).

**Counts.** 8 pages: Brahms 5 pairs one-to-one, 1 ambiguous, 3 + 3 no partner half (about 3 traced with no
detector box, about 4 not traced). Extra 2-page gathers: Brahms p0+p1 8 pairs, file holds 5 cross-system arcs
(4 ties, 1 slur); Litolff p13+p14 none.
Sean's five Brahms p0 cross-system ties (needs p1): OFF 0 of 5; ON P215, P230, P253 right; **P191 (written as
a slur) and P192 (no arc) are upstream** -- one head that 2.290 grouped with a box on staff 5 AND a box on
staff 6 (mg/0/0/477), so the tie went to staff 5's part and staff 6 got none.
File change OFF vs ON: Litolff [5,8,13,15] ties +18, slurs +7 -39; Brahms [0,11,18,20] ties +8 -2, slurs
+30 -99; Brahms [0,1] ties +18, slurs +22 -70; Litolff [13,14] ties +8, slurs +3 -21. Judged right->wrong 0
on every record; judged_claims 0; check 217; fast tier flags OFF 10,687 / 0 (flags ON not re-run).
**Open.** Unwitnessed edge halves are never offered to the join (~3); stacked halves abstain (1); clef change
at the break untested; the P191/P192 head shared by two staves. Tiles (9: every cross-system arc written):
out/print-from-worktrees/2.305-r4 -- not yet sent.

## 2.305 round 5 (2026-11-13) -- cross-system tile 4 fixed (our join, not the clef); tile 6 no fault found; `lane-2.305-arc-binding` 219e74350

STAGED, flags OFF. Sean's r4 tiles: 6 of 9 (answers/answers-2.305-r4.json).
**Tile 4 (a tie written as a slur; Brahms p11 Fag.).** The clef was READ right: a tenor clef change mid-system
on system 0 (two witnesses), tenor at the start of system 1; both positions measure the space above the top
line (-1.12 / -1.07 steps); written pitch F#4 at both ends. The manager's two guesses (position-only rule; a
missed clef) were both WRONG. **Cause:** the cross-system join decided TIE and then refused it because its
first note already ENDS a tie inside the system (the middle note of a tie chain), and the old box pairing
(`_legacy._paired_spans`) had merged the two pieces into a SLUR on the same two notes, which reached the file.
**Lesson.** "Read and claimed once" must hold across a break too: when the join reads one arc, the old path's
reading of the same two pieces steps aside; and an "already used" rule must say which END of a span it means.
**Fix** (`export._with_across_system_joins`): a tie join is refused only if its first note already STARTS a
tie or its last already ENDS one; a span of the other kind on the same two notes as a join is dropped
(`arc_across_systems_other_kind_span_replaced`). Control from the real rows:
`test_arc_across_systems_tie_chain_2_305.py`. Only tile 4's two notes change in the file; judged right->wrong
0; OFF file byte-identical. Fast tier and Litolff not re-run.
**Tile 6 ("don't look like they go together"; Brahms p11 Vcl.).** No fault found: both staves are labelled
"Vcl." (READ), one half each side in the part, both pieces real ink, F#2 to B2 = a slur by the rule. Sean
said "can't tell for sure" -- a wider crop goes to him before anything is built.
**Open, not shown by a tile:** the join writes a SLUR when a pitch at either end is unread (page-facts: an
unread pitch is only doubt); the slur version of the "already used" rule is unmeasured.

## 2.310 rule 3 pair (2026-11-15) -- the ON arc binder still follows the old reach window

STAGED, tests only (`tools/omr/tests/test_rule_arc_ends_at_its_notes_2_310.py`, fixture rows from the saved
Brahms gather; exercises `arc_claim.bind_curve` as `ownership._page_binding` feeds it, flags at their ON
defaults). YES: Brahms p11 tie `glyph/11/0/2/8/11` (Sean: "tie, yes"), ends 0.4 sp short, bound to its two
notes; fails when the start note is removed. NEVER: 2.305 r1 tile 5 (Sean: "no, there's no arc between those
two notes") -- none of the 9 traced curves on that staff returns the pair; fails when the ends are moved onto
the two notes. **Finding:** the arc Sean describes leaving the second note stops 2.4 sp short of it, past
`ANCHOR_OUT_SPACES = 1.6`, so `bind_end` abstains naming that note (margin +2.03 sp): strict xfail. The rule
(page-facts, reworded 2026-11-15) says a short arc belongs to the closest of the notes standing there; the
reader still has a measured reach window in the rule's place. Not tested: "never to a note on another staff"
(`_page_binding` keeps other staves' heads out; passed in by hand, `glyph/11/0/12/4/2` bound staff 13's notes).

## 2.305 round 6 (2026-11-15) -- the ends rule replaces the reach window; built OFF, `lane-2.305-arc-binding`; NOT landed

STAGED, `OMR_PAGE_ARC_WRITE` (OFF; the OFF file is unchanged: every OFF arm below reproduces the r6base OFF arm). Rule owning the value (Sean
2026-11-15, page-facts): "An arc ends at the notes standing where its ink ends, on the staff it sits over ... never past a nearer note ... never
to a note on another staff. Where two notes are about equally close, we don't choose."

**Cause.** The 1.6 sp window (and the page pass's 1.6 / 2.5 sp look-behinds and 4.0 sp reach) stood in for the rule because the real failure --
a note nobody boxed, so the arc takes the next note along -- was never tested directly. Removing the numbers exposed what they were silently
doing: (a) the 1.6 / 0.8 sp window was ALSO the only thing keeping a detector curve off notes 7 sp away on the staff below (`ANCHOR_DY` 2.5 sp
was the "on the staff it sits over" guard), and (b) its ahead/behind asymmetry chose between two notes the rule calls about equally close.
**Process lesson:** before dropping a number, list every rule it was quietly enforcing; each must be stated and guarded in its own words, or
the number's other job silently disappears (here: "never to another staff" and, still open, "stops SHORT of" = direction).

**Built** (`arc_claim._bind_end_by_rule`, used by `bind_curve` (2.223 curves) and `page_arc_bind.closest_binder` (page runs) when the flag is
ON; the old page-pass reach path, `OWN_BAR_BEHIND_SPACES` and the binder's use of `END_REACH_SPACES` are deleted -- that path only ran with
the flag ON; the 2.223 window stays as the flag-OFF reader):
- the end is where the ink ends (the curve's page-stroke end; a run's `core_ends`); every usable note of the arc's staff is a candidate, the
  closest wins, measured from the ink end to the head's EDGE (head extent at its 2.290 ink centre where the record has one). No reach.
- two columns within `BIND_COLUMN_MARGIN_SPACES` (0.5 sp, the existing hand-set margin, beside the rule) -> `two_columns_at_end`; where the
  traced ink LANDS on one of the two (r2's landing rule) that one binds.
- unread head ink: page strokes of a head's shape (`page_heads` M6a numbers) on a stem, whose centre no reading box (any class but line marks:
  staff, ledger, beam, stem, tie, slur, brace) and no claimed area covers, and that no claim names in `page_strokes` -> at least about as near
  as the closest note -> `unread_ink_at_end`. **Where the fact lives:** GATHER files the strokes, boxes and claims (`Q.PAGE_STROKE`,
  `Q.GLYPH_BOX`, `Q.CLAIMED_AREA`); the "ink-only head" census itself (`page_heads.read`) is GATHER but filed only behind `OMR_PAGE_HEADS`
  (OFF), so the binder (ADJUDICATE) reads the filed rows with the census's own numbers. Without the stem clause the arcs' own tips, letters
  of "pp sempre" and an accidental piece read as unread heads (2.310 rows, looked at).
- another staff: the neighbouring staves' usable heads are handed in as a guard (never candidates); one on the arc's own side (cap: below,
  cup: above), not a twin of an own head (`FOLD_IOU`), not given to this staff by `GLYPH_OWNER`, at least about as near ->
  `nearer_note_on_another_staff`. Which code keeps other staves away otherwise: `_page_binding` hands the binder ONE staff's heads (`home`).
- r6 also records `kind_evidence` on a bound-but-refused run and each bound end's margin over the next column (`second`) -- measurement only.

**Tests.** 2.310 file: the xfail now passes (arc leaving Sean's r1-tile-5 second note, 2.4 sp short, binds it); YES/NEVER pass; twins rebuilt
from the REAL page rows (staff strokes, boxes, claims added to the fixture): the note never boxed -> `unread_ink_at_end`; with its ink also
gone the end reaches a farther note (the guard is what refuses). NEVER another staff: Sean's arcs-combined r2 tile 9 (two slurs, two staves)
-> `nearer_note_on_another_staff`; twin Litolff p13 run 31 (real rows, not a tile): a neighbour's note on the far side is no rival. Tests that
pin the 2.223 window now pin it to the flag-OFF reader; page-pass window tests rewritten to the rule.

**Measures** (re-adjudicated saved 2305 gathers; baseline = the merge before r6, 18ba158f9, same gathers and stages; flags OFF vs ON):
- lane_report file change, before -> after: Litolff [5,8,13,15] ties +18 -> +24 -2, slurs +7 -39 -> +36 -44; Brahms [0,11,18,20] ties +10 -2
  (same), slurs +30 -101 -> +40 -99; Brahms [0,1] ties +18 -> +18 -2, slurs +22 -70 -> +29 -77. Judged answers right->wrong 0 on all three.
- Sean's arc tiles (r1, r2, r4; written file, by glyph key): 26 right->right, 5 unwritten both, 1 wrong both (r4 tile 5, the shared head),
  **right->wrong 0, right->unwritten 1**: r2 tile 1 (Litolff p13 tie `13/1/1/11/5`->`12/8`): the cup's left end stands under 11/5 and 0.47 sp
  nearer it than the second voice's 11/7 -- inside the 0.5 sp margin, so "don't choose". (A first build measured centre to centre, broke
  r2 tiles 7 and 10 and r4 tile 1; fixed by the landing rule, the head-edge measure and the other-staff guard.)
- "About equally close" on judged arcs: bound ends that beat the next column by 0.05-0.30 sp more than 0.5 sp were all right (r4 tiles 3, 8, 9;
  r1 tile 4; r2 tiles 2, 12); the one judged case inside the margin (0.47 sp) was the nearer note. No judged case shows the nearer of two
  near-equal notes WRONG, so the margin's lower side is unmeasured; it stays 0.5 sp.
- Page-pass runs, before -> after: Litolff written 177 -> 175, Brahms 280 -> 275. New abstentions: two columns 3 -> 11 / 3 -> 4,
  `unread_ink_at_end` 10 / 6, `nearer_note_on_another_staff` 6 / 5 (runs where an end gives it), one head at both ends 1 -> 7 / 1 -> 3 (a short arc whose BOTH ends'
  closest note is the same one: the rule as worded has no direction; "stops short of them" suggests the note at or past the end -- a
  question for Sean, not built). `end_far_from_head` 12+ -> 0 (retired).
- Blind tiles: out/print/2.305-r6 (12: 10 arcs r6 writes that the baseline did not, 2 it removed), key out/print/2.305-r6-key.json.
  Lane's look (lead only): tile 5 looks wrong -- a 40 px arc piece at a system's start bound to a notehead box near the clef 2.8 sp away (the
  piece is the tail of an arc from the previous page; the false head box defeats the edge test).

**Job 2 -- kind refusals (both ends bound, kind refused), r6 replay, by cause:**
Litolff 31: 13 the two heads' staff positions (geometry reader, from their boxes) stand 0.17-0.44 sp apart for what is one note (step
conflict 7, step between 5, plus 1 Brahms) -- box drawn tall/off its head (crops: half-note dyads, a box cut short); 9 far-head ledger reader
abstained on both ends (8 of them also in the empty interval); 5 a box taller than a head (head + its stem/ledger ink or a fused dyad) whose
two readings disagree; 5 same pitch with a head between. Brahms 25: 13 same pitch with heads between; 7 accidental printed on the stop
note; 3 accidental state unknown; 1 two ledger counts differ where positions agree; 1 box centre 0.46 sp off where ledger steps agree.
Crop looks (10 minutes, leads): heads between = a notehead box on an `sf`/`ff` dynamic kept usable (2 of 5), the displaced head of a second
in the stop chord (1), a real long slur with same-pitch ends (1: the page-facts rule says slur, the binder refuses because it cannot tell the
voice of the heads between). Accidental printed (1 looked at): a real pitch change (flat on the stop note) -- a slur the binder cannot call
because it compares only "printed on the stop" without the start's sounding pitch.
**Fix at the source:** position from the head's INK (2.290 page head / M6a ink position) instead of the box -- the largest Litolff bucket;
the far-head ledger reader's abstentions; notehead boxes on dynamics refused at ADJUDICATE (claim order: words/dynamics claim first); chord
membership by shared stem (a second's displaced head); the accidental comparison done on sounding pitch (EVALUATE has it), not on "printed".
Not built here.

**Gates.** Fast tier flags OFF 10,698 passed / 2 failed, flags ON 10,696 / 4 -- the 2 common ones were `reach.KNOWN_GAPS` still listing
`Q.PAGE_STROKE` (now read), fixed and re-run green (`test_staged_reach`, `test_staged_check` 25 / 0); the other 2 ON are the default-off
pins. `check` 216, ok (was 217). The 17 arc test files: 141 / 0 OFF; ON 140 / 1 (the default-off pin).
**Open / not verified.** The 12 tiles not yet answered; whole notes nobody boxed are not
seen by the unread-ink guard (no stem); `END_REACH_SPACES` still used by fix 4 (`staff_ink_vs_owner`); direction ("stops short") not in
the rule; scripts: scratchpad r6/ (declines.py, score_tiles.py, kind_causes.py, margins.py, tiles.py).

## 2.305 round 7 (2026-11-15) -- the cause of each r6 miss; built OFF, `lane-2.305-arc-binding`; NOT landed

STAGED, `OMR_PAGE_ARC_WRITE` (OFF). Sean's r6 answers: answers/answers-2.305-r6.json. Rule owning the value: page-facts "An arc ends at the
notes standing where its ink ends" (Sean 2026-11-15).

**Cause (all six misses).** Dropping the reach window let the closest-note rule run on inputs the window had been hiding. In every case the
note list or the ink end handed to the rule was wrong, never the rule's choice among right inputs:
- tile 1 (b): the tie's stop note was boxed in part and ADJUDICATE refused it (`13/0/10/11/3`, `too_narrow`); 2.290 had claimed its ink for
  that box, so the guard counted the ink as read; the end reached the next note 10 spaces on. The window had answered "no head".
- tile 3 (b): the half-note chord the tie starts at has NO notehead box at all, only ledger boxes (and an `arpeggiato` box); its hollow heads
  are shattered by the ledgers, so no head-sized blob exists; the start reached an eighth 6 spaces back.
- tile 5 (b): the left end of a system-start piece "bound" a box on the key signature that ADJUDICATE NARROWED (key claim), not refused;
  the binder used `not refused` as "a note", so doubt became a note and defeated the system-edge test.
- tile 8 (a)+(d): the page map carves barlines out of strokes, so the slur's page stroke ended AT the barline; r6 always took the stroke end
  as the ink end (2.271 took it only when it ran PAST the trace). And the 2.223 window's 2.5-space height limit had been the only "an arc is
  OVER its notes" guard on detector curves.
- tile 12 (c): `unread_ink_at_end` -- the "unread" ink was the top of the tied head itself, cut off by its own ledger line (box drawn low).
  Its twin tile 9 has no ledger cut, so no blob, so it bound.
- tile 7 (c): the cup's left end stands between two chords' stem tips about equally close (`two_columns_at_end`, 0.28 sp apart); with no
  binding, the old fallback decided its boxes "tie" and the old box-merge that had produced the slur no longer ran. Not fixed (the rule's
  abstention is right; the old fallback is what changed).
**Process lesson.** A guard defined by "a box stands on it" inherits every box fault: refused boxes, narrowed boxes, boxes drawn off their
head, ledger boxes on staff lines. The guard must be defined on the page's own facts -- the verdicts, the claims, the staff lines -- and every
"read" in it must be ADJUDICATE's reading, not GATHER's box.

**Built (rule's words, no new number):** (1) a notehead box refused or narrowed reads no note, and 2.290's claim made for refused boxes reads
none; (2) a narrowed head is never a candidate but is note-like ink at the end ("cannot tell" where as near) -- also Sean's tile 2 stop note
`14/7`, narrowed `stem_end_ink_only`; (3) page-facts "there is no far note without a ledger": a column of ledger lines (outside the staff
body, `page_heads`' rung test) with no read note in it is a note nobody read; (4) a blob that, joined with a read head beside it, is still one
head's size is that head's ink (`page_heads` shape numbers); (5) the ink ends at the OUTERMOST of the traced end and the stroke end;
(6) the closest note wholly on the arc's far side (a cap's above its end, a cup's below) -> `head_on_the_arcs_far_side`. Controls:
`tests/test_arc_ends_r7_2_305.py` (real rows, fixture `data/rule_arc_ends_r7_2_305.json`): NEVER tiles 1, 2, 3, 5, 8; YES tiles 4, 9, 12
and a twin (the head unboxed -> its cut-off ink refuses again). The r6 replay is the failing-first evidence (each pair written wrong / not
written there); the test file itself cannot run on the r6 tree (new arguments).

**Causes over ALL arcs r6 changed (r6base vs r6new2, 4 pages a plate):** r6 wrote 23 new, removed 7. r7 keeps 13 of the 23 (incl. Sean's
right 2, 4, 6, 9, 11) and removes 10: (b) a note nobody read -- refused box 1, ledger column 2 (tile 3 and its chord's slur), narrowed box
1; (a) ink end at a barline cut / end moved to the outermost ink 5 (tile 8; unjudged: Litolff `15/1/3/1/2`, `15/1/9/9/3`, Brahms
`0/0/11/0/4`->`1/6` now back to the baseline's `1/13`, `20/1/8/4/1`); 1 unexplained (`20/1/8/4/7`->`4/6`, an old-path arc). Of the 7 removed,
r7 restores 3 (Brahms, incl. tile 12: the head's own ink); 4 stay lost, all (c) `two_columns_at_end` (tile 7; r2 tile 1 at 0.47 sp;
Litolff `15/1/8/10/0`, `15/1/9/9/3`->`10/2`).
**Upstream, counted, not patched:** r7 replay, ends refused by the guard: Litolff narrowed heads 9, unread blobs 13, ledger columns 2,
another staff 7; Brahms narrowed 2, blobs 6, another staff 7. Narrowed real heads (ADJUDICATE's head reader) and unboxed hollow heads on
ledgers (detector) are the two upstream sources; `0/0/11/3/12` (tile 8) is an empty notehead box beside a stem. The chord column by x (tile
2's black head of the other voice, one stem touching both) needs the voice / chord reader, not the binder.

**Measures** (re-adjudicated saved 2305 gathers, same stages; baseline = 18ba158f9 merge before r6):
- lane_report file change, baseline OFF vs ON -> r6 -> r7: Litolff ties +18 / +24 -2 / +22 -2, slurs +7 -39 / +36 -44 / +29 -43; Brahms
  ties +10 -2 / +10 -2 / +12 -2, slurs +30 -101 / +40 -99 / +33 -98; Brahms p0+p1 ties +18 / +18 -2 / +20 -2, slurs +22 -70 / +29 -77 / +23 -71.
  Judged answers right->wrong 0 and unwritten->wrong 0 on all three, every arm.
- Sean's arc tiles (r1, r2, r4, r6; by glyph key; a different arc from the same start counts WRONG): r6 -> r7: 4 wrong -> right (r6 tiles 1, 3,
  5, 8), 1 unwritten -> right (r6 tile 12), right->wrong 0, right->unwritten 0. Baseline -> r7: right->wrong 0, right->unwritten 2 (r2 tile 1,
  r6 tile 7), unwritten->right 4, wrong->right 1.
- Page-pass declines r6 -> r7: Litolff written 175 -> 165 (ties 127 -> 118), `unread_ink_at_end` 5 -> 17; Brahms 275 -> 273.
- Tiles: out/print/2.305-r7 (12 unjudged r6->r7 changes: 4 arcs r7 writes, 8 it removed; whole arc in the crop, box on the two notes only),
  key out/print/2.305-r7-key.json. Tile 3's crop is very wide (the old path's arc: every curve over the notes' span is shown).

**Owed from r6.** Fast tier on the r7 tip, flags OFF: 10,709 passed / 0 failed; flags ON: 10,707 / 2 (the two default-off pins). `check` 216, ok. Whole note nobody boxed: on ledger lines the r7 ledger
column sees it; on the staff the page fact that would see it is the hollow head-shaped page stroke (`Q.PAGE_STROKE` blob `hole_share`, filed),
but Litolff hollow heads are shattered by the staff lines (tiles 1 and 3: every piece `hole_share` 0.0), so it is not built -- measure first.
**Held for Sean (not built):** a short arc whose two ends find the same closest note.

**r7 tiles remade (2026-11-16; Sean could not answer the note-boxed r7 tiles).** out/print/2.305-r7b (sheet.png), key out/print/2.305-r7b-key.json.
Each box is the arc's OWN ink as the binder had it (a page run's points; a 2.223 curve's pieces, each the union of its own page strokes plus its
traced/stroke end), ticks under the two notes the file joins. Of the 12 unjudged r6->r7 changes, 6 qualify; 6 came from the OLD box path (no ink of
ours behind them) and are not tiled. Flag ON (r7), written arcs by source: Litolff 192 = page pass 99, curve binding 28, old box path 65; Brahms
300 = page pass 203, curve binding 23, joins across systems 4, old box path 70 (baseline ON: Litolff 49 old of 187, Brahms 67 of 296).
**Scoring vs the reader.** The tile replay (`score_tiles.py`) matches an arc by its two NOTES only; the reader works from ink. So an arc counts
"right" when the notes match even if the ink it bound was another arc (Sean's arcs-combined r2 tile 9 is exactly that), and a third of the
written arcs are the old box path's, which no ink-based rule produced. Not fixed here: the replay needs the ink id (page run / curve) Sean's tile showed.

## 2.305 round 8 (2026-11-16) -- why an arc's ink is partial; scoring by ink; the new reader alone. `lane-2.305-arc-binding`, NOT landed

STAGED, flags OFF. Sean's r7b answers: answers/answers-2.305-r7b.json (3 of 6 boxes hold only PART of the arc).

**Cause.** The arc's ink reaches the binder through two GATHER steps that each cut it, and nothing joins the cuts back:
- tile 3 (Litolff p13 `13/0/0/13/7`) and tile 5 (Brahms p0 `0/0/11/0/25`): the tie / slur runs ALONG a staff line where it meets its note.
  The page stroke map is built from each staff's ERASED band (`page_strokes`, GATHER), so the stretch lying on the line is erased with it;
  what is left is a stroke that stops where the arc meets the line, plus small `horizontal` pieces on the line that nobody holds (tile 5: stroke
  1495, unclaimed; tile 3: stroke 4212, unclaimed). The curve's trace follows its stroke (ONE_CURVE) and stops at the gap.
- tile 2 (Litolff p15): two slurs CROSS; the printed arc is read by THREE detector curves (`15/1/9/9/11`, `15/1/10/10/6`, `15/1/10/9/2`) from
  boxes in two staves' cells. The 2.166 join joins a staff's own boxes only where a barline cut them, so each curve traces and claims its own
  stretch (`15/1/10/10/6` claims the stroke past the crossing, 2358); the one Sean saw holds only the crossing.
- tile 4 (removed by r7): reason word `system_edge` -- WRONG. The start note `0/0/9/0/7` is real; ADJUDICATE narrowed it
  (`claim_narrowed:word`, a word's claim over it); r7 took narrowed heads out of the candidates and the edge test then found "no note behind
  the end". Fixed (r8, forced by the cause): note-like ink nobody could read ahead of an end is a note there, never the edge (the end now says
  `unread_ink_at_end`, naming the narrowed head). Control `test_never_r7b_tile4_...` fails on the r7 tree, passes here. The arc stays
  unwritten until the head reader reads that note (upstream: real heads narrowed under word claims).
**Process lesson.** "Read and claimed once" was tested per READER, never per printed mark: a mark can be cut by the eraser before any reader
sees it, or read by several readers that each claim a part, and every reader passes its own test. A claim check must count, per printed arc,
how many readings hold its ink and whether any ink of the same line is left.

**Counts (A).** First automatic count ("curve-like ink continues beyond an end at the arc's height"): print-checked 9 hits, 0 true (8 were the
next mark at a note: head pieces, the next arc meeting at the note, ledger/beam/staff residue) -- withdrawn. Second, restricted to ends that
stand where no notehead is: Litolff 32 of 428 curves and 19 of 358 runs, Brahms 25 of 565 / 10 of 443; print-checked 9 Litolff hits, 1 true
(two crossing slurs, tile 2's kind) -- NOT trusted either. Structural count that holds up better: curves that read the SAME ink as another
curve (traces within a third of a space over at least a space): Litolff 252 of 428 curves (116 the same extent read twice, from two staves'
padded cells; 6 a shorter curve inside a longer one; 4 pairs overlapping as parts), Brahms 371 of 565 (163 / 21 / 5). Print-check of 2 Brahms
"part" cases: 1 true (a tie across a barline, the cell after the barline traced alone), 1 false (two slurs meeting at a note). Honest
size: one printed arc is commonly read 2 or more times (same extent), and a few per page are read in pieces; the erased-staff-line gap (tiles
3, 5) has no reliable count yet -- it needs the erased band's own pixels, which the record does not keep.

**Scoring by ink (B)** (`score_ink.py`): an answer is right only when one of OUR ink readings (a page-pass run, or a 2.223 curve whose binding
gave the kind) wrote its two notes with Sean's kind -- and for the r7b tiles, the SAME ink the tile boxed; an old-box-path arc is `old_path`.
r1/r2/r4/r6 tiles boxed notes, not ink, so their ink is "any ink reading of ours"; arcs-combined r2 tiles come from another gather (glyph keys
differ) and are not scored. 50 tiles: baseline right 37, old_path:right 1, wrong 3, unwritten 9; r6 right 30, old_path:right 2, wrong 10,
unwritten 8; r7 right 38, old_path:right 2, wrong 4 (incl. r7b tile 3 partial ink, r7b tile 4 other notes), unwritten 6.
**The new reader alone (C)** (filtering the written file, no flag): r7 Litolff 192 -> 127 arcs (ties 86, slurs 41; the old path wrote 36 ties,
29 slurs), Brahms 300 -> 230 (160 / 70; old path 9 ties, 61 slurs). Judged tiles: right 38 (the 2 old-path rights become unwritten), unwritten 9.
Why the page reader did not write the old path's arcs (r7): Litolff 65 -- no ink reading of ours ends at those notes 19, a run of ours wrote
those notes' ink to other notes 13, `unread_ink_at_end` 11, `two_columns_at_end` 10, kind refusals 6, other 6; Brahms 70 -- no ink reading
ends there 40, run wrote other notes 12, `same_pitch_heads_between` 6, `end_far_beyond_head` 4, other 8. The "no ink reading" bucket (59) is
not crop-checked: either the old path pairs a box with no arc ink there, or the page-ink reader never traced it.

**r8 small test: is partial arc ink the main problem?** (no reader change)
- Test 1, a random sample for Sean: out/print/2.305-r8-sample (sheet.png; seed 2305008, 6 per plate, from 639 Litolff / 873 Brahms ink readings
  that reached the binder in the r7 replay, same-extent duplicates dropped), key out/print/2.305-r8-sample-key.json. Unanswered.
- Test 2, the judged misses under score_ink (r7 wrong 4 + unwritten 6, + r7b tiles 2, 3, 5; 10 distinct arcs): partial ink 3 (r7b 2, 3, 5);
  complete ink but wrong or missing note 5 (r2 1 two voices about equally close; r2 8 lower chord member never boxed; r4 5 one head boxed on two
  staves; r6 7 two chords' stem tips about equally close; r7b 4 start note narrowed under a word's claim); complete ink but kind refused 2 (r1 9 = r2 9,
  r1 11 = r2 5: one end's position misread); other 0.
- Test 3, 10 of the 59 "no ink reading of ours ends at those notes" old-path arcs (seeded; lane's crop look, a lead): no arc between those notes
  on the print 3 (the old path invented it); arc there, never boxed 0; boxed, never traced 0; traced but our reading ended at other notes 7 (2 of
  them unsure). Crops: scratchpad r6/r7/noink/.
- Erased stretch, direct check (r7b tiles 3, 5; scratchpad r6/r8-erased-tile3.png, -tile5.png: the page-stroke map's kept ink vs the un-erased
  page): the missing stretch IS on the page, running along the staff line between the traced arc and its note; the stroke map lost it.

## 2.305 round 9 (2026-11-16) -- the page pass stands alone; judged by right / wrong / unread on Sean's swept Brahms p0. `lane-2.305-r9`, NOT landed

STAGED, `OMR_PAGE_ARC_WRITE` + `OMR_ARC_MEETING_AT_HEAD` (both OFF by default; the OFF file is byte-identical before/after on Brahms p0 and Litolff p13).
Rules owning the values: page-facts "An arc ends at the notes standing where its ink ends" (Sean 2026-11-15); "an arc is OVER its notes"; "a tie only
ever happens between 2 adjacent notes of the same pitch ... spanning multiple notes is always slur" (Sean 2026-10-29); DECISIONS 2026-11-13 NO OLD
READER BESIDE THE NEW ONE; north star "all ink is accounted for one time".

**Process.** ONE gather per page on the lane tree (Brahms p0 `g0`, Litolff p13 `l13`; both flags ON so the page-ink rows exist; Surya on, checked in
the log), every arm re-adjudicated from it (`r9/replay.py`, `r9/arms.sh`, `r9/arm_tree.sh`; the before arm runs the merge-base tree bb913d15c and
reproduces the lane-tree baseline byte for byte). `r9/replay.py` taps the exporter's own calls to name the PATH that wrote every arc span:
page_arc (page-ink run), curve (2.223 detector curve bound at both ends), old_box (`_paired_spans` over unreplaced detector boxes), record_tie (the
old `Q.TIE_PAIR` box pairing). `r9/tally.py` repeats judge.py's own arc matching and keeps the per-arc detail.

**Cause tally, flags ON before this round** (judge.py: slur 14 wrong / 31 right / 8 unread, tie 1 / 37 / 7):
- slur WRONG 14 = old box path 10 (doubles 4: P179 written twice from two staves' copies of one box, 12/4/4->12/5/0 twice, 9/2/3->9/2/1 a slur on
  the notes the page pass had tied; wrong ends 6: a long slur the page pass declined, the old path pairing a cell's PIECE of it with the notes under
  that piece -- P205, P209, P238-area, P226-area, P234-area, 6/1); 2.223 curve 3 (P162 read by two curves from two staves' cells and written twice;
  9/4/3->9/4/5 bound short of P209's end; P170 = scorer artefact, below); page pass 1 (P166 = scorer artefact).
- tie WRONG 1 = old tie pairing (13/4/2->13/5/0, no arc of his).
- Why the page pass declined the ink the old path then wrote (by run reason, crop-looked on staves 5, 9, 12): (a) the run's HOME staff was the staff
  on the arc's FAR side -- cups under staff 5's low notes lie nearer staff 6, caps over staff 9 nearer staff 8 -- so the closest notes it saw were
  the wrong staff's and the ends came out `continues_in_another_curve` / `nearer_note_on_another_staff`; the existing retry on the arc's own side ran
  only when both ends said `head_on_the_arcs_far_side`; (b) `same_pitch_heads_between`: one slur under six repeated notes (P179, P254, P241) is
  refused although Sean's rule says it is a slur; (c) end reasons upstream (step_conflict on staff 5 head boxes cut by ledgers; end_far_beyond_head
  at stem-tip ends; unread ink).
- Scorer artefact (ours): MusicXML puts a chord's slur on the chord's first written note; judge.py measures that note's box against his arc's
  box, so a slur bound to the right chord's UPPER notes is scored wrong + unread when the lower note sits > 3 sp from his box (P166, P170).

**Process lesson.** The old reader's arcs looked like coverage, but on judged cells it wrote 4 right and 10 wrong slurs; its "rights" hid that the
page pass declined real arcs for a reason of its own (the wrong staff), so measuring the new reader WITH the old one beside it never showed that
reason. Measure a new reader alone, by path, against judged truth -- the old path's presence is what kept the cause invisible.

**Built (flag ON only):**
1. `export._place_arcs`: a detector box no reading of ours bound writes nothing through the old box path (`old_box_path_retired`).
2. `export._retire_old_tie_pairs`: a tie pair the old box rule made is dropped; a pair a curve binding traced (`paired_by_page_binding`) and the
   page-ink runs' ties stay (`old_tie_pairing_retired`).
3. `export._page_bound_slur_spans`: two readings that join the SAME two notes are one printed slur, written once.
4. `page_arc_bind.far_side_ends` (used by `ownership.adjudicate_page_arc_binding`): an end is a far-side end also when the binder found a nearer
   note of the neighbouring staff on the arc's own side, or left it "half of another arc" while the note it names stands wholly on the far side
   (cup: head top below the end; cap: head foot above it); both ends so -> bind once more on the staff of the arc's own side (existing retry). No number.
5. `ownership._heads_under_the_arc`: same pitch at both ends and every head between on the arc's notes' side of the line joining its two ink ends ->
   slur (`page_binding_same_pitch_notes_between`); a head on the far side keeps the refusal. No number.
Controls (`tools/omr/tests/test_arc_page_pass_alone_r9_2_305.py`, 12; rows copied from the r9 gather): YES P195 cup, P205 cap, P179, P162, P180;
NEVER a cup end under its own note, a head the cup does not span, the wrong side; flag-OFF twins. 10 fail on the merge-base tree, 2 (OFF twins) pass.

**Measure 1 -- judge.py, Brahms p0 swept cells (wrong / right / unread):**
- slur: OFF 25 / 29 / 10; ON before 14 / 31 / 8; **ON after 2 / 32 / 7**. tie: OFF 3 / 33 / 9; ON before 1 / 37 / 7; **ON after 0 / 37 / 7**.
  Every other kind identical before/after. The 2 slur wrongs left are the scorer artefact (P166, P170: written on the right chord).
- Written by path after: page pass 70 spans, curve 6, curve ties 5, old paths 0 (before: page 63, curve 8+5, old 23).
- Unread after: ties P191, P192, P215, P230, P253 run off the page's last bar to page 1 (not in this one-page gather, unscoreable here); P185, P189
  step_conflict (head boxes cut by ledger lines, upstream); slurs P243 / P234 end_far_beyond_head at a stem-tip end, P161 unread ink, P160 and
  P237 bound by the page pass but not in the file (not traced), P166 / P170 scorer artefact.
- Litolff p13 (no swept cells: no right/wrong/unread exists): ON before -> after written arc spans 81 -> 63; 9 old tie pairs and 3 old box slurs
  removed. Why the page pass does not read those (by its run): no page-ink run over the box 4, step_unread / step_conflict 2, end_far_beyond_head 1,
  unread_ink_at_end 1, none found 1 -- the r8 erased-stretch / head-position causes. Their rightness is what the tiles ask.

**Measure 2 -- tiles.** out/print/2.305-r9/sheet.png (12, seed 2305009, 6 per plate from the changes; key out/print/2.305-r9-key.json): 9 removed,
2 doubles reduced to one, 1 added. Box = the ink the reader held (page run points; a curve's boxes; for a removed old arc the detector boxes it
paired, each drawn as its own box). Remade the same day (coordinator): same 12 places and key, one staff per tile, every tile 1250 px wide and
>= 450 px tall (a short band set on plain paper, never widened onto the next staff), each piece of ink its own box, and per tile one line in the key
(`file_said`) saying what the file wrote before and writes now. Unanswered.

**Measure 3 -- judged answers right->wrong: 0.** `judged score` (notes) per item identical before/after on Brahms p0 and Litolff p13. Sean's arc
tiles on these pages (`r9/tiles_replay.py`): Brahms p0 8 right->right, r7b tile 4 wrong->unwritten (its start note is held in doubt, r8);
Litolff p13 7 right->right, r2 tile 1 wrong->wrong (unchanged). Fast tier (flags OFF, tip 61a5f49b6): 10,722 passed / 1 failed -- the 2.274
pin "one pitch with a head between is not claimed a slur" (a drawing), which Sean's rule reverses; rewritten in d9ef40329 with a far-side twin
(file 20 / 0). Arc test files with both flags ON: 518 passed / 3 failed = the two default-off pins + that same pin (before the rewrite).

**Old box path: OFF with the flag ON** (both the slur box path and the old tie pairing). What still stops a landing: the r9 tiles; the Litolff ties
the old pairing wrote and the page pass does not read (page-ink run missing over the erased stretch; head positions); page-to-page ties need the
next page in the gather (r4's join exists, not exercised here).

## 2.305 round 10 (2026-11-16) -- why the page pass dropped real arcs Sean judged on r9; three fixed at the source. `lane-2.305-r10`, NOT landed

STAGED, both arc flags ON (OFF file byte-identical on the same gather). Sean's r9 answers: answers/answers-2.305-r9.json (main). New gathers on the
r10 tree (Brahms p0 `g0b`, Litolff p13 `l13b`, Surya on); every arm re-adjudicated from them; the before arm is the merge-base tree bb913d15c.

**Cause tally -- the five real arcs r9 removed, Sean's tile 10, and the other unread (by first stage that lost it):**
- Brahms tile 5 (tie 9/0/7 -> 9/0/9) -- ADJUDICATE, a guard wrong here: both notes are held in doubt only because the word "espr. e legato" claimed
  first (`claim_narrowed:word`); EXPORT writes them (guessed), but the binder called them unread ink -> `unread_ink_at_end`. FIXED.
- Brahms tile 9 (slur 12/0/4 -> 12/1/1) -- ADJUDICATE: the run bound its right end `two_columns_at_end` (12/1/1 against the chord 12/1/2), although
  its traced ink runs onto 12/1/1's head. FIXED.
- Litolff tile 4 (tie 13/1/5/10/0 -> 11/2) -- GATHER: no run at all; the tie's ink was blanked whole by two FALSE detector boxes, a "timeSig1" and a
  "clefF", that no page-wide header claim holds (crop: out/print/2.305-r10/crossings/litolff-p13-tile4-x1954-before.png, red = blanked).
  FIXED in GATHER: the run is now read whole across the barline (…-after.png). Still not written: its left end is refused
  `continues_in_another_curve` (it meets the previous tie at its note) -- open.
- Litolff tiles 1 and 10 (upper) -- ADJUDICATE kind refusal `step_unread`: both ends bound, both far heads whose ledgers were not read, their local
  positions 0.30 / 0.33 sp apart (inside the 0.168-0.435 empty interval) -- upstream head position (head "too_tall" for the ink centre). Not fixed.
- Litolff tile 7 (upper tie 1/11/4 -> 1/12/2) -- bound and WRITTEN by the page pass, dropped at EXPORT `tie_pitch_contradiction` (C6 vs D6; both far
  heads ledger unread) -- upstream pitch. The tile's own pair (the lower cup 11/6 -> 12/4) and tile 10's lower cup -- GATHER, no run: the cup lies
  along the bottom staff line; nothing tracked (not fixed).
- Litolff p13, the 9 ties r9 removed: none returned this round (4 had no page run, 2 step_unread / conflict, 1 end_far_beyond_head, 1 unread ink, 1
  no box found; tile 4 now has a run).
- Brahms P160 -- bound, dropped at EXPORT: its stop note is `duration_narrowed` and not written. P237 -- bound to 11/2/7 -> 11/3/7, both written, but
  neither is in the note index `_page_bound_slur_spans` builds for any part (not traced further).

**Is the page reader's run cut at a barline? No.** `r9/barline_cut.py` (the record's own runs): Brahms p0, Sean's 51 labelled arcs that cross a
barline: one run WHOLE across it 47, CUT 2 (P183, P188), none 2. Litolff p13 (no labels; 150 places where two detector arc boxes meet at a barline):
WHOLE 136, one side only 7, none 7. The barline column is carved, the tracker bridges it (crop: crossings/brahms-p0-P187-tie-x4107-whole.png, green =
the run, white gap = the carved barline). The "mark through the middle at the bar line" Sean saw on tiles 7 and 10 is the DETECTOR's two boxes cut at
the cell edge, not the page run; where the arc is lost it is refused later (binding, kind, export) or blanked before (tile 4).

**Process lesson.** Each real arc r9 lost traced to a DIFFERENT stage -- a false header box blanking ink in GATHER, a doubt flag from an unrelated
claim at ADJUDICATE, a pitch reader at EXPORT -- and the old pairing had been covering all of them. Retiring a reader needs every judged arc of the
place replayed per stage first; one count over the page hid three causes.

**Built (flags ON only):** `ownership._head_read` reads a note narrowed only by a word's claim; `page_arc_bind.ink_ends_on` (two notes about equally
near, the traced ink runs into exactly one head -> that note; no number); `page_arcs.unclaimed_header_boxes_dropped` (GATHER: a detector clef / key /
meter box whose centre no page-wide header claim holds blanks nothing; Litolff p13 20 of 96 header boxes, Brahms p0 10 of 110). Controls
`tools/omr/tests/test_arc_page_pass_r10_2_305.py` (8, real marks of tiles 4, 5, 9; 6 fail on the r9 tip).

**Measures.** judge.py Brahms p0 (wrong / right / unread), same gather g0b: before (merge-base, ON) slur 14 / 31 / 8, tie 1 / 37 / 7; **r10 ON slur
2 / 32 / 7, tie 0 / 37 / 7** (as r9; tiles 5 and 9 lie outside his swept cells). Arcs r10 changed against r9: 3, all added, all already judged right by
Sean (tile 5, tile 9, r7b tile 4); Litolff 0. Sean's 12 r9 tiles replayed: r9 -> r10 right->right 6 (2, 3, 6, 8, 11, 12), unread->right 2 (5, 9),
unread->unread 4 (Litolff 1, 4, 7, 10). Judged answers right->wrong 0 (`judged score` per item identical, both plates; arc tiles Brahms 8 right->right
+ r7b tile 4 wrong->right, Litolff 7 right->right). No new tiles: every arc this round changed already has Sean's answer. Fast tier on the final tools tip b1395de03 (no edits during the run): 10,732 passed, 0 failed.

## 2026-11-23 -- why arcs read on the page are not written (small test on overnight 20261122-night, frozen sample, STAGED; agent read, sheet not judged)

The ranking row "ties and slurs not written (arcs)" (Litolff 514, Brahms 696; `counted_marks.arcs_count`, 2.316) reproduced and split. Cause: about a quarter to a third is counting error, and of the real losses the largest share is BINDING an arc's ends to its notes at ADJUDICATE, not the arc reader.
- Counting faults (135 / 212): old tie boxes whose arc a page run DID write 33 / 88; old tie boxes on a page run already counted unwritten (one arc counted twice) 89 / 124; 13 runs from Litolff's context page 1 (`counted_view.ARC_QUANTITIES` leaves out `page_arc_binding`). The 208 / 416 "old-box refusals" come from the tie pairing 2.305 retired.
- Binding, `ownership.adjudicate_page_arc_binding` -> `page_arc_bind.closest_binder` / `arc_claim.bind_end` (about 210 / 192 runs): end more than 2 spaces from its note 66 / 32; two notes about equally near 34 / 9; unread notehead ink at the end 36 / 12; runs off the system edge 44 / 114 (sample pages are not consecutive); tie-or-slur untold because head positions conflict 36 / 19.
- EXPORT (about 50 / 65): bound but its note not written; tie pitch contradictions. Reader, GATHER (about 119 / 227): runs cut into pieces 32 / 23; old tie boxes no page run covers 86 / 204 (roughly half real on a sample).
- Upstream for the largest cause: of 77 Litolff "too far" ends, 63 have no head box within 1.5 spaces of where the ink ends; median distance 3.4 spaces, about a stem's length. The binder measures from the note's BOX CENTRE against a 2.0-space cut (kept by 2.305 r6 as "only declines"). The ends are slurs ending at a stem tip, ties beside a different chord member, a few bound to the wrong staff. Sean's 2.305 r8 tile 10 (Brahms p0 run 76), judged a complete real arc, is refused at 2.017 against 2.0.
- Sheet of 20 (agent's look: 17 real arcs; 13, 18, 19 none): `out/print/overnight-1122-arcs/sheet.png`. Lesson: a ranking row that mixes a retired path's boxes with the new path's runs counts one arc twice; and a distance from a box centre is not a measure of the mark (CLAUDE §4, joining goes by ink). ROADMAP 2.338.
