# Roadmap 1.2 — run-time budget: where ADJUDICATE/EVALUATE/INFER actually spend time

2026-09-23, staged pipeline only, no flag. Branch `claude/decide-stage-cost-1.2`.

Starting point: tonight's first whole-movement gather (Litolff Beethoven 5
mvt 1, 16 pages, `benchmarks/acceptance/gather_movement.sh`) finished GATHER
inside its 25-minute estimate and then spent **~12.3 hours** in
ADJUDICATE + groups + EVALUATE + INFER + write, single core, 17 GB RSS. The
per-decision "verdicts so far" progress lines in that log carry no
timestamps, so it cannot say WHICH decision the time went into — only that
`glyph_owner` reached 20,056 verdicts and `arc_owner`/`event`/`voices` are
large. This work profiles the same code, per decision, on the 4-page
`beethoven5-p1-p4-ink-identity.record.json` shared record (146 MB, 7 systems,
75 staves, 40,878 observations, 4,003 abstentions).

## The two mechanisms, both measured directly

### 1. `Log._ids`'s SELF_AND_DESCENDANTS branch rescanned the whole log

```python
# SELF_AND_DESCENDANTS -- scan, because descendants are not enumerable
for (q, key), ids in self._by_subject.items():
    if q != quantity:
        continue
    if subject.contains(Subject.from_key(key)):
        yield from ids
```

`self._by_subject` is keyed `(quantity, subject_key) -> [row ids]`, with one
entry per distinct subject a quantity was ever filed on — **not** one entry
per system. So this loop visited **every** (quantity, subject) pair the
whole log holds — ~45,000 of them on this 4-page record — on **every single
call**, re-parsing every matching key with `Subject.from_key` regardless of
which system was asked about.

`adjudicate_arc_owner` (`tools/omr/staged/adjudicators/ownership.py:265`)
issues exactly this call once per arc, asking for `Q.GLYPH_BOX` at its own
system: 779 calls on this record, each re-scanning the whole table and
re-parsing every one of ~700-1,540 matching glyph subjects per system. This
is the mechanism the brief named; `subjects_for()` (called once per
decision, not per subject) also does a full `log.all_rows()` scan, but that
is O(total rows) **once**, not O(total rows) **per subject**, and was never
the dominant term.

**Fix** (`tools/omr/staged/record.py`, `Log`): a per-quantity index
(`_descendants_index`) plus a per-(quantity, subject) resolved-answer cache
(`_descendants_ids`), both keyed on a write counter (`_quantity_version`,
bumped in `_index()` on every `observe`/`abstain`/`record`). Correct whether
the quantity is GATHER-frozen (the common case) or written progressively
during ADJUDICATE/EVALUATE -- no assumption was needed about whether any
decision reads its own quantity's descendants mid-run, because the cache
answers exactly "what does the log say **right now**", not "what did it say
when GATHER ended". `SELF_AND_ANCESTORS` was already O(depth) dict lookups
and needed no change.

**Isolated measurement** (`probe_arc_owner.py`, system `system/1/0`, 64
arcs, `correlated_groups()` monkeypatched to a no-op so this mechanism is
isolated from the second one below):

| | seconds | s/arc |
|---|--:|--:|
| pre-1.2 (full-table scan every call) | *(see below -- could not complete within the observation window)* | |
| **1.2 fix** (cached index + cached result) | **0.336** | **0.0052** |

### 2. `Evidence.correlated_groups()` -- O(n^2) over everything a decision "saw"

```python
rows = [self.log.row(i) for i in self._seen]
groups = []
for i, a in enumerate(rows):
    for b in rows[i + 1:]:
        if not _one_signal(self.log, a, b):
            continue
        ...
```

`self._seen` accumulates every row id a decision's `Evidence` consulted
(via `rows()`/`verdict()`/`verdicts()`) for ONE subject. For `arc_owner`,
that is essentially the whole system's `Q.GLYPH_BOX` population fetched via
mechanism 1 above -- **n ~= 770 on every one of the 779 arcs** (measured:
`considered`-set size min=770, median=770, max=770 on system `system/1/0`).
`correlated_groups()` runs this O(n^2) walk **from scratch for every arc**,
even though ~99% of that 770-row set is identical across every arc of the
same system. `_one_signal` further calls `Log.closure()` for any pair that
is not two `Observation`s sharing `(reader, frame, quantity)` -- and
`closure()` was unmemoised, doing a fresh BFS on every call, including from
`Evidence._admit`'s circularity filter (`quantities_in_closure`), which runs
on every `rows()`/`verdicts()` call regardless of scope.

