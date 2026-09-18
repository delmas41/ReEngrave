# The missing stems are PRINTED, and the convention can read them

2026-09-17. **No code outside `benchmarks/`.** Nothing re-gathered, no flag
flipped, no default changed. Prompted by Sean: *"we are still missing 90% of
the stems without a diagnosis"*, then *"does the direction as well as the side
of the note head it is connected to -- right-up and left-down -- help us at
all?"* and *"I am also wondering if the problem is not only the probe but also
afterwards in the later stages where it is actually determined that it is a
stem."*

## 0. FOUR ANSWERS

1. ⚠️ **It is not 90%.** It is **34%** (Litolff, 793 of 2,347) and **46%**
   (Breitkopf, 1,529 of 3,337). Still the largest unexplained hole on the
   thread; a third, not nine tenths.
2. **The ink is there.** 95.8% / 93.1% of `no_stem` heads have a vertical run
   of ink ≥1.75 staff spaces beside them, at a median of ~3.9 spaces.
   ⚠️ On its own that is nearly content-free (§2).
3. **The convention reads them.** *Right-and-up or left-and-down* agrees with
   the stems we ALREADY read **95.9%** and **98.2%** of the time, and it
   speaks for **472 + 653 = 1,125 heads that currently abstain**.
4. **Sean's "later stages" hypothesis is supported — by TWO filters, and the
   bigger one is not the one this document first led with.**
   * ⚠️⚠️ **CORRECTION.** `STEM_MAX_HEIGHT_LINES = 8.0` is crossed by the
     missing stems at 3.7× and 47× the rate of the read ones — but in
     ABSOLUTE reach that is **80 of 784 heads (10.2%)** and **31 of 1,442
     (2.1%)**. A striking ratio on a small population. **It is not the bulk
     and must not be ranked as though it were.**
   * **`_drop_paired_strokes` is the larger suspect** (§4b): the missing
     stems stand beside a close vertical partner at **94.6% / 79.8%**
     against **80.7% / 15.7%** for the stems we read — an excess of **+13.8
     and +64.1 points**. That rule DELETES BOTH MEMBERS of a pair.

## 1. THE HANDOFF'S DIAGNOSIS COMPARED A READING WITH A READING

`docs/handoff-2026-09-17-two-brakes-and-a-ruler.md` §4 measured, per `no_stem`
head, the distance to the nearest **stem row in the record** and concluded
*"not mislabelled, not disregarded — not read"*, with 26.6% having no stem row
anywhere in the bar.

The conclusion is right and the evidence could not establish it: a head whose
stem is absent from the page and a head whose stem the CV rung never found are
the same number there. This asks the RASTER.

## 2. ⚠️ "THERE IS INK" IS NEARLY CONTENT-FREE, AND THE CONTROL SAID SO

First run: ink beside **95.8%** of `no_stem` heads — and beside **100%** of
heads that already had a stem. On a conductor's page something vertical stands
near almost every notehead, so the test barely discriminates.

⚠️ **And the first cut of that probe FAILED its own positive control at 30.9%**,
which is what caught it. A stem is a HAIRLINE that TOUCHES the head; the probe
was sweeping a column three times too wide, placed just outside a generous
detector box. Fixed (0.12-space column, swept across both edges), the control
reads 100.0% / 99.8%.

Shape helps but not enough: scored on *attached AND one-directional*, `no_stem`
heads read **43.9% / 36.6%** against a reference of **65.2% / 76.0%**.

## 3. THE CONVENTION IS THE DISCRIMINATOR, AND IT IS ALSO A READER

**A stem is attached on the RIGHT and goes UP, or on the LEFT and goes DOWN.**
Right-and-down does not exist. Of the four (side, direction) cells two are
music and two are a barline, a neighbour's stem, a beam or a slur edge.

⚠️ **It is not the convention PR #54 measured at 0.787.** That one is *stem up
if the head is below the middle line*, which two-voice writing and chords break
constantly. This one they do not break: an upper voice stemmed up still carries
its stem on the right. The two are independent, and only this one is a rule the
engraver has no freedom about.

