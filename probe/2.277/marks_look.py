"""2.277: are the marks (copies by position) really one head? usage: marks_look.py DUMP_ON.json"""
import collections, json, os, sys
D = json.load(open(sys.argv[1]))
marks = {}
for c in D["cf"].values():
    marks.update(c.get("marks") or {})
R = {r["sub"]: r for r in D["rows"]}
g = collections.defaultdict(list)
for k, m in marks.items():
    if k in R:
        g[m].append(k)


def iou(a, b):
    ix = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    iy = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0
    i = ix * iy
    return i / (a[2] * a[3] + b[2] * b[3] - i)


def kept(k):
    return next(iter(R[k]["fate"].values()), [None])[0] is False


print("group sizes", collections.Counter(len(v) for v in g.values()))
ious, dy = [], []
for m, ks in g.items():
    kp = [k for k in ks if kept(k)]
    if len(kp) > 1:
        a, b = R[kp[0]]["box"], R[kp[1]]["box"]
        ious.append(round(iou(a, b), 2))
        dy.append(round(abs((a[1] + a[3] / 2) - (b[1] + b[3] / 2)) / max(a[3], b[3]), 2))
print("marks with >1 kept box:", len(ious))
print("iou  sorted every 10%:", sorted(ious)[::max(1, len(ious) // 10)])
print("dy/h sorted every 10%:", sorted(dy)[::max(1, len(dy) // 10)])