**Isolated measurement**, same 64 arcs, mechanism 1 already fixed so this is
the marginal cost of `correlated_groups()` alone:

| configuration | seconds / 64 arcs | s/arc | function calls |
|---|--:|--:|--:|
| `correlated_groups()` disabled | 0.336 | 0.0052 | 1,971,921 |
| pre-1.2 algorithm, `closure()` **memoised** | 8.644 | 0.1351 | 60,405,044 |
| **1.2 fix** (bucket + union-find, `closure()` memoised) | 0.355 | 0.0056 | 2,098,740 |

**26x** for the correlated-groups mechanism alone (8.644s -> 0.355s), on top
of mechanism 1's fix. `closure()` memoisation is safe with **zero**
invalidation logic: a row's `basis` is set once at creation and the log is
append-only, so `closure(row_id)` for an existing id never changes.

**Fix** (`tools/omr/staged/adjudicate.py`, `Evidence.correlated_groups`):
bucket every `Observation` by `(reader, frame, quantity)` -- `_one_signal`'s
own first branch says two Observations sharing that key are ALWAYS one
signal, so the whole bucket can be unioned against its first member in O(n)
rather than compared pairwise. The remaining rows (`Verdict`/`Abstention`,
"others") still need the general closure-intersection test, but only
against each other (O(k^2)) and against **one representative per observation
bucket** (O(k*u), u = number of distinct buckets) rather than against every
individual observation -- sound because `_one_signal` does not special-case
which specific bucket member it is comparing against. Implemented as a
union-find with path compression. Also deliberately deduplicates `_seen`
first, which is a documented, tested behaviour change: the old code could,
given a duplicate id in `_seen`, append a spurious ONE-element "group" for a
row paired with itself -- never a real correlation, and inconsistent with
the docstring's own "one signal wearing two hats".

## Combined effect, no profiling overhead (`plain_timing.py`)

Whole 4-page record, both fixes applied, `time.perf_counter()` only (no
cProfile anywhere -- the numbers below are what a real run actually pays):

| stage | seconds |
|---|--:|
| rebuild (`Log` from saved observations/abstentions) | 1.301 |
| **ADJUDICATE** (29 decisions, 18,373 verdicts) | **29.854** |
| **GROUPS** (6 redundancy checks) | **1.945** |
| **EVALUATE** (6 consequence rules, 3,537 fired) | **13.386** |
| **INFER** (1 rule enabled by default) | **0.343** |
| **TOTAL, post-load** | **46.828** |
| + `load_record` (json parse) | ~0.8 |
| **grand total** | **~47.6s** |

Against the pre-fix state: a full profiled run of the pipeline before either
fix landed did not finish `arc_owner` (decision 17 of 29) within the first
~100 seconds of ADJUDICATE -- and the corresponding base-vs-arm control
(section below, same 12 cheap prerequisite decisions + `arc_owner`
restricted to one system, run over the SAME record) was run to **468
CPU-seconds (7m48s) and then killed, still not finished**, against the
fixed code's **16.461 seconds** for the identical subset. That is a
measured lower bound of **28x** (468 / 16.461) on the one number this
session could actually observe; the true ratio over the full 7-system,
29-decision run is almost certainly much larger, because
`correlated_groups()`'s O(n^2) walk grows with n^2 while `Q.GLYPH_BOX`
population (and therefore n) itself grows with document size.

## Per-decision table (profiled -- see caveat)

`benchmarks/omr-decide-stage-cost-2026-09/out/timings.json` is the full,
generated table (one row per decision/rule, `n` subjects, seconds,
seconds/subject); `SLOWEST.md` has the top-function `pstats` listing for the
three slowest. WARNING: these numbers carry cProfile's own per-call
instrumentation overhead on EVERY decision (a fresh `cProfile.Profile()`
wraps each one so the top-3 function breakdown can be attributed to a
specific decision), so the ADJUDICATE total there (47.961s) is higher than
the unprofiled 29.854s above -- use `timings.json` for RELATIVE ranking and
function attribution, `plain_timing.py`'s numbers for the real budget.

Slowest five (profiled numbers, for ranking only):

| stage | decision | n | seconds |
|---|---|--:|--:|
| adjudicate | arc_owner | 779 | 16.499 |
| evaluate | size_measure_rest | 1,183 | 9.957 |
| adjudicate | duration | 2,993 | 6.724 |
| evaluate | reconcile_duration | 1,183 | 4.625 |
| adjudicate | meter | 7 | 4.368 |

## A residual, second-order cost the fix does not remove -- named, not fixed

