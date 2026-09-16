# A parameter threaded end to end with NO PRODUCER — a derived check

**2026-09-15.** [docs/handoff-2026-09-11-phase-2-opened.md](../../docs/handoff-2026-09-11-phase-2-opened.md)
§8 item 5. **No weights, no page, no gather, no library** — every figure here is a
property of the tree, and the check runs in a cloud container.

Shipped: `tools/omr/no_producer.py`, `tools/omr/tests/test_no_producer.py`
(22 tests), `benchmarks/omr-no-producer-check-2026-09/{red_proof.py,mutation_battery.py}`.
⚠️ **Nothing was repaired** — finding the chains is the job; wiring them is not.

---

## 0. Why it exists

The fault has been found **twice in two days, by accident both times**:
`pdf_path` (dropped by `pipeline.run_staged`, so `gather_margin_labels` filed
`not_implemented` on **75 of 75 staves on every staged run this repo has ever
made**, ending five links later in 12 of 75 staff-systems joined to the wrong
instrument), and `roster` (threaded through both entry points with no CLI
argument anywhere). **Worth a derived check rather than a third discovery.**

⚠️ **A HAND LIST WOULD NOT HAVE DONE.** `export_coverage`'s 19-name `VISIBLE`
dict reported 5 and was blind to 15; `ARITY_FIELDS` was incomplete the day it
landed. The shape is derived from the code, the way `staves_schema.py` derives
by AST and `test_flag_default_direction.py` evaluates a predicate on its own
default rather than guessing from a string.

## 1. THE FUNNEL — 8,991 → 2

`tools/`, tests not counted as producers, on `ce7b8ba7`:

| | count | what it asks |
|---|--:|---|
| **D0** | **8,991** | every parameter declared anywhere in `tools/` |
| **D1** | 323 | ...whose default is literally `None` |
| **D2** | 148 | ...that a forwarding edge TOUCHES (as source or target) |
| **D3** | 39 | ...with no producer at the fixpoint |
| **D4** | 9 | ...grouped into CHAINS crossing ≥ 2 layers |
| **D5** | **2** | ...one of whose layers ABSTAINS when the value is absent |

The naive check — *"an optional argument nobody passes"* — reports the **323**
of D1, which is the *reports 200 things, gets ignored, gets deleted* outcome
`export_coverage`'s own docstring warns about.

⚠️ **D2 IS SYMMETRIC AND THAT IS LOAD-BEARING.** A node counts if an edge
touches it as source *or* target. `run_staged(roster)` is the HEAD of its chain
and has nothing forwarding into it, so a target-only test reports every chain
**without the layer the repair lives in**.

⚠️ **D4 — THE CHAIN IS THE REPORTING UNIT, NOT THE PARAMETER.**
`run_staged(roster)` alone is an ordinary optional argument; `gather_external(roster)`
alone is a function with a sensible default. The fault is that one hands to the
other and **nobody starts the chain**. Per-parameter reporting gave four rows
for one fault; per-chain gives one, printed in the order the value would travel.

⚠️ **D5 IS THE DISCRIMINATOR AND IT EARNS ITS KEEP: 9 → 2.** A guard is
`if p is None:` / `if not p:` whose body RETURNS, RAISES, or files a reason
string. **`p = p or DEFAULT` is not a guard.**

## 2. BOTH KNOWN INSTANCES, CAUGHT WITH NO HINT

```bash
git archive 3a725f07^1 tools | tar -x -C <scratch>
python3 -m tools.omr.no_producer --scan <scratch>/tools     # pre-fix tree
python3 -m tools.omr.no_producer                            # main today
```

| | pre-`3a725f07` | main today |
|---|--:|--:|
| D3 unsupplied | 41 | 39 |
| D4 chains | 10 | 9 |
| **D5 reported** | **3** | **2** |
| findings | `pdf_path`, `dossier`, `roster` | `dossier`, `roster` |

**Instance 1 is caught on the tree where it was live and is gone on the tree
where it was fixed — the delta IS the repair, not a threshold move.** Instance 2
is a live catch with its chain named in full:
`roster: run_staged() → run_staged_on() → gather() → gather_external()`,
abstaining at `gather.py:2395`. Neither needed a hint, and
`test_roster_is_found_with_no_hint` asserts exactly that.

