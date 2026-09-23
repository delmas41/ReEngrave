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

## §8b. The size of the defect on this document: 2 of 16

Every inference checked against its glyph's own `Q.GLYPH_OWNER` verdict:

| | inferences |
|---|--:|
| **ownership points at a DIFFERENT staff than the detection cell** | **2** |
| ownership agrees with the detection cell | 1 |
| no ownership verdict — the glyph never entered the contest | 13 |

The two are both `collapse_duration_to_barline`:

* `glyph/4/0/9/5/7` — cell staff 9 (Violoncello), owned by **`staff/4/0/10`**
  (Basso). Sean adjudicated this one; the rule inferred 0.25 from Violoncello's
  columns where the note is a Basso eighth.
* `glyph/2/1/0/13/0` — cell staff 0, owned by **`staff/2/1/1`**. **Not yet seen
  by anyone**; it is the same shape and is the natural third crop.

So wiring `Q.GLYPH_OWNER` into the two rules' `reads` would change the answer on
**2 of 16 (12.5 %)** here. The other 13 are a different matter: with no
ownership verdict the detection cell is the only claim there is, so reading the
quantity would return nothing and the rule would behave exactly as it does now.
**Fixing the omission does not touch them** — they need `glyph_owner`'s DOMAIN
widened, which is the `subjects_from` question and a separate lane.

⚠️ 12.5 % is n = 1 document and 16 inferences. It is a size, not a rate.

---

# §9. The fix, measured — `Q.GLYPH_OWNER` wired in (Sean, 2026-09-23)

He adjudicated the third crop the same way — *"it belongs to a staff on the
bottom that is not the staff that has the green lines going through it"* —
making it **3 of 3** subjects where his reading, the recorded ownership verdict
and the geometry all agree, and then directed the change:

> *"add Q.GLYPH_OWNER to the rules' reads and re-measure"*

## The change

Both rules now declare `Q.GLYPH_OWNER` in `reads`, and `_events_with_x` drops a
glyph whose ownership verdict names a staff other than the cell it sits in.

* **The loser is DROPPED, not relocated** — CLAUDE.md §10, *"a resolved contest
  DROPS the loser; it never relocates it."* Moving the glyph into the winner's
  bar would be a second ownership decision taken by a duration rule.
* **Silence is not a verdict.** A glyph with NO ownership verdict was never
  contested — `adjudicate_glyph_owner`'s domain is the contested population —
  so the detection cell is the only claim there is and the glyph is KEPT.
  Reading absence as "not mine" would silently delete 13 of the 16.

## Measured, same record, same instrument

Control first, unchanged: **19,563 of 19,563 verdicts reproduced, 0 differ.**

| | base | arm |
|---|--:|--:|
| `collapse_duration_by_column` | 6 | 6 |
| `collapse_duration_to_barline` | 10 | **7** |
| **total inferences** | **16** | **13** |
| surviving inferences whose VALUE changed | — | **0** |

**Three dropped, and I predicted two.** The third is the interesting one:

| dropped | why |
|---|---|
| `glyph/4/0/9/5/7` | owned by `staff/4/0/10` — Sean's first crop |
| `glyph/2/1/0/13/0` | owned by `staff/2/1/1` — Sean's third crop |
| `glyph/2/1/0/13/5` | **no ownership verdict — kept by the guard, and still lost its inference** |

The third sits in the **same bar** as the second. Removing a foreign note
changes that bar's event structure, so the surviving glyph's endpoint — *is
there a further onset in this bar* — is no longer the same question. That is
the fix working through, not a second defect: the rule's premise was being
evaluated over a bar contaminated by another staff's ink, and with the
contamination gone it declines rather than infers. **A knock-on that produces a
REFUSAL is the safe direction**, and it is the reason the prediction of two was
low.

**Nothing changed value.** The fix is purely subtractive on this document: it
removes three inferences and corrects none, because the rules had no mechanism
to arrive at the right answer for ink they should not have been reading.

