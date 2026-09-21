# `part_partition`'s second declared check, performed — and it condemns the join it refused

**2026-09-20/21.** No flag. `tools/omr/staged/adjudicators/identity.py`.
The first item on the 2026-09-20 handoff's ranked list, and the first
convention this project has WIRED rather than counted.

| | |
|---|---|
| the declaration | *"each part carries ONE instrument across every system it appears on"*, in `checked_by` since the decision was written |
| what the body read | `Q.SYSTEM_STAFF_COUNT` and `Q.SLOT_INDEX`. **`Q.INSTRUMENT` on no path at all** |
| **reach** | **50 of 75** Litolff staves and **91 of 97** Breitkopf staves carry a named instrument |
| **what it says about the join that SHIPPED** | **0 contested parts** on both documents |
| **what it says about the join each document REFUSED** | **3 of 12** and **5 of 14** parts carry two instruments |
| what it CHANGES | **nothing.** Same outcome, reason and value on every path |

---

## Ask-first block

**CONVENTION.** Sean's, via the document: `[C..]` *a part carries one
instrument*. It is the decision's own declared check, not a new claim.

**NOT CONFIRMED WITH SEAN.** That a contested join should ever ACT — refuse,
fall back, or repair. It records. Every way of acting is a guess today and §4
says why.

**WHAT WOULD FALSIFY THE RESULT.** A document whose slot join is contested
and whose ordinal join is clean; or a contested part that is right, which
happens wherever a margin label was misread — the check cannot tell a bad
join from a bad label and does not claim to.

---

## 0. The fault, verified before anything was built

`benchmarks/omr-convention-coverage-2026-09/` counted **16 of 32 declared
checks not actually performed** and ranked this one first. Re-verified here
rather than inherited:

```
$ grep -c 'ev\.' <the body of adjudicate_part_partition>
   2   — ev.verdicts(Q.SYSTEM_STAFF_COUNT), ev.verdicts(Q.SLOT_INDEX)
```

`Q.INSTRUMENT` stood in `wants`, in `implicates` and in the `checked_by`
sentence, and was read nowhere. ⚠️ **That is the third documentation shape
this project has named** — not a stale claim about the past, but a claim
about the code in front of you, which a reader has no reason to doubt.

⚠️ **The damage it describes is already on this project's record.** The Phase
2 part-join measurement (`benchmarks/omr-part-join-phase2-2026-09/`) found
**12 of 75 staff-systems filed under a part carrying a different
instrument**, including a Timpani part holding the Viola's staff and its
seven sharps. Nothing in the pipeline said so; a human found it by reading
the file.

---

## 1. What shipped — a check that RECORDS

`_instrument_consistency(ev, join)`, called on **all four** return paths that
produce a join. It groups every decided `Q.INSTRUMENT` verdict by the part key
**the chosen join implies**, and writes the answer into the verdict's
`detail`.

⚠️ **THE FRAME WAS THE WHOLE DIFFICULTY, AND IT WAS NAMED BEFORE THE CHECK
EXISTED.** `Q.INSTRUMENT` is filed on **STAVES**; this decision runs at
**DOCUMENT**. `wiring.py`'s SCOPE-LATENT entry for this exact declaration said
so in terms — *"the repair needs `subject=` per staff, not a bare read"* — and
a bare `ev.verdicts(Q.INSTRUMENT)` returns nothing and reports a clean zero on
every page. The read is `Scope.SELF_AND_DESCENDANTS`, asserted at source level
by a test, **because a bare read fails SILENTLY**: it produces the same
`checked: False` an honest unlabelled page produces.

⚠️ **ABSENT IS NOT CLEAN, and here that is load-bearing twice over.** A page
where no instrument was read yields `checked: False, why_not:
"no_instrument_was_read"` and **no `parts_contested` key at all**. Before
`run_staged` forwarded `pdf_path`, `adjudicate_instrument` abstained
`no_evidence` on **75 of 75** staves on every staged run this repo had ever
made — so a check that read that silence as agreement would have reported the
part join **sound on precisely the documents where it was worst**.

