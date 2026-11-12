# 2.302 — the key object counts every flat (STAGED, GATHER)

Written by the manager from the lane's report. Branch
`lane-2.302-key-object-counts-flats` ea7fa6335, flag
`OMR_KEY_OBJECT_COUNTS_FLATS` default OFF. NOT LANDED: waiting on Sean's 10
tiles (`out/print-from-worktrees/2.302-r1/sheet.png`).

## Cause and process lesson

The stems were already on the page: on 17 of Sean's 19 judged three-flat
Litolff staff starts, three thin vertical strokes stand at their flat-order
staff steps. The 2.256b path (`key_object.flat_stems`) lost them three ways:
a 2.0 sp stem floor drops broken stems (1.4-1.9 sp); the chain ends at the
first foreign stroke; it needs a clef the detector's box can name. It also
kept the clef's edge or the first note as an extra piece, which 2.299 refuses.

**Lesson: a count and a position are separate measures.** Fixing the count
brings 9 -> 14 of 19 to three flats, but 2.299 still refuses several on its
natural-shape veto or its step position. The manager's "~190 notes" estimate
was again a count from one stage, not measured through the reader.

Correction to the brief: Sean's 23 judged starts are 19 three-flat and 4 with
no accidentals (the fill was right on all 23).

## What changed

`flat_stems_v2`: the longest fixed-order stem chain, skipping foreign strokes,
floor 1.4 sp. `_counts_flats` applies it only where it changes the answer
(counts more, drops a non-flat extra piece, splits one blob counted twice); a
chain shorter than 2 never makes a key; with no clef named it counts only
where one clef gives the strictly longest chain. `gather.py` keeps
`extra_pieces` on the record, never counted. Never from the system's count or
the INFER fill.

## Measured

- Replay (saved rows, OFF reproduces 184/184 Litolff, 42/42 Brahms staves):
  2.299's reader READs 53 -> 62 Litolff staves (by the detector's clef box —
  not the same measure as 2.299's ADJUDICATE "4"); Brahms 24 -> 24; no READ
  staff became an abstention; 3 of the 9 newly READ are judged and match Sean.
- Real gather OFF vs ON (Litolff p2, 4, 16; Brahms p4 — a development
  sample, not the frozen one): Litolff blue marks -12, nothing else in the
  file changes, no pitch change; Brahms unchanged.
- judged right->wrong 0; judged_claims no new contradiction; check 228.
- Fast tier OFF 10,448 passed. ON: one failure (the 2.256b test pinned to the
  old count), fixed; the whole ON tier was NOT re-run after that fix.

## Not confirmed / next cause

- Still abstaining: 3 clef-unnamed starts; 3 where the shape reader calls a
  crushed flat a natural; 4 that miss 2.299's step position. That veto and
  tolerance are the next cause; not loosened here.
- No real natural or sharp key zone exists in the saved pages.
- Blue-for-key notes total not re-measured (only the -12 delta).
