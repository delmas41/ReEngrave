"""ROADMAP 2.153 -- on an interior_white-INJECTED slice (probe), the distribution of `rows_share` over head-sized, BLACK-classed
notehead boxes, by bin, and how many of Sean's judged tiles sit in each bin (truth = Sean's value >= 2 -> half or longer).
usage: zone_2_153.py SLICE_IW.json DOC"""
import collections
import json
import sys

SL, DOC = sys.argv[1:3]
rec = json.load(open(SL))
tiles = {t["glyph"]: t for t in json.load(open("out/2.153/notes.json"))[DOC]}
cls, ink, box, space = {}, {}, {}, {}
for o in rec["observations"]:
    q = o["quantity"]
    if q == "notehead_class":
        cls[o["subject"]] = o["value"]
    elif q == "notehead_ink":
        ink[o["subject"]] = o["detail"]
    elif q == "glyph_box":
        box[o["subject"]] = o["detail"].get("bbox_page_px")
    elif q == "cell_staff_space":
        space[o["subject"]] = o["value"]


def cell_of(g):
    p = g.split("/")
    return "cell/%s/%s/%s/%s" % tuple(p[1:5])


def bin_of(r):
    return "0" if r == 0 else ("(0,.06]" if r <= 0.06 else ("(.06,.18)" if r < 0.18 else ">=.18"))


import statistics
hs = [(box[g][3] - box[g][1], box[g][2] - box[g][0]) for g in ink if g in box and box[g] and "lack" in str(cls.get(g, "")).lower()]
mh, mw = statistics.median(h for h, _ in hs), statistics.median(w for _, w in hs)
allc, tc = collections.Counter(), collections.defaultdict(collections.Counter)
for g, d in ink.items():
    iw = d.get("interior_white")
    if not iw or "lack" not in str(cls.get(g, "")).lower() or g not in box or box[g] is None:
        continue
    x0, y0, x1, y1 = box[g]
    h, w = (y1 - y0) / mh, (x1 - x0) / mw
    if not (0.75 <= h <= 1.5 and 0.75 <= w <= 1.5):
        allc["not head-sized (vs the document median box)"] += 1
        continue
    b = bin_of(iw["rows_share"])
    allc[b] += 1
    if g in tiles:
        tc[b]["half+" if tiles[g]["beats"] >= 2 else "black"] += 1
print("median black-head box h x w (page px): %.1f x %.1f" % (mh, mw))
print("black-class heads by rows_share bin (head-sized boxes):", dict(allc))
for b, c in tc.items():
    print("  judged tiles in", b, dict(c))
