# 2.295 — Judged claims: every claim tile Sean answers is replayed (2026-11-10)

STAGED, a checking tool only (`tools/omr/staged/judged_claims.py`, registry `data/judged-claims/registry.json`).
No reader, verdict or export changed: exported MusicXML byte-identical to main on Litolff 1,2 and Brahms 0,4.
Branch `lane-2.295-judged-claims` c029a23ac. Written by the manager from the lane report (the lane's Write was refused).

## Cause and process lesson

Sean's answers about CLAIMS ("what is the ink in this box?") were never replayed because each lane wrote its own
answers-file shape, and `judged` reads only written notes through the exported file — a claim tile's evidence is the
page ledger, not the file. So a later round could re-make a mistake he had already named (2.288 r3 claimed a notehead
as a whole rest; a synthetic unit control passed and the agent's own look said "all nine are rests").
Lesson: an answers file is only half recorded until a tool can replay it. A new answers file gets one line in
`judged_claims.SOURCES` in the same commit. (Sean 2026-11-10: "Make sure the fix is not just specific to this rule but
is universal enough to help us avoid missing or dropping tests like this.")

## What it holds

164 answered claim tiles from 14 answers files (2.276 r2, 2.282, 2.284 r1, 2.284b r1-r2, 2.284 r5, 2.285 r1-r2,
2.288 r1-r3, 2.289, 2.290, 2.292). 157 map to a kind from a closed vocabulary; 7 are `unmapped` (kept, never guessed);
12 have no page box (2.292 asks about a staff start). Not included: value/rhythm tiles (those are `judged`'s) and 2.291
(red bars).

## Commands

    python3 -m tools.omr.staged.judged_claims --build | --check        # registry from the answers files
    python3 -m tools.omr.staged.judged_claims REC [--unclaimed] [--crops DIR] [--controls] [--against BASE.json]

About 46 s (Brahms) / 30 s (Litolff) on a saved slice. Exit 1 on any contradiction; with `--against` only on
contradictions the baseline does not already have — lanes gate that way, because main already contradicts.

Per tile, R = share of the box's ink owned by a READ claim of the kind Sean named; W = share owned only by other kinds'
READ claims. AGREES R >= 0.5; CONTRADICTS R < 0.5 and W > R and W >= 0.3; else UNCLAIMED. CANNOT TELL (never agreement):
page not in the slice, box on < 8 ink px, no box, unmapped kind, ink owned by a kind the readout cannot name.
Conventions assumed (the tool's, not Sean's): the 0.5 / 0.3 thresholds; a note's stem, beam and flag count as the note.

## First reading on main (slices `claim-readout-slices-{brahms,litolff}.main`)

Brahms p0, p14: 59 tiles — agrees 25, contradicts 1, unclaimed 2, cannot tell 31 (page not in slice).
Litolff p1, p2: 105 tiles — agrees 29, contradicts 5, unclaimed 0, cannot tell 71 (64 page not in slice).

Contradictions on main today (listed, not fixed):
- Brahms p14: a real WHOLE REST (2.288 r3 tile 2) is owned 100% by a `beam` claim.
- Litolff p2: five DYNAMIC tiles are claimed as `word` — 2.284b r1 #2 (sf), #7 (f); 2.284b r2 #2 (sf), #5 (f);
  2.276 r2 #10 (p). (The open 2.293 item, now with five of his named tiles on it.)
Unclaimed: 2.285 r1 #11 (the "(C)" crook label); 2.288 r2 #7 (a quarter note whose head has no READ claim).
Also found: `claim_readout.FINE_OF_FAMILY` does not name `accidental_ink` (2.285), so the readout files those claims
under `other`; mapped in memory here, `claim_readout.py` not touched.

## Controls

(a) one rest tile relabelled in memory flips agrees -> contradicts and no other tile moves (both plates);
(b) every box shifted 3 spaces: agrees 25 -> 3 (Brahms), 29 -> 3 (Litolff), cannot tell rises;
(c) the 2.288 r3 false claim was caught only in a DOCTORED form (a whole-rest claim planted on the real pixels of
Sean's eighth note): no saved r3 gather of Brahms p14 exists. The real catch needs this tool run from the r3/r4 tree
on its own gather; tile r3 #4 is in the registry for it.
23 fast tests (his real phrases as fixtures) + 1 slow real-slice test. Fast tier 10196 passed; check 229.

## Not verified

`conservation --ink` end to end (its full run stalled; the new line was checked by calling its function); the real r3
catch; every page outside the two `.main` slices reads "cannot tell" (most of his tiles: a re-gather of the frozen
sample is what turns them into verdicts).
(Both closed by 2.295b below.)

---

# 2.295b — the tools see claims filed as page-stroke ids (2026-11-11, branch `lane-2.295b-tools-see-stroke-claims`)

STAGED, checking tools only: `claim_readout.py` and `judged_claims.py`. No reader, adjudicator, verdict or export changed; exported
MusicXML byte-identical to main on the conservation default pages (Litolff 1,2; Brahms 0,4; `cmp` of both files).

## Cause and process lesson
2.295 was landed on a PLANTED control (a whole-rest claim drawn on the real pixels of Sean's eighth note) because no gather of the
failing tree existed. The planted claim lived where the tool could see it (the cell `fam` canvas); the real claim lives where it could not
(a `Q.CLAIMED_AREA` row naming page strokes, `page_boxes`). A control that writes into the tool's own input proves the rule, not the
reader: it cannot fail on what the reader never sees. Lesson (rule 7, now with a case): a tool that reads a record gets one control
built from a row of the record that the tool should NOT miss, cut from a real gather of the tree that made the mistake; the planted control stays
only as the rule's control. Here the real catch was a 5-minute one-page gather of `f4a59088c`.

## What changed
- ONE reader of page-stroke claims: `claim_readout.page_stroke_claims(rows)` (any `claimed_area` row whose detail names `page_strokes`: every
  READ rest since 2.288, dynamics / repeat dots under `OMR_PAGE_CLAIM_BOXES`, arcs `system_arc`, tremolos `page_tremolo`, own-ink accidentals
  `page_accidental_ink`). Both tools call it; nothing else does. Pixels: EXACT where the page stroke map can be re-cut (`page_strokes.map_page`
  on the master cells with the keep-whole / touch boxes the gather saved on each cell, accepted only when every stroke box equals the record's
  `Q.PAGE_STROKE` row); else a bbox approximation (smallest stroke box wins a pixel). Every page printed here resolved EXACTLY.
  The ledger's own one-pixel dilation (`page_ledger.PageLabels`) can credit a stroke's edge pixel to it: small px counts in the arc pairs may be that.
- `claim_readout ink`: a READ page-stroke claim is "on the page ledger" by its kind; on a pixel where it and a READ cell/register owner of a DIFFERENT kind
  both stand, the pixel is CLAIMED TWICE with its own sub-line "page-stroke claim the cell settle did not consult", by pair ("page rest / cell beam", px).
  Same kind on both = one owner. The four lines still sum to 100% (verify_tally raises otherwise, tested). `accidental_ink` is mapped to `accidental`.
  A page-stroke claim never takes the staff ink the eraser took.
- `judged_claims`: owners come from three named sources (cell settle / register area / page-stroke claim). CHANGED RULE: AGREES now needs R >= 0.5
  AND Wa < 0.3; a tile where a READ claim of another kind stands on >= 30% of the ink CONTRADICTS (flag "claimed twice") even where his kind owns it.
  Ink the cell settle left OPEN between kinds (`contested`) is not a standing wrong claim; those agrees are counted apart ("of which N with >= 30% left open").
  Exit code 1 still means a contradiction (use `--against` to gate on new ones).

## The real catch (Brahms p14, gather of `f4a59088c`, `OMR_PAGE_CLAIM_RESTS=1`, one page, ~5 min)
| tile | 2.295 tool (origin/main tools) | 2.295b tool |
|---|---|---|
| 2.288 r3 #4, Sean "eighth note" | AGREES (notehead 100%, the rest claim invisible) | CONTRADICTS, claimed twice: rest 100% [page-stroke claim] + notehead 100% [cell settle] |
| 2.288 r3 #2, Sean "whole rest" | CONTRADICTS "beam 100%" | CONTRADICTS, claimed twice: rest 99% [page-stroke claim] + beam 100% [cell settle] |
On main today (round 4 landed; fresh one-page gather): #4 does NOT contradict (agrees); #2 reads claimed twice rest + beam. Litolff p8 (fresh main
gather): the sharp (2.285 r1 #3) agrees as an accidental (92.7%), no rest claim on it.

## Before / after on the saved slices and the fresh gathers (tiles: agrees / contradicts / unclaimed / cannot tell)
| input | 2.295 tool | 2.295b tool |
|---|---|---|
| Brahms `.main` slice (p0, p14; gather before 2.288: NO rest claims in it) | 25 / 1 / 2 / 31 | 25 (5 of them >=30% open) / 1 / 2 / 31 |
| Litolff `.main` slice (p1, p2) | 29 / 5 / 0 / 71 | 28 (2 open) / 6 / 0 / 71 |
| Brahms p14, fresh main gather | 22 / 1 / 2 / 34 | 22 (5 open) / 1 (twice) / 2 / 34 |
| Brahms p14, r3 gather | 22 / 1 / 2 / 34 | 21 (5 open) / 2 (both twice) / 2 / 34 |
Yesterday's six contradictions (Brahms r3 #2; Litolff five dynamics): the five Litolff dynamics are REAL, not blindness: their owners are cell-settle `word`
claims (41-91%) and no `page_boxes` dynamic claim exists in any record (the flag `OMR_PAGE_CLAIM_BOXES` is OFF), so the tool could not have missed one. Brahms #2
is real too, but it was described wrongly: on the old `.main` slice it is a beam only (no rest claim existed then); on today's main it is rest (page) + beam (cell).
One NEW contradiction on the Litolff `.main` slice: 2.276 r2 #4 (tremolo slash) — tremolo 66% [cell 63%, page-stroke 65%], stem 37% and accidental 21% [cell settle]: a slash
crosses its stem; whether that crossing should be the mark's (like staff/ledger lines) is for the manager: needs a crop.
Open agrees (cell settle could not choose between kinds on >=30% of the ink, old rule agreed): Brahms 2.288 r2 #1 (natural sign vs rest), 2.282 #2/#3/#8/#9
(accidental vs notehead), Litolff 2.284b r1 #12, r2 #1. These are 7 of Sean's tiles that "agree" only because his kind was one of two the settle left open.

## The gap ROADMAP 2.297 must close, by pair (px of the page; "page X / cell Y" = a READ page-stroke claim of X on ink the cell settle holds as Y)
Brahms p14 main (7,052,110 dark px): 11,375 px = 0.16% of the ink: arc/beam 2,268, rest/accidental 2,042, rest/notehead 1,954, rest/beam 1,556, rest/arc 1,016,
arc/barline 785, arc/notehead 496, rest/dynamic 398, arc/accidental 295, rest/arc+accidental 230, five smaller pairs 335 px; round 3 (r3 gather) 13,021 px (rest/notehead 3,571).
Brahms `.main` slice 8,905 px (0.08%, tremolo/notehead 2,241, arc/beam 2,269); Litolff `.main` 1,219 px (0.04%, arc/notehead 619); Litolff p8 main 364 px
(rest/accidental 106). Small in ink, and it is where a rest or arc sits on a head or beam.

## Not verified
Exact-vs-bbox only matters where the page map cannot be re-cut: every page here re-cut exactly, the bbox path is covered by unit tests only. Dynamics as page-stroke
claims (flag OFF) were never exercised on a real record. The 0.3 threshold of "stands" is the tool's, not Sean's.
