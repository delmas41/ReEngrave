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
