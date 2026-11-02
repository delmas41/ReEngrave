"""2.248 r3: how many far heads hit the plain box-centre fallback today (ledger count abstained), per plate,
from the frozen-sample slices of the 20261029-night record."""
import collections
import json

BASE = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/"
for plate in ("litolff", "brahms"):
    heads = 0
    read = 0
    ab = collections.Counter()
    lr = collections.Counter()
    for line in open(BASE + plate + "/observations.jsonl"):
        r = json.loads(line)
        if r.get("quantity") == "notehead_staff_position":
            heads += 1
        elif r.get("quantity") == "far_head_ledger_position":
            read += 1
    for line in open(BASE + plate + "/abstentions.jsonl"):
        r = json.loads(line)
        if r.get("quantity") == "far_head_ledger_position":
            ab[r.get("reason")] += 1
            d = r.get("detail") or {}
            lr[str(d.get("ledger_reason"))[:48]] += 1
    print(plate, "heads", heads, "far read", read, "far abstained", dict(ab))
    print("   ledger_reason", dict(lr.most_common(14)))
