# Probe hygiene — the audit's own instruments, fixed

**Fix agent C, 2026-09-07.** Closes `VERIFICATION.md` §M4 and §D16. No file under
`tools/omr/` was touched. Every committed figure in this directory is unchanged —
verified per probe, not assumed — **with one exception that is a finding and is
reported rather than committed** (§4).

---

## 1 · What was wrong

Not the paths. **The paths were a symptom; the bug was that a probe which looked
in the wrong place was indistinguishable from a probe that found nothing.**

Two mirror-image forms, introduced by two different agents in two rounds, the
second *after* the first had been written down:

| | form | what it does when wrong |
|---|---|---|
| **round 1** (6 probes) | `ROOT="/Users/seanjohnson/Desktop/ReEngrave"` committed *into the audit tree* | silently measures a **different tree** the moment the trees diverge |
| **round 2** (7 probes) | bare `glob.glob('benchmarks/…')`, CWD-relative | prints a clean all-zero table and **exits 0** |

Round 2 is the worse of the two, and it is worth being precise about why. This is
what `probe_meter_guard_reach.py` printed from this worktree before the fix:

```
=== scan: 0 pages, 0 measures
   uncorroborated meter changes REVERTED: 0
   measures carrying rhythm_sum_warning: 0 (0.0%)  severity {}
exit=0
```

That is not a null result. It is a **believable wrong answer** — *"the guard
never fired, and no measure anywhere fails its bar-sum"* — with nothing in the
output, the exit code, or the shape of the table to suggest otherwise. The true
figures are 21 reversions and 111 warned measures. The verifier hit the same
thing in its own `verify_r4_units.py` and only noticed by accident.

It is the same **"an abstention and a failure look alike"** fault Agent II
diagnoses for `_assign` in §R1.4 — here installed in the measuring instrument
instead of in the pipeline.

⚠️ **The obvious fix is wrong, and VERIFICATION.md withdraws it as glib.**
"Make the paths relative" cannot work: `benchmarks/*/fixtures/` is gitignored and
exists *only* in the main checkout.

---

## 2 · The fix: two roots, and a refusal

`probe/fixture_root.py`, written once and used everywhere.

### Two roots, because the artefacts differ in kind

The single-root version of this fix is also wrong, and it is the half a reviewer
is most likely to wave through:

| helper | reads | resolution |
|---|---|---|
| `repo_root()` / `repo_glob()` | **committed** artefacts — `out/contests/`, `results*.json`, `verdicts/`, `current-accuracy.json` | `Path(__file__).parents[3]` — the tree the probe **lives in** |
| `fixture_root()` / `fixture_glob()` | **gitignored** build products — `fixtures/`, `library/` | `OMR_FIXTURE_ROOT` → git → built-in |

Routing a *committed* artefact through `OMR_FIXTURE_ROOT` would re-introduce M4
by a new door: the probe would read another checkout's committed data while
shipping in this one. `probe_ownership_reach.py` needs both in the same file, and
now uses both.

### `fixture_root()` resolution order

1. **`OMR_FIXTURE_ROOT`** — explicit. If set but absent, exit 2 immediately;
   a named root that does not exist is never quietly ignored.
2. **`git rev-parse --path-format=absolute --git-common-dir`** — a linked
   worktree's common dir is the *main checkout's* `.git`, so this finds the main
   checkout from inside a worktree. The same move `library_root()` already makes.
   **Derived beats spelled out**: it survives a clone and cannot drift from the
   tree it names.
3. **built-in default** — last resort only.

**The root and how it was chosen are announced on stderr on every run**, because
the whole family of bugs is "the probe read a tree nobody named":

```
[fixture_root] /Users/seanjohnson/Desktop/ReEngrave  via git --git-common-dir (⚠️ NOT the tree this probe lives in)
```

### The half that actually closes the bug

`must_glob` / `fixture_glob` / `repo_glob` **exit 2 on an empty match**, naming
the absolute pattern tried and how the root was chosen.

⚠️ **Everything this module prints goes to stderr.** The committed `out/*.txt`
are stdout captures; a hygiene fix that moves a measured number is a bug.

---

## 3 · Proof

### It fails loudly

```
$ OMR_FIXTURE_ROOT=$PWD python3 probe/probe_meter_guard_reach.py     # a tree with no fixtures
[fixture_root] …/worktrees/fix-probe-hygiene  via OMR_FIXTURE_ROOT (same tree as this probe)

NO SCAN TRANSCRIPTIONS FOUND — refusing to report a number computed over nothing.
  pattern : …/worktrees/fix-probe-hygiene/benchmarks/omr-scan-e2e-2026-09/fixtures/*..graft09.omr.json
  root    : …/worktrees/fix-probe-hygiene   (chosen via OMR_FIXTURE_ROOT)
  ⚠️ This is the failure this guard exists for: without it the probe
     would print a clean all-zero table and exit 0, and an empty glob
     would be indistinguishable from a genuine negative result.
  OMR_FIXTURE_ROOT is set and points somewhere real, but holds no such files.

EXIT=2
```

**stdout is zero bytes.** A redirected capture is now an empty file, not a
plausible table — which is the property that matters, because the old failure
was survivable precisely because its output *looked finished*.

### It reproduces every committed number

| set | n | result |
|---|--:|---|
| probes with a committed `out/*.txt` | 14 | **byte-identical** |
| `probe/verify/*.py` | 4 | **byte-identical** |
| probes writing a committed `*.json` | 5 | **byte-identical** |
| `build_metric_registry.py` → `metric-registry.json` | 1 | **byte-identical** |

