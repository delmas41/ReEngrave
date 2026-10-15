"""2.136: cross-tab the INFER counterfactual (carry vs the source's LAST segment) against the
reconcile_duration gate, per movement.   python3 cf_table_2_136.py OUTDIR"""
import collections
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
for lab in ("lit", "brah"):
    cf = json.load(open(D / f"{lab}-gates.infer-cf.json"))
    g = {tuple(r["cell"]): r for r in json.load(open(D / f"{lab}-gates.json"))["rows"]}
    print("==", lab, cf["summary"])
    c = collections.Counter()
    for r in cf["rows"]:
        gg = g[tuple(r["cell"])]
        c[(gg["gate"], gg.get("why"), r["decline"], r["bar_fully_released"])] += 1
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(" ", v, k)