## Gate

`pytest -m "not slow"` **2,823 passed**, 3 skipped, 0 failed.
`python3 -m tools.omr.staged.check` **255 open, status ok — identical to main**.
`TestItReadsGlyphOwner` **run RED first** against the pre-fix tree (reports 1
inference where it expects 0), with two positive controls in the same class so
it cannot pass by refusing everything: a glyph owned by its OWN staff still
fires, and an uncontested glyph still fires.

## ⚠️ What this still does not settle

Both rules remain **default OFF** and this does not change that. The fix
removes three wrong inferences from a population of sixteen; it does not show
that the remaining thirteen are right. The reference encoding could not
discriminate them (§5b) and only three subjects have been read against a print.
**2.3's default decision is still open**, and it is now a cleaner question:
the rules no longer infer from ink they do not own.

## §9b. Does the same blind spot exist elsewhere? Checked — no.

The obvious next worry: if the INFER duration rules read glyphs by their
detection cell without asking who owns them, does the EXPORT path do the same?
That would matter far more, because export runs by default while both duration
rules are off.

**It does not.** `staged/export.py:971`:

```python
owner = rec.value(Q.GLYPH_OWNER, sub)
if A.is_relocated_copy(sub, owner):
    _drop("owned_by_another_staff", s)
    continue
```

`owned_by_another_staff` is one of the named refusal buckets the balance
equality already accounts for, and the comment there states the same rule this
fix follows — the contest is resolved by REFUSING the copy, not by moving it,
citing Sean's *"2 of the same note next to each other connected to the same
stem."* EVALUATE also consumes the quantity (`consequences.py:368`,
`cause=Q.GLYPH_OWNER, effect=Q.PITCH`).

So the omission was confined to the two INFER duration rules, and the fix
applies the discipline the exporter already had rather than inventing one.

---

# §10. The domain of `glyph_owner`: why 161 were never contested, and the process to hand them in

2026-09-23. §8 closed with two open halves: the 8 that resolved elsewhere, and
the 161 that reached no contest at all — *"a question about `glyph_owner`'s
DOMAIN (`subjects_from`), not about the scoring."* This section answers it.
Sean's brief: *"determine the process to get the right notes handed to the
right staff."*

`probe/owner_contest_domain.py`. It decides nothing and crops nothing; it
reports which glyphs were handed to `adjudicate_glyph_owner` at all.

## §10a. ⚠️ TWO CORRECTIONS TO THE BRIEF BEFORE ANY NUMBER

**The 358 / 161 / 189 / 8 partition is NOT on the whole-movement record.** §7b
says "the same record", and the record this whole benchmark uses is
`beethoven5-p1-p4-ink-identity.record.json` (pdf pp.1–4). The session brief for
this pass called it "the Litolff whole-movement record"; it is not.
`beethoven5-litolff-mvt1-whole-20260923.record.json` gives **11,632 / 1,725 /
960 / 704 / 61** — the same shape at 4.8× the scale (41 % never contested
against 45 %), which is corroboration, not the same measurement. **Every figure
below is p1–p4 unless the whole-movement column says otherwise.**

**§7b's probe was never committed** — `git show --stat b19f4258` touches
`FINDINGS.md` and nothing else. The population definition here is reconstructed
from §7b/§8's prose, and reproducing 2,347 / 358 / 189 / 161 / 8 EXACTLY is the
control that the reconstruction is the same population. It reproduces.

**The arithmetic control can fail and was run failing first.** Everything here
recomputes `gather._band_distance_spaces` off the record's own
`Q.GLYPH_BOX.detail.bbox_page_px` and `Q.STAFF_LINES`. Against the rows GATHER
actually wrote: **2,772 of 2,772 agree, worst |Δ| 0.00e+00** (whole movement:
12,026 of 12,026). With the staff spacing perturbed 1 %
(`OWNER_DOMAIN_BREAK_CONTROL=1`) it reports **3 of 2,772** and says so. The
partition itself survives that perturbation unchanged at 358 / 161 — worth
knowing: the signature is not sitting on a knife edge.

