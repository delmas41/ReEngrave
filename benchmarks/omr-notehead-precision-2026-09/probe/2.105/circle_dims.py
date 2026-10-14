"""ROADMAP 2.105 (b): for each MUTUAL circle (A refused stacked_head_duplicate
for B, B refused notehead_is_a_duplicate_box for A): the width/height in
spaces of both boxes. usage: circle_dims.py RECORD"""
import sys

from tools.omr.staged.readout import load_run
from tools.omr.staged.record import Q

run = load_run(sys.argv[1])
subj_of = {o["id"]: o["subject"] for o in run.observations if o["quantity"] in (Q.GLYPH_BOX, Q.STACKED_HEAD_FIT)}
sp = {}
for o in run.observations:
    if o["quantity"] == Q.STAFF_LINES and isinstance(o["value"], list) and len(o["value"]) >= 2:
        sp[o["subject"]] = (o["value"][-1] - o["value"][0]) / (len(o["value"]) - 1)


def standing(k):
    v = run.standing(k, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, "ADJUDICATE") or {}
    return v.get("reason"), subj_of.get((v.get("detail") or {}).get("duplicate_of"))


def dims(k):
    g = run.glyphs[k]
    b = g.box_page
    s = sp[g.staff_key]
    return round((b[2] - b[0]) / s, 2), round((b[3] - b[1]) / s, 2), round(g.score or 0, 2)


n = 0
for k in sorted(run.glyphs):
    r, w = standing(k)
    if r != "stacked_head_duplicate" or not w:
        continue
    r2, w2 = standing(w)
    if r2 == "notehead_is_a_duplicate_box" and w2 == k:
        n += 1
        print(k, "A(2.42-refused)", dims(k), "B(2.30-refused)", w, dims(w))
print("mutual circles:", n)
