"""Per-cell CANONICAL -> PAGE affine, in BOTH axes, with its residual printed.

⚠️ `Q.STEM` is filed on the CELL in canonical coordinates and carries NO page
box (`gather_cv_lines` reads an ERASED cell image and never converts) -- the
*gathered in a frame that cannot answer* shape this repo already records.
`staged.export._stem_probes` converts the stem's x through THE HEAD as its own
ruler, which needs no fit; S3/S4 need the stem's **y** as well, and the head
ruler cannot supply it without ASSUMING the cell rescale is isotropic.

So the map is fitted per cell and per axis over the glyph rows that carry both
frames, and **the isotropy `_stem_probes` relies on is MEASURED here rather
than assumed** -- `ay / ax` is printed as its own control. A cell whose points
do not span a range in an axis has NO map in that axis and is reported, never
approximated.
"""
from __future__ import annotations

import collections
from typing import Any, Dict, List, Optional, Tuple

from tools.omr.staged import export as E
from tools.omr.staged.record import Q

Affine = Tuple[float, float]


def _fit(pts: List[Tuple[float, float]]) -> Optional[Tuple[Affine, float]]:
    xs = [p[0] for p in pts]
    if len(pts) < 2 or (max(xs) - min(xs)) < 1e-6:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    sxy = sum((p[0] - mx) * (p[1] - my) for p in pts)
    if sxx <= 0:
        return None
    a = sxy / sxx
    b = my - a * mx
    resid = max(abs(a * p[0] + b - p[1]) for p in pts)
    return (a, b), resid


def cell_maps(rec) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """`cell key -> {"x": (a,b), "y": (a,b), "rx": .., "ry": ..}` + a report."""
    ptsx: Dict[str, List[Tuple[float, float]]] = collections.defaultdict(list)
    ptsy: Dict[str, List[Tuple[float, float]]] = collections.defaultdict(list)
    for o in rec.obs_of(Q.GLYPH_BOX):
        s = E._parse_subject(o["subject"])
        if s["glyph"] is None:
            continue
        pb = (o.get("detail") or {}).get("bbox_page_px")
        v = o["value"]
        if not pb or not isinstance(v, (list, tuple)) or len(v) < 5:
            continue
        key = f"cell/{s['page']}/{s['system']}/{s['staff']}/{s['cell'] or 0}"
        ptsx[key].append((float(v[1]) + float(v[3]) / 2.0,
                          (float(pb[0]) + float(pb[2])) / 2.0))
        ptsy[key].append((float(v[2]) + float(v[4]) / 2.0,
                          (float(pb[1]) + float(pb[3])) / 2.0))
    maps: Dict[str, Dict[str, Any]] = {}
    rx: List[float] = []
    ry: List[float] = []
    aniso: List[float] = []
    for key in ptsx:
        fx = _fit(ptsx[key])
        fy = _fit(ptsy[key])
        if fx is None or fy is None:
            continue
        maps[key] = {"x": fx[0], "y": fy[0], "rx": fx[1], "ry": fy[1]}
        rx.append(fx[1])
        ry.append(fy[1])
        if fx[0][0] > 0:
            aniso.append(fy[0][0] / fx[0][0])
    rx.sort()
    ry.sort()
    aniso.sort()

    def med(z: List[float]) -> Optional[float]:
        return z[len(z) // 2] if z else None

    return maps, {
        "cells_with_a_map": len(maps),
        "cells_seen": len(ptsx),
        "max_residual_x_median_px": med(rx),
        "max_residual_y_median_px": med(ry),
        "max_residual_x_worst_px": rx[-1] if rx else None,
        "max_residual_y_worst_px": ry[-1] if ry else None,
        "ay_over_ax_median": med(aniso),
        "ay_over_ax_min": aniso[0] if aniso else None,
        "ay_over_ax_max": aniso[-1] if aniso else None,
    }