| | Litolff | Breitkopf |
|---|--:|--:|
| heads where exactly ONE legal cell is filled — DECIDED | 938 / 1,435 (65%) | 1,495 / 1,774 (84%) |
| the same, `no_stem` | **472 / 784 (60%)** | **653 / 1,442 (45%)** |
| **agreement with the stem we already read** | **95.9%** (900/938) | **98.2%** (1,468/1,495) |

⚠️ **The agreement row is the positive control and it is what makes the rest
usable**: the convention reproduces our own readings on the population where we
have one. The `no_stem` reach is then a claim of the same kind, not a new one.

⚠️ **It goes SILENT rather than wrong where it cannot speak** — "both cells
filled" is 16% of Litolff's `no_stem` heads and **44% of Breitkopf's**, which
is the dense-column signature (a chord, two voices, or an adjacent barline).
That is the behaviour wanted from an arbiter.

⚠️ Whole notes are excluded throughout: they correctly have no stem (9 and 87
of the `no_stem` populations).

## 4. ⚠️⚠️ THE FAULT IS DOWNSTREAM OF THE INK, AND `STEM_MAX_HEIGHT_LINES` IS NAMED

Arm length where the convention speaks, in staff spaces:

| | n | median | p90 | **over 8.0** |
|---|--:|--:|--:|--:|
| Litolff, DECIDED | 938 | 3.62 | 6.54 | **4.6%** |
| Litolff, `no_stem` | 472 | 4.56 | **9.97** | **16.9%** |
| Breitkopf, DECIDED | 1,495 | 3.45 | 6.11 | **0.1%** |
| Breitkopf, `no_stem` | 653 | 4.16 | 6.59 | **4.7%** |

Both groups are measured by the same rule, so the comparison is like for like.
**The stems we fail to read are systematically longer than the ones we read**,
and they cross the shipped cap at 3.7× and 47× the rate.

⚠️ **This is a repeat of a fault this repo has already found once.** CLAUDE.md
records `STEM_MAX_HEIGHT_LINES` being raised 6.0 → 8.0 because *"a note two
ledger lines above the staff beamed to notes inside it carries a stem longer
than that — so the notes furthest from their beam were silently un-stemmed"*.
The population that forced that change is the population still failing.

**And the same split says where the missing heads are**: `no_stem` runs at
**44.8% outside the staff against 22.3% inside** on Litolff (51.8% / 40.2% on
Breitkopf) — the long-stem population, exactly.

### 4b. ⚠️⚠️ THE PAIR RULE IS THE LARGER SUSPECT

`_drop_paired_strokes` rejects two vertical strokes whose centres are within
**0.9 staff spaces** and which overlap vertically by 0.6 of the shorter, on
the stated ground that *"successive notes are set further apart than an
accidental's own strokes"* — and **it drops both members**. That premise is a
claim about how tightly this plate sets its notes, measured on 14 hand-counted
cells.

Evaluating the rule's own predicate on the raster at every head:

| | reference (stems we READ) | missing | excess |
|---|--:|--:|--:|
| Litolff | 80.7% (n=1,011) | **94.6%** (n=496) | +13.8 |
| Breitkopf | 15.7% (n=1,586) | **79.8%** (n=1,037) | **+64.1** |

⚠️ **This is a PROXY and it over-fires.** It reads raw 600-dpi ink with no
morphological opening, so it calls far more things a "stroke" than
`detect_stems` does after step 3 — which is why Litolff's reference rate is
80.7%. **The differential is the evidence, not the level**, and it runs the
same way on both publishers with a 64-point gap on the denser one.

⚠️ **The failure mode this predicts is TWO-VOICE WRITING**, not accidentals:
an up-stemmed upper voice and a down-stemmed lower voice in one column are two
strokes within 0.9 spaces that overlap vertically, and the rule deletes both.
That is the densest orchestral texture, and Breitkopf is the denser plate.

✅ **THE DECIDING EXPERIMENT IS ONE ARGUMENT**, already in the signature:
`detect_stems(..., drop_accidental_pairs=False)`. ⚠️ It needs cell images, so
it is a GATHER change and needs two full re-gathers to price — and the pair
rule's own record says it takes summed |error| from 60 to 24 on 14 cells, so
turning it off is not free and the arm must score both directions.

