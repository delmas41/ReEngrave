"""TWO FULL RE-GATHERS ON ONE TREE — pricing the GATHER half of 3.4g-3.

    python3 .../gather_ledger_ink_ab.py --arm base -- <staged CLI args>
    python3 .../gather_ledger_ink_ab.py --arm arm  -- <staged CLI args>

A GATHER change is invisible to `readjudicate` (CLAUDE.md §4d, §6b), so the
price is two full gathers. Both run THIS tree's `python3 -m tools.omr.staged`
(`__main__.main`), so the provenance stamp names one commit:

  ARM   the tree as committed: `gather_ledger_ink` files `Q.LEDGER_INK_UNDER`
        and the ledger decision reads it.
  BASE  the same process with exactly the two 3.4g-3 changes undone:
        `gather.gather_ledger_ink` replaced by a no-op (no row filed) and the
        ledger decision swapped for 3.4g-2's, loaded from `--base-ref`
        (`8226aa93`), exactly as `readjudicate_ledger_g2.load_base_fn` does.

⚠️ The detector is re-run in both, so run-to-run jitter is IN the diff; the
report names every moved verdict so a jittered box reads as one.
"""
from __future__ import annotations

import argparse
import dataclasses
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "probe"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=("base", "arm"), required=True)
    ap.add_argument("--base-ref", default="8226aa93")
    ap.add_argument("rest", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    rest = a.rest[1:] if a.rest[:1] == ["--"] else a.rest

    from tools.omr.staged import adjudicate, gather
    from tools.omr.staged import adjudicators  # noqa: F401  registers them
    from tools.omr.staged.record import Q
    from tools.omr.staged.__main__ import main as cli_main

    if a.arm == "base":
        from readjudicate_ledger_g2 import load_base_fn
        gather.gather_ledger_ink = lambda *_a, **_k: None
        spec = adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER]
        adjudicate.REGISTRY[Q.LEDGER_IS_NOT_A_LEDGER] = dataclasses.replace(
            spec, fn=load_base_fn(a.base_ref))
        print(f"BASE: gather_ledger_ink disabled, ledger decision from "
              f"{a.base_ref}", flush=True)
    else:
        print("ARM: this tree", flush=True)
    return cli_main(rest)


if __name__ == "__main__":
    raise SystemExit(main())
