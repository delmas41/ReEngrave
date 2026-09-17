# `collapse_duration_to_barline` — the bucket the first rule declined by design

**2026-09-17.** A second INFER rule, its unit fixture, its mutation battery,
and one live defect found in the stage's own self-check on the way past.

Record: `library/_shared-records/beethoven5-p1-p4.record.json`, md5
`d3620ba9cb70fc93f6b7ee91b6cbe40a`, **verified against three committed
receipts before a byte was read**. Instrument:
`benchmarks/omr-infer-stage-2026-09/reinfer.py`, an INFER-only replay over a
fixed gather AND a fixed adjudication. **Control first: 16,773 of 16,773
verdicts reproduced exactly, 33,647 of 33,647 observations, 0 differ, 0
extra.**

⚠️ The replay is **blind by construction** to a GATHER change and to an
ADJUDICATE change. Nothing here is evidence about either.

---

## 1. THE CLAIM, AND WHY IT IS NOT THE FIRST RULE'S

`collapse_duration_by_column` stops at one condition with a comment saying
why:

> No next onset in this bar, so this note runs to the BARLINE and its length
> is the bar's — which is the meter, which this rule may not read.

**Right about the METER, wrong about the NEIGHBOUR.** The note's length is the
gap from its onset column to the barline, and we do not have to compute that
gap from the meter to know it. A neighbouring staff standing at the same
column with nothing after it has already measured the same gap and called it
something. The barline is a system-wide event, so both notes end at the same
instant.

It is the first rule's claim with the barline standing in for column *m*.

---

## 2. ⚠️⚠️ THE GUARD THAT MAKES IT LEGAL, AND IT IS NOT A NO-OP

`Q.METER` stays out of `reads`, and for this rule that had to be **earned**
rather than declared. Two consequences hand a duration out FROM the meter —
`size_measure_rest` (a lone whole rest takes the bar's length) and
`reconcile_duration` (a bar that does not sum is re-read until it does) — and
**both put the meter row in their `basis`**, checked at
`consequences.py:176` and `:334`.

Borrowing such a length would read the meter by proxy: the value would be
meter-derived while `reads` truthfully said it was not,
`infer.scoring_conflict` would report clean, and `probe/bar_fill.py` would
quietly stop being an independent self-check. So a witness whose provenance
closure contains `Q.METER` is refused, via `Log.quantities_in_closure` — **the
primitive `adjudicate.py` already uses for its circularity filter**, not a new
mechanism.

**Measured: it fires on 3 subjects, refusing 2, 2 and 3 witnesses.** Not a
theoretical guard.

---

## 3. THE ENDPOINT IS A PAIR, AND THE THIRD STATE IS THE POINT

Deriving *runs to the barline* from **no later COLUMNED event** would call a
note barline-bound whenever the event after it missed every column centre —
and then hand it a neighbour's whole-bar length. Three states:

| endpoint | meaning | who takes it |
|---|---|---|
| `(m, False)` | ends at onset column *m* | rule 1 |
| `(None, True)` | nothing follows: the BARLINE | rule 2 |
| `(None, False)` | something follows, in no column: **UNKNOWN** | neither |

⚠️ **Rule 1 is behaviourally UNCHANGED by this.** `follow` non-None implies
later events exist, so `(m, True)` is unreachable and the pair comparison is
equivalent to the old column comparison there. Its 7 inferences are the same 7.

---

## 4. REACH FIRST — and the `191` in the first rule's findings is NOT this
##    rule's population

`probe/reach.py`, which **self-checks against the rule's own output** (funnel
survivors must equal what the rule proposes; they do, 10 == 10).

| | |
|---|--:|
| narrowed durations standing in a column | 356 |
| ends at an onset column — **rule 1** | 165 |
| **runs to the BARLINE — rule 2** | **190** |
| UNKNOWN endpoint — neither | **1** |

⚠️ The first rule's FINDINGS records **191** at this stop. That figure is
*no next **COLUMNED** onset*, which is the barline case and the unknown case
added together: **190 + 1**. Citing 191 as rule 2's population would be wrong,
and the split is why `probe/reach.py` exists rather than a note in the margin.

