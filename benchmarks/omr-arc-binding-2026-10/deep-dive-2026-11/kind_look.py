"""Brahms p0: hand class slur but our written kind tie (and the reverse) -- by origin, with the curve and its binding (measure only)."""
import collections
import json
import sys

hs = json.load(open("scratch/dd/brahms.base.handscore.json"))
led = {r["curve"]: r for r in json.load(open("scratch/dd/brahms.base.ledger.json"))["rows"]}
c = collections.Counter()
for o in hs:
    if o["fate"] in ("written", "two_arcs", "wrong_note") and o.get("kind") and o["kind"] != o["cls"]:
        r = led[o["curve"]]
        pb = r.get("binding") or {}
        c[(o["cls"], o["kind"], o["origin"], pb.get("rule") or pb.get("kind"), "classes=" + "/".join(r["classes"]))] += 1
        if "--v" in sys.argv:
            print(o["id"], o["cls"], "->", o["kind"], o["origin"], r["curve"], r["classes"], "pair", r.get("pair"), "pb", pb.get("kind"), pb.get("relation"), pb.get("why"))
for k, v in c.most_common():
    print(v, k)
