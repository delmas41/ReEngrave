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
