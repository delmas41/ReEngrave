# INFER has a second rule — and the stage's own self-check was circular

**2026-09-17.** Build, not measurement — Sean's instruction was *"I want
progress in the build not just more measurements. particularly in the infer
stage."* Merged as [PR #50](https://github.com/delmas41/ReEngrave/pull/50),
`7bf90c58` on main. Findings:
[benchmarks/omr-infer-barline-2026-09/FINDINGS.md](../benchmarks/omr-infer-barline-2026-09/FINDINGS.md).

⚠️ This is a **different thread** from the meter chain the three handoffs above
it record. It touches no meter flag and no meter decision. Read it beside them,
not after them.

⚠️⚠️ **ADDED 2026-09-18, AND IT CHANGES NOTHING THIS HANDOFF MEASURED — IT IS
THE STANDING RULE FOR WHOEVER PICKS THIS UP.** CLAUDE.md names this file as
*START HERE*, so the pointer lives here: **before building anything, say how a
HUMAN would read it off the page and what ENGRAVING CONVENTION governs it, and
ask Sean in one line** —
[docs/ask-first-conventions.md](ask-first-conventions.md). Sean, 2026-09-18:
*"Many times I feel like the agent is building in a counter-intuitive way, or
blind to obvious conventions."* ⚠️ Nobody to ask (a cloud session, an overnight
run) → write **CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED WITH
SEAN** at the top of the brief and proceed. ⚠️ It is a hypothesis and a cheap
test, never a licence: §3 there records the conventions this repo has
**refuted**, including one of Sean's own.

---

## 1. WHAT LANDED

`collapse_duration_to_barline` — INFER's second rule, no flag,
`tools/omr/staged/inferences.py`. `OMR_INFER` is still default OFF and off
still means ABSENT.

The first rule's funnel declined **191 of 357** narrowed durations at one
condition, with a comment saying why:

> No next onset in this bar, so this note runs to the BARLINE and its length
> is the bar's — which is the meter, which this rule may not read.

**Right about the METER, wrong about the NEIGHBOUR.** A staff standing at the
same onset column with nothing after it has already measured the same gap. The
barline is a system-wide event, so both notes end at the same instant.

| | Litolff | Breitkopf |
|---|--:|--:|
| rule 1, by column | 7 | 25 |
| **rule 2, to barline** | **10** | **16** |
| **INFER total** | **17** | **41** |

Controls first on both: 16,773 of 16,773 verdicts reproduced exactly on
Litolff, and the Breitkopf record's provenance is **clean** where Litolff's is
stamped dirty.

---

## 2. ⚠️⚠️ THE GUARD IS WHAT MAKES IT A RULE AND NOT A SHORTCUT

`Q.METER` stays out of `reads`, and for this rule that had to be **earned**.
`size_measure_rest` and `reconcile_duration` both hand a duration out FROM the
meter and **both put the meter row in their `basis`**. Borrowing such a length
would read the meter by proxy: the value meter-derived while `reads`
truthfully said it was not, `infer.scoring_conflict` reporting clean, and
`probe/bar_fill.py` quietly ceasing to be an independent check.

So a witness whose provenance closure contains `Q.METER` is refused, via
`Log.quantities_in_closure` — **the primitive `adjudicate.py` already uses for
circularity**, not a new mechanism. It fires on **3 subjects on Litolff and 14
on Breitkopf**, so it is not theoretical.

⚠️ **The endpoint is a PAIR and the third state is the point.** Deriving *runs
to the barline* from *no later COLUMNED event* would call a note barline-bound
whenever the event after it missed every column centre, then hand it a
neighbour's whole-bar length. `(m, False)` ends at a column; `(None, True)` is
the barline; `(None, False)` is UNKNOWN and **both rules decline it**. Worth 1
note on Litolff and 0 on Breitkopf — a correctness guard whose value is that it
cannot be wrong, not a reach mechanism, and two documents is not enough to call
it rare.

⚠️ **Rule 1 is behaviourally UNCHANGED.** `follow` non-None implies later
events exist, so the pair comparison is equivalent to the old column one there.

---

