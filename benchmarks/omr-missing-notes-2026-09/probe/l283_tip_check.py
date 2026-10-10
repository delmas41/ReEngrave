#!/usr/bin/env python3
"""l283_tip_check: the PRODUCTION tip reader (`gather.stem_tip_ink` with the observer's own blockers, the stem's own flag boxes set
aside, the head edge) at the true tip of given heads of a record, on the cached erased raster of the same page (`l283_cells.py`;
cells matched to the record's by the multiset of their CV stems). A rehearsal that costs seconds where a re-gather costs an hour:
what would the reader file at this head's tip on THIS tree. ROADMAP 2.83 probe.

    python3 l283_tip_check.py --record rec.json --cells cells_pN.pkl.gz key [key ...]
"""
import argparse
import collections
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_common import cell_space, load_cells  # noqa: E402
from tools.omr.staged import gather as G  # noqa: E402
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
    cells = load_cells(a.cells)
    cache = collections.defaultdict(list)
    for k, c in cells.items():
        if c["stems"]:
            cache[sig(c["stems"])].append(c)
    for key in a.keys:
        g = run.glyphs[key]
        cell = g.cell_key
        hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
        sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
        if hs is None or hs["outcome"] != "decided" or sd is None or sd["outcome"] != "decided":
            print(key, "no decided stem/direction")
            continue
        stems = [tuple(o["value"]) for o in run.obs_at(cell, Q.STEM)]
        m = cache.get(sig(stems))
        if not m or len(m) != 1:
            print(key, "cell not matched to the cache", len(m or []))
            continue
        c = m[0]
        sp = cell_space(c)
        box = next(o["value"] for o in run.obs_at(cell, Q.STEM) if o["id"] == hs["value"])
        x, y, w, h = box
        sign = 1.0 if sd["value"] == "up" else -1.0
        tip_y = y if sign > 0 else y + h
        dets, heads = [], []
        for k2, g2 in run.glyphs.items():
            if g2.cell_key == cell and g2.box_canon:
                x0, y0, x1, y1 = g2.box_canon
                dets.append(types.SimpleNamespace(smufl_name=g2.cls or "", x_canonical=x0, y_canonical=y0,
                                                  width_canonical=x1 - x0, height_canonical=y1 - y0))
                if (g2.cls or "").startswith("notehead"):
                    heads.append((x0, y0, x1 - x0, y1 - y0))
        beams = [types.SimpleNamespace(x_canonical=o["value"][0], y_canonical=o["value"][1], width_canonical=o["value"][2],
                                       height_canonical=o["value"][3]) for o in run.obs_at(cell, Q.BEAM_STROKE)]
        # the observer's own call: the CV beams of this cell are the `Q.BEAM_STROKE` rows of the CV reader
        cv_beams = [b for b, o in zip(beams, run.obs_at(cell, Q.BEAM_STROKE)) if o.get("reader") == "cv_lines"]
        blockers = G._stem_tip_blockers(cv_beams, dets, sp, own_stem=(x, y, w, h))
        edge, here = G._head_edge_for_end(heads, x, x + w, tip_y, sign, sp)
        img = (~c["img"]).astype("uint8") * 255
        res = None if here else G.stem_tip_ink(img, x, x + w, tip_y, sign, sp, head_edge=edge, blockers=blockers)
        print(key, "direction", sd["value"], "head_here", here, "->", res if res is None else {k: res.get(k) for k in ("found", "why", "area", "out", "arm", "t_first", "left_area")})


if __name__ == "__main__":
    main()
