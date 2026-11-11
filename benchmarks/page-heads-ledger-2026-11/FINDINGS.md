# 2.290 — Page heads on the ledger: round 1, measure + plan (2026-11-10)

STAGED, no code. Branch `lane-2.290-page-heads` 2c4868ca8. Plan: docs/plan-2026-11-10-page-heads-on-the-ledger.md.
Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Cause and process lesson
M6 (page heads) sat OFF for five days because it was planned from a document, not the tree: it built its own twin
fold (IoU 0.5) while two other head identities were already ON — `Q.MARK_GROUP` (box IoU 0.3, 10-07; read by export
write-once, `export_unison`, `glyph_owner`, `rhythm`) and `Q.PAGE_MARK` (shared ink 0.5, 2.240, 10-31; read by the
page owner). They disagree: 3,402 Litolff boxes are 2,706 heads by one and 2,826 by the other (591 pairs joined by
both, 234 only by IoU, 57 only by ink). Lesson: re-brief a plan with grep on the tree before building it; and a
refusal count is not a loss count.

## The three OFF flags today
`OMR_PAGE_HEADS` (M6a): file-only, nothing reads `Q.PAGE_HEAD`; all three ON vs OFF on Litolff p2 changes no note and
no head-box fate. `OMR_PAGE_HEAD_VIEWS` (M6b): the only part with a wanted effect (far-head trigger by box OR ink
centre). `OMR_PAGE_HEAD_CLAIM` (M6c): now a translation of ids the 2.284 ledger links exactly; cost one judged
right→narrowed on 11-05.

## Sizing (saved GATHER rows replayed; pre-2.285 gather)
Litolff 3,402 boxes: 66.5% written, 18.8% copies of a head, 9.6% refused as non-heads. Brahms 1,737: 63% / 11.7% /
19.9%. Head ink with one owner 77% (Litolff p2+p10; 18% twin-claimed) and 91.5% (Brahms p0; 2% twin). Only 6 of 844
twin drops are true orphans: the twin zoo costs code, not notes.

## Sean's tiles (answers/answers-2.290-r1.json)
Every sampled head-box refusal is right (7/7: a beam, two tremolo slashes, a part of a note, a ledger line, barline
ink, a tall chord box); three written controls are notes; two real heads dropped as `owned_by_another_staff` (the
2.289 loss). **The lane's crop look said 10/10 boxes held by the tremolo claim were printed heads; Sean calls both
sampled ones tremolo slashes — the "16 heads lost to the tremolo claim" is NOT supported.**

## The three open cases and where the plan fixes them
Phantom `doubleWhole` over a beam (`stroke_owner.shape_fit` accepts a 2.12 x 0.56 sp beam piece as `head_lens`) →
step 6. The ff touching a head box (`hairpin_reach.word_area_sparing_heads` drops whole components touching a note
box) → step 5. `DYNAMIC_SPARES` by box not pixel → step 5.

