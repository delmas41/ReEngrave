"""2.277: which verdicts moved between the OFF and ON arms of a lane_report (the mini-records).  usage: arm_diff.py WORKDIR PLATE OUT.json"""
import collections, json, sys
work, plate, out = sys.argv[1:4]


def load(arm):
    d = json.load(open("%s/%s.%s.mini-record.json" % (work, plate, arm)))
    v = {}
    for x in d["verdicts"]:
        v[(x["subject"], x["quantity"])] = (x["outcome"], x.get("value") if not isinstance(x.get("value"), (dict, list)) else str(x.get("value"))[:60], x.get("reason"))
    return v


a = load("off")
b = load("on")
moved = []
c = collections.Counter()
for k in set(a) | set(b):
    if a.get(k) != b.get(k):
        moved.append([k[0], k[1], a.get(k), b.get(k)])
        c[(k[1], str(a.get(k, (None, None, None))[2]), str(b.get(k, (None, None, None))[2]))] += 1
json.dump(moved, open(out, "w"))
print("moved", len(moved))
for k, n in c.most_common(40):
    print(n, k)
