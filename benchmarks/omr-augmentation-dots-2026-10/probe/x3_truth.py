"""2.180 probe 3: Sean's Brahms 317803 page 0 labels (131 augmentationDot) against our dot fates (x2) and the boxes that are
NOT truth dots but carry a dot fate on page 0. usage: x3_truth.py BRA_X1.json BRA_FATES.json"""
import collections
import json
import sys

G = json.load(open(sys.argv[1]))
F = json.load(open(sys.argv[2]))
T = json.load(open("data/hand-truth/pages/imslp317803/0.json"))["boxes"]
tdots = [b["rect"] for b in T if b["cls"] == "augmentationDot"]
theads = [b["rect"] for b in T if b["cls"].startswith("notehead")]
tstacc = [b for b in T if b["cls"].startswith("artic")]


def c(r):
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


ours = [f for f in F if f["dot"].startswith("glyph/0/")]
used = set()
tab = collections.Counter()
miss = []
for r in tdots:
    cx, cy = c(r)
    best, bd = None, 1e9
    for i, f in enumerate(ours):
        bb = f["bb"]
        if not bb:
            continue
        x, y = c(bb)
        d = abs(x - cx) + abs(y - cy)
        if d < bd:
            bd, best = d, i
    if best is None or bd > 12:
        # a box of ANY class there? (dot boxed as something else, or not boxed / under the floor)
        other = [(k, g.get("cls"), g.get("conf")) for k, g in G.items() if k.startswith("glyph/0/") and g.get("bb")
                 and abs(c(g["bb"])[0] - cx) + abs(c(g["bb"])[1] - cy) < 12]
        tab["not_a_dot_box:" + (other[0][1] if other else "none")] += 1
        miss.append(dict(truth=r, other=other))
        continue
    used.add(best)
    f = ours[best]
    tab[f["fate"]] += 1
print("truth dots", len(tdots), "articulation truth boxes", len(tstacc))
for k, n in sorted(tab.items()):
    print("  %4d %s" % (n, k))
non = collections.Counter(f["fate"] for i, f in enumerate(ours) if i not in used)
print("our dot boxes on p0 that are NOT truth aug dots:", sum(non.values()))
for k, n in sorted(non.items()):
    print("  %4d %s" % (n, k))
json.dump(miss, open("/dev/stdout", "w")) if "-v" in sys.argv else None