⚠️ **The three-state fix is worth exactly ONE note on this document.** It is a
correctness guard, not a reach play, and saying so is the point — on a worse
page, or one whose columns are read less well, that number is not 1.

### Rule 2's funnel

| stop | |
|---|--:|
| no other staff runs k → barline | 56 |
| no witness with a DECIDED, non-meter length | 37 |
| the witnesses disagree | 15 |
| **fewer than 2 INDEPENDENT witnesses** | **71** |
| 0 candidates carry that length | 1 |
| **SURVIVES** | **10** |

⚠️ **The largest stop is `COLUMN_MIN_INDEPENDENT_WITNESSES`, which is the
stage's one UNMEASURED constant**, and it now costs **71** where the first
rule's write-up priced it at 28. That is a bigger number attached to the same
unmeasured 2, and it is a reason to measure it, **not** a reason to lower it —
lowering it buys reach with the one thing this stage cannot afford to be
wrong about.

---

## 4b. ⚠️ THE SECOND PUBLISHER — n = 2, AND THE FUNNELS DO NOT LOOK ALIKE

Breitkopf Brahms 1 mvt 1, pdf p0-3, `brahms1-breitkopf-p0-p3.record.json`,
md5 `52b98f1cdfee3b39f10e56c592828ea4` verified against its receipt. ⚠️ Its
provenance is **`dirty: False`**, where the Litolff record's is `dirty: True` —
so the second document is the better-provenanced of the two.

| | Litolff | Breitkopf |
|---|--:|--:|
| narrowed durations standing in a column | 356 | **536** |
| ends at an onset column (rule 1) | 165 | 297 |
| **runs to the BARLINE (rule 2)** | **190** | **239** |
| UNKNOWN endpoint (neither) | 1 | **0** |
| **rule 2 infers** | **10** | **16** |

**The claim transfers.** Rule 2's population is a third to a half of all
narrowed durations on both plates, and the self-check holds on both (16 == 16).

⚠️⚠️ **BUT THE FUNNEL'S SHAPE INVERTS, AND THAT IS THE FINDING.**

| stop | Litolff | Breitkopf |
|---|--:|--:|
| no other staff runs k → barline | 56 | 17 |
| no witness with a DECIDED, non-meter length | 37 | 20 |
| **the witnesses DISAGREE** | **15** | **96** |
| fewer than 2 INDEPENDENT witnesses | 71 | 70 |
| 0 candidates carry that length | 1 | **20** |
| SURVIVES | 10 | 16 |

On Litolff the dominant refusal is **availability** — 56 + 37 = 93 of 190 have
no usable witness at all. On Breitkopf it is **disagreement**: 96 of 239, more
than six times Litolff's count, with a further 20 where the neighbours name a
length this reader never admitted.

**That is the unanimity requirement doing its job on the worse-read plate, and
it is corroborated from outside this work.** CLAUDE.md already records
Breitkopf reading **108 of 493 per-staff durations right (22%)** against
Litolff's **59%**. A document whose staves disagree with each other more is a
document whose staves are read worse, and the rule responds by **going quiet
rather than going wrong** — which is what *one dissenter refuses the whole
inference* was written to do, observed rather than asserted.

⚠️ **The meter guard is 4.7× busier there**: it refuses a witness on **14**
subjects against Litolff's 3, consistent with a plate carrying more
measure-rest and reconciled durations.

⚠️ **The UNKNOWN endpoint is 0 on Breitkopf.** So the three-state fix is worth
1 note on one document and 0 on the other. It remains a correctness guard
whose value is that it cannot be wrong, not a reach mechanism — and two
documents is not enough to call it rare.

---

## 5. WHAT THE STAGE NOW PRODUCES


| | Litolff | Breitkopf |
|---|--:|--:|
| `collapse_duration_by_column` | 7 | 25 |
| **`collapse_duration_to_barline`** | **10** | **16** |
| **total** | **17** | **41** |

