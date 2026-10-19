"""2.167 probe 6: `owned_by_another_staff` (the cell holds a COPY of ink another staff owns). The export drops it on the claim that the
owner staff holds a twin. Check the claim: for each refused copy, is there a box on the page (any other notehead-classed box,
any fate) overlapping it, and what became of that box? usage: p6_owned.py ROWS.jsonl OUT.json"""
import collections
import json
import sys

rows = [json.loads(l) for l in open(sys.argv[1])]


def iou(a, b):
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    i = ix * iy
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


grid = collections.defaultdict(list)
for r in rows:
    b = r["bbox"]
    grid[(r["sub"].split("/")[1], int(b[0] // 100), int(b[1] // 100))].append(r)


def near(r):
    b = r["bbox"]
    pg = r["sub"].split("/")[1]
    out = []
    for gx in (int(b[0] // 100) - 1, int(b[0] // 100), int(b[0] // 100) + 1):
        for gy in (int(b[1] // 100) - 1, int(b[1] // 100), int(b[1] // 100) + 1):
            for w in grid.get((pg, gx, gy), ()):
                if w["sub"] != r["sub"]:
                    i = iou(b, w["bbox"])
                    if i > 0.1:
                        out.append((i, w))
    return sorted(out, key=lambda t: -t[0])


def end_state(w):
    if w["fate"] == "written":
        return "written_held_bar" if w["held_cell"] else "written"
    return w["fate"]


owned = [r for r in rows if r["fate"] == "owned_by_another_staff"]
c = collections.Counter()
ex = collections.defaultdict(list)
for r in owned:
    n = near(r)
    if not n:
        k = "no_overlapping_box_at_all"
    else:
        best = n[0][1]
        k = ("overlap_iou>0.3:" if n[0][0] > 0.3 else "overlap_iou0.1-0.3:") + end_state(best)
    c[k] += 1
    if len(ex[k]) < 40:
        ex[k].append(r["sub"])
for k, v in c.most_common():
    print("%-60s %5d" % (k, v))
json.dump({"counts": dict(c), "examples": ex}, open(sys.argv[2], "w"), indent=1)
