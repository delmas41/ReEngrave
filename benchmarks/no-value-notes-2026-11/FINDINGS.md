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
