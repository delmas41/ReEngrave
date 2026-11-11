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
