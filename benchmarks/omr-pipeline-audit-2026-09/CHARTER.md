# Full pipeline audit — charter and run log

**Commissioned by Sean, 2026-09-07 (overnight).** Four agents, one coordinator.
Every report comes to the coordinator; the coordinator synthesises and Sean reads
one thing, not four.

⚠️ **This file is the coordination record.** Sequencing and scope held only in
conversation is the first thing lost to a crash — `docs/backlog-2026-09-07-open-items.md`
§A0 exists because that already happened once today.

---

## The commission, in Sean's words

1. *"a systematic process that follows and analyzes each gathered piece of
   information and asks if there is more information that should or could be
   gathered"* → **Agent I**
2. *"another agent that is analyzing each decision point in the pipeline to
   determine effectiveness as well as explore what other information could be
   helpful to make this decision better. Ask again if the type of decision —
   gating / probability etc — is the best way to decide, and what are the
   downstream implications of the decision type."* → **Agent II**
3. *"another agent that critically looks at our benchmarking and measurements
   processes and suggests improvements … convert or translate all the different
   numbering measurement systems into a single internal measurement system …
   Currently sometimes 1.000 is what we are aiming for and other times it would
   be a horrible score."* → **Agent III**
4. A verifier, at Sean's instruction, because in this project two sessions have
   confirmed a FALSE claim in opposite directions within an hour. → **Agent IV**

**Sean's decisions taken on the plan:** measurements permitted · verifier
approved · the unit is **% of achievable**, higher is better.

---

## Roster

| agent | question | file |
|---|---|---|
| **I** | the INFORMATION axis — every signal's life, and what is never gathered at all | `INFORMATION_LIFECYCLE.md` |
| **II** | the DECISION axis — effectiveness, decision TYPE, and what the type costs downstream | `DECISION_TYPES.md` |
| **III** | the MEASUREMENT axis — critique, and the % of achievable scale | `MEASUREMENT_SYSTEM.md`, `metric-registry.json` |
| **IV** | the VERIFIER — re-checks I/II/III against the tree before the coordinator accepts anything | `VERIFICATION.md` |

## What this audit is NOT

It does not rebuild [`docs/architecture-decision-map.md`](../../docs/architecture-decision-map.md).
That map already holds the ~120 decision points, the BLIND TO column, the
information ledger (§6), the gathered-and-never-used list (§7) and 27 code-vs-prose
contradictions (§8). Each agent's value is defined as **strictly beyond** it:

- I — verification of the map's consumer claims by grep, plus the **never-gathered**
  register (available-and-never-computed; obtainable-with-a-new-read), which the map
  does not cover.
- II — **effectiveness** (reach × precision, measured) and **reversibility**
  (deletion vs quantisation vs re-ranking), which no existing document classifies.
- III — the metric layer, which the map explicitly puts out of scope (§11).

## Rules carried into every brief

- **The tree outranks the ledger.** file:line or a committed artefact, or it is not a claim.
- **UNMEASURED is a word you must use.** Never estimate and present as measured.
- **Standing rule A00** — a worse score does not condemn the mechanism. Comparison →
  metric → downstream consumer → only then the mechanism.
- **Corroboration is not evidence** — two signals sharing an ancestor are one signal.
- **An uncalibrated probability is worse than none.** "Make it a probability" is not
  automatically the answer; signed evidence with a threshold often is.
- `git log --all -S` before calling anything unbuilt.
- Read-only on `tools/`, `backend/`, `frontend/`. No pipeline behaviour changes tonight.

## Machine rules in force

- ⚠️ **Never `pkill -f llama-server`** — one machine, one shared Surya server.
- No `scan_eval` / `orchestral_eval` without coordinator approval: long, and
  `page_normalise` has core priority per §A0.
- Every arm gets its own `--tag=`; check wall-clock before believing an identical A/B
  (`scan_eval` caches by default and a cached arm reports a flawless "no change").
- This worktree has neither `.venv-omrned`, `.venv-surya`, nor the weights symlink.

## Round log

