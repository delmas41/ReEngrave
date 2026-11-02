"""Of the far heads whose OWN-staff ledger count abstained (frozen-sample slices, 20261029-night), how many have a
`far_head_owner_ledger` OBSERVATION toward ANOTHER candidate staff (the head reads fine from the neighbour: owner, not reading, is the
question), and how many have none anywhere (a true 'nobody can read it')."""
import collections
import json

BASE = "/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records/lane-report-slices-20261029-night/"
for plate in ("litolff", "brahms"):
    ab = {}
    for line in open(BASE + plate + "/abstentions.jsonl"):
        r = json.loads(line)
        if r.get("quantity") == "far_head_ledger_position":
            ab[r["subject"]] = str((r.get("detail") or {}).get("ledger_reason")).split(" ")[0].split(":")[0]
    toward_other = set()
    toward_own = set()
    for line in open(BASE + plate + "/observations.jsonl"):
        if '"far_head_owner_ledger"' not in line:
            continue
        r = json.loads(line)
        s = r["subject"]
        if s not in ab:
            continue
        parts = s.split("/")
        own = "staff/%s/%s/%s" % (parts[1], parts[2], parts[3])
        cand = (r.get("detail") or {}).get("candidate")
        (toward_own if cand == own else toward_other).add(s)
    c = collections.Counter()
    for s, why in ab.items():
        c[(why, "reads toward another staff" if s in toward_other else "no other staff reads it")] += 1
    print(plate, "abstained", len(ab), "read toward another staff", len(toward_other))
    for k, v in sorted(c.items()):
        print("   ", k, v)
