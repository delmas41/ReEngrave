"""ROADMAP 2.321 -- OUR look (rule 7) at every bar of the Q1/Q3 tile pools (cuts.py's selection), to keep only bars that show the case.

    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/voice-line-of-time-2026-11 python3 benchmarks/voice-line-of-time-2026-11/look_pool.py DIR OUT_DIR PRIOR_KEY
"""
import json
import re
import sys
from pathlib import Path

import cuts as C

D, OUT, PRIOR = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
OUT.mkdir(parents=True, exist_ok=True)
prior = {(k["plate"], k["page"], k["system"], k["staff"], k["cell"]) for k in json.load(open(PRIOR))}
rows = sorted(C.load(D), key=C.place)
crops, labels, key = [], [], []
for r in rows:
    if C.place(r) in prior or not r["cell_box"]:
        continue
    sh = C.split_shape(r)
    if not sh or not C.single_stems(r, sh[1]) or any(C.A2.search(str(t)) for _x, _k, t in r["directions"]):
        continue
    cb = r["cell_box"]
    w = cb[2] - cb[0]
    x0 = (r["prev_box"] or [cb[0] - 0.8 * w])[0]
    x1 = (r["next_box"] or [0, 0, cb[2] + 0.8 * w])[2]
    top, bot, sp = C.staff_geo(r)
    crop, _ = C.cut(r, [cb[0], top - 1.0 * sp, cb[2], bot + 1.0 * sp], x0, x1, None, width=640)
    crops.append(crop)
    labels.append("%d %s p%d s%d st%d c%d" % ((len(crops),) + C.place(r)))
    key.append(dict(n=len(crops), place=C.place(r)))
C.sheet(crops, OUT / "pool_sheet.png", labels, cols=3)
(OUT / "pool.json").write_text(json.dumps(key, indent=1))
print(len(crops))
