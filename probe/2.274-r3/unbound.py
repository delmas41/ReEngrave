"""what the binder says when an end is unbound: the candidates / reason on each side, for every end_unbound abstention (ON)"""
import json
import collections
from load import *  # noqa

rec = record("on")
bind = [v for v in rec["verdicts"] if v["quantity"] == "page_arc_binding"][0]["detail"]["runs"]
n = 0
for e in bind:
    if e["status"] == "abstained" and e.get("why") == "end_unbound":
        print(e["ordinal"], json.dumps({k: v for k, v in e.items() if k not in ("row", "witnesses", "home_from")})[:900])
        n += 1
        if n >= 3:
            break
c = collections.Counter()
for e in bind:
    if e["status"] == "abstained" and e.get("why") == "end_unbound":
        for side in ("left", "right"):
            s = e.get(side) or {}
            c[(side, "bound" if s.get("head") else str(s.get("unbound")))] += 1
for k, v in c.most_common(20):
    print(v, k)
