"""K1/K2 first: is the printed `3/4` broken by erasure, or already one blob?

⚠️ REACH BEFORE ANYTHING, AND DEAD AT ZERO. `CRITERION.md` §6.

⚠️ THIS PROBE DECIDES NOTHING. It reports, per staff, what the erased image
holds in the meter's own x-window and what the intact image holds there, so the
two kill conditions can be read off ink rather than argued:

  K1  the `3` and the `4` are already ONE erased component on most staves
      -> erasure did not break the meter; the line bridge has nothing to do.
  K2  the plate's threshold has merged them into a blob with no internal
      structure -> the ceiling is the plate, not the pipeline. Clean negative.

Usage:
    python3 probe/diagnose.py <pdf> <page> --cell 6 [--out out/diagnose.json]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from bridge import (load_page, pixel_sets, components, cell_units,   # noqa: E402
                    bridge_join, groups_of)

#: The meter window, IMPORTED in spirit from the prior job's `target_cell.py`
#: (`W 1.4-2.4`, `H 3.2-5.0`, `X 0.8-2.6` staff spaces) — read off Sean's own
#: 400-dpi crops, never fitted to rows. Here only the X half is used, because
#: the whole point is that the SHAPE is what erasure destroyed: gating on H
#: would throw away the fragments this probe exists to count.
X_MIN, X_MAX = 0.8, 2.6


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cell", type=int, default=6)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    t0 = time.time()
    pws, cells = load_page(a.pdf, a.page)
    t1 = time.time()

    staves = sorted({c.staff_index for c in cells})
    n_cells = len(cells)
    print(f"REACH  staves={len(staves)}  cells={n_cells}  "
          f"prepare={t1 - t0:.1f}s")
    if not cells:
        print("DEAD: no cells")
        return 2

    here = [c for c in cells if c.measure_index == a.cell]
    print(f"REACH  cells at measure_index={a.cell}: {len(here)}")
    if not here:
        print(f"DEAD: no cell at measure_index={a.cell}")
        return 2

    rows = []
    for c in sorted(here, key=lambda c: c.staff_index):
        sets = pixel_sets(c)
        if sets is None:
            print(f"  staff {c.staff_index:2d}  NO MASK")
            continue
        intact, erased, removed = sets
        sp, thick = cell_units(c)
        if not sp:
            print(f"  staff {c.staff_index:2d}  no staff-space unit")
            continue
        n, labels, stats = components(erased)
        ni, ilabels, istats = components(intact)

        # Everything the erased image holds in the meter's x-window.
        frags = []
        for lab in range(1, n):
            x, y, w, h, area = (int(stats[lab, k]) for k in range(5))
            xs = x / sp
            if not (X_MIN <= xs <= X_MAX):
                continue
            frags.append({"label": lab, "x_sp": round(xs, 2),
                          "w_sp": round(w / sp, 2), "h_sp": round(h / sp, 2),
                          "area": area, "box": [x, y, x + w, y + h]})
        frags.sort(key=lambda f: f["box"][1])

        # Which intact component covers that window, and how big is it?
        big = 0
        if frags:
            xa = min(f["box"][0] for f in frags)
            xb = max(f["box"][2] for f in frags)
            ya = min(f["box"][1] for f in frags)
            yb = max(f["box"][3] for f in frags)
            sub = ilabels[ya:yb, xa:xb]
            vals, cnt = None, None
            import numpy as np
            v = sub[sub > 0]
            if v.size:
                vals, cnt = np.unique(v, return_counts=True)
                dom = int(vals[int(cnt.argmax())])
                big = int(istats[dom, 4])

        bound = int(round(thick)) if thick else 0
        parent, edges = bridge_join(labels, removed, bound=bound)
        gids = {parent[f["label"]] for f in frags}
        groups = groups_of(parent, stats)
        joined = []
        for g in sorted(gids):
            gg = groups[g]
            joined.append({"w_sp": round(gg["w"] / sp, 2),
                           "h_sp": round(gg["h"] / sp, 2),
                           "members": len(gg["members"])})

        print(f"  staff {c.staff_index:2d}  sp={sp:6.2f}px thick={thick}"
              f"  erased_frags_in_window={len(frags):2d}"
              f"  after_bridge={len(gids):2d}"
              f"  intact_comp_area={big}")
        for f in frags[:8]:
            print(f"        frag x={f['x_sp']:4.2f} w={f['w_sp']:4.2f} "
                  f"h={f['h_sp']:4.2f} area={f['area']}")
        for j in joined:
            print(f"        -> group w={j['w_sp']:4.2f} h={j['h_sp']:4.2f} "
                  f"from {j['members']} fragment(s)")

        rows.append({"staff": c.staff_index, "spacing_px": sp,
                     "thickness_px": thick, "bound": bound,
                     "n_erased_components": n - 1,
                     "n_intact_components": ni - 1,
                     "frags_in_window": frags,
                     "groups_in_window": joined,
                     "dominant_intact_area": big,
                     "n_bridges": len(edges),
                     "gaps": sorted({e[2] for e in edges})})

    if not rows:
        print("DEAD: no staff produced a usable mask/unit")
        return 2

    one = sum(1 for r in rows if len(r["frags_in_window"]) == 1)
    print(f"\nK1 CHECK: {one} of {len(rows)} staves hold the window's ink as a "
          f"SINGLE erased component already")
    print(f"K1 fires if that is a majority ({len(rows) // 2 + 1}+)")

    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"page": a.page, "cell": a.cell,
                                 "staves": rows}, indent=1))
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
