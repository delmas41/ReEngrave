# The page frame: Sean's barline test was UNAVAILABLE, and it is now AVAILABLE and POSITIVE

**2026-09-20.** The ranked next work of
[`benchmarks/omr-vertical-runs-2026-09/FINDINGS.md`](../omr-vertical-runs-2026-09/FINDINGS.md)
§3, taken. That lane made Sean's rule computable, got **0 of 19** print-settled
barlines firing at any tolerance while **6 of 58** adjudicated stems did — *"the
test is faintly BACKWARDS"* — and then diagnosed it: the runs are measured
inside a MEASURE CELL, whose reach is the staff plus 4 + 4 staff spaces, so a
barline taller than that has its ends clipped BY the crop. **It ranked a page
reader on the `cv_hairpins` precedent.** This is that reader, and the answer
changes.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN
**ASSUMED**, his own: *"Bar lines are the length of a staff or they extend to
other systems."* **FALSIFIER**: a print-adjudicated barline whose ends are not
on outer staff lines, or an adjudicated stem whose ends are. Both measured
against the crop pass's blind print verdicts — the SAME population, the SAME
tolerance sweep and the SAME two forms of the rule as the predecessor, so the
delta is attributable to the WINDOW and to nothing else. ⚠️ **NOT CONFIRMED**:
the tolerance (swept, reported as a curve, never set), and whether a BRACKET or
a SYSTEMIC barline belongs in the same population as a bar-dividing one.

## 1. ⚠️⚠️ THE RESULT: THE TEST FIRES ON BARLINES AND ON NO STEM AT ALL

Sean's rule in its WIDE form (*"or they extend to other systems"*), against the
print, pooled over both publishers — **cell frame from the predecessor, page
frame from this lane**:

| tolerance (staff spaces) | 0.15 | 0.25 | 0.40 | 0.60 | 1.00 |
|---|--:|--:|--:|--:|--:|
| **barlines fire** — CELL frame (of 19) | 0 | 0 | 0 | 0 | 0 |
| **barlines fire** — PAGE frame (of 19) | **2** | **11** | **12** | **13** | **18** |
| **stems fire** — CELL frame (of 58) | 0 | 0 | 0 | 0 | 6 |
| **stems fire** — PAGE frame (of 63) | **0** | **0** | **0** | **0** | 11 |

**Between 0.25 and 0.60 staff spaces the rule fires on 11-13 of 19 print-settled
barlines and on ZERO of 63 print-settled stems.** In the cell frame that band
was 0 and 0 — no signal in either direction. The window was the whole of it.

Per publisher, the wide form, barlines / stems:

| | 0.15 | 0.25 | 0.40 | 0.60 | 1.00 |
|---|---|---|---|---|---|
| **Litolff** (7 barlines, 22 stems) | 0 / 0 | 2 / 0 | 2 / 0 | 3 / 0 | 7 / 4 |
| **Breitkopf** (12 barlines, 41 stems) | 2 / 0 | 9 / 0 | 10 / 0 | 10 / 0 | 11 / 7 |

⚠️⚠️ **THE BARLINE HALF INHERITS THE PREDECESSOR'S CIRCULARITY AND THE STEM
HALF DOES NOT.** The crop pass sampled its barlines FROM the `too TALL` bucket,
so *"these marks are tall"* is true by construction, and a rule that fires on
tall marks is being scored on a population selected for being tall. **The
decisive column is therefore the STEM one**, which is not circular (sampled
across all six buckets, 1 of 58): **0 of 63 at every tolerance below 1.00, in
both frames.** The honest statement of the result is *the rule now separates,
and its false-positive side is empty*, not *it recovers 12 of 19 barlines*.

⚠️ **THE NARROW FORM IS STILL 0 OF 19, IN BOTH FRAMES AND BOTH PUBLISHERS**,
and that is informative rather than a failure: none of the adjudicated barlines
sits on exactly one staff. It is the same selection effect — the `too TALL`
bucket is, by definition, marks that cross staves — so **this lane establishes
nothing about a one-staff barline**, which is the commonest kind on the page.

