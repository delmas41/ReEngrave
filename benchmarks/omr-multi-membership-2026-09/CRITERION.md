# MULTI-MEMBERSHIP INK — the criterion, committed ALONE and FIRST

2026-09-17. **Nothing has been measured at the time this file is committed.**
No probe exists, no page has been rendered, no component has been counted.
The only things read beforehand were: that the target PDF is on disk, that
`omr-weights/` holds the production checkpoint, and the *already-committed*
`benchmarks/omr-ink-gather-2026-09/FINDINGS.md` — public record from a
previous job, which supplies the target cell and the baseline below.

This file exists because CLAUDE.md says so twice: the cleanup count's
categories were *"committed ALONE and FIRST, before a page was gathered ... or
the count fits itself to what was found"*, and **commit order is the only form
of that claim a later reader can check.**

---

## 1. THE IDEA UNDER TEST

Sean, 2026-09-17:

> *"Would it make sense to take every dot from an image and turn it into a
> format where every spot that is black becomes a digital point of
> reference... each dot could get labeled as belonging to a category... Each
> dot being able to belong to multiple things feels like it could be really
> helpful."*

The testable core is **MULTI-MEMBERSHIP**: one pixel belonging to more than one
thing at once. The pipeline has a real dilemma in its present representation:

* **lines erased** (`cell.image_no_staff`) — a glyph loses ink wherever a staff
  line crossed it, so a stacked meter can shatter into horizontal slices;
* **lines intact** (`cell.image`) — every mark a line passes through is one
  component with every other mark on that line. Measured on a clean engraved
  page at 600 dpi: **91 components, the largest 683,000 px.**

Today each reader picks one image and loses the other half. *"This pixel is
staff line AND notehead"* is the claim that dissolves that.

⚠️ **THIS IS NOT A PROPOSAL TO ERASE BEFORE THE DETECTOR.** That was measured
at −7 to −13 reading points and is refused; CLAUDE.md records it. This is about
the GEOMETRY path only.

---

## 2. THE METHOD, NAMED BEFORE IT IS RUN — the LINE BRIDGE

Per measure cell, three pixel sets:

```
intact   = ink(cell.image)
erased   = ink(cell.image_no_staff)
removed  = intact AND NOT erased      <- the pixels erasure took
```

`removed` is the multi-membership set: a pixel there is **staff line AND
(possibly) glyph.** The experiment is whether treating it as both recovers ink
that either single image alone loses.

**The join.** Two `erased` components are one MARK when a path between them
exists inside `intact` whose interior lies **entirely in `removed`** and whose
length is at most the bridge bound.

**The bound is IMPORTED, not invented:** `MeasureCell.staff_line_thickness_canonical`
— the pipeline's own measured line thickness, already on the cell. A glyph
stroke crossing a line loses about that much. If the bound has to be widened
past a small multiple of it to reach the result, that is a finding against the
method and will be reported as one, not tuned away.

**Why the bound is load-bearing.** An unbounded join through `intact` degenerates
to *"everything the staff line touches is one component"* — the 683,000-px
failure the erasure exists to prevent. The bridge is what makes multi-membership
a JOIN rather than a re-merge.

---

## 3. THE TARGET — and it has hand-confirmed ground truth, which is rare

**Beethoven 5 / Litolff `imslp984073`, PDF page index 62.** The printed `3/4`
is at the head of **CELL 6** on all 17 staves, immediately after a double
barline under *Tempo I.* Confirmed against 400-dpi crops by Sean himself;
committed at `benchmarks/omr-ink-gather-2026-09/out/print/`. Cells **7, 8 and 9
are empty rest bars**.

**Render at 600 dpi — the plate's native resolution — and not above.** The scan
is 1-bit at 600 dpi native (2897×3813, colorspace 1, 0 vector drawings);
rendering higher is pure upsampling, and components-with-a-hole measured 31 at
300 dpi and the same 31 at 1200.

---

## 4. THE THREE SCORES — all three reported, whatever they say

### SCORE 1 — THE READING (uncertain)

At cell 6, on how many of 17 staves does the method recover a `3` over a `4`?

**Baseline is ZERO: the detector fires no `timeSig*` at cell 6 on any staff**
(committed, `omr-ink-gather-2026-09/FINDINGS.md` §6.2). So any reading is a
gain — and **every one must be checked against the crop, not assumed.**

Two tiers, reported apart:

