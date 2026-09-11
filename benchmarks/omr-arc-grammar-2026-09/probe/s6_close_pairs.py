"""Name the pairs S6 could act on, rather than counting them.

*Counting cannot see a relocation; only naming the notes can.* The same rule
applies here: a table of 42 "stacked pairs" says nothing about whether any of
them is the configuration Sean describes. This prints each one with its
geometry, its two kinds, what each binds, and where on the page it is, so a
session holding the print can adjudicate it.
"""
from __future__ import annotations

import argparse
import sys

sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09")
sys.path.insert(0, "benchmarks/omr-arc-grammar-2026-09/probe")
from s6_stacks import run  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("record")
    ap.add_argument("--max-gap", type=float, default=1.0)
    a = ap.parse_args()
    r = run(a.record)
    close = [p for p in r["pairs"] if (p["gap_spaces"] or 99) <= a.max_gap]
    close.sort(key=lambda p: (p["where"], p["gap_spaces"]))
    print(f"{'where':22s} {'gap':>6s} {'xov':>5s} {'iou':>5s}  "
          f"{'lower':>5s}/{'binds':<5s} {'upper':>5s}/{'binds':<5s}")
    for p in close:
        print(f"{p['where']:22s} {p['gap_spaces']:6.2f} "
              f"{p['x_overlap_frac']:5.2f} {p['iou']:5.2f}  "
              f"{p['lower_kind']:>5s}/{p['lower_binds']:<5d} "
              f"{p['upper_kind']:>5s}/{p['upper_binds']:<5d}")
    both = [p for p in close if p["lower_binds"] >= 2 and p["upper_binds"] >= 2]
    print(f"\n{len(close)} pairs; {len(both)} where BOTH arcs bind two heads "
          f"(the only ones S6 could change anything about)")
    same_kind = sum(1 for p in close if p["lower_kind"] == p["upper_kind"])
    print(f"{same_kind} of {len(close)} pairs are the SAME kind on both arcs")


if __name__ == "__main__":
    main()
