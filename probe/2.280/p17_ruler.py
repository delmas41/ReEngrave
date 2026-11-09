"""2.280 probe 17: `Q.HEAD_STEM_REACH` (gather_head_stem_reach: a page-raster ruler beside the head, filed only for CONTESTED heads) on the 83 narrowed no-stem heads, by my label.
How many have a ruler row at all, and what does it say (up / down / both / none)? usage: p17_ruler.py"""
import collections
import json

for plate in ("litolff", "brahms"):
    R = json.load(open("out/2.280/rerunfull_%s.json" % plate))
    L = json.load(open("out/2.280/labels_%s.json" % plate))
    ct = collections.Counter()
    for s, lab in L.items():
        rc = R[s].get("reach")
        ct[(lab, "no ruler row" if not rc else "ruler " + str(rc.get("dir")))] += 1
    print(plate)
    for k, v in sorted(ct.items()):
        print("   %s %-16s %d" % (k[0], k[1], v))