All labelled, 0 skipped, on both. **7 → 17 and 25 → 41**: the new rule adds
**+143%** on Litolff and **+64%** on Breitkopf.

The population the stage can speak about at all goes **165 → 355 of 356** on
Litolff and **297 → 536 of 536** on Breitkopf — where, the UNKNOWN endpoint
being absent there, the two rules between them now reach **every** narrowed
duration standing in a column.

---

## 5b. ⚠️⚠️ THE UNMEASURED CONSTANT, NOW PRICED — AND THE SHAPE SAYS 2 IS A
##     BOUNDARY, NOT A MIDPOINT

`COLUMN_MIN_INDEPENDENT_WITNESSES` is the stage's one unmeasured constant and
is the largest single stop in both rules' funnels. `probe/witness_floor.py`
prices it in **reach**, which is the half a machine can answer — its own
docstring refuses to pretend otherwise.

⚠️ **The probe reproduces all four shipped totals independently** (Litolff 7
and 10, Breitkopf 25 and 16 at the shipped floor of 2), and its Litolff
`by_column` population of **n = 35 unanimous** is exactly the figure the first
rule's FINDINGS published. So it is measuring the rule, not itself.

### Survivors by floor

| | | floor 1 | **floor 2 (shipped)** | floor 3 |
|---|---|--:|--:|--:|
| Litolff | by column | 25 | **7** | 4 |
| Litolff | to barline | 52 | **10** | 3 |
| Breitkopf | by column | 55 | **25** | 3 |
| Breitkopf | to barline | 56 | **16** | 10 |

### The distribution — the informative artefact

Independent-group counts over the cases that reached the floor at all
(unanimous, at least one witness):

| | n | 1 | 2 | 3 | 4 | 5 |
|---|--:|--:|--:|--:|--:|--:|
| Litolff, by column | 35 | **28** | 3 | 4 | | |
| Litolff, to barline | 82 | **71** | 8 | 3 | | |
| Breitkopf, by column | 82 | **49** | 28 | 2 | 3 | |
| Breitkopf, to barline | 106 | **70** | 18 | 5 | 5 | 8 |

⚠️⚠️ **THE MASS IS AT EXACTLY ONE, ON BOTH DOCUMENTS AND BOTH RULES** — 80%,
87%, 60% and 66%. So the population the floor refuses is **overwhelmingly
single-witness**, and the floor at 2 is not slicing a continuum: it is sitting
on the boundary between *one staff said so* and *two independent staves agree*.

**That is the justification the constant never had.** It was set at 2 because
*one witness is not corroboration*, with its docstring admitting the number was
not measured. Measured, the number turns out to sit where the population
actually separates, which is a different and much better reason to keep it.

⚠️ **Floor 3 is both expensive and erratic** — Litolff's barline rule loses
70% of its inferences, Breitkopf's `by_column` loses 88%, but Breitkopf's
barline rule only 38%. A constant whose cost swings that far between two
documents is not one to raise on either document's evidence.

⚠️⚠️ **Floor 1 is printed and is NOT proposed.** It would take Litolff's
barline rule 10 → 52 — and it abolishes corroboration entirely, making a single
staff's reading an inference about another staff's note. That is the one thing
the stage's whole design rests on not doing, and a reach number is not an
argument for it.

⚠️ **This prices only reach.** Whether the extra inferences at a lower floor
are RIGHT is unmeasured and needs crops. Breitkopf's richer tail (cases with 4
and 5 independent groups, absent on Litolff) is a property of a 27-stave
system against a 12-stave one, not of the rule.

---

## 6. ⚠️⚠️ A LIVE DEFECT FOUND ON THE WAY PAST: THE STAGE'S SELF-CHECK HAS
##    BEEN SILENTLY CIRCULAR SINCE 2026-09-15

`probe/self_check.py` exists to prove `bar_fill` is independent of the rule
under test, and its condition 2 is stated in its own docstring:

> ⚠️ `OMR_METER_FROM_BARS` MUST BE OFF … With it on, the denominator is
> derived from the very quantity the rule moves, and the test becomes
> circular through a flag nobody would think to check. **Off by default;
> asserted here rather than assumed.**

