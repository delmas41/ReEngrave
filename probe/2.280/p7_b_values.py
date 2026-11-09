"""2.280 probe 7: stratum B (kept head, DECIDED duration, no touching stem row): what value was decided, by head class and head_ink?
usage: p7_b_values.py plate BUCKETSFULL.json"""
import collections
import json
import sys

plate, bk = sys.argv[1:3]
B = json.load(open(bk))
subs = {s for s, b in B.items() if b["stratum"] == "B"}
SL = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261104-night/"
val = {}
for l in open(SL + plate + "/verdicts.jsonl"):
    v = json.loads(l)
    if v["quantity"] == "duration" and v["subject"] in subs:
        val[v["subject"]] = (v["value"] or {}, v["reason"])
ink = {}
cls = {}
for l in open(SL + plate + "/observations.jsonl"):
    o = json.loads(l)
    if o["subject"] in subs:
        if o["quantity"] == "head_ink":
            ink[o["subject"]] = o["value"]
        elif o["quantity"] == "glyph_box":
            cls[o["subject"]] = o["value"][0]
c = collections.Counter()
for s in subs:
    v, reason = val.get(s, ({}, None))
    c[(cls.get(s), ink.get(s), v.get("written"), v.get("beam_levels"), B[s]["cause"][:14])] += 1
c2 = collections.Counter()
for (cl, ik, w, bl, cz), n in c.items():
    c2[(w, ik)] += n
print(plate, "B n=%d" % len(subs))
for k, n in sorted(c2.items(), key=lambda x: -x[1])[:14]:
    print("  written=%s head_ink=%s : %d" % (k[0], k[1], n))
