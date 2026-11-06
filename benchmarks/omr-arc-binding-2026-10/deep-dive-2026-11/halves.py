"""Half arcs: real curves whose end meets another curve's opposite end on the same staff (a join the trace never made).
Measure only: python3 halves.py LEDGER.json [DX_SP] [DY_SP]"""
import collections
import json
import sys

res = json.load(open(sys.argv[1]))
DX = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
DY = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
rows = [r for r in res["rows"] if r["fate"] != "not_an_arc" and r.get("x_left") is not None]
by = collections.defaultdict(list)
for r in rows:
    by[r["staff"]].append(r)
pairs = []
for st, rs in by.items():
    for a in rs:
        for b in rs:
            if a is b:
                continue
            sp = a["sp"]
            dx = (b["x_left"] - a["x_right"]) / sp
            dy = abs(b["y_left"] - a["y_right"]) / sp
            if -1.0 <= dx <= DX and dy <= DY:
                pairs.append((a, b, dx, dy))
print("candidate continuation pairs (a.right -> b.left):", len(pairs))
c = collections.Counter()
for a, b, dx, dy in pairs:
    c[(a["fate"], b["fate"])] += 1
for k, v in c.most_common():
    print("  ", k, v)
# a curve has a right continuation if it is `a` in some pair; left continuation if `b`
left_cont = {id(b) for a, b, *_ in pairs}
right_cont = {id(a) for a, b, *_ in pairs}
d = collections.Counter()
for r in rows:
    half = (id(r) in left_cont) or (id(r) in right_cont)
    d[(r["fate"], "half" if half else "whole")] += 1
print(sorted(d.items()))
lost = collections.Counter()
for r in rows:
    if r["fate"] == "dropped":
        half = (id(r) in left_cont) or (id(r) in right_cont)
        lost[(r["lost_at"] + ":" + (r["lost_rule"] or "")[:40], "half" if half else "whole")] += 1
for k, v in sorted(lost.items(), key=lambda x: -x[1])[:14]:
    print("  ", k, v)