## §10b. The cause, and it is ONE cause with three sub-causes

| cause | count |
|---|--:|
| **`NO_BAND_ROW`** — no `Q.GLYPH_BAND_DISTANCE` row of ANY state exists for the glyph, so `adjudicate.subjects_for` never made it a subject and `adjudicate_one` never ran | **161** |
| `ABSTAINED_BANDS` — band rows exist but all are Abstentions (the glyph IS a subject; the adjudicator would return `no_contest`) | 0 |
| a band row present and still no verdict | 0 |
| **sum** | **161** |

**Not one of the 161 is a scoring failure, an abstention, or a scope fault.**
There is nothing at the subject to look at: `wants` and `Scope` are never
reached. The defect is entirely in `gather_ownership_evidence`'s construction
of the contest, upstream of the decision.

That construction (`gather.py:640-653`) admits a pair on three conditions: same
`(page, system)`, `di.smufl_name == dj.smufl_name`, and
`_iou(bi, bj) >= CONTEST_IOU` (0.5). Which condition rejected each of the 161,
measured against the glyph's own NEAR staff:

| sub-cause of `NO_BAND_ROW` | p1–p4 | whole mvt |
|---|--:|--:|
| **the same ink, detected twice, but the two copies' smufl NAMES differ** | **83** | 361 |
| &nbsp;&nbsp;— the SAME head spelled `…OnLine` on one staff and `…InSpace` on the other | 38 | 178 |
| &nbsp;&nbsp;— both noteheads, different head TYPE (`Black` vs `Half`) | 16 | 91 |
| &nbsp;&nbsp;— the near staff holds no notehead there at all (`fermataAbove`, `dynamicF`, `slur`, `arpeggiato`, `staff`) | 29 | 92 |
| **same smufl name, overlapping, but IoU below `CONTEST_IOU` 0.5** | **69** | 278 |
| &nbsp;&nbsp;— of those, IoU above the legacy 0.3 | 50 | 187 |
| **no glyph of any class on the near staff overlaps it** | **9** | 65 |
| **sum** | **161** | **704** |

⚠️ **THE PAD IS NOT THE PROBLEM, AND THE MEASUREMENT SAYS SO.** All **9 of 9**
(whole movement: 65 of 65) of the no-overlap glyphs sit INSIDE a `Q.CELL_BOX`
of the near staff. The near staff's crop already reaches the ink; the detector
did not fire on it there. Nothing here argues for growing the 4-space pad, and
CLAUDE.md §10 forbids it anyway.

### The single sharpest fact

`…OnLine` / `…InSpace` is **the head's position relative to A STAFF** — the
exact quantity the contest exists to arbitrate. One notehead in the gap is
`noteheadBlackOnLine` in the staff above's cell and `noteheadBlackInSpace` in
the staff below's, and `di.smufl_name != dj.smufl_name` then rules that they
are not the same thing. **The contest's identity test is keyed on the disputed
quantity.** 38 of 161 die on that alone.

Sean's own subject is the textbook case. `glyph/2/0/9/15/5`
(`noteheadBlackInSpace`, staff 9) overlaps a `noteheadBlackOnLine` on staff 8 —
the staff Sean read it onto — at **IoU 0.314**. It fails BOTH conditions: the
names differ AND 0.314 < 0.5. Its trace shows four GATHER rows and no
`glyph_band_distance` among them. `glyph/4/0/9/5/7`, which §8 confirmed
`glyph_owner` DECIDED correctly, differs in exactly one way: its twin on staff
10 carries the same name and clears the IoU bar, so it has two band rows and a
verdict.

