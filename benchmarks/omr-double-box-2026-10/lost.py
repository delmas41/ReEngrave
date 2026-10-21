"""2.185: the all-dead clusters (every member refused or given away), by family and refusal reason. usage: lost.py ROWS.json"""
import json, sys, collections
rows = json.load(open(sys.argv[1]))
DUP = ("duplicate", "twin")
c = collections.Counter(); ex = {}
for x in rows:
    if x["out"] != "all_dead" or x["judged"] == 0: continue
    rs = sorted({m["why"].split(":", 1)[-1].split(":")[-1] if m["fate"] == "refused" else "GIVEN_AWAY" for m in x["members"]})
    dup = any(any(d in r for d in DUP) for r in rs)
    c[(x["fam"], "dup-reason-involved" if dup else "no-dup-reason")] += 1
    if dup:
        for r in rs: c[("  reason", x["fam"], r)] += 1
for k, v in sorted(c.items(), key=lambda kv: (-kv[1] if kv[0][0] != "  reason" else 0, str(kv[0]))): print(v, k)
