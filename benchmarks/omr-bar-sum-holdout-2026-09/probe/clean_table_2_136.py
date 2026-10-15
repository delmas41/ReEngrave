"""2.136: which clause of `_bar_heads_are_clean` blocks the bars INFER (after the carried-meter patch)
declines with `heads_not_this_staffs_own`.   python3 clean_table_2_136.py OUTDIR"""
import collections
import json
import sys
from pathlib import Path

D = Path(sys.argv[1])
for lab in ("lit", "brah"):
    cf = json.load(open(D / f"{lab}-gates.infer-cf.json"))
    g = {tuple(r["cell"]): r for r in json.load(open(D / f"{lab}-gates.json"))["rows"]}
    n_ag = sum(1 for r in cf["rows"] if r["clean_why"]["restatement_agrees_with_helper"])
    print("==", lab, "restatement agrees with the helper on", n_ag, "of", len(cf["rows"]))
    c = collections.Counter()
    ex = {}
    for r in cf["rows"]:
        cw = r["clean_why"]
        if not cw["fails"]:
            continue
        gg = g[tuple(r["cell"])]
        key = (gg.get("why") or gg["gate"], tuple(sorted(set(cw["fails"]))))
        c[key] += 1
        ex.setdefault(key, (r["cell"], cw["detail"][:2]))
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(" ", v, k, ex[k])
    # off_staff owner verdicts
    o = collections.Counter()
    sp = []
    for r in cf["rows"]:
        for d in r["clean_why"]["detail"]:
            if d["clause"] == "off_staff":
                o[(tuple(d["owner"][:2]) if d["owner"] else None, d["narrowed"])] += 1
                sp.append(d["spaces_off"])
    print("  off-staff heads by (owner verdict, narrowed):", dict(o))
    if sp:
        sp.sort()
        print("  spaces off the staff: min %.2f median %.2f max %.2f (n=%d)" % (sp[0], sp[len(sp) // 2], sp[-1], len(sp)))
