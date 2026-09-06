"""Is `staff_index` order the same as printed top-to-bottom order?

`compose.py` writes no staff dicts and therefore no `staff_geometry`, so
`score_2x2.py` reads a system's vertical order off `staff_index`. That is the
same thing `absent_instrument._anchored_keys` already does, but "already relied
on elsewhere" is not a measurement.

The absent-instrument branch's FULL transcription has both fields on every
staff, so the question can be answered outright rather than assumed: sort each
system's staves by `staff_index`, sort them by `staff_geometry.line_ys_page[0]`,
and compare. It also reports how many staves my `judgeable()` would score on
that file, which must be the 807 that branch scored.

Usage:  check_staff_order.py FULL-TRANSCRIPTION.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_2x2 import judgeable                              # noqa: E402


def main(path):
    d = json.load(open(path))
    systems = disagree = staves = 0
    keys = []
    for page in d.get("pages", []):
        pi = page.get("page_index")
        for sy in page.get("systems", []):
            si = sy.get("system_index")
            sts = sy.get("staves", [])
            if not sts:
                continue
            systems += 1
            staves += len(sts)
            by_index = [s["staff_index"] for s in
                        sorted(sts, key=lambda s: s["staff_index"])]
            by_y = [s["staff_index"] for s in
                    sorted(sts, key=lambda s: s.get("staff_geometry", {})
                           .get("line_ys_page", [0])[0])]
            if by_index != by_y:
                disagree += 1
            for s in sts:
                keys.append((pi, si, s["staff_index"]))
    print(f"=== {Path(path).name}")
    print(f"INPUT ASSERTION: systems={systems} staves={staves}")
    print(f"systems where staff_index order != printed y order: {disagree}")
    if disagree:
        print("  ⚠️ THE ORDERING ASSUMPTION IS WRONG. score_2x2 must not read "
              "a lineup off staff_index.")
    else:
        print("  staff_index IS printed top-to-bottom order, on every system "
              "of this document.")
    j = judgeable(keys)
    print(f"judgeable staves under score_2x2's rule: {len(j)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
