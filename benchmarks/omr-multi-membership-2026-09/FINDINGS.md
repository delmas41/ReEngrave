# MULTI-MEMBERSHIP INK — a clean negative, and the premise is already in the tree

2026-09-17. Pre-registered in [CRITERION.md](CRITERION.md), **committed alone
and first** (`210ff842`), before a page was rendered. Nothing under `tools/`
was touched: `git diff HEAD~2 HEAD -- tools/ backend/` is empty.

---

## 0. THE FIRST PARAGRAPH, AS THE BRIEF ASKED FOR IT

**The plate already merged them — and the pipeline already does
multi-membership.** Two independent negatives, either of which alone would
close the reading half:

1. ⚠️⚠️ **THE PREMISE IS FALSE FOR THIS PIPELINE.** The brief's dilemma —
   *"erase the staff lines and a glyph loses ink wherever a line crossed it"* —
   does not describe `remove_staff_lines`. That module's own first line is
   *"Phase 1.4 — Staff line removal **preserving symbol-crossing pixels**"*,
   and its rule (a vertical ink run no taller than the line's own printed
   thickness IS the line; a taller one is something CROSSING and is left
   entirely alone) **is multi-membership, per column, shipped since Phase 1.4.**
   `LINE_CROSSING_FACTOR = 2.0` is the constant that expresses it. Measured
   consequence: the line bridge makes **0 joins on 1,244 components across all
   221 cells of the page** — not because it does not work, but because there is
   nothing anywhere on the page for it to join.

2. ⚠️⚠️ **AND THE TARGET WOULD HAVE FAILED ANYWAY (K2).** The printed `3/4` is
   already **ONE erased component on 17 of 17 staves**, and the two digits are
   fused in *surviving* ink, not by a staff line. Cutting the blob at every
   staff line yields **4, 5 or 6 pieces — never 2 — on 17 of 17 staves**, and
   its narrowest interior row still carries **34%** of the blob's width. There
   is no waist. At **15.0–15.8 native px per staff space**, the whole stack is
   **28–31 × 68 native pixels** and the 1-bit threshold has filled both digits'
   counters.

**The idea is sound and it is not new here.** What this measures is that it is
already implemented, one stage earlier, in a better place than the one the
brief proposes — and that doing it after the fact is measurably worse.

---

## 1. REACH — first, because a zero here would end the job

```
python3 probe/arm.py <pdf> 62 --cell 6 --controls 7,8,9 --out out/arm-p62.json
```

```
REACH  staves=17  cells=221  prepare=4.3s
       erased components 1244        (13.5 s per arm, no detector needed)
```

Litolff Beethoven 5 / `imslp984073`, **PDF page index 62**, rendered at **600
dpi — the plate's native resolution**, as the criterion fixed. Every probe
prints reach before any accuracy number and **exits 2 declaring itself DEAD**
at zero reach.

⚠️ The 1,244 reproduces `omr-ink-gather-2026-09`'s own count on this page to
the unit, from a different code path, which is the cheapest available check
that I am looking at the same ink that job was.

---

## 2. SCORE 1 — THE READING: **0 of 17**, and the join is not what failed

| | |
|---|--:|
| staves carrying a meter-shaped component at cell 6 | **17 of 17** |
| ...of those, **built by the join** | **0** |
| joins the bridge made anywhere on the page | **0** |

⚠️⚠️ **THE 17 IS NOT MINE AND IS NOT A RESULT OF THIS EXPERIMENT.** It is the
shape window finding raw components that were already there — the prior job's
measurement (`omr-ink-gather-2026-09` §6.3), reproduced. **Multi-membership
contributed exactly nothing to it.** Because the bridge makes zero joins, its
output partition is identical to its input, so **any reader downstream sees
precisely what it sees today.** That is why tier **1b (identification) was not
run**: there is no altered input to identify anything from, and running a
template match on an unchanged blob would have measured the template reader,
not this method.

