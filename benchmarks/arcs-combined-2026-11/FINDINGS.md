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
