"""lane-farhead-5-6: why `_jut_from_head_ink` names line_y 5722 for brahms 25/1/5/5/1 (the ledger is at 5731). Read only."""
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np
import farhead_5_6_diag as D
import overnight_1004_report as R
from tools.omr.annotate import ledger_grid as lg

src, s = sys.argv[1:3]
data, rep = D.load(src)
g, r, cap, gl, ctx = D.read_one(rep, data, s)
gray = rep.gray_of(R.page_of(s))
sp = cap["sp"]
jf = lg._jut_from_head_ink(gray, tuple(g["box"]), sp, None)
print({k: v for k, v in jf.items()})
x0, y0, x1, y1 = g["box"]
mid = (y0 + y1) / 2
print("mid", mid, "sp", sp, "tol_px", lg.MIDDLE_ROW_TOL_SPACES * sp, "need", lg.RUNG_STUB_MIN_SPACES * sp, "cap", lg.LEDGER_THICKNESS_MAX_SPACES * sp)
thr = lg._otsu_threshold(gray[int(mid - 5):int(mid + 5), int(x0 - 40):int(x1 + 40)])
print("thr", thr)
for c in range(int(jf["run_x"][0]) - 2, int(jf["run_x"][1]) + 3):
    col = gray[int(mid - 20):int(mid + 21), c] <= thr
    ys = [int(mid - 20) + i for i, v in enumerate(col) if v]
    print(c, "head" if jf["head_x"][0] <= c < jf["head_x"][1] else "jut ", ys[:1], ys[-1:], len(ys))
