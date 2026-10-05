#!/usr/bin/env python3
"""lane-ledger-exclusion (2026-10-04): which detector boxes overlap / sit near
a head, and who owns them.  Diagnostic only.

    python3 benchmarks/omr-local-staff-2026-09/exclusion_diag.py [subject...]
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402

SUBJECTS = ["glyph/3/0/7/7/0", "glyph/3/0/7/4/3", "glyph/3/0/0/2/4"]


def main():
    subs = [a for a in sys.argv[1:] if a.startswith("glyph/")] or SUBJECTS
    heads = {}
    for d in ("beethoven5-litolff", "brahms1-breitkopf"):
        heads.update({h["subject"]: h for h in ec.load_heads(d)})
    for s in subs:
        h = heads[s]
        x0, y0, x1, y1 = h["box"]
        sp = (h["lines"][-1] - h["lines"][0]) / 4
        print(s, [round(v, 1) for v in h["box"]], "sp", round(sp, 1), "lines", [round(v) for v in h["lines"]])
        for sub, b in h["boxes"]:
            if sub == s:
                continue
            bx0, by0, bx1, by1 = b
            ox = max(0, min(x1, bx1) - max(x0, bx0))
            oy = max(0, min(y1, by1) - max(y0, by0))
            near = (abs((bx0 + bx1) / 2 - (x0 + x1) / 2) < 3 * sp
                    and abs((by0 + by1) / 2 - (y0 + y1) / 2) < 3 * sp)
            if (ox > 0 and oy > 0) or near:
                print("   ", sub, [round(v, 1) for v in b],
                      "overlap %.2f of subject" % (ox * oy / ((x1 - x0) * (y1 - y0))),
                      "centre", round((by0 + by1) / 2, 1))
        for sub, b in h["acc"]:
            bx0, by0, bx1, by1 = b
            if (abs((bx0 + bx1) / 2 - (x0 + x1) / 2) < 3 * sp
                    and abs((by0 + by1) / 2 - (y0 + y1) / 2) < 3 * sp):
                print("    ACC", sub, [round(v, 1) for v in b])


if __name__ == "__main__":
    main()
