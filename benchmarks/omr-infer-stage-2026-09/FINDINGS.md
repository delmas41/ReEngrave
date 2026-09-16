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
