"""Test-artefact share: does the slice's missing pages (3,5,7,12-15) / missing opening page change the fills?
    python3 artefact.py X.json
Reports, per page, staves whose SLOT is undecided / inferred, and fills that rest on a staff placed by an inference (`part_from_an_inference`) or
on the part's OTHER systems (tier part_majority), i.e. the places a missing page could matter."""
import collections
import json
import sys

d = json.load(open(sys.argv[1]))
S = d["staffs"]
cnt = collections.Counter()
rows = []
for k, v in S.items():
    slot = v["slot"][0] if v["slot"] else None
    if slot is None or slot["outcome"] != "decided":
        cnt["slot undecided"] += 1
        sl = "undecided"
    elif slot["decider"].startswith("infer"):
        cnt["slot inferred"] += 1
        sl = "inferred"
    else:
        cnt["slot named"] += 1
        sl = "named"
    kf = v["key"][0] if v["key"] else None
    if kf and kf["decider"].startswith("infer"):
        det = kf.get("detail") or {}
        rows.append((k, sl, det.get("tier"), det.get("part_from_an_inference")))
print(path := sys.argv[1], dict(cnt))
print("filled keys by slot standing:", collections.Counter(r[1] for r in rows), " by tier:", collections.Counter(r[2] for r in rows),
      " rest on a staff placed by an inference:", sum(1 for r in rows if r[3]))
