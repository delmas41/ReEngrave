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

## Round 2 (2026-11-19): the two fixes hold; the page-wide pass is short on Litolff G clefs

Branch `lane-2.324-clef-pagewide` a010e9a15, `OMR_CLEF_PAGE_ONLY` still OFF, nothing retired. STAGED, GATHER.

**Cause and lesson.** Round 1's causes are fixed: the C clef's thick bar is measured against the thin line
beside it (not a width taken from Litolff), and the F clef's dots are read as ink at their two places either
side of line 4, whatever they touch. Round 2's cause: the lane's own new start-of-staff G test looks for ink
past the staff only inside the detector box's columns and needs the box itself to reach past the staff;
Litolff's G boxes are cut short at the top (ink above the staff 0.0-0.15, below 0.44-0.61), so G clefs are
refused for their BOXES, not their ink. Lesson: a new cut proved on 2+2 pages failed on the other six Litolff
sample pages -- a new reader's test sees the frozen sample before it is trusted; and again, measure the mark's
ink near the box, never the box's extent.

**Both sides of each boundary (real marks).** C: bar at least 2.2x its thin line (line at least 0.1 space):
read, five Breitkopf start-of-staff C clefs at 2.4-3.5x (Brahms p0 staves 11, 12 on Sean's labelled page; p12,
p19, p25 staff 11); refused, Litolff p8 G clef by a barline at 2.0x and the barline of Sean's 2.251 r1 tile 9.
F: smaller dot fill at least 0.7: read, the 4 round-1 Litolff misses at 0.80-1.0; refused, G boxes at 0.48 or
less, C bowls 0.47-0.64. These numbers rest on two plates: they may narrow, not decide, until a third confirms.

**Proof pages (Litolff 2, 9; Brahms 0, 12).** Reach 97 of 98 staves, 0 disagreements; all 15 of Sean's labelled
Brahms p0 clefs read with the right kind, one staff each; p0 staff 12 written tenor again; round 1's ~22 Brahms
pitch changes gone. The one miss (Litolff p2 s1 staff 3) is a bass clef with no detector box; today's locator
calls it tenor (wrong), flag ON writes bass from the other systems (right, by the crop).

**Frozen sample, shared `lane_report --from gather --cell-map master`, OFF -> ON.**
- Litolff: blue +138 / -69; clefs, keys, meters each +1 / -1; red bars 158 -> 157; judged right->wrong 0 of 308.
- Brahms: notes +7, flags +2, slurs +1, articulations +3, pitches ~4, blue -19, words +2 / -2; clefs, keys,
  meters each +1 / -1; red bars 137 -> 139; judged right->wrong 0 of 261. The non-clef Brahms changes and the
  +2 red bars are NOT traced.
- Decided clefs: 184 of 184 Litolff staves and 199 of 199 Brahms staves both arms; the two that change
  (Litolff p2/1/3 tenor -> bass, Brahms p8/1/3 bass -> tenor) are both right by the crop (agent's look).
- Read by the page-wide pass itself: Litolff 163 of 184, Brahms 197 of 199.
- 15 Litolff start-of-staff clefs today's readers read and the page-wide pass does not: G (10) p4 s0 staves 0,
  1, 5, 6, 7; p6 s0 staves 1, 2; p8 s0 staff 0; p10 s0 staff 1; p16 s0 staff 0. F (4) p4 s0 staff 3 (no dots),
  p6 s0 staff 3 and p8 s0 staff 8 (dots name no line), p6 s1 staff 10 (box top off the top line). C (1) p8 s0
  staff 7, alto refused as G-shaped. Those staves take their clef from the other systems, so their notes go
  blue: that is the +138. Brahms loses nothing.
- Not losses: 6 bass clefs with no detector box in either arm (Litolff p2/1/3, p4/1/6, p4/1/10, p11/0/8,
  p11/1/5; Brahms p14/0/12) and Litolff p6/1/0 (G, no box).
- Crops: `out/print/2.324-clef-page-only/frozen-misses/` (`sheet.png`, all 22).

**Clef ink, proof pages, OFF -> ON (`claim_readout ink`).** Litolff one owner 89.8% -> 92.1%, claimed twice
5.3% -> 2.9%, clef claimed twice 2.1-2.5% -> 0. Brahms one owner 86.7% -> 88.6%, twice 6.3% -> 4.4%, clef twice
1.9-2.1% -> 0. Not run on the frozen sample.

**Not done.** Fast tier and `check` not run this round; three tests in `test_staged_clef_slot_claim_2_208.py`
fail with the flag ON; Sean's 2.251 clef tiles not replayed; the G fix (ink above and below the staff beside
the box) and the 4 F + 1 C misses not built. Round 3 takes these.

