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
