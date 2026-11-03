"""For each head a new reread reads that the base abstained on (or moved): the record's owner-ledger rows toward OTHER
staves (a refutation of the own staff), and the page owner's verdict if any.  usage: newreads.py PLATE BASE NEW"""
import json
import sys

from tools.omr.staged import lane_report as LR

plate, a, b = sys.argv[1:4]
A = json.load(open(a))["heads"]
B = json.load(open(b))["heads"]
base = LR.slice_dir(plate, "20261029-night")
want = {s for s in A if A[s]["got"] != B[s]["got"] and B[s]["got"][0] == "pos" or (A[s]["got"][0] == "pos" and A[s]["got"][1] != B[s]["got"][1])}
other = {}
for l in open(base / "observations.jsonl"):
    if '"far_head_owner_ledger"' not in l:
        continue
    o = json.loads(l)
    s = o["subject"]
    p = s.split("/")
    if s in want and o["detail"].get("candidate") != "staff/%s/%s/%s" % (p[1], p[2], p[3]):
        other.setdefault(s, []).append((o["detail"]["candidate"], o["value"]))
owner = {}
for l in open(base / "verdicts.jsonl"):
    if '"glyph_owner"' not in l:
        continue
    o = json.loads(l)
    if o["subject"] in want:
        owner[o["subject"]] = (o.get("value"), o.get("status"))
for s in sorted(want):
    print(s, "base", A[s]["got"][1], "new", B[s]["got"][1], "| toward other:", other.get(s), "| owner verdict:", owner.get(s))
