"""ROADMAP 2.105 (a): kept filled heads whose page box overlaps/abuts (gap <= tol sp)
a KEPT flagged-rest box (rest8th..rest128th) in the same staff. usage: head_rest_abut.py RECORD [tol]"""
import sys

from tools.omr.staged.readout import load_run, adjudicate_status
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
tol = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
sp = {}
for o in run.observations:
    if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
        sp[o["subject"]] = (o["value"][-1] - o["value"][0]) / (len(o["value"]) - 1)
by_staff = {}
for g in run.glyphs.values():
    if g.box_page is None or g.staff_key not in sp:
        continue
    by_staff.setdefault(g.staff_key, []).append(g)
n = 0
for st, gs in by_staff.items():
    s = sp[st]
    heads = [g for g in gs if (g.cls or "").startswith("noteheadBlack") and adjudicate_status(run, g)[0] != "refused"]
    rests = [g for g in gs if (g.cls or "") in ("rest8th", "rest16th", "rest32nd", "rest64th", "rest128th")
             and adjudicate_status(run, g)[0] != "refused"]
    for h in heads:
        for r in rests:
            a, b = h.box_page, r.box_page
            dx = max(a[0], b[0]) - min(a[2], b[2])
            dy = max(a[1], b[1]) - min(a[3], b[3])
            if dx <= tol * s and dy <= tol * s:
                n += 1
                ix, iy = max(0.0, -dx), max(0.0, -dy)
                print(h.key, h.cls, r.key, r.cls, "overlap/head_area",
                      round(ix * iy / ((a[2] - a[0]) * (a[3] - a[1])), 3), "ix_sp", round(ix / s, 2), "iy_sp", round(iy / s, 2))
print("pairs", n)
