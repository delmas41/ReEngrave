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
| 1 | 2026-09-07 ~22:25 | I (stages 4–7 + ownership), II (clef ladder + ownership), III (critique + registry prototype) | running |
| 1v | pending | IV verifies round 1 | held until I/II/III report |
| 2 | pending | remaining stages, scoped from round 1's schemas | — |

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
