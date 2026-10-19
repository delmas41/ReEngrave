"""2.167d probe 2: CONTROL. The base-cell re-run at conf>=0.25 must reproduce the record's detector boxes (same class, same page box).
usage: d2_control.py PLATE RERUN.json RECORD_EXTRACT.json"""
import json
import sys

plate, rr, rx = sys.argv[1:4]
t = json.load(open(rr))
r = json.load(open(rx))


def iou(a, b):
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    i = (ix1 - ix0) * (iy1 - iy0)
    return i / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


tot = same = miss_rec = extra_mine = 0
by_reader = {}
for k, v in t.items():
    if "variants" not in v:
        print("skip", k, v)
        continue
    rec = r["cells"][k]
    if rec["cell_box"] and [round(x) for x in rec["cell_box"]] != [round(x) for x in v["cell"]]:
        print("CELL BOX DIFF", k, rec["cell_box"], v["cell"])
    mine = [b for b in v["variants"]["base"]["boxes"] if b[1] >= 0.25]
    used = set()
    for g in rec["glyphs"]:
        tot += 1
        best = None
        for i, b in enumerate(mine):
            if i in used or b[0] != g["cls"]:
                continue
            u = iou(g["bbox"], b[2:6])
            if u > 0.8 and (best is None or u > best[0]):
                best = (u, i)
        rd = by_reader.setdefault(g["reader"], [0, 0])
        rd[0] += 1
        if best:
            used.add(best[1])
            same += 1
            rd[1] += 1
    extra_mine += len(mine) - len(used)
print(plate, "record boxes", tot, "reproduced by my base re-run", same, "record boxes not reproduced", tot - same, "my >=0.25 boxes not in record", extra_mine)
print("by reader (n, reproduced)", by_reader)
