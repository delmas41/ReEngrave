# INFER — the fourth stage: built, bypassable, and in line to test itself

2026-09-15. `tools/omr/staged/infer.py` + `inferences.py`, behind `OMR_INFER`,
**default OFF**. Phase 4 of
[docs/plan-2026-09-10-wire-first-then-reconcile.md](../../docs/plan-2026-09-10-wire-first-then-reconcile.md).

---

## 0. ⚠️⚠️ THE PHASING OVERRIDE, RECORDED BECAUSE IT IS A DECISION

The plan says this stage **"may not be built before the first cleanup count"**
(§5d, and again in §6 Phase 4). **Sean overrode that on 2026-09-15:** *"I think
our best advances will come from building out the 4th stage and making sure
all our info gets to where it needs to."* He also asked for more effort on
**builds** than on long test runs.

The plan's reasoning was that *the count is what says which abstentions are
worth resolving by inference*. That reasoning is **satisfied rather than
ignored**: Phase 2 IS open. Sean read one page against the print and produced
seven observations, five of which are answered — and the unwritten notes
(`duration_narrowed` 339, `no_pitch` 215 on the cleanup artefact) are exactly
this stage's population. The evidence that ranks the work exists in the form
the plan wanted; what does not exist is a NUMBER, which the plan also says
must never exist.

⚠️ **One redirect of the coordinator's, recorded so it can be overturned with
evidence.** The plan names *"calibration from the score library"* as the first
piece of this stage. It was **deliberately not built**: it is a corpus run,
which is the shape Sean asked us to spend less on, and `record.Candidate`'s
own docstring says relative support, ORDERED, has been enough for every
consumer written so far — while a calibrated probability is the one thing this
repo has measured FAILING (ECE 0.1277, worst at the top of the range).
**The first rule needs no probability at all.**

---

## 1. WHAT WAS BUILT

| file | what it is |
|---|---|
| `tools/omr/staged/infer.py` | the stage: registry, `run(log, evaluated)`, `Report`, five guards |
| `tools/omr/staged/inferences.py` | the rules. One: `collapse_duration_by_column` |
| `tools/omr/tests/test_infer_stage.py` | the five guards, each asserted |
| `tools/omr/tests/test_infer_bypass.py` | off is ABSENT, not quiet |
| `reinfer.py` | run INFER ALONE over a saved post-EVALUATE record, with `--control` |
| `export_arm.py` | one record to MusicXML, stamping the EXPORTING tree |
| `probe/reach.py` | what is there to infer about, **before** the rule exists |
| `probe/byte_control.py` | the structural control + the accounting identity |
| `probe/self_check.py` | scores by an invariant the rule did NOT read, or refuses |
| `mutate.py` | the mutation battery |

### 1a. The five rules, each in the harness rather than in a docstring

1. **It may not run before EVALUATE.** `run()` *requires* EVALUATE's report as
   an argument, so a caller that has not run EVALUATE has nothing to pass.
2. **It may not loosen GATHER or ADJUDICATE.** It refuses an unfrozen log. The
   whole design rests on the earlier stages still refusing to guess, so that
   this stage can tell *"nobody could read this"* from *"this was read and it
   is wrong"*.
3. **It may only speak where the record has no answer.** `INFERABLE` is
   `{NARROWED, ABSTAINED}`; `DECIDED` is absent and must stay absent. An
   inference that can overturn a READING makes a cleanup count unable to
   separate a reading fault from an inference fault.
4. **It may not invent a value.** Collapsing a narrowing, the proposed value
   must be one of *that reader's own* candidates, else `ValueNotAdmitted`.
   The reader's refusal bounds the inference.
5. **It supersedes VISIBLY.** A rule returns a `Proposal` — a dataclass with
   **no `decider` and no `outcome` field** — and the harness builds the
   verdict, stamps `decider="infer:..."` and `detail["inferred"]=True`, and
   points `supersedes` at the prior. The log is append-only, so the narrowing
   stays in the record with its candidates and their support.

⚠️ **The exporter's refusal to argmax is UNTOUCHED.** `export.py` still writes
nothing for a narrowed verdict. INFER is the stage allowed to collapse one,
and the exporter then writes it because it is DECIDED — not because the
exporter started guessing.

