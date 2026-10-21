"""ROADMAP 2.180 -- in lane 2.179's labelled dot bars: each dot decided `augmentation`, the head it names, and that head's
duration chain (last 3). usage: why2_2179_bars.py BASE CENSUS LABELS"""
import collections
import json
import sys

import ijson

base, census, labels = sys.argv[1:4]
C = json.load(open(census))
bars = set()
for line in open(labels):
    if line.startswith("#") or "|" not in line:
        continue
    i, codes, note = [x.strip() for x in line.split("|", 2)]
    cs = codes.split()
    if cs and cs[0] == "e" and "dot" in note:
        bars.add(C[int(i)]["bar"])
role, dur = {}, collections.defaultdict(list)
with open(base, "rb") as f:
    for v in ijson.items(f, "record.verdicts.item", use_float=True):
        s = v["subject"]
        if not s.startswith("glyph/"):
            continue
        if v["quantity"] == "dot_role" and "/".join(s.split("/")[1:5]) in bars:
            d = v.get("detail") or {}
            role[s] = (v["outcome"][:4], v.get("value"), v.get("reason"), d.get("head"), d.get("detector_class"))
        elif v["quantity"] == "duration":
            val = v.get("value") if isinstance(v.get("value"), dict) else {}
            dur[s].append((v["outcome"][:4], val.get("written"), val.get("dots"), v.get("decider"), v.get("reason"),
                           [(c.get("value") or {}).get("dots") for c in (v.get("candidates") or [])]))
tab = collections.Counter()
for s, r in sorted(role.items()):
    if r[1] != "augmentation":
        continue
    h = "/".join(str(r[3]).split("/")[:6]) if r[3] else None
    ch = dur.get(h, [])
    last = ch[-1] if ch else None
    tab[(last[0], bool(last[2])) if last else None] += 1
    print(s, r[2], r[4], "->", h, ch[-3:])
print(tab)
