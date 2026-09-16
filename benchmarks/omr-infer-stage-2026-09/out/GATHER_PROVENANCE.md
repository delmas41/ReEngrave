# ⚠️ THE RECORD'S OWN `provenance` STAMP IS MISLEADING, AND HERE IS WHY

`staged/__main__.py` calls `_provenance()` **after** `run_staged` returns, so
the stamp names the tree **at the END of the run**, not the tree that RAN.
Every module this run executes was imported at process start and keeps that
code for the life of the process (CLAUDE.md records this as the second of
"three facts about that one import order"). So:

| | |
|---|---|
| tree that **ran** | `ce7b8ba7`, **clean** |
| what the stamp will say | a later commit, `dirty: true` |

**The evidence that the run started on a clean `ce7b8ba7`, in order:**

1. `git status --porcelain` printed nothing immediately before launch.
2. The gather launched at **2026-09-16T03:19:07Z** (`gather-p1-p4.timing`).
3. The first file of this branch was written afterwards; `git log` on
   `claude/infer-stage` shows every commit dated after that timestamp.

⚠️ This is a THIRD instance of the import-order hazard, in a new direction:
not *"an edit mid-run reaches the exporter"* and not *"an edit mid-run does
not reach an imported module"*, but **the stamp reports neither**. A consumer
that trusts `provenance` on this record would attribute the gather to code
that did not produce it.

It does not affect any A/B here: both arms are produced by `reinfer.py` from
THIS ONE record, so the gather tree cancels exactly. It would matter to anyone
comparing this record with another.
