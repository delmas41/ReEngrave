"""ROADMAP 2.105 (c): the width/height population of every `rest*` box, in staff
spaces, kept vs refused, with whether it stands on its cell's edge (a barline
column).  usage: PYTHONPATH=. python3 rest_widths.py RECORD"""
import collections
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
sp_of = {}
for o in run.observations:
    if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
        ys = o["value"]
        sp_of[o["subject"]] = (ys[-1] - ys[0]) / (len(ys) - 1)
cellbox = {}
for o in run.observations:
    if o["quantity"] == Q.CELL_BOX and isinstance(o["value"], list):
        cellbox[o["subject"]] = o["value"]
rows = []
for g in run.glyphs.values():
    if not (g.cls or "").startswith("rest") or g.box_page is None:
        continue
    sp = sp_of.get(g.staff_key)
    if not sp:
        continue
    b = g.box_page
    w, h = (b[2] - b[0]) / sp, (b[3] - b[1]) / sp
    cb = cellbox.get(g.cell_key)
    edge = None
    if cb:
        edge = min(abs(b[0] - cb[0]), abs(b[2] - cb[0]), abs(b[0] - cb[2]), abs(b[2] - cb[2])) / sp
    st, why = adjudicate_status(run, g)
    rows.append((w, h, edge, st, g.cls, g.key, why[0] if why else ""))
rows.sort()
print("n rest boxes", len(rows))
print("narrowest 40 (w_sp, h_sp, edge_sp, status, class, key, why):")
for r in rows[:40]:
    print(f"{r[0]:.2f} {r[1]:.2f} {('%.2f' % r[2]) if r[2] is not None else '-'} {r[3]} {r[4]} {r[5]} {r[6][:60]}")
kept = [r for r in rows if r[3] != "refused"]
print("kept narrowest 10:", [(round(r[0], 2), r[4], r[5]) for r in kept[:10]])
by = collections.defaultdict(list)
for r in kept:
    by[r[4]].append(r[0])
for k, v in sorted(by.items()):
    v.sort()
    print(k, len(v), "min", round(v[0], 2), "p5", round(v[len(v) // 20], 2), "median", round(v[len(v) // 2], 2))