### ⚠️ THE STAGED CONTEST IS THE LEGACY CONTEST, RESTATED AT TWO DIFFERENT VALUES

`transcribe._dedupe_cross_staff_detections` — FROZEN, and the reference reader —
admits a pair on `di["category"] == dj["category"]` and
`IoU > _CROSS_STAFF_DUPLICATE_IOU`, **0.3**, swept at 0.25/0.3/0.4/0.5 over
three orchestral works and documented as the lowest value costing no
correctly-matched note on any of them
(`benchmarks/omr-orchestral-e2e/DEDUPE_THRESHOLD.md`). The staged gather
restates the same predicate as smufl NAME equality and **0.5**, citing
`(A-OWN-3)`, whose assumption record was never written
(`omr-staged-dedupe-2026-09` §6.2 already recorded that and its own cost: 134
of 636 overlapping cross-staff groups with no verdict at all).

**And `category` is already on the record.** `gather.py:401` writes
`box_detail["category"] = d.category` into every `Q.GLYPH_BOX` row; the contest
loop reads `smufl_name` instead. CLAUDE.md's standing bug class, unchanged:
*the value existed and nothing read it.*

How many of the 161 the LEGACY predicate would hand in, counted (it changes
nothing):

| arm | p1–p4 | whole mvt |
|---|--:|--:|
| category equality **and** IoU > 0.3 — the legacy predicate | **87 of 161** | **374 of 704** |
| category equality alone, IoU left at 0.5 | 21 | 117 |
| smufl name alone, IoU > 0.3 | 50 | 187 |
| residual: no same-CATEGORY ink on another staff at all | 38 | 157 |
| residual: same category, IoU ≤ 0.3 (below the swept floor) | 36 | 173 |

Neither axis alone reaches half. **Together they hand in 54 % of the
never-contested, and neither value is new to this repository.**

## §10c. The 8 that resolved elsewhere — the scoring, read

Five DECIDED, three ABSTAINED; **in all five decided cases the winner is the
glyph's own filed staff**, and in none of the eight is it a third staff.

| subject | filed (spaces) | nearest (spaces) | outcome | reason | what the scoring did |
|---|--:|--:|---|---|---|
| `glyph/2/0/5/3/2` | 3.02 | 2.40 | decided → own | `range_veto` | near staff scores exactly −6.0; distance would have won it |
| `glyph/4/1/2/5/8` | 2.79 | 1.84 | decided → own | `range_veto` | same, margin 4.60 |
| `glyph/4/1/5/0/3` | 2.75 | 1.40 | decided → own | `range_veto` | same, margin 4.63 |
| `glyph/4/1/4/7/0` | 2.67 | 1.93 | decided → own | `ladder` | a COMPLETE ledger ladder to the filed staff, +4.0, beats distance |
| `glyph/4/1/5/8/0` | 2.39 | 1.76 | decided → own | `ladder` | ladder +4.0 AND the near staff vetoed |
| `glyph/4/1/3/13/0` | 3.48 | 0.65 | **abstained** | `tied` | see below |
| `glyph/4/1/3/13/2` | 3.49 | 0.64 | **abstained** | `tied` | " |
| `glyph/4/1/3/13/4` | 3.48 | 0.65 | **abstained** | `tied` | " |

Whole movement: 39 `range_veto`, 18 `ladder`, 4 `tied`; 57 of 61 to the filed
staff, **0 of 61 to a third staff**.

This is Sean's own convention doing the work — *"notes should never be that far
away from a staff unless there are ledger lines close to the staff connecting
the note conceptually to the staff"* — read in the two tiers that outrank
distance. **It is not evidence that the five are right**; none has been read
against a print. It is evidence that the scoring is behaving as declared and is
not where the 161 went.

**The three `tied` abstentions have an exact and slightly uncomfortable
mechanism**, read off the record:

