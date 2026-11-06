"""GATHER: why a detector arc box got no page curve (Q.SYSTEM_ARC abstentions), straight from the saved slice. Measure only.
python3 trace_abstentions.py PLATE [TAG] [PAGES]"""
import collections
import json
import sys

plate = sys.argv[1]
tag = sys.argv[2] if len(sys.argv) > 2 else "20261104-night"
pages = set(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 else None
d = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-%s/%s/abstentions.jsonl" % (tag, plate)
c = collections.Counter()
n_boxes = 0
for line in open(d):
    a = json.loads(line)
    if a.get("quantity") != "system_arc":
        continue
    pg = int(a["subject"].split("/")[1])
    if pages and pg not in pages:
        continue
    note = (a.get("detail") or {}).get("note") or a.get("note") or ""
    why = (a.get("detail") or {}).get("why") or a.get("why") or ""
    if "bows" in note:
        note = "not bowed (straight trace)"
    elif "inks" in note:
        note = "trace inks < 0.5 of the box's columns"
    c[(a.get("reason"), why, note[:60])] += 1
for k, v in c.most_common():
    print(v, k)
