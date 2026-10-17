"""ROADMAP 2.157 -- cut an existing slice file into SMALLER slices, one per named group of systems, in ONE streamed pass
(ijson; no whole-file load, so a 2.6 GB slice costs no 30 GB of memory). Subjects that are not system-scoped go to every
group (they are small), as `slice_2_153.py` keeps them.
usage: cut_groups_2_157.py IN.json OUT_PREFIX "p,s;p,s|p,s;..."     writes OUT_PREFIX<i>.json per |-separated group"""
import json
import sys

import ijson

IN, PREFIX, SPEC = sys.argv[1:4]
groups = [{tuple(int(x) for x in t.split(",")) for t in g.split(";") if t} for g in SPEC.split("|")]


def where(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        k = (int(p[1]), int(p[2]))
        return [i for i, g in enumerate(groups) if k in g]
    return list(range(len(groups)))


for i in range(len(groups)):          # one group in memory at a time
    o = {"observations": [], "abstentions": [], "verdicts": []}
    for kind in o:
        with open(IN, "rb") as fh:
            for it in ijson.items(fh, kind + ".item", use_float=True):
                if i in where(it["subject"]):
                    o[kind].append(it)
    json.dump(o, open("%s%d.json" % (PREFIX, i), "w"), default=str)
    print(i, {k: len(v) for k, v in o.items()}, flush=True)
    del o
