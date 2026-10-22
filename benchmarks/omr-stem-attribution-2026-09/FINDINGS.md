# A stroke belongs to the head at ONE OF ITS ENDS — ⚠️⚠️ REFUTED BY THE PRINT, AND THE PREMISE WAS THE INSTRUMENT'S

⚠️⚠️ **READ THIS BANNER BEFORE ANY NUMBER BELOW IT.** This lane set out to
confirm a fault two lanes had converged on, measured a population for it, and
**Sean refuted it in three messages by looking at the pictures.** Everything
under §1-§6 is the measurement AS TAKEN and is kept because the correction is
the finding; the conclusion it reaches is **withdrawn**. §0 is what replaced it.

## 0. ⚠️⚠️ WHAT ACTUALLY HAPPENED — the refutation, in order

**(a) The chord test could not see a two-note chord.** A head counted as a
legitimate chord member only if it had a companion ABOVE *and* BELOW on the
same stroke. An octave pair has ONE companion, so by construction neither note
could ever qualify and whichever was not at the stem's end was filed as a
suspected fault. Sean, on the first strip he was shown: *"it is an octave of
C's and the stem belongs to both"* — and the software had put that strip in the
**presumed-fault** group.

**The shape is most of the group.** Heads on a stroke with exactly one
companion — what a two-note chord looks like — are **98 of 153 (64%)** on
Litolff and **219 of 231 (95%)** on Breitkopf. ⚠️ **So the headline "148 and 228
heads take a direction from a stroke that is not theirs" was inflated by a
broken test and must not be quoted.**

**(b) Corrected to Sean's own rule** — *a companion on the stem, either side,
is a chord* — the suspect population falls to **51 and 14**:

| | Litolff | Breitkopf |
|---|--:|--:|
| head at an END of its stroke — fine | 1,526 | 1,635 |
| not at an end, companion at the SAME x — a chord | 182 | 246 |
| not at an end, companion 0.1-0.5 notehead widths away | 33 | 6 |
| not at an end, companion >0.5 away | 9 | 3 |
| not at an end, NO companion at all | 9 | 5 |

⚠️ The x split is a SORT, not a rule: the widest empty interval in the
offset distribution is **0.08 notehead widths**, i.e. noise. 72% / 79% sit at
essentially zero, which is the only reason sorting on it is worth anything.

**(c) The residual was put to the print, and it is not a fault either.** Three
of the 26 unexplained cases were rendered and shown to Sean: *"they look like
clean notes with basic stems on them."*

**(d) TWO STEMS ARE BEING MEASURED AS ONE — Sean's diagnosis, and it is
supported by four measurements and a crop.** Shown three residual cases he
read them off the plate: *"the third one has a stem that goes up on the right
hand side and down on the left-hand side… the second has two notes close
together because they're a second apart, one stemming up and the other down…
In all of these cases there are two separate stems that are being measured as
one stem."*

⚠️⚠️ **THE DECISIVE TEST IS AN ASYMMETRY A SINGLE STEM CANNOT PRODUCE. A stem
STARTS at its notehead**, so one stem can overshoot its note at ONE end only.
Measuring the overshoot past the outermost head at BOTH ends:

| | flagged runs overshooting at BOTH ends |
|---|--:|
| Breitkopf | **7 of 14 (50%)** |
| Litolff | 9 of 51 (18%) |

On the most extreme case (`glyph/1/0/3/4/0`) the run reaches **2.5 noteheads
above the top head and 2.8 below the bottom one** over 5.7 staff spaces, and
the crop shows why: **two voices, the upper stemming UP to the beam above and
the lower stemming DOWN to the beam below, at nearly the same x, fused into one
component.**

⚠️⚠️ **CORRECTION, 2026-09-20, FROM THE LANE THAT TESTED THIS
(`benchmarks/omr-stem-run-split-2026-09`): THE BREITKOPF FIGURES BELOW WERE
COMPUTED UNDER A FLAT 100 px AND ARE WRONG BY UP TO 25%.** The unit is
`Q.CELL_STAFF_SPACE` — the CELL's own staff space — and `_upscale_to_canonical`
scales a too-wide cell by WIDTH, so the nominal is wrong on a minority of cells
and silently so. **Only 514 of 817 Breitkopf cells sit at 100**, against 1,167
of 1,180 on Litolff — which is why Litolff is unaffected and Breitkopf is not.
Corrected: unflagged stroke length **3.817** (not 3.46); widths **0.25 /
0.214** (not 0.21 / 0.18). ⚠️ The overshoot figures reconcile once a second
convention is named — this file measures from the head's CENTRE, that lane from
its box EDGE. **This is the exact trap `Q.CELL_STAFF_SPACE`'s own docstring
exists to prevent, and it was committed here.**