It was neither off by default nor asserted. The check read

```python
os.environ.get("OMR_METER_FROM_BARS", "0")   # allow-list: default OFF
```

while the owning predicate at `staged/adjudicators/rhythm.py:1144` reads

```python
os.environ.get(METER_FROM_BARS_ENV, "1") ... not in ("0","","false","no","off")
```

— **default ON, deny-list**, since the 2026-09-15 flip. So with the variable
unset, which is the default configuration and what every run in this thread
has had, the pipeline had the flag **ON** and the check printed
`'0' -> ok`.

**That is the guard failing in precisely the manner it was written to
prevent**, and it is three of this repository's recorded patterns at once: the
flag-direction hazard (five shipped flags had the test backwards), *a fallback
must never convert "cannot tell" into a definite answer*, and a constant
restated instead of imported.

**REPAIRED** by importing `rhythm.meter_from_bars_enabled()` so the two cannot
drift. It now reports:

```
OMR_METER_FROM_BARS='<unset>' (resolved: ON) -> REFUSED
```

⚠️ **The consequence is that INFER's only truth-free self-check does not run
under current defaults**, and that is the honest state rather than a
regression introduced here. A replay arm may legitimately assert
`OMR_METER_FROM_BARS=0` — the flag acts in ADJUDICATE and this record's meter
verdicts are already fixed — but that is a decision with a reason, which is
what the refusal now forces someone to supply.

---

## 7. THE TESTS, AND THE BATTERY

⚠️⚠️ **THE REGISTERED RULES HAD NO UNIT FIXTURE AT ALL.**
`test_infer_stage.py` asserts the HARNESS's five disciplines using one-off
rules installed per test — right for what it covers, and it means either real
rule could have stopped firing entirely with the suite green. The only thing
exercising them was a benchmark arm over a 132 MB record needing `library/`.

`tools/omr/tests/test_infer_barline_rule.py` builds the smallest system the
rules can actually walk — three staves, one bar, two onset columns,
page-frame glyph boxes, `Q.ONSET_COLUMN` in the shape `adjudicate_onset_column`
really writes — and asserts **both** rules on it. 23 tests. The INFER suite is
**66 green**.

⚠️ The closed `READERS` vocabulary rejected the first fixture outright
(`'test' is not a known reader`). A vocabulary that refuses a plausible typo
refuses a plausible fixture too, which is the design working.

**Mutation battery: 14 arms, 14 red, restore verified by hash, positive
control (`refuse_everything`) red.** It carries an **in-flight sentinel** and
**refuses a dirty `tools/` tree** without `--force`, both from CLAUDE.md's
record of a battery killed mid-arm leaving its mutation on disk
indistinguishable from a real edit.

⚠️ **The first run reported 2 survivors and they were the two recorded
kinds**, one each:

* **a MIS-AIMED ARM** — `an_unknown_endpoint_is_treated_as_the_barline` aimed
  at a fixture where the witnesses run to the barline while the subject's
  endpoint is unknown, so the *witness* comparison refuses them and the
  subject filter never gets a chance to act. Retargeted at the fixture where
  every staff shares the unknown endpoint.
* **a REAL TEST GAP** — comparing the endpoint on the column half alone
  survived, because in the existing fixture the rejected witness ends at a
  *column*, so the halves already differ. The discriminating case is a witness
  whose endpoint is **unknown**: it shares the `None` column with a
  barline-bound subject and only the pair separates them. That test did not
  exist and now does.

---

## 8. TWO FAULTS OF MY OWN, RECORDED RATHER THAN SMOOTHED OVER

1. **A detail field where a lone `0` was ambiguous.**
   `witnesses_refused_meter_derived: 0` reads identically for *this rule
   checked and refused nobody* and *this rule does not check* — and rule 1
   does not check. Now a flag travels beside the count
   (`refuses_meter_derived_witnesses`), and both are written even when zero.
   Same lesson as `empty_bars_padded_without_meter`, which was incremented
   only on the bad branch and so vanished from the report exactly when
   everything was fine.

