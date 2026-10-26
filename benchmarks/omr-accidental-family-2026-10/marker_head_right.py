"""2.201 pre-check of the role-by-position exclusion: of the key-signature marker rows a gathered record holds, how many stand directly left of a notehead
at their own height (the `head_right` test the family gather uses to call a mark in-bar)? usage: marker_head_right.py GATHERED.record.json"""
import json, sys, collections
from tools.omr.staged import gather as G
d = json.load(open(sys.argv[1]))
obs = d["record"]["observations"] if "record" in d else d["observations"]
boxes = collections.defaultdict(list)       # cell key -> glyph boxes (cls, x, y, w, h, category)
for o in obs:
    if o["quantity"] == "glyph_box":
        sub = o["subject"]
        cell = "/".join(sub.split("/")[:5]).replace("glyph", "cell")
        v = o["value"]
        boxes[cell].append((v[0], v[1], v[2], v[3], v[4], (o.get("detail") or {}).get("category")))
tot = collections.Counter(); ex = []
for o in obs:
    if o["quantity"] != "keysig_marker":
        continue
    dd = o.get("detail") or {}
    sub = o["subject"]                      # staff/p/s/i ; cell 0
    cell = "cell/" + "/".join(sub.split("/")[1:4]) + "/0"
    sp = dd.get("cell_staff_space") or 0
    x, yc = dd.get("x"), dd.get("y_center")
    mine = [b for b in boxes.get(cell, ()) if b[0] == dd.get("detector_class") and abs(b[1] - x) < 0.6 and abs(b[2] + b[4] / 2 - yc) <= 1.5]
    if not mine or not sp:
        tot["unmatched"] += 1; continue
    m = mine[0]
    x1 = m[1] + m[3]
    tot["markers"] += 1
    tot["role_" + str(dd.get("detector_role"))] += 1
    hit = None
    meters = [b for b in boxes[cell] if str(b[0]).lower().startswith("timesig")]
    if any(x1 - 0.25 * sp <= mt[1] <= x1 + 1.5 * sp for mt in meters):
        tot["meter_follows_so_not_in_bar"] += 1
        continue
    for h in boxes[cell]:
        if h[5] != "notehead" or any(mt[1] <= h[1] + h[3] / 2.0 <= mt[1] + mt[3] and mt[2] <= h[2] + h[4] / 2.0 <= mt[2] + mt[4] for mt in meters):
            continue
        gap = (h[1] - x1) / sp
        if gap < -0.25 or gap > G.FAMILY_HEAD_GAP_SPACES:
            continue
        dy = abs((h[2] + h[4] / 2.0) - (m[2] + m[4] * 0.6)) / (sp / 2.0)
        if dy <= G.FAMILY_HEAD_DY_STEPS:
            hit = (round(gap, 2), round(dy, 2)); break
    if hit:
        tot["would_be_in_bar"] += 1; tot["in_bar_role_" + str(dd.get("detector_role"))] += 1; ex.append((sub, dd.get("detector_class"), round(x), hit))
print(dict(tot)); print(ex[:12])
