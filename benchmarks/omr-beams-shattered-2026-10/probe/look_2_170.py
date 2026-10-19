"""2.170: list changed heads in NEWLY held bars and decided-eighth -> quarter moves, for a look. usage: look_2_170.py REPLAYDIR DOC OUT.json"""
import json
import sys
from pathlib import Path

RD, DOC, OUT = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
d = json.load(open(RD / ("%s.changed.json" % DOC)))
new, e2q, rest = [], [], []
for g, rule, x, y, ho, hn in d:
    if hn and not ho:
        new.append(g)
    elif x["outcome"] == "decided" and x["written"] != y["written"]:
        e2q.append(g)
        print("decided move", g, x["written"], "->", y["written"], x["decider"], x["reason"], "| on", y["decider"], y["reason"])
    elif rule:
        rest.append(g)
print("changed in newly held bars", len(new), "decided moves", len(e2q), "other rule changes", len(rest))
json.dump(dict(new_held=new, decided_moves=e2q, rest=rest), open(OUT, "w"))
