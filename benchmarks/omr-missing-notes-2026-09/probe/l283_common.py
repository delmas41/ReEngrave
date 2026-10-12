"""l283_common: shared loading for the ROADMAP 2.83 probes -- the cached cells (l283_cells.py), Sean's truth (l281_truth)
and the matching of a CV stem (cell canonical frame) to one of his stem boxes (page frame)."""
import gzip
import pickle
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402


def load_cells(path):
    with gzip.open(path, "rb") as fh:
        return pickle.load(fh)


def to_page(cell, x, y, w=0.0, h=0.0):
    """canonical (x, y, w, h) -> page px (x0, y0, x1, y1)."""
    bx0, by0, _bx1, _by1 = cell["bbox_page_px"]
    s = cell["scale"]
    return (bx0 + x / s, by0 + y / s, bx0 + (x + w) / s, by0 + (y + h) / s)


def cell_space(cell):
    ls = cell["lines"]
    return (ls[-1] - ls[0]) / (len(ls) - 1) if len(ls) >= 2 else None


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def cv_stems_page(cells):
    """[(page_rect, cell_key, stem_index, cell)] for every cached CV stem."""
    out = []
    for key, c in cells.items():
        for i, s in enumerate(c["stems"]):
            out.append((to_page(c, *s), key, i, c))
    return out


def match_truth_stems(T, stems_page):
    """truth stem id -> best CV stem (by x overlap and y overlap), with the overlap fraction of the truth stem's
    length. A stem Sean boxed that the CV rung did not find maps to None."""
    out = {}
    for ts in T.stems:
        r = ts.rect
        best = None
        for sp_, key, i, c in stems_page:
            ox = min(r[2], sp_[2]) - max(r[0], sp_[0])
            if ox <= 0:
                # allow a pixel or two of slack on a thin stem
                if max(r[0], sp_[0]) - min(r[2], sp_[2]) > 3:
                    continue
            oy = min(r[3], sp_[3]) - max(r[1], sp_[1])
            if oy <= 0:
                continue
            frac = oy / max(1.0, r[3] - r[1])
            if best is None or frac > best[0]:
                best = (frac, key, i, c, sp_)
        if best and best[0] >= 0.5:
            out[ts.id] = best
    return out
