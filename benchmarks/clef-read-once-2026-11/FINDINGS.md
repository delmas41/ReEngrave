# Is the clef read once on the page? (ROADMAP 2.324), 2026-11-19

STAGED, GATHER and ADJUDICATE. Cause-finding, read-only; filed by the manager from the lane agent's report.
Code's count on the 20261117-night slices of Litolff p9 and Brahms p12 unless marked "look". No code changed;
the agent's scripts were not committed.

## Cause, and what it teaches

Two different things. (1) Most "clef claimed twice" ink is BOOKKEEPING: each detector clef box reaches the
stroke-owner settle as itself and again as its own claim-register row (`gather_claimed_register`,
`owner_glyph` = that box), and nothing matches the row to the box. One read, counted as two owners. The
2.322 agent's guess (page-wide header read plus detector box) was wrong. (2) Separately, the clef is NOT
read once at the page level: a header clef's meaning is gathered in several places and combined later.
Lesson: an ink count by kind cannot tell one read filed twice from two reads; keep the claimant ids.

## Where a clef is read or claimed today (`tools/omr/staged/`)

- `gather.py::gather_clef` -- detector `clef*` boxes on cell 0; rows, no claim.
- `gather.py::gather_clef_locator` -- CV C-clef locator on two crops (header window and cell 0); rows, no
  claim. Shared LEGACY reader `tools/omr/clef_locator.py` (also `clef_geometry.py`, `staff_header`).
- `gather.py::gather_clef_seed` -- dossier / fact-sheet clef; reads no ink.
- `gather.py::gather_claimed_register` -- PER CELL: a clef claim from each locator row, and one from every
  clef-sized detector box in any cell.
- `gather.py::gather_clef_slot_claim` -- claims the slot on a staff with no clef claim.
- `gather.py::gather_clef_pagewide` (`clef_pagewide.py`) -- the only page-wide reader: C by shape, F by box
  plus dots, G by box; files mid-staff changes; skips header ink the register already holds.
- ADJUDICATE `adjudicators/clef.py` (`Q.CLEF`) -- decides the staff's clef from glyph, position, locator,
  seed and the key-signature clef fit. Not page-wide.
- Consumers: pitch (`restate_pitch`) and export take `Q.CLEF` plus the page-wide changes
  (`OMR_CLEF_CARRY`); key signature reads `KEYSIG_CLEF_FIT`.

## The two claims on one clef

Clef-only ink "twin" vs "one": Litolff p9 43,855 px vs 4,936; Brahms p12 136,866 vs 0. By stroke view: one
box plus its own register row 43 (Litolff) and 77 (Brahms); locator row plus detector row 6 and 1; two boxes
alone 0. By overlapping claim areas, Litolff p9 25 marks / Brahms p12 29: single detector claim 21 / 20;
locator plus detector 1 / 1; locator plus two boxes on one staff 1 / 1; a clef covered by boxes from TWO
staves 1 / 6, three staves 0 / 1; page-wide only 1 / 0. Look (5 crops per page) agrees: the cross-staff
cases are the neighbour staff's clef showing in this staff's padded cell, boxed again and claimed on the
wrong staff; a C clef's box is sometimes split into an upper and lower half.

Mid-staff clefs: read by the page-wide pass; the register also files a detector claim on the same box.

## Not checked

Whether two readings of a header clef ever DISAGREE (no overlapping readings on these two pages). Whether the
double claim changes anything written: by code reading "merged" is treated as "decided" everywhere it is
consulted (`ink_consult`, `claim_final`, `claim_order`, `stroke_owner`), so probably counting only -- not
run. The cross-staff claims could change what is written. Two pages only.

## What the change would touch (not built)

Small: the settle counts a register row once when its `owner_glyph` is a box it already counts; no clef claim
from a box that is not that staff's own clef. Large (Sean's rule): one page-level clef read -- extend
`clef_pagewide` to the header window, retire the register's detector and locator clef claims and the per-cell
reads. Tests pinning those paths, by file: page-wide 6, clef slot 2, register 12, locator 2.

## Round 1 (2026-11-19): the page-wide pass reads fewer start-of-staff clefs than today -- STOPPED, not landed

Branch `lane-2.324-clef-pagewide` 1b072fdb0, flag `OMR_CLEF_PAGE_ONLY` built OFF. Filed by the manager from
the lane agent's report. Proof pages only (Litolff 2, 9; Brahms 0, 12), flag OFF vs ON gathered on the same tree.

**Cause:** the page-wide reader was built for mid-staff changes and never measured on start-of-staff clefs;
its cut-offs were measured on one publisher. C clef: the thick bar must be 0.45 staff spaces wide, set from
Litolff (0.7-0.8); Brahms p0's alto and tenor clefs measure 0.434 and 0.438 and are refused. F clef: on
Litolff the two dots touch the key flats and the dot test fails. **Lesson:** measure reach before moving any
consumer (it is what stopped the lane); a number tuned on one plate may only narrow (CLAUDE.md §4).

Built (flag ON only): the page-wide pass reads the start-of-staff clef, takes a box only when its middle sits
on this staff's own lines measured at the box (the neighbour-staff fix), reads a start-of-staff G from its box
plus its own ink above and below the staff, files the one clef claim; the cell-0 detector read, the two-crop
locator and the register's clef claims stand down; `Q.CLEF`, the key object and identity read the page-wide
rows. Seed row and clef-slot claim stay. Nothing retired.

**Reach (code's count):** page-wide read agrees with today's decided clef on 51 of 56 Litolff staves and 39 of
42 Brahms; 0 disagreements; misses = 4 Litolff bass clefs (dots not found), 3 Brahms C clefs (bar just too
thin), and 1 Litolff staff (p2 s1 st3) where TODAY's locator reads a false tenor and the page-wide read is
right (bass; agent's look at the crop).

**A clef is lost with the flag ON:** Brahms p0 staff 12, a printed tenor C clef (labelled by Sean on the
hand-labelled page), is written bass; about 22 Brahms pitch changes probably follow (not traced). The other 7
misses are saved only by the carry from other systems. Judged right->wrong 0 on both plates, but no judged
tile sits on that clef -- only the labelled page catches it.

Not done: frozen sample, `claim_readout` clef ink, the new test file and controls, the fast tier, step 3.
3 tests in `test_staged_clef_slot_claim_2_208.py` fail with the flag ON (they pin the path it replaces).
Crops: `out/print/2.324-clef-page-only/reach-misses/`.
