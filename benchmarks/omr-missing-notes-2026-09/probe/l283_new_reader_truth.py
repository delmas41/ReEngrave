#!/usr/bin/env python3
"""l283_new_reader_truth: the PRODUCTION `gather.stem_tip_ink` and `gather.stem_tip_hooks` (whatever tree this runs on) at the
true tip of every matched truth stem of Sean's page, by his label, on the real erased cell raster (`l283_cells.py`), with his
head boxes clipping the window exactly as `gather._head_edge_for_end` does. The rehearsal that must agree with the probe
(`l283_shape.py`) before any re-gather is spent, and the base/arm table of the reader alone. ROADMAP 2.83.

    python3 l283_new_reader_truth.py CELLS.pkl.gz [--list]
"""
import argparse
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_common import cell_space  # noqa: E402
from l283_dataset import build  # noqa: E402
from l283_features import head_edges_canonical  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    from tools.omr.staged import gather as G
    T, cells, rows = build(a.cells)
    tab = collections.defaultdict(collections.Counter)
    hooks = collections.defaultdict(collections.Counter)
    listing = []
    for r in rows:
        if r["cv"] is None or r["label"] == "trem":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        img = (~c["img"]).astype("uint8") * 255
        heads = [(p, q, c_ - p, d - q) for p, q, c_, d in head_edges_canonical(T, c)]
        edge, here = G._head_edge_for_end(heads, x, x + w, tip_y, sign, s)
        if here:
            tab[r["label"]]["head_at_this_end"] += 1
            continue
        m = G.stem_tip_ink(img, x, x + w, tip_y, sign, s, head_edge=edge)
        if m is None:
            tab[r["label"]]["None(off)"] += 1
            continue
        key = {True: "flag", False: "none", None: "cannot_tell"}[m["found"]] + ":" + str(m.get("why"))
        tab[r["label"]][key] += 1
        listing.append((r["label"], r["stem"], key, {k: m.get(k) for k in ("area", "left_area", "out", "arm", "t_first", "right", "left")}))
        if m["found"]:
            hk = G.stem_tip_hooks(img, x, x + w, tip_y, sign, s, head_edge=edge)
            hooks[r["label"]]["None" if hk is None else (f"hooks={hk['hooks']}" if hk["hooks"] else "uncounted:" + str(hk["hooks_reason"]))] += 1
    for lab in ("flag", "bare", "beam"):
        print(lab, dict(tab[lab]))
    print("hook counter on the reads:", {k: dict(v) for k, v in hooks.items()})
    if a.list:
        for item in listing:
            print(item)


if __name__ == "__main__":
    main()
