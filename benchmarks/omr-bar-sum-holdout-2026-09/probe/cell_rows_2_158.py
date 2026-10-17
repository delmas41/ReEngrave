"""ROADMAP 2.158 -- every row (observations, abstentions, verdicts) of one staff's bar, plus that staff's own rows (lines),
streamed out of a record. usage: cell_rows_2_158.py RECORD.json cell/p/s/st/c OUT.json"""
import json
import sys

import ijson

REC, CELL, OUT = sys.argv[1:4]
p = CELL.split("/")
staff = "staff/%s/%s/%s" % (p[1], p[2], p[3])
pre = "/".join(p[1:5])
out = {"observations": [], "abstentions": [], "verdicts": []}


def want(s):
    q = s.split("/")
    return s == CELL or s == staff or (q[0] == "glyph" and "/".join(q[1:5]) == pre)


for k in out:
    with open(REC, "rb") as fh:
        for it in ijson.items(fh, "record.%s.item" % k, use_float=True):
            if want(it["subject"]):
                out[k].append(it)
json.dump(out, open(OUT, "w"), indent=0, default=str)
print({k: len(v) for k, v in out.items()})