⚠️ **The arm is an over-estimate where a beam is involved**: the vertical run
does not stop at the beam, it continues through it. That inflates BOTH groups
and is why the comparison, not the absolute 8.0, is the claim.

## 5. TWO ROUTES MEASURED AND REFUSED

* **Attachment tolerance is NOT the lever.** 73.4% / 80.3% of `no_stem` heads
  sit in a cell that HAS stem rows, none overlapping the head — but the
  vertical gap to the nearest one is a **median 2.85 / 2.63 spaces**, and only
  **7 / 20 heads** are within half a space. Those rows are other notes' stems.
  ⚠️ **This also retires the handoff's ranked item 3**, "the attachment
  near-misses (45 heads, 6%) are the only cheap stem win left": measured as box
  gaps rather than centre distances the population is ~7-20, and worth less
  still.
* **Crowding is refuted.** `no_stem` rate against noteheads-per-cell is flat on
  Litolff (31.5 / 32.5 / 40.7 / 32.4%) and **inverted** on Breitkopf (54.5%
  at 1-2 heads falling to 45.2% at 11+).

## 6. WHAT IS NOT ESTABLISHED

* **Nothing was built and nothing was changed.** No constant was moved, and
  raising `STEM_MAX_HEIGHT_LINES` is **not** proposed here — its own docstring
  says 8.0 is *"where the two populations separate"*, so moving it needs the
  measurement that constant was set on, re-taken. What is established is that
  the missing stems are on the wrong side of it far more often than the read
  ones.
* **No note was checked against the print by eye.** Every figure is the raster
  against the record.
* **The convention's 1,125 heads are REACH, not accuracy.** Its 95.9% / 98.2%
  is measured where we already had an answer — which is, by construction, the
  population that was easy enough to read once.
* ⚠️ `_drop_paired_strokes` in `line_detection` was noticed as a second
  downstream candidate (it deletes vertical strokes coming in pairs half a
  space apart, which is what an accidental looks like) and **was not tested** —
  doing so needs the cell images, i.e. a re-gather.
* n = 2 documents, 2 publishers, 8 pages.

---

# THE ARM RAN. Two thirds of the missing stems are not a filter's fault.

2026-09-17, after the sections above. **Still no code outside `benchmarks/`.**
`git diff origin/main -- tools/ backend/` is empty. Three arms:
`pair_rule_arm.py`, `filter_sweep_arm.py`, `width_cap_check.py`.

## A. THE CONTROL IS EXACT, AND IT HAD TO BE CHECKED

The arms RE-CUT the cells, so a difference from the record could be the re-cut
rather than the flag. Two controls, both passed before any delta was read:

* `line_detection.py`, `measure_extractor.py`, `staff_detector.py`,
  `staff_line_removal.py` and `preprocessing.py` are **byte-identical**
  between the record's own commit (`9d4ccc85`, `dirty: true`) and this tree.
* With the shipped settings the re-cut reproduces the record **783 of 783
  cells, stem for stem, 1,920 against 1,920.** The arms exit non-zero rather
  than report a delta if this fails.

## B. THE SWEEP — Litolff Beethoven 5 pp.1-4, 793 heads abstaining `no_stem`

| relaxing… | recovers | of 793 | new strokes | on an accidental |
|---|--:|--:|--:|--:|
| `drop_accidental_pairs=False` | 73 | 9.2% | 244 | **56** |
| `max_height_lines` 8.0 → 24.0 | **17** | 2.1% | 81 | 0 |
| `min_height_lines` 2.0 → 1.0 | 58 | 7.3% | 1,127 | 140 |
| **`max_width_lines` 0.6 → 1.5** | **217** | **27.4%** | 175 | **4** |
| **ALL FOUR (ceiling)** | **287** | **36.2%** | 2,793 | 340 |

⚠️ The arms overlap (73+17+58+217 = 365 > 287): a head can be recovered by
more than one relaxation. Only the ceiling is additive.

⚠️ **`min_height_lines` interacts with the pair rule and the total goes DOWN**
(1,920 → 1,200 strokes): a lower floor admits more short strokes, which then
pair with each other and are dropped in pairs. A filter sweep on this function
is not separable, and the table must not be read as four independent knobs.

