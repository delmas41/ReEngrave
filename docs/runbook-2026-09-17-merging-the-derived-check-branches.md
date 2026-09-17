# Merge runbook: the branches that add DERIVED CHECKS

**For a fresh session.** Two branches are unmerged and both add a derived
check or a new quantity. `git merge` reports **zero conflicts** on each — and
that is exactly why this runbook exists: **the conflicts are not textual.**

| branch | commits | what it adds |
|---|--:|---|
| `claude/family-position-facts` | 11 | `staged/positions.py` — 10 position quantities + 1 basis row, `OMR_FAMILY_POSITIONS`, default OFF |
| `claude/multi-membership-ink` | 3 | a clean NEGATIVE — no behaviour. Merge for the record, or leave it |

## ⚠️⚠️ THE PATTERN, OBSERVED NOT PREDICTED

Merging `claude/ink-memory-store` on 2026-09-17 produced **six test failures
neither branch could see**, and `git merge` reported no conflict. All six were
**RED ON SUCCESS** — the `capture` audit asserting gaps that the other branch
had CLOSED:

* a **new quantity** (`Q.DOCUMENT_IDENTITY`) that no table classified;
* a **KNOWN_GAPS entry gone STALE** (`CROSS-DOCUMENT`), because a closed gap
  must LEAVE the inventory and `--check` fails on one that lingers;
* a test asserting `publisher_in_gather_code == 0`, **true when written and
  false once the gap was closed**.

This is the same shape CLAUDE.md records from the day the last stub closed:
*eight assertions went red because the thing they asserted had been achieved,
and none was deleted.*

**`claude/family-position-facts` will do this again, harder** — it fills nine
of the eleven `POSITION <family> has no staff-grid position fact` entries that
`capture.KNOWN_GAPS` currently asserts. Expect roughly that many stale entries
plus ten unclassified quantities.

## THE PROCESS

```bash
git merge --no-edit origin/claude/family-position-facts      # expect: clean
for m in capture reach wiring inventory health; do
  printf "%-10s " $m; python3 -m tools.omr.staged.$m --check >/dev/null 2>&1; echo "exit=$?"
done
python3 -m pytest tools/omr/tests/ -q                        # the WHOLE suite
```

1. **Merge, then run all five derived checks.** A clean `git merge` means
   nothing. `--check` is the real merge test.
2. **Read each failure and decide which of three it is:**
   * **UNCLASSIFIED QUANTITY** — add it to the right table with a reason
     saying what KIND of fact it is. `Q.DOCUMENT_IDENTITY` was declared
     `NOT_A_MARK` because it is a catalog fact, not a measurement of ink.
   * **STALE GAP** — the other branch closed it. **Delete the entry.** A gap
     list that keeps closed entries stops describing the pipeline and starts
     describing its history.
   * **RED ON SUCCESS TEST** — an assertion that a gap EXISTS. **Rewrite it to
     the new contract; never delete it**, and make sure it still exercises the
     mechanism. `test_publisher_is_unreachable_in_gather` asserted `== 0` and
     became `assertGreater(..., 0)` — so the tool still has to FIND it.
3. **Full suite, and compare against a baseline you took yourself.** Targeted
   tests passing is not evidence: a fix "verified against its reproduction" is
   verified in ONE environment. Main was `4268 passed / 11 skipped / 0 failed`
   at `e38dbc25`; the position branch reports 4325 on its own base.
4. **Then push.**

## ⚠️ TWO TRAPS THAT COST TIME ON 2026-09-17

* **A worktree has no `.venv-surya`**, and before the conftest fix that meant
  **9 failures in every agent worktree** that nobody could reproduce in the
  main tree. Fixed structurally — but if you see surya failures, check
  `tools/omr/tests/conftest.py` survived the merge.
* **`git add -A` swept a 140 MB staged record into a commit** and GitHub
  rejected the push at its 100 MB limit. Records under
  `benchmarks/omr-positional-store-2026-09/out/` are now gitignored. **Add
  paths explicitly.**

## WHAT NOT TO CONCLUDE FROM THE MERGED TREE

⚠️ `A-INK-4`: the new position facts are wired to **no consumer**, deliberately.
So when anything asks *"do they help?"* the answer will be no — their partners
do not exist yet. **That is the expected result, not a verdict.** `Q.STEM` is
the near-miss: gathered and unread through THREE separate discoveries, worth
114 narrowed durations the day something finally read it.

⚠️ And a factor CONTRIBUTES, it does not decide. The p.62 case measured this:
the broken-barline fragments read as a real digit's height (4.16 / 4.34 steps),
so **geometry refuses nothing there**. Do not add a rule, veto or threshold
that uses a position to rule something out.
