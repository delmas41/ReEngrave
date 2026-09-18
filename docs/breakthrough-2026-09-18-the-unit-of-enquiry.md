# The unit of enquiry is the DETECTOR'S GUESS, not the page's ink

**2026-09-18.** Four lanes ran in one night on unrelated questions — a stem
reader, a print crop pass, a width test, a stage tracer — and each ended by
naming the same thing from a different direction. This document states what they
were circling.

⚠️ **It is a HYPOTHESIS with a falsification test (§7), not a result.** What is
measured is every number it cites; what is unproven is the conclusion drawn
across them.

Read with [the stage charter](stage-charter-2026-09-18-what-each-stage-does.md),
[the diagnosis](diagnosis-2026-09-18-who-actually-decided-it.md) and
[the boxing proposal](proposal-2026-09-18-boxing-is-a-decision.md), which are
the three steps that led here.

---

## 1. THE CLAIM

**Every decision in this pipeline is filed against an address whose last
coordinate is an index into the detector's output list.**

`gather.py:330-331`:

```python
for gi, d in enumerate(dets):
    g = R.glyph(p, sys_idx, st_idx, c.measure_index, gi)
```

So the subject `glyph/1/0/2/4/1` — the address CLAUDE.md's own worked example
traces through all five stages — means, literally, **"the second thing the
detector returned for this cell."**

Everything downstream is organised around that: five stages, 28 adjudicators,
69 quantities, ten derived checks, every abstention, every recorded refusal,
every accounting identity. **They are rigorous. They are rigorous about a
population the detector invented.**

⚠️ **THE TELL IS A WORKAROUND ALREADY IN THE TREE.** `gather_ink` files its rows
at `_INK_GLYPH_BASE + i` (`gather.py:1528-1529`) — it had to **offset its
ordinals out of the detector's address space**, because the address space *is*
the detector's. The author of the ink layer met this wall and stepped around it.

## 2. WHY THIS IS NOT JUST "THE DETECTOR IS WRONG SOMETIMES"

Of course the detector errs. The claim is structural: **when it errs, there is no
subject corresponding to the real mark, and no stage can create one.** Subjects
come from GATHER, and GATHER's population is the detections. So:

* ink the detector missed has **no address**, therefore no verdict, no
  abstention, no refusal — it is not *wrongly* decided, it is **outside the
  domain of every decision in the system**;
* two marks fused into one detection have **one address** where the music has
  two things;
* one mark carved into two detections has **two addresses** where the music has
  one thing;
* and a stage that abstains is abstaining **about the detector's guess**, not
  about the page.

**A carefully recorded "cannot tell" about a subject that does not correspond to
anything is not humility. It is precision aimed at the wrong object.**

## 3. ⚠️⚠️ IT EXPLAINS FOUR LANES AT ONCE, WHICH IS WHY IT IS WORTH STATING

Every one of these was measured independently, by a different instrument, with
no knowledge of the others:

| what a lane found | why this claim predicts it |
|---|---|
| **A width read off the detector's box can catch the detector contradicting itself but can never corroborate its class** (`omr-notehead-width`) | the box and the class are **one assertion**, because the box is the extent *of the hypothesised class*. Measuring the subject cannot test the subject. |
| **46 of 180 boxes are not noteheads** — barlines, a capital **B**, the `e` of *cresc*, **the two round counters of a printed time-signature 8** (`omr-stem-crop-pass`) | the counters are the decisive case: the boundary is wrong in the *other* direction, a **sub-part carved out of a bigger glyph**. Nothing inside the box disagrees; only the surrounding **ink** does. |
| **The width cap discards 217/345 stems because the box measures stem + notehead fused** (`omr-stem-ink`) | one address for two marks. The filter is not wrong about the extent it was given; **it was given the wrong extent.** |
| **The stroke IS separable inside a fused blob — 92.1% / 73.6%** (`omr-stem-stroke`) | the information was on the page all along. What was missing was **a subject to file it against.** |
| **The beam-mate tier loses 16-0, and its failures are 6-of-6 one fault: the notehead box stands part-way ALONG a neighbouring note's stem** (`omr-stem-crop-pass`) | a boundary error presenting as a *direction* error. The tier reasons correctly about a mis-addressed thing. |
| **2,377 places where a stage says `no_ink` and the ink layer shows ink** (`omr-stage-trace`) | `no_ink` is computed over **detections**. It means *"no detection of my kind here"* and says *"no ink"* — the population confused for the page. |
| **A filter-rejected stem candidate is recorded as `NO_INK`** (`gather.py:1305`) | same, one layer down: a candidate the pipeline **found and discarded** leaves no row, so absence-of-subject is reported as absence-of-ink. |
| **All ten derived checks are aggregate and static; none can be given a subject** (`omr-stage-trace`) | they verify the wiring **between subjects**. They cannot see that the subjects are wrong, because the subjects are their axis. |