## Round 3 (2026-11-20) -- reach closed on the start of the staff; flag still OFF, nothing retired

Branch `lane-2.324-r3` 7350ba122 (STAGED, GATHER; `clef_pagewide.py`, `gather.py`). Agent's report, checked
against the tree for the branch and files only; the counts are the lane's own from the shared `lane_report`.

**Cause and process lesson.** Round 2 blamed the G boxes being cut short; that was wrong, the boxes are right.
The page-wide pass measured each clef against ONE set of staff lines for the whole staff; on Litolff's first
systems those sit 0.25-1.1 spaces off the print at the start of the staff, so "ink above the staff" fell on
blank paper. The start-of-staff reads now take the first cell's own traced lines. Lesson: we looked at the
measurements before the pixels, and a new reader broke "measure against the staff locally" -- a new reader
takes the lines its own cell already traced. F p6/1/10 and p8/0/8: the dot is looked for anywhere in the
middle half of its own space. C p8/0/7: ink at or left of a line running past the staff further than any clef
can (the system barline) is not the clef's.

**Two new nevers for the F reading** (dot ink alone cannot tell F from G or a C clef's bowls): refused where
the box columns have ink past the staff above AND below (real F <= 0.06, real G >= 0.13), or a C clef's thick
bar stands in the box (0 of 98 real F, 46 of 46 C). Both cuts are set on our two plates.

**Frozen sample, OFF -> ON.**
- Litolff: blue +8 / -67 (round 2: +138 / -69); clefs, keys, meters each +1 / -1; red bars 158 -> 157; judged
  right->wrong 0 of 308.
- Brahms: notes +2 / -49, rests +8 / -9, accidentals -24, flags -46, articulations +1 / -43, blue +6 / -24,
  words +23 / -6, pitches changed 4, red bars 137 -> 142, notes not written +48; judged right->wrong 0 of 261.
- 189 of the 234 changed Brahms places are p25 s0 staff 3: tenor header, a printed bass clef at the end of bar
  0 (crop `out/print/2.324-r3/question_brahms_p25_s0_st3.png`; the manager looked: plainly a bass clef). Flag
  OFF wrote bars 1-9 plain with tenor pitches (a fifth off); ON the tenor clef stops at the bass-clef box
  (narrowed, not read) and those notes are unread (red).
- Sean's 12 clef/key answers (2.292): OFF 11 of 12 clefs right, ON 12 of 12 (Litolff p2/1/3 wrong -> right).
- Reach: Litolff 163 -> 178 of 184; Brahms 198 of 199. The 7 not read have no detector box and are carried
  from their other systems (crops `out/print/2.324-r3/not_read_sheet.png`).
- Round 2's untraced Brahms changes are traced (p8/1/3 clef corrected; p5/1/3 and p14/1/9 bar 0: OFF placed
  the key window after a mid-bar detector clef box and the key claim swallowed noteheads; ON writes the bars,
  both red). Round 2's ON arm also wrote p5's notes after the bass clef as tenor and the clef's dots as a C4;
  fixed (an unread clef-sized box keeps its narrowing claim).

**Gate.** Fast tier flag OFF: 11,019 passed, the one known far-head failure. `check` 216 open, not compared
with main. 76 real-pixel controls in `test_staged_clef_page_only_2_324.py`.

**Open.** A mid-staff F clef is only narrowed, never read (Brahms p25/0/3; p8/0/9 dots fused with an
accidental is missed outright). Sean's 2.251 clef tiles not replayed by place (their files hold no places).
Not run on a whole movement. Retirement list (nothing removed): `gather_clef` rows on cell 0,
`gather_clef_locator`, the clef sections of `gather_claimed_register`, the OFF-only `KO.clef_of_box` edge;
`gather_clef_seed` and `gather_clef_slot_claim` stay.