⚠️ **A PART NAMED ON ONE SYSTEM IS REPORTED APART.** It cannot disagree with
itself, so counting it among the parts that agree would report reach the check
does not have. `parts_with_two_or_more_named_staves` is the denominator that
means anything.

⚠️ **AND THE CHECK IS ASKED IN THE JOIN'S OWN TERMS.** The `slots_are_ordinals`
branch is checked as an **ORDINAL** join, because that branch has just decided
the slot table amounts to the ordinal; asking it in slot terms would check a
partition that does not ship.

---

## 2. Reach, before any result

Two shared staged records, two publishers. Reach is the first number because
a clean zero at zero reach is the failure mode this check was written against.

| | Litolff Beethoven 5 p1-p4 | Breitkopf Brahms 1 p0-p3 |
|---|--:|--:|
| staff-systems on the page | 75 | 97 |
| **staves carrying a named instrument** | **50** | **91** |
| slots decided | 50 | 97 |
| parts under the shipped join | 12 | 14 |
| **parts named on ≥2 systems** — the only ones that CAN disagree | **7** | **14** |
| staves belonging to no part under the join | 0 | 0 |

So the check speaks about **7 of 12** parts on one document and **14 of 14**
on the other. On Litolff five parts are named on one system only and the check
is structurally silent about them — **that is a limit, not a pass.**

---

## 3. The result — and the counterfactual is the interesting half

| | Litolff | Breitkopf |
|---|--:|--:|
| **the join that SHIPPED (slot): parts contested** | **0** | **0** |
| the join each document REFUSED (ordinal): parts contested | **3 of 12** | **5 of 14** |

The contested parts under the ordinal join, named:

| | Litolff | Breitkopf |
|---|---|---|
| | part 1 · Oboe ×6, **Clarinet ×1** | part 7 · Trumpet ×6, **Timpani ×1** |
| | part 2 · Clarinet ×6, **Bassoon ×1** | part 8 · Timpani ×6, **Violin ×1** |
| | part 3 · Bassoon ×6, **Horn ×1** | part 10 · Violin ×6, **Viola ×1** |
| | | part 11 · Viola ×6, **Cello ×1** |
| | | part 12 · Cello ×6, **Contrabass ×1** |

⚠️⚠️ **EVERY ONE OF THE EIGHT IS THE SAME SHAPE, AND THE SHAPE IS THE
SIGNATURE OF INTERIOR SUPPRESSION: six systems agree and exactly one
dissents, and the dissenter is always the NEXT instrument down.** That is what
a suppressed interior staff does — everything below it shifts up by one — and
it is the Phase 2 finding arriving from a third direction, after the measure
math and the key signatures.

⚠️ **IT IS NOT THE PHASE 2 NUMBER AND MUST NOT BE QUOTED AS ONE.** That
measurement is **12 of 75 staff-systems against hand-read PRINT truth**. This
is **3 and 5 contested PARTS** against our own instrument readings, over the
50 and 91 staves we managed to name. Same fault, different denominators, and
this one is a LOWER BOUND: where the dissenting staff was never named, the
check sees nothing.

⚠️ **THE SHIPPED JOIN'S ZERO IS EVIDENCE AND IT IS NOT PROOF.** It is a
constraint satisfied, on the parts the check can speak about, and the same
sentence this decision's own docstring already carries applies:
`beethoven-sym5-mvt1-984073-p4` prints 11 staves in BOTH systems with
DIFFERENT lineups, and **an equal-count check is a constraint satisfiable by
accident.** A slot table can be wrong and consistent.

⚠️ **AND THE CHECK IS ONE-SIDED ABOUT CAUSE.** A contested part means the join
and the labels disagree. It does **not** say which is wrong: a single misread
margin label produces exactly the same row as a grafted staff.

---

## 4. Why it records and does not act

The wiring plan's one condition is that **a wiring pass may CONNECT a
decision, it may not let one GUESS.** Both ways of acting are guesses today:

