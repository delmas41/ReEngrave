# Review — FIX AGENT K, `claude/wire-cv-hairpin-reader`

**Reviewer: Agent II**, who classified this module UNREACHABLE-with-a-live-gap in
`TECHNOLOGY_LEDGER.md` §5. Reviewed at `c98aa972`. Read-only; its test file run
(**33 passed**, 0.72 s, no pipeline), suite not run, no `scan_eval`.

## VERDICT: **APPROVE WITH FIXES** — one docstring overclaim (§1). The merge was right.

The ledger call holds: this was a wiring job, not research. The module was
built, measured, and imported by nothing; it is now imported by one gated call
site and it finds **56 hairpins where the detector finds zero** on the family
that needs them.

⚠️ **And this is the first build tonight to commit its own evidence.**
`results-reproduce-gate.json` is in the tree, and I re-derived every headline
number from it rather than from the report: truth **99**, yolo **0**, fresh
render **62**, pipeline binary **57**. Three previous branches left their
figures in prose. This one should be the pattern.

---

## 1. ⚠️ The staff-lines-INTACT deviation — the DECISION is right, the stated REASON overclaims

**The decision is correct and I would not change it.** But the justification as
written is stronger than the evidence, and I measured it rather than reasoning
about it.

The gate is `_is_isolated`: a candidate's full-page connected component must not
exceed `MAX_COMPONENT_GROWTH = 2.0` times its own box. The module's claim is that
erasing the staff lines *"dissolves the page's single connected mass and the
constant no longer separates anything."*

**I built the minimal case and ran it** (synthetic page, a beam with two stems
crossing a staff, an isolated hairpin in the gap below, `_is_isolated`'s own
arithmetic):

| | beam growth | verdict | hairpin growth | verdict |
|---|--:|---|--:|---|
| lines **INTACT** | **130.7** | attached → rejected | 0.73 | isolated → kept |
| lines **ERASED** | **13.75** | **attached → still rejected** | 0.73 | isolated → kept |

**Erasure cut the margin by 9.5× and did not close it.** The beam is still
attached to its stems, and the stems alone put the component far above 2.0. So
the *directional* claim is right — erasure substantially reduces the separation —
and the *categorical* claim, that the constant "no longer separates anything",
is **not demonstrated and is contradicted by this construction.**

⚠️ **My measurement is n=1 and hand-built**, with long stems relative to a short
beam, which favours the erased case. It cannot show erasure is safe either. What
it shows is that the categorical claim is not self-evident, and **neither the
builder nor I have measured the erased arm on a real page** — `reproduce_gate.py`
runs two ink RECIPES (fresh render, `PageImage.binary`), both lines-intact.

**Two better justifications are available and both are already true:**

1. **Lines-intact is the substrate the constant was CALIBRATED on.** The 1.0×
   vs 3248× population is measured on raw ink. Running the gate there is using
   it on its own calibration substrate; running it on erased ink would be using
   it off-calibration. That alone settles it and needs no mechanism story.
2. **Erased ink is not merely different, it is UNPREDICTABLE.** This repo's own
   record: erasure is destructive, leaves glyphs in pieces, and manufactures
   structure — YOLO's `beam` detections went 46 → 105 on staff-line *residue*.
   A gate keyed on connectivity is exactly the kind that residue would perturb
   in an unmodelled direction.

**FIX:** replace *"erasing them dissolves the page's single connected mass and
the constant no longer separates anything"* with the calibration argument, or
mark the dissolution claim UNMEASURED. As written a future agent will read it as
measured — and this audit has already had to correct one docstring that was
false in the failure direction.

⚠️ **On your rule:** it is a genuine exception, and it is narrower than "CV rungs
read erased ink". The rungs that take the erased image (`line_detection`,
`staff_header`, `direction_text._blank_detections`) all want the lines GONE
because the lines are the noise. This gate wants the lines PRESENT because the
lines are the *signal* — they are what makes an attached component big. **The
rule is about what each consumer is measuring, not about CV as a category**, and
CLAUDE.md's own framing already allows it: *"erase for the CV consumer, BOUND
THE SEARCH for everyone else."*

