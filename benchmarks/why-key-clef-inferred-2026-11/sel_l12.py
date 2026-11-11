"""Selection of every filled-key / filled-clef staff-system in one analyze.py JSON, for crops.py.
    python3 sel_l12.py X.json PLATE OUT.json"""
import json
import sys

d = json.load(open(sys.argv[1]))
out = []
for k, v in sorted(d["staffs"].items(), key=lambda kv: tuple(int(x) for x in kv[0].split("/")[1:])):
    kf = v["key"] and v["key"][0]["decider"].startswith("infer")
    cf = v["clef"] and v["clef"][0]["decider"].startswith("infer")
    if kf or cf:
        b = ("K:" + v["key"][-1]["reason"] if kf else "") + (" C:" + v["clef"][-1]["reason"] if cf else "")
        out.append(dict(plate=sys.argv[2], json=sys.argv[1], staff=k, bucket=b.strip()))
json.dump(out, open(sys.argv[3], "w"), indent=1)
print(len(out))
