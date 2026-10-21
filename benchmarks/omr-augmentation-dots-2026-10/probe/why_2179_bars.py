"""ROADMAP 2.180 -- for lane 2.179's labelled dot bars, the standing dot_role verdict of every dot box in the bar's cell and the
standing duration of every head there, from the 2.179 BASE record (streamed). usage: why_2179_bars.py BASE CENSUS LABELS"""
import collections
import json
import sys

import ijson

base, census, labels = sys.argv[1:4]
C = json.load(open(census))
bars = {}
for line in open(labels):
    if line.startswith("#") or "|" not in line:
        continue
    i, codes, note = [x.strip() for x in line.split("|", 2)]
    cs = codes.split()
    if cs and cs[0] == "e" and "dot" in note:
        bars.setdefault(C[int(i)]["bar"], note)
pre = {"glyph/%s/" % b: b for b in bars}
role, dur, cls = {}, collections.defaultdict(list), {}
with open(base, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        if o["quantity"] == "glyph_box":
            s = o["subject"]
            k = "/".join(s.split("/")[1:5])
            if k in bars:
                cls[s] = o["value"][0]
with open(base, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        s = v["subject"]
        k = "/".join(s.split("/")[1:5]) if s.startswith("glyph/") else None
        if k not in bars:
            continue
        if v["quantity"] == "dot_role":
            role[s] = (v["outcome"][:4], v.get("value"), v.get("reason"))
        elif v["quantity"] == "duration":
            val = v.get("value") if isinstance(v.get("value"), dict) else {}
            dur[s].append((v["outcome"][:4], val.get("written"), val.get("dots"), v.get("reason")))
tab = collections.Counter()
for b, note in sorted(bars.items()):
    rs = {s: r for s, r in role.items() if "/".join(s.split("/")[1:5]) == b}
    reasons = collections.Counter(r[2] if r[0] != "deci" else "deci:" + str(r[1]) for r in rs.values())
    for k in reasons:
        tab[k] += 1
    print(b, "|", note[:40], "|", dict(reasons))
print("bars containing a dot box of each fate:", dict(tab))