| candidate | instrument | written range | clef | implied pitch | veto |
|---|---|---|---|---|---|
| `staff/4/1/3` (filed, 3.48 sp) | Bassoon | 34–72 | bass | G1 = 31 | **fires** |
| `staff/4/1/4` (near, 0.65 sp) | Horn | 41–77 | treble | G5 = 79 | **fires**, by 2 semitones |

Both vetoed. Because a veto Term and that candidate's distance Term share the
band row, `tally`'s correlated-group collapse counts the group ONCE at the
strongest weight, so **every vetoed candidate scores exactly −6.0 regardless of
distance** — which is why two candidates 2.8 spaces apart tie. Abstaining is
the right output for a tie, but a veto built for the IMPOSSIBLE firing 2
semitones out, and then being indistinguishable from a wild one, is a finding
of its own. **Recorded, not chased; it is not the 161.**

## §10d. The process — what would hand the right notes to the right staff

**ASK FIRST (CLAUDE.md rule 3).** How would a human read this off the page? A
reader does not consult the class name at all: the ink is ONE head, and which
staff owns it is settled by the ledger rungs that join it to a staff. Nothing
below lets a decision be made on less evidence than today — it lets the
decision be MADE AT ALL on ink where it currently is not.

**The stage is GATHER, and there is no ADJUDICATE version of this change.**
`adjudicate_glyph_owner`'s `subjects_from=Q.GLYPH_BAND_DISTANCE` is CORRECT and
must not move: the domain being the contested population is what makes
`adjudicate.is_relocated_copy` and `export._drop("owned_by_another_staff")`
safe — a glyph awarded elsewhere has a twin there BY CONSTRUCTION, so dropping
the loser cannot lose ink. Widening the DECLARATION rather than the contest
would break exactly that, and `test_staged_dedupe.py` asserts the declaration
off the registry so it would go red. The rows are measurements and ADJUDICATE
may not gather, so the change is in **`tools/omr/staged/gather.py ::
gather_ownership_evidence`** (the class test at `:647`, `CONTEST_IOU` at
`:538`) and nowhere else.

### The four changes, by cause, ranked

**1 — the class test reads `category`, not `smufl_name`** (83 of 161; 38 of
them pure spelling). One line: compare the `d.category` the row already
carries. **CONNECTS, does not guess**: it stops a string comparison from
overruling the detector's own statement that both copies are noteheads, and the
winner is still decided by ladder → range → distance on evidence that already
exists. ⚠️ It must NOT be allowed to settle the head TYPE as a side effect: for
the 16 `Black`-vs-`Half` pairs the drop of the loser silently picks a duration.
Those must be admitted with the disagreement VISIBLE (the losing row stays on
the record; `Q.NOTEHEAD_CLASS` disagreement is a fact for `duration`, not for
`glyph_owner`) or held out of this change and priced separately.

**2 — `CONTEST_IOU` returns to the measured 0.3** (50 of the 69). **CONNECTS**:
0.3 is not a new number, it is the swept legacy constant this file restated
without an assumption record. ⚠️ It must NOT go to 0.25 — measured to start
merging genuinely distinct neighbours and to drop three correctly-matched notes
on Brahms. The 36 that sit at or below 0.3 stay out; a clipped copy at IoU 0.1
is not a contest anyone can win, and inventing a clipping-tolerant overlap
measure to reach them would be a new rule with no measurement behind it.

