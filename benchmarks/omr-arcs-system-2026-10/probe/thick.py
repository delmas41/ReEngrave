"""ROADMAP 2.166 -- stroke thickness of traced arcs vs detector beam boxes, in spaces (debug). usage: thick.py DOC PAGE"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "benchmarks/omr-arcs-system-2026-10/probe")
import numpy as np  # noqa: E402

import arc_debug  # noqa: E402
from tools.omr.staged import arcs_system as AS  # noqa: E402
from tools.omr.staged import record as R  # noqa: E402

pws, cells, local, dets, log, summary, traces = arc_debug.run(sys.argv[1], int(sys.argv[2]))
sp = np.median([a["space_page_px"] for a in summary["arcs_detail"]])
med = [np.median([b - a + 1 for a, b in t["points"].values()]) / sp for t in traces if t["points"]]
p90 = [np.percentile([b - a + 1 for a, b in t["points"].values()], 90) / sp for t in traces if t["points"]]
print("sp", sp, "trace median thickness pct", np.percentile(med, [10, 50, 90]).round(2), "p90 of p90", np.percentile(p90, [50, 90]).round(2))
ink = AS.composite_ink(pws.page.binary, cells)
bt = []
for c in cells:
    key = local.get(c.staff_index)
    if key is None:
        continue
    for d in dets.get(R.cell(c.page_index, key[0], key[1], c.measure_index).to_key(), ()):
        if d.smufl_name == "beam":
            b = AS._page_box(c, d)
            xm = int((b[0] + b[2]) / 2)
            runs = [bb - aa + 1 for aa, bb in AS._runs(ink[int(b[1]):int(b[3]) + 1, xm])]
            if runs:
                bt.append(max(runs) / sp)
print("beam runs at box middle (max run) pct", np.percentile(bt, [10, 25, 50, 90]).round(2), len(bt))