## C. ⚠️⚠️ THE CEILING IS THE RESULT: 506 OF 793 ARE LOST BEFORE ANY FILTER

Relaxing **every** filter to absurd values recovers **287 of 793 (36.2%)**.
The other **506 (63.8%) never reach a filter at all** — they do not survive
step 3, the vertical morphological opening with a one-staff-space kernel on
the staff-line-ERASED image, as a single connected component.

**So stem recall is not a threshold problem.** It is the shape of the
component, and the named, scoped, unbuilt repair is already in CLAUDE.md:
*"a thin glyph is BROKEN by erasure where the lines crossed it and MERGED INTO
the lines if they are kept, so find the component on the ERASED image and
measure its ink inside that box on the ORIGINAL."*

⚠️ That is a GATHER change and this arm cannot price it. What the arm
establishes is only that **no amount of filter tuning can reach two thirds of
this population**, which is what makes the two-pass read worth building rather
than one more constant worth sweeping.

## D. THE WIDTH CAP IS THE LARGEST SINGLE COST — AND IS NOT SHIPPABLE ON THIS

217 heads for 175 strokes and only 4 on an accidental is the cheapest row in
the table by that measure. ⚠️ But *"not an accidental"* is not *"is a stem"*,
and Litolff is the plate this repo records as MERGING where Breitkopf
shatters — a stem fused to its own notehead or a beam stub is exactly a
component wider than 0.6 spaces.

Put to an INDEPENDENT reader — the right-up/left-down convention off the
raster, which agrees with the stems we already read **95.8% (902/942)**:

| | agrees | n | rate |
|---|--:|--:|--:|
| the 217 recovered | 112 | 134 | **83.6%** |
| **reference (stems we READ)** | 902 | 942 | **95.8%** |

**Better than chance by a wide margin and clearly short of the bar.** Reading
it as a mixture of real stems agreeing at 95.8% and junk agreeing at 50%,
about **73% are real** — roughly 160 stems and 57 false ones.

⚠️ **RECOMMENDATION: do not move `max_width_lines` on this.** A 27% recall
gain carrying ~27% junk is a trade, not a win, and the constant was measured
onto its value. What this establishes is that the width cap is where to look
first if anyone does re-take that measurement — not that it should move.

## E. ⚠️⚠️ CORRECTIONS TO THIS DOCUMENT'S OWN EARLIER SECTIONS

**The raster proxy in §2 and §4b over-stated two filters out of three, and
both over-statements reached a user-facing claim before the arm ran.**

| | what the proxy implied | what the arm measured |
|---|---|---|
| `_drop_paired_strokes` | "the larger suspect", 94.6% vs 80.7% | **73 heads, 9.2%** |
| `STEM_MAX_HEIGHT_LINES` | 80 heads (10.2%) | **17 heads, 2.1%** |

The cause is one thing and it is worth carrying: **the proxy reads raw ink at
600 dpi; `detect_stems` reads connected components AFTER a morphological
opening.** Most of what the proxy called a neighbouring "stroke" was never a
stroke candidate. A proxy for a filter's predicate is not a proxy for the
filter, because the filter's INPUT POPULATION is not the ink.

⚠️ §4's ranking of the height cap as a named lever stands corrected at 2.1%,
and §4b's "larger suspect" stands corrected at 9.2%. Both are kept above
rather than rewritten, because the correction is the finding.

## F. WHAT IS NOT ESTABLISHED

* **One document.** Every figure here is Litolff Beethoven 5 pp.1-4. Breitkopf
  was NOT run — its `no_stem` population is 1,529 and its plate SHATTERS where
  this one merges, so the width-cap row in particular should be expected to
  behave differently, not the same.
* **No note was checked against the print.** The convention cross-check is one
  reading against another, from different pixels by a different method —
  stronger than a recall count, weaker than a crop.
* **The cost column is a floor.** "Lands on an accidental the detector found"
  misses every false stroke that is a beam stub, a slur edge, a barline
  fragment or a neighbour's stem, and misses accidentals the detector missed.
* **Nothing was changed and no constant is proposed for a move.**
