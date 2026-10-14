"""kept rest boxes of a record nearest a cell edge (width >= 0.8 sp), for tile controls.
usage: ctrl_rests.py RECORD"""
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
sp, cb = {}, {}
for o in run.observations:
    if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
        sp[o["subject"]] = (o["value"][-1] - o["value"][0]) / (len(o["value"]) - 1)
    if o["quantity"] == Q.CELL_BOX and isinstance(o["value"], list):
        cb[o["subject"]] = o["value"]
rows = []
for g in run.glyphs.values():
    if not (g.cls or "").startswith("rest") or g.box_page is None or g.staff_key not in sp or g.cell_key not in cb:
        continue
    if adjudicate_status(run, g)[0] == "refused":
        continue
    b, c, s = g.box_page, cb[g.cell_key], sp[g.staff_key]
    w = (b[2] - b[0]) / s
    e = min(abs(b[0] - c[0]), abs(b[2] - c[0]), abs(b[0] - c[2]), abs(b[2] - c[2])) / s
    if w >= 0.8:
        rows.append((round(e, 2), round(w, 2), g.cls, g.key))
rows.sort()
for r in rows[:12]:
    print(r)
