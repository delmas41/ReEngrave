# 2.288 — Rests claim their ink page-wide before later readers (2026-11-10/11)

STAGED GATHER, `page_claim_names.py` rest functions (+ `ink_attachment.py` from r4), flag `OMR_PAGE_CLAIM_RESTS`,
default OFF. Branch `lane-2.288-rests-claim-first` (r1 2a0ceb994, r2 313c537b7, r3 f4a59088c; r4 in flight when this
was written). Written by the manager from the lane reports (the lanes' Writes were refused). Answers:
`answers/answers-2.288-r1.json`, `-r2.json`, `-r3.json`.

## Why the lane exists
A rest the detector boxed is not a claim when the page-wide readers run (only a whole rest names strokes, behind
`OMR_PAGE_CLAIM_BOXES`, OFF; rests sit last in the claim layers). 2.285 r1 therefore read two quarter rests as flats.
2.285 landed with a private `rest_box` list inside `page_accidental_ink`; this lane replaces it with a ledger claim
and deletes the list at landing (RETIRE AS YOU LAND).

## Round 1 — a READ rest claims by ink share; the ledger refuses `claimed_by:rest`
Exported file identical OFF vs ON (Litolff p2, p8; Brahms p14, p19). Sean: 10 of 11 claims right; tile 7 is part of an
eighth note's FLAG claimed as a rest. ~45% of Brahms rest boxes — nearly every eighth rest — stood weak and unclaimed.
Own mistake found and fixed in-round: a rest box took the "cr" of "cresc." from a READ word (the word's claim is an
area; the rest step now consults READ area claims).

## Round 2 — the cause was a size where the convention is about attachment
r1's gate was the 2.150b thin-run length: a flag has no long thin run (passed as a rest); an eighth rest's own slanted
stroke has one (called a stem). Rule now (Sean's convention, "a rest stands free; a stem carries a head"):
`rest_attachment` refuses ink that hangs from a stem carrying a head, touches a head, or is a bare vertical.
Brahms weak share 49% / 50% → 17% / 21%; weak eighth rests ~270 → 13. The file was already right at tile 7 and weak
eighth rests were already written plain (275 of 276): the claim gate was stricter than the writer.
Sean: new eighth-rest claims 5/5; refusals 6/7 (tile 2 = half of a real quarter rest refused `touches_a_head`).

## Round 3 — whole/half rests fused to their staff line
Cause: the page stroke is the block PLUS a slab of the line, so under half of it sits in the detector box. Fix: the
0.5 share is asked of the block's own rows. A second cause on Litolff: `shape_fit`'s 1.6 sp width cut (tuned on
Brahms) refused 73 real whole rests on two pages. Whole/half boxes naming nothing: Brahms p14 27 → 9, p19 10 → 2;
Litolff 73 → 1. **Sean: newly claimed whole rests 8/9 — TILE 4 IS A FALSE CLAIM (a filled notehead on a staff line
claimed as a whole rest); still-refused 2/3 (tile 1 a real whole rest refused).** The lane's own look had said all
nine were rests and its synthetic control passed. Not landable on r3.
Process: the lane ran a broad `pkill -f` on shared process names; forbidden in every later brief.

## Round 4 (in flight) — the general fix Sean asked for
"Make sure the fix is not just specific to this rule but is universal enough to help us avoid missing or dropping
tests like this." Shared module `ink_attachment.py`: `attachment` (a stem that carries a head counts when the head is
the claimed stroke itself — tile 4's gap) and `line_sides` (a rest block lies on ONE side of its line and never
touches two; side threshold 0.25 sp — real rests show 0.00-0.12 sp on the far side, heads 0.44-0.50). Why r3 passed
tile 4: `BLOCK_MAX_H_SP` is 1.0 sp, not the "half a space" the notes said. Controls are now Sean's 36 answered rest
tiles replayed on their REAL pixels: the reader agrees on 35; the exception is r3 tile 1 (detector box covers 47% of
the block — a short box, named).

## Handed to 2.290 step 5 (merged ink)
40 rest boxes refused `touches_a_head` on the four pages (list: `touches_a_head_for_2290.json` on the lane branch);
by the lane's own look ~12 are real rests.

## Open
35 quarter-rest boxes on Brahms p19 naming no stroke; four pages only; `judged_claims` cannot see stroke-id rest
claims (tool blind spot, 2.295 follow-up).
