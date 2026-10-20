"""2.167e probe 25: the duration reason of all whole-valued heads, both plates. usage: e25_reasons.py"""
import json
import collections

c = collections.Counter()
for pl in ("lit", "bra"):
    for r in json.load(open("probe/2.167e/data/%s_whole.json" % pl)):
        c[(pl, r["dur_reason"])] += 1
print(dict(c))
