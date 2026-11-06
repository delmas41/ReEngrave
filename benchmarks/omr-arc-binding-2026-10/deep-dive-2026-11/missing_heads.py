"""Tie ends decided by ADJUDICATE that are not a written note: why (measure only). python3 missing_heads.py LEDGER.json ARCS.json MUSICXML"""
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import written as W

led = json.load(open(sys.argv[1]))
dump = json.load(open(sys.argv[2]))
wr = W.parse(pathlib.Path(sys.argv[3]).read_text())
notes = wr["notes"]
nin = {v["subject"]: v for v in dump["verdicts"] if v["quantity"] == "notehead_is_not_a_notehead"}
heads = {h["subject"]: h["box"] for h in dump["heads"]}


def twin_in_file(k):
    b = heads.get(k)
    if not b:
        return None
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    for rg in notes:
        hb = heads.get(rg)
        if hb and abs((hb[0] + hb[2]) / 2 - cx) < 0.6 * (hb[2] - hb[0]) and abs((hb[1] + hb[3]) / 2 - cy) < 0.6 * (hb[3] - hb[1]) and rg != k:
            return rg
    return None


c = collections.Counter()
ex = {}
for r in led["rows"]:
    if r.get("lost_rule") != "export:tie_not_in_file" and r.get("lost_rule") != "export:slur_bound_not_in_file":
        continue
    a, b = r["pair"]
    for end, k in (("start", a), ("stop", b)):
        if k in notes:
            continue
        v = nin.get(k)
        why = "no_verdict" if v is None else "%s:%s:%s" % (v["outcome"], v["value"], v["reason"])
        tw = twin_in_file(k)
        c[(r["lost_rule"][7:], end, why, "twin_written" if tw else "no_twin_written")] += 1
        ex.setdefault((why, bool(tw)), (r["curve"], k, tw))
for k, v in c.most_common():
    print(v, k)
print(ex)