| round | dispatched | agents | state |
|---|---|---|---|
| 1 | 22:25 | I (stages 4–7 + ownership), II (clef ladder + ownership), III (critique + registry prototype) | **done** — `ac88148e`, ~2,100 lines, 9 probes |
| 1v | 22:47 | IV verifies I + III, extended to II at 23:00 | running |
| 2 | 23:05 | I (stage 3 → census → arcs) · II (direction_text → arcs → export → meter) · III (structural floor + the `input` ceiling) | running |
| 3 | pending | scoped from round 2 + the verifier's corrections | — |

**Round 2 scopes are the agents' OWN recommendations**, approved with two changes:
Agent III's `input` ceiling promoted to joint-first (it is the empty ceiling that
makes every scan detector percentage a fiction), and musicdiff scoring
un-embargoed for it. `scan_eval` / `orchestral_eval` remain embargoed.

⚠️ **Round 2 convergence to watch:** all three agents arrived independently at
`direction_text` (72 uncatalogued decision points, an `accepted[0]` argmax over a
`Reader` interface with no confidence field, ~75% of whole-work wall clock) and
at tie/slur pairing (71 points, zero §5 rows, where Agent II's 263 arc-class
contests land). Convergence from three lenses is a reason to look, **not**
evidence — they share one substrate, the map.

## ⚠️ Cross-report hazard, round 1 — one observation, reported twice

Agents I and II both report **436** contested pairs whose two readings disagree
about what the ink IS. Two agents agreeing is not corroboration when they read the
same `OMR_CONTEST_DUMP` artefacts. And their breakdowns **disagree**: arc-class
263 both ways, but accidentals **15 vs 31** and dynamics **22 vs 38**. Referred to
Agent IV as its first cross-report item. Until it reports, the coordinator states
this as ONE finding, never two.

## Inference discipline issued to all agents, 2026-09-07

**A near-50% split is what NO relationship looks like.** Round 1 reported that the
deleted copy of a contested pair scored higher than the survivor 44.8% of the
time. That is what you would see if confidence were unrelated to correctness —
evidence that confidence is uninformative at that site, not that the site chooses
wrongly. Issued after it appeared, not before, which is the honest ordering.

⚠️ Round 1 is deliberately a **scoping + worked-example** round: the coordinator
approves each schema before it is applied to five more stages.

---

## ⚠️ Incident, round 1, 2026-09-07 — the audit started on a stale tree

**Sean asked whether the evening's map changes had landed. They had — on `main`,
and not here.** This worktree was **28 commits behind** at dispatch, so the
coordinator read, and all three round-1 agents were briefed against, the
**superseded 1,303-line map**. The current one is 1,629 lines.

| landed on main this evening | what it did | in the audit tree at dispatch |
|---|---|---|
| `fbbd09c1` | adversarial VERIFICATION of the map — 11 errors, **all negatives about consumers** | **no** |
| `94c46e80` | second pass — §5 **120 → 176 rows**, CONSUMED BY on all 15 tables, check `V8` | **no** |

Also absent: `tools/omr/transcribe.py` +35, `contextual.py` +103,
`measure_extractor.py` +104, `line_detection.py` +9, `export.py` +19, and a new
463-line `score_language.py` — three of those inside round 1's own slices.

**Fixed** by rebasing this branch onto `main` (`5ba44c44`) ~10 minutes after
dispatch, while the agents were still in their reading phase, and messaging all
three to re-anchor: re-derive every `file:line`, and do not re-report a
correction that already landed.

⚠️ **The lesson is the project's own standing rule and it caught the audit
itself**: *measure the merged tree; check the base before building.* An audit
of a stale tree produces citations that are individually checkable and
collectively wrong. Recorded here rather than quietly fixed because Agent III's
Part A is a critique of exactly this failure mode — and it now has a live
instance from tonight rather than only the `c378412f` precedent.

