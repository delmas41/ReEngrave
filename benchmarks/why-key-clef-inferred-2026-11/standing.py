"""Standing key / clef of every staff-system: READ (adjudicate decided) / FILLED (infer) / still abstained or narrowed (and why).
    python3 standing.py X.json [X.json ...]"""
import collections
import json
import sys

for path in sys.argv[1:]:
    d = json.load(open(path))
    S = d["staffs"]
    kc, cc = collections.Counter(), collections.Counter()
    for k, v in S.items():
        for name, ch, c in (("key", v["key"], kc), ("clef", v["clef"], cc)):
            if not ch:
                c["no verdict"] += 1
                continue
            t = ch[0]
            if t["outcome"] == "decided":
                c["READ (adjudicate)" if not t["decider"].startswith("infer") else "FILLED (infer)"] += 1
            else:
                c["%s: %s" % (t["outcome"], t["reason"])] += 1
    print(path.split("/")[-1], d["plate"], d["pages"], "staff-systems", len(S))
    print("  key :", dict(kc.most_common()))
    print("  clef:", dict(cc.most_common()))
    by_page = collections.defaultdict(lambda: collections.Counter())
    for k, v in S.items():
        p = k.split("/")[1]
        t = v["key"][0] if v["key"] else None
        by_page[p]["staves"] += 1
        if t and t["decider"].startswith("infer"):
            by_page[p]["key_filled"] += 1
        c = v["clef"][0] if v["clef"] else None
        if c and c["decider"].startswith("infer"):
            by_page[p]["clef_filled"] += 1
    print("  per page:", {p: dict(c) for p, c in sorted(by_page.items(), key=lambda kv: int(kv[0]))})
