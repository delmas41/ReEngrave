"""For dropped real curves with an unbound end: what the binder recorded (measure only). python3 ends.py LEDGER.json"""
import collections
import json
import sys

led = json.load(open(sys.argv[1]))
c = collections.Counter()
dist = []
n = 0
for r in led["rows"]:
    if r["fate"] != "dropped":
        continue
    pb = r.get("binding")
    if not pb:
        c["no_binding_row"] += 1
        continue
    for side in ("left", "right"):
        e = pb.get(side) or {}
        if e.get("unbound"):
            c[(side, e["unbound"])] += 1
            if n < 6:
                print(r["curve"], side, json.dumps(e)[:300])
                n += 1
            if e.get("margin_spaces") is not None:
                dist.append(e["margin_spaces"])
print(c)
if dist:
    dist.sort()
    print("n", len(dist), "median", dist[len(dist) // 2], "quartiles", dist[len(dist) // 4], dist[3 * len(dist) // 4])
