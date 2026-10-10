#!/usr/bin/env python3
"""l283_frag_scan: where does the FRAGMENT-tolerant reading (`l283_shape_k.read(frag=...)`) say flag at a head's true tip and the
attached-only reading does not -- on a whole page of a record (heads with a decided stem and direction, the stem's own head clipping
the window), with a montage of the erased tips of every such head (tip row red) to LOOK at. The false-positive question for the
broken-flag extension. ROADMAP 2.83 probe (no blockers here: the production reader also abstains where a detection covers the ink).

    python3 l283_frag_scan.py --record rec.json --cells cells_pN.pkl.gz --page N --out m.png
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
import l283_shape_k as SH  # noqa: E402
from tools.omr.staged import readout as RD  # noqa: E402
from tools.omr.staged.record import Q  # noqa: E402

FRAG = (0.35, 1.6, 0.25, 0.3)


def sig(stems):
    return tuple(sorted((round(x), round(y), round(w), round(h)) for x, y, w, h in stems))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", required=True)
    ap.add_argument("--cells", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    run = RD.load_run(a.record)
    cache = collections.defaultdict(list)
    for k, c in load_cells(a.cells).items():
        if c["stems"]:
            cache[sig(c["stems"])].append(c)
    heads_by_cell = collections.defaultdict(list)
    for k, g in run.glyphs.items():
        if g.page == a.page and (g.cls or "").startswith("notehead") and g.box_canon:
            heads_by_cell[g.cell_key].append(g.box_canon)
    tally = collections.Counter()
    shown = []
    for key, g in run.glyphs.items():
        if g.page != a.page or not (g.cls or "").startswith("notehead"):
            continue
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        if not (hs and hs["outcome"] == "decided" and sd and sd["outcome"] == "decided" and sd.get("value") in ("up", "down")):
            continue
        stems = [tuple(o["value"]) for o in run.obs_at(g.cell_key, Q.STEM)]
        m = cache.get(sig(stems))
        if not m or len(m) != 1:
            continue
        c = m[0]
        s = cell_space(c)
        x, y, w, h = next(o["value"] for o in run.obs_at(g.cell_key, Q.STEM) if o["id"] == hs["value"])
        sign = 1.0 if sd["value"] == "up" else -1.0
        tip_y = y if sign > 0 else y + h
        head_t, here = None, False
        for hx0, hy0, hx1, hy1 in heads_by_cell[g.cell_key]:
            if hx0 >= x + w + 1.8 * s or hx1 <= x - 1.8 * s:
                continue
            near, far = (hy0, hy1) if sign > 0 else (hy1, hy0)
            t_near, t_far = (near - tip_y) * sign / s, (far - tip_y) * sign / s
            if t_near <= 0.3 and t_far > -0.3:
                here = True
            elif t_near > 0.3 and (head_t is None or t_near < head_t):
                head_t = t_near - 0.1
        if here:
            continue
        r0 = SH.read(c["img"], x, x + w, tip_y, sign, s, head_t=head_t)
        r1 = SH.read(c["img"], x, x + w, tip_y, sign, s, head_t=head_t, frag=FRAG)
        tally[(r0["v"], r1["v"])] += 1
        if r1["v"] == "flag" and r0["v"] != "flag":
            shown.append((key, c, (x, y, w, h), sign, r1))
    print({f"{k[0]}->{k[1]}": v for k, v in tally.items()})
    print("newly flag-shaped with fragments:", len(shown))
    tiles = []
    for key, c, (x, y, w, h), sign, r1 in shown[:48]:
        s = cell_space(c)
        tip_y = y if sign > 0 else y + h
        x0, x1 = int(x - 1.0 * s), int(x + w + 2.6 * s)
        ya, yb = sorted((tip_y - sign * 0.6 * s, tip_y + sign * 4.2 * s))
        ya, yb, x0 = max(0, int(ya)), int(yb), max(0, x0)
        sub = np.where(c["img"][ya:yb, x0:x1], 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
        ty = int(tip_y - ya)
        cv2.line(rgb, (0, ty), (rgb.shape[1] - 1, ty), (0, 0, 255), 1)
        rgb = cv2.resize(rgb, (150, 200), interpolation=cv2.INTER_AREA)
        rgb = cv2.copyMakeBorder(rgb, 0, 0, 0, 4, cv2.BORDER_CONSTANT, value=(0, 200, 0))
        cv2.putText(rgb, "/".join(key.split("/")[2:6]), (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 0, 0), 1)
        tiles.append(rgb)
    per = 12
    rows = []
    for i in range(0, len(tiles), per):
        r = tiles[i:i + per]
        while len(r) < per:
            r.append(np.full((200, 154, 3), 255, np.uint8))
        rows.append(np.concatenate(r, axis=1))
    if rows:
        cv2.imwrite(a.out, np.concatenate(rows, axis=0))
        print("wrote", a.out, len(tiles))


if __name__ == "__main__":
    main()
