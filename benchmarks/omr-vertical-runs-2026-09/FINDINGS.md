# `Q.VERTICAL_RUN` — the refused population arrives, and Sean's barline test is UNAVAILABLE rather than refuted

**2026-09-18.** Built because Sean asked whether the stages hold what is needed
to tell one kind of vertical line from another, and the measured answer was
**no**, for two fixable reasons. ⚠️ **The findings file was refused to that lane
— the FIFTH refusal of the day** — so this is its text transposed at
integration; **[mgr]** marks what the managing session re-derived.

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN
**ASSUMED**, his own: *"Bar lines are the length of a staff or they extend to
other systems"*; *"Length is helpful in all of them except stems."*
**FALSIFIER**: a print-adjudicated barline whose ends are not on the outer
lines, or an adjudicated stem whose ends are. **Both measured against the crop
pass's blind print verdicts.** ⚠️ **NOT CONFIRMED**: the TOLERANCE (swept and
reported as a curve, never set — the plate's warp makes it unreadable off the
print), and whether a **bracket** or a **systemic** barline belongs in the same
population as a bar-dividing one.

## 1. Flag-off reproduces BOTH records exactly — the requirement that protects every sibling arm

| | record | re-cut flag-OFF | cells disagreeing | flag-ON moves |
|---|--:|--:|--:|--:|
| **Litolff** Beethoven 5 pp.1-4 | **1,920** | **1,920** | **0** | **0** |
| **Breitkopf** Brahms 1 pp.0-3 | **2,305** | **2,305** | **0** | **0** |

**[mgr] re-derived from the committed output.** Candidates leave through an
append-only out-parameter; `detect_stems`' return, control flow and filter order
are untouched. ⚠️ The arm ABORTS rather than reporting against a moved baseline
— and its own first run refused **for the wrong reason** (`190 = 1920` on a
one-page re-cut of a four-page record). *A control that refuses for the wrong
reason is indistinguishable from one that refuses for the right one.*
⚠️ **Flag-ON renumbers later row ids** (a running counter, as with `Q.INK`), so
byte-identity is claimed **only for OFF**.

## 2. Reach and cost

| | candidates | `Q.STEM` | refused by a DIMENSION bound | MB/page |
|---|--:|--:|--:|--:|
| Litolff | **6,128** | 1,920 (31.3%) | 3,964 (**64.7%**) | **0.96** |
| Breitkopf | **6,816** | 2,305 (33.8%) | 3,724 (**54.6%**) | **1.11** |

**The record was carrying about a third of the population the pipeline looked
at.** ⚠️ **THE COST IS REAL — 1.6-2× the ink layer**, ~15 MB over a sixteen-page
movement. **A genuine argument against the default ever flipping**, and the
honest statement is that the rows are worth their size only once something reads
them, and nothing does.

## 3. ⚠️⚠️ SEAN'S BARLINE TEST IS NOW COMPUTABLE, AND IT IS A CLEAN NEGATIVE

| | joined | fires at 0.15 / 0.25 / 0.40 / 0.60 / 1.00 spaces |
|---|--:|---|
| Litolff adjudicated **barlines** | 7 | **0 / 0 / 0 / 0 / 0** |
| Litolff adjudicated **stems** | 22 | 0 / 0 / 0 / 0 / **2** |
| Breitkopf adjudicated **barlines** | 12 | **0 / 0 / 0 / 0 / 0** |
| Breitkopf adjudicated **stems** | 41 | 0 / 0 / 0 / 0 / **4** |