⚠️⚠️ **AND THE CONCLUSION IS BOUNDED MUCH TIGHTER THAN THIS SECTION IMPLIES.**
That lane measured the reach: **17 of 4,225 runs (0.40%) overshoot at both
ends**, only **3** carry the two mid-run heads the diagnosis predicts, and at
most **13 noteheads of 5,684 (0.23%)** could take a wrong stem direction.
**13 crops were opened and ONE is the fused-stem fault** — the rest are
cross-staff fusion through the measure-cell padding, stems whose pair was never
detected, a spurious notehead, and accidental/dynamic/rest/blotch ink.
⚠️ **The Litolff 18% INVERTS**: 6 of 6 opened are NOT fused stems, so that
population wears the signature without the cause. Read that lane's FINDINGS
before acting on anything here.

Three further measurements agree and none contradicts:

* flagged runs are **longer** — 5.72 vs 4.12 staff spaces (Litolff), 4.43 vs
  3.46 (Breitkopf), against a ~3.5-space stem;
* cutting the run at the flagged head leaves a **substantial piece on BOTH
  sides** — medians 2.75 / 3.06 and 2.50 / 2.03 spaces — two stems, not one
  stem plus an overrun;
* flagged runs are **~18% WIDER** (0.38 vs 0.32; 0.21 vs 0.18 spaces),
  consistent with two stems at slightly different x merging.

> **The convention is sound and the notes are ordinary. TWO STEMS ARE READ AS
> ONE VERTICAL RUN, and the note that appears stranded mid-stroke is simply
> the one sitting at the junction. The repair is upstream, in SEGMENTING a
> vertical run — NOT in `adjudicate_stem_direction`.**

⚠️ **THE EARLIER GUESS IN THIS FILE — *"merged with a staff line, a beam or
neighbouring ink"* — IS WITHDRAWN.** It was a story offered without a test;
this one has four and a crop. ⚠️ It also **rescues** the 09-18 observation
rather than discarding it: that lane reported the head sitting part-way along
*a neighbouring note's stem*, and the head genuinely IS part-way along a run —
the run is two stems rather than a neighbour's one. Same symptom, corrected
cause.

⚠️⚠️ **AND IT MEETS THE PAGE-FRAME LANE OF THE SAME DAY FROM THE OTHER SIDE.**
That one found a barline's ENDS measured wrong because the measure cell clips
them; this one finds two stems FUSED into one run. **Two independent lanes, one
conclusion: vertical runs are not segmented correctly**, and that is where the
work belongs.

⚠️ **THIS DOES NOT CLEAR THE ORIGINAL 09-18 OBSERVATION.** That lane adjudicated
its own crops and reported *"the record's notehead box stands part-way ALONG a
NEIGHBOURING note's stem"*, 6 of 6. Both can be true: a head box in the wrong
place and a stroke measured too long both put a head mid-stroke. What is
established here is that **this lane's population is not the fault it was built
to find**, and that a repair aimed at the stem DECISION would have been aimed
at the wrong stage.

⚠️ **AND IT VINDICATES THE FIRST REACTION.** Sean, on the very first batch:
*"so far they all look like simple notes with stems."* That was read at the
time as an artefact of an unclear marking. It was the correct read of the
population, arrived at before the instrument could say so.

## 0b. WHAT THE STRIPS COST AND WHAT THEY BOUGHT

⚠️ **The first batch asked a question it had not identified the subject of.**
The strips marked the note's X with ticks in the margin — and *which note owns
this stroke* is a question about **Y**, since the candidates are stacked at the
same x. Marking x alone cannot express it. Re-marked with corner brackets that
name the exact notehead and sit clear of the ink; Sean's verdicts all came
after that change. **Three messages of a musician's time refuted a lane that
four probes and a 17-arm battery had not.**

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

⚠️ `docs/ask-first-conventions.md` governs and this job could not ask, so the
assumption is written down rather than left in the code.

**HOW A HUMAN GETS IT.** An editor with the plate in front of them measures
nothing: the stem *starts at the notehead* and runs away from it. The head is
at the stroke's **END** — its bottom for a stem-up note, its top for a
stem-down one. A vertical line passing through the *middle* of a head, with
the head part-way along it, is a neighbour's stem, a barline or a bracket.

