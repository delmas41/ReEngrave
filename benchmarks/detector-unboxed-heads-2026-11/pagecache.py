"""Per-page helper: load master cells, find the cells holding a page point, serve boxes from the cache. MEASUREMENT ONLY."""
import sys
sys.path.insert(0, '.'); sys.path.insert(0, 'benchmarks/detector-unboxed-heads-2026-11')
import cachelook as cl
from tools.omr.staged import cell_map
from tools.omr.staged.gather import _system_local

_P = {}


def page(doc, pg):
    k = (doc, pg)
    if k not in _P:
        (pws, cells), = cell_map.load_prepared(cl.PDF[doc], [pg])
        _P[k] = (pws, cells, _system_local(pws.staves))
    return _P[k]


def cells_at(doc, pg, px, py):
    """Master cells whose page rectangle contains the page point -> list of (cell, (system, staffLocal, measure))."""
    pws, cells, local = page(doc, pg)
    out = []
    for c in cells:
        x0, y0, x1, y1 = c.bbox_page_px
        if x0 <= px <= x1 and y0 <= py <= y1:
            k = local.get(c.staff_index)
            out.append((c, (k[0], k[1], c.measure_index) if k else None))
    return out
