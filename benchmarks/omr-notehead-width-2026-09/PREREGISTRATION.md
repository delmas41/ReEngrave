# PRE-REGISTRATION — the notehead WIDTH test

**Committed BEFORE any width was computed.** Commit order is the only form of
this claim a later reader can check (the precedent is the crop pass's
`cc24eaad`). Nothing below was written with a number in hand.

---

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

**CONVENTION ASSUMED** — two entries of `docs/engraving-conventions.md`, and
the second is filed there as **LITERATURE ONLY, untested on any plate**:

* `[C1 + L3]` *A notehead is one staff space tall* — and its own numbers give
  the width as well: Bravura `noteheadBlack` / `noteheadHalf` **1.180 × 1.000**
  staff spaces, `noteheadWhole` **1.688 × 1.000**. So a notehead is **wider
  than it is tall**, and roughly **1.18 spaces wide** unless it is a whole
  note. ⚠️ That entry's rigidity row says the height is RIGID and the **width
  is font- and era-variable** — so width is the WEAKER half of that convention
  and this job must not pretend otherwise.
* `[L4]` *A whole notehead is wider than a black one, and the same height* —
  which predicts, in its own words, that *"width, not height, separates a whole
  note from a half note … A reader distinguishing hollow heads should use width
  and the presence of a stem, **never height**."* ⚠️ The registry records that
  **both** discriminators it names are unmeasured here, **while the one it
  rules out (height) is what the repo's shipped `OMR_WHOLE_REST_INK` band is
  expressed in.**

**HOW A HUMAN WOULD READ IT.** An editor with the plate does not measure
anything: a notehead is an oval about as wide as the space it sits in, and a
**barline, a rest, a clef, a letter of a printed word** are not oval and are
not that shape. The crop pass found 46 of 180 sampled "noteheads" to be exactly
those things. The mechanical form of *"that is not a notehead"* which is
cheapest to compute is **it is too NARROW to be one** — a barline is a
fraction of a space wide where a head is more than a space.

**WHAT WOULD FALSIFY IT**, stated three ways, each checkable:

1. **The convention itself** — a plate whose genuine noteheads are NOT ~1.2–1.7
   spaces wide, i.e. a width distribution over the heads we read CORRECTLY that
   is not concentrated there.
2. **`[L4]`** — a plate where whole and half heads measure **the same width**
   (the registry's own falsifier for that entry).
3. **The TEST** — the floor is not worth having if a material share of the
   heads the pipeline reads correctly fall below it. **Pre-registered bar: if
   more than 2% of the `decided` population sits under 1.0 staff spaces, the
   floor is NOT free** and must be reported as a cost, not a filter.

**NOT CONFIRMED WITH SEAN.** Nothing here was put to him. He chose this job
and said *"I feel like the previous issues (1 and 2) will be affected by
this"*; he has not been asked whether the width convention holds on his plates,
nor whether a narrow box should be refused, recorded, or both.

---

## WHAT IS MEASURED, AND ON WHAT

The population is **every `notehead*` glyph box on both shared records** — not
a sample, so there is no drawn set to register. What is registered instead is
the **decision rule and the thresholds, fixed in advance**:

* **Threshold: 1.0 staff spaces**, inherited unchanged from
  `benchmarks/omr-stem-crop-pass-2026-09/FINDINGS.md` §2 (*"a floor at width <
  1.0 spaces catches 39 of the 46 at a cost of 0 of 63 real stems"*). It is
  **not fitted here** and will not be moved to improve any number; the full
  distribution is reported so a later reader can see whether it sits on a
  plateau, an empty interval, or a slope.
* **Two independent rulers, both reported.** `glyph_box.value[1:5]` is a
  CANONICAL **width-box** `(x, y, w, h)` divided by that cell's own
  `cell_staff_space`; `glyph_box.detail.bbox_page_px` is a PAGE **corner-box**
  `(x0, y0, x1, y1)` divided by that staff's `staff_spacing`. ⚠️ Those two
  conventions differ and the handoff records a session losing time to exactly
  that (*"measure bbox = CORNERS, detection bbox = WIDTH"*). If the two rulers
  disagree, **the finding is the disagreement** and no headline is taken.
* **Reported APART by publisher, never pooled.** The contamination differs 7×
  between the two plates (5.5% vs 37.7%) and nothing says which is typical.

## THE THREE QUESTIONS, in the order they will be answered

1. **REACH / FALSE POSITIVES.** What share of the population the pipeline reads
   CORRECTLY (`stem_direction` decided) falls under the floor? This is the
   open side the crop pass declared: its test was measured *only* on heads the
   census already abstains on.
2. **`[L4]`.** Do `noteheadWhole*` boxes measure wider than
   `noteheadBlack*`/`noteheadHalf*` on a real plate, and is there a separating
   interval?
3. **CONTAMINATION IN ISSUES 1 AND 2** — Sean's own reason for choosing this
   job. How much of the beam-mate tier's measured disagreement, and of
   `OMR_STEM_STROKE`'s measured reach, is a box that is not a notehead?

## WHAT THIS CANNOT DO, written before it is run

* **It cannot tell a narrow box from a real notehead by looking.** Width is a
  proxy; the print is the truth, and the print was consulted by the crop pass
  on **180 boxes**, not by this job on any. Every claim of the form *"this is
  not a notehead"* rests on that sample of 180 and inherits its n.
* **No re-gather.** Everything is read off the two committed records and the
  lanes' committed per-head rows, so **any GATHER change is priced by nothing
  here** and `readjudicate` / `reexport_arm` are structurally blind to it.
* **No OMR-NED**, deliberately — the metric is symmetric and would pay for
  emitting fewer noteheads whether or not they were noteheads.
