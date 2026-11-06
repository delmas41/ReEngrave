"""Decided same-position ties whose flank search finds a head between (tie_pair `not_adjacent`) and binder `same_pitch_heads_between`: what the page
binding knows about them (measure only). A tie never skips a note (page-facts 10-01), so a curve whose two bound ends are one pitch with notes between
can only be a slur (Sean's rule: two notes of different pitch / not adjacent -> slur). python3 not_adjacent.py PLATE [ARM]"""
import collections
import json
import pathlib
import sys

plate = sys.argv[1]
arm = sys.argv[2] if len(sys.argv) > 2 else "base"
led = json.load(open(pathlib.Path("scratch/dd") / ("%s.%s.ledger.json" % (plate, arm))))
c = collections.Counter()
for r in led["rows"]:
    lr = r.get("lost_rule") or ""
    pb = r.get("binding") or {}
    if lr == "tie_pair:not_adjacent" or pb.get("why") == "same_pitch_heads_between":
        both = bool((pb.get("left") or {}).get("head")) and bool((pb.get("right") or {}).get("head"))
        c[("not_adjacent" if lr == "tie_pair:not_adjacent" else "binder_same_pitch_heads_between", "both ends bound by the page binder" if both else "ends not bound",
            "relation=%s" % pb.get("relation"), "fate=%s" % r["fate"])] += 1
for k, v in c.most_common():
    print(v, k)
