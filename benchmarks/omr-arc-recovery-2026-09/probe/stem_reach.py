"""REACH of the stem rule, before any of it is written.

A slur or tie over stem-up notes is drawn from STEM TOP to STEM TOP, and a
stem stands at the SIDE of its notehead -- so the arc's ink stops roughly half
a notehead width inside both outer head CENTRES, which is the only thing
`_noteheads_under` measures. This repo has already paid for exactly this
mechanism once: `_beam_levels` tested a head's centre against a beam stroke
that *"runs from the FIRST stem it joins to the LAST"*, and the overshoot
clustered at **0.35-0.47 notehead widths**. The repair there was not a
tolerance -- it was to join a note to its beam BY ITS STEM.

Here the same quantity measures a median **0.52** notehead widths, and the
distribution has NO empty interval, so the pad cannot be re-read off this page
and must not be moved. This probe asks the other question: how many refused
arcs would bind two notes if a head were reachable AT ITS STEM?

⚠️ `Q.STEM` IS FILED ON THE CELL IN CANONICAL COORDINATES AND CARRIES NO PAGE
BOX -- the *gathered in a frame that cannot answer* fault this repo already
records for `gather_glyph_families`. The map is DERIVED per cell from the
glyph rows that carry both frames (an exact affine in x), and the fit's
residual is printed as its own control: a cell whose glyphs do not agree on
one scale has no usable map and is reported, never approximated.
"""
from __future__ import annotations

import collections
import json
import statistics
import sys
from typing import Any, Dict, List, Optional, Tuple

from tools.omr import export as _legacy
from tools.omr.staged import export as E
from tools.omr.staged.record import Q

sys.path.insert(0, "benchmarks/omr-arc-recovery-2026-09")
from arc_partition import heads_by_cell  # noqa: E402


def cell_x_maps(rec) -> Tuple[Dict[str, Tuple[float, float]], List[float]]:
    """`cell subject -> (a, b)` with `x_page = a * x_canonical + b`, and the
    residuals, so the caller can see whether the map is real."""
    per_cell: Dict[str, List[Tuple[float, float]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.GLYPH_BOX):
        s = E._parse_subject(o["subject"])
        if s["glyph"] is None:
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        v = o["value"]
        if not pb or not isinstance(v, (list, tuple)) or len(v) < 5:
            continue
        key = f"cell/{s['page']}/{s['system']}/{s['staff']}/{s['cell'] or 0}"
        per_cell[key].append((float(v[1]) + float(v[3]) / 2.0,
                              (float(pb[0]) + float(pb[2])) / 2.0))
    maps: Dict[str, Tuple[float, float]] = {}
    resid: List[float] = []
    for key, pts in per_cell.items():
        xs = [p[0] for p in pts]
        if len(pts) < 2 or (max(xs) - min(xs)) < 1e-6:
            continue
        n = len(pts)
        mx = sum(p[0] for p in pts) / n
        my = sum(p[1] for p in pts) / n
        sxx = sum((p[0] - mx) ** 2 for p in pts)
        sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
        if sxx <= 0:
            continue
        a = sxy / sxx
        b = my - a * mx
        maps[key] = (a, b)
        resid.extend(abs(a * p[0] + b - p[1]) for p in pts)
    return maps, resid


def main(path: str) -> None:
    rec = E.Record(json.load(open(path)))
    parts, *_ = E.build(rec)
    heads = heads_by_cell(rec)
    maps, resid = cell_x_maps(rec)
    resid.sort()
    print(f"canonical->page x map: {len(maps)} cells, "
          f"residual med {statistics.median(resid):.2f}px "
          f"p99 {resid[int(len(resid)*0.99)]:.2f}px  (0 == an exact affine)")

    stems_by_cell: Dict[str, List[Tuple[float, float]]] = collections.defaultdict(list)
    n_unmapped = 0
    for o in rec.obs_of(Q.STEM):
        key = o["subject"]
        m = maps.get(key)
        v = o["value"]
        if m is None or not isinstance(v, (list, tuple)) or len(v) < 4:
            n_unmapped += 1
            continue
        a, b = m
        x0 = a * float(v[0]) + b
        x1 = a * (float(v[0]) + float(v[2])) + b
        y0 = float(v[1])
        y1 = y0 + float(v[3])
        stems_by_cell[key].append(((x0 + x1) / 2.0, (y0, y1, float(v[0]),
                                                     float(v[0]) + float(v[2]))))
    print(f"stems: {sum(len(v) for v in stems_by_cell.values())} mapped, "
          f"{n_unmapped} with no cell map")

    # A head's stem: the stem whose canonical x-range overlaps the head's --
    # `_stem_joined`'s own BOX OVERLAP rule, x only (an arc is an x question).
    head_stem_x: Dict[str, float] = {}
    for o in rec.obs_of(Q.GLYPH_BOX):
        sub = o["subject"]
        s = E._parse_subject(sub)
        if s["glyph"] is None or not rec.obs(Q.NOTEHEAD_CLASS, sub):
            continue
        v = o["value"]
        if not isinstance(v, (list, tuple)) or len(v) < 5:
            continue
        key = f"cell/{s['page']}/{s['system']}/{s['staff']}/{s['cell'] or 0}"
        hx0, hx1 = float(v[1]), float(v[1]) + float(v[3])
        best = None
        for px, (_y0, _y1, cx0, cx1) in stems_by_cell.get(key, ()):
            if cx0 <= hx1 and cx1 >= hx0:
                best = px if best is None else best
        if best is not None:
            head_stem_x[sub] = best
    print(f"noteheads with a stem: {len(head_stem_x)}")

    before = after = 0
    gained: "collections.Counter" = collections.Counter()
    for part in parts:
        measures, pma, kinds, spacings, tops, breaks = E._flatten_part(part)
        if not measures or not any(pma):
            continue
        cells = E._part_cells_in_order(part)
        for segments in _legacy._merge_arcs_across_barlines(
                measures, pma, spacings, tops, breaks):
            covered = _legacy._noteheads_under(measures, segments)
            kind = ("tie" if "tie" in {kinds.get(id(b)) for _m, b in segments}
                    else "slur")
            n2 = 0
            seen = set()
            for m_idx, (ax, _ay, aw, _ah) in segments:
                r_, c_ = cells[m_idx]
                pool = [h for h in
                        (heads.get((r_.page, r_.system, r_.staff, c_)) or [])
                        if h["page_box"] and h["fate"] == "written"]
                if not pool:
                    continue
                pad = _legacy._SLUR_ARC_PAD_NOTEHEADS * (
                    sum(h["page_box"][2] for h in pool) / len(pool))
                for h in pool:
                    pb = h["page_box"]
                    xs = [pb[0] + pb[2] / 2.0]
                    sx = head_stem_x.get(h["subject"])
                    if sx is not None:
                        xs.append(sx)
                    if any(ax - pad <= x <= ax + aw + pad for x in xs):
                        if h["subject"] not in seen:
                            seen.add(h["subject"])
                            n2 += 1
            if len(covered) >= 2:
                before += 1
            if n2 >= 2:
                after += 1
            if len(covered) < 2 <= n2:
                gained[kind] += 1

    print(f"\ngroups binding 2+ heads   now {before}   with the stem rule {after}")
    print(f"  gained: {dict(gained)}  total {sum(gained.values())}")


if __name__ == "__main__":
    main(sys.argv[1])
