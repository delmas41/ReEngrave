"""2.282 step 1: KIND (b) without any accidental box -- the POSITION signature of a sharp written as a head (page-facts s3: an accidental stands LEFT of its head
at the head's height): a KEPT head box with no stem (head_stem abstained no_stem), another kept head within RIGHT_SP to its right at about its height, and the
box standing no wider than an accidental. This is a population to LOOK at, not a verdict. Reads c3_<plate>.json (kept head boxes) + the slice's head_stem verdicts.
usage: c4_leftheads.py SLICE_DIR C3.json OUT.json"""
import collections
import json
import sys

d, c3, out = sys.argv[1:4]
rows = json.load(open(c3))
hs = {}
for line in open(d + "/verdicts.jsonl"):
    if '"head_stem"' not in line:
        continue
    v = json.loads(line)
    if v["quantity"] == "head_stem":
        hs[v["subject"]] = (v["outcome"], v["reason"])
cand = []
for r in rows:
    if not r["head_to_right"]:
        continue
    o = hs.get(r["sub"])
    if o is None or o[1] != "no_stem":
        continue
    r["head_stem"] = o
    w = (r["page_box"][2] - r["page_box"][0]) / r["sp"]
    r["w_sp"] = round(w, 2)
    cand.append(r)
json.dump(cand, open(out, "w"))
print("kept heads with no stem and a kept head right of them at its height:", len(cand))
print("per page", dict(sorted(collections.Counter(r["page"] for r in cand).items())))
print("by score band", dict(sorted(collections.Counter(round(min(0.99, (r["score"] or 0)) * 5) / 5 for r in cand).items())))
