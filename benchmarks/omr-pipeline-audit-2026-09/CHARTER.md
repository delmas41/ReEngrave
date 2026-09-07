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