`size_measure_rest` (an EVALUATE consequence) and `adjudicate_duration` both
read `Q.DURATION` via `SELF_AND_DESCENDANTS`, and `size_measure_rest` itself
**revises** `Q.DURATION` verdicts as it walks 1,183 CELL subjects one at a
time. Each revision bumps `_quantity_version[Q.DURATION]`, which correctly
invalidates the per-quantity index -- but that means the index gets rebuilt
from scratch roughly **once per cell** rather than once for the whole rule,
because the write and the read interleave at fine granularity. Measured in
the `pstats` listing: `_descendants_index` for `Q.DURATION` alone accounts
for 6.631s of `size_measure_rest`'s 9.957s (profiled). This is *correct*
(nothing stale is ever served) and *bounded* (the rule still finishes in
under 10s, well inside budget), but it is not free, and it is the reason
`size_measure_rest`/`duration` remain the two next-slowest entries after
`arc_owner`. **Not fixed here** -- a safe fix would need incremental index
maintenance (append the new verdict's subject to the existing index rather
than rebuilding it) rather than the current full-rebuild-on-any-write
policy, and that is real design work this session's time budget did not
reach. Left as the next concrete target if `duration`/`size_measure_rest`
prove to matter on a larger (16-page) record -- `Q.GLYPH_BOX`-style
GATHER-only quantities (the `arc_owner`/`arc_kind` case, by far the largest
share of the pre-fix cost) are wholly fixed by this change and pay this cost
never.

## The control (base vs arm), and what it could and could not show

**Method**: `dump_verdicts_one_system.py` runs the 12 cheap prerequisite
decisions plus `arc_owner` (ORDER's first 13 entries) over the SAME saved
record, dumps `(subject, quantity, outcome, value, reason, sorted basis,
sorted considered)` for every verdict filed under system `system/1/0`, once
against `origin/main`'s `record.py`+`adjudicate.py` (all other files --
every adjudicator, `evaluate.py`, `groups.py`, `infer.py`,
`consequences.py`, `inferences.py` -- are this branch's own, unmodified by
1.2) and once against this branch's fixed versions.

**What ran**: the base run was launched, moved to a background task by
bash's own 120-second foreground timeout (it had not printed even its
first progress line, which the arm prints after 16.461s), and was left
running for a further several minutes. It reached **468 CPU-seconds
(7m48s)** without finishing and was then killed by this session -- the
arm's identical dump (`arm_system0.json`, 365 verdicts) had completed in
16.461s over three minutes earlier.

WHAT THIS DOES ESTABLISH: base is at least **28x** slower on the one subset
both could be asked to compute (468s of CPU time and still not done, against
the arm's 16.461s to a finished answer) -- a measured floor, not an
estimate, since the base process was killed still running.

WHAT THIS DOES NOT ESTABLISH, AND MUST NOT BE READ AS ESTABLISHED:
byte-identical verdict equality between base and arm over this specific
subset, because the base run did not finish inside this session's time
budget. `base_system0.json` may or may not exist in the tree depending on
whether the background task finished after this report was written -- check
its timestamp against `arm_system0.json`'s before trusting a diff between
them; if both exist, run:
`diff <(python3 -m json.tool out/base_system0.json) <(python3 -m json.tool out/arm_system0.json)`

What DOES establish correctness, and is not a compromise: two independent,
exhaustive-by-construction test suites, not a single frozen snapshot
comparison:

1. `test_staged_record.py::TestDescendantsCache` -- cache-hit counting
   (`_desc_result_builds`/`_desc_index_builds` do not increase on a repeated
   identical query), a write-after-cached-query visibility test (the literal
   "row filed by decision N is visible to decision N+1" requirement), a
   write-to-an-unrelated-quantity non-invalidation test, and an exact
   order-preserving equivalence check against a re-implementation of the
   pre-1.2 full-scan algorithm, run over every `(quantity, subject)` pair
   the log actually holds.
2. `test_staged_adjudicate.py::TestCorrelatedGroupsRewrite` -- four
   deterministic scenarios (shared-key bucketing, a dossier-derived pair
   correlating across a bucket, two verdicts with disjoint ancestry NOT
   correlating) plus a 25-trial randomised equivalence test against a
   deduplicated re-implementation of the pre-1.2 algorithm, covering random
   numbers of observation buckets, random verdict chains (some ancestry-
   linked, some not), and deliberate duplicate ids in `_seen` -- the exact
   shape `arc_owner`'s real `_seen` has (one huge bucket, a handful of
   verdicts, most of them independent of each other).

Both suites are part of `pytest -m "not slow"` (2,818 passed, 3 skipped,
unchanged pass/skip counts from before this branch plus the 29 new test
methods, 0 failures).

