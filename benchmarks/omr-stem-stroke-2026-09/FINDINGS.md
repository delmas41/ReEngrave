# The stroke IS separable inside a fused blob — and the reader that finds it SPLITS BY PUBLISHER

2026-09-18. Branch `claude/stem-stroke-reader-2026-09`, off
`origin/claude/integration-2026-09-18`. `docs/handoff-2026-09-17-the-ink-is-fused.md`
§4b asked for *"a reader that recovers the stroke from inside a fused
component — a column-profile or projection method, not a component filter"*
and recorded that **nothing had been built or measured for it**.

It is built, behind `OMR_STEM_STROKE` (**default OFF**, allow-list), and the
only file touched under `tools/` is `line_detection.py` plus its own test.

---

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

Per the standing instruction of 2026-09-17 (PR #55): before building, state
how a HUMAN reads this off the page and which engraving convention governs
it. This ran unattended, so the block is written and the work proceeded.

**CONVENTION ASSUMED**, all from `docs/engraving-conventions.md`:

* **`[C9 + L10]` — a stem attaches on the RIGHT going UP or on the LEFT going
  DOWN, at x = 0 or x = notehead width.** Status MEASURED HERE, RIGID, *"one
  of the most reliable conventions in all of notation"*. Used TWO ways: as the
  reason a stem's ink is at the head's vertical EDGE and never through its
  middle (so the profile's band should stand there), and as the arbiter the
  recovered strokes are scored against.
* **`[C13 + L11]` — 3½ staff spaces by default, and as long as the music
  needs.** Used as *where to look*, never as a cap; the shipped
  `STEM_MAX_HEIGHT_LINES = 8.0` is imported, not restated.
* **`[L14]` — a stem is about a tenth of a staff space thick.** This is what
  makes *thin AND isolated* the property to test, and it is what the width
  cap protects. It is the reason a band cut by the cap is refused (§6).
* **`[C79 + L20]` — stacked beams sit 0.75 sp apart, stroke 0.5, gap 0.25, so
  the gap is NARROWER than the stroke and an erosion tuned to open the gaps
  eats the strokes first.** Taken as a prohibition: **this reader performs no
  erosion and no re-thresholding of its own.** It corroborates the handoff's
  own dead hypothesis (horizontal pre-dilation at 2/3/5 px recovered 3, 3 and
  4 heads of 793).

**WHAT WOULD FALSIFY THEM HERE**

* `[C9 + L10]`: if the recovered strokes agreed with right-up/left-down at
  the 0.506 always-the-commoner-direction baseline. They read **82.6%** and
  **96.3%**, so the convention is not vacuous on this population — but see
  §7, which is where it loses.
* `[L14]`: if refusing a band cut by the width cap cost real reach. It costs
  **5 heads of 351** on Litolff and **6 of 548** on Breitkopf.
* `[C13 + L11]`: if the strokes recovered clustered at a length the
  convention forbids. Not separately measured — **NOT ESTABLISHED.**

**NOT CONFIRMED WITH SEAN.** Nothing here is a default and nothing changes
until the flag is set.

---

## 0. SIX ANSWERS

1. ⚠️⚠️ **§5's FALSIFICATION DOES NOT FIRE.** The stem's ink inside a fused
   component *can* be separated by a column profile: of the components the
   census blames as `too WIDE`, **92.1% (Litolff) and 73.6% (Breitkopf)** hold
   a separable stroke band. A within-blob reader IS available.
2. **The reader works as a reader.** It re-finds **98.0% / 98.2%** of the
   strokes `detect_stems` already accepts — the positive control that makes
   everything below it readable.
3. **REACH: 346 of 793 (43.6%) and 544 of 1,529 (35.6%)** `no_stem` heads
   newly covered, per publisher, never pooled.
4. ⚠️⚠️ **QUALITY SPLITS BY PUBLISHER — Breitkopf 96.2% against a 98.2% bar,
   Litolff 82.6% against 96.1% — BUT §4b WITHDRAWS THE READING I FIRST GAVE
   THAT SPLIT.** A sibling crop pass put the neighbouring population to the
   print and found the width cap's recoveries **33 of 33 real**, so an ~83%
   convention score there meant ~100% real and the mixture model is refuted.
   **The Litolff verdict is UNDETERMINED, not a refusal on quality.** The flag is
   still OFF, for the unpriced BEAM risk alone.
5. ⚠️⚠️ **A THIRD OF THE BREITKOPF DENOMINATOR IS NOT A NOTEHEAD — 576 of
   1,529 boxes (37.7%) are thinner than a notehead can be, reproducing a
   sibling crop pass's sampled 35.6% from a different instrument. Litolff is
   5.5%. The reader DECLINES them (12 of 576) and the scores do not move**
   (§4b), so the barline hazard is measured and absent — but every reach
   figure over the unrestricted population understates the job.
6. ⚠️⚠️ **THE CROP PASS THE THREAD HAS OWED SINCE 09-17 IS DONE, AND IT NAMES
   THE RESIDUAL AS SOMEBODY ELSE'S.** All **6 of 6** sampled Breitkopf
   disagreements are one fault: the record's notehead box stands part-way
   ALONG a neighbouring note's stem. The stroke is real; the ATTRIBUTION is
   wrong, and it is wrong in a stage this reader cannot reach.

---

## 1. ⚠️⚠️ A CORRECTION FIRST: §3's 8.1-SPACE FUSED BLOB IS NOT THE DISTRIBUTION

The handoff's §3 concludes **"THERE IS NO STEM COMPONENT TO FIND"** from one
spot-checked cell — *"3 connected components with a median height of 811 px,
in a cell whose staff spacing is 100 px"* — and its own §6 says so: *"it
explains the direction of the result and does not measure how often."*
Measured over every cell of both plates (`probe_fusion.py`, 0 drift):

| | Litolff | Breitkopf | handoff §3 (n = 1 cell) |
|---|--:|--:|--:|
| cells | 1,183 | 818 | 1 |
| components | 6,128 | 6,816 | 3 |
| components per cell, median | **4** | **7** | 3 |
| component HEIGHT, median (staff spaces) | **4.18** | **3.20** | **8.1** |
| over the 8.0 cap | 30.5% | 22.0% | (that cell failed it) |
| component WIDTH, median | 0.26 | 0.21 | — |
| **over the 0.6 width cap** | **6.1%** | **6.0%** | — |

⚠️ **The typical component is stem-shaped.** Its median height sits in the
middle of the 2.0–8.0 window and only **6%** of components exceed the width
cap. The spot-checked cell is about **2× the median height** and is not
representative.

⚠️ **The genuine merge is a MINORITY, and it is the direct test** — how many
NOTEHEADS one component covers, which the census cannot ask because it reads
only shape:

| a component covers | Litolff | Breitkopf |
|---|--:|--:|
| NO notehead | 67.4% | 61.8% |
| 1 notehead, ≥ 2 spaces tall | 18.4% | 21.5% |
| 1 notehead, shorter than 2 spaces | 4.7% | 4.7% |
| **2+ noteheads (a MERGE across notes)** | **9.6%** | **12.0%** |

⚠️⚠️ **AND THE OVER-CAP POPULATION IS MOSTLY FURNITURE, NOT FUSED STEMS.** Of
the components exceeding the 8.0-space cap, **1,759 of 1,866 (Litolff) and
1,270 of 1,500 (Breitkopf) cover NO notehead at all** — barlines and brackets
crossing the crop, which is exactly what `STEM_MAX_HEIGHT_LINES`' own
docstring says the cap is for. **The cap is working as designed on that mass**
and the census never blames it there, because it does not overlap a head.

**So the corrected claim is narrower and better defined than §3's**: it is not
that there is no stem component to find, it is that **a minority of components
— roughly a tenth — merge across notes, and those are where the census's
blame lands.** The handoff's §2 generalisation survives intact and is the one
the reader rests on: on both plates the dominant failure is *a component
exists and is the wrong shape*.

⚠️ What does NOT change: the top bucket still INVERTS between publishers
(Litolff WIDE 29.9%, Breitkopf TALL 31.1%), so no constant serves both, and
that was the brief's reason for measuring them apart. It was right.

---

## 2. §5 ANSWERED: THE STROKE IS SEPARABLE, AND ONLY IN THE `WIDE` BUCKET

`probe_separability.py`, 0 cells drifted on either plate. Positive control
first, because the failure mode here is a believable zero:

| agree (staff spaces) | Litolff control | Breitkopf control |
|---|--:|--:|
| 0.10 | 98.1% | 98.3% |
| **0.25 (shipped)** | **98.0%** | **98.2%** |
| 0.60 | 98.0% | 98.2% |

The profile re-finds the strokes `detect_stems` already calls stems. It is a
stem reader, so the rest of the table means something.

**Does a REJECTED component hold a separable stroke?** (agree = 0.25)

| rejected as | Litolff n | holds a band | Breitkopf n | holds a band |
|---|--:|--:|--:|--:|
| **too WIDE** | 215 | **92.1%** | 288 | **73.6%** |
| too TALL | 1,866 | 7.0% | 1,500 | 8.3% |
| too SHORT | 1,276 | **0.0%** | 1,682 | 0.1% |
| at a CELL EDGE | 607 | 7.7% | 254 | 2.8% |

⚠️⚠️ **THE BRIEF ASKED FOR THE TRANSFER TEST ON BREITKOPF'S BIGGEST BUCKET,
`TALL` (476, 31.1%), AND THE ANSWER IS THAT THE READER DOES NOT REACH IT —
7.0% and 8.3%, on both plates.** The reason is structural and worth stating
plainly: **a column profile separates ACROSS x and not ALONG y.** It can
narrow a wide blob, because the columns beside a stem hold no long run; it
cannot shorten a tall one, because a narrow agreeing band inside a 12-space
component *is* 12 spaces and fails the same height cap the component did.
Splitting a tall stroke needs a y-cut this reader does not have.

⚠️ `too SHORT` at 0.0% is the probe's own sanity check: a component shorter
than two spaces cannot contain a ≥ 2-space band, so a non-zero there would
have meant the instrument was fabricating.

⚠️ The tolerance sits on a **PLATEAU, not an empty interval** — heads a band
covers read 289 / 281 / 279 / 274 / 270 across 0.10–0.60 on Litolff and 376 /
375 / 374 / 374 / 374 on Breitkopf, with the control flat at 98.0–98.3%.
Nothing separates. The shipped 0.25 is the middle of a flat region and is
tuned to neither plate.

---

## 3. THE ARM: REACH, COST, AND THE TWO CONTROLS IT PASSES FIRST

`stroke_arm.py`. One re-cut, four variants, both publishers.

⚠️ **CONTROL 1 — FLAG-OFF REPRODUCES THE RECORD, STROKE FOR STROKE.** Asked
for directly rather than inferred from the guard: Litolff **1,920 against
1,920 with 1,183 of 1,183 cells matching exactly**, Breitkopf **2,305 against
2,305 with 818 of 818**. This matters beyond tidiness — `line_detection.py`
is on the path every arm of `benchmarks/omr-stem-ink-2026-09/` proves
faithful before it reports a delta, so a flag-off difference here would break
their instruments and look like their bug.

⚠️ **CONTROL 2 — the arm has teeth.** The ON sets differ from OFF on every
variant; the arm exits non-zero declaring itself DEAD if they do not, or if
reach is zero.

| variant | Litolff heads | of 793 | +strokes | heads/stroke | Breitkopf heads | of 1,529 | +strokes | heads/stroke |
|---|--:|--:|--:|--:|--:|--:|--:|--:|
| `raw` | 351 | 44.3% | 1,393 | 0.25 | 548 | 35.8% | 2,157 | 0.25 |
| **`side`** | **346** | **43.6%** | **581** | **0.60** | **544** | **35.6%** | **1,074** | **0.51** |
| `side+end` | 344 | 43.4% | 545 | 0.63 | 542 | 35.4% | 1,015 | 0.53 |
| `side+end+legal` | 328 | 41.4% | 498 | 0.66 | 532 | 34.8% | 970 | 0.55 |

**The convention prior is worth a factor of ~2.4 in cost for ~1% of reach**:
anchoring a band to a notehead's left or right EDGE (`[C9 + L10]`) takes
Litolff from 1,393 added strokes to 581 and Breitkopf from 2,157 to 1,074,
losing 5 and 4 heads. That is the registry earning its keep — a human does
not scan columns, they look at the side of a notehead.

⚠️ **`side+end+legal` is graded on a rule it was BUILT to satisfy**, so its
agreement rate is circular and only its REACH may be read. The arm prints
`<- CIRCULAR` beside it.

### 3b. Is it the WIDTH CAP by another name? ~62% yes, ~38% no

`filter_sweep_arm.py` recovers 217 Litolff heads by relaxing
`max_width_lines` 0.6 → 1.5, and `width_cap_check.py` measured those at 83.6%
convention agreement against a 95.8% bar and **REFUSED** them. So the overlap
is the question:

| | both | ONLY the column profile | ONLY the relaxed cap | shared |
|---|--:|--:|--:|--:|
| Litolff `side` | 213 | **133** | 4 | 61.6% |
| Breitkopf `side` | 344 | **200** | 1 | 63.2% |

**About 62% of the reach is a constant this thread already refused**, and
about 38% (133 and 200 heads) is genuinely new. So it is not merely the width
cap — but it inherits most of that population, which is the first reason the
Litolff verdict below is a refusal.

---

## 4. ⚠️⚠️ QUALITY: THE RESULT SPLITS BY PUBLISHER

Scored against the one independent reader on this thread — the engraving
convention read off the ORIGINAL page raster in page pixels, a different
image and a different method from the canonical-cell band reader.

| | recovered | AGREES | disagrees | silent | rate | the bar | estimated real* |
|---|--:|--:|--:|--:|--:|--:|--:|
| **Litolff `side`** | 346 | 190 | 40 | 116 | **82.6%** | 95.8% | **~71%** |
| **Breitkopf `side`** | 544 | 360 | 14 | 170 | **96.3%** | 97.9% | **~97%** |

\* the mixture `width_cap_check.py` uses: real strokes agree at the bar's
rate, junk at 50%.

**Breitkopf HOLDS: 544 heads at ~97% real.** **Litolff FAILS: 82.6% is
statistically indistinguishable from the 83.6% at which this thread refused
the width cap**, and refusing one while shipping the other would be
inconsistent.

⚠️ **The split is the expected direction given what this repo already
records** — *"Litolff MERGES and Breitkopf SHATTERS"*. On a merging plate a
band inside a merged mass is more often not a stroke; on a shattering plate a
band is a clean stroke. The reader is a fusion reader and it is better on the
plate with LESS fusion, which is worth saying because it is the opposite of
what the brief's framing would predict.

⚠️ **The bar is itself reach-adjacent.** 95.8% / 97.9% is measured where the
pipeline already had an answer — *"by construction, the population that was
easy enough to read once"* — so a hard population scoring lower is partly
expected. That is exactly what the crop pass was for.

---

## 4b. ⚠️⚠️ TWO CORRECTIONS FROM A SIBLING CROP PASS, AND THEY PULL IN OPPOSITE DIRECTIONS

`benchmarks/omr-stem-crop-pass-2026-09` read **180 of these boxes against the
print** and its two results land squarely on §4. Both were checked here
against the population rather than taken on report.

### (i) A THIRD OF THE BREITKOPF DENOMINATOR IS NOT A NOTEHEAD — confirmed

That pass found **46 of 180 sampled boxes are not noteheads** (15.6% Litolff,
35.6% Breitkopf) — whole rests, a printed capital **B**, the `e` of *cresc*,
a bass clef, a trill, eighth rests, a repeat dot, barlines — and on
Breitkopf's `too TALL` bucket, the handoff's own headline inversion, it is
**12 of 12**, every one a box 0.40–0.45 spaces wide sitting on a vertical
rule.

**Measured over the whole population here rather than a sample**, using that
pass's own cut (a notehead is ~1.3 spaces wide; a floor at 1.0 catches 39 of
its 46 non-noteheads at a cost of 0 of 63 real stems):

| | `no_stem` boxes | thinner than 1.0 sp | share |
|---|--:|--:|--:|
| Litolff | 793 | **44** | **5.5%** |
| Breitkopf | 1,529 | **576** | **37.7%** |

⚠️ **37.7% independently reproduces that pass's sampled 35.6% from a
different instrument** — they adjudicated crops, this measures box widths over
the population — which is the strongest corroboration either result has.
⚠️ Litolff's 5.5% is much lower than its sampled 15.6%, and the two are
consistent: the pass's own figure says the width floor catches 39 of 46, so
most of what it found is Breitkopf's, and its sample is STRATIFIED and
therefore not a population rate.

**THE REACH FIGURES IN §3 ARE THEREFORE UNDERSTATED, AND BREITKOPF'S BADLY:**

| | reach as §3 reports it | over PLAUSIBLE heads only |
|---|--:|--:|
| Litolff `side` | 346 of 793 = 43.6% | **338 of 749 = 45.1%** |
| Breitkopf `side` | 544 of 1,529 = 35.6% | **532 of 953 = 55.8%** |

⚠️⚠️ **AND THE HAZARD THE COORDINATOR NAMED IS MEASURED AND DOES NOT
MATERIALISE.** The worry was that a box on a barline would have the reader
find the barline while the convention probe, sweeping the same box's edges,
finds the SAME barline and agrees about it — a correlated-witness failure with
the correlation running through a spurious DETECTION rather than through ink
quality. **The reader fires on 12 of 576 thin Breitkopf boxes (2.1%) against
532 of 953 plausible ones (55.8%), and restricting the score moves it
96.3% → 96.2% and 82.6% → 82.6%.** It declines the barline population almost
entirely, of its own accord, and the quality figures are not inflated by it.
Restricted bars: **96.1%** and **98.2%**.

⚠️ *Why* it declines them was not designed and is worth stating as luck until
measured: a 0.4-space box gives the `side` anchor a tolerance of 0.14 spaces,
and a full-height rule is refused by the edge filter or the height cap. Aiming
at that bucket deliberately would be a different matter.

### (ii) ⚠️⚠️ THE MIXTURE MODEL IS REFUTED, AND MY LITOLFF REFUSAL LOSES ITS STATED BASIS

§4 refused Litolff because **82.6% is indistinguishable from the 83.6% at
which `width_cap_check.py` refused the width cap**, and read both through that
arm's mixture model as *~71-73% real*.

**That crop pass put the width cap's own recoveries to the print and they are
33 of 33 REAL, 0 junk, 95% lower bound 0.913.** So an 83.6% convention score
on this plate corresponded to **~100% real, not 73%**.

Three consequences, and the first two are against my own write-up:

1. **The mixture model is refuted on the neighbouring population.** Junk does
   not agree at chance there, because there was no junk. The ~71% and ~97%
   figures in §4 are **withdrawn** — they are kept in the table with this
   paragraph beside them, because the correction is the finding.
2. **My Litolff verdict is no longer a refusal ON QUALITY; it is
   UNDETERMINED.** 82.6% against a 96.1% bar is not evidence that ~18% of the
   recoveries are junk — on the one Litolff population anyone has checked
   against the print, a similar score was ~100% real. **The convention probe
   UNDERSTATES this plate**, which is exactly what my own crop pass suggested
   from the other side when it could not adjudicate 5 of 12 tiles (§5).
3. **~62% shared reach with the width cap flips from a liability to an
   asset.** §3b read that overlap as *"inherits a refused verdict"*. With the
   width cap's recoveries shown real, the shared population is the
   BETTER-EVIDENCED part of this reader's reach, not the worse.

⚠️⚠️ **SO THE RECOMMENDATION DOES NOT CHANGE BUT ITS REASON DOES, AND THE NEW
REASON IS THE HONEST ONE.** Leave `OMR_STEM_STROKE` **OFF** — not because the
Litolff recoveries look like junk (that is no longer supported) but because
**the effect on BEAMS is completely unpriced** and 581–1,074 extra strokes
enter `detect_beams` with the flag on. That was always the largest open risk;
it is now the only one.

⚠️ **What a third publisher is needed for has also changed.** It is no longer
to break a 82.6 / 96.3 quality tie — that gap is now substantially an artefact
of the ARBITER, not of the reader. It is to check the 5.5% / 37.7% denominator
contamination, which differs 7× between two plates and is a DETECTOR property.

---

## 5. THE CROP PASS — 600 dpi, frame control, stratified and declared

`crop_pass.py`, seed 20260918. 18 tiles per publisher, 6 per stratum
(`agree` / `disagree` / `silent`), sheets in `out/print-litolff/` and
`out/print-breitkopf/`.

⚠️ **Frame control passed 18 of 18 on both** — every window's head box is
more than 20 grey levels darker than its surround, so each tile is on a
notehead and its verdict is admissible. The probe exits non-zero if more than
10% are flagged.

⚠️ **The sample is STRATIFIED. There is no "18 of 18" figure here** and the
two strata are reported apart; drawing 18 at random from 346 would have landed
~2 disagreements and settled nothing.

⚠️ **THE ZOOM IS PART OF THE INSTRUMENT.** The first run used ±7 staff spaces
in 300-px tiles, which put a one-space notehead at a fifteenth of the tile —
unadjudicable, and it would have produced verdicts anyway. Re-rendered at ±5
spaces in 420-px tiles.

### Breitkopf — the plate the reader holds on

**AGREE stratum: 6 of 6 correct and unambiguous.** Textbook down-stems on the
head's left (#1, #2 — a hollow half note, #3, #5), one up-stem into a beam
(#0), one between two heads of a beamed group (#4).

⚠️⚠️ **DISAGREE stratum: 6 of 6 are ONE FAULT, and it is not the reader's.**
In every one the record's notehead box stands **part-way along a neighbouring
note's stem** — a long vertical running from a head above (#6, #7, #10, #11)
or up to a head below (#8, #9), with our box somewhere in the middle of it.
The stroke the reader found is a real printed stem. What is wrong is **which
head owns it**, and the direction then follows from where the box happens to
sit along the stroke.

**So the Breitkopf residual is an ATTRIBUTION fault, and the reader's true
quality on that plate is better than 96.3%.**

### Litolff — the plate it fails on

**AGREE stratum: 4 of 6 clearly correct** (#2, #3, #4, #5 all show a plain
vertical running down from the head), 2 ambiguous. **DISAGREE stratum: ~2 of
6 look right, 1 is clearly wrong** (#10: a stroke running DOWN to a head
below, called `up`), **3 ambiguous.**

⚠️⚠️ **THE HONEST LIMIT: ON LITOLFF I COULD NOT CONFIDENTLY ADJUDICATE 5 OF
12 TILES.** The plate is blotchy at 600 dpi, heads merge into beams and staff
lines, and several tiles show a full-height barline beside the head. **So the
crop pass CONFIRMS THE DIRECTION of the convention score there — the agree
stratum reads clearly better than the disagree stratum, so the bar is
measuring something real — and it CANNOT put a number on it at this sample
size and by this adjudicator.** That is a fact about the plate and about me,
and it is why §4's Litolff verdict rests on the convention score rather than
on the crops.

---

## 6. ⚠️⚠️ A HYPOTHESIS I FORMED FROM THE CROPS, BUILT, MEASURED AND REFUTED

The crop diagnosis above has an obvious repair. `[C9 + L10]`'s anchor geometry
(`stemUpSE` = [1.18, 0.168], `stemDownNW` = [0.0, −0.168]) says the stem MEETS
its head, so an up-stem's foot is at the head and a stroke overshooting the
head in BOTH directions is not that head's stem. Implemented as `end_tol`.

**The geometry confirms the diagnosis** — one band runs 6.58 spaces straight
through a head, +3.75 above and +2.83 below — and **enforcing it changes
nothing: disagreements 40 → 40 on Litolff and 14 → 14 on Breitkopf.**

⚠️⚠️ **THE REASON IS A STAGE, NOT A TOLERANCE, AND IT IS THE MOST USEFUL
THING IN THIS SECTION.** `detect_stems` emits **STROKES, not (stroke, head)
pairs.** A band this rule refuses for head A is still in the cell's stroke
list because head B admitted it, and the downstream overlap test hands it
straight back. **The fault is in ATTRIBUTION and is not repairable in the
reader.** It lives in `adjudicate_stem_direction`, which is another agent's
file and which this branch does not touch.

**That is the fifth dead hypothesis on this thread and the first that is
mine-from-the-print rather than mine-from-a-proxy.** The refutation is kept
in `stroke_columns.py` with its numbers rather than deleted.

---

## 7. WHAT SHIPPED, AND WHY BEHIND A FLAG

`tools/omr/line_detection.py`: `STEM_STROKE_ENV`,
`stem_stroke_enabled()`, `STEM_STROKE_AGREE_SPACES = 0.25`,
`_column_stroke_bands()`, and eight lines at the foot of `detect_stems`.
Nothing else under `tools/` but the test file.

* **Default OFF**, so the OFF test is an **ALLOW-LIST**
  (`in ("1","true","yes","on")`) — a typo must not switch a document ONTO an
  unpriced GATHER change. Derived-checked: `test_flag_default_direction.py`
  enumerates it as `('OMR_STEM_STROKE', '0', In, default_on=False)`.
* **ADDITIVE, and it runs AFTER the pair rule** so the shipped set is
  untouched. ⚠️ That also means the added bands do NOT get
  `_drop_paired_strokes`. That is what was measured and therefore what ships;
  whether the pair rule should police them is **open and unmeasured**.
* **The `raw` variant is what ships**, because `side` needs the NOTEHEADS and
  `detect_stems` is handed a cell and nothing else. Threading them in would
  mean a parameter with no producer — the exact shape `tools/omr/no_producer.py`
  exists to flag — so the convention anchor stays in the benchmark, measured,
  with its 2.4× cost saving recorded for whoever wires it.

⚠️ **IT IS A GATHER CHANGE.** `readjudicate.py` and `reexport_arm.py` rebuild
from a saved record and are **structurally blind** to it. Pricing its effect
on a FILE needs two full re-gathers, which were not taken and are not
claimed.

⚠️ **NO OMR-NED FIGURE, deliberately**: the metric is symmetric and pays for
emitting FEWER symbols, which is the wrong direction for a recall change.

⚠️ **RECOMMENDATION: leave it OFF.** It clears the bar on one publisher of
two and fails on the pessimistic plate at the level a sibling arm was
refused at. What would change that is §6's attribution repair, in
`adjudicate_stem_direction`, plus a third publisher.

### Controls and the battery

* Full derived-check set exits 0: `inventory`, `health`, `wiring`, `capture`,
  `no_producer`. ⚠️ Each was ALSO run before the change and also exited 0, so
  "passes after" is a result and not a coincidence.
* `tools/omr/tests/test_line_detection_stroke_reader.py`: **30 tests.**
* **Mutation battery: 12 arms, 12 RED, 0 survived, 0 BAD ANCHOR**, positive
  control first and red, restore verified by hash, baseline green
  (`out/mutation-battery.json`).

---

## 8. ⚠️⚠️ WHAT THE INSTRUMENTS GOT WRONG — FIVE FAULTS, FOUR IN MY OWN

Every one of these was caught by a control rather than by review, and two of
them had already reached a number in this document's earlier drafts.

1. **The benchmark held its OWN COPY of the profile, and the copy was wrong
   twice.** It read a column's FIRST-TO-LAST extent rather than its LONGEST
   RUN (so a column with two runs reported one stroke spanning both, or, once
   its own guard fired, nothing at all), and it cut a band at the width cap
   instead of applying the cap to the whole agreeing region (so a solid blob
   two spaces wide came out as three stems). **Both were found by the shipped
   code's unit tests, neither was visible in any aggregate the arms printed,
   and every figure taken before they were fixed is superseded.** The copy is
   deleted: `stroke_columns.read_strokes` now calls the shipped function.
   *A probe that re-implements its subject measures the re-implementation.*
2. **The separability probe credited BARLINES as separable stems.** Its first
   run applied no edge filter to the band, and **607 of Litolff's rejected
   components are rejected for standing at a cell edge, 99.8% of which hold a
   clean band** — because a barline is the cleanest vertical stroke on a page.
   Heads covered fell 345 → 287 when the filter was applied to the band's own
   x.
3. **My own diagnostic guard inverted TEN mutation arms.** Added to explain a
   survivor, it read `if "no tests ran" in last or "deselected" in last and
   "passed" not in last` — which parses as `A or (B and C)`, so a perfectly
   good `1 failed, 28 deselected` matched B and C and was reported as
   COLLECTED NOTHING, i.e. as a pass. **A guard's fallback converting *cannot
   tell* into a definite answer, inside the battery built to catch that.**
   Repaired to read pytest's exit code (5 = nothing collected) rather than its
   prose.
4. ⚠️⚠️ **`__pycache__` SURVIVED A MUTATE/RESTORE CYCLE AND SILENTLY TESTED
   THE UNMUTATED CODE — A NEW MEMBER OF THIS REPO'S BATTERY-HAZARD FAMILY.**
   `restore()` copies the snapshot back with `shutil.copy2`, which
   **preserves the original mtime**, so a `.pyc` written during one arm can
   still satisfy Python's (mtime, size) validity check during a later one.
   Two arms reported **NOT RED** while the same mutation applied by hand
   outside the battery went red immediately — and NOT RED is
   indistinguishable from a test gap, so one of them was hand-debugged as a
   missing assertion before the cause was found. `PYTHONDONTWRITEBYTECODE=1`
   in the subprocess environment took the battery from 10 RED / 2 survived to
   **12 RED / 0**. The battery now sets it itself and also verifies by hash
   that each mutation actually changed the file.
5. **The crop pass's first render was unadjudicable** (§5) and would have
   produced verdicts anyway.

⚠️ And two arms are held OUT of the battery as **EQUIVALENT MUTANTS**, named
in `mutate.py` rather than left in the list: dropping the height FLOOR, and
skipping the vertical opening. They are two sides of one identity — the
opening is by `(1, min_h)`, so **the opening IS the floor**, and either alone
is unobservable. Together they say the opening is **redundant** and could be
deleted; it is not deleted, because every figure here was taken with it in.

---

## 9. WHAT IS NOT ESTABLISHED

* **n = 2 documents, 2 publishers, 7 pages.** Nothing here is a rate beyond
  that, and the one thing measured on both plates that MATTERS — the quality
  score — **disagrees between them by 13.7 points**. A third publisher is
  what this needs, not more pages of these two.
* **No effect on a FILE is measured.** This is a GATHER change; `readjudicate`
  and `reexport_arm` are structurally blind to it and two full re-gathers were
  not taken. **Nothing here says a single note comes out differently.**
* **ACCURACY IS NOT ESTABLISHED on Litolff.** The crop pass could not
  adjudicate 5 of 12 tiles there. The 82.6% is a convention score, the
  convention is read off the same page as the reader, and
  `width_cap_check.py`'s own caveat applies unchanged: *"the two are not
  independent of the PAGE, only of each other's METHOD."*
* **The estimated-real figures (~71%, ~97%) are a MIXTURE MODEL**, inherited
  from `width_cap_check.py`, assuming junk agrees at chance. That assumption
  is not tested.
* **The `TALL` bucket is out of reach BY CONSTRUCTION** (§2) — 476 heads on
  Breitkopf, the plate's largest cause, untouched. A y-cut is a different
  reader.
* **The attribution fault of §6 is diagnosed on 6 tiles of one publisher** and
  is not measured at population scale. Its repair is in a file this branch
  does not own.
* **The `side` variant is measured and NOT shipped**, so the 2.4× stroke-cost
  saving is an unrealised number.
* **Whether the added strokes help or harm BEAMS is completely unmeasured**,
  and that is the prize the handoff names (`A-DUR-8`: 12 assessable / 7
  correct → 16 / 16). 1,074–2,157 extra strokes enter `detect_beams` and
  `rhythm._beams_attached_to_stem` with the flag on. **This is the largest
  open risk and it is the reason the flag is off.**
* **The engraved family is untouched**, by construction.
* **No OMR-NED figure**, deliberately.
* ⚠️⚠️ **THE MIXTURE-MODEL FIGURES IN §4 ARE WITHDRAWN** (§4b): junk does not
  agree at chance on the one Litolff population checked against the print.
* **Why the reader declines the 576 thin Breitkopf boxes is not designed and
  not measured** — it may be the edge filter, the height cap or the anchor
  tolerance. Treat 12 of 576 as an observation, not a guarantee.
* **The 5.5% / 37.7% denominator contamination is a DETECTOR property that
  differs 7x between two plates**, and nothing here says which is typical.

---

## 10. RANKED NEXT WORK

1. **The ATTRIBUTION repair (§6)**, in `adjudicate_stem_direction`: a stroke
   belongs to the head at ONE OF ITS ENDS, not to every head it crosses.
   Diagnosed from the print here, 6 of 6 on Breitkopf, and it is where that
   plate's whole residual lives.
2. **Two re-gathers with the flag on**, to price the beam and duration effect
   — the only measurement that can say whether this is worth having.
3. **A third publisher — for the DENOMINATOR, not the tie.** The 82.6 / 96.3
   gap is now substantially an artefact of the arbiter (§4b); what needs a
   third plate is the 5.5% vs 37.7% non-notehead contamination, which is a
   detector property differing 7x between two editions.
4. **Thread the noteheads into `detect_stems`** so the convention anchor can
   ship — 2.4× fewer strokes for ~1% of reach, measured here.
5. **A y-cut for the `TALL` bucket** (476 Breitkopf heads), which no column
   profile can reach.

---

## PROPOSED CLAUDE.md PARAGRAPH

*(For Sean to paste; CLAUDE.md was not edited.)*

> | `OMR_STEM_STROKE` | `0` (off) | **A stem read from a COLUMN PROFILE instead of from a connected component. It HOLDS on one publisher of two, and the reason it is OFF is that its effect on BEAMS is unpriced — not that its recoveries look wrong.** `detect_stems` is a component reader, and `benchmarks/omr-stem-ink-2026-09`'s census says the dominant failure on both plates is *a component EXISTS and is the wrong SHAPE*. On, `_column_stroke_bands` reads each column's LONGEST vertical ink run and bands adjacent columns only where they AGREE about that run's endpoints — never labelling a component, so a stem fused to its own notehead is no longer measured at the NOTEHEAD's width. ⚠️⚠️ **§5's falsification does NOT fire: the stroke IS separable inside a fused blob** — 92.1% / 73.6% of `too WIDE` components hold a separable band — and the profile re-finds **98.0% / 98.2%** of the strokes `detect_stems` already accepts, the positive control the rest rests on. ⚠️⚠️ **REACH MUST BE READ OVER A CLEANED DENOMINATOR, because a third of the Breitkopf population is not a notehead: 576 of 1,529 boxes (37.7%) are thinner than a notehead can be (Litolff 44 of 793, 5.5%), independently reproducing a sibling crop pass's sampled 35.6% from a different instrument.** Over boxes that can plausibly BE noteheads the reach is **338 of 749 (45.1%)** and **532 of 953 (55.8%)** — more than half the Breitkopf job, where the unrestricted figure reads 35.6%. ⚠️ **The barline hazard is measured and absent**: the reader fires on **12 of 576** thin boxes (2.1%) and restricting the score moves it 96.3% → **96.2%** and 82.6% → **82.6%**, so neither figure is inflated by two readers agreeing about the same vertical rule. ⚠️⚠️ **QUALITY: Breitkopf 96.2% against a 98.2% bar — it HOLDS. Litolff 82.6% against 96.1% — and that is UNDETERMINED rather than a refusal.** The first write-up refused it as *"indistinguishable from the 83.6% at which `width_cap_check.py` refused the width cap"* and read both through that arm's mixture model as ~73% real; **the same sibling crop pass put those very recoveries to the print and they are 33 of 33 REAL, 0 junk (95% lower bound 0.913), so an ~83% convention score on this plate meant ~100% real and the mixture model is REFUTED.** The convention probe UNDERSTATES Litolff, which is what this lane's own crops said from the other side when they could not adjudicate 5 of 12 tiles. **~62% of the reach is shared with that width cap, which therefore makes it the better-evidenced part rather than a liability.** ⚠️⚠️ **THE CROP PASS THE STEM THREAD HAS OWED SINCE 2026-09-17 IS DONE (600 dpi, frame control 18/18, stratified and declared): Breitkopf's AGREE stratum is 6 of 6 textbook, and its DISAGREE stratum is 6 of 6 ONE FAULT — the record's notehead box stands part-way ALONG a neighbouring note's stem, so the stroke is real and the ATTRIBUTION is wrong.** That repair belongs in `adjudicate_stem_direction` and **cannot be made here: `detect_stems` emits STROKES, not (stroke, head) pairs**, which is why an end-at-the-head constraint built from those crops moved disagreements 40 → 40 and 14 → 14 — the fifth dead hypothesis on this thread, kept with its numbers. ⚠️ **It also corrects the handoff's §3**: the 8.1-space fused blob is ONE SPOT-CHECKED CELL, and over 2,001 cells of both plates the median component is **4.18 / 3.20 spaces** with only **6%** past the width cap — the typical component is stem-shaped, genuine merges across notes are **9.6% / 12.0%**, and ~94% of the over-cap mass covers NO notehead at all, i.e. is the furniture the cap exists for. ⚠️ **The `TALL` bucket is out of reach BY CONSTRUCTION** (7.0% / 8.3%): a column profile separates across x and not along y — and on Breitkopf that bucket is where the crop pass found 12 of 12 barlines, so it is the wrong place to test transfer anyway. ⚠️ `STEM_STROKE_AGREE_SPACES = 0.25` sits on a **PLATEAU** (reach 289/281/279/274/270 and 376/375/374/374/374 across 0.10–0.60), not an empty interval. ⚠️ Additive and it runs AFTER the pair rule, so flag-off is byte-identical — **asserted directly against both shared records, 1,920 = 1,920 on 1,183 of 1,183 cells and 2,305 = 2,305 on 818 of 818** — which matters because this file is on the path every sibling arm proves faithful before reporting a delta. ⚠️ **A GATHER change**, so `readjudicate` and `reexport_arm` are structurally blind and **no effect on a FILE has been measured**; the 581–1,074 extra strokes reaching `detect_beams` are the only remaining reason this is off. ⚠️ No OMR-NED figure, deliberately. Allow-list OFF test, correct for a default-OFF flag. Suite 4,477 passed; battery 12 arms 12 RED. See [benchmarks/omr-stem-stroke-2026-09/FINDINGS.md](benchmarks/omr-stem-stroke-2026-09/FINDINGS.md). |

> ⚠️⚠️ **AND A NEW CLAUSE ON THE MUTATION-BATTERY RULE, PAID FOR ON 2026-09-18: `__pycache__` SURVIVES A MUTATE/RESTORE CYCLE.** `restore()` copying a snapshot back with `shutil.copy2` **preserves the original mtime**, so a `.pyc` written during one arm can still satisfy Python's (mtime, size) validity check during a later one — and that arm then imports the UNMUTATED code and reports **NOT RED**, which is indistinguishable from a test gap. Two arms were affected and one was hand-debugged as a missing assertion before the cause was found; the same mutation applied by hand outside the battery went red immediately. `PYTHONDONTWRITEBYTECODE=1` in the subprocess environment took the battery from 10 RED / 2 survived to **12 RED / 0**. So the rule grows a third clause:
>
> > **A mutation battery must leave the tree as it FOUND it — which is not the same as leaving it as GIT has it, AN INTERRUPTED BATTERY OBEYS NEITHER, and A RESTORE THAT PRESERVES mtime CAN LEAVE THE OLD BYTECODE IN CHARGE.**
>
> The cheap prophylactics are all three: commit a checkpoint first, write an in-flight sentinel, and disable bytecode in the arms — plus verify by hash that each mutation actually changed the file, because an anchor that matches once and a write that succeeds are not evidence that anything moved.