⚠️ **One finding is NOT explained by it, and saying so matters**: on Litolff
**988 of the refused noteheads are `staff_not_identified` + `no_pitch`, both
ZERO on Breitkopf** — notes gathered, decided, pitched and arbitrated, absent
only because **nobody could name the staff.** That is an *identity* shortfall,
not a segmentation one, and it is `OMR_HOLD_OUT_UNIDENTIFIED` working exactly as
designed. **A single-cause story would have swallowed it; this one does not.**

## 4. WHAT SEAN HAS BEEN SAYING, AND WHAT IS ACTUALLY NEW

He has stated the conclusion for months and it is already in this tree:

> *"Ink is ink. There is nothing that should be classified as unseen — only
> unclassified."*
> *"GATHER collects it without naming or categorizing it… all information about
> anything on the page without declaring what it is, and it should make that
> information available to all stages."*
> *"Is boxing something a decision? We are sending something forward that
> already has a declaration."*

**What is new is not the principle. It is four things:**

1. **The MECHANISM by which the current arrangement defeats it** — subject
   identity. Not "we should also gather ink" but *"the ink cannot be reasoned
   about, because reasoning is addressed to detections."*
2. **The measured evidence**: 2,377 false empty claims on one record; 46 of 180
   boxes not noteheads; boundary failures dominating every census bucket; and
   the separability result showing the information was present.
3. **That `Q.INK` already IS the alternative population** — exhaustive, on by
   default, **read by nothing** — which is why it kept arriving as the answer to
   four unrelated questions.
4. **That the stages are not the problem.** They are careful, they abstain, they
   correct each other, they balance. Sean's worry that *"the complexity is
   making our readings very bad"* is, on this evidence, **not right in the way
   he feared**: the complexity is sound and is pointed at the wrong population.

## 5. WHAT FOLLOWS — invert the relationship

**Today**: the detection is the subject; the ink is invisible.
**Proposed**: **the ink is the subject; the detection is an OPINION about it.**

A detection becomes a row *filed against a piece of ink*, saying *"a notehead
of this extent, at this confidence"* — one of possibly several opinions, none
privileged, all revisable. Then:

* *"is this a notehead?"* becomes a real question with a real subject, and can
  ABSTAIN — which it cannot today, because the answer is the subject's name;
* a **merge** is one ink subject carrying two opinions; a **carved sub-part** is
  one ink subject whose opinions cover part of it; a **missed mark** is an ink
  subject with **no** opinion — *visible for the first time*;
* the layer-1-versus-layer-2 comparison becomes available, which is a genuine
  two-witness test (raster against model) where a second measurement of the box
  never was.

## 6. ⚠️⚠️ THE STRONGEST COUNTER-ARGUMENT, AND IT IS NOT FATAL BUT IT IS REAL

**The ink is also badly segmented.** This repo measured it: *"Litolff MERGES and
Breitkopf SHATTERS, and neither plate gives one row per mark"* — the median
Litolff cell's largest component holds **46%** of its ink, and **56%** of
Breitkopf's rows are specks. A connected component is not a mark.

**So making ink the subject replaces one wrong segmentation with a different
wrong segmentation.** That must be said plainly, because a document that
promised otherwise would be selling something.

**Why it is still the better foundation, and the reason is not accuracy:**

1. **It is EXHAUSTIVE.** Nothing is discarded, so nothing is outside the domain
   of enquiry. A wrong boundary can be revisited; **a row that was never created
   cannot be.**
2. **It is UN-OPINIONATED.** It carries no name, so it cannot make the
   name-and-boundary into one unfalsifiable assertion.
3. **It REPORTS ITS OWN UNCERTAINTY.** `Q.INK` already carries
   `ink_n_components` and `ink_share_of_cell` **as a merge warning rather than
   repairing the merge** — the one place in the codebase where a segmentation
   decision declines itself and says so. That is the property the detector's box
   lacks entirely.

**The claim is therefore not "the ink is correct." It is that the ink is
HONEST** — and an honest wrong boundary is a thing later stages can work on,
which is exactly the difference the whole staged architecture exists to
preserve.

## 7. THE FALSIFICATION TEST — ⚠️⚠️ RUN THE SAME DAY, AND IT DID NOT HOLD AS WRITTEN

