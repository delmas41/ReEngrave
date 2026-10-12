#!/usr/bin/env python3
"""l283_stem_tip_offset: where the CV rung's stem ENDS against where Sean's stem box ends, at the TIP end, for every truth stem the
CV rung found (matched by overlap), in local staff spaces (+ = the CV stem stops SHORT of his tip, toward the head). The tip reader
reads from the CV stem's end, so a stem the CV rung cut short has its flag below the place the reader looks. By label (flag / bare /
beam). ROADMAP 2.83 probe (stems are read here, not changed: CLAUDE.md fence).

    python3 l283_stem_tip_offset.py CELLS.pkl.gz
"""
import collections
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_common import cell_space, to_page  # noqa: E402
from l283_dataset import build  # noqa: E402


def main():
    T, cells, rows = build(sys.argv[1])
    res = collections.defaultdict(list)
    for r in rows:
        if r["cv"] is None or r["label"] == "trem":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        px0, py0, px1, py1 = to_page(c, x, y, w, h)
        sx0, sy0, sx1, sy1 = r["stem_rect"]
        sp_page = s / c["scale"]
        if r["tip_end"] == "top":
            off = (py0 - sy0) / sp_page          # CV top below his top = positive = stops short
        else:
            off = (sy1 - py1) / sp_page
        res[r["label"]].append(off)
    for lab in ("flag", "bare", "beam"):
        v = sorted(res[lab])
        if not v:
            continue
        short = sum(1 for x in v if x > 0.5)
        long_ = sum(1 for x in v if x < -0.5)
        print(f"{lab:5s} n={len(v)}  median {statistics.median(v):+.2f}  min {v[0]:+.2f}  max {v[-1]:+.2f}  "
              f"CV stem stops short of his tip by > 0.5 sp: {short}   runs past it by > 0.5 sp: {long_}")
        print("      ", [round(x, 2) for x in v])


if __name__ == "__main__":
    main()
