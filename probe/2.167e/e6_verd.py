"""2.167e probe 6: full verdicts (incl. detail) of one quantity on listed glyph indices.
usage: e6_verd.py CELLS.json CELLKEY QUANTITY idx [idx...]"""
import json
import sys

d = json.load(open(sys.argv[1]))[sys.argv[2]]
q = sys.argv[3]
for i in sys.argv[4:]:
    sub = "glyph/%s/%s" % (sys.argv[2], i)
    for v in d["verd"]:
        if v["subject"] == sub and v["quantity"] == q:
            print(sub, json.dumps({k: x for k, x in v.items() if k not in ("basis", "correlated")})[:1500])
