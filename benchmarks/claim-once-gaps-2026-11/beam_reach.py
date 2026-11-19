"""2.322 fix A reach: head boxes that stand on NO-OWNER ink of beam-role strokes (the ink a beam claim would take), and on ANY beam-role stroke ink.
    python3 beam_reach.py PLATE DATADIR"""
import collections
import json
import pathlib
import sys

import numpy as np

plate, data = sys.argv[1], pathlib.Path(sys.argv[2])
heads = json.load(open(data / ("%s_heads2.json" % plate)))
by = collections.defaultdict(list)
for h in heads:
    by[h["page"]].append(h)
res = []
for pg, hs in by.items():
    z = np.load(data / ("%s_p%d.npz" % (plate, pg)))
    ink, rm, st, nn = z["ink"], z["rolemap"], z["state"], z["none"]
    for h in hs:
        x0, y0, x1, y1 = h["box"]
        m = ink[y0:y1, x0:x1] & (st[y0:y1, x0:x1] != 5)
        n = int(m.sum())
        if not n:
            continue
        isb = np.isin(rm[y0:y1, x0:x1], [1, 2, 3])
        h2 = dict(h)
        h2["beam_none_share"] = round(float((isb & nn[y0:y1, x0:x1] & m).sum()) / n, 3)
        res.append(h2)
for lo in (0.05, 0.25, 0.5):
    s = [h for h in res if h["beam_none_share"] >= lo]
    print("head boxes with >= %.2f of their ink on NO-OWNER beam-role stroke ink: %d (written as notes %d)" % (lo, len(s), sum(h["written"] for h in s)))
print("total no-owner beam-role px under head boxes:", sum(int(h["beam_none_share"] * h["ink"]) for h in res))
