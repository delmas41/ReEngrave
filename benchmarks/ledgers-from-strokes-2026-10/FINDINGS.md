# 2.217 -- ledger rungs from the stroke map (step 7 of the shared ink map)

Flag `OMR_LEDGERS_FROM_STROKES`, default OFF. Code: `tools/omr/annotate/ledger_strokes.py` (pure), `staged/adjudicators/ledger_read.py`
(adapter), read by `ownership._note_first_ledger_owner` / `glyph_owner` and `position.adjudicate_notehead_position`. STAGED ADJUDICATE.

## 1. Cause and process lesson

**Cause.** The four ledger readings do not answer one question. `glyph_ladder` and `ledger_rung_ink` ask "is there ink where the
staff spacing says rung n should be" (a grid extended from the staff, which page-facts section 3 forbids: ledgers are hand-drawn);
`far_head_owner_ledger` asks "what is printed beside this head" (an ink walk); `ledger_owner_density` asks "how dark is one window".
Re-measured on the frozen-sample slices of the 20261022-night record (`disagree.py`, per head and candidate staff, the three presence
readings only): they disagree on **42.8% (Litolff, 1,485 of 3,466) / 37.3% (Brahms, 1,586 of 4,247)** -- the plan's 34% / 38% on a
different count of readings. The dominant pattern (Litolff 1,027; Brahms 625+651) is the grid readers saying "no ledger" where the walk
finds one. `ledger_not_read` on those pages: far_head_owner_ledger 2,424 / 2,725, far_head_ledger_position 1,094 / 1,276 (the plan's
2,211 / 4,713 are other populations).

**Second cause, found building the fix: the stroke map cannot see most ledgers.** The one-reading design assumes a ledger is a horizontal
stroke. On the page it usually is not: a rung through a head has short stubs (under the 1.0 sp horizontal floor) that fuse into the
head's blob, and Litolff merges the rest. On the two fail-fast pages, of the heads the old reader placed and the new one could not (154 /
143): the only stroke at the head is its own blob 68 / 76 (rung stubs inside it), no stroke at all 37 / 37, a horizontal stroke 37 / 8,
vertical 7 / 20 (`why_no_rung.py`). So the new reader decides 22 of 311 (Litolff p16) and 22 of 185 (Brahms p0) positions where the old
decides 167 / 164.

**Process lesson (rule 7, plan section 5 step 1).** Step 1's coverage guard named "every existing ledger rung must be covered >= 99%"
and nobody ran it for rungs: the map was built from stem and beam finders and checked against those. A consumer step must run its
coverage guard against its OWN old reader before it is built, not after. Fixing the disagreement needs the rung ink the stroke map
dropped (stubs through a head, rungs merged into a blob), i.e. a map change (a ledger-stub pass at the head, beside step 1's horizontal
opening, floor 0.3 sp when a head blob stands within it), which is a step of its own.

## 2. What was built, and what it does

`read_head` reads only ink: thin horizontal strokes wholly outside the staff, spanning the head's x, owned by nobody else
(`Q.STROKE_OWNER`; a contested stroke is no witness and is named), counted outward by the ink and placed by the staff at their own x
(`end_steps_from_top`), never by an extended spacing; head on a rung / in the space beyond the nearest staff-side rung; first space
outside the staff needs none; a gap wider than a missing rung could hide, or a head more than a space past the last rung, abstains with
its numbers. With the flag ON `glyph_owner` reads no `glyph_ladder`, `ledger_rung_ink`, `ledger_owner_density`; the old GATHER rows stay
on the record as the control. 2-witness owner rule untouched (2.216).

## 3. The three measures (fail-fast pages only: Litolff p16, Brahms p0 -- NOT the frozen sample)

`lane_report --from gather`, `/out/lane-report/2.217-ff/report.txt` (one-page control sample; OFF==record not checked in re-gather mode).

1. File changes: Litolff p16 notes +1, ties -6, pitches ~45, blue marks +4 -4, words -1, notes not written 332 -> 331. Brahms p0 ties
   -24, slurs +28 -6, pitches ~8, blue -1. Verdicts: Litolff `notehead_position` decided 167 -> 22 (154 decided -> abstained, 9
   abstained -> decided, 6 changed value), `glyph_owner` value unchanged on every head, its REASON moves (`ledger_note_first` ->
   `stem_toward_staff` 153, `distance` 37, `range_veto` 22). Brahms: position decided 164 -> 22 (143 lost, 7 changed value).
2. Judged right -> wrong: **0** on both pages (117 + 194 judged tiles); right -> abstained/gone 0; wrong -> right 0. (The 154 / 143
   decided -> abstained are not among his judged answers.)
3. Tiles: `out/print/2.217/tiles/sheet.png` (12: 9 heads where old and new positions differ, 3 where they agree), key in
   `out/print/2.217/key.json`. Question: where does the boxed note sit (e.g. 2nd ledger line above). Awaiting Sean; his answers say which
   of the old walk and the new reading is right on the 13 disagreeing heads.

Not run: the frozen-sample lane_report (about 2 h for 16 pages). With the reader seeing 13% of the old reader's placements the result is
known to be a loss of positions; it was not worth the machine time before the map covers rungs.

## 4. Status

Flag stays OFF, not a landing candidate. Next, if Sean wants it: a rung-stub pass in `stroke_map` (map change), re-run the coverage guard
(target >= 99% of the old reader's placed heads), then the frozen sample.
