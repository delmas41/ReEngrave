"""2.167d probe 9: does confidence depend on where the symbol stands in the bar crop?  For every base box (>= 0.05) of notehead / rest / flag / dot class
inside the 90 sampled bars: x position as a fraction of the bar crop width, and the share kept (>= 0.25), by x tenth, per plate.
Also the floor-lowering table: how many base boxes sit in 0.10-0.25 by family. usage: d9_position.py"""
import collections
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/data/"


def fam(c):
    for f in ("notehead", "rest", "flag", "augmentationDot"):
        if c.startswith(f):
            return f
    if c[:3] in ("F8t", "F16", "F32"):
        return "flag"
    if c == "dot":
        return "augmentationDot"
    return None


for pl in ("lit", "bra"):
    rr = json.load(open(D + "%s_rerun.json" % pl))
    by = collections.defaultdict(lambda: [0, 0])
    band = collections.Counter()
    for key, R in rr.items():
        x0, y0, x1, y1 = R["cell"]
        for b in R["variants"]["base"]["boxes"]:
            f = fam(b[0])
            if not f:
                continue
            cx = (b[2] + b[4]) / 2
            if not x0 <= cx <= x1:
                continue
            t = min(9, int(10 * (cx - x0) / (x1 - x0)))
            by[t][0] += 1
            by[t][1] += b[1] >= 0.25
            if b[1] < 0.25:
                band[(f, "0.20-0.25" if b[1] >= .2 else "0.15-0.20" if b[1] >= .15 else "0.10-0.15" if b[1] >= .1 else "0.05-0.10")] += 1
            else:
                band[(f, ">=0.25")] += 1
    print(pl, "share of boxes >=0.05 that are >=0.25, by tenth of the bar width:", [round(by[t][1] / by[t][0], 2) if by[t][0] else None for t in range(10)], "n", [by[t][0] for t in range(10)])
    for f in ("notehead", "rest", "flag", "augmentationDot"):
        print("   ", f, {b: band[(f, b)] for b in (">=0.25", "0.20-0.25", "0.15-0.20", "0.10-0.15", "0.05-0.10")})
