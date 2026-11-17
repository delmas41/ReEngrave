"""ROADMAP 2.312 -- what the ledger finder saw at Sean's four wrong fallback tiles (2.311 ledger tiles 2, 6, 8, 11), against the printed ledger count his words give.
    PYTHONPATH=.:benchmarks/note-loss-funnel-2026-11:benchmarks/ledger-count-2026-11 python3 benchmarks/ledger-count-2026-11/sean4.py HEADS_ALL.json
"""
import json
import sys

import numpy as np

from checksheet import page_image
from ledger_heights import load
from tools.omr.annotate import ledger_grid as lg

allh = {h["key"]: h for h in json.load(open(sys.argv[1]))}
rows, _ = load("litolff")
sl = rows["staff_lines"]
for t, k, owed in ((2, "glyph/4/0/0/14/4", 1), (6, "glyph/2/1/7/14/0", 3), (8, "glyph/8/1/0/5/5", 2), (11, "glyph/16/1/10/1/7", 2)):
    h = allh[k]
    p, s, st = (int(x) for x in k.split("/")[1:4])
    ys = [float(v) for v in sl["staff/%d/%d/%d" % (p, s, st)]["value"]]
    sp = (ys[4] - ys[0]) / 4
    b = h["box"]
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    g = np.array(page_image("litolff", p).convert("L"))
    above = cy < ys[0]
    edge = ys[0] if above else ys[4]
    r = lg.measure_ledger_rungs(g, ys, cx, head_y=cy, head_box_x=(b[0], b[2]), collapse_edges_box=tuple(b)).get("above" if above else "below", [])
    near = b[3] if above else b[1]
    far = b[1] if above else b[3]
    print("tile", t, "printed ledgers between head and staff:", owed, "| head centre %.2f sp from the staff edge; box %.2f x %.2f sp" % (abs(cy - edge) / sp, (b[2] - b[0]) / sp, (b[3] - b[1]) / sp),
          "| finder rungs (sp from edge):", [round(abs(y - edge) / sp, 2) for y in r], "| box staff-side / far edge at %.2f / %.2f sp" % (abs(near - edge) / sp, abs(far - edge) / sp),
          "| reason:", ((h["ledger_refusal"] or {}).get("detail") or {}).get("ledger_reason", "?")[:60], "| geom", round(h["geom"], 2))
