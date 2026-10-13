"""keys of kept restQuarter boxes with width in [lo,hi) spaces and edge flag.
usage: rest_keys.py RECORD lo hi edge(0/1)"""
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
lo, hi, want = float(sys.argv[2]), float(sys.argv[3]), bool(int(sys.argv[4]))
sp_of, cellbox = {}, {}
for o in run.observations:
    if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
        ys = o["value"]
        sp_of[o["subject"]] = (ys[-1] - ys[0]) / (len(ys) - 1)
    if o["quantity"] == Q.CELL_BOX and isinstance(o["value"], list):
        cellbox[o["subject"]] = o["value"]
for g in sorted(run.glyphs.values(), key=lambda g: g.key):
    if g.cls != "restQuarter" or g.box_page is None:
        continue
    sp, cb = sp_of.get(g.staff_key), cellbox.get(g.cell_key)
    if not sp or not cb or adjudicate_status(run, g)[0] == "refused":
        continue
    b = g.box_page
    w = (b[2] - b[0]) / sp
    edge = min(abs(b[0] - cb[0]), abs(b[2] - cb[0]), abs(b[0] - cb[2]), abs(b[2] - cb[2])) / sp <= 0.15
    if lo <= w < hi and edge == want:
        print(g.key, round(w, 2), round((b[3] - b[1]) / sp, 2))
