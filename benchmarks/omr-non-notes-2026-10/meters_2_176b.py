"""2.176b: print the meter reads and the timeSig boxes of one system from a probe JSON. usage: meters_2_176b.py PROBE.json PAGE SYSTEM"""
import json
import sys

d = json.load(open(sys.argv[1]))
pg, sy = sys.argv[2], sys.argv[3]
for m in d["meters"]:
    s = m[0].split("/")
    if s[1] == pg and s[2] == sy:
        print("READ", m)
for g, (val, bb) in sorted(d["boxes"].items()):
    s = g.split("/")
    if s[1] == pg and s[2] == sy and str(val[0]).startswith("timeSig"):
        print("TS", g, val[0], [round(x) for x in bb])