⚠️⚠️ **RESULT, 2026-09-18, a few hours after this section was written: the
prediction below is NOT SUPPORTED on Litolff.** Joined to the crop pass's 106
blind print verdicts, **confirmed noteheads and confirmed non-noteheads BOTH
come back `MERGE_TALL`** — `AGREES` 0.074 against 0.143. **The table is
undifferentiated, which is the condition this section itself named.** There is a
ratio signal in the right direction (junk at a median ink/box area of **14.93**
against real heads' **6.01**) but it is a continuum, n = 14 on the junk side,
and the shape cuts were invented. Full record, with its four controls and the
two bugs they caught:
[benchmarks/omr-ink-extent-2026-09/FINDINGS.md](../benchmarks/omr-ink-extent-2026-09/FINDINGS.md).

⚠️ **WHY it fails is already on record: Litolff MERGES.** A *real* notehead's
component is >3× its box on **59%** of confirmed heads, because the head is
fused to its stem and beam — **on a plate where nearly every component is a
merge, "is this a merge?" cannot discriminate.** The test's natural home is the
SHATTERING plate, and **the Breitkopf record predates `OMR_INK`, so it cannot
be run there at all.** That is now the blocking artefact, and it is one gather.

⚠️⚠️ **AND THE METHOD FINDING CUTS AT THIS DOCUMENT: THE TEST WAS RUN
BOX-FIRST, WHICH IS THE ARRANGEMENT §1-§5 ARGUE IS WRONG.** Every row starts
from a box and asks what ink is under it — so the test inherited the defect it
was meant to examine. **Asked from the ink instead**, the same record is highly
structured: **42.5%** of ink pieces have **zero** detections overlapping them,
**49.2%** are explained <5% (**36% of all ink AREA**), **22.7%** are claimed by
**more than one** detection, and coverage is **BIMODAL** (p25 0.000, median
0.062, p75 0.804) — the detector either sees a piece of ink or it does not.
⚠️ **Those figures QUANTIFY THE GAP; they do not validate the framing.**
`Q.INK` filters nothing, so much of that 42.5% is specks and staff residue, and
**the shape/size split is not done.** So this document's core claim stands
**neither confirmed nor refuted**, and the honest next test is the ink-first
one with a residue split and a print join.

⚠️ Two bugs the controls caught, both predicted by this document's own §6:
`glyph_box.value` is `[name, x, y, w, h]` while `ink_bbox_canonical` is
`[x0, y0, x1, y1]` — **opposite conventions in one record**, and read alike a
notehead's width comes out **−108 px**, producing a clean believable
`NO_INK_UNDER_BOX` on 100 of 106; and an earlier draft joined **Breitkopf**
verdicts to the **Litolff** record where **11 of 26 subjects "matched"** by
coincidence, **because a subject's last coordinate is a positional index** —
the breakthrough's point arriving as a bug in its own test.

### The prediction as originally written, kept for the record



**If this framing is right**, then comparing the ink extent against the
detector's box should sort the *already-adjudicated* failures into distinct,
countable shapes:

* ink extent **≫** box → a **MERGE** (the fused stem: 217 / 345 heads)
* box claims a notehead over a long thin run → a **BARLINE** (459 of 476)
* ink extent **⊃** box, surrounding component is a digit → a **CARVED SUB-PART**
  (the eight time-signature counters)
* many ink components inside one box → a **SHATTERED** mark (Breitkopf's specks)

⚠️ **IF THAT TABLE COMES BACK UNDIFFERENTIATED — if the disagreement does not
separate cases the print has already settled — THE FRAMING IS WRONG** and the
detector's box is as good a subject as the ink. That is a real risk: both
populations are badly segmented, and it is possible neither dominates.

**It needs no new threshold, no routing change, no default, and no re-gather
beyond one.** It is `Q.INK`'s first consumer, it changes no value, and it is the
cheapest decisive experiment available.

## 8. ⚠️ WHAT THIS DOES NOT CLAIM

* **Not measured.** §7 is a prediction from print evidence, not a result.
* **It does not say the detector should be replaced**, or that boxes are wrong
  everywhere — they are demonstrably fine for noteheads on clean engraving
  (**856 of 856**). The narrow claim is that **a box cannot carry a merge, a
  split, or a sub-part**, and that on these plates those are the common cases.
* **It does not say the stages are wasted.** The opposite: they are the part
  that works, and repointing them is the whole proposal.
* **It does not price anything.** Inverting the subject population would touch
  routing-by-class across every family — the largest change this codebase could
  undergo — and record size is already **0.6-3.1 MB/page** for the ink layer
  alone. **§7 is deliberately the version that costs nothing.**
* **n = 2 publishers, 8 pages, one adjudicator**, and on the Litolff plate ~60%
  of noteheads cannot be adjudicated by eye at all. **No OMR-NED figure**,
  deliberately.
