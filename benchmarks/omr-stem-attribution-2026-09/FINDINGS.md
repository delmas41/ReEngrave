# A stroke belongs to the head at ONE OF ITS ENDS — the convention holds, and geometry alone cannot apply it

**2026-09-20.** The ranked first item of
[`docs/handoff-2026-09-18-three-lanes-and-the-print.md`](../../docs/handoff-2026-09-18-three-lanes-and-the-print.md)
§5, and `RESUME-HERE-2026-09-18`'s *"what is still owed"*. Two lanes reached
the same conclusion from different instruments on 2026-09-18 — the stroke
lane's Breitkopf DISAGREE stratum is **6 of 6 one fault, the record's notehead
box standing part-way ALONG a NEIGHBOURING note's stem**, and the beam-mate
standoff put its own error in GROUPING rather than convention. **Nothing under
`tools/` changes here.** No weights, no re-gather, no detector: every figure is
read off the two committed shared records.

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