**Carried into round 1 as substance, not just correction:**
- The verify pass's headline — ***what is MISSING outranks what is wrong***.
  Independent enumeration from code found **185 decision points** where §5
  catalogued a fraction: `direction_text` **72** (incl. an `accepted[0]` argmax
  over a `Reader` interface that carries **no confidence at all**), slur pairing
  **46**, tie pairing **25** — all in the spine, all with zero §5 rows.
  `staff_labels_surya`, the free DEFAULT reader, is absent while the unreachable
  human rung is catalogued in full.
- ***A name grep is not a consumer check*** — E1: `nominal_line_spacing_px`
  "no production site reads it" is FALSE; `types.py:102` returns it from the
  `line_spacing_px` PROPERTY, which has 15 production readers.
- `bracket_reader.py` (390 lines) is a **third** orphan module.
- `V4` undercounts **by construction** — it matches only literal
  `os.environ.get()`, so a name held in a constant vanishes silently. 36/16
  becomes **41 in tree / 20 undocumented**.
- ⚠️ `OMR_CONDENSED_PARTS` is **INERT even when set** — nothing writes the
  `condensed_parts` field in production (E9). Any figure resting on its oracle
  ceiling describes a configuration that cannot currently occur.

---

## Round 1 verified — and the coordinator's own claim was one of the errors

`VERIFICATION.md` (549 lines). **All three reports sound**: of ~48 quantities
recomputed from artefacts and source, **44 reproduced exactly**, several to the
last digit of a float; all probe families re-ran with `git diff` empty.

⚠️ **Six of the eight defects are negatives or universals** — the same
distribution the decision map's own verification pass found. That is now twice in
one day, from independent auditors, on independent material. **Treat "the only",
"never", "nobody" and "zero" as the highest-risk sentence shapes in this project,
and prefer "n of m".**

| # | claim | corrected |
|---|---|---|
| D1 | Agent II: *"0 of 4,521 ownership verdicts are ever revisited"* | FALSE. `OMR_ARC_ATTRIBUTION=move` is default-ON and re-decides every arc — reaching exactly the 263 arc-class contests. The sharper claim is COVERAGE: arcs have a live recovery path, note rank-0 has one that is off, **flags (47, where the disagreement IS the duration) and accidentals (31, where it IS the pitch) have none.** |
| D2 | Agent I: *"the only silent deletion rule with no counter"* | FALSE. Four counterexamples, two in the same neighbourhood. A member of a class, and the class is the better finding. |
| **D3** | **The COORDINATOR: *"`condensed_parts.py` is a fourth orphan module, stronger than either agent claimed"*** | **FALSE, and it is my error.** `players_for_label` has **three benchmark importers**. It is a *production* orphan — `probe` by the map's own legend, the exact `NOBODY`-vs-`probe` distinction the verify pass was created to police. My grep was `tools/omr/*.py`: one directory, no recursion, no `benchmarks/`. **I relayed "a name grep is not a consumer check" to three agents and then made that mistake in the same message.** The `condensed_parts` FIELD half stands — read at `export.py:3331`, written nowhere — so `OMR_CONDENSED_PARTS` is still inert. |
| D4 | Agent III: *"none records the commit"* | FALSE — `results-condensation-arm.json` carries `git_head`; and 19 files, not 20. |
| D5 | Agent III: Dvořák's zero structural charge *"confirmed three ways"* | ONE fact seen three ways. The auditor of shared substrate missed it in its own report. |

**The cross-report hazard resolved, and there was no discrepancy.** Agents I and
II read the same 20 `OMR_CONTEST_DUMP` files, so **436 is ONE observation** and is
reported as one. Their "conflicting" breakdowns were a named class *pair* against
a whole *category*: 15 ⊂ 31 and 22 ⊂ 38, both right, different questions.
`additive-vs-gated/FINDINGS.md` contains no 436, so the column is genuinely new.

**What held hardest.** The engine-independence ceiling is **stronger than
claimed**: four rival predictors of the 7/10 bit-identical split were tested —
page index, work, staff count, our own charge magnitude — **none separates, and
`n_systems` separates 10/10**. It is not serendipity either: CLAUDE.md's
`OMR_SLOT_STITCH` entry **predicts that variable**, so a post-hoc predictor turns
out to have been pre-registered. Also exact: 35/35 registry transforms, Agent II's
truth adjudication on all three rows, and Agent I's D23 overturn.

