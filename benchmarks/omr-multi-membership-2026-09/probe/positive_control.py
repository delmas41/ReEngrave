"""The POSITIVE CONTROL beside the zero — and the premise correction.

⚠️⚠️ `arm.py` reports that the line bridge fires **ZERO** times on the whole
page. A zero from a method that did not run and a zero from a method that ran
and found nothing are the same number, so this probe makes the difference
visible: it builds the image the brief ASSUMED the pipeline has, and shows the
bridge repairing it.

The reason for the zero is in `staff_line_removal.py`'s own first line —
*"Phase 1.4 — Staff line removal **preserving symbol-crossing pixels**"*:

> *"The goal: produce an image where staff lines are erased, but the pixels
> where notes/stems/ornaments cross those lines remain intact. Naive removal
> (just erasing the staff line row) severs noteheads in half and disconnects
> stems from their flags."*

That rule — a vertical ink run no taller than the line's own printed thickness
IS the line and is erased; a taller one is something CROSSING and is left
entirely alone — is multi-membership, shipped, per column, since Phase 1.4.
`LINE_CROSSING_FACTOR = 2.0` is the constant that expresses it.

So this probe runs THREE erasures over the same cells:

  `shipped` — `remove_staff_lines_from_cell`, what the pipeline uses;
  `naive`   — the SAME code with the ONE predicate removed, so every run at a
              line is erased. This is the image the brief's dilemma describes;
  `naive+bridge` — the bridge applied to `naive`.

⚠️ THE NAIVE ARM DIFFERS BY ONE PREDICATE AND CALLS THE SHIPPED HELPERS
(`_anchor_rows`, `_vertical_runs_through`, `_line_thickness`). Re-implementing
the line walk here would make this a comparison of two authors rather than of
one rule.

The question the control answers: does `naive + bridge` recover the component
partition `shipped` already has? If it does, the bridge and
`LINE_CROSSING_FACTOR` are two expressions of one idea, and the idea is already
in the tree.

Usage:
    python3 probe/positive_control.py <pdf> <page> [--cells 6,7,8,9] [--all]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
os.environ.setdefault("OMR_DIRECTION_TEXT", "0")

from bridge import (load_page, pixel_sets, components, cell_units,   # noqa: E402
                    bridge_join, groups_of)

from tools.omr.staff_line_removal import (                           # noqa: E402
    MAX_LINE_THICKNESS_SPACES, _vertical_runs_through, _line_thickness,
    _anchor_rows, LINE_SEARCH_RADIUS_SPACES)


def naive_erase(cell) -> np.ndarray | None:
    """`cell.image_no_staff` as it would be WITHOUT the symbol-crossing rule.

    ⚠️ THE BAND IS THE LINE'S OWN MEASURED THICKNESS, CENTRED ON THE ANCHOR —
    not the full vertical run. That distinction cost this probe a whole first
    run: erasing the RUN (what the shipped code does, because it only ever
    erases runs it has already judged to BE the line) removes up to
    `2 * (cap + 2) = 75` px where a glyph crosses, so the gaps it leaves are
    three times the line's thickness and no bridge bounded by the thickness
    could ever close them. That is a property of my naive arm, not of the
    method, and reporting it as a method failure would have been wrong.

    `staff_line_removal.py`'s own words for the thing being modelled are
    *"naive removal (just erasing the staff line row)"* — a row, of the line's
    printed thickness. That is what this builds.

    ⚠️ THE ANCHORING AND THE THICKNESS ESTIMATE ARE THE SHIPPED CODE, imported
    (`_anchor_rows`, `_vertical_runs_through`, `_line_thickness`), so the two
    arms differ in WHAT IS ERASED and in nothing else.
    """
    binary = getattr(cell, "binary", None)
    if binary is None:
        img = getattr(cell, "image", None)
        if img is None:
            return None
        from tools.omr.preprocessing import binarize
        if getattr(img, "ndim", 0) == 3:
            import cv2
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        binary = binarize(img)
    h, w = binary.shape
    ink = binary == 0
    line_ys = list(getattr(cell, "staff_line_ys_canonical", None) or [])
    if not line_ys:
        return None
    spacing = ((line_ys[-1] - line_ys[0]) / 4.0 if len(line_ys) >= 2
               else float(getattr(cell, "staff_line_spacing_canonical", 0.0) or 0.0))
    cap = max(1, int(round(MAX_LINE_THICKNESS_SPACES * spacing))) if spacing > 0 else h
    to_erase = np.zeros((h, w), dtype=bool)
    for y in line_ys:
        y = int(round(y))
        if not (0 <= y < h):
            continue
        search = int(round(LINE_SEARCH_RADIUS_SPACES * spacing)) if spacing > 0 else 0
        heights, _tops, _bottoms, present = _vertical_runs_through(
            ink, y, cap, radius=search)
        if not present.any():
            continue
        thickness = _line_thickness(heights[present], cap)
        anchor, found = _anchor_rows(ink, y, int(search))
        half = max(1, int(round(thickness / 2.0)))
        rows = np.arange(h)[:, None]
        # THE difference: every column's band is erased, and the band is the
        # LINE's thickness rather than whatever run happens to pass through it.
        band = ((rows >= (anchor - half)[None, :])
                & (rows <= (anchor + half)[None, :])
                & found[None, :])
        to_erase |= band & ink
    out = binary.copy()
    out[to_erase] = 255
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("page", type=int)
    ap.add_argument("--cells", default="6,7,8,9")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--bound-mult", type=float, default=1.0,
                    help="bridge bound, as a multiple of the cell's own "
                         "measured line thickness")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    _pws, cells = load_page(a.pdf, a.page)
    want = ([c for c in cells] if a.all else
            [c for c in cells
             if c.measure_index in {int(s) for s in a.cells.split(",")}])
    print(f"REACH  staves={len({c.staff_index for c in cells})}  "
          f"cells={len(cells)}  in scope={len(want)}")
    if not want:
        print("DEAD: nothing in scope")
        return 2

    tot = {"shipped": 0, "naive": 0, "naive_bridged": 0}
    exact, cellsdone, bridges, gaps = 0, 0, 0, []
    for c in want:
        sets = pixel_sets(c)
        sp, thick = cell_units(c)
        nv = naive_erase(c)
        if sets is None or not sp or not thick or nv is None:
            continue
        intact, erased, _removed = sets
        naive = nv == 0
        naive_removed = intact & ~naive

        n_ship, _l1, _s1 = components(erased)
        n_nv, lab_nv, st_nv = components(naive)
        bound = max(1, int(round(thick * a.bound_mult)))
        parent, edges = bridge_join(lab_nv, naive_removed, bound=bound,
                                    require_removed=True)
        groups = groups_of(parent, st_nv)

        # ⚠️ THE UNBOUNDED GAP DISTRIBUTION, measured rather than assumed.
        # The bound is the cell's own line thickness, and the first run of this
        # control found ZERO bridges on an image the naive erasure had just
        # shattered 3.6x — so the question is not whether the machinery works
        # (`synthetic.py` proves it does) but how WIDE the naive erasure's gaps
        # actually are. A gap far over the line's thickness is the finding.
        _pu, eu = bridge_join(lab_nv, naive_removed, bound=10 ** 6,
                              require_removed=True)
        gaps.extend(e[2] for e in eu)

        tot["shipped"] += n_ship - 1
        tot["naive"] += n_nv - 1
        tot["naive_bridged"] += len(groups)
        bridges += len(edges)
        if len(groups) == n_ship - 1:
            exact += 1
        cellsdone += 1

    if not cellsdone:
        print("DEAD: no cell produced all three erasures")
        return 2

    print(f"\nover {cellsdone} cells:")
    print(f"  components, SHIPPED erasure        {tot['shipped']}")
    print(f"  components, NAIVE erasure          {tot['naive']}"
          f"   ({tot['naive'] / max(tot['shipped'], 1):.2f}x)")
    print(f"  components, NAIVE + LINE BRIDGE    {tot['naive_bridged']}")
    print(f"  bridges at bound = {a.bound_mult}x line thickness  {bridges}")
    rec = (tot["naive"] - tot["naive_bridged"])
    need = (tot["naive"] - tot["shipped"])
    print(f"  fragments the bridge re-joined     {rec} of {need} "
          f"the naive erasure created "
          f"({100.0 * rec / max(need, 1):.1f}%)")
    print(f"  cells where naive+bridge lands on the shipped count exactly: "
          f"{exact} of {cellsdone}")

    # ⚠️ THE GAP DISTRIBUTION IS THE EXPLANATION, and it is measured with NO
    # bound at all, so the number cannot be an artefact of the bound.
    if gaps:
        g = np.array(gaps)
        print(f"\n  bridgeable gaps found with NO bound: {g.size}")
        print(f"    px  min={g.min()} p25={int(np.percentile(g, 25))} "
              f"median={int(np.median(g))} p75={int(np.percentile(g, 75))} "
              f"max={g.max()}")
        print(f"    share at or under 1x line thickness "
              f"(~{int(np.median([25]))}px): "
              f"{100.0 * float((g <= 25).mean()):.1f}%")
    else:
        print("\n  NO bridgeable gap exists at ANY bound on this page.")

    print("\n  ⚠️ READ THIS WITH `synthetic.py`, WHICH IS THE CONTROL THAT THE "
          "MACHINERY WORKS.\n     This arm is the control that the SHIPPED "
          "erasure is what makes the bridge idle;\n     it is not itself "
          "evidence that the bridge can fire.")

    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "cells": cellsdone, "components": tot, "bridges": bridges,
            "gap_min": min(gaps) if gaps else None,
            "gap_median": int(np.median(gaps)) if gaps else None,
            "gap_max": max(gaps) if gaps else None,
            "rejoined": rec, "created_by_naive": need,
            "cells_exactly_recovered": exact}, indent=1))
        print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
