# 2.294 — Micro test: one owner, or shared ink where two marks cross? (2026-11-10)

STAGED, sizing only; stopped at step 1, nothing built. Branch `lane-2.294-shared-crossing-test` 2a778e7fd. Written by the manager from the lane report (the lane's own Write was refused by a hook). Scripts are on the lane branch named below.

## Answer
Sharing ink at crossings would very probably give almost the same file as single ownership. Marks that cross are
already SEPARATE strokes on the page ledger, so single ownership is not punching holes in symbols (none seen in ~32
looks). What is lost at contacts is a rest or small mark FUSED to a head, and unclaimed ink beside a contact — neither
recoverable by sharing.

## Sizing (main e2cfc1bd6, Brahms p0+p14, Litolff p1+p2; site = ≥3 px where ink of kind A is within 1 px of kind B)
Brahms 895 sites: 722 nothing lost, 85 one mark refused, 88 unclaimed ink at the contact. Litolff 532: 395 / 29 / 106
(+2 weak). Ink within 3 px of a crossing: 1.3-1.5% of all ink (Brahms), 2.8% (Litolff). Most refusals are correct
(tremolo slashes boxed as heads, head boxes where a slur meets a barline).

## Ruling
Sean, 2026-11-10: "We can drop the shares ink idea." One owner per piece of ink stands; where a mark crosses a staff
line the crossing ink is the mark's (page-facts §3). Fused marks → 2.290 plan step 5. Tiles not sent.
