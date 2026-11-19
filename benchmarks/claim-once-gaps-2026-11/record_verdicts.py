"""2.322: what the RECORD itself says about head boxes on the sample pages: notehead_is_not_a_notehead verdicts by reason, and the ink_consult /
claim_final entries it filed (refused or not). Streams the slice's verdicts.jsonl.   python3 record_verdicts.py PLATE PAGES [TAG]"""
import collections
import json
import pathlib
import sys

plate = sys.argv[1]
pages = {int(p) for p in sys.argv[2].split(",")}
tag = sys.argv[3] if len(sys.argv) > 3 else "20261117-night"
D = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/_shared-records") / ("lane-report-slices-%s" % tag) / plate
c = collections.Counter()
near = []
for line in open(D / "verdicts.jsonl"):
    i = line.find('"subject": "')
    sub = line[i + 12:i + 60].split('"')[0]
    p = sub.split("/")
    if len(p) < 2 or not p[1].isdigit() or int(p[1]) not in pages:
        continue
    if '"quantity": "notehead_is_not_a_notehead"' not in line:
        continue
    r = json.loads(line)
    d = r.get("detail") or {}
    refused = r["value"] is True
    c[("refused" if refused else "kept", r["reason"] if refused else "-")] += 1
    for key in ("ink_consult", "claim_final"):
        e = d.get(key)
        if e and not refused:
            near.append({"subject": r["subject"], "key": key, "by": e.get("by"), "share": e.get("share"), "tier": e.get("tier"), "by_tier": e.get("by_tier"),
                         "owns": e.get("owns")})
tot_kept = sum(v for (k, _r), v in c.items() if k == "kept")
print(plate, "pages", sorted(pages), "head verdicts: kept (written as a head candidate)", tot_kept, "refused", sum(v for (k, _r), v in c.items() if k == "refused"))
for (k, r), v in c.most_common():
    if k == "refused":
        print("   refused", r, v)
print("KEPT boxes that carry an ink_consult / claim_final entry (a claim of an EARLIER tier held >= 25% of the box, box not refused):", len(near))
by = collections.Counter((n["by"], "owns" if n["owns"] else "owns-nothing", n["share"] >= 0.5) for n in near)
for k, v in by.most_common():
    print("   ", k, v)
json.dump(near, open("/tmp/claude-near-%s.json" % plate, "w"))
