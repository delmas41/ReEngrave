"""2.174 step 2a: Sean's JUDGED tiles whose standing verdict on the night record is a decided quarter (`decided 1 beats (head_and_marks)`),
from the `judged score` output of the SAME record (`python3 -m tools.omr.staged.judged score REC --doc DOC --json SCORE.json`; that join
resolves subject keys by page box where a manifest names no document), joined with the census by subject.
usage: judged_2_174.py DOC SCORE.json CENSUS.json OUT.json"""
import collections
import json
import sys

DOC, SCORE, CEN, OUT = sys.argv[1:5]
cen = {r["subject"]: r for r in json.load(open(CEN))["rows"]}
out = []
for t in json.load(open(SCORE))["tiles"]:
    if not t["note"].startswith("decided 1 beats"):
        continue
    subs = t["subject"] if isinstance(t["subject"], list) else [t["subject"]]
    for s in subs:
        out.append(dict(item=t["item"], tile=t["tile"], subject=s, answer=t["answer"], status=t["status"], note=t["note"],
                        in_census=s in cen, row=cen.get(s)))
json.dump(out, open(OUT, "w"))
c = collections.Counter()
for o in out:
    r = o["row"]
    k = "not-first-verdict-quarter" if r is None else ("nostem" if not r["has_stem"] else "both" if r["cv"] and r["yolo"] else "one" if r["cv"] or r["yolo"] else "none")
    c[k, o["status"]] += 1
print(DOC, "judged tiles with a decided quarter standing", len(out), sorted(c.items()))
