"""ROADMAP 2.166 -- trace Sean's tile 11 fixture and print the trace's centre y per 4 columns (debug)."""
import sys

sys.path.insert(0, ".")
import numpy as np  # noqa: E402

from tools.omr.staged import arcs_system as AS  # noqa: E402

z = np.load("tools/omr/tests/data/system_arc_tile11.npz")
shape = tuple(z["shape"])
ink = np.unpackbits(z["composite"])[:shape[0] * shape[1]].reshape(shape).astype(bool)
raw = np.unpackbits(z["raw"])[:shape[0] * shape[1]].reshape(shape).astype(bool)
sp = float(z["sp"])
box = z["arcs"][0][:4]
t = AS.trace_arc(ink, box, sp, x_min=box[0] - AS.CUT_EXTEND_SPACES * sp, x_max=box[2] + AS.FREE_EXTEND_SPACES * sp, raw=raw)
print("box", box.round(), "cov", t["coverage"], "x", t["x0"], t["x1"])
print([(x, round(sum(r) / 2.0)) for x, r in sorted(t["points"].items())][::4])
for x in (150, 160, 170, 180, 185, 190, 195):
    print(x, AS._runs(ink[100:200, x]))