* **Refusing the join over a contradiction** hands the document to the
  fragment fallback — 12 parts → 75 fragments on Litolff, which this project
  has already measured and taken deliberately once — on the evidence of what
  may be one misread label.
* **Repairing the join** needs to know WHICH staff is misfiled. The check
  cannot say. Six-against-one looks decisive and is a majority vote, which is
  INFER-stage work and is exactly what EVALUATE goes silent for.

So the result goes into the verdict, where the next reader and the next
measurement can both see it, and the value does not move. That is asserted,
not promised: `test_the_check_changes_NOTHING_about_the_join` runs two
documents identical but for the instruments — one clean, one contested — and
requires the same outcome, reason and value, with the contested count as its
positive control.

⚠️ **`used` is NOT extended with these ids.** The join was not decided from
them. They arrive in `considered`, because `ev.verdicts` records every hand-in
— the honest place for the basis of a check that changed no value.

---

## 5. Controls

**THE JOIN IS UNMOVED.** `check_arm.py --control` re-adjudicates each shared
record through the SHIPPED decision and requires the same outcome, reason and
value the record itself carries. ⚠️ **With a POSITIVE control beside it**: the
`instrument_consistency` detail must be PRESENT, because *"nothing moved"* is
also exactly what a check that never ran looks like.

**TWO INSTRUMENTS, TWO ROUTES.** `probe_records.py` asks the same question
with **no pipeline code at all** — it reads the record's JSON, re-derives the
part keys from the subject strings and the slot verdicts by hand, and never
builds a `Log`, an `Evidence` or a scope. Both routes give the same 3 and 5.
Had only the shipped check been run, it would have been agreeing with itself.

⚠️ The probe also asks **both** joins on every document, which the shipped
check cannot and should not: the decision checks the join it CHOSE. The
counterfactual column in §3 is therefore a property of the probe, and it is
where the whole result lives.

**THE DERIVED CHECKS CAUGHT THE CLOSURE THEMSELVES.** Wiring this turned
`test_staged_inventory` and `test_staged_wiring` RED, each naming exactly one
stale entry — `part_partition declares 'instrument'` — and **not** its sibling
`Q.STAFF_ORDINAL`, which is still genuinely inert. **Two derived tools written
by different sessions independently noticed that a gap had closed**, which is
what those lists are for and is stronger corroboration than either alone. Both
entries were removed; the `Q.STAFF_ORDINAL` entry was repointed, since it
cited the one that left.

**MUTATION BATTERY: 13 arms — and its FIRST THREE RUNS ARE THE FINDING.**
See §5a.

### 5a. ⚠️⚠️ THE BATTERY WAS MEASURING NOTHING, AND FIXING IT FOUND FOUR REAL GAPS

`headline()` compared pytest's summary line **verbatim**, and that line ends
`" in 0.57s"` — pytest's own elapsed time, which **differs between two runs of
an UNMUTATED tree**. So `out != b_out` was true for every arm and **every arm
scored RED for free.** Measured, two baseline runs back to back:

```
run A: (0, '13 passed, 5 warnings in 0.57s')
run B: (0, '13 passed, 5 warnings in 0.61s')
IDENTICAL: False
```

**A battery whose judge cannot say two identical trees are identical is not a
battery**, and it is the *control that computes the wrong thing* family
failing in the direction that looks like success: the first run reported
**13 of 13 RED, 0 survivors** and would have shipped as a clean result.

| run | judge | result |
|---|---|---|
| 1 | summary verbatim | **13 RED, 0 survivors** — VOID |
| 2 | duration stripped | **10 RED, 3 SURVIVORS** |
| 3 | after closing those three | **12 RED, 1 SURVIVOR** |
| 4 | after closing that one | see the committed output |

**All four survivors were real, and three were the same shape** — a test that
reaches everything about a mechanism except the branch the mutation lives in:

