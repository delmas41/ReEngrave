"""lane-local-staff-lines: where the new abstentions and the changed answers come from.
  python3 local_lines_breakdown.py <audit.json>"""
import json, sys, collections
d = json.load(open(sys.argv[1]))
c = collections.Counter()
for r in d["rows"]:
    for k, v in r["cand"].items():
        if v["new_flag"]:
            c["newflag_oldplausible" if not v["old_flag"] else "newflag_oldflag"] += 1
            c["newflag_%s" % ("own" if k == r["own"] else "nb")] += 1
    if "old" in r:
        o, n = r["old"], r["new"]
        if o["pos"] is not None and n["pos"] is None:
            c["dec2abs:" + str(n["reason"])[:40]] += 1
            own = r["cand"][r["own"]]
            c["dec2abs_own_new_abstained"] += (own["new_flag"] is not None)
            c["dec2abs_own_old_flagged"] += bool(own["old_flag"])
        if o["pos"] is not None and n["pos"] is not None and o["pos"] != n["pos"]:
            c["val2val_oldflag_own"] += bool(r["cand"][r["own"]]["old_flag"])
        if (o["owner"], o["word"]) != (n["owner"], n["word"]):
            c["own:%s/%s->%s/%s" % (o["word"], "x" if o["owner"] is None else ("own" if o["owner"] == r["own"] else "nb"),
                                    n["word"], "x" if n["owner"] is None else ("own" if n["owner"] == r["own"] else "nb"))] += 1
for k in sorted(c):
    print("%-60s %d" % (k, c[k]))
