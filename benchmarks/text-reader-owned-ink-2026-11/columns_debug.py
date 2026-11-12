"""ROADMAP 2.304: the barline columns of a page as the ledger carves them: x, carved width, carved rows against the column's own height. A look, not evidence.

    python3 benchmarks/text-reader-owned-ink-2026-11/columns_debug.py PDF PAGE
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from tools.omr.staged import barline_columns as BC  # noqa: E402
from tools.omr.staged import page_strokes as PS  # noqa: E402
from tools.omr.staged.pipeline import prepare_pages  # noqa: E402

pdf, page = sys.argv[1], int(sys.argv[2])
((pws, cells),) = prepare_pages(pdf, [page], dpi=600)
sp = float(np.median([s.line_spacing_px for s in pws.staves]))
cols = BC.fit_columns(pws)
canvas = pws.page.binary.copy()
got = {}
for c in cols:
    for b in PS.carve_columns(canvas, [c], sp):
        got[(c["system"], c["x"])] = b
print("sp %.1f; %d columns" % (sp, len(cols)))
for c in cols:
    b = got.get((c["system"], c["x"]))
    h = c["y1"] - c["y0"]
    print("sys %d x %7.1f  votes-staves %d/%d  column h %5.0f px (%.0f sp)  carved: %s" % (
        c["system"], c["x"], len(c["staves"]), c["n_staves"], h, h / sp,
        "none" if b is None else "width %d px (%.2f sp)  rows %d (%.0f%% of column)  ink %d px" % (b["width_px"], b["width_px"] / sp, b["rows"], 100.0 * b["rows"] / max(1, h), b["ink_px"])))
