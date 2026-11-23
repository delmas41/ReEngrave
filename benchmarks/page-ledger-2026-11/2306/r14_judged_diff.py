"""2.306 r14: right->wrong (and every other move) between two `judged score --json` outputs, tile by tile. Usage: r14_judged_diff.py BASE.json ARM.json"""
import collections
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])


def outcomes(j):
    out = {}
    for t in j["tiles"]:
        k = json.dumps([t.get(x) for x in ("item", "tile", "subject", "key")], default=str)
        out[k] = t.get("status")
    return out


A, B = outcomes(a), outcomes(b)
moves = collections.Counter((A[k], B.get(k)) for k in A if A[k] != B.get(k))
print("tiles", len(A), len(B), "moves", dict(moves))
for k in A:
    if A[k] == "right" and B.get(k) != "right":
        print("RIGHT->", B.get(k), k)
