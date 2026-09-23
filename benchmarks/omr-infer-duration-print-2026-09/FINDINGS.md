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

### ⚠️ CLOSED: 2.4a DOES refuse it

`probe/would_2_4a_refuse.py` evaluates the rule's two conditions against the
record's own geometry — admissible only because both are pure arithmetic over
values this record already carries, and because `_cell_box_page(ev)` was read
and returns the raw `Q.CELL_BOX` value, the same number used here.

| | |
|---|---|
| height | 47 / 100 = **0.470 spaces**, under `CLIPPED_NOTEHEAD_MAX_SPACES` **0.6** |
| top edge | `bbox_page_px[1]` **1670.0** against `cell_box[1]` **1670.0** — distance **0.00 px**, tolerance 1.0 |
| `clipped_fragment` | short ∧ touching → **FIRES. 2.4a refuses this glyph as not a notehead.** |
| `too_narrow` | 1.460 spaces against the 1.0 floor → does not fire |

**So neither of the two ordering-overrides survives scrutiny.** One
(`glyph/2/0/9/15/5`) is on ink today's tree refuses as not a notehead at all;
the other (`glyph/4/0/9/5/7`) fails the reference membership check by moving
away from the encoded duration (§5b). The cases that were supposed to show the
stage buying something a consequence could not are, on this document, one
non-notehead and one wrong answer.

### How much of the reach is affected — measured, and it is SMALL

Running the same two conditions over all sixteen: **2.4a would refuse 1 of 16
(6%)**. The "reach is an upper bound" caveat above is therefore CORRECT BUT
SMALL, and saying only the first half would leave a false impression — the
pre-2.4a record does not inflate reach materially. It inflates it by one, and
that one happens to be an ordering-override.

Two further shapes the sweep surfaced, neither caught by either refusal:

* **`glyph/4/0/9/5/7` sits flush against the cell edge too (0.00 px) but is
  0.79 spaces tall, just over `clipped_fragment`'s 0.6 ceiling.** It is the
  second-shortest head in the set, on the boundary, and it is the one that
  fails the reference membership check. Suggestive that the net is slightly
  too tight here; NOT evidence for moving a measured threshold, which was set
  against 255 print-adjudicated boxes and must not be retuned to suit sixteen.
* **`glyph/4/0/8/2/3` is 3.12 spaces tall** — three times a notehead, a merged
  blob on a MERGING plate. Neither shipped refusal targets over-height ink, so
  nothing refuses it. Recorded; not this lane's to fix.

⚠️ This still does not decide the default: n = 1 document, the other 14
inferences unexamined by either instrument, and a re-adjudication of the whole
population on today's tree (§5.1) remains the honest way to restate reach. But
the direction of the evidence is now negative rather than absent.

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

## 5b. The reference encoding, on the two pages whose join is clean — AND THE
##     FIRST DRAFT OF THIS CHECK WAS A CONTROL THAT COULD NOT FAIL

`probe/score_against_reference.py`. Pages 3 and 4 only; the join's own control
is the record's cell counts being UNANIMOUS across every staff and matching the
verified window exactly (p3 16+18 = mm 49–82; p4 15+15 = mm 83–112), re-checked
at run time, refusing rather than scoring on disagreement. **11 of the 16
inferences are on a clean join.**

⚠️⚠️ **THE FIRST DRAFT REPORTED "6 OF 6 INFERRED CORRECT" AND THAT NUMBER WAS
WORTHLESS.** Two independent faults, both caught before it was believed:

1. **It compared left-to-right noteheads against a PART-MAJOR note list.**
   Flauti is reference parts `[0, 1]`; concatenating them gives
   part0-n0, part0-n1, part1-n0, part1-n1, which is not page order. Every one
   of the six "correct" rows was a two-part staff.
2. **It counted HEADS where the reference counts NOTES.** Measured:
   `cell/4/0/0/12` holds 4 heads at **2 distinct x** — two events of two
   stacked heads, not four notes. The 4-against-4 match was an accident.

The repair groups heads into events by x and aligns against whichever part's
own note count matches. And then the real result appears:

