"""The LINE BRIDGE — multi-membership over a measure cell's two images.

⚠️ THE MECHANISM, stated in `CRITERION.md` before anything was measured. Per
cell:

    intact  = ink(cell.binary)            # lines in
    erased  = ink(cell.image_no_staff)    # lines out
    removed = intact AND NOT erased       # the pixels erasure took

`removed` is the multi-membership set: a pixel there is **staff line AND
(possibly) glyph**. The question is whether treating it as both recovers ink
that either single image alone loses.

⚠️⚠️ THE BRIDGE IS VERTICAL-ONLY, AND THAT IS WHAT STOPS IT DEGENERATING.
A staff line is horizontal, so it breaks VERTICAL strokes; the repair is
therefore vertical. Two erased components are joined when some column `x`
carries a pixel of A at `y1`, a pixel of B at `y2 > y1`, every pixel strictly
between them is in `removed`, and the gap is at most the bound. A bridge can
never run ALONG a line, so it structurally cannot join two marks that stand
side by side on one staff line — which is the 683,000-px re-merge the erasure
exists to prevent.

⚠️ THE BOUND IS IMPORTED, NOT INVENTED: `MeasureCell.staff_line_thickness_canonical`,
the pipeline's own measured line thickness, already on the cell. If the bound
has to be widened past a small multiple of it, that is a finding against the
method, reported rather than tuned away.

⚠️ THE CONTROL IS NAIVE DILATION, and it is the reason this file computes two
joins rather than one. `bridge_join(..., require_removed=False)` joins the same
fragments using only the vertical gap — no multi-membership at all. If naive
dilation does the same job, multi-membership adds nothing; if it joins things
the bridge refuses, the `removed` requirement is what buys the refusal. Every
score in FINDINGS is reported for both arms.
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ── the three pixel sets ─────────────────────────────────────────────────────

def pixel_sets(cell: Any) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """`(intact, erased, removed)` as boolean masks, or None.

    ⚠️ `intact` IS `cell.binary`, NOT `cell.image`. `remove_staff_lines_from_cell`
    starts from `binary` (binarising `image` itself when the cell carries none),
    so binarising `image` here with a different rule would make `removed` the
    difference between two THRESHOLDS as well as the difference between two
    images — and a pixel that changed because I binarised differently is not a
    staff-line pixel. Same rule, same spelling, imported.
    """
    ns = getattr(cell, "image_no_staff", None)
    if ns is None or getattr(ns, "ndim", 0) != 2:
        return None
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
    if binary.shape != ns.shape:
        return None
    intact = binary == 0
    erased = ns == 0
    removed = intact & ~erased
    return intact, erased, removed


def components(mask: np.ndarray):
    """`(n_labels, labels, stats)` for a boolean ink mask, 8-connected."""
    import cv2
    n, labels, stats, _c = cv2.connectedComponentsWithStats(
        mask.astype(np.uint8), 8)
    return n, labels, stats


# ── the join ─────────────────────────────────────────────────────────────────

class _DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def bridge_join(erased_labels: np.ndarray, removed: np.ndarray, *,
                bound: int, require_removed: bool = True
                ) -> Tuple[Dict[int, int], List[Tuple[int, int, int, int]]]:
    """Join erased components across a short vertical gap. Returns (parent, edges).

    `parent` maps every erased label (1..n-1) to its group representative.
    `edges` are `(label_a, label_b, gap_px, x)` — one per bridge found, kept so
    the gap distribution can be reported rather than asserted.

    ⚠️ `require_removed=True` is the multi-membership arm: every pixel strictly
    inside the gap must be a pixel erasure TOOK. `False` is the naive-dilation
    CONTROL: the gap need only be short. They differ exactly where the gap is
    plain paper — i.e. where two marks merely stand near each other vertically
    with no line between them, which is what a control has to be able to expose.
    """
    h, w = erased_labels.shape
    n = int(erased_labels.max()) + 1
    dsu = _DSU(max(n, 1))
    edges: List[Tuple[int, int, int, int]] = []
    if n <= 2 or bound <= 0:
        return {i: i for i in range(n)}, edges

    for x in range(w):
        col = erased_labels[:, x]
        nz = np.flatnonzero(col)
        if nz.size < 2:
            continue
        # Runs of one label in this column, in y order.
        starts = [0]
        for i in range(1, nz.size):
            if nz[i] != nz[i - 1] + 1 or col[nz[i]] != col[nz[i - 1]]:
                starts.append(i)
        starts.append(nz.size)
        runs = [(int(col[nz[starts[k]]]), int(nz[starts[k]]),
                 int(nz[starts[k + 1] - 1])) for k in range(len(starts) - 1)]
        for k in range(len(runs) - 1):
            la, _y0a, y1a = runs[k]
            lb, y0b, _y1b = runs[k + 1]
            if la == lb:
                continue
            gap = y0b - y1a - 1
            if gap < 0 or gap > bound:
                continue
            if require_removed and gap > 0:
                if not removed[y1a + 1:y0b, x].all():
                    continue
            dsu.union(la, lb)
            edges.append((la, lb, int(gap), int(x)))
    return {i: dsu.find(i) for i in range(n)}, edges


def groups_of(parent: Dict[int, int], stats: np.ndarray
              ) -> Dict[int, Dict[str, Any]]:
    """Group representative -> box, area, and the member labels."""
    out: Dict[int, Dict[str, Any]] = {}
    for lab in range(1, stats.shape[0]):
        r = parent.get(lab, lab)
        x, y, w, h, a = (int(stats[lab, k]) for k in range(5))
        g = out.setdefault(r, {"x0": x, "y0": y, "x1": x + w, "y1": y + h,
                               "area": 0, "members": []})
        g["x0"] = min(g["x0"], x)
        g["y0"] = min(g["y0"], y)
        g["x1"] = max(g["x1"], x + w)
        g["y1"] = max(g["y1"], y + h)
        g["area"] += a
        g["members"].append(lab)
    for g in out.values():
        g["w"] = g["x1"] - g["x0"]
        g["h"] = g["y1"] - g["y0"]
    return out


# ── the cell's own units ─────────────────────────────────────────────────────

def cell_units(cell: Any) -> Tuple[Optional[float], Optional[float]]:
    """`(staff space px, line thickness px)` in the CELL's canonical frame.

    ⚠️ BOTH ARE THE CELL'S OWN AND NEITHER IS THE NOMINAL. `_upscale_to_canonical`
    scales a too-wide cell by WIDTH, so `CANONICAL_STAFF_SPAN_PX / 4` is wrong
    on roughly half the cells of one engraved fixture — which is why
    `Q.CELL_STAFF_SPACE` exists as a quantity. Spacing is taken from
    `gather._cell_grid`, the one spelling of that measurement; thickness from
    `staff_line_thickness_canonical`, which `types.py` states is None when the
    staff's lines were never traced.
    """
    from tools.omr.staged.gather import _cell_grid
    grid = _cell_grid(cell)
    spacing = grid[1] * 2.0 if grid else None
    thick = getattr(cell, "staff_line_thickness_canonical", None)
    return (float(spacing) if spacing else None,
            float(thick) if thick else None)


def load_page(pdf: str, page: int, dpi: int = 600):
    """Render + detect staves + cut cells + erase lines. No detector.

    ⚠️ 600 dpi IS THE PLATE'S NATIVE RESOLUTION and the criterion fixes it
    there: the scan is 1-bit at 600 dpi, so rendering above it is pure
    upsampling.
    """
    from tools.omr.staged.pipeline import prepare_pages
    return prepare_pages(pdf, [page], dpi=dpi)[0]