## Plan (steps; each names what it retires — see the plan doc)
1 one identity (measure) · 2 one identity ON · 3 one position / far-head read per head · 4 one claim per head on the
ledger · 5 pixels where a head meets another claim · 6 refusals from ink · 7 ink-only heads (on Sean's yes).
Build of steps 1, 2, 4 started 2026-11-11 on `lane-2.290-build`.

## 2.290 build r1 — one identity, one claim per head (2026-11-11 overnight; built OFF, tiles unanswered)

STAGED GATHER + ADJUDICATE. Branch `lane-2.290-build`; `lane-2.290-build-pre-retire` = the flags-OFF build (fast tier 10385 passed / 0 failed);
the branch tip is the RETIRE commit (the landing commit: flags deleted, old mechanisms deleted) — include it only on Sean's approval.

**Cause.** Three answers to "which boxes are one head" (`Q.MARK_GROUP` IoU 0.3, `Q.PAGE_MARK` shared ink, M6a fold) and none asked the ink whether two
boxes stand on ONE printed head; head ink was claimed per padded cell by box coverage, so one head's ink was a head in one cell and a twin in the next.
**Process lesson.** (1) The box's own clipped ink is a biased witness of where a head is: round 1 split 56 twin pairs because each box clips the head
differently; the stroke the box stands on (a head-sized stroke is one head) is the witness. (2) A lane-report `--from gather` record carries the
GATHER-time verdicts: an ADJUDICATE-only change re-armed on it measures nothing (r3's Brahms "eighths read as quarters" came from the gather-time code,
gone after re-adjudication). Re-adjudicate both arms on the tree (`readjudicate.py`) before trusting an ADJUDICATE delta.

**Built.** `page_heads.read_one / core / partition / choose_claims / file_one_claims`; one identity filed as the notehead `Q.MARK_GROUP` rows
(`gather_mark_groups(page_heads=)`) and the head `Q.PAGE_MARK` ids (`page_marks.gather_page_marks(page_heads=)`); one `Q.CLAIMED_AREA` per head (owner
`head`, unit `page_ink`, source `page_head_one`, `page_strokes`, `members`), after accidental ink; `adjudicators/stroke_owner._page_head_claims` hands each
cell the claim on its LINKED strokes (`page_ledger` link rule) at the head tier, `how` area (on the ledger), the head's shape test kept;
`stroke_owner._settle`: a page head and its member boxes are ONE owner (decided, never merged); the one consult (`ink_consult`) holds a page head's ink
final against later OWNER families (accidental, dot, dynamic, articulation), never a rest (rests claim first, 2.288) nor a consumer.
Identity rule: two notehead boxes of one system are one head when both hold head ink, share >= 0.5 of the smaller's, and either stand mostly on the same
head-sized stroke (centres < 0.9 sp apart) or their ink centres lie in one oval (0.65 sp across, 0.75 sp along: nothing is printed a step apart at one
x); joins need every member in one oval (no chain across a chord); a box on no head ink makes no head (joins at the old IoU 0.3 twin rule, else alone).
Claim rule: a page stroke is the head's when >= 0.5 of it lies in the head's oval (the 2.220 trim, else a printed-head-sized oval at the ink centre),
it is head-shaped and no bigger than a head, no other head's oval holds 0.2 of it, and no earlier page claim names it (then it is MARKED).

**Partitions (same gather pair, notehead boxes):** Litolff p2/p8/p11 1740 boxes: MARK_GROUP 1439 heads, PAGE_MARK 1525, M6a fold 1607, ONE 1418.
Brahms p14/p19 2049 boxes: 1709 / 1739 / 2019 / 1704. Disagreements left (Litolff): ONE joins what the old ones kept apart 40 pairs (same ink, same
oval); ONE keeps apart 33 (little shared head ink 16, two ovals 9, no ink 5, tall read 2, near oval 1). Brahms: 9 joins, 3 apart.

**File (lane_report, flags OFF vs ON, fresh page gathers + re-adjudicated both arms, `out/lane-report/2.290-build-r4`):** Litolff notes +3 -6, flags
+2, beams -1, ties -2, blue +1 -1, red 0 -> 0; Brahms notes +1, flags +1. Judged right->wrong 0, unwritten->wrong 0. Lost: two same-pitch doubles now
written once (p8 m69 F5, p11 m86 E-14: one ink, same pitch); four notes of two boxes at one x 0.6-0.95 sp apart now one (p2 m4 B-14 of a 7-sp tall box,
p2 m7 F3/G3, p2 m32 G3/E-13, p11 m107 A4/B-14) — tiles. Gained: chord members at their own x (p2 m28 E-13, p8 m73 A-12, p11 m104 C3, Brahms p19 m26 E5) —
tiles.

**Ink (`claim_readout ink`, 2.295b tools, same gathers):** Litolff one owner 89.5 -> 90.2%, on the ledger 71.8 -> 77.0, by a cell box 17.7 -> 13.2, twice
5.4 -> 5.2, none 5.0 -> 4.5; notehead on the ledger 0 -> 5.2, by a cell box 5.4 -> 1.1, notehead twice 0.8 -> 0.4. Brahms one owner 87.7 -> 88.3, ledger
65.7 -> 74.0, cell box 21.9 -> 14.3, twice 6.6 -> 6.0, none 5.7 -> 5.5; notehead ledger 0 -> 8.3, cell 8.1 -> 0.6, notehead twice 0.8 -> 0.1.
`judged_claims` ON against OFF: 0 new contradictions on either plate.

**Real cases** (`real_cases/`, 83 of Sean's named marks; crops of 59 cut from the ON gathers, replayed in the fast tier): Litolff 30/31 agree, Brahms
30/30; the one miss (2.289 tile 10, an eighth fused with its chord neighbour into one 1.26 x 3.15 sp stroke) is unclaimed, never mis-claimed: step 5.

**Not built / deferred:** ledger stubs (step 3 with M6b); splitting fused strokes (step 5); refusals from ink, the phantom doubleWhole (step 6: it makes
no page head and no claim here, but its cell box is still refused only as before); the `page_boxes` claims of rests reach the GATHER-side `held`
of the heads but not the cell settle (`adjudicators/stroke_owner._layer_claims` / `_rects` read rectangles only: ROADMAP 2.297).