> **0 of 11 rows are INFORMATIVE.** Every positionally comparable bar has a
> rhythmically UNIFORM reference — all `1.0`, or all `2.0` — so every
> alignment agrees and no index could have been wrong. **A check that cannot
> fail is not a check**, so these rows are reported and excluded from the
> tally rather than counted as passes.

**That is a result about the instrument, not about the rules.** On this
document the encoding cannot discriminate a right duration inference from a
wrong one positionally, because the rules fire overwhelmingly in bars of even
rhythm — which is, on reflection, exactly where neighbouring staves agree and
therefore exactly where these rules CAN fire. The instrument and the rules
select the same bars.

### The membership check, which CAN fail — and does, once

Weaker than positional and needing no alignment: is the inferred duration
present among the reference bar's durations at all?

| | rows |
|---|--:|
| inferred present, reader's top also present | 10 |
| **inferred ABSENT, reader's top also absent** | **1** |

The single failure is **`glyph/4/0/9/5/7`, m88 Violoncello** — and it is one of
§2's two ordering-overrides, the one with the highest detector confidence on
the page (0.77). The rule writes **0.25** where the reference bar holds only
**1.0**, overriding the reader's own **0.5**. Both are wrong; the rule moved
**further from** the reference, not nearer.

⚠️ **Do not read that as the rule being refuted.** That bar is badly misread
BEFORE any inference: our cell holds **4 events / 5 heads where the reference
has 2 notes**. The rule borrowed a length from neighbours in a bar whose ink we
had already over-read, which is the failure mode its own docstring names
("the column grouping may have merged two instants"). What it shows is that the
rule does not repair a bad bar and can deepen it — and that the 10 agreeing
rows carry little weight, because on those the rule and the reader picked the
SAME value, so they test the reader and not the rule.

**Net: the encoding returns one failable observation, and it is negative.**
Nine of the other ten are uninformative by construction. The crops remain the
instrument that can actually settle this.

## 6. What this pass does NOT establish

- **No default is decided and none should be read from it.** No crop has been
  adjudicated by anyone.
