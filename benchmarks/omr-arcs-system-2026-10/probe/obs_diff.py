"""ROADMAP 2.166 -- GATHER rows that differ OFF vs ON for subjects under a prefix (debug).
usage: obs_diff.py PREFIX(out/2.166/ab_brahms_p1) SUBJECT_PREFIX"""
import collections
import json
import sys

pre, sub = sys.argv[1], sys.argv[2]
arms = {}
for arm in ("off", "on"):
    rec = json.load(open("%s.%s.record.json" % (pre, arm)))["record"]
    rows = collections.defaultdict(list)
    for o in rec["observations"]:
        if sub in o["subject"] and o["quantity"] != "system_arc":
            rows[(o["subject"], o["quantity"])].append(json.dumps([o.get("value"), o.get("detail")], sort_keys=True,
                                                                  default=str)[:300])
            rows[(o["subject"], o["quantity"])][-1] = __import__("re").sub(r"obs:\d+", "obs", rows[(o["subject"], o["quantity"])][-1])
    arms[arm] = rows
for k in sorted(set(arms["off"]) | set(arms["on"])):
    if sorted(arms["off"].get(k, [])) != sorted(arms["on"].get(k, [])):
        print(k)
        print("  OFF", arms["off"].get(k))
        print("  ON ", arms["on"].get(k))