### 1b. The two hazards, addressed rather than described

**(a) An uncalibrated number must not be laundered into evidence.** Nothing in
the module ranks candidates by `support`. `Rule.forbids_argmax` is asserted
for every rule; `support` is REPORTED beside an answer
(`chosen_candidate_support`, `was_readers_top_candidate`) as a diagnostic and
is never the reason for one.

**(b) Two readers can fall silent together.** *"Why are they N witnesses and
not one"* is a **computation**: `independent_groups()` partitions the witness
verdicts by whether their `Log.closure` provenance sets INTERSECT, so two
witnesses resting on a shared row count once. The partition is written to the
verdict's **`correlated`** field — built for exactly this and until now
consumed by nothing.

⚠️ **It is ONE-SIDED and the module says so at the function.** Disjoint
closures prove the ROWS differ; they do **not** prove the readings fail
independently. Two staves of one badly-printed page share no row and still
degrade together — the convention/ink correlation CLAUDE.md records as
measured but unquantified. So it rules out the correlation the record can see
and is silent about the one it cannot.

### 1c. The rule, and why it is the one that belongs here

`collapse_duration_by_column`, scope SYSTEM, reads `Q.ONSET_COLUMN`,
`Q.EVENT`, `Q.DURATION`, `Q.GLYPH_BOX`.

> An onset column is an instant. If this staff's event stands at column k and
> its own next event stands at column k+1, this note sounds for exactly the
> gap between those two instants. If a NEIGHBOURING staff also goes k to k+1
> and its note there is DECIDED at d, then the gap IS d — so this note is d.

