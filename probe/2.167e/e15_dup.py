"""2.167e probe 15 (Q2): the rest boxes refused `rest_is_a_duplicate_box`: how much did they overlap the box that refused them? A real duplicate is the SAME ink
boxed twice (IoU high, centres together); a real NEIGHBOUR (two eighth rests side by side) overlaps a little at the box edge (IoU low, centres a box apart).
usage: e15_dup.py ALL.json OUT.json"""
import json
import sys
import collections

G = json.load(open(sys.argv[1]))
RESTCLS = ("rest8th", "rest16th", "restQuarter", "restWhole", "restHalf")
cells = collections.defaultdict(list)
for sub, g in G.items():
    if g.get("cls") in RESTCLS and g.get("bb"):
        cells[tuple(sub.split("/")[1:5])].append(sub)


def iou(a, b):
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = iw * ih
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


rows = []
for key, subs in cells.items():
    for s in subs:
        g = G[s]
        v = g.get("V", {}).get("rest_is_not_a_rest")
        if not (v and v[2] is True and v[1] == "rest_is_a_duplicate_box"):
            continue
        best = None
        for s2 in subs:
            if s2 == s:
                continue
            g2 = G[s2]
            o = iou(g["bb"], g2["bb"])
            if o >= 0.02 and (best is None or o > best[0]):
                best = (o, s2)
        if best is None:
            continue
        g2 = G[best[1]]
        w = max(g["bb"][2] - g["bb"][0], 1.0)
        dx = abs((g["bb"][0] + g["bb"][2]) / 2 - (g2["bb"][0] + g2["bb"][2]) / 2) / w
        dy = abs((g["bb"][1] + g["bb"][3]) / 2 - (g2["bb"][1] + g2["bb"][3]) / 2) / max(g["bb"][3] - g["bb"][1], 1.0)
        rows.append(dict(sub=s, cls=g["cls"], conf=g.get("conf"), bb=g["bb"], other=best[1], other_cls=g2["cls"], other_conf=g2.get("conf"),
                         other_bb=g2["bb"], iou=round(best[0], 3), dx=round(dx, 2), dy=round(dy, 2),
                         other_refused=bool(g2.get("V", {}).get("rest_is_not_a_rest", [0, 0, False])[2])))
print("rest boxes refused as a duplicate:", len(rows), collections.Counter(r["cls"] for r in rows))
for cls in ("rest8th", "restQuarter", "restWhole"):
    rr = [r for r in rows if r["cls"] == cls]
    if not rr:
        continue
    ious = sorted(r["iou"] for r in rr)
    print(cls, "n", len(rr), "IoU quartiles", ious[len(ious) // 4], ious[len(ious) // 2], ious[3 * len(ious) // 4],
          "| IoU<0.15:", sum(1 for r in rr if r["iou"] < 0.15), "| IoU<0.15 and centres >=0.6 box widths apart:",
          sum(1 for r in rr if r["iou"] < 0.15 and r["dx"] >= 0.6), "| the refusing box itself refused:", sum(1 for r in rr if r["other_refused"]))
json.dump(rows, open(sys.argv[2], "w"))