- **The reference encoding settles nothing positionally** (§5b): 0 of 11 rows
  discriminate. Page 2's five inferences are not scored at all — the verified
  `984073-p2` row records this raster **dropping one barline** (m19|m20,
  pipeline 16 bars against the print's 17), so its cell→measure map is off by
  one after that point and a silently shifted join would score a right answer
  wrong.
- **The one negative membership result is not a refutation.** Its bar is
  over-read before the rule runs (4 events against the reference's 2 notes).
- **The witnesses were not cropped.** A crop shows whether THIS note's printed
  duration matches; it does not show whether the neighbours the rule borrowed
  from were read correctly. Both rules are only as good as those witnesses.
- **n = 1 document, 16 inferences, 10 crops.**

---

# §7. Sean's adjudication, 2026-09-23 — and it moves the finding off durations

**He read the crops and found the crop defective first**, which is the more
useful half:

> *"in the 2 cells you sent me there is a staff at the top and a staff at the
> bottom - i dont know which staff the cell is focussing on. the first cell has
> an 8th note on a ledger line above the staff on the bottom of the cell. the
> 2nd cell has an 8th note on a ledger line below the staff in the top of the
> cell"*

A window centred on a note in the GAP between two staves shows both and commits
to neither. The crop could not distinguish a correct attribution from a
cross-staff error — which is exactly what both subjects turned out to be.
`probe/crop_inferred.py` now names the staff the record filed the subject on and
traces that staff's own five `Q.STAFF_LINES` across the crop in green.

## The geometry agrees with him on both, and both are MISATTRIBUTED

| subject | filed on | glyph page-y | the staff it actually sits on |
|---|---|---|---|
| `glyph/4/0/9/5/7` | staff 9 = **Violoncello** | 1865.6–1878.0 | **staff 10 = Basso**, lines 1894–1957 — the note is 1 space above its top line, i.e. its first ledger line |
| `glyph/2/0/9/15/5` | staff 9 = **Viola** | 1670.0–1677.5 | **staff 8 = Violino II**, lines 1585–1649 — 1.3 spaces below its bottom line, its first ledger line |

## ⚠️ THIS REVERSES §5b's VERDICT ON `glyph/4/0/9/5/7`

§5b scored it against **Violoncello** m88 — `[1.0, 1.0]` — and called inferred
and reader's-top both absent, "both wrong". That comparison was against the
wrong part. Against **Basso** m88, the part the note actually belongs to:

| | |
|---|---|
| reference (Basso, m88) | `[0.5, 0.5, 0.5]` — **eighths** |
| Sean, off the print | **an eighth** = 0.5 |
| reader's top candidate | **0.5 — CORRECT** |
| the rule's inference | **0.25 — WRONG** |

Two independent sources — the print and the encoding of the correct part —
agree, and they agree against the rule. **The reader had it right and
`collapse_duration_to_barline` overrode it with a worse answer.**

## What this pass now says

The two ordering-overrides were chosen as the cases that decide whether the
stage buys anything, because they are the only ones where the rule contradicts
the reader. On this document:

* one (`glyph/2/0/9/15/5`) is ink **2.4a refuses as not a notehead**, and is
  **filed on the wrong staff**;
* the other (`glyph/4/0/9/5/7`) is **filed on the wrong staff** and the rule's
  override is **wrong against both the print and the encoding**.

⚠️ **THE FINDING HAS MOVED OFF DURATIONS.** Both discriminating subjects are
`glyph_owner` failures across a staff boundary — a ledger-line note in the gap,
given to the neighbour. The duration inference is DOWNSTREAM of that, and a
duration rule cannot be fairly judged on ink the owner decision has already
misplaced. Roadmap 2.3's default decision should not be taken on these two; the
prior question is why a first-ledger-line note in the gap goes to the wrong
staff, which is `glyph_owner`'s contest (CLAUDE.md §10: ladder completeness,
then range, then distance) and is not this lane's.

⚠️ Still n = 2 subjects. What it establishes is that the two cases that were
supposed to settle 2.3 cannot settle it, and why.

## §7b. Sizing the owner question — 358 of 2,347, and what that number is NOT

Sean's two subjects are n = 2. Swept the same record, every notehead carrying a
page box (2,347): for each, the distance from its FILED staff's nearest line
against the distance to the nearest OTHER staff's.

| | |
|---|--:|
| noteheads examined | 2,347 |
| **a neighbouring staff is clearly nearer than the filed one** (by over half a space) | **358 (15.3 %)** |
| of those, carrying a `glyph_owner` verdict — contested, and resolved to the FARTHER staff | **197** |
| of those, with no `glyph_owner` verdict — never contested at all | **161** |

⚠️⚠️ **358 IS NOT A MISATTRIBUTION COUNT AND MUST NOT BE QUOTED AS ONE.** It is
the population carrying the geometric signature of Sean's two. A notehead may
sit legitimately far from its own staff on ledger lines; what makes the two
adjudicated cases wrong is the PRINT, not the arithmetic. **Exactly 2 of the
358 have been checked against a page, and both were wrong.** The other 356 are
unverified in both directions.

**One competing explanation was tested and REFUTED.** If the recorded staff
geometry were simply wrong for some staves, every note on them would read as
distant and the signal would be an artefact. Every staff line span in the
concentration table is **63–65 px** — uniform across pages, systems and staves.
The staves are consistently detected; this is not a staff-detection artefact,
which also distinguishes it from the `staff/4/0/1` contrast −12.25 fault in §3.

**It is not one bad staff either.** The most affected is `staff/4/0/5` at 28 of
36, but the population spreads across at least ten (page, system, staff) blocks
on all four pages.

**What this justifies**: a lane that adjudicates a print sample of the 358
against the plate and, if the rate holds, asks why `glyph_owner`'s contest
(ladder completeness → range → distance) puts a first-ledger-line note in the
gap on the wrong side — and why 161 of them reached no contest at all, which is
a question about the DOMAIN (`subjects_from`), not about the scoring.
**What it does not justify**: any claim about how many are wrong.

---

# §8. ⚠️ TWO CORRECTIONS TO §7 AND §7b — `glyph_owner` IS NOT THE CULPRIT

Sean, 2026-09-23, on being shown the two crops:

> *"how can you have a cell that doesnt know what staff it is dealing with...
> Also notes should never be that far away from a staff unless there are ledger
> lines close to the staff connecting the note conceptually to the staff"*

Both halves were right, and chasing them overturned this lane's own diagnosis.

**On the first half, the write-up was sloppy and the tree is not.** A cell knows
its staff exactly — `cell/2/0/9/15` IS staff 9's cell 15, and cells run one
measure at a time keyed `(page, system, staff, cell)`. What a cell is, is a
CROP, padded 4 staff spaces (6 where the neighbour is far), and on a
conductor's page that pad reaches the next staff's ink. `glyph/2/0/9/15/5`
therefore means *the 5th detection in staff 9's cell-15 crop*, never *a note
belonging to staff 9*. §7's phrase "filed on the wrong staff" invited exactly
the confusion Sean reports.

**On the second half, his convention is confirmed by the geometry:**

| | distance from the FILED staff | distance from the staff Sean names |
|---|--:|--:|
| `glyph/4/0/9/5/7` | 3.60 spaces below staff 9 | **1.41 spaces above staff 10** |
| `glyph/2/0/9/15/5` | 3.77 spaces above staff 9 | **1.55 spaces below staff 8** |

1.4–1.55 spaces is the FIRST LEDGER LINE position. 3.6–3.8 spaces would need a
three-rung ladder. The conventional reading is unambiguous in both, and it is
his. The rungs that should prove it were not detected: the one x-overlapping
`ledgerLine` near `glyph/4/0/9/5/7` is **7.34 spaces away**, and
`glyph/2/0/9/15/5`'s cell holds **zero** ledgerLine detections — the recall gap
that made 2.4a's `unladdered` rule net negative and kept it held back.

## Correction 1 — `glyph_owner` DECIDED `glyph/4/0/9/5/7` CORRECTLY

```
subject glyph/4/0/9/5/7   quantity glyph_owner
outcome decided   value "staff/4/0/10"   reason "distance"
```

**`staff/4/0/10` is Basso. That is exactly where Sean says the note belongs.**
§7's claim that both subjects are `glyph_owner` failures is WRONG for this one:
ownership got it right, by distance, without needing the ladder.

The other subject, `glyph/2/0/9/15/5`, has **no `glyph_owner` verdict at all** —
it never entered the contest. Two different causes, not one.

## Correction 2 — §7b's "197 resolved to the FARTHER staff" was UNFOUNDED

§7b reported that 197 of the 358 were "contested, and resolved to the FARTHER
staff". **That sweep only checked whether a verdict EXISTED; it never read the
verdict's VALUE.** Presence is not direction, and stating it as direction was
the error CLAUDE.md names — a convincing number offered as evidence about its
cause. Reading the values:

| of the 358 geometrically suspicious noteheads | |
|---|--:|
| contested → **resolved to the NEAR staff (correct)** | **189** |
| never contested at all | 161 |
| contested → resolved elsewhere | 8 |

**`glyph_owner` is largely getting this right.** The 8 are worth a look; the 189
are it working.

## What the defect actually is

Both duration rules declare:

```python
reads=(Q.ONSET_COLUMN, Q.EVENT, Q.DURATION, Q.GLYPH_BOX)
```

**`Q.GLYPH_OWNER` is absent** (`inferences.py:298` and `:389`). So the rules walk
glyphs by their DETECTION CELL and use that staff's onset columns and that
staff's neighbours as witnesses — for a glyph ownership has already awarded
somewhere else. On `glyph/4/0/9/5/7` the record says Basso; the rule inferred
0.25 from **Violoncello's** column structure; the note is a Basso eighth
(reference `[0.5, 0.5, 0.5]`, and Sean reads an eighth off the print).

That is CLAUDE.md's standing bug class in its sharpest form: **the value existed
and nothing read it.** And the declaration is the enforcement — a rule that
tried to read `Q.GLYPH_OWNER` without declaring it would raise
`UndeclaredEvidence`, so this is a one-line omission with a measurable
consequence, not a hidden coupling.

⚠️ **Still not a default decision, and the target has moved again**: the
question for 2.3 is no longer "are these rules right" but "are they reading the
right glyphs at all". The 161 never-contested glyphs remain a separate
question, about `glyph_owner`'s DOMAIN (`subjects_from`), and
`glyph/2/0/9/15/5` is one of them — though 2.4a refuses that one as not a
notehead in any case.
