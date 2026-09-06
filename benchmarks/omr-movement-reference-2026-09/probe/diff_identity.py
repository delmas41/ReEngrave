"""Diff staff identity between two runs of the same pages.

Reports every (page, system, staff) whose emitted instrument changed, so a
controlled A/B can be read as "N staves changed, N fixed, N broken" rather than
as a net number that hides both directions.

`--truth` scores each change against the printed lineup where a system is FULL
(see `score_full_systems.py` for why a full system needs no page reading), so
"fixed" and "broken" are earned rather than assumed.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

from score_full_systems import LINEUPS, systems, truth_for


def identity(path):
    r = json.load(open(path))
    out = {}
    for page, sys_i, staves in systems(r):
        for i, st in enumerate(staves):
            out[(page, sys_i, i)] = st.get("instrument")
    return out, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--work", default=None, choices=sorted(LINEUPS))
    args = ap.parse_args()

    a, ra = identity(args.before)
    b, rb = identity(args.after)
    print(f"INPUT ASSERTION: before={len(a)} after={len(b)} staff records")
    if not a or not b:
        print("REFUSING: a run has no staff records")
        return
    if set(a) != set(b):
        print(f"⚠ the two runs disagree about which staves EXIST "
              f"({len(set(a) ^ set(b))} keys differ) — segmentation moved, "
              f"which this change cannot do; comparing the intersection only")

    ref_a = len((ra.get("contextual") or {}).get("reference") or [])
    ref_b = len((rb.get("contextual") or {}).get("reference") or [])
    print(f"reference slots: before={ref_a}  after={ref_b}")

    sizes = {}
    if args.work:
        for path in (args.before,):
            r = json.load(open(path))
            for page, sys_i, staves in systems(r):
                sizes[(page, sys_i)] = (len(staves),
                                        truth_for(args.work, page, len(staves)))

    changed = [k for k in sorted(set(a) & set(b)) if a[k] != b[k]]
    print(f"changed: {len(changed)} of {len(set(a) & set(b))}")

    fixed = broken = neutral = unscored = 0
    kinds = collections.Counter()
    for key in changed:
        page, sys_i, i = key
        names = sizes.get((page, sys_i), (None, None))[1] if args.work else None
        if names is None:
            unscored += 1
            kinds[(a[key], b[key], "?")] += 1
            continue
        want = names[i]
        if b[key] == want and a[key] != want:
            fixed += 1
            kinds[(a[key], b[key], "FIX")] += 1
        elif a[key] == want and b[key] != want:
            broken += 1
            kinds[(a[key], b[key], "BREAK")] += 1
        else:
            neutral += 1
            kinds[(a[key], b[key], "--")] += 1
    if args.work:
        print(f"  on FULL systems: fixed={fixed} broken={broken} "
              f"neutral={neutral}; on reduced systems (no truth): {unscored}")
    print("\nchanges (before -> after), most common first:")
    for (x, y, tag) in [k for k, _ in kinds.most_common(30)]:
        print(f"  {kinds[(x, y, tag)]:5d}  {tag:5s} {str(x):16s} -> {y}")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main()