## 3. ⚠️ A THIRD INSTANCE, FOUND BY THE CHECK — `dossier`

Same chain, same file, same shape, **recorded nowhere**:

```
dossier: run_staged() -> run_staged_on() -> gather() -> gather_external()
    ABSENCE CHANGES BEHAVIOUR in gather_external() at gather.py:2386
```

`grep -rn dossier tools/omr/staged/__main__.py` returns **nothing** — the staged
CLI has no `--dossier`, where `tools.omr.transcribe` has had one since the
dossier layer landed. `Q.DOSSIER_FACT` abstains `OUT_OF_SCOPE: "no dossier
supplied"` on **every staged run**, beside `Q.ROSTER_ENTRY`.

⚠️ **This is NOT a claim that the staged path should be dossier-seeded** —
CLAUDE.md records that the scan benchmark runs dossier-free BY PROTOCOL. It is a
claim that the parameter is there, the consumer waits on it, and **no route
exists to hand it one** — a different fact from a deliberate default, and
currently indistinguishable from one in the record. **Not repaired.**

## 4. THE FULL LIST, WITH A REASON EACH

**Reported**, and `RECORDED` says in terms that each is an **OPEN FINDING, not a
permission**: `roster`, `dossier`. They are recorded only so `--check` gates a
*fourth* instance while these two are live, and
`test_every_recorded_entry_still_fires` **fails the day a producer lands**,
forcing the entry out — the `KNOWN_GAPS` stale-entry rule.

**Not reported** — 7 chains with no producer and no absence branch, every one
`None means use the module default`. ⚠️ They are **PRINTED under `NOT REPORTED`,
never suppressed**, and the split is derived from the guard test: **no name
appears anywhere in the module.**

| chain | why it is fine |
|---|---|
| `dossier_dir: resolve_dossier → find_dossier` | `(dossier_dir or DOSSIER_DIR)` |
| `catalog_path: work_id_for_pdf → … → _catalog` | falls through to the catalog's own path |
| `fixtures: survey → load_run` | documented: resolves at CALL time |
| `most_labelled: assign_slots → … → reference_view` | a ranking preference; `None` is a valid third value |
| `timeout_s: read_staff_labels_surya → read_crops_surya` | subprocess timeout default |
| `timeout_s: score_pair → score_batch` | same |
| `n_pages: acquire_roster → search_order` | optional upper bound on the page walk |

## 5. PROOF IT CAN GO RED — three levels

**(a) On the real tree, with an instance it was never told about.**
`red_proof.py` copies `tools/` to scratch and threads a `rank_pages` parameter
through two real functions in `export_coverage.py` with no producer and an
abstaining consumer:

```
CONTROL (unmutated copy of tools/): ['dossier', 'roster']
MUTATED (one injected chain):      ['dossier', 'rank_pages', 'roster']
```

⚠️ The control arm **exits non-zero unless the copy reproduces the tree's own two
findings**, so a broken copy cannot read as a successful injection.

**(b) At the CLI.** A test clears `RECORDED` and asserts `--check` exits 1
naming the chains.

**(c) Mutation battery** — 11 arms, positive control run unmutated first, every
anchor asserted to occur **exactly once**. ⚠️ First run: **2 SURVIVORS, and both
were *a test named for a hazard it does not reach*** — the one-layer test's
parameter never entered D3 at all (no edge touched it), so the chain-size rule
was never consulted and `len(keys) < 0` walked past it; and the decorator test
passed a *string* on the decorator, which cannot distinguish the two scopes.
Both closed with fixtures that REACH the mechanism. Second run: **11 arms, all
red, 0 survivors, 0 bad anchors, positive control green.**

## 6. WHAT THE MEASUREMENT REFUTED

