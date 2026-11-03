"""Compare two reread jsons (base vs new): abstained->read, read->abstained, read->other position; Sean's r4 answers.
usage: compare.py BASE.json NEW.json [verbose]"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
a = json.load(open(sys.argv[1]))["heads"]
b = json.load(open(sys.argv[2]))["heads"]
SEAN = {x["rg"]: x["sean_position"] for x in json.load(open(os.path.join(HERE, "../../benchmarks/ink-extent-2026-10/answers-r4.json")))["answers"]}
c = collections.Counter()
rows = []
for s in a:
    ga, gb = a[s]["got"], b[s]["got"]
    if ga[0] == "abs" and gb[0] == "pos":
        k = "abstained->read"
    elif ga[0] == "pos" and gb[0] == "abs":
        k = "read->abstained"
    elif ga[0] == "pos" and ga[1] != gb[1]:
        k = "read->moved"
    else:
        k = "same"
        if ga[0] == "abs" and ga[2] != gb[2]:
            k = "abstained, other reason"
    c[k] += 1
    if k != "same":
        rows.append((k, s, ga[1], gb[1], str(ga[2])[:40], str(gb[2])[:70], SEAN.get(s)))
print(dict(c))
for r in sorted(rows):
    if len(sys.argv) > 3 or r[0] != "abstained, other reason":
        print("  ", r)
for s, v in SEAN.items():
    if s in b:
        print("  SEAN", s, v, "base", a[s]["got"][1], "new", b[s]["got"][1])
