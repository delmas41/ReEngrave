# 2.293 — One number for "ink claimed once" (2026-11-10)

STAGED, a counting tool only (`claim_readout ink`, `conservation --ink`). No reader, verdict or export changed:
exported MusicXML byte-identical to main on Litolff 1,2 and Brahms 0,4. Branch `lane-2.293-one-ink-number` db885b4c6.
Written by the manager from the lane report (the lane's Write was refused).

## Cause and process lesson

Three tools gave three figures because each counted a different thing over a different denominator on a different
gather; none was wrong. 2.283's 68-75% was one-owner pixels over NON-STAFF ink; 2.288's 42.6% / 35.7% was the same
pixels over ALL ink (staff lines are ~40% of a page: 71.0% x (1 - 0.396) = 42.8%); 2.286's 31.8% / 56.0% was the old
readout's unclaimed bucket on the 20261029-night slice, a gather that predates 2.284 and carries no page-ledger links.
The old readout also OR-ed every candidate of every padded cell, so a stroke the ledger had SETTLED between two kinds
counted as contested and a box seen in two cells as a twin.
Lesson: a figure is printed with its denominator, its slice date and its definition of "owner", or it is not quoted.

## The command

    python3 -m tools.omr.staged.claim_readout ink REC --pages 0,14 [--out DIR] [--controls]
    python3 -m tools.omr.staged.conservation --ink          # notes block + ink number, ~3.5 min both plates

11-35 s a page on a saved slice (no gather). Every dark pixel of the page is exactly one of four lines; the tool raises
if they do not sum to 100%: ONE OWNER by kind (sub-lines "on the page ledger" / "claimed by a cell box, not on the
page ledger"; "settled over a rival" shown) · WEAK ONLY · CLAIMED TWICE · NO OWNER (split by a shape guess, labelled
as the tool's guess). The header prints the slice, the record's write time, the tree sha and how many strokes carry
page-ledger links.

## Result (freshest post-2.284 gathers; denominator = all dark pixels of the pages named)

- Brahms p0, p14 (11,405,508 px): one owner 89.0% (79.9% of non-staff ink) — on the page ledger 65.7%, by a cell box
  23.3%; weak only 1.3%; claimed twice 6.0%; no owner 3.8%.
- Litolff p1, p2 (2,845,326 px): one owner 88.4% (80.2% of non-staff) — ledger 66.9%, cell box 21.5%; weak 0.7%;
  twice 5.9%; no owner 5.0%.

The claim plan's to-do list = cell-box ink to move onto the ledger, % of dark pixels:
Brahms notehead 9.0, stem 5.1, beam 3.2, rest 2.4, accidental 1.3, arc 0.6, ledger line 0.5, flag 0.5, dot 0.5;
Litolff stem 7.2, notehead 5.4, rest 3.8, beam 3.2, mark 0.6, dynamic 0.5, arc 0.3. (2.288's rest claims are not in
these slices.)

Claimed twice: clef 1.9-2.3% of the page (a clef detector box AND the register's clef area both stand on the ink),
accidental 0.9, beam 0.8, meter 0.6, notehead 0.3-0.6, dynamic 0.3-0.6. Cause seen, NOT changed: `page_ledger.pool`
sorts candidates by key string, so a glyph key sorts before the register's row and the area no longer decides first.

No owner: staff-line residue 1.3-1.4%; then 0.3-1.0% each of note-like blob, refused claim, small mark, text-like.

## Reconciliation (same pixels, old readout vs new)

Brahms p0 on a current gather: 2.283-style 71.0%, 2.288-style 42.8%, 2.286-style unclaimed 6.5%; NEW one owner 87.8%
(79.5% non-staff). On the stale 10-29 slice the same page reads 26.9% / 22.8% / 59.8% and NEW 37.9%. Litolff p2:
68.9 / 41.7 / 6.9, NEW 87.8 (79.6); stale 46.2 / 34.4 / 36.2, NEW 58.6.

## Against Sean's page-pass labels, Brahms p0 (nine page-wide kinds, one Breitkopf page; a capture measure only)

Of the ink Sean's confirmed labels own, the ledger gives the SAME kind: staff 83.0%, barline 93.0%, bracket 98.5%,
clef 93.2%, key 90.1%, meter 83.3%, arc 94.3%, word 53.3% (38.4% held only by a GUESSED claim), dynamic 37.0% (63%
claimed as `word`). Meter and barline leave 6-7% of their ink unowned. Most staff/clef/key/meter "another kind" is
staff-line pixels under a mark — a convention question (whose are the line pixels a mark sits on?), not a defect.

## Controls (each fails where it must)

Erasing every notehead claim moves exactly the ink it alone held (497,289 px on Brahms p0) to weak/no owner; a planted
second notehead box raises claimed-twice by exactly its ink (492,633 px); a stateless pixel and an off-by-one tally
each trip the sum check. 16 unit tests. Fast tier 10173 passed; check 229.

## CONVENTIONS ASSUMED / NOT CONFIRMED by Sean

A stroke the settle chose between two kinds has one owner. A clef box plus the register's clef area is "claimed
twice" (if two readings of one ink should count once, subtract 2.1-3.5%). Eraser-taken staff-line ink is the staff's.

## Not verified

Only Brahms p0, p14 and Litolff p1, p2 have a post-2.284 gather; a saved slice shows the gather it was cut from; the
no-owner shape classes are the tool's guess.
