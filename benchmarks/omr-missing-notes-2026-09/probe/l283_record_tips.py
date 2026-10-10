#!/usr/bin/env python3
"""l283_record_tips: the candidate shape reading (`l283_shape.read`) at the TRUE tip of every head the base record gave a decided
stem and a decided stem direction, on the cached erased rasters of the same page (`l283_cells.py`), with the record's own head
boxes clipping the window. A rehearsal of the real arm on a plate with no hand truth, to LOOK at (montage of reads) before the
re-gather. Cells are matched between the record and the cache by the multiset of their CV stems (deterministic, identical).
ROADMAP 2.83 probe.

    python3 l283_record_tips.py --record rec.json --cells cells_pN.pkl.gz --page N --out montage.png [--which flag] [--n 36]
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
import l283_shape as SH  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
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
    ap.add_argument("--which", default="flag")
    ap.add_argument("--n", type=int, default=36)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    run = RD.load_run(a.record)
    cells = load_cells(a.cells)
    cache = collections.defaultdict(list)
    for k, c in cells.items():
        if c["stems"]:
            cache[sig(c["stems"])].append(c)
    rec_stems = collections.defaultdict(dict)
    for o in run.observations:
        if o["quantity"] == Q.STEM and o["subject"].startswith("cell/%d/" % a.page):
            rec_stems[o["subject"]][o["id"]] = tuple(o["value"])
    cell_of = {}
    for ck, d in rec_stems.items():
        m = cache.get(sig(d.values()))
        if m and len(m) == 1:
            cell_of[ck] = m[0]
    print("record cells with stems", len(rec_stems), "matched to a cached cell", len(cell_of))
    heads_by_cell = collections.defaultdict(list)
    for k, g in run.glyphs.items():
        if g.page == a.page and (g.cls or "").startswith("notehead") and g.box_canon:
            x0, y0, x1, y1 = g.box_canon
            heads_by_cell[g.cell_key].append((x0, y0, x1 - x0, y1 - y0))
    res = []
    for k, g in run.glyphs.items():
        if g.page != a.page or not (g.cls or "").startswith("notehead"):
            continue
        hs = run.standing(k, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(k, Q.STEM_DIRECTION, "ADJUDICATE")
        if hs is None or hs["outcome"] != "decided" or sd is None or sd["outcome"] != "decided" or sd.get("value") not in ("up", "down"):
            continue
        c = cell_of.get(g.cell_key)
        if c is None:
            continue
        box = rec_stems[g.cell_key].get(hs["value"])
        if box is None:
            continue
        x, y, w, h = box
        sign = 1.0 if sd["value"] == "up" else -1.0
        tip_y = y if sign > 0 else y + h
        s = cell_space(c)
        edge, here = G._head_edge_for_end(heads_by_cell[g.cell_key], x, x + w, tip_y, sign, s)
        if here:
            res.append((k, {"v": "decline", "why": "head_at_this_end"}, c, box, sign))
            continue
        head_t = None if edge is None else (edge - tip_y) * sign / s - 0.1
        res.append((k, SH.read(c["img"], x, x + w, tip_y, sign, s, head_t=head_t), c, box, sign))
    cnt = collections.Counter(m["v"] + ":" + m["why"] for _k, m, *_r in res)
    print("heads with a decided stem + direction:", len(res), dict(cnt))
    pick = [r for r in res if r[1]["v"] == a.which]
    random.Random(a.seed).shuffle(pick)
    tiles = []
    for k, m, c, (x, y, w, h), sign in pick[:a.n]:
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
        cv2.putText(rgb, "/".join(k.split("/")[2:6]), (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (255, 0, 0), 1)
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
