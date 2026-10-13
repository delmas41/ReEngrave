#!/usr/bin/env python3
"""l283_close_exp: does a wider CLOSING of the erased raster (bridging the hairline breaks a scan and the staff-line eraser leave in
a flag) read the "hugging" flags the attached-ink reader declines, without reading anything that is not a flag? The shape probe
(`l283_shape_k.read`, a copy of `l283_shape.read` with the kernel a parameter) at kernels 0.06 (production) .. 0.20 spaces, on (a) Sean's
page-0 stems by his label and (b) named heads of a record (Sean's 2.81 tile 04, Brahms pdf 1 `glyph/1/1/8/1/11`). ROADMAP 2.83 probe.

    python3 l283_close_exp.py --truth-cells cells_p0.pkl.gz [--heads rec.json cells.pkl.gz key ...]
"""
import argparse
import collections
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l283_common import cell_space, load_cells  # noqa: E402
from l283_dataset import build  # noqa: E402
from l283_features import head_edges_canonical  # noqa: E402
import l283_shape_k as SH  # noqa: E402

KS = (0.06,)
FRAG = (0.35, 1.6, 0.25, 0.3)
SHAPE_NEW = (0.33, 0.40, 1.2, 0.8, 1.0, 1.6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--truth-cells", required=True)
    ap.add_argument("--heads", nargs="+", default=None)
    a = ap.parse_args()
    T, cells, rows = build(a.truth_cells)
    tab = {k: collections.defaultdict(collections.Counter) for k in KS}
    fp = {k: [] for k in KS}
    for r in rows:
        if r["cv"] is None or r["label"] == "trem":
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        heads = head_edges_canonical(T, c)
        head_t, here = None, False
        for hx0, hy0, hx1, hy1 in heads:
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
        for k in KS:
            m = SH.read(c["img"], x, x + w, tip_y, sign, s, head_t=head_t, kclose=k, frag=FRAG, shape=SHAPE_NEW)
            tab[k][r["label"]][m["v"] + ":" + m["why"]] += 1
            if r["label"] != "flag" and m["v"] == "flag":
                fp[k].append(r["stem"])
    for k in KS:
        print(f"kernel {k:.2f} sp:")
        for lab in ("flag", "bare", "beam"):
            print("   ", lab, dict(tab[k][lab]))
        print("    non-flags read as a flag:", fp[k])
    if a.heads:
        import collections as C
        from tools.omr.staged import readout as RD
        from tools.omr.staged.record import Q
        run = RD.load_run(a.heads[0])
        cache = C.defaultdict(list)
        for kk, cc in load_cells(a.heads[1]).items():
            if cc["stems"]:
                cache[tuple(sorted((round(x), round(y), round(w), round(h)) for x, y, w, h in cc["stems"]))].append(cc)
        for key in a.heads[2:]:
            g = run.glyphs[key]
            hs = run.standing(key, Q.HEAD_STEM, "ADJUDICATE")
            sd = run.standing(key, Q.STEM_DIRECTION, "ADJUDICATE")
            stems = [tuple(o["value"]) for o in run.obs_at(g.cell_key, Q.STEM)]
            m = cache.get(tuple(sorted((round(x), round(y), round(w), round(h)) for x, y, w, h in stems)))
            c = m[0]
            s = cell_space(c)
            x, y, w, h = next(o["value"] for o in run.obs_at(g.cell_key, Q.STEM) if o["id"] == hs["value"])
            sign = 1.0 if sd["value"] == "up" else -1.0
            tip_y = y if sign > 0 else y + h
            hb = [(g2.box_canon[0], g2.box_canon[1], g2.box_canon[2], g2.box_canon[3]) for k2, g2 in run.glyphs.items()
                  if g2.cell_key == g.cell_key and (g2.cls or "").startswith("notehead") and g2.box_canon]
            head_t = None
            for hx0, hy0, hx1, hy1 in hb:
                if hx0 >= x + w + 1.8 * s or hx1 <= x - 1.8 * s:
                    continue
                near = hy0 if sign > 0 else hy1
                t_near = (near - tip_y) * sign / s
                if t_near > 0.3 and (head_t is None or t_near < head_t):
                    head_t = t_near - 0.1
            for k in KS:
                res = SH.read(c["img"], x, x + w, tip_y, sign, s, head_t=head_t, kclose=k, frag=FRAG, shape=SHAPE_NEW)
                print(key, f"k={k:.2f}", {kk: res.get(kk) for kk in ("v", "why", "area", "out", "arm", "t_first", "left")})


if __name__ == "__main__":
    main()
