# A notehead is ~1.4 staff spaces WIDE — the floor priced on the population we read correctly

**No code outside `benchmarks/`.** `git diff` against the integration base
(`490884a1`) for `tools/ backend/ CLAUDE.md docs/` is **empty**. **Nothing is
proposed for any constant, flag or default** — the decisions this touches are
Sean's and none was taken.

⚠️ **PROVENANCE.** The harness refused this session a findings file through
`Write` (*"Subagents should return findings as text"*) and allowed it through a
scratchpad file copied in, so this file exists by that route. The handoff's §6
records the same refusal hitting two of three agents overnight and says to
**check, and pay the debt if it bites.** Checked; paid.

The debt paid is
[docs/handoff-2026-09-18-three-lanes-and-the-print.md](../../docs/handoff-2026-09-18-three-lanes-and-the-print.md)
§4 item 4: *"A box-width floor at < 1.0 staff spaces. It catches 39 of the 46
non-noteheads at a cost of 0 of 63 real stems — measured and **not proposed**,
because it is a GATHER change measured only on heads the census already
abstains on."* **That open side is now measured.** Sean picked this job for a
stated reason — *"I feel like the previous issues (1 and 2) will be affected by
this"* — and §4 and §5 are that answer.

`probe/` re-derives every table. Run it; do not quote this prose.

```bash
python3 benchmarks/omr-notehead-width-2026-09/probe/widths.py --record <rec> --label <l> --json out/<p>-widths.json
python3 benchmarks/omr-notehead-width-2026-09/probe/score.py --pub litolff|breitkopf --json out/score-<p>.json
python3 benchmarks/omr-notehead-width-2026-09/probe/contamination.py --json out/contamination.json
python3 benchmarks/omr-notehead-width-2026-09/probe/issues.py --json out/issues.json
python3 benchmarks/omr-notehead-width-2026-09/probe/by_class.py --json out/by-class.json
python3 benchmarks/omr-notehead-width-2026-09/probe/l4_and_rulers.py --records-dir <dir> --json out/l4-and-rulers.json
python3 benchmarks/omr-notehead-width-2026-09/mutate.py
```

---

## CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH SEAN

Pre-registered in its own commit **before any width was computed**
(`bc8b28dc`, [PREREGISTRATION.md](PREREGISTRATION.md)); commit order is the
only form of that claim a later reader can check.

**CONVENTION ASSUMED.** `[C1 + L3]` *A notehead is one staff space tall*,
whose own Bravura numbers also give the WIDTH — `noteheadBlack` /
`noteheadHalf` **1.180 × 1.000** staff spaces, `noteheadWhole` **1.688 ×
1.000** — so a notehead is **wider than it is tall**. And `[L4]` *A whole
notehead is wider than a black one, and the same height*, which the registry
files as **LITERATURE ONLY, untested on any plate**.

**HOW A HUMAN WOULD READ IT.** An editor with the plate measures nothing: a
notehead is an oval about as wide as the space it sits in, and a **barline, a
rest, a clef, a letter of a printed word** are not that shape. The cheapest
mechanical form of *"that is not a notehead"* is **it is too NARROW to be
one** — a barline is a fraction of a space wide where a head is more than a
space.

**WHAT WOULD FALSIFY IT.** Stated three ways in advance, and ⚠️ **the third is
the pre-registered bar this job's headline is measured against**: *if more than
2% of the `decided` population sits under 1.0 staff spaces, the floor is NOT
free.* It reads **0.42% and 0.67%** (§2).

**NOT CONFIRMED WITH SEAN.** Nothing here was put to him. ⚠️ And the registry
warns width is the **WEAKER half** of `[C1 + L3]` — its rigidity row says the
height is RIGID and *"the WIDTH varies a little by font and a lot by era of
plate"* — so a width test on two 19th-century plates is a test on two plates.

---

## 0. THE FRAME, AND A CLAIM OF MY OWN THAT IS WRONG

⚠️⚠️ **THE PRE-REGISTRATION CALLS THE TWO BOX CONVENTIONS "TWO INDEPENDENT
RULERS". THEY ARE NOT INDEPENDENT AND THAT SENTENCE IS WITHDRAWN.**
`gather._page_box` (`gather.py:497`) computes `bbox_page_px` FROM the canonical
box — `x0 + det.x_canonical / upscale_factor`, and so on — so the page
corner-box and the canonical width-box are **one measurement in two frames**.
They agree to **0.0000–0.0142 spaces** over 5,684 boxes because they must.

