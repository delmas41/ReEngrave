"""2.167b probe 9b: for cells that went WRITTEN -> held_bar_sum between two nights, what changed in the duration verdicts of that cell?
usage: python3 probe/2.167/p9b_newheld.py OLD.part.rows.jsonl NEW.part.rows.jsonl"""
import collections
import json
import sys

o = {r["sub"]: r for r in map(json.loads, open(sys.argv[1]))}
n = {r["sub"]: r for r in map(json.loads, open(sys.argv[2]))}


def cell(s):
    return tuple(s.split("/")[1:5])


newheld = collections.defaultdict(list)
for s in o:
    if o[s]["bucket"] == "WRITTEN" and n[s]["bucket"] == "held_bar_sum":
        newheld[cell(s)].append(s)
chg = collections.defaultdict(list)
for s in o:
    a, b = o[s]["duration"], n[s]["duration"]
    if a != b:
        chg[cell(s)].append((a[0] if a else None, a[1] if a else None, b[0] if b else None, b[1] if b else None))
print("cells newly held", len(newheld), " of them with a duration verdict change in the cell:", sum(1 for k in newheld if k in chg))
t = collections.Counter()
for k in newheld:
    for x in chg.get(k, []):
        t[x] += 1
for x, v in t.most_common(8):
    print(v, x)