**19 of 19 print-settled barlines fire at NO tolerance, while 6 of 58
adjudicated STEMS do — the test is faintly BACKWARDS.** ⚠️ The **WIDE** form
(Sean's *"or they extend to other systems"*) was operationalised and **reads
identically**, widened **before** the negative was reported, per his own S4
instruction.

### ⚠️⚠️ THE DIAGNOSIS IS THE RESULT: THE CELL CLIPS THE BARLINE

Signed end offsets in staff spaces (`+` = below the line):

| outcome | n | d_top median | d_bot median |
|---|--:|--:|--:|
| accepted | 1,920 | **−0.24** | **−0.30** |
| **too TALL** | 1,866 | **−4.00** | **+4.00** |
| paired (accidentals) | 244 | +0.24 | −0.11 |

**−4.00 / +4.00 is exactly `PAD_ABOVE_STAFF_LINES` / `PAD_BELOW_STAFF_LINES`,
reproduced to two decimals on BOTH publishers.** **[mgr] verified:
`measure_extractor.py:44-45` reads `= 4` and `= 4`.** Those runs span the whole
crop, and **ten of the nineteen barlines read `h = 12.00` exactly — 4 + 4 + 4
staff spaces, the cell.**

> **A barline taller than the cell has its ends clipped BY the cell, so its
> endpoints are the CROP's and not the staff's. Sean's test is structurally
> UNAVAILABLE on the staged path — it is NOT refuted.**

`probe_can_a_cell_hold_two_staves.py` proves it structurally off the records'
own `Q.STAFF_LINES` with no re-cut: the next staff's top line is inside the
cell's 4.0-space reach on **4 of 71** Litolff pairs and **35 of 93** Breitkopf.

**The fix is the `cv_hairpins` precedent** — read the runs off a **staff BAND
across the page**, *"so its hairpins are never cut by a barline."* A new reader,
not a threshold. **Ranked next work.** Same family as *a slur is drawn OVER its
notes and a hairpin BETWEEN them*, where a sound overlap test scored 0 of 4 on
perfectly good evidence.

⚠️ And the 6 false-firing stems are 4.12-5.46 spaces, mostly `too WIDE` — the
coincidence exactly: **a one-staff barline is 4.0 spaces, at the median of the
stem distribution (3.93).**

## 4. ⚠️ The negative has a POSITIVE inside it — and its circularity is named

| | Litolff | Breitkopf |
|---|---|---|
| **spans the WHOLE cell** | **3 of 7** barlines / **0 of 20** stems | **10 of 12** / **0 of 38** |
| h range, barlines | 8.18 - 12.01 | **9.49** - 13.94 |
| h range, stems | 0.92 - **9.56** | 0.83 - **6.58** |

*"The run reaches both crop edges"* has a **0-of-58 false-positive rate against
the eye** at 43% / 83% reach, and on Breitkopf the heights leave an **EMPTY
INTERVAL, 6.58 → 9.49.** ⚠️⚠️ **The circularity is named**: the crop pass
**sampled its barlines FROM the `too TALL` bucket**, so *"19 of 19 are too
TALL"* is true **by construction** and is not evidence, and the barline height
range is circular for the same reason. Not circular: the **stem** row (sampled
across all six buckets, 1 of 58) and the whole-cell row in both directions.
⚠️ **NOT proposed as a rule** — it is a property of the CROP and would stop
working the day a page-band reader lands, which is the repair §3 ranks.

## 5. ⚠️⚠️ TWO OF THE SIX FILTERS CANNOT FIRE AT THE SHIPPED DEFAULTS

**Arithmetic, not a fixture gap.** **ASPECT** (`h/w < 3.0`): past the height and
width bounds `h/w ≥ 2.0/0.6 = 3.33` **always**, and the ratio is
scale-invariant so the pixel conversion cancels. **AREA**: a component surviving
a `(1, 1.6 spaces)` opening carries ≥ 32 px against a floor of 10. **Both read
ZERO over 12,944 real candidates.**

**[mgr] confirmed by arithmetic from the shipped defaults.**

⚠️⚠️ **EVERY DOCUMENT DESCRIBING THIS CHAIN CALLS IT SIX FILTERS — the
function's own docstring, the stage charter, the boxing proposal §9 and the
forward plan. FOUR can fire.** ⚠️ **Not an argument for deleting them**:
`max_width_lines` is a keyword and `filter_sweep_arm.py` relaxes it to 1.5, at
which **both become live**. Asserted as an **inequality over the constants**,
because *"I could not make it fire"* and *"it cannot fire"* are different claims.

## 6. The length asymmetry — supported in SHAPE, not in separability

| coincides with | Litolff p05/med/p95 | Breitkopf p05/med/p95 |
|---|---|---|
| accidental | 0.92 / **2.63** / 4.06 | **1.58 / 2.46 / 3.02** |
| keysig | 1.06 / 2.66 / 3.43 | 2.10 / 2.62 / 2.96 |
| clef | 1.16 / 2.35 / 5.38 | 1.10 / 2.15 / 4.56 |
| notehead-attached | 1.32 / **4.06** / **7.23** | 1.17 / **3.78** / **12.00** |

**The ORDERING is exactly as the length-asymmetry addendum predicts**, and the
notehead-attached spread is **5×** the accidental's. ⚠️⚠️ **BUT THE
DISTRIBUTIONS OVERLAP WITH NO EMPTY INTERVAL ANYWHERE** — so by ask-first's own
test, **length alone is not a positive identifier on these plates, in either
direction.** The addendum is right that it is **weaker for stems**; what is
**not** established is that it is **strong for the others.** ⚠️ Breitkopf
supports it far better than Litolff (accidental spread 1.44 vs 3.14 spaces),
which is why they are reported apart.

## 7. Discipline
**Battery 19 arms / 3 targets / 2 judges — 19 RED, 0 survivors, 0 bad anchors,
restore md5-verified.** Suite **4,556 passed / 19 skipped / 0 failed**; seven
derived checks exit 0. ⚠️ The full run first found **4 failures the lane caused**,
all the same shape — a derived registry refusing an unaccounted quantity — and
**all four were filled in rather than suppressed.** ⚠️ 8 further failures are
**pre-existing**, all in `backend/tests`, and the claim is **checked**: the
branch touches no file under `backend/`.

**Producer only**, first consumer named in `wiring.KNOWN_GAPS`, with a test
asserting no adjudicator, consequence, inference or exporter declares it.
⚠️ **Writing the quantity's comment CLOSED a live `Q.INK` gap** — `wiring
--check` went STALE because a comment spelled `ink_bbox_canonical` and the
question credits by leaf name. **A doc mention is not a consumer**, a fourth
instance; reworded.

## 8. ⚠️ NOT ESTABLISHED
Accuracy of nothing — the print evidence is the crop pass's, joined. **The
barline test is UNAVAILABLE, not refuted**, and the page-band experiment that
would settle it was **not built**. Tolerance swept, never set. n = 2 documents /
2 publishers / 8 pages, **both scans**; the engraved family untouched by
construction. **No OMR-NED figure**, deliberately. **A GATHER change** —
`readjudicate`/`reexport_arm` are structurally blind, and no downstream effect is
claimed. ⚠️ **A limit of the quantity itself, named**: the population is what the
**opening** produced, and the opening is itself a filter — ink under 1.6 spaces
never becomes a candidate. **So this widens `Q.STEM`'s survivors to the
opening's output, not to the ink**; `Q.INK` is that layer, complementary rather
than nested. ⚠️ How many of the ~3,400 `too TALL` rows are pure crop artefact is
**unmeasured**.

## 9. Lane note
⚠️ The lane touched **three files outside its brief** — `staged/meaning.py`,
`staged/reach.py`, `tests/test_staged_capture.py` — one derived-registry entry
each, because their `--check` refuses an unaccounted quantity and there is no
other way to satisfy them. **Disclosed rather than found at integration.**
