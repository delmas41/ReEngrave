# Why printed notes are written with no value — ROADMAP 2.317

STAGED. Small tests only, no build. Records: the 20261117-night whole movements (main d98c042c3).
Filed by the manager from four read-only agents' reports; every "look" below is an AGENT'S look
unless it says Sean. Scratch: `out/print/2.317-*` (untracked).

## Cause, and what it teaches

About 1,070 note boxes carry no value (314 Litolff, 755 Brahms; about 860 are real printed notes).
About two thirds stop where a stem or beam is joined to its head. The largest group -- "one possible
beam stroke" / "beam certain, a further level possible" (347 notes) -- is NOT doubtful ink: the stroke
is a plain printed beam (24 of 24 random crops, and the manager's own look at 12), usually the second
beam of a sixteenth group. It is held as "possible" because our TWO beam readings disagree (the
bar-box reader finds a stroke the stroke-map tip reader does not, or the reverse), or because the
stroke covers the head's column with no stem joined to it.

Lessons: (1) "possible" in a reason word described OUR disagreement, and the manager read it as a
doubt about the ink -- two hypotheses in a row (box off-centre; slur ink at the tip) were refuted by
a count before a lane was opened. (2) Two readers of one mark, kept side by side, turn a readable
beam into an abstention. (3) Our tools count claims, not uses: a reader that uses ink without
claiming it is invisible to every read-out.

## What was measured

| test | result |
|---|---|
| Sean, 60 random no-value notes (`out/print/2.317-no-value-tiles`) | "about half of them the box feels just slightly off where it should be and all of them should be easily read. Prob 3 or 4 are not notes but accidentals or part of a beam." |
| off-centre box loses the stem | REFUTED: about 13 of 1,069 |
| naive "stroke ink meets the stem" beam test | fails its control: settles ~190 of ~400, disturbs about a third of decided notes |
| doubtful stroke is ink an arc has claimed (`out/print/2.317-claimed-ink`) | REFUTED: Litolff 6 of 79 mostly claimed, 1 partly, 69 not; Brahms 10 of 268 mostly, 19 partly, 239 not. A rule "beams may not count arc-claimed ink" settles at most ~5%, and loses 1 real beam in 200 decided Litolff notes |
| whole-stroke straightness (Sean 2026-11-18, restating 2026-10-09 "A beam never has an arc") | does not separate here: the doubtful strokes are beams, so they are straight; long Brahms beams (7-31 sp) bow up to 0.96 sp on the scan, and the few arc pieces sit inside the beams' range. Thickness separates better (arc pieces <= 1.87 x a staff line, doubtful strokes >= 1.94) |
| why held | Litolff "one possible beam stroke" 62: 47 bar-box reader yes / stroke-map tip reader no, 11 the reverse. Brahms "further level" 176: 36 the same disagreement, 62 stroke-map candidates. Litolff: several beams fused into a thickened staff line |

Not measured: hairpins directly (5 claimed areas on Litolff). The per-cause split of the other
two thirds is in `out/print/2.317-no-value/*.cause.json`.

## One beam reading instead of two? (`out/print/2.317-one-beam-reading`) -- NO

There are THREE beam readings in the held verdict, not two: A the bar-crop ink test
(`rhythm.py::_beam_levels :3233`), B the stroke-map tip (`_beams_from_strokes :4170`), C the stem-tip
ink look (`_stem_tip_strokes :1596` via `_tips_honouring_claims :4573`, block `:5281-5310`), which is
the source of "a further level possible". Truth is the AGENT'S look except 1 note Sean judged; the
agent could read only 40 of 119 Litolff tiles (a beam fused into a staff line cannot be excluded).

| | A right/wrong | B right/wrong/silent | C |
|---|---|---|---|
| Litolff held, 20 read | 14 / 6 | 14 / 5 / 1 | said "two" 8 times, wrong 8 of 8 |
| Brahms held, 49 read | 18 / 31 | 21 / 27 / 1 | spoke 16 times, right 16 of 16 |

Neither A nor B can be retired: B is no better than A. The common miss on Brahms is a SECOND BEAM
SHORTER THAN THE FIRST (starting at a later stem): A and B both count one. C sees it on Brahms and is
wrong on Litolff (beam against a thickened staff line; not tested at pixel level).

The control could not fail: a decided note is one where the readings agreed (A equals the decided
value on 400 of 400). By the agent's look 4 of 31 decided Brahms beamed notes are written with one
beam where the print shows two -- NOT CONFIRMED (no judged or hand-labelled cover; Sean's judged
answers cover 4 of the 747 notes here, the hand-labelled page 12).

Lesson: we have no judged truth for beam counts, so three hypotheses were tested against our own
agreement. Next is truth first (Sean's reading of beamed notes on both plates), then one beam count
taken where the beams meet the stem's ink that is right on both plates.

## Sean's 24 beam tiles (`out/print/2.317-beam-tiles`, answers.json; key beside the folder)

Sean named the value of 24 boxed notes (his numbers 1-24; OUR reading: 1-12 = B01-B12, 13-24 = L01-L12).

| | A bar-crop | B stroke-map tip | C stem-tip look | agent's look |
|---|---|---|---|---|
| Brahms, 12 | 7 right / 5 wrong | 7 / 5 | 4 / 0 | 7 / 4 |
| Litolff, 12 | 8 / 4 | 11 / 1 | 0 / 5 | 5 / 0 |

- Brahms: the 4 decided eighths the agent thought were sixteenths ARE eighths (no hidden wrong there;
  the agent's look was wrong 4 of 4). The 4 held notes where C says two beams are sixteenths: A and B
  both miss a real second beam, C reads it.
- Litolff: 4 held notes are QUARTERS (pages 15 and 13); A counts a beam that is not printed, B reads
  none and is right. C says two beams on 5 eighths and is wrong all 5. B is wrong once (an eighth read
  with no beam).
- So the two plates fail in opposite directions: Brahms MISSES a printed beam, Litolff INVENTS one.
  Why A sees a beam on a Litolff quarter and why C sees a second one is not yet found (staff-line ink
  is the suspect, not tested). 24 notes: a control set, not a rate.

## 2.318 Part 0: the cause of each beam fault (`out/print/2.318-part0`; agent's trace on Sean's 24 notes)

All three are STAGED ADJUDICATE judging a STROKE AS A WHOLE where the page asks how many beams stand at
THIS stem. Lesson: a stroke is not a beam level, and three readers each carried a different ruler.

1. Brahms misses the second beam (B01, B04, B06, B10). The second beam starts at a later stem and its gap
   fills in on the scan: one stroke, one beam thick over its first stems and two over its last. B
   (`beam_strokes.py::tip_reading`) calls a stroke double only when its MEDIAN thickness is >= 1.0 sp
   (`FUSED_DOUBLE_MIN_THICKNESS_SPACES`) and local >= 0.8; at the stem these read 1.42 / 1.28 / 1.06 sp
   with medians 0.93 / 0.73 / 0.77. A (`rhythm.py::_fused_double_beams :1497`) needs a second stroke to
   compare. B01's fused wedge is refused `not_straight` (bow 0.48 against 0.40). Same condition:
   36 + 8 of the 176 Brahms "further level" notes; 65 + 45 DECIDED one-beam notes of 3,145 (at risk or
   already wrong -- not judged).
2. Litolff, A counts a beam on a quarter (L02, L05, L07, L09). `gather.py::beam_stroke_ink :12903`
   measures thickness on the raw raster with NO staff-line exclusion: a staff line with a neighbour's
   head fused to it reads 0.67 sp. `_stem_joined :547` then joins by BOX overlap. Same condition: 25 of
   62 Litolff "one possible beam stroke"; 70 of 3,701 decided beamed notes.
3. Litolff, C counts a second beam (L01, L06, L08, L10, L12). `gather.py::beam_runs_at_stem_end` reaches
   2.4 sp up the stem and lands on the staff's bottom line, which stays ink wherever a head touches it.
   C spoke 23 times on Litolff, never decided: removing it costs no written Litolff note. Brahms not
   counted.

Hand count "bars of beam ink at this stem's tip, staff lines out" (agent's look): agrees with Sean on
all 17 tiles read (12 Litolff, B01/04/06/10/12); 7 Brahms tiles drawn but not read. Hard: L11, L12
(beam on a line, fused with `ff` or a wedge), L07, B01, B04. Prior: 2.311's whole-stroke "ink meets
stem" test was refuted (disturbed a third of decided notes); M4a page beams OFF (slurs, staff residue,
word ink filed as beams).

## 2.318 build rounds 1-2 and the pixel test: the rule as built does NOT beat today's readings

Sean 2026-11-18 "Let's try it" (one beam count at the note's own stem). Branch `lane-2.318`
(`tools/omr/staged/beams_at_stem.py`, flag `OMR_BEAMS_AT_STEM`, OFF, NOT merged).

- Round 1 (count on stroke-map rows at ADJUDICATE): Sean's 24 notes 17 right / 0 wrong / 7 marked; Litolff
  p2,3,6,13,15 judged right->wrong 3 (four beamed eighths, p2 bar 13: the stem stroke ends INSIDE the beam
  and the rule looked past it -- not a chord, as first guessed); beams +33 -125; red bars 129 -> 144.
- Round 2 (tip follows the stem's ink; a bar may cover the tip): right->wrong 0, control 21 / 0 / 7, but
  86 notes written today become marked and 35 lose their beam (agent's look: 10 of 12 were right before);
  red bars 129 -> 137. Causes: stem not in the stroke map (~30), a 0.85-1.0 sp "one thick or two fused"
  band (29), no bar at the tip (52). Brahms not run. Stopped by the manager: stroke rows are whole-stroke
  summaries again, and the agent's next step was looser cut-offs.
- Pixel test, no build (`out/print/2.318-pixel-count`, `pc.py`): bars of ink counted in a thin column
  beside the stem on the page raster, staff-line rows out. Sean's 24: 17 right / 4 wrong / 3 cannot tell
  after one revision made AFTER seeing the tile failures (optimistic); reading B alone is 18 of 24. All
  189 judged notes with a beam-relevant answer: quarters 89 right / 1 wrong / 7 cannot tell; ONE-BEAM
  notes 32 / 35 / 16; two-beam 6 / 1 / 2. Against 300 decided notes per plate it disagrees or cannot tell
  on 90 of 197 Litolff one-beam notes and 58 of 100 Brahms two-beam notes.
- THE CAUSE UNDER ALL OF IT: where the count failed, the stem's tip is on or beside a STAFF LINE in 74 of
  98 Litolff cases and 66 of 106 Brahms cases. A beam lying on or fused into a staff line cannot be told
  from the line by thickness in one column; that is also fault 2 (A's beam on a quarter) and fault 3 (C's
  second beam). Every reading we have, old or new, fails at the same place.

Lesson: the rule was right as a musician says it and wrong as we measured it; "at the stem" is where
the staff line is. Not known: how a reader tells a beam on a line from the line -- asked of Sean.

## 2.318: the erased-staff reading (B) used alone (`out/print/2.318-erased-alone`; read-only, real `tip_reading` called on stored strokes, reproduces the record 5,600/5,600 and 13,658/13,658)

Sean 2026-11-18: "Why don't we used the erased staff to get beams?" B is the one reading built on the
staff-erased raster.

- BEAMS on Sean's tiles (+ Litolff p2 bar 13): Litolff B 14 right / 1 wrong / 1 silent, today 5 right / 11
  silent. Brahms B 7 right / 5 wrong / 0 silent, today 6 right / 6 silent -- B alone would WRITE the missed
  second beam as an eighth (a hidden wrong) where today the note is held.
- B is not a flag reader: alone it turns 172 Litolff and 2,848 Brahms flagged eighths into quarters (15 of
  its 22 right->wrong against Sean's 189 judged notes). Flags must stay with the flag reader; "B alone"
  can only mean the BEAM count.
- Why B is silent on notes written as beamed today (542 Litolff, 384 Brahms): STEM CHOICE 314 / 307 -- B
  takes the stem by its midpoint against the head's centre, so the upper head of a chord gets none;
  choosing by the stem's far end restores 267 / 247 to today's value. TWO VOICES 224 / 76: B is skipped by
  design. Narrowed 18 / 55 (a one-stem stub; about half are the note's own ledger line). The eraser left
  every printed beam intact in 18 crops looked at (agent's look).
- Thickness at the stem: without the median gate 163 Litolff / 61 Brahms decided notes go 1 -> 2; on
  Litolff 156 of those sit on a staff line (the restored thickness includes the line). With the line's own
  thickness taken out: Litolff 15 decided / 0 held, Brahms 5 decided / 38 held -- and only B04 of the four
  Brahms second-beam tiles is fixed. The fused second beam is NOT solved by thickness at the stem.
- Angle: 668 of 1,547 Litolff and 862 of 1,855 Brahms beam strokes lie on a line for half their length;
  only 19 and 49 are flat. A flat beam on a line: 35 Litolff and 104 Brahms notes.
- Of the 347 held notes B gives a count to 71 of 79 Litolff and 249 of 268 Brahms (not judged).

## Is ink claimed once? (audit, `out/print/2.317-claim-audit`)

Asked by Sean 2026-11-18. Enforced in ADJUDICATE only, and by box share (a box is refused at >= 50%
claimed ink; a surviving box keeps all its ink). Not enforced in GATHER: the stem-tip look
(`gather.py::_observe_stem_tip_ink`) reads a raster window before any claim exists, and
`OMR_STEMS_FROM_STROKES` is OFF so the stroke route does not replace it; `gather_notehead_ink`,
ledger ink, dot positions and `gather_ink` never ask. Words, dynamics and brackets claim after the
heads, against the plan. No gate fails if a reader takes claimed ink.

Litolff pages 1, 2, 8 (`claim_readout ink`): one owner 89.5%, none 4.4%, claimed twice 5.7%; most of
the twice figure is one mark on two of our lists (the clef alone ~2.2%); two different kinds ~1.4%.
12 random double claims: all slivers where two real marks touch, none a whole mark claimed twice.

## Where the join is measured from the box (worklist for "join by ink", Sean 2026-11-18)

stem-head `adjudicators/stem_value.py:361`, `geometry.py:196`; beam levels `adjudicators/rhythm.py:3233`,
`:5009`, `_stem_joined :547`; beam/flag side `:3494/:600/:2148`; dot-head `:2364`; chord grouping
`:6674`; unison split `:3432`; twins `notehead_precision.py:2644/:2111`, `family_precision.py:405`,
`claims.py:296`, `ownership.py:4335`; owning staff `ownership.py:697/:4266`; accidental-head
`ownership.py:5094`; ledger rungs `family_precision.py:1746`; arc ends `arc_claim.py:716`. The page
stem reader `stem_strokes.py:175` reads ink and is OFF; the page beam reader (M4b-e) is not built.


## 2.318 round 3 -- the erased-staff reading as the one beam count (built OFF, stopped at the gate)

STAGED, ADJUDICATE. Branch `lane-2.318-r3` (ac9b3ee9c), flag `OMR_ONE_BEAM_COUNT`, default OFF, not merged.
A lane agent's report, filed by the manager; branch, flag, tests and the two strict xfails checked against the tree.

**Cause and lesson.** Reading B was already the best of the three but was silenced by its own stem pick and its
two-voice skip. Giving it the stem's far end and both voices lets it speak -- and then the lane added three
"cannot tell" rules of its own (unexplained ink at the stem's end, a stub at the tip, a stem touching a beam it
did not count), and those take the value from more notes than the three-reader disagreement did. Lesson: a
refusal rule added to protect a new reader is a change to the file like any other, and must be measured on notes
that are written right today before it is kept.

**File changes** (`lane_report`, `--from adjudicate`, record 20261117-night; changes, not verdicts):
- Litolff frozen sample: notes +80 -275, beams +56 -132 ~53, flags +51 -55, blue +230 -140, red bars 160 -> 154,
  notes not written 2077 -> 2255.
- Brahms frozen sample: notes +82 -275, beams +26 -42 ~9, flags +19 -38, blue +339 -148, red bars 134 -> 129,
  notes not written 3068 -> 3268.
- Tile pages: Litolff red bars 129 -> 129, not written 1585 -> 1732; Brahms red bars 50 -> 53, 1422 -> 1457.
- Decided notes that lost their value, tile pages: Litolff 255 (unexplained ink at the stem's end 108, no stem
  stroke in the map 55, stem touches a beam it did not count 31, stub at the tip 25, several stems 15, thick at
  the stem 6); Brahms 91 (unexplained ink 40, stub 22, no stem 14, thick 11, several stems 3).
- Decided notes that changed value, Litolff frozen sample: 33; direct reads 0->1 ten, 1->0 nine, 1->2 five,
  2->1 one. The nine 1->0 are unjudged and could be hidden wrongs. Flag-sourced values changed: 0, both plates.
- The 347 held notes (offline, on extracted cells, not a pipeline run): 191 now carry a value, 83 marked {1,2},
  about 72 {0,1}.

**Judged right->wrong: 0** on every run. Right->narrowed: tile pages Litolff 3, Brahms 0; frozen sample 1 and 3.

**Controls** (real stroke rows of Sean's 24 tiles, Litolff p2 bar 13, 11 more judged notes): old B writes the
five Brahms sixteenths as eighths; the new count marks B01, B04, B06, B10 {1,2}; bar 13 reads four eighths.
STILL WRITTEN WRONG, `xfail(strict)`: **B09** (0.79 sp thick at the stem, 0.54 with the staff line out; a
"thick here >= 0.75" rule catches it and narrows 2 of Sean's 47 one-beam notes, but about 360 one-beam stems on
the whole movement) and **L11** (a beam fused with an `ff`; narrowing on claimed ink at the stem's end marked
65 notes written right today, so it was turned off).

**Numbers added**: staff-line thickness 0.25 sp (measured, narrows only); stem bridge gap 0.35 sp (from 2.161);
stem collinear 0.3 sp and break gap 0.6 sp (from `stem_strokes`). Tuned on our two plates: may narrow, not decide.

**Baseline** OFF reproduces the record (0 differing verdicts). Fast tier 10,886 passed, 2 failed (the known
far-head order test; `test_judged_index_2_106` reads the checkout's `out/print`). `staged.check` open=216, not
diffed against main.

**Not done**: no clear crops of the lost-value and changed-value notes (the lane's panels are too small, Brahms
none); no default flip.


## 2.318 rounds 4-5 -- the refusal rules measured, B09 and L11 closed (built OFF, gate not yet met)

STAGED, ADJUDICATE. Branch `lane-2.318-r4` (09563b178), flag `OMR_ONE_BEAM_COUNT` OFF. A lane agent's reports,
filed by the manager; "look" below is the agent's or the manager's look at crops, not truth.

**Causes and lessons.**
- Round 3's three added refusal rules protected no judged note; out one at a time, Sean's tiles stayed right.
  The count's "ink at the tip" window reached 3.3 spaces inward, so on short stems slurs, neighbour heads and
  another note's beam counted as ink at the tip. A cannot-tell rule is measured on the real pages before it is kept.
- **B09 was never a thickness problem.** The second beam is a separate stroke from the second stem to the last;
  the count merged the two as one level because it compared the strokes' BOX centres (0.39 sp apart on a sloped
  pair) where the ink lines are 0.96 sp apart. Measured by centre lines along the shared stretch: B09 right, 0
  other notes changed on the tile pages. The round-4 "step in thickness" rule would have marked about 60 good
  notes to catch it. Measure the mark, not its box; read the real stroke rows before proposing a measurement
  (the manager proposed thickness twice).
- L11 (beam run into an `ff`): ink claimed by a dynamic or word, or beam-shaped claimed ink, touching the stem's
  ink in the first-level zone marks the note; about 20 notes on both plates (round 3's "any claimed ink": 65).
- Several lost and changed notes were stem-pick faults, not beam faults: a head cut in pieces lent an outline
  piece as its stem; a vertical running past a head both ways was read at the neighbour's tip.

**Rules now in the count** (each narrows only): stub at the tip only where a full beam is already counted; claimed
dynamic/word ink at the tip; a flat thin unclaimed line at least 2 sp long at the tip keeps a scan-thinned beam;
levels told apart by centre lines; an outline piece under 2.5 sp within 0.7 sp of the head is not a stem; a
vertical past a head both ways with no direction verdict is read from both ends (agree = read, differ = marked);
where the map has no stem or the count cannot rule out a beam, the flag reader speaks first. Measured and refused
(switches left OFF): step-in-thickness, cut-by-cell, stem direction from the ink, looser stem x-slack.

**File changes, round 5** (`lane_report`, ON vs OFF, `--from adjudicate`, record 20261117-night; changes, not verdicts):
- Litolff tile pages: notes +101 -72, beams +46 -62 ~25, flags +41 -29, blue +71 -106, red bars 129 -> 136, not written 1585 -> 1563.
- Brahms tile pages: notes +70 -35, beams +58 -44 ~9, flags +36 -26, blue +81 -77, red bars 50 -> 54, not written 1422 -> 1394.
- Litolff frozen sample: notes +75 -123, beams +51 -112 ~37, flags +57 -47, blue +100 -117, red bars 160 -> 161, not written 2077 -> 2119.
- Brahms frozen sample: notes +98 -70, beams +28 -43 ~10, flags +33 -22, blue +120 -153, red bars 134 -> 126, not written 3068 -> 3037.

**Judged right->wrong 0** on all four runs; one judged Litolff eighth (rhythm-leftovers-2 tile 10) right -> marked
(the both-ways rule). None of Sean's 24 tiles, bar 13 or the 11 other judged notes is written wrong; no xfails left.
Flag-sourced values changed 0. Fast tier: only `test_the_committed_index_is_current`. `staged.check` 216 = main.

**Decided notes that lose their value, tile pages** (round 3: 255 / 91): 87 Litolff boxes, 32 Brahms. By look,
39 Litolff and 3 Brahms are NOT noteheads (clef, key, rest, dynamic letter, beam strip, barline, sliver, "8a.").
Real noteheads about 48 Litolff: no stem stroke in the map 14 (stem fused into a barline/clef blob), count 0 but
the flag-ink reader found ink 13 (today's quarter looks wrong in the crops), thin line 7, thick at the stem 7,
stub 3, several stems 3, claimed ink 1. Brahms 29: thick at the stem 10, no stem 9, stub 8, claimed ink 2.

**Changed value** (Litolff 20, Brahms 17, all sheets looked at): most Litolff eighth -> quarter are boxes on beam
ends or slivers; real heads where ON looks right: Brahms 4 quarter -> eighth, 6 eighth -> sixteenth, Litolff 3
quarter -> eighth. Unclear: Litolff 15/1/3/18/0 and /3, 2/0/9/1/3, 15/0/10/0/2; four Brahms dotted quarter -> quarter.

**Open after round 5**: newly red bars on the tile pages (Litolff 15 new vs 10 cleared, Brahms 11 vs 7), of which
9 and 8 hold no note that OFF had decided and are untraced; the Litolff frozen sample writes fewer notes; the
no-stem heads (upstream stroke map); the unclear changed notes.


## 2.318 round 6 -- the wrong end of the right stroke (branch `lane-2.318-r6`, a0b7e2627)

STAGED, ADJUDICATE. A lane agent's report (Fable), filed by the manager; "look" is the agent's look, not truth.

**Cause and lessons.** Round 5's losses and red bars were almost all the count reading the wrong END of the right
stroke, or a join the stroke map files in pieces -- not beams it could not see. The stem's ink ran on past its beam
into an `ff`; a neighbour's stem passing just below the head counted as a second stem; the head's own body was
taken for the stem; the beam's stroke stops a hair short of its outer stem; the barline or clef claimed the stem
set against it. Round 5 had also changed the "no beam" state for beamless cells, which sent those heads to the
stem-tip flag look for the first time (it read a ledger line and the word `Vcl.` as hooks: 7 lost Litolff notes,
3 quarters written as eighths) -- wiring, not the count. The four Brahms dotted quarter -> quarter were one chord
head with no stem in the map speaking first for the whole stem. Lessons: when a new reader says "no beam", check
which end it read and whether the join exists before adding a refusal; a rule developed on the tile pages wrote
two wrong sixteenths on a page outside them and only the frozen sample showed it.

**File changes** (`lane_report`, ON vs OFF, `--from adjudicate`, record 20261117-night; changes, not verdicts):
- Litolff tile pages: notes +101 -31, beams +52 -34 ~24, flags +28 -18, blue +52 -95, red bars 129 -> 133, not written 1585 -> 1528.
- Brahms tile pages: notes +68 -11, beams +59 -8 ~8, flags +15 -24 ~3, blue +26 -71, red bars 50 -> 52, not written 1422 -> 1364.
- Litolff frozen sample: notes +73 -75, beams +50 -65 ~24, flags +42 -28, blue +62 -111, red bars 160 -> 158, not written 2077 -> 2076.
- Brahms frozen sample: notes +104 -34, beams +38 -15 ~3, flags +16 -16, blue +69 -143, red bars 134 -> 137, not written 3068 -> 2996.

**Judged right->wrong 0** on all four runs. Right->marked: 0 on the tile pages; 1 on the Litolff frozen sample
(2.83-fix-review tile 8, a quarter the count reads right, marked by the old tip-readers-disagree narrowing that
the bar sum no longer settles). Sean's 24 tiles, bar 13 and the 11 others: none written wrong (84 tests).
Flag-sourced values changed 0. OFF reproduces the record. Fast tier 10,915 passed, the two known failures only.
`staged.check` 216 = main.

**Real noteheads losing a decided value, tile pages (look):** about 17 Litolff, 6 Brahms. Litolff: a lump on the
beam at the stem 6 (head run into the beam, or a short second beam; L12 is the judged example), a beam the map
measures thinner than a beam 5, stem lost in a blob or chord stack 2-3, stem and beam outside the cell's cut 1,
second upright the other way 1, stub 1. Brahms: word or hairpin ink at the stem's end 2, clef-claimed stem with no
beam to witness 2, no stem 1, thick at the boundary 1.

**Newly red bars, traced.** Tile pages: Litolff 9 new / 6 gone, Brahms 5 / 3; no decided real note is read worse
in any. Litolff: 5 are a box that is not a notehead newly written a quarter (tie arc, sharp, accidental, a glyph,
a tremolo slash), 1 the bar rule guessing an eighth on a quarter the count read right, 2 gain right-looking notes
in a still-incomplete bar, 1 unclear (p15 0/3/19). Brahms: 1 a dot not attached, 1 tremolo-slash boxes, 3 gains in
incomplete bars. Frozen sample: Litolff 10 / 12, Brahms 11 / 8; five bars hold a real note now marked.

**Briefed questions answered.** The 13 "count 0 but flag ink found": 7 the flag-look wiring, 6 the both-ways rule,
none a missed beam. No real dotted-figure stub exists on these pages (all 19 stand 2.0-3.1 sp from the beam).
"Thick at the stem" is still needed (B01, B04, B06, B10) and now marks only stems within 2 sp of the thick stretch.

**Rules added** (each with a real-stroke control that fails with the rule off; numbers narrow only): the free end
is the tip (an end passing the head by under 0.75 sp is the foot: 0.0-0.67 for 125 strokes, 0.9+ for 32); a beam
ends on its outer stems (join across at most 0.5 sp, never a stroke under 2.5 sp); a stem ends at its beam where
its ink runs on into a dynamic or word; mark at a bare tip with a long curved flag or beam-thick stroke joined to
no second stem; a stem in a barline's or clef's claim is read only with a beam touching it; end-on hair of paper
0.35 sp (0.6 where a ledger line cut it); stem up to 9 sp where its ink touches the head; a second beam only at
stems it reaches (2.0 sp); a stub must stack on the beam (0.75 sp); a box on the beam at the stem's far end
carries the stem's count; clot at the join up to 1.6 sp inside the beam's band; an outer beam must share two
stems with the touched beam; the head's own body is not a stem; a letter's claim cut in pieces still marks;
`stem_value.py`: a head with no stem in the map does not speak for the stem's levels; `rhythm.py`: the "no beam"
state stays what OFF had, so flags are asked exactly as today.

**Open, named, not fixed:** non-notehead boxes newly written as quarters (7 Litolff, 1 Brahms; OFF already writes
46 and 11 such -- a head-box fault, not a beam fault); thin-beam and lump-on-beam notes marked; the judged quarter
marked on the frozen sample; unclear by look: Litolff 15/0/3/19/2 and /3, 2/0/9/1/3; the final traces were run one
commit before the last (three Litolff p4 heads differ).

**Manager's landing decision (2026-11-19, Sean asleep, under his "Take as many rounds as necessary to land
this").** The lane agent ended "GATE NOT MET" against the stricter round-6 brief. Against the gate recorded in
DECISIONS -- judged right->wrong 0, none of his 24 tiles or bar 13 written wrong, lost notes down to a handful
each named by cause -- it holds: 17 and 6 real notes marked, each named; more notes written on three of four
runs and level on the fourth; the remaining red bars are a head-box fault OFF already has. Landed ON; the open
items above go to the overnight read and to their own rows.

## 2026-11-23 -- 2.341 built OFF (`lane-2.341` 641fdb4a0; `OMR_HOLLOW_HEAD_WINS`, `OMR_STEM_TIP_FLAG_WHEN_DECLINED`; STAGED ADJUDICATE)

A, half notes written quarter: on Litolff the detector box sits on the upper part of the head (the head's own ink centred 0.1-0.44 sp below the box centre); the 2.148 read looks at the box's middle rows, misses the half's slit, reports 0.00 white, and a plain black quarter is written. Re-reading the box on the page raster also gives 0.00: the box placement is the cause. The own-ink read finds the slit; but on Brahms every disagreement looked at was a black chord head or a sharp (the "opening" is the gap between fused heads). Sean's m169: the box sits a whole space above the head, neither read sees it (a head-position fault in GATHER). Built: where the two reads disagree and the stem carries nothing the note is written blue with both values, never plain; "never the gap between two fused heads" NOT yet enforced. B, unread flags: `reader_declined` only means the cell has no beam the page beam reader accepted; nobody looked at the stem, the flag look never ran. Built: a flag makes an eighth only where a counted, shaped hook hangs from a free tip; never a stroke crossing both sides of the stem, a stem running into ledger lines or words, or an uncounted hook (those keep the quarter blue with the eighth beside it). Lesson: a read that measured a box nobody checked against the mark answers as confidently as a real read. Frozen sample, re-adjudicated ON vs OFF: A Litolff notes +2, values ~4, blue +10, red 139 -> 138; A Brahms notes -2, blue +10, red 126 -> 125 (all cost by the agent's look: blue on right black heads, a sharp on p19 written a blue half); B Litolff blue +3, red 139; B Brahms values ~15 (flags +14), blue -6, red 126 -> 116; both: 139 -> 138, 126 -> 115. Judged right->wrong 0, no judged value tile moved. 2.318 r6 controls stay quarters. Sheets `out/print/2.341/`. A is not ready (fused heads); B's nine Brahms eighths on its sheet look right to the agent, put to Sean.


## 2026-11-24 night -- 2.349 built OFF (`lane-2.349`; GATHER `OMR_STEM_TIP_COLUMNS`, ADJUDICATE `OMR_TWO_BEAMS_AT_STEM`; STAGED; NOT proven by a page gather)

CONVENTION ASSUMED: two beams are parallel bars about half a space thick, the second lying inward of the first with less paper between them than a beam is thick. WOULD FALSIFY IT: a judged eighth showing a second beam-thick bar parallel to its beam with thin paper between; another publisher's sixteenths with more than 0.4 sp between beams. NOT CONFIRMED by Sean.

**Cause.** Brahms prints two beams 0.06-0.25 sp apart. The stroke map reads the page at 16 px a space, so that paper is only 1-4 px and the reduction fills it in: two beams become one stroke, double-thick over part of its run. Every reader after that judged the fused stroke as a whole (median, box edge, a 12-sample profile spaced 0.6-1.1 sp apart). At full resolution on the staff-erased raster, the column just beside the stem shows both bars and the paper between them. **Lesson:** before tuning cut-offs, check that the measurement's resolution is finer than whatever separates the two marks. 2.318's pixel test did look at full resolution, but on the unerased raster, where the staff lines got in the way.

**Rule (musician's words).** Beside the stem, a second beam is a second bar lying just inside the first, toward the head, with a thin line of paper between them. Where the two meet the stem the scan may fuse them into one slab; a little way along the beam the paper shows again. One bar beside the stem, on every side that has a beam, means one beam. NEVER on a slab alone (L12, Sean "8th", slab 1.27-1.33, cannot be told from tile 5's fused pair at 1.37 by thickness). NEVER on ink as thick as a head cluster, on a second bar first seen past a stretch of single beam (a neighbour's partial beam), on a bar another mark claims, or on a bar that does not run parallel over 3 columns.

**Numbers** (columns 0.15-1.2 sp out from the stem's ink edge, canonical erased raster, Sean's judged marks): paper between two beams at most 0.4 sp. Sixteenths measure 0.06-0.25 (B01 0.22, B04 0.12, B06 0.25, B10 0.08, B09 0.07-0.18, Brahms p5 1/5/12 0.19, p0 tile 5 0.06-0.16). Inside a judged single beam, the nearest ink is 0.64 sp or more (L06 0.64, L08 1.01, L01 1.07, B05 1.78). A bar counts from 0.5 sp, an existing convention (singles measure 0.54-0.91). A slab starts at 1.0 sp, existing (slabs measure 1.27-1.45). A head cluster starts at 1.75, existing (the thickest slab is 1.66; a head is 1.81). Two tolerances: a bar must hold for 3 columns (tile 5 has exactly 3), and the bars must stay parallel within 0.15 sp (the judged pairs vary by at most 0.10). Of these, only the 0.4 sp gap and the two tolerances are new, and they rest on our two plates.

**Controls on real pixels** (`tools/omr/tests/test_two_beams_at_stem_2_349.py`, crops in `fixtures/two_beams_at_stem_2_349/`): B01, B04, B06, B10 and tile 5 come out narrowed 1-2 OFF (fails on old code) and read as 2 ON. No judged note of the 2.318 fixture moves except those five. L12 stays narrowed. A claimed second bar is not read. GATHER files nothing with its flag OFF.

**Replay** (lane_report, `--from adjudicate`, 20261123-night sliced to Sean's 2.317 tile pages + Brahms p0; tip_columns added offline from the master cells, where every cell reproduced the record's strokes: Litolff 1,964, Brahms 2,508; NOT the frozen sample):
- Litolff p2,3,6,13,15: notes +2, beams +3, blue +2, red bars 100 -> 100. OFF reproduces the record. Judged (307 tiles): right->wrong 0, wrong->right 0. Values: 2 narrowed {0.25,0.5} -> 0.5.
- Brahms p0,1,4,7,15-20,25: notes +79 -1, beams +79 ~19, values ~12, blue +9 -65, red bars 158 -> 155, not written 4038 -> 3957. Control: OFF differs from the record by 1 of 16,688 verdicts (the tree moved since the night; the flag is not the cause). Judged (306 tiles): right->wrong 0, unwritten->right 5. Values: 46 narrowed {0.25,0.5} -> 0.25; 14 decided 0.5 -> 0.25; 9 {0.375,0.75} -> 0.75; 4 {0.25,0.5} -> 0.5; 1 narrower. Tile 5 is decided 0.25 ON but still not written (a later stage holds it, untraced).
- The 14 decided eighths -> sixteenths (Brahms p17/p18: dotted-eighth-and-sixteenth figures): by the agent's look, all stand under two beams, so OFF was a hidden wrong. Not judged. Crops: `out/print/2.349-changed/` (sheets `sheet_eighth_to_16th.png`, `sheet_sample.png`).

**Not done:** no page gather (the GATHER fact is unproven by a gather); not run on the frozen sample or whole movements; Brahms p1 chords {0.25,0.5} -> 0.5 unclear by look; no example of a neighbour's partial beam reaching within 1.2 sp exists among the judged marks, so that never-rule has no real control.


## 2026-11-25 -- 2.349 proved by a LIVE page gather (`lane-2.349-proof`; STAGED GATHER `OMR_STEM_TIP_COLUMNS` + ADJUDICATE `OMR_TWO_BEAMS_AT_STEM`; measure only, nothing flipped)

Live gather, flags OFF then both ON, one arm at a time, `--from gather --cell-map master`, tree = lane-2.349 + main 601faee4c. Brahms p0, 17, 18 (p0 also the meter context) and Litolff p6 (context p1). NOT the frozen sample. Scratch `/private/tmp/claude-501/lane-2.349-proof/`.

- **Live agrees with the offline replay.** The offline replay was rebuilt from the 20261123-night rows plus `tip_columns` computed from the master cells (every cell reproduced the record's strokes, 0 mismatches). Matched by place: Brahms 3,369 notes, the two_bars read the same on all 764 notes that carry one (52 two, 691 one, 27 slab/unread), every duration verdict the same (0 of 3,369 differ; the two OFF arms also 0 of 3,369). Litolff p6: 1,047 notes, read same 356 of 358, verdicts 9 differ, all 9 also differ OFF (tree moved since the night; not the flag). The flag moves the same 63 Brahms notes (38 narrowed -> 0.25, 14 decided 0.5 -> 0.25, 9 narrowed -> 0.75, 2 narrowed -> 0.5) and the same 2 Litolff notes (narrowed -> 0.5). The 14 decided eighths -> sixteenths are the same 14 places live and offline (p17 12, p18 2).
- **File changes, live ON vs OFF** (`lane_report`): Brahms notes +67, rests +3, accidentals +6, dots +13, flags +4 -7, beams +70 ~18, ties +7, slurs +20, articulations +8, values ~12, blue +5 -46, words +6 -34, red bars 29 -> 27, not written 1010 -> 940. Litolff p6 notes +2, flags -1, beams +3, blue +2, words +1 -1, red 38 -> 38. The offline replay's file change on the same pages is line for line identical.
- **Judged**: right->wrong 0, unwritten->wrong 0 on both plates. B01, B04 (p17) and tile 5 (p0, `glyph/0/0/12/1/1`) are narrowed OFF and decided 0.25 ON (two_bars read "two"); B09 decided 0.25 both arms. L01, L06, L08 stay decided eighths (read "one"); L12 stays narrowed {0.5, 0.25} (slab, never read two), written neither as a sixteenth. NOT RUN live: B06, B10 (Brahms p4) and L02, L05, L07, L09 (Litolff p15), pages outside the set.
- **Tile 5 trace.** The lane named `glyph/0/0/12/1/15`; the note that is decided 0.25 is `/1`, and it IS written (plain 16th G4, `rg` `/1`, page box 2602,6343 -- both live and replay). Tile 5 lists two ids; `/15` is a second head-sized box at the stem's far end (page box 2571,6443-6481), narrowed `beams_ambiguous` ({1.0, 0.5}) in BOTH arms because its stem finder says `no_vertical_touches_the_head` (the count is `silent`, the flag never reaches it) and refused in EXPORT `_place_notes._drop` as `duration_narrowed`. The report's NOT FOUND is the judged scorer following `/15`. Cause upstream: ADJUDICATE `rhythm._one_beam_count` -> `beam_strokes.beam_count` finds no stem for that box.
- **Cost** (single run each, a heavy lane on the machine): gather wall Litolff 244 s OFF / 241 s ON (p6 160 / 161 s); Brahms 1,984 s OFF / 1,844 s ON (p0 845 / 784, p17 515 / 468, p18 624 / 592). Peak RSS Litolff 5.83 / 5.94 GB; Brahms 9.37 / 13.28 GB, but the process already stood at 8.5 / 11.1 GB two seconds in, so the flag's own share is about +1.3 GB at most (not isolated). Gathered record 226.9 -> 228.4 MB.