## 3. ⚠️⚠️ THE CLAIM TRANSFERS AND THE REFUSALS DO NOT — AND THAT IS THE
##    MOST USEFUL THING HERE

| stop | Litolff | Breitkopf |
|---|--:|--:|
| no other staff runs k → barline | 56 | 17 |
| no witness with a DECIDED, non-meter length | 37 | 20 |
| **the witnesses DISAGREE** | **15** | **96** |
| fewer than 2 INDEPENDENT witnesses | 71 | 70 |
| 0 candidates carry that length | 1 | 20 |

On Litolff the dominant refusal is **availability**; on Breitkopf it is
**disagreement**, six times the count. Corroborated from outside this work:
CLAUDE.md already records Breitkopf reading **22%** of per-staff durations
right against Litolff's **59%**.

**The worse-read plate makes the unanimity requirement go QUIET rather than go
WRONG** — which is exactly what *one dissenter refuses the whole inference* was
written to do, now observed rather than asserted. That is the strongest
evidence this thread has that the stage's refusals are load-bearing.

---

## 4. THE STAGE'S ONE UNMEASURED CONSTANT IS NOW PRICED

`COLUMN_MIN_INDEPENDENT_WITNESSES` was the largest stop in both funnels.
`probe/witness_floor.py` prices it in **reach** — the half a machine can
answer — and **reproduces all four shipped totals independently**, its Litolff
`by_column` population being exactly the **n = 35 unanimous** the first rule
published. It measures the rule, not itself.

Independent-group counts over the cases that reach the floor:

| | n | 1 | 2 | 3 | 4 | 5 |
|---|--:|--:|--:|--:|--:|--:|
| Litolff, by column | 35 | **28** | 3 | 4 | | |
| Litolff, to barline | 82 | **71** | 8 | 3 | | |
| Breitkopf, by column | 82 | **49** | 28 | 2 | 3 | |
| Breitkopf, to barline | 106 | **70** | 18 | 5 | 5 | 8 |

⚠️⚠️ **THE MASS IS AT EXACTLY ONE, ON BOTH DOCUMENTS AND BOTH RULES.** The
refused population is overwhelmingly single-witness, so the floor at 2 **sits
on a boundary, not a midpoint**: it separates *one staff said so* from *two
independent staves agree*. **That is the justification the constant never
had** — it was set at 2 on an argument, with its docstring admitting the number
was unmeasured.

⚠️ **Floor 3 is expensive AND erratic** (−70%, −88%, −38% across the three
rule/document pairs). ⚠️⚠️ **Floor 1 is printed and NOT proposed**: it
abolishes corroboration, which is the one thing the stage rests on not doing.

---

## 5. ⚠️⚠️ A LIVE DEFECT, FOUND ON THE WAY PAST AND REPAIRED

**The INFER stage's only truth-free self-check has been silently circular since
the 2026-09-15 default flip.** `probe/self_check.py`'s condition 2 is stated in
its own docstring — *"`OMR_METER_FROM_BARS` MUST BE OFF … Off by default;
asserted here rather than assumed"* — and it was neither. It read

```python
os.environ.get("OMR_METER_FROM_BARS", "0")      # allow-list: default OFF
```

while the owning predicate (`staged/adjudicators/rhythm.py:1144`) is `"1"`
against a **deny-list** — default ON. With the variable unset, which is the
default and what every run in this thread has had, the pipeline had the flag
**ON** and the check printed `'0' -> ok`.

**That is the guard failing in precisely the manner it was written to
prevent**, and it is three of this repository's recorded patterns at once: the
flag-direction hazard, *a fallback must never convert "cannot tell" into a
definite answer*, and a constant restated instead of imported.

**Repaired** by importing `rhythm.meter_from_bars_enabled()`. ⚠️ **The
consequence is that the self-check now correctly REFUSES under current
defaults.** That is the honest state, not a regression introduced here — and it
is a live open item for whoever wants a score out of that probe.

---

## 6. THE TESTS, AND WHAT THE BATTERY FOUND

