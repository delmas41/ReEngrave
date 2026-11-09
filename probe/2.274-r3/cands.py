"""python3 cands.py [ARM]: for every printed arc that is not right (buckets.json), the file arcs near it: overlapping x by >= 50% of the printed arc, within 7 sp of its height"""
import json
import sys
from load import *  # noqa
import audit_spans as AS  # noqa

arm = sys.argv[1] if len(sys.argv) > 1 else "on"
C = json.load(open("buckets.json"))
W = AS.spans(arm)
for c in C:
    if c["bucket_" + arm] == "right":
        continue
    x0, x1 = c["x0"], c["x1"]
    yc = (c["y0"] + c["y1"]) / 2
    print("P%d %s %s x%d-%d y%d  [%s] %s" % (c["n"], c["staff"], c["kind"], x0, x1, yc, c["bucket_" + arm], c["why_" + arm][:70]))
    for w in W:
        lo, hi = max(w["cl"], x0), min(w["cr"], x1)
        if hi - lo >= 0.5 * (x1 - x0) and abs(w["yc"] - yc) <= 7 * SP:
            print("     file %s %s x%d-%d (dl %+.1f dr %+.1f sp) y%d  %s -> %s" % (w["kind"], w["staff"], w["cl"], w["cr"], (w["cl"] - x0) / SP, (w["cr"] - x1) / SP, w["yc"], w["start"].split("/", 2)[2], w["stop"].split("/", 2)[2]))