⚠️⚠️ **AND A SIBLING LANE SAYS HOW UNCOMMON THE KIND MEASURED HERE IS.**
[`omr-barline-height-2026-09`](../omr-barline-height-2026-09/FINDINGS.md) counts
82 Litolff barlines of which **7 cross every inter-staff gap** (all of them a
system's FIRST) and 49 Breitkopf ones of which **4 do** — so the marks this
lane's print sample is drawn from are roughly **8% of the barlines on the
page.** Its own §4 names this work in advance: *"any future endpoint-based
barline rule needs a page-band reader, not this data."* That is the reader; the
93% it does not speak for is §6's first item.

## 2. THE DECISIVE CONTROL: the crop signature is gone, and it can be seen to return

The predecessor's fault has an exact signature: end offsets of **−4.00 / +4.00**
staff spaces, `PAD_ABOVE_STAFF_LINES` / `PAD_BELOW_STAFF_LINES` to two decimals
on both publishers. If it survived here, the reader would not be reading the
page and nothing in §1 would be readable.

| runs over 8 spaces | n | d_top median | d_bot median | ends at ±4.00 |
|---|--:|--:|--:|--:|
| Litolff | 327 | **−0.06** | +26.25 | **0** |
| Breitkopf | 156 | **−0.15** | +38.70 | **0** |
| Litolff p1, `--clip-like-a-cell` | 48 | −0.12 | **+4.00** | **48** |

The top end is now the INK's (−0.06 / −0.15 spaces from the staff's own top
line, i.e. on it) and the bottom end runs tens of spaces down the page, which is
what a mark crossing staves does.

⚠️⚠️ **AND THE CONTROL WAS TESTING FOR SOMETHING THAT CANNOT HAPPEN HERE,
WHICH A MUTATION BATTERY FOUND.** The signature is a PAIR, and the pair is an
artefact of per-cell DUPLICATION: one barline appears in every cell it crosses,
and the middle copies are cut at BOTH ends. A page reader emits the mark ONCE,
so even with the cell's window deliberately re-imposed only the FAR end is cut —
measured, `d_bot` returns to exactly 4.00 while `d_top` stays at the ink. So
testing for the pair read **zero under the fault as well as under the repair**.
Widened to EITHER end: **0 under the repair, 48 of 48 under the reproduced
fault.** A control that has never been seen to fire is indistinguishable from
one that cannot.

## 3. Reach, and a number the cell frame could not report

| | page runs | `Q.STEM` strokes | cell-frame candidates (predecessor) | reader time |
|---|--:|--:|--:|--:|
| Litolff pp.1-4 | **3,465** | 1,920 | 6,128 | **0.0-0.1 s/page** |
| Breitkopf pp.0-3 | **4,536** | 2,305 | 6,816 | 0.1 s/page |

⚠️ **THE CELL POPULATION IS NOT 1.8x LARGER, IT IS DOUBLE-COUNTED.** Measure
cells overlap by 4 + 4 staff spaces, so a mark in the gap between two staves is
a candidate in BOTH, and a tall one is a candidate in every cell it crosses.
6,128 against 3,465 is that duplication, not more ink found. **The page frame
is the first count of vertical marks on these pages that is a count of MARKS.**

⚠️ **COST: none that lands anywhere.** This reader writes no record row, so
there is no 0.96-1.11 MB/page to weigh as there was for `Q.VERTICAL_RUN`; the
whole of it is ~0.1 s/page on top of a re-cut that costs 3-6 s/page. That is a
property of it being a READER with no producer — and the day it gains one, that
cost argument returns.

**How many staves a run spans** — the quantity a cell frame cannot express at
all, because a cell is one staff:

| spans | 0 | 1 | 2-4 | 5-9 | 11-14 |
|---|--:|--:|--:|--:|--:|
| Litolff | 371 | 2,773 | 274 | 31 | 16 |
| Breitkopf | 462 | 3,931 | 10 | 126 | 7 |

The 16 Litolff runs spanning 11-12 staves and the 7 Breitkopf ones spanning
13-14 land on exactly the staff counts those pages' SYSTEMS have (Litolff 12
and 11; Breitkopf 14 and 13-14) — which is a match of counts and not an
identification. ⚠️ **NOT PROPOSED AS A RULE**: they are reported
because the number exists now, and nothing here says a run spanning a system is
a barline rather than a bracket. That is the question §5 leaves open.

