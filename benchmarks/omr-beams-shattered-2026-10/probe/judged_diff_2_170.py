"""2.170: which of Sean's judged tiles move between the OFF and ON judged scores. usage: judged_diff_2_170.py OFF.json ON.json"""
import json
import sys

a, b = (json.load(open(p))["tiles"] for p in sys.argv[1:3])
ka = {(r["item"], r["tile"], str(r.get("subject"))): r for r in a}
n = 0
for r in b:
    k = (r["item"], r["tile"], str(r.get("subject")))
    o = ka.get(k)
    if o and o["status"] != r["status"]:
        n += 1
        print("%s tile %s %s: %s -> %s  (Sean: %r) %s" % (r["item"], r["tile"], r.get("subject"), o["status"], r["status"],
                                                        r.get("answer"), r.get("note") or ""))
print("moved", n)