**THE CONVENTION.** A stem attaches at the side of its head and terminates
there, extending away ~3.5 staff spaces or to a beam. That is not a statistic;
it is what attachment IS.

**WHAT WOULD FALSIFY IT.** A print-adjudicated head whose own stem genuinely
passes through it — which happens: an interior member of a chord shares one
stem with the heads above and below it and is mid-stroke by construction.

**NOT CONFIRMED WITH SEAN.**

## 1. ⚠️ THE CONVENTION HOLDS ON BOTH PLATES, AND IT IS BIMODAL

`t` = the head's vertical centre as a fraction of the stroke's own height; 0.0
is the stroke's top end, 1.0 its bottom, 0.5 halfway along. Pairs that are not
flagged chord-interior:

| decile of `t` | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **Litolff** (n=1,644) | **412** | 264 | 65 | 50 | 70 | 48 | 29 | 75 | **450** | 181 |
| **Breitkopf** (n=1,859) | **732** | 128 | 115 | 24 | 105 | 72 | 10 | 22 | 208 | **443** |

**Two peaks at the ends and a trough in the middle, on both plates** — 412 and
450 against 29 at the trough on Litolff; 732 and 443 against 10 on Breitkopf.
So *the head is at an end of its stem* is a measured property of these plates,
not an assumption. Distance from the head's centre to the **nearer** end, in
notehead heights: **1,180 of 1,644 (71.8%)** and **1,437 of 1,859 (77.3%)**
within half a notehead height.

## 2. THE FAULT IS REAL, AND THE TRUE OWNER IS AVAILABLE

| | Litolff | Breitkopf |
|---|--:|--:|
| notehead boxes / stem rows | 2,347 / 1,920 | 3,337 / 2,305 |
| (head, stroke) overlapping pairs | 1,759 | 1,895 |
| heads claiming exactly ONE stroke | 1,357 | 1,714 |
| **…and that stroke does not end at them** | **148** | **228** |
| far pairs where ANOTHER head claims the same stroke from an end | **153 of 169** | **231 of 246** |
| far pairs claimed by that head ALONE | 9 | 5 |

