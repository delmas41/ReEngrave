"""Slur/tie totals per work, one column per arm, against the truth.

The edit count alone cannot say whether a rule is RIGHT: musicdiff is symmetric,
so emitting fewer symbols is rewarded by the alignment even when the symbols
removed were real. This is the control for that — the arm that scores best must
also be the arm whose arc counts move TOWARD the truth's.
"""
from __future__ import annotations
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from tab import WORKS

FIX = ("/Users/seanjohnson/Desktop/ReEngrave/.claude/worktrees/sad-austin-7e16e7"
       "/benchmarks/omr-orchestral-e2e/fixtures")


def counts(path):
    root = ET.parse(path).getroot()
    s = sum(1 for x in root.iter("slur") if x.get("type") == "start")
    t = sum(1 for x in root.iter("tied") if x.get("type") == "start")
    return s, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--root", default=str(Path(__file__).parent))
    args = ap.parse_args()
    print(f"{'work':26s}" + "".join(f"{t:>16}" for t in args.tags) + f"{'TRUTH':>16}")
    tot = [[0, 0] for _ in args.tags]
    ttot = [0, 0]
    for w in WORKS:
        cells = ""
        for i, tag in enumerate(args.tags):
            p = Path(args.root) / f"pred-{tag}" / f"{w}.musicxml"
            if p.exists():
                s, t = counts(p)
                tot[i][0] += s
                tot[i][1] += t
                cells += f"{f'{s}s/{t}t':>16}"
            else:
                cells += f"{'-':>16}"
        s, t = counts(Path(FIX) / f"{w}.musicxml")
        ttot[0] += s
        ttot[1] += t
        print(f"{w:26s}{cells}{f'{s}s/{t}t':>16}")
    print(f"{'POOLED':26s}"
          + "".join(f"{f'{a}s/{b}t':>16}" for a, b in tot)
          + f"{f'{ttot[0]}s/{ttot[1]}t':>16}")


if __name__ == "__main__":
    main()
