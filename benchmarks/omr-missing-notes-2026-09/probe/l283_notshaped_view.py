#!/usr/bin/env python3
"""l283_notshaped_view: a montage of the erased tips (tip row red) of the heads of a record whose true-tip row is the abstention
`ink_not_flag_shaped`, each tile captioned with the measures (out / arm / t_first / area) the reader filed -- to see whether the cuts
decline flags the eye reads. Cells of one page matched by CV stems (`l283_cells.py`). ROADMAP 2.83 probe.

    python3 l283_notshaped_view.py --record rec.json --cells cells_pN.pkl.gz --page N --out m.png [--why ink_not_flag_shaped] [--n 36]
"""
import argparse
import collections
import random
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
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--why", default="ink_not_flag_shaped")
    ap.add_argument("--n", type=int, default=36)
    ap.add_argument("--seed", type=int, default=2)
    a = ap.parse_args()
    run = RD.load_run(a.record)
    cache = collections.defaultdict(list)
    for k, c in load_cells(a.cells).items():
        if c["stems"]:
            cache[sig(c["stems"])].append(c)
    abst = {}
    for o in run.abstentions:
        if o["quantity"] == Q.STEM_TIP_INK and (o.get("detail") or {}).get("why") == a.why:
            d = o["detail"]
            abst[(o["subject"], d.get("stem_row_id"), d.get("end"))] = d
    picks = []
    for key, g in run.glyphs.items():
        if g.page != a.page or not (g.cls or "").startswith("notehead"):
            continue
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        if not (hs and hs["outcome"] == "decided" and sd and sd["outcome"] == "decided" and sd.get("value") in ("up", "down")):
            continue
        end = "top" if sd["value"] == "up" else "bottom"
        d = abst.get((g.cell_key, hs["value"], end))
        if d is None:
            continue
        stems = [tuple(o["value"]) for o in run.obs_at(g.cell_key, Q.STEM)]
        m = cache.get(sig(stems))
        if not m or len(m) != 1:
            continue
        picks.append((key, m[0], next(o["value"] for o in run.obs_at(g.cell_key, Q.STEM) if o["id"] == hs["value"]), end, d))
    print(len(picks), "heads with", a.why)
    random.Random(a.seed).shuffle(picks)
    tiles = []
    for key, c, (x, y, w, h), end, d in picks[:a.n]:
        s = cell_space(c)
        sign = 1.0 if end == "top" else -1.0
        tip_y = y if sign > 0 else y + h
        x0, x1 = int(x - 1.0 * s), int(x + w + 2.6 * s)
        ya, yb = sorted((tip_y - sign * 0.6 * s, tip_y + sign * 4.2 * s))
        ya, yb, x0 = max(0, int(ya)), int(yb), max(0, x0)
        sub = np.where(c["img"][ya:yb, x0:x1], 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
        ty = int(tip_y - ya)
        cv2.line(rgb, (0, ty), (rgb.shape[1] - 1, ty), (0, 0, 255), 1)
        rgb = cv2.resize(rgb, (150, 200), interpolation=cv2.INTER_AREA)
        rgb = cv2.copyMakeBorder(rgb, 0, 18, 0, 4, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(rgb, f"o{d.get('out')} a{d.get('arm')} t{d.get('t_first')}", (2, 212), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 0, 0), 1)
        tiles.append(rgb)
    per = 12
    rows = []
    for i in range(0, len(tiles), per):
        r = tiles[i:i + per]
        while len(r) < per:
            r.append(np.full((218, 154, 3), 255, np.uint8))
        rows.append(np.concatenate(r, axis=1))
    if rows:
        cv2.imwrite(a.out, np.concatenate(rows, axis=0))
        print("wrote", a.out, len(tiles))


if __name__ == "__main__":
    main()