* **1a STRUCTURAL** — the joined mark is one component of meter shape, and it
  carries a two-digit vertical stack. Shape window **IMPORTED** from
  `omr-ink-gather-2026-09/probe/target_cell.py` (`W 1.4–2.4`, `H 3.2–5.0`,
  `X 0.8–2.6` staff spaces), which was read off the print rather than fitted.
* **1b IDENTIFICATION** — the stack's two halves match Bravura `timeSig3` and
  `timeSig4` better than any other digit, using the templates already in
  `tools/omr/symbol_library/`.

⚠️ A structural pass with an identification failure is a **partial** result and
will be reported as one. It is not a reading.

### SCORE 2 — THE REFUSAL (equally important)

At **cell 8** the pipeline today reads a false `3/4` from ONE barline broken
into two fragments — 0.35 and 0.40 staff spaces wide, 1.17–2.17 tall, both at
`x_canonical = 0`. **The method must REFUSE it.** Cells **7 and 9** are the
negative control and must also yield nothing.

**A method that reads a meter at cell 6 and also at cell 8 has learned
nothing**, and that outcome is a refutation, not a mixed result.

### SCORE 3 — THE MECHANICAL HALF (expected to work; the half that generalises)

Independent of digits, over **every cell of the page**: does the correspondence
between intact and erased components recover ink that EITHER image alone loses?

Scored as a count of components that are **both**

* **broken** under erased-only — the bridge joins ≥2 erased fragments; and
* **merged** under intact-only — the intact component containing them also
  holds ink the bridge does NOT join (i.e. ≥2 marks share one intact
  component),

so neither single image gives that mark's ink complete and separated.

**If the digits fail but this succeeds, that is a positive result and must be
reported as one** — it is the thing that would let every thin glyph keep its
strokes, not just these two.

---

## 5. WHAT WOULD KILL IT — pre-registered, and I stop and say so

| | kill condition | what it means |
|---|---|---|
| **K1** | At cell 6 the `3` and the `4` are already **one erased component** on most staves | Erasure did not break the meter; the line bridge has nothing to do there and the reading failure is not a representation problem. Score 1 dies; score 3 still runs. |
| **K2** | The plate's own threshold has already merged the two digits into a blob with no recoverable internal structure | **The ceiling is the plate, not the pipeline.** Clean negative — say it in the first paragraph and stop. |
| **K3** | No bridge bound both joins the meter's fragments AND leaves cell 8 refusing | The method cannot read and refuse at once. Refutation. |
| **K4** | Fewer than **1%** of the page's components are repaired under score 3 (broken-under-erased AND merged-under-intact) | Multi-membership buys nothing measurable. Negative. |

⚠️ **A clean negative delivered fast is a success here.** Sean: *"I don't want
to waste time."* This repo's record is that five of six jobs came back refuting
their brief's mechanism, and each refutation was worth more than the repair.

---

## 6. SCOPE AND DISCIPLINE — pre-registered too

* **An experiment, not a feature.** A probe under `benchmarks/`. **No second
  gather mode.** `tools/` is touched only if the question genuinely cannot be
  answered otherwise, and then behind a flag, **default OFF, allow-list**
  (CLAUDE.md, *"A flag's OFF test must follow its DEFAULT"*).
* **REACH FIRST.** Every probe prints how many components, cells and staves it
  reaches before any accuracy number, and **exits non-zero declaring itself
  DEAD at zero reach.**
* **A POSITIVE CONTROL beside every zero** — a zero from a method that did not
  run and a zero from a method that ran and found nothing are otherwise the
  same number.
* Reuse `gather_ink`, `cell.image`, `cell.image_no_staff`, the shape window and
  the thickness constant. Reinvent none of them.
* Every figure reproducible by a named command. Anything I could not check is
  marked **unchecked**, never asserted.
* **Mutation battery if any code ships under `tools/`**, with a byte snapshot
  before the first arm, an in-flight sentinel, and the restore VERIFIED.

---

## 7. WHAT THIS CANNOT ESTABLISH, SAID IN ADVANCE

n = 1 document, 1 publisher, 1 page, on the *low-res bitonal* end of this
corpus. Nothing here will speak for the engraved family, for Breitkopf, or for
any page whose staff lines are thicker or thinner than this plate's. No OMR-NED
figure will be claimed: the metric is symmetric, it compares two files at the
far end, and it cannot see a representation change that reaches no exporter.