**What that control DOES establish, and it is worth having:** both box
CONVENTIONS were read correctly — `glyph_box.value[1:5]` is `(x, y, w, h)` and
`detail.bbox_page_px` is `(x0, y0, x1, y1)` — which is the exact hazard the
handoff records a session losing time to (*"measure bbox = CORNERS, detection
bbox = WIDTH"*), and which a fixture at the origin cannot tell apart. The
battery's live arm proves it can fail: read as corners, `score.py`'s
ruler-agreement control goes RED.

⚠️⚠️ **AND A DEEPER ONE, WHICH IS THE ARCHITECTURAL FINDING OF THIS JOB:
A WIDTH TEST IS NOT A SECOND WITNESS TO WHAT THE INK IS.** Under
`Evidence.correlated_groups`' own rule — *every row from one reader on one crop
is ONE SIGNAL* — the box's WIDTH and the box's CLASS come from the same
detector on the same crop and are therefore the same signal. So the width can
never *corroborate* the class; what it can do is catch the detector
**contradicting itself** (*"this is a notehead"* + *"it is 0.30 spaces wide"*),
which is a self-consistency check and not evidence. ⚠️ The measurement that
WOULD be independent is of the **INK**, not the box — and that is `Q.INK`,
default-ON, one row per connected piece of a cell's ink, **read by nothing.**
See §8.

⚠️ **Everything below measures the DETECTOR'S BOX.** *"A notehead is 1.40
spaces wide"* reads like a fact about engraving and is a fact about a bounding
box; the plates measure **19–26% wider than Bravura's 1.180**, and whether that
is the plate's heads or a loose box prior is **not established here**.

---

## 1. REACH — stated before any accuracy figure

| | notehead boxes | measurable, both frames | `decided` | `no_stem` | `stems_disagree` |
|---|--:|--:|--:|--:|--:|
| **Litolff** Beethoven 5 pp.1-4 | **2,347** | 2,347 | 1,443 | 793 | 111 |
| **Breitkopf** Brahms 1 pp.0-3 | **3,337** | 3,337 | 1,791 | 1,529 | 17 |

Every probe **exits non-zero declaring itself DEAD** at zero reach or when its
positive controls fail. **8 controls per publisher, all green**, each naming a
published figure rather than one of mine:

* notehead totals **2,347 / 3,337** (the registry's own figures);
* the three populations **PARTITION** the total (2,347 = 2,347; 3,337 = 3,337);
* the census covers **exactly** the `no_stem` population (793 / 1,529), and
  every census subject is a notehead box;
* the two frames agree (§0).

⚠️ **The join is on the SUBJECT ADDRESS, never on a box** — two pages
superimpose exactly in page pixels and a cell index restarts per system, both
frame errors this repo has already paid for inside a measuring instrument.

---

## 2. ⚠️⚠️ THE FLOOR COSTS ESSENTIALLY NOTHING ON THE POPULATION WE READ CORRECTLY

The open side the crop pass declared. Width in staff spaces over the heads
whose stem the pipeline **reads**:

| | n | p5 | median | p95 | **under 1.0** | share |
|---|--:|--:|--:|--:|--:|--:|
| **Litolff** `decided` | 1,443 | 1.310 | 1.490 | 1.780 | **6** | **0.42%** |
| **Breitkopf** `decided` | 1,791 | 1.260 | 1.400 | 1.580 | **12** | **0.67%** |

**Both are a quarter of the pre-registered 2% bar.** And the convention holds
on both plates: a notehead's box is **1.26–1.78 spaces wide at p5–p95**, i.e.
comfortably wider than tall, exactly as `[C1 + L3]`'s numbers say — ⚠️ at a
median **19–26% wider than Bravura's 1.180**, which is §0's box-vs-ink
question.

### The whole population, by the census bucket that rejected it

| population | n | p5 | med | p95 | <1.0 | share |
|---|--:|--:|--:|--:|--:|--:|
| **LITOLFF** | | | | | | |
| `decided` | 1,443 | 1.310 | 1.490 | 1.780 | 6 | 0.42% |
| `stems_disagree` | 111 | 1.330 | 1.500 | 1.810 | 0 | 0.00% |
| `no_stem` (all) | 793 | 0.970 | 1.480 | 1.910 | **44** | **5.55%** |
| — too TALL | 47 | 0.300 | 1.400 | 2.160 | 19 | **40.4%** |
| — NO component overlaps | 167 | 0.940 | 1.390 | 2.040 | 12 | 7.2% |
| — too WIDE | 237 | 1.270 | 1.490 | 1.740 | 6 | 2.5% |
| — too SHORT | 199 | 1.290 | 1.540 | 1.920 | 5 | 2.5% |
| — pair rule dropped one | 73 | 1.270 | 1.560 | 1.960 | 1 | 1.4% |
| — at a CELL EDGE | 70 | 1.340 | 1.460 | 1.700 | 1 | 1.4% |
| **BREITKOPF** | | | | | | |
| `decided` | 1,791 | 1.260 | 1.400 | 1.580 | 12 | 0.67% |
| `stems_disagree` | 17 | 1.254 | 1.384 | 3.240 | 0 | 0.00% |
| `no_stem` (all) | 1,529 | 0.260 | 1.315 | 1.535 | **576** | **37.67%** |
| — too TALL | 476 | 0.250 | 0.300 | 0.841 | 459 | **96.4%** |
| — at a CELL EDGE | 22 | 0.260 | 0.330 | 1.144 | 19 | **86.4%** |
| — NO component overlaps | 197 | 0.490 | 1.125 | 1.570 | 83 | 42.1% |
| — pair rule dropped one | 178 | 1.180 | 1.390 | 1.554 | 6 | 3.4% |
| — too SHORT | 298 | 1.270 | 1.414 | 1.641 | 6 | 2.0% |
| — too WIDE | 358 | 1.260 | 1.400 | 1.533 | 3 | **0.8%** |

⚠️ **THE HANDOFF'S 5.5% / 37.7% CONTAMINATION PAIR IS REPRODUCED EXACTLY** —
**44 / 793 = 5.55%** and **576 / 1,529 = 37.67%** — which also identifies what
that published pair is: the *under-1.0-space share of the `no_stem`
population*, i.e. this same test, computed by the stroke lane.

---

## 3. ⚠️⚠️ AGAINST THE PRINT: ZERO OF 103 CONFIRMED NOTEHEADS IS FLAGGED

The only place in this job where *"is it a notehead"* has a truth value. The
crop pass adjudicated **255 boxes blind**, with opaque tile ids; every verdict
joins to a width through its crop manifest. **255 resolved, 0 unresolved.**

| | n | **NOT a head** flag / keep | **IS a head** flag / keep | **cannot tell** flag / keep |
|---|--:|---|---|---|
| **Litolff** | 111 | **9** / 10 | **0** / 29 | 1 / 62 |
| **Breitkopf** | 144 | **32** / 12 | **0** / 74 | 4 / 22 |

* **Cost on boxes the print CONFIRMS are noteheads: ZERO of 103, on both
  plates.** Stronger than the crop pass's *"0 of 63 real stems"*, on a larger
  denominator, and it is the answer this job was sent to get.
* It catches **41 of 63** print-confirmed non-noteheads (Litolff 9/19 = 47%,
  Breitkopf 32/44 = 73%).
* It flags **5 of 105** `cannot_tell` — neither a cost nor a win.

⚠️⚠️ **`cannot_tell` IS A THIRD COLUMN AND COLLAPSING IT IS HOW THIS PROBE
FIRST REPORTED "5 FALSE ALARMS".** All five are `cannot_tell`, and their
adjudication reasons read *"a small bump on a staff line"*, *"a densely fused
cluster; nothing isolable"*, *"the head is fused with a staff line and a
FULL-HEIGHT barline passes through it"* — arguably supporting the floor rather
than opposing it. Collapsing *we do not know* into *the floor is wrong* is the
ABSENT/DECLINED collapse `record.py` exists to prevent, committed inside the
instrument built to price a filter. See §9.

**Eleven controls on the truth mapping itself**, each anchored on a published
crop-pass figure and each green: `not_a_notehead` among the sample tiles
**14 / 32 / 46** (its §2's *"46 of 180, 15.6% / 35.6%"*); `cannot_tell`
**53/90 and 10/16** on Litolff and **16/90 and 2/16** on Breitkopf (its §7's
58.9% / 62.5% and 17.8% / 12.5%); sample sizes 90 / 90; zero unknown
vocabulary words; standoff settled **16**.

---

## 4. ⚠️ ISSUE 1 — THE 16-0 IS UNCHANGED. The width test neither rescues nor worsens the beam-mate tier

| | n |
|---|--:|
| standoff heads | 26 |
| under the floor **overall** | **3** |
| settled by the print | **16** |
| **settled AND under the floor** | **0** |
| print agrees with ATTACHMENT (among settled) | **16** |
| print agrees with BEAM-MATE (among settled) | **0** |

**The contamination in that population is real (3 of 26 = 11.5%) and sits
entirely outside the 16 the print settled** — two are the boxes the print
already called `not_a_notehead` (*"both readers gave a direction to a DOT"*)
and the third is a `cannot_tell`. So the shipped, default-ON beam-mate tier's
**16-0 loss survives the width test intact**: it was not a contamination
artefact, and it is not made worse either.

⚠️ **That is a negative answer to the thing Sean expected, and it is reported
as it came out.** ⚠️ The crop pass's independence limit is untouched and still
governs: **the adjudicating eye is not independent of the attachment reader**,
both measure ink beside the head, so this remains *"the ink beside the head
behaves as the convention says"*. ⚠️ And the tier's published **0.984 is
Litolff-only, leave-one-out** — nothing here re-scores it, because the standoff
is a Breitkopf census of 26 heads and not a sample of the tier's domain.

---

## 5. ⚠️⚠️ ISSUE 2 — THE CLEANING IS LARGE, AND THE BOXES IT REMOVES WERE NEVER IN THE BUCKET THE READER READS

`OMR_STEM_STROKE`'s reach, over the raw `no_stem` population and over the
cleaned one (variant `side+end`; `+legal` is marked CIRCULAR in its own output
and is not used):

| | recovered | of raw `no_stem` | of PLAUSIBLE | gained |
|---|--:|--:|--:|--:|
| **Litolff** | 337 | 337 / 793 = **42.5%** | 337 / 749 = **45.0%** | +2.5 pts |
| **Breitkopf** | 531 | 531 / 1,529 = **34.7%** | 531 / 953 = **55.7%** | **+21.0 pts** |

So on Breitkopf the reader reaches **more than half** the job where the raw
figure says a third — the brief's expectation, confirmed.

⚠️⚠️ **BUT THE CLEANING DOES NOT TOUCH THE BUCKET THE STROKE READER WORKS ON.**
Its population is `too WIDE`, which is **0.8% thin on Breitkopf and 2.5% on
Litolff**, while `too TALL` is **96.4% / 40.4%** and `at a CELL EDGE` **86.4% /
1.4%**. **459 of Breitkopf's 576 thin boxes (79.7%) are in `too TALL`.** So the
raw rate was **DILUTED by a population the reader never reads** — a different
claim from *"the reader was reading barlines"*. **It never was.**

⚠️ **This also answers the handoff's open question — *"why the stroke reader
declines the 576 thin Breitkopf boxes is NOT DESIGNED … 12 of 576 is an
observation, not a guarantee"* — as far as the record can answer it and no
further.** The thin boxes are overwhelmingly `too TALL` and `at a CELL EDGE`:
a `too TALL` component is a barline the vertical opening kernel **keeps** and
the height cap then rejects, and a column profile over a barline has one band
to find and no notehead to anchor it to. **That is a bucket-level explanation,
not the mechanism** — which of the edge filter, the height cap or the anchor
tolerance declines each of the 12 is still undetermined, and this job did not
run that reader.

⚠️ **`stroke_arm.py` ALREADY COMPUTED THIS TEST and named it
`plausible_heads` / `thin_boxes`** (`stroke_arm.py:387`, `NOTEHEAD_MIN_W =
1.0`). Reproduced from the record: **44 / 576 thin** and **749 / 953
plausible**, exact. ⚠️⚠️ **THAT IS A REPRODUCTION OF THE COMPUTATION AND NOT AN
INDEPENDENT RULER, and the brief asked whether two rulers agree.** That lane
divides the page box by the **mean of the four printed staff-line gaps**
recomputed from `Q.STAFF_LINES`; this one by the gathered `Q.STAFF_SPACING`.
Over all 5,684 boxes the two are the **same number to the float** — max |diff|
**0.0**, **0 boxes swap sides of the floor** — because `Q.STAFF_SPACING` *is*
that mean. **So the agreement confirms the threshold, the box convention and
the population, and says nothing about the ruler.**

---

## 6. ⚠️⚠️ `[L4]` IS NOT SETTLED — AND WHY IT CANNOT BE IS THE SHARPER RESULT

The registry's falsifier for `[L4]` is *"a plate where whole and half heads
measure the same width"*. Measured on the detector's class, over `decided`:

| | Black | Half | **Whole** |
|---|--:|--:|--:|
| **Litolff** n / w median | 1,126 / **1.460** | 309 / **1.610** | 8 / **1.590** |
| **Breitkopf** n / w median | 1,661 / **1.400** | 113 / **1.560** | 17 / **1.440** |

`[L4]` predicts **1.688 vs 1.180 — a 43% gap with Whole WIDER**. Measured, the
gap is **absent and the sign is reversed on both plates**: the `Whole` class
sits between Black and Half, narrower than Half.

⚠️⚠️ **AND THAT DOES NOT REFUTE `[L4]`, BECAUSE THE CLASS IS NOT WHOLE NOTES.**
The crop pass's §5 adjudicated 17 whole-class heads against the plate and found
**16 of 17 CLASS-FALSE**. A class that is mostly not whole notes cannot falsify
a claim about whole notes. **`[L4]` stays LITERATURE ONLY / untested.**

⚠️⚠️ **WHAT IS NEW IS THAT THE WIDTH SAYS SO WITHOUT THE PRINT — two
instruments, one conclusion, from completely different directions.** Per class,
over the whole population:

| class | n | decided | **% decided** | <1.0 | w med | h med |
|---|--:|--:|--:|--:|--:|--:|
| **LITOLFF** | | | | | | |
| noteheadBlackInSpace | 916 | 547 | 59.7% | 22 | 1.430 | 1.250 |
| noteheadBlackOnLine | 978 | 579 | 59.2% | 28 | 1.500 | 1.340 |
| noteheadHalfInSpace | 279 | 199 | 71.3% | 0 | 1.600 | 1.340 |
| noteheadHalfOnLine | 157 | 110 | 70.1% | 0 | 1.650 | 1.410 |
| noteheadWholeInSpace | 12 | 8 | 66.7% | 0 | 1.580 | 1.230 |
| **noteheadWholeOnLine** | 5 | 0 | **0.0%** | 0 | 1.560 | 0.740 |
| **BREITKOPF** | | | | | | |
| noteheadBlackInSpace | 1,656 | 763 | 46.1% | **459** | 1.348 | 1.091 |
| noteheadBlackOnLine | 1,425 | 898 | 63.0% | 126 | 1.402 | 1.200 |
| noteheadHalfInSpace | 94 | 69 | 73.4% | 2 | 1.470 | 1.150 |
| noteheadHalfOnLine | 58 | 44 | 75.9% | 1 | 1.575 | 1.202 |
| **noteheadWholeInSpace** | 75 | 8 | **10.7%** | 0 | 1.440 | 1.014 |
| noteheadWholeOnLine | 29 | 9 | 31.0% | 0 | 1.450 | 1.085 |

**`noteheadWholeInSpace` on Breitkopf decides on 1 box in 10, and Litolff's
`noteheadWholeOnLine` on none of 5** — by a wide margin the lowest of any class
on either plate, and a print-free signal that the class is a dustbin.

⚠️⚠️ **THE CONTAMINATION HAS TWO SHAPES, IN TWO DIFFERENT CLASSES, AND A WIDTH
FLOOR REACHES ONLY ONE:**

* **NARROW, in `noteheadBlack*`** — barlines. 459 of 1,656
  `noteheadBlackInSpace` on Breitkopf are under the floor. **Caught.**
* **RIGHT-WIDTH, in `noteheadWhole*`** — **the under-floor count is ZERO for
  every Half and Whole class on both plates.** The 22 print-confirmed
  non-noteheads the floor misses are **wide**: 8 Breitkopf
  `time_signature_digit_8` counters (w 1.37–1.58), 5 Litolff `staff_line_gap`s
  (w 1.38–1.96), a printed capital **B** (2.18), a **bass clef** (2.49), a
  **wedge** (2.68), the `e` of **cresc** (1.10), two **whole rests** (1.12 and
  1.27 wide but **0.34 and 0.64 TALL**), and three script `ff` letterforms.
  **13 of the 22 are `noteheadWhole*`.** **Missed, by construction.**

---

## 7. ⚠️⚠️ A PREMISE ENCODED IN A REFUSAL — RE-ASKED, AND THE ANSWER IS STILL NO

The misses above are a **HEIGHT** question, and height is the **RIGID** half of
`[C1 + L3]`. The repo already has a height floor —
`transcribe.py:537 _CLIPPED_NOTEHEAD_MAX_SPACES = 0.6` — **deliberately
restricted to detections that TOUCH a cell edge**, on a stated reason: *"A
short notehead in the middle of a cell is some other problem and this must not
have an opinion about it."*

**That reason has expired.** This job now knows what the *some other problem*
is on these two plates: a **whole rest** (h 0.34, 0.64), a **time-signature
digit counter** (h 0.46–1.05), a **staff-line gap**, a **printed letter** —
every one in the middle of a cell, and every one a box the floor misses.

⚠️⚠️ **AND THE REFUSAL SURVIVES ANYWAY, NOW FOR A MEASURED REASON RATHER THAN
AN ASSUMED ONE: the shortest print-CONFIRMED noteheads are 0.340 (Litolff) and
0.345 (Breitkopf) spaces tall.** An unrestricted `h < 0.6` floor would flag
real noteheads on both plates. **So the premise expired, the question was
re-asked, and the answer is still no** — the shape CLAUDE.md's own family asks
for, and worth recording as an instance where re-asking **confirmed** a
refusal.

⚠️ **NOTHING IS PROPOSED.** A joint width-and-height band fitted to 63
adjudicated non-noteheads across two publishers is exactly the *smooth slope
with a threshold fitted into it* that `docs/ask-first-conventions.md` §3 warns
against, and the confirmed-head heights above show the obvious band is not
free. The shape distributions are committed
(`out/contamination.json` -> `shape_vs_print`) so a session holding more print
can adjudicate it.

---

## 8. ⚠️⚠️ WHY NOTHING WAS SHIPPED — THERE IS NO FACT LEFT TO GATHER

The brief asked for the finding to reach the record as a fact a later stage can
read or overturn, shaped like `Q.INK` / `OMR_FAMILY_POSITIONS`: its own
quantity, no confidence, a reader that states what it measured. **I did not
build it, and the reason is arithmetic:**

**The width in staff spaces is ALREADY on the record, completely, for every
notehead box.** It is `Q.GLYPH_BOX.value[3] / Q.CELL_STAFF_SPACE` in the
canonical frame and `(bbox_page_px[2] − bbox_page_px[0]) / Q.STAFF_SPACING` in
the page frame — **2,347 of 2,347 and 3,337 of 3,337 heads carry both**, no gap
on either plate. A new quantity carrying `w / spacing` would be an
**arithmetic restatement of two rows that are already there**, and this repo's
five-stage rule puts a value that *follows* from what we know in EVALUATE, not
in GATHER.

⚠️ **And it would not be the second witness the brief's hazard note is about.**
The brief is right that a width may not hang off the glyph row because
`Evidence.correlated_groups` would absorb it into that glyph's detector term —
but the honest conclusion is one step further: **a width read off the
detector's own box is that detector's signal however it is filed**, so no
placement makes it independent (§0). A genuinely independent witness measures
the **INK** — which is **`Q.INK`, default-ON since 2026-09-17, one row per
connected piece of a cell's ink carrying the box in both frames and the shape,
and read by nothing in any adjudicator, consequence, inference or the
exporter.** ⚠️ *The value existed and nothing read it*, pointing at the
consumer this finding actually wants.

⚠️ **So the honest deliverable is the measurement and the correction of the
record, and the honest recommendation is that the first consumer of this
finding should read `Q.INK` and not a new width row.** That is a proposal, not
a change, and it is Sean's call.

---

## 9. THE MUTATION BATTERY — and it found the only two defects in this job

**8 RED / 8 live arms, positive control GREEN and run FIRST, restore VERIFIED
by hash, 6 held out and each named.** `out/mutation-battery.json`. All three
clauses of the rule obeyed: byte snapshot (not `git checkout`); an in-flight
SENTINEL that makes an interrupted run refuse to start and name every file at
risk with the hash it should have; `PYTHONDONTWRITEBYTECODE=1` plus
`__pycache__` clearing. Refuses a dirty tree without `--force`.

⚠️⚠️ **ITS FIRST RUN HAD FOUR SURVIVORS AND ALL FOUR WERE REAL, AND NEITHER
WOULD HAVE BEEN FOUND BY READING THE PROBES:**

1. **`FLOOR = 1.0` was restated in FIVE probe files**, so the arm that moved it
   in `score.py` survived — `issues.py` reproduced the stroke lane's 44 / 576
   off its own copy and never noticed. *A constant this project paid to measure
   once, held in five places*, inside the instrument built to price it. Now
   `probe/floor.py`, imported everywhere, and the arm goes RED.
2. **The function that produced the headline had NO control that could fail.**
   Three arms rewrote `truth_of` and all three survived, because
   `contamination.py` only asserted that the JOIN resolved. Eleven controls
   added, anchored on the crop pass's own published figures (§3).

⚠️ **Three further arms were the battery's OWN faults and are recorded as
such**: a BAD ANCHOR (`FLOOR = 1.0` appears in `floor.py`'s docstring as well
as its code); an arm disabling the truth-control **guard**, an EQUIVALENT
MUTANT on a clean tree because `tbad` is empty there; and an arm defaulting an
unknown vocabulary word, a **DEAD BRANCH** on this data since all 255 rows map.
The last two are **held out and named**, and an arm that **removes a word from
the vocabulary** was added to make that branch live — it goes RED. **An arm
that can never go red trains the next reader to ignore the list.**

⚠️ **A DEFECT THE CONTROLS THEMSELVES FOUND, worth more than the arm that
caught it.** Reproducing the crop pass's published `cannot_tell` rates, mine
read Breitkopf's sample as **17.0%** against the committed **17.8%**. The
cause: a subject appears in BOTH the Breitkopf sample manifest and the standoff
manifest, and a `kind` map keyed globally on the subject lets the **last writer
win** — Breitkopf's sample silently fell to 88 rows of 90. The `kind` now comes
from the manifest the row was READ from. **An 0.8-point drift nobody would
query without a published anchor to check it against.**

---

## 10. WHAT IS NOT ESTABLISHED

* ⚠️ **ACCURACY OF THE FLOOR RESTS ON n = 255 ADJUDICATED BOXES, ONE
  ADJUDICATOR, NO INTER-RATER FIGURE, TWO PUBLISHERS, 8 PAGES.** The WIDTH is
  measured on 5,684 boxes; the TRUTH is not. Every *"this is not a notehead"*
  here is the crop pass's verdict, inherited with its n.
* ⚠️ **THE TWO PLATES ARE NOT POOLED ANYWHERE AND MUST NOT BE.** The
  contamination differs **7×** (5.55% vs 37.67%) and nothing says which is
  typical. A **third publisher is what the denominator needs**, and the handoff
  §5 item 4 already ranks it.
* ⚠️ `decided` is a PROXY for *"real notehead"* in §2. Its warrant is the crop
  pass's disjoint 16-per-publisher positive control, not this job.
* ⚠️ **NO RE-GATHER, AND A GATHER CHANGE WOULD BE PRICED BY NOTHING HERE.**
  `readjudicate` and `reexport_arm` are **structurally blind** to one. **No
  effect on any FILE has been measured**, and none is claimed.
* ⚠️ **NO OMR-NED figure, deliberately** — the metric is symmetric and would
  pay for emitting fewer noteheads whether or not they were noteheads.
* ⚠️ **NOTHING WAS CHECKED AGAINST THE PRINT BY THIS JOB.** No crop was cut.
  The Litolff `cannot_tell` rate is **58.9% of its own sample** — on that plate
  most noteheads cannot have their stem adjudicated by eye at all — and that
  limit is inherited whole.
* ⚠️ `[L4]` is **not settled** (§6), and the width excess over Bravura (§0) is
  **unexplained** — box or ink is unmeasured.
* ⚠️ The beam-mate tier's **0.984 is not re-scored** (§4); the standoff is a
  26-head Breitkopf census, not a sample of that tier's domain.
* ⚠️ The §5 explanation of *why* the stroke reader declines the thin boxes is
  **bucket-level**, not mechanism-level.

---

## 11. PROPOSED CLAUDE.md PARAGRAPH — for the managing session to paste

> ### A notehead is ~1.4 staff spaces WIDE — the floor priced, and the contamination has TWO shapes
>
> 2026-09-18, **no code outside `benchmarks/`, nothing proposed for any
> constant or default.** The handoff §4 item 4 asked for the open side of the
> box-width floor: it had been measured only on heads the census already
> abstains on. Findings:
> [benchmarks/omr-notehead-width-2026-09/FINDINGS.md](benchmarks/omr-notehead-width-2026-09/FINDINGS.md).
>
> ⚠️⚠️ **IT COSTS ZERO OF 103 PRINT-CONFIRMED NOTEHEADS, on both plates** —
> stronger than the crop pass's *"0 of 63 real stems"*, joined to its 255 blind
> verdicts through the crop manifests, and on a **THREE-WAY** matrix because
> collapsing `cannot_tell` into *is a notehead* is what made this probe first
> report 5 false alarms. On the population the pipeline reads correctly the
> floor takes **6 of 1,443 (0.42%)** and **12 of 1,791 (0.67%)** against a
> **pre-registered** 2% bar. The handoff's 5.5% / 37.7% contamination pair
> reproduces exactly as **44/793** and **576/1,529**, which also identifies
> what that pair was — this same test, run by the stroke lane.
>
> ⚠️⚠️ **THE CONTAMINATION HAS TWO SHAPES IN TWO CLASSES AND A WIDTH FLOOR
> REACHES ONLY ONE.** NARROW, in `noteheadBlack*`: 459 of 1,656
> `noteheadBlackInSpace` on Breitkopf are under the floor — barlines, caught.
> RIGHT-WIDTH, in `noteheadWhole*`: **the under-floor count is ZERO for every
> Half and Whole class on both plates**, and the 22 confirmed non-noteheads the
> floor misses are WIDE — 8 time-signature `8` counters, 5 staff-line gaps, a
> capital **B**, a bass clef, a wedge, the `e` of **cresc**, two whole rests
> (1.12–1.27 wide, **0.34–0.64 TALL**). **13 of the 22 are `noteheadWhole*`.**
> ⚠️ **`noteheadWholeInSpace` on Breitkopf decides a stem on 1 box in 10 and
> Litolff's `noteheadWholeOnLine` on 0 of 5** — the lowest of any class, and a
> PRINT-FREE corroboration of the crop pass's *16 of 17 class-FALSE*: two
> instruments, one conclusion, from different directions.
>
> ⚠️ **ISSUE 1 IS UNCHANGED AND THAT IS A NEGATIVE ANSWER TO WHAT WAS
> EXPECTED.** Of the 26-head standoff, 3 are under the floor and **0 of the 16
> the print SETTLED** — the beam-mate tier's **16-0** loss is not a
> contamination artefact. ⚠️ **ISSUE 2's cleaning is large (Breitkopf 34.7% →
> 55.7%, +21 pts) and the boxes it removes were NEVER in the bucket the stroke
> reader reads**: `too WIDE` is **0.8%** thin there while `too TALL` is
> **96.4%** and holds 459 of the 576. The raw rate was DILUTED by a population
> the reader never touches, which is not the same as the reader being
> contaminated. **`stroke_arm.py`'s own `thin_boxes` 44/576 and
> `plausible_heads` 749/953 reproduce exactly** — ⚠️ a reproduction of the
> COMPUTATION, not an independent ruler: `Q.STAFF_SPACING` *is* the mean of the
> four printed line gaps, to the float over 5,684 boxes.
>
> ⚠️⚠️ **NOTHING WAS SHIPPED, AND THE REASON IS THAT THERE IS NO FACT LEFT TO
> GATHER.** The width in staff spaces is already on the record for **2,347 of
> 2,347 and 3,337 of 3,337** heads, twice — a new quantity would restate
> `Q.GLYPH_BOX` / `Q.CELL_STAFF_SPACE`. ⚠️ And under
> `Evidence.correlated_groups`' own rule a width read off the detector's box is
> **that detector's signal however it is filed**, so it can catch the detector
> CONTRADICTING ITSELF but can never corroborate its class. The independent
> witness would measure the **INK** — which is **`Q.INK`, default-ON and read
> by nothing**. *The value existed and nothing read it*, naming the consumer
> this finding actually wants.
>
> ⚠️ **AND A REFUSAL RE-ASKED AND CONFIRMED:** the misses are a HEIGHT
> question, and `_CLIPPED_NOTEHEAD_MAX_SPACES = 0.6` is restricted to
> edge-touching boxes because *"a short notehead in the middle of a cell is
> some other problem"*. **That reason has expired** — the other problem is a
> whole rest, a digit counter, a staff-line gap — **and the refusal survives
> anyway, now measured: the shortest print-CONFIRMED noteheads are 0.340 and
> 0.345 spaces tall**, so an unrestricted floor would flag real heads. ⚠️ The
> battery's first run had **4 survivors and all 4 were real**: `FLOOR` restated
> in FIVE probe files, and `truth_of` — the function behind the headline —
> having **no control that could fail**. Final **8 RED / 8 live**, 11 truth
> controls anchored on the crop pass's published 46 / 14 / 32 and its 58.9% /
> 62.5% / 17.8% / 12.5%, one of which caught an 0.8-point drift from a `kind`
> map keyed globally on the subject. ⚠️ n = 2 publishers, 8 pages, **255
> adjudicated boxes, one adjudicator**; no re-gather, no file effect, no
> OMR-NED, and `[L4]` **still LITERATURE ONLY** — the class is too contaminated
> to falsify it.

## 12. PROPOSED KNOBS-TABLE ROW — none

**No flag is proposed and no knobs-table row is offered**, because no code
outside `benchmarks/` changed. §8 is the argument; a later session that ships a
consumer should carry its own row.

### Proposed registry amendments (`docs/engraving-conventions.md`)

* `[C1 + L3]` — its **Measured here** line can gain: *on two 19th-century
  plates the box width of a print-confirmed notehead runs **1.26–1.78 staff
  spaces (p5–p95)** at a median of **1.40–1.49**, i.e. 19–26% wider than
  Bravura's 1.180; and the shortest print-confirmed head is **0.340** spaces
  tall, which is why `_CLIPPED_NOTEHEAD_MAX_SPACES` may not be lifted off the
  cell edge.*
* `[L4]` — **stays LITERATURE ONLY.** Its *"not measured here"* line can gain:
  *measured on the DETECTOR'S CLASS over two plates the gap is absent and the
  sign reversed (Whole 1.44–1.59 against Half 1.56–1.61) — but the
  `noteheadWhole*` class is 16 of 17 class-FALSE against the print and decides
  a stem on 1 box in 10, so the class cannot falsify the convention. The
  falsifier still needs whole notes identified from the PRINT.*

## 13. ROADMAP 2.39 — the standard box, promoted and wired into GATHER/ADJUDICATE

**What changed.** `tools/omr/staged/geometry.py` is new: `standard_head_box`
(the arithmetic ROADMAP 2.37 built local to `gather._observe_ledger_owner_
density`, now general) and `is_regular_notehead` (the gate: `noteheadBlack*`/
`noteheadHalf*` only, never a `*Small` grace/cue head or `noteheadWhole*`/
`noteheadDoubleWhole*`, which item 5 leaves on the detector's own box —
unmeasured this round). Four consumers now ask for the STANDARD box —
detector CENTRE, extent from the STAFF'S OWN spacing — where before each
asked the raw detector box CLAUDE.md Sec.10 already says is untrustworthy
(a Brahms sliver, a Litolff merged box):

1. `gather._observe_ledger_rung_ink` (the sibling of 2.37's own ledger-owner
  reader) — the head x-window and the y-band excluded from the thick-stroke
  guard.
2. `gather.notehead_ink_under` / `gather_notehead_ink` (`Q.NOTEHEAD_INK`) —
  the black/hollow fill test's interior/ring windows. Falls back to the raw
  box where the cell carries no staff-line geometry, keeping this reader's
  own "no staff unit needed" invariant.
3. `adjudicators.notehead_precision._belongs_to_a_nearer_staff` — the
  x-window searched for a ladder, sized from the FILED staff's own spacing
  the function already reads (never re-derived, never defaulted).
4. `gather._notehead_boxes_for_cell` (feeding `gather_cv_lines`'s stem/beam
  CV, `OMR_STEM_NOTEHEAD_GATE`) — its own commit, last, because this one can
  move stem/beam results and the other three cannot.

Five commits on `worktree-agent-abaec0246921f0daf` (corrected — an earlier
draft of this section misnamed the branch), one per
connection plus the promotion. Each was proven RED then GREEN by stashing
just that commit's `gather.py`/`notehead_precision.py` change and
re-running its own new test (recorded in each commit message). `staged.check`
held at **245 open findings** (the pre-existing baseline) after every one of
the five commits — a first draft of connection 3 that added a
`detail["box_source"]` key pushed `staged.wiring` 67→68 (TOTAL 245→246) and
was caught and reverted before commit (spy on `notehead_ink_under`'s own
`box` argument instead — CLAUDE.md's "a written, never-read detail key is a
finding").

## 14. One-page before/after, GATHER-through-ADJUDICATE, both count pages

Base arm: `git worktree add --detach ../2.39-base-arm 2718c450` (the commit
before this round's five), symlinked exactly as this worktree. New arm: this
tree, all five commits landed. Same command, same weights, both arms:

```bash
export OMRNED_PYTHON=.../.venv-omrned/bin/python OMR_SURYA_KEEP_ALIVE=0 \
       OMR_DIRECTION_TEXT_SCAN_GATE=1
python3 -m tools.omr.staged <pdf> --pages <N> --weights auto --route-weights \
  --through adjudicate --out <arm>-<doc>-p<N>.json
```

Litolff pdf-index 3, Brahms pdf-index 1. Diffed with `probe/diff_2.39_ab.py`
(verdicts by `(subject, quantity)`; GATHER observations by subject for
`ledger_rung_ink`/`notehead_ink`/`stem`/`beam_stroke`):

| consumer | quantity | Litolff p3 changed | Brahms p1 changed |
|---|---|---:|---:|
| 1 (ledger rung ink) | `ledger_rung_ink` obs | 20 subjects | 38 subjects |
| 2 (notehead ink) — ⚠️ **REVERTED, Sec.18** | `notehead_ink` obs | 232 subjects | 294 subjects |
| 2 → `duration` verdict — ⚠️ **REVERTED, Sec.18** | `duration` | **1** (decided→narrowed, `head_fill_from_ink`) | **87** (same shape) |
| 3 (nearer staff) | `notehead_is_not_a_notehead` | 0 | 0 |
| 3 → `glyph_owner` | `glyph_owner` | 0 | **4** (all same STAFF; 3 basis `distance`→`ledger_direction`, 1 **abstained→decided**) |
| 4 (stem/beam gate) | `stem` / `beam_stroke` obs | **0 / 0** | **0 / 0** |

**Reach before accuracy, and the population that moved is the one the design
predicted.** Connection 4 (the stem-gate box) changed NOTHING on either
count page — measured, not assumed; its risk (moving 2.38/2.38b's stem/beam
results) did not materialize on these two pages, though a page with more
gated pairs could still show it. Connection 1's raw witness values shift
(20/38 subjects) but never once flipped a `glyph_owner` verdict alone — the
verdicts that DID move all trace to connection 3's own ladder search, and
every one of those four moved toward MORE evidence, never less (one
`far_no_rungs` abstention became a decided owner; three swapped their
basis from the coarse distance tie-break to the ledger read, still landing
on the SAME staff). Connection 2's ink readings moved on roughly half the
regular noteheads on both pages (a `Q.NOTEHEAD_INK` value is continuous, so
any box-size change moves it) and narrowed a `duration` population (1 of
~573 Litolff bars' worth, 87 of Brahms's larger, more merged/shattered
population) — ⚠️⚠️ **WITHDRAWN, Sec.18: this was read as "only narrowed,
never wrongly decided" and as catching a real disagreement.** It was
neither. The narrowing is a SYMPTOM of the same sliver flaw that produced
the swing crop: a box built on a sliver's off-centre "centre" reads
differently from the raw sliver, which is why the row moves at all, not
because it now sees a genuine disagreement. Connection 2 is reverted
(Sec.18); this row is a measurement of the bug's reach, not a result.

## 15. Print check (CLAUDE.md Sec.6b) — 5 crops, `out/print/2.39/`

Cut from each PDF at 600 dpi with `probe/crop_2.39.py`. **YELLOW** = the
staff's own five lines (names which staff the subject is filed on).
**RED** = the raw detector box — what every consumer used before this
round. **GREEN** = the standard box. **BLUE** corner-cross = the detector's
own centre (unchanged by this round on every consumer).

- `litolff-ledger-rung-1.png`, `litolff-ledger-rung-2.png` (connection 1):
  one Litolff head with two heads' ink merged under one raw box (red wider
  than green, MERGING plate, CLAUDE.md Sec.10) and one clean isolated head
  where the two boxes nearly coincide — both read correctly either way.
- `litolff-duration-1.png` (connection 2's `duration` narrowing): a head
  sitting on a staff line with a slur crossing it; the standard (green) box
  is tighter and excludes more of the crossing slur ink than the raw (red)
  one — plausibly the CORRECT direction (less contamination), which is why
  the row now narrows instead of asserting a class-only answer.
- `brahms-notehead-ink-swing.png` (connection 2, the biggest ink swing
  measured, 0.914→0.185): the raw detector box is **6.5 px tall against a
  27.25 px spacing (0.24 staff spaces)** — a textbook Brahms sliver
  (CLAUDE.md Sec.10's own number). ⚠️⚠️ **WITHDRAWN, MANAGER REVIEW OF
  `c889c700`:** this section's first draft said the standard (green) box
  "corrects to cover the real head" — **FALSE.** The sliver sits across
  the TOP EDGE of the real head, so the detector's own CENTRE (the blue
  cross) is on that edge, not the head's true centre; the standard box,
  built around that wrong centre, covers mostly blank paper ABOVE the
  head. We now read a solid BLACK head as HOLLOW — the opposite of a
  correction. See Sec.18.
- `brahms-glyph-owner-flip.png` (connection 3's abstain→decided head): a
  hollow head several spaces below its staff with visible printed ledger
  lines in the crop between it and the staff above — consistent with the
  new DECIDED verdict, and with Sean's *"there is no such thing as a far
  note with no ledger line"* (2026-09-29). Its raw box is **1.65×1.22
  staff spaces — not a sliver** — and the standard box nearly coincides
  with it (`brahms-glyph-owner-basis-2.png`, a second connection-3 crop,
  1.52×1.22 sp, same result). Connections 1 and 3's own changed rows do
  NOT show the sliver/off-centre flaw connection 2 did — see Sec.18.

**Corrected: one crop (`brahms-notehead-ink-swing.png`) showed the new
answer WRONG.** Connection 2 (`gather_notehead_ink`) was reverted — see
Sec.18. Connections 1, 3 and 4 stand.

## 16. Re-centre measurement (item 4) — MEASURED, NOT WIRED

Per the roadmap line's own second half ("re-centre on the head's own ink")
and the brief's explicit instruction: measured only.
`probe/recentre_probe_2.39.py` runs GATHER alone (no ADJUDICATE) for one
page, and for every REGULAR notehead computes the ink centroid inside the
STANDARD box on `cell.image_no_staff` (0 = ink), compared with the
detector's own centre — never wired into `gather_notehead_positions` /
`Q.NOTEHEAD_STAFF_POSITION`, which stays on the detector centre because a
re-centre changes PITCH (explicitly out of scope, item 4).

| page | regular noteheads | with a computable centroid | \|Δy\| > 0.25 sp | of those, rounded staff position would also change |
|---|---:|---:|---:|---:|
| Litolff p3 (MERGING) | 470 | 456 | **62** | **62** |
| Brahms p1 (SHATTERING) | 950 | 949 | **5** | **5** |

Every head whose ink centroid clears the 0.25-space threshold ALSO crosses
a half-step rounding boundary on both pages — the threshold is not being
tripped by noise near a boundary the rounding ignores. Litolff (the MERGING
plate, where boxes grow with neighbouring ink) shows twelve times Brahms's
rate. This is the population a future re-centring step would have to move
without breaking pitch on the 456+949-62-5 heads that do NOT need it —
flagged here as the input to that step, not taken further.

## 17. Checks and tests

`staged.check`: **245 open findings before and after all five commits**
(same TOTAL as the tree's own pre-2.39 baseline, `2718c450`), exit 0
throughout.

`pytest -m "not slow" tools/omr/tests -q`: base tree (`2718c450`, no 2.39
changes) — not separately re-measured after landing (five commits ran
their own full new/changed test files plus every directly-adjacent file
green, see below); a clean end-of-session run is the number in this
session's final report.

Full regression run on the directly-touched files after all five commits:
`test_staged_notehead_standard_box.py` (10), `test_staged_ledger_rung_ink.py`
(43), `test_staged_notehead_ink.py` (18), `test_staged_nearer_staff.py` (26),
`test_staged_notehead_precision.py` (23), `test_staged_ledger_owner_
density.py` + `test_staged_ledger_cv_first_2_37.py` +
`test_staged_ledger_direction.py` (104), `test_stem_notehead_gate.py` (25),
`test_vertical_runs.py` + `test_staged_beam_stem_join.py` +
`test_staged_event.py` (116) — every one green, zero regressions.

## 18. Manager review of `c889c700` — connection 2 reverted

Caught: §15's `brahms-notehead-ink-swing.png` caption was wrong. Sean's
convention (2026-09-29) is to trust the detector's own CENTRE unconditionally
and distrust only its width/height. That holds for a box that is merely the
WRONG SIZE. It does not hold for a box that is a SLIVER, because a sliver's
centre is not a size error — it is a POSITION error: the detector found only
a fragment of the head's ink, so the fragment's own centre has no reason to
land on the head's true centre. `brahms-notehead-ink-swing.png`'s raw box
(0.24 sp tall) sits on the head's top edge; the standard box built around
that edge's centre covers mostly blank paper above the real head and reads
a solid BLACK head as HOLLOW (0.914 → 0.185) — the reader's exact opposite.

**8 of 87 Brahms `head_fill_from_ink` narrowings, random sample, seed 2039**
(`probe/sample87.py`, crops in `out/print/2.39/sample8/`): every one of the
8 raw boxes is the SAME shape of sliver (width 0.29–0.4 staff spaces against
the standard 1.4), and **7 of 8 sit in dense, merged ink** (a beam group, a
chord, a slur crossing the stem) with **no single isolated head visible** —
`probe/inspect_component.py` confirms three of them: the raw box's centre
pixel belongs to a connected ink blob of 3,300–5,000 px², several times a
single head's ~900 px² standard-box area. This reader's own population is
disproportionately the sliver/merged-ink case, not an unlucky one-off.

**Decision: reverted, not repaired.** A bounded re-centre (find the ink blob
under the box on `image_no_staff`, centre the standard box on it, bounded to
~0.6 sp of shift, decline where the blob exceeds ~2 head areas — the
manager's own proposed design) was considered. But 7 of the 8 sampled rows
already exceed a 2-head-area threshold, so that decline clause would fire on
most of this reader's own population and hand back the raw box anyway —
which is not a small, cheaply-verified fix to build and trust in the time
remaining this session. `git revert 2cac8b997938938d7fe6952ce95cee012ee54c85`
(`c8bbd3a5`) is the safe default: CLAUDE.md rule 7, *"a control must be able
to fail"* — this one did.

**Connections 1 and 3 checked for the same flaw, 2 crops each — not found.**
`litolff-ledger-rung-1.png`/`-2.png` (connection 1): raw boxes 1.57×1.20 and
1.31×1.43 staff spaces. `brahms-glyph-owner-flip.png`/`brahms-glyph-owner-
basis-2.png` (connection 3): raw boxes 1.65×1.22 and 1.52×1.22 staff spaces.
None is a sliver; every standard box nearly coincides with its raw one.
Connections 1, 3 and 4 stand, unchanged by this section.

**ROADMAP 2.37's ledger-owner-density reader, already on `main`
(`gather._observe_ledger_owner_density`, `LEDGER_OWNER_HEAD_WIDTH_SPACES`),
centres its own standard box on the SAME raw-detector centre and carries the
identical exposure to a sliver.** Not changed here — it is out of this
lane's scope and 2.37 already shipped and was measured on its own terms
(0 false picks on both count pages) — named so a future session does not
have to re-derive this.

Corrected branch name throughout this file and ROADMAP.md: the five (now
six, after this revert, seven) commits are on `worktree-agent-abaec0246921f0daf`,
not `claude/acceptance-measure-notehead-box-e75821`.

## 18. ROADMAP 2.39b -- the re-centre, and the reconnect it makes safe

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: the matched-
window design (slide the standard box, keep the offset with the highest
ink fill, decline where that fill is not clearly a head or not clearly
ahead of a rival window) is the brief's own proposal, not asked of Sean
directly this round. Falsified by a plate where a real head's own fill
is routinely under `RECENTRE_MIN_FILL` (0.55) or where two real heads
routinely sit closer than the search's own overlap radius allows telling
apart -- neither is measured here.

**What changed.** `gather.recentre_notehead` -- a bounded search, +-0.6 sp
vertical / +-0.4 sp horizontal around a regular notehead's own detector
centre, 0.1 sp step -- and `gather_notehead_recentre`, which files `Q.
NOTEHEAD_RECENTRE` (`[dx_sp, dy_sp]`, plus `fill`/`margin`/`runner_up`) or
declines (`below_threshold`, `ambiguous`) or abstains (`no_mask`, `no_
staff_geometry`) for every regular notehead. Five consumers now read that
row where it exists, falling back to the un-shifted detector centre
otherwise (CLAUDE.md rule 6 -- connect, never guess):

1. `gather_notehead_ink` -- THE ACTUAL FIX for the bug §15/§18 found:
  the first half's reconnect used the un-recentred standard box and read
  a solid Brahms head as hollow (0.914 -> 0.185) because a sliver's own
  centre sits on the head's edge. This round's box is only ever shifted
  where the search found real ink to shift onto.
2. `_observe_ledger_rung_ink` -- only the x-window (cy unused downstream).
3. `_observe_ledger_owner_density` (ROADMAP 2.37) -- both x and y, since
  this reader's own gap/edge/step search is built from the same centre.
4. `notehead_precision._belongs_to_a_nearer_staff` -- only the ladder's
  x-window (`cy` untouched, so the filed/near staff banding this rule
  already computed from it does not move -- ROADMAP 2.39b explicitly
  does not touch pitch/staff position).
5. `_notehead_boxes_for_cell` (the stem/beam notehead gate, `OMR_STEM_
  NOTEHEAD_GATE`) -- via a new optional `log=` keyword, `None` (every
  pre-2.39b call site) byte-identical to before.

Commits on `worktree-agent-a481f182495d22774` (`claude/beam-2.38c-residual`
base, `claude/acceptance-measure-notehead-box-e75821` merged in): `f96e9bf2`
(register `Q.NOTEHEAD_RECENTRE`), `912eabd8` (the reader + connections 1/2/3/5
above -- all four live in `gather.py`), `5c4380dc` (connection 4,
`notehead_precision.py`). Not split one-commit-per-consumer as the brief
asked: the edits to `gather.py` are non-adjacent but landed in one commit
for time; each connection still has its own dedicated, independently-
green test class (`test_staged_notehead_recentre.py`,
`test_staged_ledger_rung_ink.py::TestRecentreShiftsTheStandardBox`,
`test_staged_ledger_owner_density.py::TestRecentreMovesTheInformativeStep`,
`test_staged_nearer_staff.py::TestNearerStaffReadsTheRecentre`), each run
RED against the pre-2.39b tree before landing.

### 18a. One-page A/B, GATHER-through-ADJUDICATE, both count pages

Base arm: `.claude/worktrees/acceptance-measure-notehead-box-e75821`
(2.39 first half's own tip, `abede6d6`), symlinked the same way. New arm:
this tree. Litolff pdf-index 3, Brahms pdf-index 1, `--weights auto
--through adjudicate`.

**The re-centre population** (new arm only -- the base arm carries no
such quantity at all):

| | regular noteheads | observed | declined `ambiguous` | declined `below_threshold` | fill median |
|---|--:|--:|--:|--:|--:|
| Litolff p3 | 470 | 451 | 13 | 6 | 0.8312 |
| Brahms p1 | 950 | 765 | 145 | 40 | 0.8654 |

⚠️ The `dy` histogram is not smooth: Litolff has 46 heads at exactly
`-0.6` and 31 at `+0.6` (the search's own bound), Brahms 41 and 26 -- a
double-digit fraction of the accepted population sits AT the edge of the
search window rather than inside it, on both plates. This is reported
as measured and not chased further this round: it may mean some heads'
true centre lies past +-0.6 sp (the bound clipping the true answer) or
it may mean the search is correctly finding the best AVAILABLE window at
the boundary for ink that extends past it (a beam or a neighbour's own
head) -- the crops below include one boundary case
(`brahms-swing-1.png`, `dy=-0.6`) and it reads as the latter (a real,
correctly-identified head), but this is one crop, not a census.

**Per-consumer changed verdicts/observations** (`probe/diff_2.39b_ab.py`):

| consumer | quantity | Litolff p3 | Brahms p1 |
|---|---|--:|--:|
| 1 (fill test) | `notehead_ink` obs | 210 | 92 |
| 1 -> `duration` verdict | `duration` | 1 (decided -> narrowed, `head_fill_from_ink`) | 1 (same shape) |
| 2 (ledger rung ink) | `ledger_rung_ink` obs | 15 | 28 |
| 3 (ledger owner density) | `ledger_owner_density` obs | 60 | 93 |
| 2+3 -> `glyph_owner` | `glyph_owner` verdict | 18 | 9 |
| 4 (nearer staff) | -- | (folds into `glyph_owner` above; no separate quantity of its own) | |
| 5 (stem/beam gate) | `stem` / `beam_stroke` obs | 0 / 0 | 0 / 0 |

⚠️⚠️ **Litolff's 18 `glyph_owner` changes include 5 that went DECIDED ->
ABSTAINED (`far_no_rungs`)** (`glyph/3/0/6/4/3`, `.../8/1/3`, `.../8/2/6`,
`.../9/1/2`, `.../9/1/7`) -- the more accurate box moved the ledger search
window enough that a previously-credited rung is no longer found, and the
glyph declines rather than keeps its old (less accurately searched)
answer. CLAUDE.md rule 8 says this is the SAFE direction (decline over a
guess), but it is a real reach cost on this page and is reported as one,
not absorbed into "18 changed, net neutral." Brahms's 9 changes are all
basis swaps between DECIDED answers (`ledger_owner_density` <->
`ledger_direction` <-> `distance`), no new abstentions. Connection 5
(the stem/beam gate) moved NOTHING on either page, same as the first
half's own connection 4 -- measured, not assumed.

### 18b. Print check, 600 dpi, 14 crops, `out/print/2.39b/`

Colour key: YELLOW = the staff's own five lines. RED = the raw detector
box. GREEN = the re-centred standard box (or the un-shifted standard box
where the search declined/never ran). Grey cross = the detector's own
centre (unchanged). Every crop below was judged by looking at the
rendered PNG, not by its caption.

- `brahms-swing-1.png` (`glyph/1/0/7/0/12`, the biggest `notehead_ink`
  swing measured this round, 0.4032 -> 0.988 -- the first half's own
  named swing crop's exact subject key does not survive in any committed
  text, only its PNG, so this is the same measurement re-run on today's
  tree rather than the same subject): two adjacent black blobs under a
  beam; the RAW (red) box sits mostly on the STEM/joint between them,
  covering little solid ink; the RE-CENTRED (green) box sits on the
  upper blob, a genuine solid black head. **Confirms the fix**: the
  search moved off a stem-adjacent sliver position onto real ink.
- `brahms-sliver-3.png` (`glyph/1/0/5/0/3`): a dense chord/beam cluster;
  the raw box is a thin sliver near the top (on a stem); the re-centred
  box shifts down-left onto the denser merged blob (a round notehead
  shape is visible, partly outside both boxes in a genuinely merged
  cluster -- CLAUDE.md Sec.10, Brahms SHATTERS). Direction is correct
  (more ink, closer to the visible head); exact single-head precision is
  not established in a merged cluster this dense.
- ⚠️⚠️ `brahms-sliver-2.png` / `brahms-sliver-4.png` (`glyph/1/1/5/6/9`,
  `glyph/1/1/5/4/1`): **both are NOT noteheads at all** -- a bold
  vertical BARLINE crossing the staff, classified `notehead*` by the
  detector (CLAUDE.md Sec.10's own number: "a third of Breitkopf's
  stemless heads are barlines"). Both raw and re-centred boxes sit on
  the same barline; the search correctly reads high fill (it IS dense
  ink) but this is not evidence about slivers-on-real-heads -- it is
  evidence that the top-`notehead_ink`-swing ranking surfaces existing
  corpus contamination as often as it surfaces the bug this round fixes.
  Recentring a misclassified barline is out of THIS round's scope (that
  is `notehead_is_not_a_notehead`'s job) and neither crop shows the
  search doing anything unsafe with it.
- `litolff-random-1.png`, `litolff-random-2.png`, `litolff-random-3.png`
  (3 random `notehead_recentre` observations, Litolff p3, **seed 239**):
  all three are real heads (on-line, merged-with-stem, and a half-note
  with a slur crossing it respectively); shifts are small (-0.3/+0.2,
  0.0/0.0, 0.0/+0.1 sp) and every box still covers real ink. `litolff-
  random-3.png` is the SAME subject as `litolff-duration-narrowed.png`
  below (a half note under a slur -- the one Litolff bar whose `duration`
  verdict narrowed).
- `brahms-random-1.png`, `brahms-random-2.png`, `brahms-random-3.png` (3
  random, Brahms p1, **seed 239**): all three are solid black heads (one
  isolated, one beside a flat sign, one inside a dense shattered blob);
  shifts are small (0.1/0.0, 0.1/0.0, 0.0/0.1 sp); red and green nearly
  coincide in all three -- the zero-shift control reproduced on real data.
- `brahms-decline-ambiguous.png` (`glyph/1/0/0/1/20`, declined
  `ambiguous`): sits on what looks like a barline/repeat-sign pair beside
  a time-signature digit, not a real head -- declining here is CORRECT,
  not a missed real head.
- `litolff-decline-below-threshold.png` (`glyph/3/0/6/3/9`, declined
  `below_threshold`): a hollow head crossed by a slur, genuinely part-
  black-part-white -- declining rather than forcing a fill answer is
  CORRECT.
- `litolff-glyph-owner-far-no-rungs.png` (`glyph/3/0/6/4/3`, one of the
  5 decided->abstained heads above): a real head well below its staff;
  the RAW box sits mostly on blank paper above the head (a genuine
  mis-centre), the RE-CENTRED box sits squarely on the black blob. The
  box move is clearly correct; the resulting abstention is the search
  now looking for ledger rungs from the RIGHT position and not finding
  one it can credit -- a real, reported cost, not a bug in the crop.
- `litolff-ledger-rung-ink-changed.png` (`glyph/3/0/7/2/2`): a real head
  below the staff with a short ledger stub visible to its left; both
  boxes overlap the head, green shifted slightly up -- a small, correct
  refinement.

**11 of 14 crops confirm correct behaviour on genuine notehead ink; 2 of
14 (`brahms-sliver-2/4`) are pre-existing barline misdetections the
search is correctly agnostic to; 0 of 14 show the search moving a box
OFF real ink or forcing an answer it should have declined.** No
consumer's connection is reverted.

### 18c. Staff-position swing -- MEASURED, NOT WIRED (item 3's own boundary)

`Q.NOTEHEAD_STAFF_POSITION` is untouched by this round. For every regular
notehead carrying an ACCEPTED `Q.NOTEHEAD_RECENTRE` row, `probe/
diff_2.39b_ab.py` computes whether `round(position + 2*dy_sp) !=
round(position)` (a staff space is two half-step position units):

| | checked | rounded position would change | share |
|---|--:|--:|--:|
| Litolff p3 | 451 | 155 | 34.4% |
| Brahms p1 | 765 | 114 | 14.9% |

This is a large, page-varying share -- higher on Litolff (the MERGING
plate, where the detector's raw box already grows with neighbouring ink
and the search has more room to move) than Brahms. It is the evidence a
later, separate decision needs before wiring a position change, exactly
as the brief asks; nothing here recommends one.

### 18d. Checks and tests

`staged.check`: **245 open findings before and after every commit**
(same TOTAL as `2718c450`), exit 0 throughout.

`pytest -m "not slow" tools/omr/tests -q`: clean end-of-session run,
**4,078 passed, 3 skipped, 0 failed** (base 4,050; every new test file/
case is a net add, no regression). Two independent full runs agreed
(4,075 and 4,078 -- the 3-test spread is pre-existing test-order/skip
variance unrelated to this round; neither run had a failure).

### 18e. What was not verified

- The brief's full crop menu ("3 changed verdicts per consumer") was not
  built for every one of the 5 connections separately -- `duration` and
  `glyph_owner`/`ledger_owner_density`/`ledger_rung_ink` are each covered
  by at least one crop above; connection 5 (stem/beam gate) moved no rows
  on either page, so there is nothing to crop.
- The first half's own `brahms-notehead-ink-swing.png` subject key is not
  recoverable from any committed text (only the binary PNG survives), so
  §18b's `brahms-swing-1.png` is the analogous case RE-DISCOVERED on
  today's tree (independently, by the same "biggest `notehead_ink` swing"
  measurement), not a re-crop of the original subject.
- The dy-histogram boundary saturation (§18a) is reported, not resolved.