⚠️⚠️ **This is the thing EVALUATE structurally cannot do.** Every consequence
is `cause -> effect`, vertical; a bar sitting in a system with eleven other
staves playing the same stretch of time has eleven readings of it that no
consequence may look at. Sean's efficiency argument — *"we don't need much
info from a particular symbol because we have what we need elsewhere"* — is
entirely horizontal, and until this rule there was nowhere for it to live.
`Q.ONSET_COLUMN` measured that redundancy (1,483 real instants against a
phase-shuffled null's 2,409) and **its own findings named a first consumer
that was never built.** This is it.

⚠️ **It is not entailment, which is why it is here and not in EVALUATE.**
Three ways it can be wrong, all real: the note may be followed by a rest the
detector never read, so its own next EVENT is not its end; the column grouping
may have merged two instants; and a tie or held note can cross a column
without a new onset. Each makes the answer BEST rather than FORCED — and each
is why the verdict is labelled.

⚠️ **It never reads the meter or a bar sum**, which is what leaves
`bar_fill.py` a legitimate independent self-check. See §5b.

---

## 2. BYPASS — provable, and what was actually run

**Off means ABSENT, not quiet.** `pipeline.run_staged_on` omits the
`inference` key entirely when the stage did not run (the same
`**({} if ... else {...})` shape the divergence table already uses). Writing
`"inference": None` would change the serialised record for a stage that never
ran — and that is the hazard: **the stage perturbing upstream by EXISTING
rather than by running.**

`test_infer_bypass.py` asserts, each able to fail (the mutation arms in §6
were run against these):

* no `inference` key, and the top-level key set is exactly what it was;
* no verdict is labelled inferred, and nothing supersedes a narrowing;
* **two flag-off runs are byte-identical** — the control — and **turning the
  flag ON makes that same comparison report a difference**, which is the
  positive control that the comparison has teeth;
* `Verdict.__dataclass_fields__` and `Verdict.to_json()`'s key set are
  unchanged (the "a field was added" shape, asserted directly);
* `record.py` imports nothing named `infer` — checked on IMPORT LINES, not as
  a substring, because that file's prose uses the word and a check that fails
  for the wrong reason teaches the next reader to delete it;
* importing `infer` registers **no** rule (the import-side-effect shape: the
  rules load lazily inside `_ensure_rules`);
* `infer.run` is never entered with the flag off, and IS entered with it on.

### 2a. The instruments, run rather than reasoned about

| | result |
|---|---|
| `inventory --check` | **exit 0** |
| `health --check` | **exit 0** |
| `gather_coverage` | **exit 0** |
| `export_coverage --all` | **exit 0**, and it reported *"no fixtures on disk"* — it exercised the code path and **not** the comparison, because the engraved fixtures are build products and gitignored in a worktree. Stated rather than counted as a pass. |
| `test_flag_default_direction.py` | 3 passed — **after a repair, see §5a** |
| full suite | §6a |
| `readjudicate.py`, `reexport_arm.py` | **reasoned about, NOT run** — see below |

⚠️ **The two arms were not run and the reason is structural rather than
convenience.** `readjudicate.py` rebuilds a `Log` from a saved record's GATHER
rows and re-runs ADJUDICATE + EVALUATE; INFER is not in that path at all, and
the module is never imported by it. `reexport_arm.py` re-exports a stored
`.omr.json`, which is the LEGACY transcribe path with no staged record in it.
So the claim that they are unaffected rests on the bypass tests above plus
one grep: neither imports `infer`, and `pipeline`'s call site is the only one.
**That is weaker than running them and is labelled as such.**

---

## 4. ⚠️ WHAT WAS REFUSED, AND WHY

* **Calibration from the score library** — §0. A corpus run, and the one thing
  this repo has measured failing.
* **Argmax on `support`** — hazard (a). It is one line and it would be the
  whole of the failure this stage exists to avoid.
* **Inferring a PITCH for the `no_pitch` population.** A note has no pitch
  because its staff's CLEF abstained, so filling one means inferring the clef —
  and the obvious sideways route is *the same part's staff on another system*,
  which is keyed on the PART JOIN. **The part join is exactly what was just
  measured wrong on this document**: 12 of 75 staff-systems carry a different
  instrument from the part they are filed under, and `P7`, the Timpani, holds
  the VIOLA's staff on p3/s1. Carrying a clef across that join is
  `StaffCandidate.can_carry`'s own recorded hazard, and the key-signature
  session declined to build a cross-system vote for precisely this reason.
  **Refused on the same ground, one quantity over.**
* **Majority voting among witnesses.** One dissenter refuses the whole
  inference. A majority would be a tie-break on an uncalibrated count, and the
  disagreement is the more useful fact — it says those staves did not read the
  same bar.
* **Choosing between two candidates of the same length.** Refused, which is
  `reconcile_duration`'s own uniqueness rule arriving one stage later.
* **A bar-sum rule.** Two reasons, the second decisive: a bar-sum arbiter falls
  silent exactly where the reading is worst; and a rule that READ the bar sum
  would make `bar_fill.py` — the only self-check this stage has that needs no
  truth file — a measurement of the quantity the rule optimises. §5b.
* **Touching the exporter's refusal to argmax.** §1a.

---

## 5. WHAT THE BUILD FOUND ON ITS WAY

### 5a. ⚠️⚠️ The derived flag check had the drift it exists to prevent — again

`OMR_INFER` is default-OFF and written as an allow-list, which is correct —
and **`test_flag_default_direction.py` could not see it.** That scan resolves
a module constant on the LEFT (the flag NAME, `METER_SEGMENTS_ENV`, a hole its
own docstring records being fixed) and **not on the RIGHT**, so
`... in _ON_WORDS` was silently skipped by the very check written to catch
that class of mistake.

Widened to resolve a tuple/list/set-of-strings constant too, and `OMR_INFER`
added to the positive control's named-flag list. ⚠️ **The widening surfaced
exactly ONE new flag (20 to 21), mine** — so no other flag in the tree was
hidden by this hole, and the repair is for the next one. *An anti-drift check
is itself an artefact that drifts*, which CLAUDE.md already records of
`gather_coverage`'s guard; this is the second instance, in the mirror
position.

### 5b. The self-check has a SECOND independence condition nobody would check

`probe/self_check.py` refuses to print a score unless the invariant is
independent of the rule. Condition 1 is mechanical:
`infer.scoring_conflict(rule, (Q.METER,))` must be empty, and the column rule
reads `onset_column`, `event`, `duration`, `glyph_box` — no meter.

⚠️ **Condition 2 is the subtle one: `OMR_METER_FROM_BARS` must be OFF.** That
flag lets a system's own BAR SUMS name its meter, and `bar_fill` compares a
bar's sum against the `<time>` in the same file. With it on, the denominator
is derived from the very quantity the rule moves, and **the test becomes
circular through a flag nobody would think to check.** It is off by default;
the probe asserts it rather than assuming it, and REFUSES (exit 2) rather than
printing a number with a caveat — a caveat beside a number is read as a
number. Verified in both directions: it prints `ok` by default and
`REFUSED: the meter would be derived from the bar sums this rule moves` under
`OMR_METER_FROM_BARS=1`.

⚠️ **And the self-check is a REPORT and an alarm, never an objective.**
`bar_fill --check` deliberately fails only when the instrument assessed
NOTHING, never on a threshold, because a bar-fill number used as a gate is
gamed by emitting FEWER symbols — an inference stage optimising it would learn
to SUPPRESS, which is the trap OMR-NED's symmetry set from the other
direction. Nothing in `tools/` reads it.

### 5c. ⚠️ A third fact about the same import order: the provenance stamp reports neither

`staged/__main__.py` calls `_provenance()` **after** `run_staged` returns, so
it names the tree at the END of the run — while every module executed was
imported at process start and keeps that code. The two recorded facts are
*"an edit mid-run reaches the exporter"* and *"an edit mid-run does not reach
an imported module"*; this is a third: **the stamp reports neither.**

Evidence that this gather ran on a clean `ce7b8ba7`, in order: the working
tree was clean immediately before launch; the run started at
`2026-09-16T03:19:07Z`; every commit on `claude/infer-stage` is dated after
it. Recorded in `out/GATHER_PROVENANCE.md`.

It does not affect any A/B here — both arms come from THIS ONE record, so the
gather tree cancels exactly. It would matter to anyone comparing this record
with another.

### 5d. The obvious byte control is wrong for this family

*"Strip the elements and compare the rest"* fits a change that ADDS a kind of
element (`<slur>`, `<wedge>`). INFER collapses a narrowed duration, and **a
narrowed note was not written at all**, so the arms differ by whole `<note>`
elements and every offset after them in the bar. There is nothing to strip.

The control is structural instead: parts and measures identical, **ON contains
OFF** per bar in order, plus an accounting **IDENTITY** —

    notes(ON) - notes(OFF)  ==  d(duration_narrowed) - d(no_pitch)

an equality and never a `<=`, because a `<=` is what let TEN decided hairpins
be accounted for nowhere while the balance reported `True`. The arc-export
session learned the general form the expensive way (*rather than widen the
strip until it passed*); this is that move for this family.

### 5e. A recorded gap closed in passing

`export_arm.py` stamps the **exporting** tree into the coverage JSON, commit
and dirtiness together or neither. The dedupe session recorded that *"the
record names the tree that GATHERED it and nothing names the tree that
EXPORTED it, hours later in a separate process"*, which is why that artefact's
numbers could not be reproduced.

### 5f. Three of my own test faults, caught by running them

The first run of `test_infer_bypass.py` was **3 red of 45**, and all three
were the TEST's fault, not the code's: two field lists sorted `declined`
before `decider` (they sort the other way), and the `record.py` import check
was a substring test that matched the word *"infer"* inside that file's own
prose. Repaired in the test. ⚠️ The third is worth the line: **a check that
fails for the wrong reason is worse than no check**, because the next reader
deletes it.

### 5g. ⚠️⚠️ `Verdict.single_pass_revision` IS NEVER SERIALISED, SO NO RECORD CAN BE REPLAYED

Found by `reinfer --control` failing on its first run against the real record,
with `UphillConsequence` on a verdict **the original run had accepted**.

`record.py` SETS that field (`:835`) and the fixpoint guard READS it
(`:1026`), and `Verdict.to_json` does not carry it. It is the ONE exemption
from the guard — the pipeline's single sanctioned loop, where durations vote
the meter and the meter re-reads the durations — so **any consumer rebuilding
a `Log` from a saved record hits a guard that refuses ten verdicts this
document legitimately holds.**

It is the *value computed and nothing reads it* family in a new form: a value
computed, read by the guard, and **never written down**.

⚠️ **NOT FIXED HERE, deliberately.** Adding a key to `Verdict.to_json` changes
the serialisation of every record in the tree — which is precisely the
"perturbs upstream by existing" hazard this stage is required not to cause,
and `test_infer_bypass.py` asserts against it. `reinfer.py` restores the flag
on replay and **prints the count**, because a silent blanket
`single_pass_revision=True` would hide a genuine fixpoint, which is the one
thing that guard exists to catch. Ranked in §9 for a session that can price
the serialisation change.

---

## 6. THE MUTATION BATTERY

**10 arms, ALL RED, including a positive control in the same class.**

| arm | must go red on |
|---|---|
| `infer_may_overturn_a_reading` | `TestRule3ItMayNotOverturnAReading` |
| `infer_may_invent_a_value` | `TestRule4ItMayNotInventAValue` |
| `the_label_is_not_stamped` | `TestRule5ItSupersedesVisibly` |
| `is_inferred_always_false` | `TestRule5ItSupersedesVisibly` |
| `it_does_not_name_what_it_superseded` | `TestRule5ItSupersedesVisibly` |
| `it_may_run_before_evaluate` | `TestRule1ItMayNotRunBeforeEvaluate` |
| `it_may_run_on_an_open_log` | `TestRule2ItMayNotLoosenGather` |
| `witnesses_are_never_correlated` | `TestIndependence` |
| `bypass_writes_a_null_key` | `TestOffMeansAbsentNotQuiet` |
| **`refuse_everything`** (positive control) | **`test_an_admitted_candidate_lands`** |

⚠️ `refuse_everything` makes `_admit` reject every proposal, and the test that
must go red for it is the **ACCEPT** test. Without it, nine refusal arms would
prove only that the guards are reachable, never that anything is ever admitted
— *a battery of refusal tests can pass by refusing everything.*

⚠️ The battery **snapshots and restores the files it mutates rather than
reverting them through version control**, because that collision has already
cost a session its first three-arm run; and an anchor that does not occur
exactly once is reported as a **BAD ANCHOR error, not a skip** — two batteries
here have silently mutated the wrong occurrence of a repeated line and
reported a survivor that was really a mis-aimed arm.

---

## 3. REACH, MEASURED BEFORE THE RULE WAS CHOSEN

One fresh gather, Litolff Beethoven 5 mvt 1, pdf pages 1-4, 26 min 37 s
(`probe/reach.py`, `out/reach.json`). The probe exits non-zero if the record
holds no narrowed durations at all, so a clean zero could not be mistaken for
a clean result.

| | |
|---|--:|
| `duration` verdicts | **2,993** — decided 2,636, **narrowed 357**, abstained 0 |
| narrowed, on a notehead | **357** (all of them) |
| narrowed with 2 / 3 candidates | 304 / 53 |
| noteheads with no decided pitch | **215** |

⚠️⚠️ **THE `no_pitch` REFUSAL IS THE DATA'S, NOT A PREFERENCE.** Of those 215
noteheads, their staff's CLEF verdict is **abstained 108 / narrowed 107 —
decided ZERO**. So filling a pitch means inferring a clef, and the only
sideways route for a clef is the same part's staff on another system, which is
keyed on the PART JOIN — measured wrong on this very document for 12 of 75
staff-systems, with `P7` (Timpani) holding the VIOLA's staff on p3/s1. §4.

**The coarse funnel said the sideways evidence is universally present:** all
357 narrowed durations sit on a system with a DECIDED `Q.ONSET_COLUMN` and
have other staves deciding in the same bar (338 of them with 6+ other staves).
So nothing about the choice of population was speculative.

⚠️ One probe artefact, stated so nobody quotes it: `reach.py`'s independence
sample (874 of 3,101 pairs sharing a provenance row) keys a bar without the
staff, so it includes SAME-STAFF pairs, which of course share their cell's
rows. It is an upper bound and not the rule's number. The rule's own figure is
in §7 and it is measured only across different staves.

---

## 7. THE MEASUREMENT

⚠️ **ONE gather, adjudicated once, INFER'd once, exported twice.** The arms
carry no detector jitter and no adjudication jitter; they differ only in
whether INFER ran.

### 7a. The control, before any arm is read

    CONTROL: 16,923 of 16,923 verdicts reproduced exactly, 0 differ, +0 extra
             33,736 of 33,736 observations replayed

### 7b. ⚠️⚠️ THE FIRST RULE WAS TOO STRICT, THE FUNNEL SAID SO, AND THE FIX IS THE FINDING

The rule first required the narrowed note's own next onset to be the very
**next** column, and it inferred **1** of 357. `probe/funnel.py` — which
CHECKS ITSELF against the rule's own count, so a duplicated loop cannot drift
— put **335 of 356** at that one condition.

**A column is an instant on the SYSTEM.** A staff playing a half note while
its neighbours play eighths SKIPS columns, so adjacency only ever admitted the
finest-subdivided staff in each bar — which is the staff least likely to have
been narrowed in the first place. The claim never needed adjacency: it needs
the witness to END WHERE THIS NOTE ENDS. If both go k -> m, the stretch of
time is the same one for both, whatever lies between. Generalised:

| | strict (k+1) | **general (k -> m)** |
|---|--:|--:|
| narrowed durations reached | 357 | 357 |
| its event is in a column | 356 | 356 |
| it has a next onset in this bar | 21 | **165** |
| a witness spans the same k -> m | 6 | **40** |
| the witnesses are unanimous | 4 | **35** |
| **two or more INDEPENDENT witnesses** | 1 | **7** |
| exactly one candidate carries that length | 1 | **7** |

### 7c. What reached the file

One record exported twice by one tree (`export_arm.py`, which stamps the
exporting tree into the coverage JSON):

| | OFF | ON |
|---|--:|--:|
| parts | 75 | 75 |
| measures | 1,183 | 1,183 |
| note + rest elements | 2,460 | **2,466** (+6) |
| `notes_not_written: duration_narrowed` | 339 | **333** (−6) |
| `notes_not_written: no_pitch` | 215 | 215 |
| `notes_not_written: owned_by_another_staff` | 176 | 176 |

**The accounting IDENTITY holds:**
`notes(ON) − notes(OFF) == Δnarrowed − Δno_pitch`, i.e. `+6 == +6 − 0`. The
containment control holds too: every note the OFF arm wrote is still in the ON
arm, in order, in the same bar.

⚠️ **7 inferred, 6 reach the file.** The seventh is `glyph/4/0/8/9/3`, whose
`Q.GLYPH_OWNER` names a different staff — so the exporter refuses it as
`owned_by_another_staff` before it ever looks at the duration. **The one note
the rule could speak about there is a cross-staff duplicate the ownership
decision had already disowned**, which is the two stages agreeing, not a
defect.

⚠️ **The OFF arm reproduces the cleanup artefact to the unit** —
`duration_narrowed` 339, `no_pitch` 215 — which is the evidence that this is
the same document and the same pipeline the Phase 2 count was taken on.

### 7d. Hazard (b) is not a no-op: it refuses 8 of 35

Of the 28 unanimous cases stopped for want of two INDEPENDENT witnesses:

* **20** had only ONE witness verdict — a single witness is not corroboration;
* **8** had TWO or THREE witness verdicts that **collapsed into ONE
  independent group** (4 at 2→1, 4 at 3→1).

So the correlation computation is doing real work on real data: a naive count
of distinct witnesses would have made 8 more inferences that rest on a shared
provenance row. And among the 7 that landed, five witness verdicts reduce to
**3** independent groups in four cases.

⚠️ `COLUMN_MIN_INDEPENDENT_WITNESSES = 2` is **UNMEASURED and its price is now
known: 28**. It is not lowered to 1 — a single witness is exactly what hazard
(b) says cannot be trusted — but the number is stated rather than buried.

### 7e. ⚠️ THE ARGMAX REFUSAL EARNS ITS KEEP: 2 of 7 chose the reader's SECOND candidate

`was_readers_top_candidate` is **False on 2 of the 7**. So in two cases the
sideways evidence overturned the reader's own support ordering — which is
precisely what an argmax on `support` would have got wrong, silently, with a
number that reads as evidence.

### 7f. The self-check, on an invariant the rule did not read

`probe/self_check.py` proved independence first (the rule reads no `meter`;
`OMR_METER_FROM_BARS` is off) and then ran `bar_fill.py` on both arms:

| bars (1,183) | OFF | ON |
|---|--:|--:|
| **exact** | 449 (38.0%) | **451 (38.1%)** |
| SHORT | 218 (18.4%) | 216 (18.3%) |
| OVERFULL | 516 (43.6%) | 516 (43.6%) |

**Two bars became exact and none became overfull.** One-sided and in the right
direction, on a quantity the rule never consulted.

⚠️⚠️ **+2 of 1,183 IS NOT A RESULT TO CELEBRATE AND MUST NOT BECOME A TARGET.**
Four of the six written notes landed in bars that are still short. The number
is a REPORT and an alarm: bar fill is gamed by emitting FEWER symbols, so an
inference stage optimising it would learn to suppress. Nothing in `tools/`
reads it.

---

## 8. ⚠️ WHAT IS NOT ESTABLISHED

* **ACCURACY. Nothing here was checked against the print.** Six notes were
  added to the file and **no human has looked at one of them**. The self-check
  is an internal-consistency invariant, not truth. On a cleanup count these
  six are six things a human might have to take back out — an unadjudicated
  COST, exactly as the voices work's 31 refused ties and the dedupe work's
  `ff` 47 → 39 were.
* **n = 1 document, 1 publisher, 4 pages of ~16**, and Litolff `984073` is the
  *low-res bitonal* scan this file already calls the pessimistic end of the
  corpus. **Breitkopf Brahms 1 is where every figure here should be
  re-measured** — it fires 371 flag boxes and 656 dots against this
  document's 49 and 35, so its duration readings, its narrowings and its
  onset columns are all a different population.
* **The ENGRAVED family is untouched, by construction, and was not measured.**
* **Whether the witnesses are truly independent.** `independent_groups` is
  ONE-SIDED: disjoint provenance closures prove the ROWS differ, they do not
  prove the READINGS fail independently. Two staves of one badly-printed page
  share no row and still degrade together — the convention/ink correlation
  this repo records as real and unquantified. **Nothing here measures it.**
* **`COLUMN_MIN_INDEPENDENT_WITNESSES = 2` is asserted, not measured** (§7d).
* **`readjudicate.py` and `reexport_arm.py` were not run** (§2a) — the bypass
  claim for those two rests on the tests plus a grep, which is weaker.
* **The 191 narrowed notes that run to the barline are out of reach BY
  DESIGN**, not by accident: their length is the bar's, which is the meter,
  which this rule may not read without destroying its own self-check.
* **The 125 that lose every witness are a READING shortfall upstream**, not
  this rule's — the other staves in those bars have no decided duration to
  offer. The same shape as *76% of merged arcs bind fewer than two noteheads*.

---

## 9. WHAT A HUMAN STILL OWES A DECISION ON

1. ⚠️⚠️ **`Verdict.single_pass_revision` is not serialised** (§5g). It is SET
   (`record.py:835`) and READ by the fixpoint guard (`:1026`) and absent from
   `Verdict.to_json`, so **no saved record can be replayed through that
   guard** — ten verdicts on this record need it. Adding it to `to_json`
   changes the serialisation of every record in the tree, which is the exact
   hazard this stage was required not to cause, so it was **deliberately not
   fixed here**. Someone should price it.
2. **Whether the six added notes are right.** They need the print. Until then
   the flag stays off.
3. **Whether `OMR_INFER` should ever default on.** Not on this evidence: n = 1
   document, no accuracy, 6 notes.
4. **Whether the 191 barline-bounded notes are worth a second rule** that
   reads the meter — which would be a legitimate INFER rule but would need a
   different self-check, since `bar_fill` would then be scoring the quantity
   it optimises.
