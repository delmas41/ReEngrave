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

## Round 4 (2026-11-20) -- the F clef inside the line is read (Sean: "Teach it"); flag still OFF, nothing retired

Branch `lane-2.324-r3` 953e53ae5 (STAGED, GATHER; `read_mid_f` in `clef_pagewide.py`). Agent's report; the
manager checked the branch and function exist, not the counts.

**Cause and process lesson.** The reader inside the line wanted two separate round dots; on these clefs the
dots touch the clef's curve, a stem, a barline or an accidental. The dot test that reads ink at the two dot
places whatever it touches was given only to start-of-staff clefs in round 2. Lesson: one mark needs one
reader -- strengthening the evidence for one position of a mark leaves a weaker second reader for the same
mark elsewhere. Mid-line F clefs are NOT smaller here (body 2.6-2.8 spaces against 2.5-2.7 at the start).
Side finding: on the bar's own lines the old two-dot test reads Litolff's quarter rest (p9 s0 staff 11) as a
bass clef; it was refused only because the staff-wide lines sat off there.

**Rule.** On the clef's own bar's lines: the body starts at the top line and ends at the fourth line; dot ink
in both spaces either side of the fourth line; never a G clef's ink (past the staff above and below), never on
a C clef's thick bar. The box says only where to look. A box refused as not an F clef no longer stops the clef
in force (found on the touched-pages run: a half note beside the barline stopped the new bass clef on p25).

