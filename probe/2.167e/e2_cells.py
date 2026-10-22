"""2.167e probe 2: every observation and verdict (full, nothing dropped) on the six tile bars' cells. READ-ONLY.
usage: e2_cells.py RECORD OUT.json p,s,st,c [p,s,st,c ...]"""
import ijson
import sys
import json

path, out = sys.argv[1], sys.argv[2]
cells = [tuple(int(x) for x in a.split(",")) for a in sys.argv[3:]]
pref = {c: "/".join(map(str, c)) for c in cells}


def which(sub):
    p = sub.split("/")
    if p[0] not in ("glyph", "cell"):
        return None
    k = tuple(int(x) for x in p[1:5])
    return k if k in pref else None


res = {pref[c]: {"obs": [], "verd": []} for c in cells}
with open(path, "rb") as f:
    for o in ijson.items(f, "record.observations.item", use_float=True):
        k = which(o["subject"])
        if k:
            res[pref[k]]["obs"].append(o)
with open(path, "rb") as f:
    for o in ijson.items(f, "record.verdicts.item", use_float=True):
        k = which(o["subject"])
        if k:
            res[pref[k]]["verd"].append(o)
json.dump(res, open(out, "w"), default=float)
for k, v in res.items():
    print(k, len(v["obs"]), len(v["verd"]))
