"""ROADMAP 2.165 -- Sean's judged tiles, base vs on: every tile whose status moved (judged.score --json of each arm).
usage: judged_diff_2_165.py BASE.judged.json ON.judged.json"""
import collections
import json
import sys

B, O = (json.load(open(p)) for p in sys.argv[1:3])
key = lambda t: (t["item"], str(t["tile"]), json.dumps(t["subject"]))
b = {key(t): t for t in B["tiles"]}
moves = collections.Counter()
for t in O["tiles"]:
    s0 = b[key(t)]["status"]
    if s0 != t["status"]:
        moves[(s0, t["status"])] += 1
        print(s0, "->", t["status"], t["item"], t["tile"], t["subject"], "| Sean:", t["answer"], "|", t["note"])
print(dict(moves))