## 2. Placement — mechanically correct, and its reach on this corpus is ZERO

The wiring sits before both dedupers and a source-level test pins the ordering
(`min(cv lineno) < min(dedupe lineno)`). The mechanism checks out end to end:
the CV detection carries `class` ∈ `{dynamicCrescendoHairpin,
dynamicDiminuendoHairpin}` (= `_WEDGE_HAIRPIN_CLASSES`), `category: "dynamic"`,
and `bbox_page` as `[x, y, w, h]` — the convention `_bbox_center_y` and
`_bbox_iou_xywh` read. So a CV/YOLO contest across two staves would reach
`_dedupe_cross_staff_detections`' rank-1 notes-in-bar tier, which is the
hairpin-specific protection.

⚠️ **But there is no contest to arbitrate on the measured corpus.** The committed
artefact reports `yolo: 0` on **all eleven rows**. The tier's reach here is
exactly zero; the placement is insurance that the data cannot currently exercise.
It would matter on the engraved family, where YOLO finds 9 — and that family is
not what the flag is measured on.

**That is correct engineering and it should be stated as reach-zero rather than
as protection obtained.** Same-measure doubling is separately prevented by the
guard at `hairpin_detection.py:355-358`, which does fire.

## 3. The per-row finding — RIGHT, and I would go further than "report per row"

Re-derived from the artefact, per row rather than per edition:

| row | truth | found | |
|---|--:|--:|---|
| brahms-317803-p2 | 68 | 40 | 59% |
| brahms-317803-p1 | **0** | **2** | invents |
| dvorak-405834-p6 | 4 | 4 | **exact** |
| dvorak-405834-p5 | 7 | 4 | 57% |
| mahler-p3 | 17 | **2** | 12% |
| mahler-p2 | 3 | **5** | **over-emits** |
| bach ×1, beethoven ×4 | 0 | 0 | silent |

(Your table is in `<wedge>` TAGS, the artefact in hairpins — 68×2 = 136, 20×2 =
40, 11×2 = 22. They reconcile exactly; nobody should think they conflict.)

**The row is the right unit, and the reason is sharper than the spread being
large: the two Mahler rows differ in DIRECTION.** p3 under-emits by 15, p2
over-emits by 2. An edition aggregate reports "Peters finds 7 of 20" and
**conceals that one of its two pages invents marks**. Direction of error is not
an averageable quantity — the mean of an over- and an under-emission describes
neither page and predicts nothing about a third.

**Does it change how the hollow-notehead edition effect should be read?**
⚠️ It does not refute it and I am not claiming it does. What it supplies is a
**concrete counter-example, on the same corpus and overlapping rows, to the
assumption that a two-row edition aggregate is homogeneous.** So the honest
consequence is a cheap precondition rather than a re-opening:

> **An "edition effect" is only attributable to the edition once the rows within
> that edition are shown to agree in DIRECTION.** Otherwise it may be a row
> effect wearing the edition's name, and the edition is the label on whichever
> rows were sampled.

That check is free on any result already computed per row, and this repo's own
publisher-shaped-rule trap (Simrock 45/45 vs Litolff 2/50, same rule) is the
reason to want it.

## 4. The duplicate pair — YES, it is the eventless-measure path, and it is not this branch's

Confirmed: `export._mxl_empty_measure` (`:1529`) takes a **`wedges`** parameter
(`:1532`) alongside `directions`. A bar with no events takes that path and emits
its wedge tags directly, with nothing to anchor them to — which is exactly the
degenerate `diminuendo` + `stop` with no note between them on Mahler p3.

⚠️ **It is a pre-existing export behaviour that this rung is the first thing to
reach.** Before this branch no wedge could arrive in an eventless measure on a
scan: the CV rung never ran and YOLO finds zero. So this is not a hairpin-reader
defect — it is the export path becoming reachable, which is the same shape as
this repo's own history there (the eventless-measure marks bug was predicted to
need a scanned page and was invisible to the engraved benchmark for exactly this
reason).

Correct not to touch `export.py`. 1 of 56, 2 tags of 112. Worth a backlog line
now that it is reachable; not worth blocking.

