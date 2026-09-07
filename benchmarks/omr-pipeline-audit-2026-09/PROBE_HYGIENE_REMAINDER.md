# Probe hygiene — the remainder, after deferring to `_fixtures.py`

**Fix agent C, 2026-09-07.** Most of what this agent was commissioned to build
**already existed on `main` by the time it looked**, and has been withdrawn
rather than shipped a second time. What follows is only the part that was
genuinely uncovered.

---

## 0 · What was withdrawn, and why

This agent was briefed against `main` at `974971e3` and built, in good faith:

| built | superseded by | disposition |
|---|---|---|
| `probe/fixture_root.py` + 23 probe conversions | `probe/_fixtures.py` (19 importers) and `probe/_fixtureroot.py` | **withdrawn** |
| `probe/check_probe_hygiene.py` (AST lint) | `probe/test_probe_hygiene.py` (pytest lint, mutation-tested) | **withdrawn** |
| `tools/dashboard/registry_report.py` (registry renderer) | `tools/dashboard/registry_report.py` **already on main**, 1067 lines, handling `mandatory_caption` generically | **withdrawn** |

The commissioned renderer is the sharper loss and worth naming precisely: this
agent's version hard-coded the ledger-zone pair as a `SHOWCASE` constant, which
is exactly the defect main's version records itself as having superseded — *"read
the one pair described to it in prose and never read `mandatory_caption`."* A
third renderer would have re-introduced a fault already fixed.

The superseded work is preserved on **`claude/fix-probe-hygiene-superseded`**
(`c7bf60a2`) rather than deleted, because two of its findings survive (§2) and
because a reviewer may want to compare the two-root idea against the incumbent.