**6a. ⚠️⚠️ COUNTING TEST CALL SITES AS PRODUCERS TAKES THE REPORT TO ZERO.**
`--tests-produce` still catches `pdf_path` and **loses both live findings**,
because `test_staged_part_join.py:66` calls `run_staged('/some/score.pdf', [0],
**kwargs)` and that unreadable splat marks every `run_staged` parameter
supplied. **A parameter only ever supplied by a test fixture has no production
producer.** The arm is a flag, so the cost is priced rather than assumed.

**6b. ⚠️⚠️ WIDENING THE SCAN SILENCED IT, AND THAT WAS A REAL DEFECT.** Adding
`backend/` took the report **from 2 findings to 0**. Cause: the call graph is
keyed by NAME, and `asyncio.gather(*tasks, return_exceptions=True)` in
`backend/modules/claude_vision.py` matched `staged.gather` by its last segment —
its `*tasks` splat then marked every parameter of *our* `gather` supplied.
Repaired by `_local_packages` (a name bound by importing a module we do not scan
is not our function); after it, `--scan tools --scan backend` reports the same 2.
**The lesson is the FAILURE DIRECTION: the check reported a clean tree, which is
exactly what a working check reports.**

**6c. Name-keying is imprecise, and the DIRECTION is the argument for it.** Two
functions sharing a name have producers POOLED, so a collision can **hide** a
finding and never invent one. With the splat rule and the positional rule, every
imprecision runs toward silence: **the findings can be trusted; the silence
cannot.**

**6d. Of the brief's four candidate discriminators, two matter and two do not.**

- *"absence changes behaviour"* — **this is the one**, 9 → 2.
- *"forwarded through ≥ 2 layers"* — yes; it is what makes the report readable.
- *"the entry point has no such argument"* — **measured and deliberately NOT
  implemented.** It is a *consequence* of the fixpoint, not an input: if the CLI
  had the argument it would supply it and the chain would have a producer.
  Detecting it separately adds nothing and needs a hand list of entry points.
- *"declared in `wants` and read by nothing"* — **a DIFFERENT fault, already
  owned** by `inventory --check` / `gather_coverage`. ⚠️ `pdf_path` was invisible
  to both, because `gather_margin_labels` **was** reading its input and
  reporting honestly. **Read-by-nothing and supplied-by-nothing are different
  questions**; this answers only the second. No duplication.

**6e. A decorator is evaluated in the OUTER scope.** The handoff warns that a
similar check once reported zero because `inspect.getsource` *includes* the
decorator. An AST walk has the mirror hazard: a bare name in `@decide(wants=…)`
would be read as the decorated function's parameter and **manufacture a
forwarding edge out of a declaration**. Decorators are visited before the
parameter scope is pushed. ⚠️ It is an **EQUIVALENT MUTANT on this tree** — the
funnel does not move — so it is named and pinned by a synthetic test rather than
claimed as a fix.

## 7. WHAT IS NOT ESTABLISHED

- That `roster` and `dossier` **should** be supplied. The check says no route
  exists, not that one is wanted.
- **Recall.** Three instances caught (two real, one injected); the denominator is
  unknown.
- **Non-`None` sentinels.** D1 requires a literal `None`; a parameter defaulting
  to `""`, `()` or a sentinel object is not examined, and widening D1 was not
  measured.
- **Dynamic supply** (`functools.partial`, runtime dict splats, `getattr`
  dispatch) is invisible — and every such case makes the check **quieter, never
  louder**.
- Anything outside `tools/`. `backend/` and `benchmarks/` were scanned as arms
  and report the same 2; `frontend/` is TypeScript.

## 8. COST

| | |
|---|--:|
| `python3 -m tools.omr.no_producer` (291 files) | **2.8 s** |
| `--scan tools --scan benchmarks` (1,000 files) | 5.7 s |
| `test_no_producer.py`, 22 tests | ~14 s |
| `red_proof.py` | ~5 s |
| `mutation_battery.py`, 11 arms | ~6 min |

No weights, no venv, no network.

## 9. Reproduce

```bash
python3 -m tools.omr.no_producer            # the report
python3 -m tools.omr.no_producer --check    # non-zero on a NEW chain
python3 benchmarks/omr-no-producer-check-2026-09/red_proof.py
python3 -m pytest tools/omr/tests/test_no_producer.py -q
```
