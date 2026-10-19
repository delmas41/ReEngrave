"""2.167 probe 2b: one stem cause per sampled head of p2_stems.py's output (first match, same words as 2.161's causes_2_161.py).
usage: python3 probe/2.167/p2b_causes.py STEMS.json [OUT.json]"""
import collections
import json
import sys

R = json.load(open(sys.argv[1]))


def cause(r):
    if "error" in r:
        return "ERR"
    for n in r["stems_near"]:
        if not n["touches"] and n["dy_sp"] == 0 and n["dx_sp"] <= 0.5:
            return "ii  S1 stem FOUND beside the box; contact test fails"
    for n in r["stems_near"]:
        if not n["touches"] and n["dx_sp"] == 0 and n["dy_sp"] <= 0.5:
            return "ii  S1v stem FOUND above/below the box; contact test fails"
    for n in r["refused_near"]:
        if n["outcome"] != "accepted" and n["dx_sp"] <= 0.35 and n["dy_sp"] == 0 and n["h_sp"] >= 1.5:
            return "i   S2 run beside head REFUSED by the finder: " + n["outcome"]
    m = max((v["len_sp"] for v in r["raw_runs"].values()), default=0)
    if m >= 1.5:
        return "i   S2x ink run beside head never a candidate"
    return "0   S3 no vertical ink beside the head"


c = collections.Counter()
out = {}
for s, r in sorted(R.items()):
    cs = cause(r)
    out[s] = cs
    c[cs] += 1
    print(s, r.get("cls", "")[:16], r.get("fate", "")[:14], "w%.2f h%.2f" % (r.get("w_sp", 0), r.get("h_sp", 0)), cs,
          {k: v["len_sp"] for k, v in r.get("raw_runs", {}).items()})
print()
for k, v in sorted(c.items()):
    print(v, k)
if len(sys.argv) > 2:
    json.dump(out, open(sys.argv[2], "w"), indent=0)