⚠️ **The general lesson is one this repo already has written down** — CLAUDE.md's
own instruction, from the duplicated hairpin export: *"`git log --all --oneline
-S "<the thing>" -- tools/omr/` before building anything."* Checking `main`
rather than the branch point would have caught all three in a minute. **A brief
is a snapshot; the tree is the fact.**

---

## 1 · What was actually uncovered, and is now fixed

### ⚠️ THE LINT HAD THE SHAPE OF THE BUG IT LINTS FOR

`test_probe_hygiene.py:probe_files()` was `HERE.glob("*.py")` — **non-recursive**.
So `probe/verify/` was **never linted**, and all four files in it carried the
exact defects the module exists to catch:

| file | defect |
|---|---|
| `verify_ladder_q3_q4.py` | `ROOT = Path("/Users/seanjohnson/Desktop/ReEngrave")` |
| `verify_r1_r2_tier2.py` | `R = "/Users/seanjohnson/Desktop/ReEngrave/"` |
| `verify_r4_units.py` | `ROOT = Path("/Users/…")` |
| `verify_436.py` | CWD-relative glob |

The lint looked in one place, found a clean set, and reported success — which is
precisely the failure it is written against, one level up. It did not *fail*; it
silently shrank its own reach, and 56 green tests said nothing about four files.

All four now use `_fixtures.py` and **reproduce byte-identically** against
baselines captured from `main` before the change — now from the worktree, where
three of them previously read the *other* checkout.

**Two new tests, each mutation-proved red:**

- `test_the_lint_descends_into_subdirectories` — pins the blind spot. Put
  `HERE.glob` back and it fails.
- `test_no_probe_hard_codes_a_checkout` — the mirror defect at probe level. The
  incumbent `test_no_probe_resolves_its_inputs_from_the_cwd` catches only the CWD
  half; a probe pinned to `/Users/<someone>/…` does not glob nothing, it globs
  **another tree**. All four verify files passed every existing test while
  carrying it.

⚠️ **That rule caught two things that turned out to be MY rule's fault, not
defects**, and both were checked before touching anything:
`probe_sauvola_dpi_scale.py` reaches `OMR_FIXTURE_ROOT` *inside*
`_fixtureroot.fixture_root()`, so a line-local test was wrong and the rule now
asks the file; and my own explanatory comment contained the substring `.glob(`,
which tripped the incumbent token heuristic. Neither probe was modified.

### `probe_direction_share.py` globbed raw while importing the guard

It imports `fixtures` for `chdir_root()` only, then globs with bare
`glob.glob(...)`. The incumbent lint's `GUARD_TOKENS` heuristic sees the string
`"fixtures("` in the import line and passes the file — **a false negative of the
token approach**, and the reason the AST-based check is worth keeping in mind
even though the pytest lint is the survivor. Now routed through `fixtures(...,
expect_at_least=11)`; output byte-identical.

### `_fixtures.fixtures()` silently degraded `**` — closed defensively

`glob.glob` needs `recursive=True` for `**` to cross more than one directory;
without it `**` behaves like `*`. **Latent today** — no pattern currently routed
through `fixtures()` nests deeper than one level, verified — but
`probe_direction_share` is exactly the kind of caller that passes one, and the
failure is not loud. One word, no-op for every pattern in use, verified by
re-running.

⚠️ **This cost a real number when it was hit elsewhere in this work**:
`benchmarks/**/*.json` read **48** artefacts instead of 69, and 48 was entirely
plausible. Found by re-running, not by reading the diff.

---

## 2 · A FINDING THAT IS NOT A FIX — `measurement-hygiene.json` is a census with
no commit

While re-running the audit's probes on this branch, `measurement-hygiene.json`
regenerated as **69** result artefacts against the committed **68**;
`with_commit` 26 → 27, `with_era` 55 → 56. Fully accounted for by exactly one
file:

```
only in this branch : benchmarks/omr-page-normalise-fixes-2026-09/results-normalised-arm-19of20.json
only in audit branch: (none)
```

Committed at `833afe9f`; absent from `claude/pipeline-audit-opus-agents-0eb4b1`.
`probe_measurement_hygiene.py` was byte-unmodified. **A tree difference, not a
regression** — reported here rather than committed over.

⚠️ **The finding underneath the number is the useful part.** That probe is one of
the `parents[3]` probes VERIFICATION.md §M4 calls *"immune"*, and it is immune to
reading the **wrong** tree. But its output **is a census of the tree it runs in**,
so its figure is only meaningful for the commit it was taken at — and nothing in
the artefact records which commit that was. That is §A1's own complaint —
*"`scan_eval.py` writes no commit and no machine-checked era"* — reproduced inside
the audit's own probe, **the one whose subject is missing provenance stamps.**

**Proposed, not done**, because it means committing over the audit's own figure:
stamp `git rev-parse HEAD` into `measurement-hygiene.json`, and have the registry
treat an unstamped census the way `accuracy_record.check()` treats an unstamped
record. A coordinator decision.

---

## 3 · A review note on `_fixtures.py`, offered not applied

`_fixtures.CONTESTS` points at
`benchmarks/omr-additive-vs-gated-2026-09/out/contests/*.contests.json`, which is
a **committed** artefact, and routes it through `root()` — i.e. through
`OMR_FIXTURE_ROOT`, defaulting to the main checkout.

For gitignored fixtures that is exactly right. For a committed artefact it means
a probe shipping in tree A reads tree B's copy of a file tree A also has — which
is M4 arriving by a new door, and it is invisible while the trees agree (they are
byte-identical today; I diffed them). The distinction the withdrawn
`fixture_root.py` drew was `repo_root()` for committed artefacts vs
`fixture_root()` for gitignored ones.

**Not applied** — the coordinator's instruction was to defer to `_fixtures.py`
rather than converge everyone onto a third API tonight, and this would change
what 19 importers read. Recorded for whoever owns that file.

---

## 4 · Verification summary

| set | result |
|---|---|
| `out/*.txt` with a matching probe (18) | **17 identical**, 1 pre-existing trailing-newline diff in `probe_clef_ladder_reach` — **attributed by re-running pristine `main` as a control**, not mine |
| `probe/verify/*.py` (4) | **byte-identical** to baselines captured from `main`, now from the worktree |
| `probe_direction_share.py` | **byte-identical** |
| committed `*.json` / `*.txt` artefacts | **none modified** — only `.py` files touched |
| `test_probe_hygiene.py` | **103 passed, 36 skipped**; both new tests mutation-proved red |