…and now identical **from any cwd**: re-run from `/` and from this worktree, both
14/14. Six of the fourteen previously printed zeros from here.

Two probes are heavy (`probe_beam_bar_positions` needs `library/` + OpenCV;
`probe_structural_floor` needs `.venv-omrned`) and were **not** re-run. Their
change is a constant substitution — `Path(literal)` → `env_path(VAR, literal)` —
proved equivalent by evaluating both constants with no env set, without invoking
either `main()`. `probe_structural_floor`'s pin to the `reconciliation` worktree
is **deliberate** (it sha256-checks those fixtures against the canonical arm) and
is preserved; making it nameable does not loosen it.

### The checker is not vacuous

`probe/check_probe_hygiene.py` — a source scan, no fixtures needed, so it runs in
the environment the defects hide in. Three rules, each mapped to an observed
failure rather than to a style preference (R1 hard-coded checkout, R2
CWD-relative glob, R3 unguarded glob).

Green on the current tree; **each rule was then run RED** by reintroducing the
exact defect it targets, and green again on restore. A prose warning did not stop
the second instance of this bug; a check that fails does.

---

## 4 · ⚠️ ONE NUMBER MOVED, AND IT IS NOT MY CHANGE — REPORTED, NOT COMMITTED

`measurement-hygiene.json` regenerates as **69** result artefacts on this branch
against the committed **68**; `with_commit` 26 → 27, `with_era` 55 → 56.

**Cause — fully accounted for, exactly one file:**

```
only in MY tree   : benchmarks/omr-page-normalise-fixes-2026-09/results-normalised-arm-19of20.json
only in AUDIT tree: (none)
```

That file is committed at `833afe9f`, an ancestor of this branch's base
`974971e3`, and **does not exist on `claude/pipeline-audit-opus-agents-0eb4b1`**.
`probe_measurement_hygiene.py` is byte-unmodified by this work (its only change
is the R3 guard, proved a no-op below). So the delta is a **tree difference**,
not a regression, and the committed artefact has been **restored to 68**.

⚠️ **The finding underneath it is worth more than the number.** This probe was
one of the `parents[3]` probes VERIFICATION.md calls *"immune"* — and it is
immune to reading the *wrong* tree. But its output **is a census of the tree it
runs in**, so its figure is only meaningful for the commit it was taken at, and
nothing in the artefact records which commit that was. That is §A1's own
complaint — *"scan_eval.py writes no commit and no machine-checked era"* —
reproduced inside the audit's own hygiene probe, by the probe whose subject is
missing provenance stamps.

**Proposed, not done** (it would mean committing over the audit's figure): stamp
`git rev-parse HEAD` of `repo_root()` into `measurement-hygiene.json`, and have
the registry treat an unstamped census the way `accuracy_record.check()` treats
an unstamped record. A coordinator decision, not a 2 a.m. one.

### A second, smaller thing the re-run caught — in my own fix

Converting that probe's `rglob` to `must_glob` silently changed 69 → **48**:
`glob.glob` needs `recursive=True` for `**` to cross directories, and `rglob`
implies it. The wrong number was entirely plausible. Fixed in `must_glob`
(no-op for patterns without `**`), and the guard then verified byte-identical to
the pre-guard run **on the same tree** — which is the only comparison that
isolates the guard from the tree difference above.

*Recorded because it is the same failure shape as the bug being fixed: a wrong
answer that looked like a right one, caught only by re-running rather than by
reading the diff.*

---

## 5 · Inventory

**New** — `probe/fixture_root.py`, `probe/check_probe_hygiene.py`

**Converted, committed output re-verified identical** (18)

- CWD-relative → `fixture_glob` (7): `probe_direction_funnel`,
  `probe_direction_refusals`, `probe_label_reader_tiers`, `probe_meter_changes`,
  `probe_meter_guard_reach`, `probe_stitch_refusal_reach`,
  `probe_tie_pairing_replay`
- hard-coded root → `fixture_glob`/`repo_glob` (6): `probe_clef_argmax_contests`,
  `probe_clef_midstaff_flips`, `probe_clef_winner_confidence`,
  `probe_ownership_reach`, `probe_ownership_reversibility`,
  `probe_unladdered_threshold_neighbourhood`
- had the env escape, gained the empty-glob refusal (1): `probe_clef_ladder_reach`
- unguarded glob → guarded (3): `probe_retro_stamp`,
  `probe_input_ceiling_from_labels`, `probe_measurement_hygiene`
- `verify/` (4): `verify_436`, `verify_ladder_q3_q4`, `verify_r1_r2_tier2`,
  `verify_r4_units`

**Constant substitution, equivalence proved without a re-run** (2):
`probe_beam_bar_positions` (`OMR_LIBRARY_ROOT`, `OMR_ENGRAVED_FIXTURES`),
`probe_structural_floor` (`OMR_RECONCILIATION_FIXTURES`)

**Left alone**: `probe_contest_class_disagreement` already fails on an empty
glob with its own guard, which R3 accepts. A working guard is not worth churning.

```bash
python3 benchmarks/omr-pipeline-audit-2026-09/probe/check_probe_hygiene.py   # 0 = clean
python3 benchmarks/omr-pipeline-audit-2026-09/probe/fixture_root.py          # what this tree resolves to
```