### 2.1 K1 fired: erasure never broke the meter

`python3 probe/diagnose.py <pdf> 62 --cell 6`

On all 17 staves the printed `3/4` is a **single** erased component,
**1.72–2.07 spaces wide × 3.75–4.54 tall** — a stacked two-digit meter spanning
the staff, whole. It crosses four staff lines and survives all four.

### 2.2 K2 fired: the digits are fused in surviving ink

`python3 probe/separability.py <pdf> 62 --cell 6`

| test | result |
|---|---|
| cut the blob at every staff line | **4–6 pieces on 17 of 17** — never the 2 that would mean "joined by a line" |
| narrowest interior row | median **64 ink px of a 187-px blob** (**34%**) |
| is that narrowest row at a staff line? | **0 of 17** |

So the join between the `3` and the `4` is not a staff line and is not at a
staff line. **It is ink the erasure correctly judged not to be a line.** Cutting
at the lines does not separate the digits — it shatters the glyph.

### 2.3 The ceiling, in native pixels

`python3 probe/zoom.py <pdf> 62 --cell 6 --staves 0,2,7,16`

```
staff  0  upscale=6.349  NATIVE_sp=15.8px  glyph = 28x68 NATIVE px (1.78x4.31 spaces)
staff  2  upscale=6.349  NATIVE_sp=15.8px  glyph = 29x68 NATIVE px
staff  7  upscale=6.452  NATIVE_sp=15.5px  glyph = 30x68 NATIVE px
staff 16  upscale=6.667  NATIVE_sp=15.0px  glyph = 31x68 NATIVE px
```

⚠️ **THE CANONICAL FRAME FLATTERS THE PICTURE AND I NEARLY QUOTED IT.**
`_upscale_to_canonical` rescales every cell to 100 px per staff space, so the
crops in `out/zoom/` are a **6.3–6.7× magnification** of what the plate carries.
A judgement about whether two digits touch has to be made on the pixels that
exist. **Each digit is about 29 × 34 native pixels**, and a staff line is **4**.
The crops (`out/zoom/s02-meter-overlay.png`, `s16-meter-erased.png`) show both
counters of the `3` filled solid and the `4`'s triangle filled — the 1-bit
threshold, not the erasure.

---

## 3. SCORE 2 — THE REFUSAL: satisfied, and for a reason that deserves no credit

| cell | bridge arm | dilate arm |
|---|--:|--:|
| 7 | 0 | 0 |
| **8** (the false `3/4`: one barline in two fragments) | **0** | **0** |
| 9 | 1 | 1 |

The cell-8 barline fragments — 0.35 and 0.40 spaces wide — are joined by
neither arm and are nowhere near the 1.4-space floor. **The refusal holds.**

⚠️ **IT IS NOT A RESULT.** A method that makes zero joins refuses everything by
construction. Passing the refusal test costs a do-nothing method nothing, and
reporting it as a win would be the *battery of refusal tests that passes by
refusing everything* this repo already records.

⚠️ **AND THE ONE HIT AT CELL 9 IS THE SHAPE WINDOW'S, NOT THE METHOD'S.** The
bridge made no join there either; it is a raw component that happens to be
meter-shaped. Cropped (`out/zoom/cell9-s12-falsepos.png`) it is **a quarter
note — a notehead with its stem**, 1.43 × 3.94 spaces, which is the bounding
box of a stacked meter. **A stemmed notehead and a two-digit meter have the
same box**, so the shape window alone cannot be a meter reader. Worth recording
against the 17-of-17 above: that window's precision on this page is 17 true to
1 false, and the false one is the commonest object in music.

⚠️ Cells 7/8/9 are described as "empty rest bars" from `staff 0`'s crop. Staff
12 plays there. No contradiction — but the description is one staff's.

---

## 4. SCORE 3 — THE MECHANICAL HALF: **0.00%**, and K4 fires

Over every cell of the page:

