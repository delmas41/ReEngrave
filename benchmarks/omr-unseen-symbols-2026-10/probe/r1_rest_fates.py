"""ROADMAP 2.179 -- in the red bars of a census: every rest box refused by a gate, and whether a KEPT box of the rest family stands
on the same ink (then the refusal lost nothing). Prints per reason: refused, lost (no kept rest on that ink)."""
import collections
import json
import sys


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy; u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0


def same(a, b):
    if iou(a, b) > 0.3:
        return True
    for p, q in ((a, b), (b, a)):
        cx, cy = (p[0] + p[2]) / 2, (p[1] + p[3]) / 2
        if q[0] <= cx <= q[2] and q[1] <= cy <= q[3]:
            return True
    return False


d = json.load(open(sys.argv[1]))
c = collections.Counter()
lost = []
seen = set()
for i, e in enumerate(d):
    if e["bar"] in seen:
        continue
    seen.add(e["bar"])
    rec = e["record"]
    kept = [g for g in rec.values() if not g["refused"] and g["cls"].startswith("rest")]
    for s, g in rec.items():
        if not (g["refused"] and g["cls"].startswith("rest")):
            continue
        r = g["refused"][0]
        c[(r, "refused")] += 1
        if not any(same(g["box"], k["box"]) for k in kept):
            c[(r, "lost")] += 1
            lost.append((i, s, g["cls"], round(g["conf"], 2), r))
for k in sorted(c):
    print(k, c[k])
json.dump(lost, open(sys.argv[2], "w"))
