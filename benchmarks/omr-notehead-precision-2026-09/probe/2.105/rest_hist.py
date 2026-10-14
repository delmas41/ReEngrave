"""ROADMAP 2.105 (c): histogram of kept `restQuarter` widths (staff spaces),
split by 'flush on a cell edge (<= 0.15 sp)'. usage: rest_hist.py RECORD"""
import collections
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
sp_of = {}
cellbox = {}
for o in run.observations:
    if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
        ys = o["value"]
        sp_of[o["subject"]] = (ys[-1] - ys[0]) / (len(ys) - 1)
    if o["quantity"] == Q.CELL_BOX and isinstance(o["value"], list):
        cellbox[o["subject"]] = o["value"]
hist = collections.Counter()
for g in run.glyphs.values():
    if g.cls != "restQuarter" or g.box_page is None:
        continue
    sp = sp_of.get(g.staff_key)
    cb = cellbox.get(g.cell_key)
    if not sp or not cb:
        continue
    st, _ = adjudicate_status(run, g)
    if st == "refused":
        continue
    b = g.box_page
    w = (b[2] - b[0]) / sp
    h = (b[3] - b[1]) / sp
    edge = min(abs(b[0] - cb[0]), abs(b[2] - cb[0]), abs(b[0] - cb[2]), abs(b[2] - cb[2])) / sp
    hist[(round(int(w * 10) / 10, 1), edge <= 0.15)] += 1
for k in sorted(hist):
    print(k, hist[k])
