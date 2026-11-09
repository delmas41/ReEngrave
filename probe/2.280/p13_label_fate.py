"""2.280 probe 13: my-look label (p6) of each stratum-A head against its export fate (p8, current tree). usage: p13_label_fate.py plate"""
import collections
import json
import sys

plate = sys.argv[1]
L = json.load(open("out/2.280/labels_%s.json" % plate))
fates = {}
for l in open("out/2.280/fates_%s.jsonl" % plate):
    r = json.loads(l)
    fates[r["sub"]] = r
ct = collections.Counter()
for s, lab in L.items():
    f = fates.get(s)
    ct[(lab, f["fate"] if f else "NO_ROW")] += 1
for k, v in sorted(ct.items()):
    print("  %s  %-36s %d" % (k[0], k[1], v))