## 4. The controls, each able to fail

* **CROSS-READER**: every stroke `detect_stems` accepted must have a page run
  over it, or nothing above is a result about barlines. **1,920 of 1,920 and
  2,305 of 2,305 — 100% on both.** ⚠️ It sits at its CEILING, so it can only be
  seen to fail in the blinded state, which is why it is computed BEFORE the
  DEAD exit. Blinded: 0 of 190.
* **DEAD AT ZERO REACH**: `--blind-the-reader` hands the reader a blank render
  of the same page; it returns 0 runs and the arm exits 2 saying so.
* **§2's POSITIVE CONTROL**: `--clip-like-a-cell`, above.
* **MUTATION BATTERY**: **17 arms, 17 RED, 0 survivors, 0 bad anchors, restore
  md5-verified**, two subjects (the reader, judged by the unit suite; the arm,
  judged by its own headline over all three runs) and a green baseline first.
  ⚠️ **Its first run had FOUR survivors and only one was a test gap** — the
  other three were controls at their ceiling, §2 and the bullet above; the gap
  was that nothing asserted what the kernel's HEIGHT buys, so shrinking it back
  to one staff space (the pre-2026 stem bug, where a notehead survives the
  opening and the component comes out as wide as the HEAD) left the suite green.

## 5. ⚠️ NOT ESTABLISHED

* **Nothing is NAMED.** This reader returns vertical ink with coordinates and a
  length. It does not say barline, stem or bracket, and no adjudicator reads it.
  The test firing is evidence that the FACT is now available, not that anything
  uses it.
* **The one-staff barline is untouched** (§1), and it is the common case.
* **The barline half of the print join is circular** (§1), inherited.
* **n = 2 documents, 2 publishers, 8 pages, one adjudicator, both SCANS.** The
  engraved family is untouched.
* **No record changed and no file moved.** No OMR-NED figure is claimed,
  deliberately — nothing here reaches an export.
* **The page frame is 6.5x COARSER than the canonical cell frame** — 16 page px
  per staff space on Litolff against ~100 canonical — so this reader works at a
  resolution the cell path does not. The cross-reader control says it is not
  blind at that resolution (100% on both); it does not say the BOXES are as
  precise, and a length measured here is a page-frame length.
* **The staff lines are not erased** for this reader (no page-level erased
  raster exists, and a vertical opening removes a horizontal line by
  construction). Every run says so. The two readers see different images and
  that is recorded rather than assumed away.

## 6. The ranked next work

1. **The one-staff barline.** A crop pass sampling from the ACCEPTED bucket and
   from the `too WIDE` bucket — never again from `too TALL` — is what would
   remove the circularity and reach the common case. It is a print pass, not
   code.
2. **A quantity, once something reads it.** `Q.VERTICAL_RUN` is producer-only
   and costs 0.96-1.11 MB/page; a page-frame sibling would cost less (no
   duplication) and is worth filing only when a decision consumes it. The
   consumer this lane makes possible is *is this vertical mark a barline*, and
   the evidence it would take — ends on outer staff lines, staves spanned — is
   exactly what §1 and §3 now measure.
3. ⚠️ **It also bears on `measure_extractor`'s barline detection**, which finds
   barlines by a per-staff column scan and a fitted line. Whether a page-frame
   run set agrees with it is unasked here and is a cheap comparison.

## How to run it

```bash
export PYTHONDONTWRITEBYTECODE=1
python3 benchmarks/omr-vertical-runs-page-2026-09/page_run_arm.py \
  --pdf library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf \
  --pages 1,2,3,4 \
  --crop-rows benchmarks/omr-stem-crop-pass-2026-09/out/litolff-rows.json \
  --crop-manifest benchmarks/omr-stem-crop-pass-2026-09/out/crop-manifest-litolff.json \
  --crop-adjudication benchmarks/omr-stem-crop-pass-2026-09/ADJUDICATION-litolff.json \
  --label "Litolff Beethoven 5 pp.1-4" --json out/litolff.json
```

⚠️ **NO WEIGHTS ARE NEEDED**, and the detector never runs. It needs `library/`
(the PDF) and ~15-25 s per four pages, essentially all of it the re-cut.
`--blind-the-reader` and `--clip-like-a-cell` are the two positive controls.
