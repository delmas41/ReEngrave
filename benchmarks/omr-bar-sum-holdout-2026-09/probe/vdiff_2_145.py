"""2.145 -- every standing verdict that differs between the OFF and ON replays, grouped by cell.
usage: vdiff_2_145.py REPLAY.json"""
import collections
import json
import sys

d = json.load(open(sys.argv[1]))
a, b = d["off"]["_verdicts"], d["on"]["_verdicts"]
by_cell = collections.defaultdict(list)
for k in sorted(set(a) | set(b)):
    if a.get(k) != b.get(k):
        sub, q = k.split("|")
        p = sub.split("/")
        by_cell["/".join(p[1:5])].append((sub, q, a.get(k), b.get(k)))
print("cells with a changed verdict:", len(by_cell), "verdicts changed:", sum(len(v) for v in by_cell.values()))
cnt = collections.Counter(q for v in by_cell.values() for (_s, q, _a, _b) in v)
print(dict(cnt))
for cell, rows in sorted(by_cell.items()):
    print("CELL", cell)
    for sub, q, x, y in rows:
        if q in ("duration", "unboxed_ink_is_a_rest", "head_ink_is_a_rest", "notehead_is_not_a_notehead", "event", "meter"):
            print("   ", sub, q, "\n        OFF", x, "\n        ON ", y)
