# benchmarks/_archive

Mutation batteries archived under ROADMAP 0.4d (2026-10-07). Each script
keeps its original path below `benchmarks/`, so
`benchmarks/<name>/probe/mutate.py` is now
`benchmarks/_archive/<name>/probe/mutate.py`.

They were one-off proofs (CLAUDE.md §6c): the `FINDINGS.md` beside each
original directory stands as the record; the scripts are not maintained, are
not run by any test, and may import siblings (`probe/common.py`, the
`omr_ledger_extrapolation_shim`) that stayed where they were. No new ones are
written; `python3 -m tools.omr.staged.check` counts any that reappear outside
this directory.
