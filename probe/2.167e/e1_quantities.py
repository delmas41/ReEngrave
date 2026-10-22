"""2.167e probe 1: which quantities and verdict outcomes a record holds, with one example each. READ-ONLY.
usage: e1_quantities.py RECORD"""
import ijson
import sys
import collections
import json

path = sys.argv[1]
oc = collections.Counter()
ex = {}
with open(path, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        k = (o["subject"].split("/")[0], o["quantity"])
        oc[k] += 1
        if k not in ex:
            ex[k] = json.dumps(o)[:300]
vc = collections.Counter()
vx = {}
with open(path, "rb") as f:
    for o in ijson.items(f, "record.verdicts.item", use_float=True):
        k = (o["subject"].split("/")[0], o["quantity"], o["outcome"])
        vc[k] += 1
        if k not in vx:
            vx[k] = json.dumps({a: b for a, b in o.items() if a not in ("considered", "correlated", "basis")})[:300]
print("OBS")
for k, n in sorted(oc.items()):
    print(n, k, ex[k])
print("VERD")
for k, n in sorted(vc.items()):
    print(n, k, vx[k])
