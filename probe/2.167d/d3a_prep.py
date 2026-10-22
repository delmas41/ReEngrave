"""2.167d probe 3a: subset the 2.167c capture (c1_capture.py output, all held bars) to the 45 sampled bars per plate.
usage: d3a_prep.py lit|bra CAPTURE.json"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
plate, cap = sys.argv[1], sys.argv[2]
d = ROOT + "/probe/2.167d/data/"
sample = [tuple(s) for s in json.load(open(d + "%s_sample.json" % plate))]
rows = {(r["page"], r["system"], r["staff"], r["cell"]): r for r in json.load(open(cap))}
out = {}
for s in sample:
    r = rows[s]
    out["%d/%d/%d/%d" % s] = r
json.dump(out, open(d + "%s_held_sample.json" % plate, "w"))
print(plate, len(out))
