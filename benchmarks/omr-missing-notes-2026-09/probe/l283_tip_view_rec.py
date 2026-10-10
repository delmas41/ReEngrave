#!/usr/bin/env python3
"""l283_tip_view_rec: the erased cell raster around the TIP of given heads of a record (the pixels the reader sees), cells matched
to the cache of `l283_cells.py` by their CV stems, tip row red, 0.5-space ticks green. ROADMAP 2.83 probe.

    python3 l283_tip_view_rec.py --record rec.json --cells cells_pN.pkl.gz --out m.png key [key ...]
"""
import argparse
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l283_common import cell_space, load_cells  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402


def sig(stems):
    return tuple(sorted((round(x), round(y), round(w), round(h)) for x, y, w, h in stems))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=0.8)
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    cache = collections.defaultdict(list)
    for k, c in load_cells(a.cells).items():
        if c["stems"]:
            cache[sig(c["stems"])].append(c)
    tiles = []
    for key in a.keys:
        g = run.glyphs[key]
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        stems = [tuple(o["value"]) for o in run.obs_at(g.cell_key, Q.STEM)]
        m = cache.get(sig(stems))
        if not (hs and hs["outcome"] == "decided" and sd and sd["outcome"] == "decided" and m and len(m) == 1):
            print(key, "not drawable")
            continue
        c = m[0]
        s = cell_space(c)
        x, y, w, h = next(o["value"] for o in run.obs_at(g.cell_key, Q.STEM) if o["id"] == hs["value"])
        sign = 1.0 if sd["value"] == "up" else -1.0
        tip_y = y if sign > 0 else y + h
        x0, x1 = int(x - 1.0 * s), int(x + w + 2.6 * s)
        ya, yb = sorted((tip_y - sign * 0.6 * s, tip_y + sign * 4.2 * s))
        ya, yb, x0 = max(0, int(ya)), int(yb), max(0, x0)
        sub = np.where(c["img"][ya:yb, x0:x1], 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
        ty = int(tip_y - ya)
        cv2.line(rgb, (0, ty), (rgb.shape[1] - 1, ty), (0, 0, 255), 1)
        for k in range(1, 9):
            yy = int(ty + sign * k * 0.5 * s)
            if 0 <= yy < rgb.shape[0]:
                cv2.line(rgb, (0, yy), (10, yy), (0, 160, 0), 1)
        rgb = cv2.resize(rgb, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
        tiles.append(cv2.copyMakeBorder(rgb, 0, 0, 0, 5, cv2.BORDER_CONSTANT, value=(0, 200, 0)))
    H = max(t.shape[0] for t in tiles)
    cv2.imwrite(a.out, np.concatenate([cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles], axis=1))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
