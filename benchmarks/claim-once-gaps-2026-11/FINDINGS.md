# Claim-once gaps small test (ROADMAP 2.322), 2026-11-19

STAGED, GATHER (page claims). Read-only. Filed by the manager from the lane agent's report (branch
`lane-2.322-claim-gaps-smalltest`, scripts in this directory on that branch). Frozen sample, slices of the
20261117-night records. "tool" = a tool's count; "look" = the agent's look at crops, small samples (6-10 each).
Sean has seen none of the crops (`out/print/2.322-claim-gaps/`).

## Cause, and what it teaches

The manager's diagnosis (from 2.320) half held. Head boxes do sit on other marks' ink, and the claim is
enforced only as a share of the box -- but it is small and almost always right already. "Beams claim no ink"
and "dynamics claim after heads" are NOT where ink goes unaccounted: a boxed beam already counts as a claim in
`claim_readout`, and words are already in the first tier. Lesson: a stroke the stroke map calls a beam is often
a head fused to a staff-line stub or a piece of a rest; a role name is not a look.

## 1. `claim_readout` on the sample (tool)

| | one owner | no owner | claimed twice | weak |
|---|---|---|---|---|
| Litolff, 8 pages, 15.07M dark px | 89.6% (81.7% of non-staff ink) | 5.0% | 5.3% | 0.1% |
| Brahms, 8 pages, 55.1M dark px | 87.8% (78.3% of non-staff ink) | 5.7% | 6.2% | 0.4% |

`claim_readout ink` CRASHED on Brahms on its own sum check ("weak by kind exceeds the weak line"); the Brahms
row is the agent's recount from the same canvas (the recount reproduces the tool's Litolff row exactly). Open.

## 2. The no-owner ink

Beam-role ink (tool): Litolff 7.4% of no-owner ink (0.37% of all ink), Brahms 1.2%; the beam claim already
holds 76% / 69% of beam-role ink. Of the Litolff unowned beam-role ink, 62% lies under head boxes (look: heads
fused to a staff stub); the rest (0.15% of all ink) is, in 5 of 6 crops, a piece of an unclaimed rest.
Rest of the no-owner ink: Litolff (tool classes) other shape 23%, refused claim 22%, staff-line residue 21%,
small mark 13%, text 10%, note-like blob 9%; look at 10: 4-5 rests, 2 words/numerals, 2 slivers, 1 tangle.
Brahms: staff-line residue 64% (look: scan residue along a staff line, 4 of 6).
Converse gap (tool): 221 written Litolff heads (5%) have half or more of their box ink unowned (look: real
heads whose stroke the claim refused).

## 3. Head boxes on someone else's ink (tool, pixel shares from the ledger canvas)

| group | Litolff boxes (written) | Brahms boxes (written) |
|---|---|---|
| any claimant share above 0 | 715 (260) | 1,681 (340) |
| under the 50% cut | 373 (225) | 491 (310) |
| at or over the cut, still written | 35 | 30 |
| dominant claimant is a later tier | 495 (212) | 715 (326) |

Against Sean's judged answers and claim tiles: of written boxes with 10% or more claimed, 17 are real heads
and 2 are not (a barline box at 40%, Litolff p4; a sharp at 97%, Brahms p19). At 50% or more: 8 real heads
(three plain hollow Litolff heads 100% under a CLEF claim; two eighths under a dynamic; Brahms arc 97%, arc
54%, rest 52%) against 1 non-head. Hand-labelled Brahms p0: 398 of 407 written boxes are real heads.
So a stricter refusal at the cut breaks 8 judged-real heads to fix 1.

## 4. The three candidate fixes (not built)

A, beam strokes claim their ink: reaches 0.15-0.37% of Litolff ink and would take head and rest ink by role.
B, dynamics before heads: 5 written boxes, 2 of them judged-real heads. C, ink not share decides: 65 written
boxes, a net loss on judged marks because the CLAIM is wrong more often than the head.

## Outcome

No lane on A, B or C. Two upstream places a lane could start, causes not found: why a clef or arc claim stands
on a printed head; why rests and text go unclaimed (the largest named part of Litolff's no-owner ink, by look).
Also open: the `claim_readout` crash on Brahms.
