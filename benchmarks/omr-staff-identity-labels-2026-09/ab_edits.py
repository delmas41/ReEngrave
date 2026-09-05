#!/usr/bin/env python3
"""Price the shared-block rule in OMR-NED edits, per row.

    python3 ab_edits.py OFF.json ON.json

Two `scan_eval.py` runs over the six rows the rule touches, on one tree,
differing only by `_surya_worker._assign`. Rows the rule does not touch are not
run: the label A/B already showed 396 of 407 staves unchanged, and running
fourteen unaffected rows twice would buy a pair of identical numbers at an
hour of CPU.

⚠️ THIS IS A SIX-ROW SUBSET AND ITS POOLED FIGURE IS NOT THE SCAN GATE.
The canonical 20-row baseline is `BASELINE_20ROW_2026-09-05.md`
(0.8444 / 74,968). Nothing here may be quoted against it — a pooled OMR-NED is
a property of the work set it is pooled over. The comparison that is valid is
OFF vs ON, row by row, on these six.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def rows(path):
    d = json.loads(Path(path).read_text())
    out = {}
    for r in d["rows"]:
        n = r["omr_ned"]
        rid = n["name"].rsplit(".", 1)[0]
        out[rid] = n
    return out, d["pooled"]


def main() -> int:
    a, pa = rows(sys.argv[1])
    b, pb = rows(sys.argv[2])
    print(f"{'row':34} {'OFF ned':>9} {'ON ned':>9} {'d ned':>8} "
          f"{'OFF ed':>8} {'ON ed':>8} {'d ed':>7}")
    for rid in sorted(set(a) | set(b)):
        x, y = a.get(rid), b.get(rid)
        if not x or not y:
            print(f"{rid:34}  MISSING ONE SIDE")
            continue
        print(f"{rid:34} {x['omr_ned']:>9.4f} {y['omr_ned']:>9.4f} "
              f"{y['omr_ned'] - x['omr_ned']:>+8.4f} "
              f"{x['omr_ed']:>8} {y['omr_ed']:>8} "
              f"{y['omr_ed'] - x['omr_ed']:>+7}")
    print()
    print(f"{'SUBSET POOLED (not the gate)':34} {pa['omr_ned']:>9.4f} "
          f"{pb['omr_ned']:>9.4f} {pb['omr_ned'] - pa['omr_ned']:>+8.4f} "
          f"{pa['omr_ed']:>8} {pb['omr_ed']:>8} "
          f"{pb['omr_ed'] - pa['omr_ed']:>+7}")
    print()
    cats = sorted(set(pa.get("categories", {})) | set(pb.get("categories", {})))
    print(f"{'category':32} {'OFF':>8} {'ON':>8} {'delta':>7}")
    for c in cats:
        x = pa.get("categories", {}).get(c, 0)
        y = pb.get("categories", {}).get(c, 0)
        if x != y:
            print(f"{c:32} {x:>8} {y:>8} {y - x:>+7}")
    print()
    print(f"symbols: OFF pred {pa['pred_symbols']} truth {pa['truth_symbols']}"
          f" | ON pred {pb['pred_symbols']} truth {pb['truth_symbols']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
