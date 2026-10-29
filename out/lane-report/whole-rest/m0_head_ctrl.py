"""whole-rest m0 control: the ink-run height (staff spaces) of black noteheads IN A SPACE vs the whole rests, same measure.
For a box, take its middle-third columns, the contiguous dark run through the box's centre row, in staff spaces.
usage: m0_head_ctrl.py PLATE PKL N"""
import sys, pickle, random, collections
import numpy as np
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
plate, pkl, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
d = pickle.load(open(pkl, "rb"))
sp = {o["subject"]: float(o["value"]) for o in d["observations"] if o["quantity"] == "staff_spacing"}
dec = {v["subject"]: v for v in d["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead"}
heads = [o for o in d["observations"] if o["quantity"] == "glyph_box" and o["value"][0] == "noteheadBlackInSpace"
         and (o.get("detail") or {}).get("bbox_page_px") and not (dec.get(o["subject"]) or {}).get("value")]
random.seed(2); heads = random.sample(heads, min(n, len(heads)))
heads.sort(key=lambda o: int(o["subject"].split("/")[1]))
cache = {}; hs = []
for o in heads:
    s = o["subject"]; p = s.split("/"); pg = int(p[1])
    if pg not in cache:
        cache.clear(); cache[pg] = np.asarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb).mean(axis=2) < 140
    dark = cache[pg]; x0, y0, x1, y1 = o["detail"]["bbox_page_px"]; u = sp["staff/%s/%s/%s" % tuple(p[1:4])]
    cx0, cx1 = int(x0 + (x1 - x0) / 3), int(x1 - (x1 - x0) / 3)
    prof = dark[:, cx0:cx1].mean(axis=1) >= 0.7
    c = int((y0 + y1) / 2)
    if not prof[c]:
        continue
    a = c
    while a > 0 and prof[a - 1]: a -= 1
    b = c
    while b < len(prof) - 1 and prof[b + 1]: b += 1
    hs.append((b - a + 1) / u)
hs = np.array(hs)
print("black notehead in space, n=%d, ink run height sp percentiles 0/10/25/50/75/100:" % len(hs), np.round(np.percentile(hs, [0, 10, 25, 50, 75, 100]), 2))
