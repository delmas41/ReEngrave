# Pre-registered criterion — does POSITION separate classes?

Committed **alone and first**, before any separation number was computed, on
this repo's own standing rule: *"the categories must be fixed before looking or
the count fits itself to what was found."*

The store this benchmark exists to justify is a **position-keyed** accumulator:
*where do things actually fall*, conditioned on publisher, so that a later stage
can ask **"what sorts of things are likely HERE?"** of an unnamed blob.

**If position does not separate classes, the store is a well-engineered
container for noise and that is the finding.** This file fixes what would count
as each answer before the answer is known.

---

## THE QUESTION

Does a mark's **staff-relative vertical position** carry information about
**what the mark is**?

Position is `(y_center_page − y_of_top_staff_line) / half_staff_space`, i.e. the
same clef-free quantity `Q.NOTEHEAD_STAFF_POSITION` already records for
noteheads, computed here for every family. It is chosen because it is the one
positional quantity that **composes across documents** — a `bbox_page_px` is a
fact about one page at one dpi and pools with nothing.

## THE INSTRUMENT

Mutual information `I(bucketed position ; class)` in bits, over detected glyphs
from committed staged records.

MI is **biased upward** by bucket count, which is precisely why the null below
is the only thing that may be quoted.

## THE NULL

**Shuffle the class labels within publisher**, preserving the position
distribution and the class marginals exactly, and recompute. Repeat for
≥ 20 seeds. This is the shape the onset-column work used: destroy only the
association under test, keep every other property of the data.

Report `I_observed`, `mean(I_null)`, `sd(I_null)`, and the margin in units of
the null's sd.

## PRE-REGISTERED OUTCOMES

**POSITIVE** — the store is measuring the music — requires ALL of:

1. `I_observed − mean(I_null) > 5 · sd(I_null)`, and
2. the effect holds **independently in both publishers** (Litolff and
   Breitkopf), not only pooled, and
3. it is **not carried by a single class** — removing the single
   highest-contributing class leaves the margin above 5 sd.

**NEGATIVE** — the store is a container for noise — if the margin falls inside
the null's range, or if it appears in one publisher and not the other.

**PARTIAL** — reported as such and NOT as a positive — if 1 and 2 hold but 3
fails. In that case the honest statement is *"position separates ONE family,"*
and the per-class table is the result rather than the pooled number.

⚠️ **The per-class table is reported whatever the pooled number does.** A
pooled positive carried by clefs says nothing about whether the store can help
with an unnamed blob in the middle of a bar. Concentration is reported per
class, always.

## BUCKET SIZE IS A MEASUREMENT, NOT A GUESS

Report the margin as a function of bucket width across at least a decade of
widths (≈0.05 → ≈4.0 staff spaces). **Choose the width where the margin
plateaus**, and say where it is. Too coarse and classes stop separating; too
fine and every bucket holds one observation and MI measures the sample.

## ⚠️ THE CONFOUND, NAMED IN ADVANCE

The class label here is the **DETECTOR's**, and the detector is one classifier
over the same raster. If the detector has its own positional bias, part of any
measured separation is **the detector agreeing with itself** rather than the
music. This is the `source_kind` hazard in a new place.

So the OBSERVED tier can establish that position separates *the detector's
classes*; it **cannot** establish that position separates *what is printed*.
A `TRUE` tier — positions from `page_truth.py`'s rendered ground truth, known
by construction — is the control, and any claim about the music rather than
about our reader must be made there.

**Pre-registered:** if OBSERVED is positive and TRUE is unavailable or
unmeasured, the finding is stated as *"position separates the detector's
classes"* and not more.

## WHAT WOULD MAKE THE WHOLE THING VOID

- The two records carry **zero `Q.INK` rows** (they predate `gather_ink`), so
  the UNKNOWN half of the store has no population here. Reach for unnamed ink
  is expected to be **0** and must be reported as 0 rather than quietly
  omitted — a store that cannot hold the case it was built for is the finding.
- Fewer than two publishers reachable.
