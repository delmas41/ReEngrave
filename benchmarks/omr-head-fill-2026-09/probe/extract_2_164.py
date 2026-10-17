"""ROADMAP 2.164 -- pull every row (observations, abstentions, verdicts) of the cells that hold 2.160's left-edge
arc-tail candidates and of the cells their arcs were filed in, out of a night record, streamed (ijson). Read-only.
usage: extract_2_164.py RECORD.json TAILS.json OUT.json"""
import json
import sys

import ijson

REC, TAILS, OUT = sys.argv[1:4]
hits = json.load(open(TAILS))["hits"]
cells = set()
for h in hits:
    for g in (h["glyph"], h["arc_glyph"]):
        p = g.split("/")
        cells.add("/".join(p[1:5]))


def want(sub):
    p = sub.split("/")
    return len(p) >= 5 and p[0] in ("glyph", "cell") and "/".join(p[1:5]) in cells


out = {"observations": [], "abstentions": [], "verdicts": []}
for k in out:
    with open(REC, "rb") as fh:
        for it in ijson.items(fh, "record.%s.item" % k, use_float=True):
            if want(it["subject"]):
                out[k].append(it)
    print(k, len(out[k]), flush=True)
json.dump(dict(cells=sorted(cells), **out), open(OUT, "w"), default=str)