**3 — the 38 with no notehead twin at all: DO NOT hand these to the contest.**
This is the one place a plausible fix is the wrong one. A glyph with no twin
that `glyph_owner` awarded to the neighbour would be DROPPED at export as
`owned_by_another_staff` and the note would vanish — turning a
wrong-staff error into a missing note, which is worse in every category on
`omr-cleanup-count-2026-09/CATEGORIES.md`. The admissible routes are (a) the
detector recall gap (the crop already reaches the ink: 9 of 9 inside the near
staff's `Q.CELL_BOX`), which is a DETECTOR question and one of `check`'s three
blind spots; or (b) recording the contest as a GROUP with the twin's SUBJECT, so
a resolution can relocate rather than drop — already specified in
`omr-staged-dedupe-2026-09` §6.6 and explicitly a GATHER change there. **Neither
belongs in this item.**

**4 — nothing changes in `adjudicate_glyph_owner`, `is_relocated_copy`,
`move_glyph` or `export`.** The scoring got 189 of 197 right and the 8 are
explained above. A change that also touched the scoring would make the delta
unattributable.

### What it must not do

* **Never relocate.** A resolved contest DROPS the loser. The domain may grow
  only where a twin exists.
* **Never widen the cell pad.** Measured here: the pad already reaches.
* **Never turn "cannot tell" into an answer.** `tied` stays an abstention;
  `no_contest` stays a decision for the glyph's own staff.
* **Never lower the IoU floor below the swept 0.3.**
* **No new flag.** CLAUDE.md rule 9 and §7: the product path reads at most 15.
  This is a correction of two values to the reference reader's measured ones,
  which is a behaviour change to be measured and landed or refused, not a knob.

### How it is measured

1. **REACH BEFORE ACCURACY.** Run `probe/owner_contest_domain.py` on both
   acceptance scans FIRST and print the population: how many NEW contests each
   axis creates, on Litolff AND on Breitkopf (which SHATTERS where Litolff
   MERGES, so the IoU axis need not transfer). An arm that moves nothing
   because it is inert and one that moves nothing because the page holds
   nothing to move are the same number.
2. **THE CONTROL THAT MUST HOLD: the 189 stay 189.** Loosening can add a THIRD
   candidate to a contest that already had two and flip it, so the arm must
   report every pre-existing `glyph_owner` verdict that changed, by subject,
   and not merely the count of new ones.
3. **THE ACCOUNTING CONTROL:** `export.status_census`'s `unaccounted` bucket
   stays empty and `owned_by_another_staff` is reported before and after. A
   rise there that is not matched by a fall in written noteheads is ink loss.
4. **THE PRINT CHECK, and it is the only thing that can say the notes went to
   the RIGHT staff.** `probe/crop_inferred.py` at the gather's own DPI, frame
   control that can fail, corner brackets on the exact head, and the filed
   staff's own five `Q.STAFF_LINES` drawn in green — the version Sean's
   adjudication forced. A sample of the newly-contested, and **a positive
   control in the same class**: some of the 189 in the same batch, unlabelled,
   so the sample can fail.
5. **IT IS A GATHER CHANGE, so `readjudicate.py` and `reexport_arm.py` are
   structurally blind to it and a zero from either is not evidence.** Price it
   with two full re-gathers (`benchmarks/omr-cleanup-count-2026-09/run_gather.sh`,
   then `benchmarks/omr-staged-notations-2026-09/regather_control.py` to prove
   the pair provenanced, clean and distinct). It shares that cost with
   `omr-staged-dedupe-2026-09` §6.1 (the staged gather's NMS arguments) and
   §6.6 (the contest as a group), all three of which are the same detection set
   and the same contest construction, so they should be one gather pair and not
   three.

## §10e. What this section does NOT establish

* **Not one of the 161 has been read against a print.** §7b's warning stands
  verbatim: 358 is the population carrying a geometric signature, not a
  misattribution count, and exactly 2 of it have ever been checked against a
  page. This section says why 161 were never ASKED; it does not say what the
  answer would have been.
* **It does not show the 87 would resolve to the near staff.** They would enter
  a contest and be scored on ladder → range → distance like the rest. The 189
  suggest that scoring is good; the 8 show it can also hold a note where it was
  cut, correctly.
* **n = 1 document, 2 records.** Breitkopf SHATTERS and is not measured here at
  all; the IoU axis in particular may behave differently on a plate where ink
  components are not marks.