1. **A contested SLOT join abstaining.** `test_the_check_changes_NOTHING_
   about_the_join` builds two systems of EQUAL staff count, so it takes the
   ORDINAL branch and never reaches the slot branch at all. *A test named for
   a hazard it does not reach*, with the name exactly right and the fixture
   two staves short of the branch.
2. **and 3. Both of the ARM's own controls.** A benchmark arm is a script; no
   suite imports it, so an arm against it is free unless something drives it.
   Closed by tests that run `check_arm.main()` over a synthetic record.
4. ⚠️⚠️ **The arm's POSITIVE control, which is the hazard one layer out.**
   Deleting *"the detail must be PRESENT"* left `rc == 0` and `"DID run"` both
   true on a faithful record — because **"nothing moved" is exactly what a
   check that never ran looks like**, which is the reason the arm has that
   control. A test suite that cannot tell those apart has the same blind spot
   the arm was built to close. Closed by stripping the detail after
   adjudication and requiring the control to FAIL.

⚠️⚠️ **THE SAME JUDGE IS IN
`benchmarks/omr-stem-notehead-gate-2026-09/mutate.py`, WHICH THIS ONE WAS
COPIED FROM — so that lane's published "21 arms, 21 RED, 0 survivors" IS VOID
AS PUBLISHED.** Both are fixed. **Only 2 of the repo's 30 batteries carry the
shape**, both written on 2026-09-20, so it is a regression and not historic.

### 5b. ⚠️ AND A COMMIT CAPTURED A LIVE MUTATION

`git add -A` over this benchmark directory ran while this lane's OWN battery
was mid-arm, and committed `if False:` in place of the arm's join comparison.
The battery restored the file correctly (md5 verified) and **the working tree
was right the whole time; HEAD was not** — caught by the NEXT battery's
dirty-target refusal, not by review. CLAUDE.md already says *"NEVER `git add
-A` anywhere another agent may be working"*; the clause this adds is that **a
mutation battery is such an agent, and it is one you started yourself** — so
the window is not *another session is running*, it is *anything at all is
running*.

---

## 6. WHAT IS NOT ESTABLISHED

* **ACCURACY. No print was consulted.** Every statement here is agreement or
  disagreement between two of our OWN readings — the join and the instrument
  labels. Where they disagree the check cannot say which is wrong, and where
  they agree both can still be wrong about the same staff.
* **The shipped join's 0 is not a clearance.** §3's last two warnings.
* **n = 2 documents, 2 publishers, 8 pages, both SCANS.** The engraved family
  is untouched.
* **No export, no file, no OMR-NED figure.** Nothing about a note changed:
  this is a check whose entire output is a dictionary in a verdict. The metric
  is symmetric and would have nothing to say about it in any case.
* **Nothing CONSUMES the result yet, deliberately** — the `Q.INK` /
  `OMR_FAMILY_POSITIONS` discipline. A consumer landing in the same change
  would move the numbers used to decide whether the check is worth having.
* **The 25 Litolff staves that were never named** are outside the check's
  reach entirely, and they are the half of the page most likely to be
  misjoined: this edition stops labelling its strings on continuation systems,
  which this project has already measured as structurally unavailable
  (*29 of 29 unresolved non-treble staves print no label at all*).

---

## 7. Running it

```bash
B=benchmarks/omr-part-instrument-check-2026-09
R=library/_shared-records

python3 $B/check_arm.py $R/beethoven5-p1-p4-ink-identity.record.json --control
python3 $B/check_arm.py $R/brahms1-breitkopf-p0-p3.record.json --control
python3 $B/check_arm.py $R/beethoven5-p1-p4-ink-identity.record.json \
        --tag litolff-beethoven5-p1-p4
python3 $B/probe_records.py $R/*.record.json     # the second route
python3 $B/mutate.py
python3 -m pytest tools/omr/tests/test_part_instrument_check.py
```

⚠️ `check_arm.py` re-adjudicates a whole record and takes **many minutes** per
document. `probe_records.py` answers the same question in under a second and
is the one to reach for first; the arm is what proves the SHIPPED code says it.
