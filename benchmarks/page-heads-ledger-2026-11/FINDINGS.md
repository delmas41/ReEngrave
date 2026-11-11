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
