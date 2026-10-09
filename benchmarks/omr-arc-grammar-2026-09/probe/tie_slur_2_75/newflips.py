import collections
import json
import sys

old = {r["sub"]: r for r in json.load(open(sys.argv[1]))}
new = {r["sub"]: r for r in json.load(open(sys.argv[2]))}
c = collections.Counter()
rows = []
for k, r in new.items():
    if r["refused"] or not r["box"]:
        continue
    o = old[k]
    if (o["kind"], o["outcome"]) == (r["kind"], r["outcome"]):
        continue
    tn = (r.get("rule") or {}).get("two_note") or {}
    key = (o["det"], o["kind"], "->", r["kind"], tn.get("start_candidate"), tn.get("stop_candidate"),
           "chord" if tn.get("chord") else "")
    c[key] += 1
    rows.append((k, key, tn.get("dy_spaces"), tn.get("start_step"), tn.get("stop_step")))
for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
    print(v, k)
if "--list" in sys.argv:
    for r in rows:
        print(r)