2. **A comment claiming a guard that lives somewhere else.** The witness
   comparison carried a note saying it excluded the unknown-endpoint case. It
   does not: two unknowns compare **equal** as `(None, False)`. What keeps
   them apart is one layer up, where both rules exclude an unknown *subject*.
   The test that covered it was passing for a different reason than it
   claimed, and now asserts on the span's own state instead of the outcome it
   happened to produce.

---

## 9. ⚠️ WHAT IS NOT ESTABLISHED

**Accuracy.** Not one of the 10 inferred notes has been checked against the
print. On a cleanup count they are 10 things a human might have to take back
out. The stage's guarantee is that each is **labelled**, supersedes visibly,
and chose among candidates the reader itself admitted — not that it is right.

**No export arm was run**, so *"10 inferred"* is not *"10 reached the file"*.
The first rule's own measurement had 7 inferred and 6 reaching the file, the
seventh being a cross-staff duplicate `glyph_owner` had already disowned.

**No OMR-NED figure**, deliberately: the metric is symmetric and rewards
under-prediction, so it would pay for suppression here in the direction that
makes the file worse.

**n = 1 document, 1 publisher, 4 pages**, on the *low-res bitonal* Litolff
`984073` this file already calls the pessimistic end of the corpus. The
engraved family is untouched by construction. **Breitkopf Brahms 1 is where to
re-measure**, and its shared record exists.

**The `71`** — subjects lost to the independent-witness floor — is a reach
figure and says nothing about whether those 71 would have been inferred
*correctly*.

---

## 10. THE RANKED NEXT WORK, WITH WHAT EACH IS BLOCKED ON

1. **Measure `COLUMN_MIN_INDEPENDENT_WITNESSES`.** It is the stage's one
   unmeasured constant and it is now the largest single stop in both rules'
   funnels — **71 here, 28 in the first rule's**. Measuring it needs no new
   code: the two arms are `2` and `3`, and the honest score is not *how many
   more fire* but **how many of the extra ones a human accepts**, which needs
   crops. ⚠️ **Lowering it to 1 is the one change that must not be made on a
   reach argument**: one witness is not corroboration, and the whole stage
   rests on that.

2. **An export arm, so *inferred* becomes *reached the file*.** The first
   rule's own measurement lost one of seven to a cross-staff duplicate
   `glyph_owner` had already disowned — two stages agreeing, and invisible
   without the export. `benchmarks/omr-infer-stage-2026-09/export_arm.py`
   already exists.

3. **Re-measure on Breitkopf.** Its shared record exists
   (`brahms1-breitkopf-p0-p3.record.json`, md5
   `52b98f1cdfee3b39f10e56c592828ea4`). Everything here is n = 1 document on
   the *low-res bitonal* end of the corpus; a plate whose columns read better
   would move the funnel's first two stops and a plate whose columns read
   worse would move the `UNKNOWN` count off 1.

4. ⚠️ **A meter-FORM rule is the obvious third rule and it is NOT a quick
   win.** `bars_name_a_length_without_a_form` is a genuine ABSTENTION on
   `Q.METER` and is the named blocker on Brahms `p0p3` — the bars reach length
   3.0 at +7.0 and cannot spell it, because the only system to borrow a
   spelling from is the one that misread. Widening the borrow to *any* system
   of the document is exactly sideways and exactly this stage's remit. **But a
   rule that writes `Q.METER` and reads other systems' `Q.METER` puts the
   meter in its `reads`, so `infer.scoring_conflict` fires and
   `probe/self_check.py` refuses to score it** — correctly. It would need a
   different invariant before it could be believed, and that is a design
   question rather than a rule.

5. **The `no_pitch` population stays REFUSED** on the ground the first rule's
   findings give: filling a pitch means inferring the clef, the sideways route
   is the same part on another system, and that is keyed on the PART JOIN,
   which this document is measured getting wrong on 12 of 75 staff-systems.
   Unchanged by anything here.
