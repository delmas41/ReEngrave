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

## 2.290 build, round 2 (2026-11-11) — built OFF, waiting on Sean's tiles

Written by the manager from the lane's report. Branch `lane-2.290-build-r2`
df506a4b9 (flags OFF; the retire commit is NOT included). Sean's r1 tiles: 8
of 12 right (`answers/answers-2.290-build-r1.json`).

**Cause of the four wrong r1 claims**
- Tile 12 (a claim between two half notes a third apart): `page_heads.same_head`
  compared ink centres CLIPPED by each detector box; each box clips toward
  the other, the centres came out 0.53 sp apart and the two heads were called
  one. The file then wrote ONE note where two are printed.
- Tiles 8 and 10 (slivers): nothing checked that a claim is a whole head; a
  rim-of-a-hollow-head allowance (thin piece up to 1.6 sp) and a 0.3 sp
  minimum side let slivers through.
- Tile 9 (half a quarter rest): the detector boxed the rest as a notehead and
  never as a rest, so the rest reader (which claims first) had nothing to fire
  on; the head tier claimed rest pieces by shape. It also wrote a false
  quarter C3 (Litolff p11 m104).

**Process lesson:** an ink centre clipped by a detector box is a biased
witness; a claim must be checked against what ONE head can be; a lone box
whose claim is refused falls back to the old twin rule, never becomes a new
note. Also: `benchmarks/**/crops/` is gitignored, so r1's real-case controls
SKIPPED on a clean checkout — real-case pixels now live in a tracked
`real_cases/npz/`.

**What changed**
- Two head-sized boxes whose centres are >= 0.9 sp apart are never one head
  (`BOX_CENTRES_A_THIRD_SP`; the farthest true twin pair on five pages is 0.85).
- A head claim is refused whole and counted (`claim_size`) when a side is
  under 0.6 sp or it is taller than 1.5 sp. No width cut (a head fused to its
  ledger line is ~2.8 sp wide).
- A lone box refused for size is re-read by the old twin rule (removes the false C3).
- `ink_attachment` could NOT separate the rest from stacked chord heads (same
  contact, 2.4-2.5 sp): the remaining half of that quarter rest is still
  claimed by a head. Only reading rests from ink fixes it.

**Measured** (flags OFF vs ON, fresh arms; Litolff p2, 8, 11; Brahms p14, 19)
- Litolff file: notes +2 -5 (r1: +3 -6). All five lost are one pitch at one x
  written once instead of twice; all three gained are eighths Sean judged.
  Brahms: notes +1.
- Ink on the page ledger: Litolff 71.8 -> 76.5%, Brahms 65.8 -> 74.0%;
  one owner 89.5 -> 90.1 / 87.7 -> 88.4.
- 258 of ~2,400 r1 claims are now refused (192 too small, 52 too tall): that
  ink stays with the cell boxes. Only ~10 of them are on Sean's tiles.
- judged right->wrong 0 (203 / 173 scored); judged_claims no new
  contradiction; check 228; fast tier 10,412 passed, 0 failed.
- All 12 r1 tiles replayed on real pixels; 5 cases fail on the r1 code.

**Not confirmed:** the 0.9 / 0.6 / 1.5 cut-offs are measured on two plates
only. Known misses left for plan step 5: r1 tile 3 (an eighth fused with its
stem stub, unclaimed) and 2.289 tile 9 (unison half note, two thin rims, now
refused by design). Hazard: `claim_readout` slices are cached by file name
and one lane silently reused another's stale slice.