## 5. The two self-caught vacuities — both genuinely closed

- **Polarity.** The first check was `endswith(".binary")` on unparsed source,
  which accepts `255 - page.binary`. The replacement asserts
  `isinstance(a, ast.Attribute) and a.attr == "binary"` — `255 - page.binary`
  parses as `ast.BinOp` and fails. **The named mutation is now forbidden.**
- **Blanking.** The fixture now asserts the **negative control first** —
  `read_hairpins_for_page(...) == 0` unblanked, with the message *"if this
  passes, the fixture is not exercising the blanking and the test below is
  vacuous"* — then `== 1` with the detection present. Two-sided, and it names
  the vacuity it guards.

Both are the pattern the audit has been asking for. Catching them in its own
harness rather than in review is the thing five agents needed tonight.

## 6. Flag-off byte-identity — by construction

**One** call site (`transcribe.py:5237`), inside **one** `if
_cv_hairpins_enabled():` branch — verified by AST, not by grep. Flag-off cannot
execute the rung, so identity is structural and the measured control is
confirmation rather than the claim.

## 7. The near-miss on the gate — and a better argument than the one offered

The builder explains 62/57 against a documented 59 by *"the fixtures were
re-transcribed with different weights since"*. You flagged that as a convenient
explanation, and you are right to — but **the numbers make a stronger argument
that does not need the weights story to be true**:

> **59 lies BETWEEN the two arms measured today** — 57 (`PageImage.binary`) and
> 62 (fresh 600 dpi render). Two defensible ink recipes on the same eleven rows
> span a range that contains the documented figure.

So this is not a near-miss requiring an excuse; it is inside the spread that the
choice of ink recipe alone produces. The weights mechanism is real and
unfalsified — `blank_point_detections` erases boxes named by the stored
detections, so a different checkpoint genuinely changes the search — but it is
not load-bearing, and the write-up would be stronger leading with the interval.
⚠️ Neither of us has run the falsifying arm (the gate against a transcription
made with the original weights).

---

## Your direct question: is a pooled `scan_eval` arm worth it?

**Run the arm. Report per row. Do NOT compute a pooled figure at all** — not
"compute it and caveat it".

I agree with your inclination and would go one step further, for two reasons
specific to this data:

1. **Pooling averages an over-emission against an under-emission.** Mahler p2
   invents 2, p3 misses 15. A pooled OMR-NED does not merely lose that — it
   reports an apparent moderate under-emission that is true of neither page. That
   is worse than uninformative; it is a number that would be quoted.
2. ⚠️ **Six of eleven rows carry ZERO truth hairpins.** They contribute their
   full symbol counts to the pooled denominator while the feature can only hurt
   them — and on one of the six it does, inventing 2. The pool is dominated by
   rows where the change cannot help.

You cited my arc pricing and it is the right precedent, with the sign reversed:
there a pooled figure hid a trade because the metric rewards emitting FEWER
symbols; here it would hide a trade because the metric cannot distinguish 56
added-and-mostly-right from 56 added-and-scattered. **In both cases the
protection is the same — a COUNT control beside the metric.** For this arm that
is: hairpins found vs truth per row, and false positives on the six blank rows,
which the committed artefact already produces.

The precision signal is genuinely good and belongs in the report: **silent on 5
of the 6 hairpin-free rows across two publishers**, inventing on one.

---

## What I want on the record as good

- **Committing the gate artefact.** First tonight. Every number in this review
  was re-derived from `results-reproduce-gate.json` rather than from the report.
- **Reproducing the gate before adding the call site**, on the stated ground
  that a measurement for code nothing imports is exactly what this repo has been
  bitten by. That is the ledger's UNREACHABLE distinction being used correctly by
  the person acting on it.
- **The polarity assertion.** `_INK_FRACTION_CEILING` turns a silent null — the
  one failure this project treats as worse than a crash — into a loud one, and
  the reasoning is written at the site.
- **Refusing to fudge the near-miss.** Reporting 62 and 57 against a documented
  59, with the discrepancy named, is the right call even though the explanation
  offered is weaker than the one available.