| | bridge (multi-membership) | dilate (control) |
|---|--:|--:|
| erased components | 1,244 | 1,244 |
| groups the join made | **0** (0.00%) | 68 (5.47%) |
| ...AND merged under intact | **0** (0.00%) | 56 (4.50%) |

**K4's threshold was 1%. The bridge scores 0.00%.** The half the criterion
called *"expected to work, and the half that generalises"* is the one that
found nothing — because the work is already done upstream.

⚠️ **THE DILATE COLUMN IS NOT A CONSOLATION.** Those 68 joins are naive
vertical proximity across **paper**, with no multi-membership in them at all;
`synthetic.py`'s third case is built to expose exactly that difference (two
marks stacked with a paper gap: bridge refuses, dilate accepts). Joining across
paper is how a note and the mark above it become one object. It is reported
because the control is the point, not because it is a result.

### 4.1 The intact side of the dilemma IS real — it is the half that has no repair here

At cell 6, with the lines in, a cell holds a **median of 2** connected
components and the dominant one covers a **median 314,669 canonical px**. So
the brief's second horn is accurate: the intact image really does merge
everything a line touches. What this experiment shows is that the erased image
**is already the repair**, and that nothing is lost in it that the intact image
would give back.

---

## 5. THE POSITIVE CONTROL — the bridge is alive, and it is WORSE than the shipped rule

A zero from a method that did not run and a zero from a method that ran and
found nothing are the same number. Two controls separate them.

**`probe/synthetic.py`** — ink whose every dimension is chosen here, right
answer known by construction. **PASS on all four cases:**

```
stroke through a line      erased=2  bridge=1  dilate=1
two strokes on one line    erased=4  bridge=2  dilate=2   <- never 1: no horizontal bridge
stacked, PAPER between     erased=2  bridge=2  dilate=1   <- the arms MUST differ
bare line, nothing else    erased=0  bridge=0  dilate=0
```