**148 and 228 heads get a confident direction from a stroke the convention
says is not theirs** — a wrong answer, not an abstention. And in **90% and
94%** of far pairs the stroke demonstrably has a head at one of its ends, so
the evidence needed to disown it is already on the record. The 9 and 5 lone
cases are a READING gap (the owner's head was never detected), not an
attribution one, and no attribution rule can reach them.

## 3. ⚠️⚠️ AND NO CONSTANT-FREE RULE SEPARATES THE TWO POPULATIONS

Three forms were priced off the record before any was written:

| rule | strips FAR pairs | strips CHORD-INTERIOR |
|---|---|---|
| **A** own iff the head's end-distance is the MINIMUM among claimants | 159/169, 238/246 | **113/115, 32/36** |
| **B** own iff nearer the head-end than the far end | 92/169, 98/246 | 51/115, 19/36 |
| **C** chain over the heads' own boxes from the end-most claimant | 145/169, 190/246 | 63/115, 22/36 |

**A takes almost every fault and destroys chords. B does neither well. C sits
between.** There is no form among them that takes the faults and leaves the
chords, and the reason is measurable: the quantity that would separate them —
the gap between consecutive heads claiming one stroke — runs **0.0 to 4.0
notehead heights on Litolff and 0.0 to 5.0 on Breitkopf, continuously, with no
empty interval anywhere on either plate.**

That is the same test that refused `_SLUR_ARC_PAD_NOTEHEADS` (*"a pad read off
it would be fitted to a wish"*) and that ADMITTED the augmentation-dot window
(bimodal, 52 at 0.00 and 52 at +0.50, nothing between). Here it refuses.

⚠️⚠️ **AND THE `chord_interior` COLUMN MAY ITSELF BE THE FAULT, WHICH IS WHY
THE PRINT IS THE INSTRUMENT.** It is computed as *this head has a claiming
mate above AND below on the same stroke* — and **three unrelated heads crossed
by one long stroke satisfy that exactly as a three-note chord does.** So the
cost column of the table above may be counting faults as costs. No arrangement
of these two records can tell them apart; a person looking at the plate can.

## 4. WHAT IS ASKED OF THE PRINT — 79 strips, pre-registered

**One question per strip:** *is the vertical stroke under the marked head THIS
head's stem, or does it belong to another note?* Verdicts:
`this_heads_stem` / `another_notes_stem` / `cannot_tell` / `not_a_notehead`.

Two strata, sampled **equally** at 20 each per document rather than in
proportion — the question is whether the LABELS are right, not how common each
is — from populations of 153 / 115 (Litolff) and 231 / 36 (Breitkopf).
**Written: 39 of 40 and 40 of 40.**

⚠️ **The sample was committed BEFORE a single strip was rendered** (`623776c7`,
against `3bac707d`), because the question is which of two populations a pair
belongs to, and choosing the pairs after seeing them would decide the answer.
The predecessor lane's own circularity — it sampled its barlines FROM the `too
TALL` bucket and then measured that they are tall — is the precedent.

⚠️ **Full-width STRIPS, not tiles**, and the mark is two red ticks in the
MARGIN rather than a box over the ink. Both are instructions from a paid-for
mistake: *"at tile magnification the adjudicator read two heads WRONG and a
wide strip corrected both — a numeral and a dotted half note each read as a
hollow head with no stem"* (09-18 handoff §3). Strips are upscaled to 100 px
per staff space with NEAREST resampling, because both plates are `bpc: 1` and
an interpolating filter would invent grey that is not on the plate.

⚠️ **Ids are opaque and the strata live in a separate manifest**, so the
adjudication can be genuinely blind.

## 5. ⚠️ TWO FAULTS IN THIS LANE'S OWN INSTRUMENT, BOTH FRAME ERRORS

1. **The frame control refused 38 of 40 crops, and was right to fire and wrong
   about the cause.** Asked inside a one-bar-wide strip of dense orchestral
   music, line-minus-space contrast collapses because the spaces in that bar
   are full of ink: Litolff p2 staff 0 reads **+12.2 in the bar and +69.7
   across the page**, its neighbours −25.6 / +100.9 and +19.7 / +89.7. The
   question the control exists to ask is page-wide. It was **not relaxed** —
   one Litolff strip is still refused, at +13.7.
2. **Every mark then landed outside its own bar**, because a `Q.GLYPH_BOX`
   row's value is CANONICAL-CELL while a crop is placed in PAGE pixels, and
   the probe was throwing away the `detail.bbox_page_px` that was sitting right
   beside it. **The fifth instance of the frame fault CLAUDE.md records**, this
   time inside a measuring instrument. Both spellings now travel with each row,
   named apart, with their conventions (`[x, y, w, h]` against CORNERS) stated
   at the site.

⚠️ **The pre-registered draw is unchanged across both repairs** — asserted row
by row against a copy taken before them, 40 of 40.

## 6. ⚠️ NOT ESTABLISHED

* **Nothing is repaired.** `adjudicate_stem_direction` is untouched; `tools/`
  has an empty diff. This measures the population and states why the obvious
  repair cannot be chosen from geometry.
* **No strip has been adjudicated.** Every number here is about the RECORD.
* **No effect on a file, and no OMR-NED figure** — the metric is symmetric and
  would pay for emitting fewer stems either way.
* n = **2 documents, 2 publishers, 8 pages, both SCANS**; the engraved family
  is untouched, and on Litolff a sibling lane measured that **~60% of noteheads
  cannot have their stem adjudicated by eye at all**, controls and sample
  alike — so a `cannot_tell` rate near that is expected there and is not a
  failure of the strips.
* The `t` and end-gap figures are computed with a **strict** box-overlap test,
  matching the shipped `_stems_on`; a looser test measures a different
  population.

## 7. WHAT WOULD SETTLE IT

The 79 strips. If `far_with_a_better_claimant` adjudicates predominantly
`another_notes_stem` and `chord_interior` predominantly `this_heads_stem`, the
two strata are real and rule **A** plus a chord rescue is worth building —
and the rescue's shape is then a question for the print too, since the gap
distribution says geometry will not supply it. If the two strata adjudicate
ALIKE, the box test is not seeing what we think it sees and the repair is
upstream, in the notehead boxes themselves.

## How to run it

```bash
export PYTHONDONTWRITEBYTECODE=1
B=benchmarks/omr-stem-attribution-2026-09
SR=/path/to/library/_shared-records
python3 $B/probe_where_along_the_stem.py --record $SR/beethoven5-p1-p4.record.json \
    --label Litolff --json $B/out/litolff.json
python3 $B/preregister.py --probe $B/out/litolff.json --label litolff \
    --out $B/out/sample-litolff.json
python3 $B/crop_strips.py --sample $B/out/sample-litolff.json \
    --record $SR/beethoven5-p1-p4.record.json --pdf <pdf> \
    --out-dir $B/out/strips-litolff --manifest $B/out/manifest-litolff.json
python3 $B/mutate.py
```
