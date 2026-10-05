#!/usr/bin/env python3
"""lane-ledger-exclusion: ASCII dump of the thresholded page around a head.

    python3 exclusion_ascii.py SUBJECT x0 x1 y0 y1
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import edge_census as ec  # noqa: E402
from tools.omr.annotate import ledger_grid as lg  # noqa: E402


def main():
    s = sys.argv[1]
    X0, X1, Y0, Y1 = (int(v) for v in sys.argv[2:6])
    doc = "brahms1-breitkopf" if s.startswith("glyph/1/") else "beethoven5-litolff"
    h = {h["subject"]: h for h in ec.load_heads(doc)}[s]
    g = h["gray"]
    win = g[Y0:Y1, X0:X1]
    thr = lg._otsu_threshold(win)
    bx0, by0, bx1, by1 = h["box"]
    print("thr", thr, "box", [round(v, 1) for v in h["box"]])
    print("     " + "".join(str((X0 + i) // 10 % 10) if (X0 + i) % 10 == 0 else " " for i in range(X1 - X0)))
    for y in range(Y0, Y1):
        row = "".join("#" if g[y, x] <= thr else "." for x in range(X0, X1))
        mark = ">" if by0 <= y <= by1 else " "
        print(f"{y:4d}{mark}{row}")


if __name__ == "__main__":
    main()
