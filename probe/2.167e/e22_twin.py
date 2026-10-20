"""2.167e probe 22: one head boxed twice in two head CLASSES (black + half/whole, IoU >= 0.8), BOTH kept (neither refused as a duplicate): the tile-2 shape (a black eighth head
also boxed as a hollow half; EVALUATE groups both into one chord and the longer value is written). usage: e22_twin.py PLATE"""
import json
import sys
import collections

pl = sys.argv[1]
G = json.load(open("probe/2.167e/data/%s_all.json" % pl))
red = json.load(open("probe/2.167e/data/%s_red_rows.json" % pl))
redcells = {(b["page"], b["system"], b["staff"], b["cell"]) for b in red}
cells = collections.defaultdict(list)
for s, g in G.items():
    if str(g.get("cls", "")).startswith("notehead") and g.get("bb"):
        nn = g.get("V", {}).get("notehead_is_not_a_notehead")
        if nn and nn[2] is True:
            continue
        cells[tuple(int(x) for x in s.split("/")[1:5])].append(s)


def iou(a, b):
    iw = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    ih = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    i = iw * ih
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def fam(c):
    return "black" if "Black" in c else ("half" if "Half" in c else ("whole" if "Whole" in c else c))


pairs = []
for key, subs in cells.items():
    for i, a in enumerate(subs):
        for b in subs[i + 1:]:
            ga, gb = G[a], G[b]
            if fam(ga["cls"]) != fam(gb["cls"]) and iou(ga["bb"], gb["bb"]) >= 0.8:
                pairs.append((a, b, fam(ga["cls"]) + "+" + fam(gb["cls"]), key in redcells))
print(pl, "one head, two classes, both kept:", len(pairs), collections.Counter(p[2] for p in pairs), "| in red bars:", sum(1 for p in pairs if p[3]))
json.dump(pairs, open("probe/2.167e/data/%s_twin.json" % pl, "w"))