## What is NOT established

- **The 16-page whole-movement number.** Everything here is measured on the
  4-page, 7-system shared record. `correlated_groups()`'s O(n^2) term grows
  with the SQUARE of `Q.GLYPH_BOX` population per system, which itself grows
  with page count if systems get denser or if a 16-page movement's systems
  are comparable in size to this 4-page one's (700-1,540 glyphs/system) --
  in the worst case the fix's benefit is even larger there than measured
  here, but this was not run.
- **A byte-identical full-record control.** See above: the base run did not
  finish. The two randomised/property test suites are the correctness
  evidence this branch actually has; they test the MECHANISM (does the cache
  return what the old scan returned, does the rewritten grouping find the
  same connected components) rather than one frozen full-pipeline snapshot.
- **`OMR_DIRECTION_TEXT_SCAN_GATE` was already ON** for the acceptance
  script and is unrelated to this work; not re-measured here.
- **Print/accuracy**: nothing here touches what any decision decides. Every
  fix changes HOW OFTEN the same computation runs and HOW a set of already-
  fetched rows is grouped, never WHAT a decision reads or answers. No
  verdict's `value` can be affected by either fix; only `considered`/`basis`
  ordering-independent SETS and `correlated`'s connected components (proven
  as SETS, never claimed byte-identical in serialised order) could differ,
  and the property tests check exactly that.
- **The residual `Q.DURATION` interleaved-write cost** (see above) is named,
  measured, and left unfixed.
- **`groups.py`'s own `_signal_classes`** has an O(n^2) inner loop
  (`for i in range(len(rows)): for j in range(i+1, len(rows))`) that this
  session noticed but did not profile in isolation -- GROUPS took 1.945s
  total on this record (not a bottleneck here), so it was not chased, but a
  16-page record could expose it the same way `arc_owner` was exposed here.

## Corrected budget for `gather_movement.sh`

The script's existing estimate (before this session) covered GATHER only --
`~93 s/page` with the scan gate, `~93+267 s/page` without -- and said
nothing about ADJUDICATE/GROUPS/EVALUATE/INFER, which tonight's run showed
dwarfing GATHER by roughly **30x** (25 min vs 12.3 h) on 16 pages. This
session's own measurement is a single 4-page, 7-system data point (47.6s
post-GATHER, unprofiled) and cannot by itself supply a page-count exponent
-- extrapolating linearly from 4 pages/7 systems to 16 pages/~28 systems
would predict ~190s post-GATHER, which is three orders of magnitude below
the observed ~12.3 hours, so the true relationship on the UNFIXED code was
clearly superlinear (consistent with the O(n^2) mechanisms this session
found and fixed).

RECOMMENDATION, NOT YET VERIFIED: re-run
`benchmarks/acceptance/gather_movement.sh beethoven5-litolff --pages 0-17`
on this branch and measure the ADJUDICATE+GROUPS+EVALUATE+INFER wall time
directly, now that both O(n^2)-in-the-wrong-thing mechanisms are fixed.
Until that 16-page data point exists, `gather_movement.sh`'s budget
estimate should say explicitly that it covers GATHER only and that the
post-GATHER stages are unbounded pending that re-run -- this session did
not have time to also land that re-run and rewrite the estimate text, so
the script's budget-estimate block (its step 5) is UNCHANGED here; only the
clean-tree guard (coordinator addendum) was touched in that file.

## What the brief got wrong

- It named the cost shape as "several decisions are O(arcs x system
  glyphs)" -- true of `adjudicate_arc_owner`'s own body, but the actual
  measured dominant cost was `correlated_groups()`'s O(n^2) over `_seen`, a
  HARNESS mechanism (`Evidence`, in `adjudicate.py`) that runs on every
  decision's every subject regardless of what that decision's own code
  does -- 26x the remaining cost on `arc_owner` alone, and the brief's own
  conditional instruction ("leave it unless the profile makes it the
  dominant term, and then say so") is what licensed fixing it once
  measured.
- It suggested a cache "at the Evidence level ... for the duration of one
  decision over one system", i.e. per-decision-run scoped. The fix
  implemented here is scoped to the `Log`'s own lifetime, versioned per
  quantity -- strictly more general (it also benefits `_admit`'s
  circularity filter, GROUPS, and EVALUATE, all of which call the same
  `Log` methods) and does not need a decision-boundary hook at all, which
  is also why the requested "cache lifetime never crosses a decision
  boundary" test is reframed here as "a write to the quantity, whenever it
  happens, is visible to the next read of it" -- a strictly stronger and
  simpler invariant to state and to check.
