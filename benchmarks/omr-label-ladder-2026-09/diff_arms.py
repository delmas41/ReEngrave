"""Diff two scan_eval result files row by row.

A pooled figure that does not move is two different claims -- "the change does
not reach the metric" and "the change never ran" -- and only the per-row diff
plus a positive control can tell them apart.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NOISE = {"seconds", "elapsed_s", "duration_s", "wall_s", "timestamp"}


def rows(doc):
    return doc["rows"] if isinstance(doc, dict) and "rows" in doc else doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    args = ap.parse_args()

    da, db = (json.loads(Path(p).read_text()) for p in (args.a, args.b))
    ra, rb = rows(da), rows(db)
    print(f"{len(ra)} vs {len(rb)} rows")
    same = diff = 0
    for x, y in zip(ra, rb):
        kx = {k: v for k, v in x.items() if k not in NOISE}
        ky = {k: v for k, v in y.items() if k not in NOISE}
        if kx == ky:
            same += 1
            continue
        diff += 1
        print(f"DIFFERS: {x.get('row_id')}")
        for k in sorted(set(kx) | set(ky)):
            if kx.get(k) != ky.get(k):
                print(f"    {k}: {kx.get(k)!r} -> {ky.get(k)!r}")
    print(f"\nrows identical: {same}   differing: {diff}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