**`probe/positive_control.py`** — the same 221 cells re-erased NAIVELY (the
shipped code with one predicate changed: erase every column's band at the line,
of the line's own measured thickness), then bridged:

| | components |
|---|--:|
| **SHIPPED** erasure | **1,244** |
| NAIVE erasure | **5,143** (4.13×) |
| NAIVE + bridge, bound = 1.0× line thickness | 3,551 — rejoins 1,592 of 3,899 (**40.8%**) |
| NAIVE + bridge, bound = 1.5× | **1,982** — rejoins 3,161 (**81.1%**) |
| NAIVE + bridge, bound = 2.0× | 1,982 — **saturated**, every gap ≤ 1.4× |

Gap distribution, measured with **no bound at all**: min 21, median **25**, max
35 canonical px, against a measured line thickness of **25**. The gaps are the
line, exactly as the method predicts.

⚠️⚠️ **THE CONCLUSION IS A COMPARISON, NOT A ZERO.** The bridge recovers **81%**
of what naive erasure destroys and **saturates 59% short of the shipped
erasure** (1,982 against 1,244). **Multi-membership decided at erasure time
beats multi-membership reconstructed afterwards**, and the reason is
structural: erasure knows which pixels to KEEP, while the bridge can only
restore connectivity between fragments whose pixels are already gone. This is
the generalisable statement of the whole experiment, and it argues *for* the
existing design rather than merely against the proposed one.

---

## 6. ⚠️⚠️ THE CONTROL LIED ON ITS FIRST RUN, AND TWO FAULTS WERE MINE

`positive_control.py`'s first run printed

> `POSITIVE CONTROL: the bridge is alive. Its zero on the SHIPPED erasure is a
> property of that erasure, not of this code.`

directly under a table reading **`bridges the method made on naive   0`**, on an
image it had just shattered 1,244 → 4,513. **The sentence was written before the
number and survived it.** That is the *control that computes the wrong thing*
family, arriving inside the control built to prevent exactly that — and the
green-looking output is what would have stopped the search.

Two distinct faults behind it, both mine:

1. **The claim was unearned.** A control cannot certify itself; the certifying
   evidence now lives in `synthetic.py`, on ink whose answer is known by
   construction, and `positive_control.py` now says in terms that it is *not*
   evidence the bridge can fire.
2. **The naive arm was not naive — it was worse.** It erased the whole vertical
   RUN at each line (what the shipped code does, because it only ever erases
   runs it has already judged to BE the line), removing up to
   `2 × (cap + 2) = 75` px where a glyph crosses. So its gaps were **three times
   the line's thickness** and no thickness-bounded bridge could ever close them.
   `staff_line_removal.py`'s own words for the thing being modelled are *"just
   erasing the staff line row"* — a row, of the line's thickness. **Fixing that
   one band took the arm from 0 bridges to 91,613**, and the whole of §5 exists
   only because it was fixed rather than reported.

⚠️ **The tell was not review.** It was the arithmetic: a 3.63× shatter with 0
repairs is not a believable pair, and the unbounded gap distribution (median
**75** px against a 25-px line) named the cause in one run.

---

## 7. WHAT THIS DOES **NOT** ESTABLISH

* **n = 1 document, 1 publisher, 1 page**, on the *low-res bitonal* end of this
  corpus. Nothing here speaks for Breitkopf, whose ink fragments where this
  plate blots (`omr-ink-gather-2026-09` measures 30 components per cell against
  this page's 5.6), nor for the engraved family, which is untouched by
  construction.
* **The negative is about the VERTICAL bridge.** A horizontal or diagonal
  bridge was not tested, deliberately: a horizontal bridge runs ALONG a staff
  line and is precisely the 683,000-px re-merge the erasure exists to prevent —
  `synthetic.py`'s second case pins that the shipped formulation cannot do it.
  ⚠️ But the stronger statement does not depend on the formulation at all:
  **under ANY join rule there is nothing to join**, because the erased partition
  already holds each glyph whole.
* **No reading accuracy was measured**, because nothing changed the input to any
  reader. No OMR-NED figure is claimed; the metric compares two files at the far
  end and cannot see a representation change that reaches no exporter.
* **`LINE_CROSSING_FACTOR = 2.0` was not re-priced.** This measures that the
  rule fires and what it is worth against naive removal; it does not test
  whether 2.0 is the right value, and one page cannot.
* **The 5-of-221 and 13-of-221 "exact recovery" counts are weak** — they compare
  component COUNTS, not partitions, so a cell can match by coincidence. They are
  reported for shape, never leaned on.

---

## 8. WHAT I WOULD DO INSTEAD, IF ANYTHING

Not a recommendation to build — a note for whoever asks this question next.

**The reading failure at cell 6 is upstream of every representation.** Both
digits' counters are filled at 15.8 px per staff space; no partition of those
pixels recovers a `3`. The levers that could reach it are the RASTER (a 1-bit
600-dpi plate has no grey to recover — measured by the prior job: components
with a hole number 31 at 300 dpi and the same 31 at 1200) or a **template match
against the whole stack rather than its parts** — `symbol_library/` already
holds `timeSig0-9` and `time_signature_locator` already slides composites, and
that reader does not need the digits to be separable. ⚠️ **Unmeasured here**,
and it is not multi-membership.

**And the one genuinely open version of Sean's idea is the opposite direction.**
Everything above is about a pixel that is *line AND glyph*. `Q.INK` shipped
yesterday makes the ink the population and the classification an attribute —
that is already the multi-membership representation, one level up, and it has
**no consumer**. A pixel belonging to several *marks* (a notehead and the slur
that touches it, a stem and its beam) is untested and is where a merge on this
plate actually costs us: 5.7% of this page's components are blobs too big to be
one mark, and §4.1's median intact component is 314,669 px. That is a SPLIT
question, and nothing in this experiment addresses it.
