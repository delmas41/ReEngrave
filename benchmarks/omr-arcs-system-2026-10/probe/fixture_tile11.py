"""ROADMAP 2.166 -- cut the test fixture for Sean's tile 11 (Brahms 317803 pdf 1, `glyph/1/1/11/1/21`: a tie in bar 1 our
trace carried across the barline onto the SLUR in bar 0). Writes tools/omr/tests/data/system_arc_tile11.npz:
composite (page ink, staff lines removed) and raw crops (bit-packed), the arc piece box, the system's x extent, the
cell edges, the staff lines and the head boxes, all in crop pixels; plus the space.
usage: fixture_tile11.py"""
import os
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arcs-system-2026-10/probe")
import numpy as np  # noqa: E402

import arc_debug  # noqa: E402
from tools.omr.staged import arcs_system as AS  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402

X0, Y0, X1, Y1 = 1291, 6532, 1656, 6841          # the tile's own page crop (out/2.166/tiles-key.json, tile 11)
pws, cells, local, dets, log, summary, traces = arc_debug.run("brahms", 1)
ink = AS.composite_ink(pws.page.binary, cells)[Y0:Y1, X0:X1]
raw = (pws.page.binary < 128)[Y0:Y1, X0:X1]
arcs, heads, edges = [], [], set()
for c in cells:
    key = local.get(c.staff_index)
    if key is None or key != (1, 11):
        continue
    edges.update([c.bbox_page_px[0] - X0, c.bbox_page_px[2] - X0])
    for gi, d in enumerate(dets.get(R.cell(1, key[0], key[1], c.measure_index).to_key(), ())):
        b = AS._page_box(c, d)
        if b[2] < X0 or b[0] > X1 or b[3] < Y0 or b[1] > Y1:
            continue
        bb = [b[0] - X0, b[1] - Y0, b[2] - X0, b[3] - Y0]
        if d.smufl_name in ("tie", "slur"):
            arcs.append(bb + [c.measure_index])
        elif str(d.smufl_name).startswith("notehead"):
            heads.append(bb)
sp = AS._space_page([c for c in cells if local.get(c.staff_index) == (1, 11)][0])
lines = [y - Y0 for st in pws.staves for y in st.line_ys if Y0 <= y <= Y1]
os.makedirs("tools/omr/tests/data", exist_ok=True)
np.savez_compressed("tools/omr/tests/data/system_arc_tile11.npz", composite=np.packbits(ink), raw=np.packbits(raw),
                    shape=np.array(ink.shape), arcs=np.array(arcs, float), heads=np.array(heads, float),
                    edges=np.array(sorted(edges), float), lines=np.array(lines, float), sp=np.array(sp))
print("arcs", arcs, "heads", len(heads), "edges", sorted(edges), "sp", sp)
