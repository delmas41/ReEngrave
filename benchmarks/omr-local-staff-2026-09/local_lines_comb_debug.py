"""lane-local-staff-lines debug: the comb score curve for one head's candidate staff.
  python3 local_lines_comb_debug.py <scratch> <doc> <subject> <staff key>"""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import numpy as np
import offbox_measured as OM
S, doc, s, key = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
data = json.load(open(S / "x" / f"{doc}-20261006-night-combined.json"))
rep = OM.CachedReplay(doc, data)
page = int(s.split("/")[1])
g = rep.gray_of(page)
gl = sorted(data["staff_lines"][key])
x0, y0, x1, y1 = data["glyphs"][s]["box"]
w = x1 - x0
sp = (gl[-1] - gl[0]) / 4
for a, b in ((int(x0 - 2 * w), int(x0 - w)), (int(x1 + w), int(x1 + 2 * w))):
    prof = g[:, a:b].astype(float).mean(axis=1)
    med = np.median(prof)
    sh = np.arange(-int(0.8 * sp), int(0.8 * sp) + 1, 0.5)
    sc = np.array([sum(max(0, med - prof[int(round(y + d))]) for y in gl) for d in sh])
    print((a, b), "med", round(med, 1), "max", round(sc.max(), 1))
    print([(float(d), round(float(v) / sc.max(), 2)) for d, v in zip(sh, sc) if v >= 0.85 * sc.max()])