⚠️⚠️ **THE REGISTERED RULES HAD NO UNIT FIXTURE AT ALL.**
`test_infer_stage.py` asserts the HARNESS's five disciplines using one-off
rules installed per test — right for what it covers, and it means **either real
rule could have stopped firing entirely with the suite green**. The only thing
exercising them was a benchmark arm over a 132 MB record needing `library/`.
`test_infer_barline_rule.py` builds the smallest system the rules can actually
walk and asserts both. INFER suite **68 green**.

**Battery: 14 arms, 14 red, restore verified by hash**, positive control red.
It carries an **in-flight sentinel** and **refuses a dirty `tools/` tree**,
both from the record of a battery killed mid-arm leaving its mutation
indistinguishable from a real edit.

⚠️ **Its first run reported 2 survivors and they were one of each recorded
kind** — a MIS-AIMED ARM (aimed at a fixture where a different guard fired
first) and a REAL TEST GAP (comparing the endpoint on the column half alone
survives every existing fixture; the discriminating case is a witness whose
endpoint is UNKNOWN, which shares the `None` column with a barline-bound
subject). Both closed.

---

## 7. ⚠️ TWO FAULTS OF MY OWN, RECORDED RATHER THAN SMOOTHED OVER

1. **A detail field where a lone `0` was ambiguous.**
   `witnesses_refused_meter_derived: 0` reads identically for *checked and
   refused nobody* and *does not check* — and rule 1 does not check. A flag now
   travels beside the count. Same lesson as
   `empty_bars_padded_without_meter`.
2. **A comment claiming a guard that lives elsewhere.** The witness comparison
   said it excluded the unknown-endpoint case. It does not — two unknowns
   compare **equal**. The real exclusion is one layer up, and the test covering
   it was passing for a different reason than it claimed. It now asserts on the
   span's own state.

---

## 8. ⚠️ WHAT IS NOT ESTABLISHED, AND THE RANKED NEXT WORK

**Accuracy.** Not one of the 17 or 41 inferred notes has been checked against a
print. On a cleanup count they are things a human might have to take back out.
The guarantee is that each is LABELLED, supersedes visibly, and chose among
candidates the reader itself admitted — not that it is right.

**No export arm ran**, so *inferred* is not *reached the file*. The first
rule's own measurement lost one of seven to a cross-staff duplicate
`glyph_owner` had already disowned.

**No OMR-NED**, deliberately — the metric is symmetric and rewards
under-prediction.

**The ranked next work**, with what each is blocked on, is
[FINDINGS §10](../benchmarks/omr-infer-barline-2026-09/FINDINGS.md):

1. **Crops for the witness floor.** The reach half is now measured; whether the
   extra inferences at a lower floor are RIGHT is not, and only crops answer it.
2. **An export arm**, so *inferred* becomes *reached the file*.
   `benchmarks/omr-infer-stage-2026-09/export_arm.py` already exists.
3. **A third publisher.** Everything here is n = 2.
4. ⚠️ **A meter-FORM rule is the obvious third rule and is NOT a quick win** —
   `bars_name_a_length_without_a_form` is a real abstention and the named
   blocker on Brahms `p0p3`, but a rule writing `Q.METER` and reading other
   systems' `Q.METER` puts the meter in its `reads`, so `scoring_conflict`
   fires and `self_check` refuses to score it. It needs a different invariant
   first — a design question, not a rule.
5. **The `no_pitch` population stays REFUSED** on the first rule's ground: it
   means inferring the clef, keyed on the part join, measured wrong on 12 of 75
   staff-systems.

---

## 9. ⚠️ ONE OPEN ITEM ON THE SUITE, REPORTED RATHER THAN OMITTED

The full suite reports **9 failures and 8 are PROVEN PRE-EXISTING** — all in
`test_surya_worker_session.py`, which fails **8 on this work and 8 on
`origin/main`** run standalone on both trees. This work touches no Surya file.

**The 9th appears only in a full run, not standalone, and was not isolated
before landing.** It is named here so the next person does not rediscover it as
new. The blast radius argues against it being this change — the diff is INFER,
one test file, benchmarks and docs — but that is an argument, not a
measurement.
