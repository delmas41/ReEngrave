"""Was 2.256b (key stems) in this gather?  Compare each staff's key_object own_slots across saved slices.
    python3 ko_compare.py PLATE PAGES TAG [TAG ...]"""
import collections
import json
import sys

plate, pages = sys.argv[1], set(int(x) for x in sys.argv[2].split(","))
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-%s/%s/observations.jsonl"
res = {}
for tag in sys.argv[3:]:
    own = {}
    with open(LIB % (tag, plate)) as fh:
        for line in fh:
            if '"cv_key_object"' not in line:
                continue
            o = json.loads(line)
            sj = o["subject"].split("/")
            if len(sj) < 4 or int(sj[1]) not in pages:
                continue
            ko = (o.get("detail") or {}).get("key_object")
            if isinstance(ko, dict):
                own["/".join(sj[1:4])] = ko.get("own_slots")
    res[tag] = own
tags = sys.argv[3:]
print("staves per tag:", {t: len(r) for t, r in res.items()})
for t in tags:
    print(t, dict(collections.Counter(res[t].values())))
a = res[tags[0]]
for t in tags[1:]:
    b = res[t]
    ch = [(k, a[k], b[k]) for k in a if k in b and a[k] != b[k]]
    print(tags[0], "->", t, "changed", len(ch), ch[:12])
