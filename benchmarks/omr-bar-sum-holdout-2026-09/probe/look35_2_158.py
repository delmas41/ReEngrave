"""ROADMAP 2.158 -- the stored (20261016-night) verdicts in the 35 Litolff crop bars: every duration verdict in the staff's bar,
its event grouping, and the system's meter. Streamed (ijson), no whole load.
usage: look35_2_158.py INDEX.json RECORD.json OUT.json"""
import collections
import json
import sys

import ijson

IDX, REC, OUT = sys.argv[1:4]
tiles = json.load(open(IDX))
cells = {"cell/%d/%d/%d/%d" % (t["page"], t["system"], t["staff"], t["cell"]): t["n"] for t in tiles}
systems = {"system/%d/%d" % (t["page"], t["system"]) for t in tiles}
keep = collections.defaultdict(list)
with open(REC, "rb") as fh:
    for v in ijson.items(fh, "record.verdicts.item", use_float=True):
        s = v["subject"]
        if s.startswith("glyph/"):
            c = "cell/" + "/".join(s.split("/")[1:5])
            if c in cells:
                keep[c].append(v)
        elif s in cells or s in systems:
            keep[s].append(v)
json.dump(keep, open(OUT, "w"), default=str)
print(len(keep))
