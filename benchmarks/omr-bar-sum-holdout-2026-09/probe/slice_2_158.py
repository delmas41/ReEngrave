"""ROADMAP 2.158 -- cut the rows of NAMED SYSTEMS (page,system) out of a night record into a slice file (observations +
abstentions + the stored verdicts), streamed (ijson). Subjects not system-scoped are kept whole (`slice_2_153.py`'s rule).
usage: slice_2_158.py RECORD.json OUT.json "p,s;p,s;..." """
import json
import sys

import ijson

REC, OUT, SYS = sys.argv[1:4]
keep = {tuple(int(x) for x in t.split(",")) for t in SYS.split(";") if t}


def want(sub):
    p = sub.split("/")
    if len(p) >= 3 and p[1].lstrip("-").isdigit() and p[2].lstrip("-").isdigit():
        return (int(p[1]), int(p[2])) in keep
    return True


out = {"observations": [], "abstentions": [], "verdicts": []}
for k in out:
    with open(REC, "rb") as fh:
        for it in ijson.items(fh, "record.%s.item" % k, use_float=True):
            if want(it["subject"]):
                out[k].append(it)
print({k: len(v) for k, v in out.items()}, flush=True)
json.dump(out, open(OUT, "w"), default=str)
