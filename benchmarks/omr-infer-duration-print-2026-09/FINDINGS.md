# Roadmap 2.3 — the INFER duration rules against the PRINT

2026-09-23. `collapse_duration_by_column` and `collapse_duration_to_barline`
are both default OFF, and `benchmarks/omr-infer-default-2026-09/FINDINGS.md`'s
own table gives the reason in four words: **"no note checked against a page"**.
This pass cuts a crop for every inference either rule would write, so that
sentence can stop being true.

**It does not decide the default.** It produces the evidence a decision needs
and names three things that must be settled first. The crops are uncropped by
any adjudication: `VERDICT_none_yet` is null on every row of the manifest.

Record: `library/_shared-records/beethoven5-p1-p4-ink-identity.record.json`
(Litolff, pdf pp.1–4), provenance `commit e38dbc2556…, dirty: False` — a real
baseline. Instrument: `benchmarks/omr-infer-stage-2026-09/reinfer.py`,
INFER-only replay over a fixed gather and a fixed adjudication.

**Control first**: 19,563 of 19,563 verdicts reproduced exactly, 0 differ,
+0 extra; 40,878 of 40,878 observations replayed.

---

## 1. Reach, on today's tree

`OMR_INFER=1`, both rules on:

| rule | inferences |
|---|--:|
| `collapse_duration_by_column` | 6 |
| `collapse_duration_to_barline` | 10 |
| **total** | **16** |

⚠️ The earlier findings recorded 7 + 10 = 17 on the OLDER
`beethoven5-p1-p4.record.json`. This is a different record by a different
reader, not a regression — and the difference is the point of §4 below.

## 2. ⚠️ THE RULE IS NOT AN ARGMAX, AND 2 OF 16 PROVE IT

`Rule.forbids_argmax` is asserted by the suite; here is what it buys. Thirteen
inferences pick the candidate the reader already ranked first. **Two do not**:

| subject | rule writes | its support | reader's top candidate | its support |
|---|--:|--:|--:|--:|
| `glyph/2/0/9/15/5` | 0.5 | 1.0 | 1.0 | 2.0 |
| `glyph/4/0/9/5/7` | 0.25 | 1.0 | 0.5 | 2.0 |

(A third, `glyph/2/1/7/7/1`, also overrides the ordering but its crop was
REFUSED by the frame control — see §3.)

These are the cases worth reading first: they are where the neighbours
contradict the reader, which is the whole claim of the stage. If the rule is
right on these it is buying something no consequence could; if it is wrong on
these it is overwriting a better answer with a worse one.

## 3. The crops, and the control that refused six of them

`probe/crop_inferred.py`, 600 dpi, corner brackets on the exact head, a staff-
space ruler down the left edge.

⚠️ **THE FRAME CONTROL CAN FAIL, AND IT WAS RUN IN A STATE WHERE IT DOES.**
Rendered at the wrong resolution (300 dpi against the record's 600), the
staff-line contrast goes NEGATIVE and **16 of 16 are refused**. That is the
control working, not the tree failing, and it is why the 10 crops below are
evidence at all.

At the correct 600 dpi: **10 written, 6 refused.**

| refused subject | contrast | note |
|---|--:|---|
| `glyph/2/1/7/7/3`, `glyph/2/1/7/7/1` | 5.00 | below the 8.0 margin |
| `glyph/4/0/0/12/2`, `glyph/4/0/0/12/4` | 7.77 | below the margin, narrowly |
| `glyph/4/0/1/12/0`, `glyph/4/0/1/12/4` | **−12.25** | INVERTED: the staff's own `Q.STAFF_LINES` rows are BRIGHTER than a half-space off them |

⚠️ **The margin was NOT lowered to recover the 5.00 and 7.77 pairs.** Lowering
it buys crops with the one thing a print check cannot afford to be wrong
about, which is whether the picture is the record's own frame. They stay
refused.

⚠️ **The −12.25 pair is a finding in its own right and is not this lane's.**
A staff whose recorded lines land on white is a staff-detection fault on
`staff/4/0/1`, visible here only because a frame control looked. Recorded, not
chased.

## 4. ⚠️⚠️ THE POPULATION IS MEASURED ON A PRE-2.4a RECORD

`notehead_is_not_a_notehead` verdicts in this record: **0**. Roadmap 2.4a
shipped two refusals — `too_narrow` and `clipped_fragment` — print-checked by
Sean 12 of 12 on 2026-09-22, and this record was gathered before that decision
existed. So the 16 inferences are counted over a notehead population that
**today's tree would not hand the rules unchanged**.

The sharpest instance is one of §2's two ordering-overrides. Every inferred
glyph but one has a canonical height of 105–150 (a notehead is about one staff
space, 100 units here). `glyph/2/0/9/15/5` has **height 47 at y = 0** — half a
head, at the very top edge of the cell's 4-space pad, which is the shape
`clipped_fragment` exists to refuse, and its crop shows it sitting in the
inter-staff gap at detector confidence **0.30**.

⚠️ **Whether 2.4a actually refuses it is NOT established here** — that needs a
re-adjudication on today's tree, not an argument from its dimensions. What IS
established is that the question is open and that the reach figure above is
therefore an upper bound.

One more shape worth naming: `glyph/4/0/8/2/3` has height **312**, two to three
times a notehead. A merged blob on a plate CLAUDE.md records as MERGING.

## 5. What must happen before the default is decided

1. **Re-gather or re-adjudicate on today's tree**, so the population is the one
   2.4a leaves behind. Until then reach is an upper bound and the two
   ordering-overrides may not both survive.
2. **Sean adjudicates the crops** — `out/print/`, manifest
   `crop-manifest-litolff.json`, `VERDICT_none_yet` null on every row. The two
   (surviving) ordering-overrides first.
3. **Breitkopf**, which has not been run here. The earlier findings record the
   funnel's shape INVERTING between the two plates (disagreement 15 → 96), so a
   Litolff-only answer is a one-publisher answer.

## 6. What this pass does NOT establish

- **No default is decided and none should be read from it.** No crop has been
  adjudicated by anyone.
- **The reference encoding was not used.** The obvious second instrument is the
  measure alignment through `works.json`, and it is deliberately not used here:
  the verified `984073-p2` row records that this raster **drops one barline**
  (the m19|m20 boundary, pipeline 16 bars against the print's 17), so the
  cell→measure map on page 2 is off by one after that point and five of the
  sixteen inferences are on page 2. A join that is silently off by a bar would
  score a right answer wrong and a wrong answer right. Pages 3 and 4 have clean
  windows and are scorable; that is the next step, not a claim made here.
- **The witnesses were not cropped.** A crop shows whether THIS note's printed
  duration matches; it does not show whether the neighbours the rule borrowed
  from were read correctly. Both rules are only as good as those witnesses.
- **n = 1 document, 16 inferences, 10 crops.**
