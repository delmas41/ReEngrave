#!/usr/bin/env python3
"""l283_frag_exp: the connected components of the ink in a stem tip's window (no closing), with each one's bounding box in (t, u)
spaces from the tip / from the stem's right edge, its area, whether it touches the stem, and the smallest gap (spaces) to the
stem-attached component -- to see WHY a flag the eye reads is not one component. ROADMAP 2.83 probe.

    python3 l283_frag_exp.py --record rec.json --cells cells.pkl.gz key [key ...]
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
    ap.add_argument("keys", nargs="+")
    a = ap.parse_args()
    run = RD.load_run(a.record)
    cache = collections.defaultdict(list)
    for k, c in load_cells(a.cells).items():
        if c["stems"]:
            cache[sig(c["stems"])].append(c)
    for key in a.keys:
        g = run.glyphs[key]
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        stems = [tuple(o["value"]) for o in run.obs_at(g.cell_key, Q.STEM)]
        c = cache[sig(stems)][0]
        s = cell_space(c)
        x, y, w, h = next(o["value"] for o in run.obs_at(g.cell_key, Q.STEM) if o["id"] == hs["value"])
        sign = 1.0 if sd["value"] == "up" else -1.0
        tip_y = y if sign > 0 else y + h
        ya, yb = sorted((tip_y - sign * 0.3 * s, tip_y + sign * 3.6 * s))
        xa, xb = int(x - 1.0 * s), int(x + w + 2.6 * s)
        ya, yb = int(ya), int(yb)
        sub = c["img"][ya:yb, xa:xb].astype(np.uint8)
        n, lab, stats, cent = cv2.connectedComponentsWithStats(sub, connectivity=8)
        sx0, sx1 = int(x) - xa, int(x + w) - xa + 1
        stem_labels = set(np.unique(lab[:, sx0:sx1]).tolist()) - {0}
        print("==", key, "direction", sd["value"], "space", round(s), "stem labels", stem_labels)
        att = np.isin(lab, list(stem_labels))
        dist = cv2.distanceTransform((~att).astype(np.uint8), cv2.DIST_L2, 3)
        for i in range(1, n):
            xx, yy, ww, hh, area = stats[i]
            ts = sorted(((ya + yy - tip_y) * sign / s, (ya + yy + hh - tip_y) * sign / s))
            u0, u1 = (xa + xx - (x + w)) / s, (xa + xx + ww - (x + w)) / s
            gap = float(dist[lab == i].min()) / s if i not in stem_labels else 0.0
            if area * 1.0 / (s * s) < 0.02:
                continue
            print(f"   comp {i:3d} {'STEM-ATTACHED' if i in stem_labels else '             '} t {ts[0]:+.2f}..{ts[1]:+.2f}  u {u0:+.2f}..{u1:+.2f}  area {area / (s * s):.3f} sp2  gap to the attached ink {gap:.2f} sp")


if __name__ == "__main__":
    main()
