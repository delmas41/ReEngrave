"""2.172 (f): the tiles of Sean's judged index whose scored status differs between the OFF and an ON-arm record of a plate.
usage: j1_judged_diff.py PLATE ARM   (data/judged_<plate>_off.json vs data/judged_<plate>_<arm>.json, both from `judged score --json`)"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
pl, arm = sys.argv[1], sys.argv[2]
a = json.load(open(ROOT / ("probe/2.172/data/judged_%s_off.json" % pl)))["tiles"]
b = json.load(open(ROOT / ("probe/2.172/data/judged_%s_%s.json" % (pl, arm))))["tiles"]
if isinstance(a, dict):
    a, b = list(a.values()), list(b.values())
ka = {(t.get("item"), t.get("tile")): t for t in a}
n = 0
for t in b:
    o = ka.get((t.get("item"), t.get("tile")))
    if o is not None and o.get("status") != t.get("status"):
        n += 1
        print(" ", t.get("item"), t.get("tile"), t.get("subject"), "| sean:", str(t.get("answer"))[:30], "|", o.get("status"), "->", t.get("status"))
print(pl, arm, "differing:", n)
