#!/usr/bin/env python3
"""lane-ledger-exclusion: exactly which (box, rows) the one-sided rule keeps
for one head, and the jut geometry the test saw.

    python3 exclusion_one_rows.py SUBJECT
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
import score_exclusion as se  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402

KEPT = {}
_orig = lg._thin_flat_one_sided_jut


def _spy(ink, x0, yy0, img_gray, thr, abs_y, tx0, tx1, spacing):
    r = _orig(ink, x0, yy0, img_gray, thr, abs_y, tx0, tx1, spacing)
    if r:
        KEPT.setdefault((tx0, tx1), set()).add(abs_y)
    return r


def main():
    lg._thin_flat_one_sided_jut = _spy
    s = sys.argv[1]
    doc = "brahms1-breitkopf" if s.startswith("glyph/1/") else "beethoven5-litolff"
    h = {x["subject"]: x for x in ec.load_heads(doc)}[s]
    pos, why = se.read(h, **se.RULES["one"], connected_continuation=True)
    print(s, pos, h["truth"])
    for k, v in sorted(KEPT.items()):
        v = sorted(v)
        print("  box x", k, "rows", v)
    boxes = {b: sub for sub, b in h["boxes"]}
    for sub, b in h["boxes"] + h["acc"]:
        if (int(b[0]), int(b[2]) + 1) in KEPT:
            print("  ", sub, [round(v, 1) for v in b])


if __name__ == "__main__":
    main()