⚠️ **Inference correction, issued and then corrected the same night.** I told the
agents a near-50% split is what no relationship looks like. At n=4,521, 44.8% is
**z ≈ −7** — the effect is REAL and still not evidence about correctness. The
usable phrase is **"real but uninformative"**, not "indistinguishable from
chance".

⚠️ **M4, a process defect worth more than its size.** Six of Agent II's probes
hard-code `/Users/seanjohnson/Desktop/ReEngrave`. Byte-identical today, but it is
**the stale-tree incident installed into the audit's own instruments** — a probe
that reads an absolute path measures a tree other than the one it is run against.
Ordered fixed before round 2 lands.

---

## Phase 2 — build. Sean's authority, 2026-09-07 ~23:40

> *"I am giving you authority to turn analysis into fixes … new agents be spun up to
> do the fixes and then use the analysis agents that dug up the work double check and
> advise the fixing/building agents. You manage, our current agents analyze, advise
> and check the work, new agents you send out do the fixes and builds."*

**The separation is the control.** An agent does not review its own build, and the
agent that found a thing does not implement it.

| role | agents | may edit |
|---|---|---|
| coordinate, merge | this session | audit dir + merges |
| analyse · advise · **review the builds** | I, II, III | nothing in `tools/` |
| **build** | A, B, C (new) | only their own file list |
| verify | IV | nothing — reports only |

**Isolation:** each build agent has its own git worktree cut from `main` at
`974971e3` — ⚠️ **not** from the audit branch, and **re-cut after main moved 5
commits under us**, because tonight's first incident was an audit that began 28
commits stale. Venv and weights symlinks pre-created so no agent re-bootstraps.

**File ownership is disjoint by construction** — the only reliable way to run three
builders at once:

| agent | branch | owns |
|---|---|---|
| A | `claude/fix-record-refusals-clef` | `transcribe.py` · `clef_locator.py` · `clef_correction.py` · `key_signature_vote.py` · `time_signature_locator.py` |
| B | `claude/fix-barline-evidence` | `types.py` · `measure_extractor.py` · `staff_detector.py` |
| C | `claude/fix-probe-hygiene-dashboard` | `benchmarks/omr-pipeline-audit-2026-09/**` · new files in `tools/dashboard/` |

### The acceptance bar, identical for all three

1. **Exported MusicXML byte-identical**, scanned page and engraved fixture, before
   and after. Proven by `diff`, never asserted.
2. Result JSON may gain **new keys only** — a committed comparison walks both and
   asserts no pre-existing key changed value. The auditors re-run it.
3. Unit tests **run RED first**, with the change removed. ⚠️ This repo has shipped a
   test that passed vacuously; the ledger-zone parity test is the precedent.
4. Targeted test files only. **Nobody runs the whole suite** — seven concurrent
   agents once timed it out at 10 minutes.

⚠️ **Change no default, and fix no decision you are recording.** A builder who wants
to correct the decision it is instrumenting must stop and report. *Record first,
decide later — including deciding not to.* That is the audit's own shortlist item 1
and it is what makes this phase byte-identical.

### What is deliberately NOT being built tonight

- **The clef / key-signature / meter guard.** The strongest finding of the audit,
  and it is **coupled to the held `OMR_INSTRUMENT_CLEF_DEFAULT` decision, which is
  Sean's.** Queued to be built default-OFF behind its own flag once the recording
  sweep lands, so the evidence exists before the repair does.
- **`_drop_close_outliers` consuming the new `Barline` evidence.** Recording is
  byte-identical; consuming it is a measured change and needs an A/B this machine
  cannot afford beside three builders.
- **Dashboard integration.** The renderer is standalone; the `generate.py` diff is
  proposed and not applied. A generated artefact with a staleness gate does not get
  edited unreviewed at 2am.
