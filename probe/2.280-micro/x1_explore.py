"""exploration: stem and cell rows. usage: x1_explore.py plate"""
import json
import sys

S = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/%s/" % sys.argv[1]
want = {"stem": 2, "cell_box": 2, "cell_staff_space": 1, "glyph_box": 2, "head_stem_reach": 1, "stem_tip_ink": 1, "flag": 1, "beam_stem_join": 1}
n = {}
for l in open(S + "observations.jsonl"):
    o = json.loads(l)
    q = o["quantity"]
    if q in want and n.get(q, 0) < want[q]:
        n[q] = n.get(q, 0) + 1
        print(json.dumps(o)[:1100])
        print()
