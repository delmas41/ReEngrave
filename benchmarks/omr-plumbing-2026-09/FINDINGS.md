# The plumbing matrix — 143 arms, and the pipeline is connected

**143 runs, 0 non-zero exits, 0 crashes.** Every fixture × every derived flag
flipped in both directions, plus the OCR rungs and a no-weights control.
Tree `29fa5ca4`, one page per run, ~11 s each.

```bash
bash benchmarks/omr-plumbing-2026-09/probe/run_matrix.sh
python3 benchmarks/omr-plumbing-2026-09/probe/edges.py out/matrix/*.record.json
```

## The headline

| state | n | what it means |
|---|--:|---|
| **LIVE** | **120** | a value crossed this edge, PROVED by the verdict naming the row |
| ASKED_ABSENT | 4 | the consumer asked; the page was silent — the pipeline working |
| NOT_EXERCISED | 3 | the consumer never ran: no fixture printed this ink |
| READ_UNTRACEABLE | 1 | read via `ev.state()`, which leaves no trace |
| INDIRECT_ONLY | 3 | declared, never read directly, present in the ancestry |
| **NEVER_ASKED** | **8** | declared and never read — a wiring fault |
| PRODUCER_DEAD | 3 | nothing produced the value in any arm |
| CONSUMER_DEAD | 1 | `join_parts`, a DECLARED STUB — correct |

⚠️⚠️ **THE RESULT IS A NEGATIVE, AND THAT IS THE POINT: every one of the 8
NEVER_ASKED edges is already on `inventory --check`'s known list, and
`measured NOT in the static list` is EMPTY.** So 143 arms found **no wiring
fault the tree did not already declare.** The staged pipeline's declared
connections carry.

## ⚠️ Three instrument bugs, each found before its result was believed

1. **An INFER edge could never be LIVE.** Nothing added to `carried` for an
   inference, so rule 1's four edges reported NEVER_ASKED across 143 arms in
   which it fired **46 times**. A firing is the only available proof — the
   record does not name what a rule consulted — so a fired rule now marks its
   declared `reads` at `strength: inferred`.
2. **`ev.state()` leaves no trace.** It calls `_check()` (which enforces the
   declaration) and NOT `_note()` (which records the row), so a quantity read
   only through `state()` never enters `considered`/`used`/`basis`. Three
   decisions do exactly that. Those edges are now `READ_UNTRACEABLE` —
   unprovable, not false.
3. **`basis` is the TRANSITIVE closure and was being read as a direct read.**
   On one arm `adjudicate_part_partition` carried `instrument` and
   `staff_ordinal` purely because `slot_index`'s verdict rests on them. The
   instrument contradicted `inventory --check`; **`inventory` was right.**
   Now `considered ∪ used` only, with ancestry reported apart as
   `INDIRECT_ONLY`.

## ⚠️⚠️ The finding that outranks the edge table: `state()` is invisible to the independence computation

`Log.closure()` walks `row.basis`. A `state()` read never enters `basis`. So
**two verdicts that both depend on a quantity through `state()` have disjoint
closures with respect to it**, and `infer.independent_groups` — whose whole job
is to stop double-counting witnesses that rest on a shared row — will count
them as independent.

Its docstring already names itself one-sided about the ink/convention
correlation *"the record cannot see"*. This is a **second, undocumented**
blindness, and unlike the first one the record COULD see it.

⚠️ **LATENT, not observed.** All three `state()`-only reads today are at fine
scope (`KEYSIG_RUN_POSITION` per staff, `BEAM_STROKE`, `STEM`), so two
witnesses would rest on different rows anyway. The exposure arrives the day a
decision reads a PAGE- or DOCUMENT-scoped quantity via `state()`: every verdict
of that decision would then share an invisible row. No instance today.

## What the fixtures could not exercise

`adjudicate_tuplet` **never ran in any of 143 arms** — the detector produced no
tuplet marker on any fixture, including `v2_marks`, which prints explicit
`\tuplet 3/2` and `\tuplet 5/4`. That is a REACH finding, not a wiring one, and
it propagates: `tuplet_ratio → export` reads PRODUCER_DEAD for the same reason.

## What is NOT established

- **Quality. Nothing here scores a reading.** Connectivity only.
- The fixtures are **engraved LilyPond**, the easy domain. `v6_scanlike` is a
  raster of one of them, not a real scan.
- **The flag list covers 24 of 61 flags.** `test_flag_default_direction.py`,
  which the matrix derives its arms from, only matches the inline
  `os.environ.get(FLAG, x) in {...}` form — it is blind to the two-statement
  and injectable-environ forms. 37 flags were never flipped here.
- **EXPORT edges are `strength: inferred`**, never proved: the exporter records
  counters, not reads.
- ⚠️ Every record is stamped `provenance.dirty: true`, because a concurrent
  agent was writing documentation into the same worktree. `git status
  --porcelain -- tools/ backend/` returned **0** for the whole run, so no
  pipeline code changed — but the stamp cannot say that itself, which is its
  own finding: **in a shared worktree the dirty flag saturates and stops
  carrying information.**
