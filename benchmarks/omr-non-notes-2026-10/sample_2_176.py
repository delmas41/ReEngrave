"""2.176 step 1: seeded RANDOM sample of WRITTEN notes (decided, not a rest, in a bar that is not held out -> reaches the file)
and of notes in HELD bars, from a 2.174-style replay's OFF arm (`replay_2_176.py` output: DOC.off.json).
usage: sample_2_176.py DOC OFFJSON NWRITTEN NHELD OUT.json"""
import json
import random
import sys

DOC, OFF, NW, NH, OUT = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
d = json.load(open(OFF))
held = {tuple(h) for h in d["held_bars"]}


def bar(g):
    p = g.split("/")
    return (int(p[1]), int(p[2]), int(p[3]), int(p[4]))


written, heldn = [], []
for g, v in d["glyphs"].items():
    if v["rest"] or v["measure_rest"]:
        continue
    if bar(g) in held:
        heldn.append(g)
    elif v["outcome"] == "decided":
        written.append(g)
rnd = random.Random(2176)
sw = sorted(rnd.sample(sorted(written), NW))
sh = sorted(rnd.sample(sorted(heldn), NH))
print(DOC, "written pool", len(written), "held pool", len(heldn))
json.dump(dict(written=sw, held=sh, pool_written=len(written), pool_held=len(heldn)), open(OUT, "w"))