**Every mid-line clef on the frozen sample.** F read plain 14 (9 Litolff as before; Brahms p0 s0 st12 bar 5,
p25 s0 st3, p5 s1 st3 bars 0 and 9, p8 s0 st9 -- no cut tuned for the last). F narrowed 2 (Brahms p4 s1 st3,
one dot at the cut; Litolff p10 s0 st3, lower dot cleared with a thick line; file unchanged, header is bass).
Refused, not clefs, 7 (an "sf", two half notes, a flagged note, a flag, an eighth rest, the quarter rest). C 13
read, unchanged; two Litolff C clefs (p4 s1 st3 bar 3, p11 s0 st2 bar 15) stay kind-unread. G: one real case,
Brahms p14 s1 st9 bar 0 (treble after the viola's alto; round 3 called it a false box, wrong) -- NOT read, its
notes still pitched in alto (a red bar); two Litolff non-clef boxes pass the same ink test, so no two-sided
rule from one case; left as it was.

**Two-plate cuts (measurements on Litolff and Brahms only).** Dot fill 0.7; body top within 0.55 of the top
line (real 0.09-0.38, non-clefs >= 0.72); body end within 0.5 of the fourth line (real -0.14 to -0.04, quarter
rest +0.95). Plain only at dot fill >= 0.8 and body top within 0.45, else narrowed. Three plain reads sit at
exactly 0.80 (Litolff p11 s0 st2, p16 s0 st3, Brahms p8 s0 st9). Near-cut readings narrow (red) rather than
GUESSED blue: blue is decided in `consequences.py`/`export.py`, outside the lane's fence.

**Frozen sample, OFF -> ON** (OFF arm reused from round 3: main not merged since, new code runs only ON).
- Litolff: blue +8 / -67; clefs, keys, meters each +1 / -1; red bars 158 -> 157 (as round 3).
- Brahms: notes +6 / -1, flags +2, ties +2, slurs +1 / -2, articulations +3, ~59 pitches changed, blue -19,
  words +1 / -3; clefs, keys, meters each +4 / -4; red bars 137 -> 137; notes not written 2996 -> 2991.
- The 59 pitches: p25 bars 1-9 (44) tenor -> bass; p8 s0 st9 bars 9-12 (7); p8 s1 st3 (4); p5 s1 st3 bars 0-1
  (4). p25 bars 1-9 against the crop (agent's look): bass, plain, agree with the printed naturals and flats;
  none red.
- Judged right->wrong 0 both plates; `judged score` Litolff 131/13, Brahms 88/3 and `judged_claims` 75/13,
  51/4, identical to OFF. Sean's 2.292 clefs 12 of 12 ON (OFF 11).

**Gate.** Fast tier flag OFF 11,042 passed, the one known far-head failure. 22 new real-pixel controls
(`data_clef_page_only_2_324_r4.npz`).

**Open.** Mid-line G clef (one case); the two between-lines C clefs; cuts unseen on a third publisher; not run
on a whole movement; branch not merged with main since round 3.

## Round 5 (2026-11-20) -- bass and treble kind from ink, no box needed; TOUCHED PAGES ONLY (Sean: "Do minimal testing until we know that we're headed the right direction")

Branch `lane-2.324-r3` b99db38aa. Only Litolff 2, 4, 6, 9, 10, 11 and Brahms 4, 14, 25 were read; no frozen
sample, no replays over it, no fast tier. Agent's report; the manager looked at the sheet
(`out/print/2.324-r5/sheet.png`).

**Step 0 (the manager's worry, measured).** Clefs with no detector box: 7 of 383 start-of-staff on the frozen
sample, all already written right by carry from their other systems; mid-line, none found (Sean's labelled
Brahms p0 has one mid-line clef, boxed -- labels pre-filled from the detector, so not independent; 8 crops of
bars far off their staff's register held 0 missed changes). The silent-wrong-pitch risk the manager put to
Sean is small on our pages. No mid-line shape scan was built.

**Cause and process lesson.** A never must measure the mark, not the processing: round 4's "the F body ends at
the fourth line" measured where staff-line clearing cut the tail (real start-of-staff tails reach the bottom
line); dropped. One F test and one G test now work from ink, the box a witness.

**Touched pages.** All 7 no-box clefs read from ink, right kind, plain. All 371 boxed start-of-staff clefs
re-read as if boxless: no wrong kind (treble 214 of 221, bass 82 of 104 + 7 narrowed, C 46 of 46). Brahms p14
mid-line treble narrows (notes -18, were written in alto). No false clef READ; two Litolff non-clefs pass the
mid-line treble test and narrow: p9 s0 st3 (accidental + half note + arc) -- ~10 correct bass notes in bars
11-14 now unread, a real loss; p10 s1 st4 (arc over a stem), no change. Judged right->wrong 0 on these pages.
Litolff notes -10, blue +9 / -79, red bars 128 -> 126; Brahms notes -18, 44 pitches (p25), red bars 52 -> 50.
Not traced: Litolff p2 s1 st3 bar 0 lost its whole rest.

**Manager's look at the sheet.** Tiles 1 and 10 are plainly not clefs; tile 5 is a treble clef. The claimed
area is not the clef's ink on tiles 2, 3, 6 (runs well below the staff) and 9 (sits on the dots and first
flat, not the body).

**Open.** Claimed area cut to the clef's own ink; mid-line treble narrows on non-clefs; nothing beyond the
touched pages measured.

**Sean's answers to the round-5 sheet (2026-11-20, `answers.json`).** Tiles 2, 3, 6, 7, 8, 9 bass clef; 4 and 5
treble clef; 1 "just a stem"; 10 "2 half notes in a chord". All seven no-box kinds agree. Correction to the
round-5 text above: by the key, tile 1 is Litolff p10 s1 st4 and tile 10 is Litolff p9 s0 st3 (the staff that
lost ~10 correct notes) -- the agent's report had the two tile numbers swapped.

## Round 5b (2026-11-20) -- the clef claims only its own ink; Sean's two non-clefs refused. NINE PAGES ONLY

Branch `lane-2.324-r3` 4bc7b9e7f. Same nine pages, the lane's own tests file (127 pass); no frozen sample, no
fast tier, no `judged score` / `judged_claims` replays. Sheet `out/print/2.324-r5b/sheet.png` (manager looked:
the seven ink-read boxes now sit on the clefs).

**Cause and lesson.** The clef column started 0.3 space left of the leftmost sibling clef, so the system's thin
barline stood at its edge; bridging ink back across cleared staff lines joined barline and clef, and the claim
ran 2.5 spaces past the staff both ways. Now the clef's place starts just right of a barline at its edge and
the area is kept inside a clef's reach. Tile 9 was never wrong (misread from a downscaled sheet) and the
"lost" whole rest on Litolff p2 s1 st3 was a false eighth-rest box in the key slots now claimed by the key
(the comparison paired them wrongly). Lesson: look at the pixels at full size before reporting a fault.

**Sean's ruling "require the spiral" could not do the refusing.** Tile 10 (his "2 half notes in a chord") sits
inside the start-of-staff treble range on every shape measure the lane has (reach above 1.33 / below 1.84;
hole area 0.31, height 1.08, against start-of-staff trebles' minimum 1.14 / 1.44 and 5th percentiles 0.15 /
0.94; tile 5: 2.51 / 1.42 / 0.84 / 2.36). What refuses tiles 1 and 10 is a new never: "never a treble clef
over a notehead" -- 76-84% of each detector head box's ink is joined to the glyph's ink; none of 242
start-of-staff `clefG` boxes holds a notehead box. That rests on the detector's head boxes and has only Sean's
two tiles on its refusing side. Tile 5 (his treble clef) stays NARROWED, not read: Brahms p14 s1 st9 bars 1-5
unread (-18 notes).

**Nine pages, ON vs OFF.** Litolff: rests -1 (the false key-slot rest), blue +9 / -79, clefs/keys/meters each
+1 / -1, red bars 128 -> 126, notes vs round 5 back to 0 lost (p9 s0 st3 bars 11-14 written again). Brahms:
notes -18, 44 pitches (p25), red bars 52 -> 50. Lane report judged right->wrong 0 (300 Litolff, 221 Brahms).

**Open.** A real spiral test (the hole measures do not tell a spiral from two hollow heads); tile 5 read; the
barline cut and reach limit seen only on seven clefs; nothing past nine pages.

## Round 6 -- the treble clef's curl, traced (2026-11-20; nine touched pages only; branch `lane-2.324-r3` bacb099c0; STAGED, flag OFF)

**Cause and process lesson.** Round 5/5b measured the "spiral" as the size of enclosed paper; a hollow
notehead encloses paper too, so Sean's half-note chord (tile 10) passed and the refusal fell to the
detector's notehead boxes. Looking at the full-size pixels first showed what the curl is: the clef's own
upright stroke runs down THROUGH its curl and cuts the curl's paper in two. A hollow head is one ring with
nothing through it. Lesson (third time on this lane): look at the mark's shape before choosing a measure.

**The rule.** A treble clef is one stroke that curls round the second line. Inside a line it is read only
where that curl is seen; otherwise it is refused outright (not narrowed). Never over a notehead, a stem or
blank paper. Beside the rule: enclosed paper on BOTH sides of the clef's own stroke across line 2 (count
>= 2 is the shape; band 0.3 space and area 0.05 sq space are cuts from our two plates), and ink past the
staff above and below (fill >= 0.08 each, unchanged). The C test is read first (C bowls can reach 2).

**Both sides of the boundary (lane's count).** Reading side: start-of-staff trebles on the frozen sample
208 of 221 count >= 2 (the other 13 still read where the detector drew a box); tile 4 >= 2; tile 5 = 3.
Refusing side: bass clefs 0 of 98; tile 10 = 1; tile 1 = 0; of 788 hollow heads on the nine pages 2 reach 2
with ink past the staff -- one is a detector head box sitting on a real treble clef (Litolff p6 s1 st0),
one an "ff" under a note with a ledger line. "Never over a notehead" is kept as a second witness only;
real-pixel controls for tiles 1, 5 and 10 fail with the curl test switched off.

**Sean's three tiles.** Tile 5 (treble): READ by its curl; Brahms p14 s1 st9 bars 1-5 written in treble
(B4+G4, Bb4+G4, E4+G4, A4+F4, D4+F#4, G4+Eb4, D4+F4, F4+Db4 -- lane's check against the print, sheet tile
11). Tile 1 (stem) and tile 10 (chord): refused outright, Litolff p9 s0 st3 bars 11-14 written.
Not a clef matter and not fixed: the fourth chord prints F# and A-natural, file writes Ab4+F4; the chord
right after the clef and two chords in the next bar are unwritten in both arms; one head there is written
blue as G3 (a position error).

**Nine pages OFF -> ON** (shared `lane_report --from gather --cell-map master`). Start-of-staff trebles all
read: Litolff 79/79 (71 by curl, 8 by box), Brahms 46/46 (all curl). Litolff: rests -1, values changed 1,
blue +9 -79, words -1, red bars 128 -> 126, notes not written 1579 -> 1581, judged right->wrong 0 of 300.
Brahms: notes -1, pitches changed 61 (p25 bars 1-9 bass, p14 bars 1-5 treble), blue -2, red bars 52 -> 52,
notes not written 1280 -> 1281, judged right->wrong 0 of 221. The -18 notes of round 5 are gone.

**Other publishers (crops only, the curl test alone; `out/print/2.324-r6/other_publishers.png`).** Simrock
1896 (Dvorak Cello Concerto), Eulenburg 1926 (Bruckner 7), Muzgiz 1947 (Manfred), Jurgenson (Mazeppa),
picked by eye from page views. Treble clefs read 28 of 28 (curl 2-5; Simrock 9, Eulenburg 6, Muzgiz 7,
Jurgenson 6), including ONE small mid-line treble (Simrock p10 staff 7, curl 3). Non-clefs refused 24 of
24, but only ~17 landed on a note or chord (~6 hollow); the rest on beams, rests, a slur, blank staff.
Thinnest margin: a Jurgenson clef's ink above the staff 0.084 against the 0.08 cut -- not retuned.

**Not verified.** Frozen sample, fast tier, `judged score` / `judged_claims` replays since round 4. One
mid-line treble from another publisher; the other-publisher refusing side is thin on hollow chords. The
0.08 fill cut has a clef 0.004 from it. Crops: `out/print/2.324-r6/sheet.png`, key
`out/print/2.324-r6-key.json`.
