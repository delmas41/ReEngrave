"""usage: pd_cmp.py OFF.json ON.json SUBSTR -- print verdict rows whose subject contains SUBSTR, OFF vs ON, only where they differ (value/outcome/reason)"""
import json, sys
a = json.load(open(sys.argv[1]))
b = json.load(open(sys.argv[2]))
sub = sys.argv[3]


def idx(rows):
    d = {}
    for kind, rid, s, q, o, v, reason, det in rows:
        if kind == "verdicts" and sub in s:
            d[(s, q)] = (o, v, reason, det)
    return d


A, B = idx(a), idx(b)
for k in sorted(set(A) | set(B)):
    if A.get(k, (None,) * 4)[:3] != B.get(k, (None,) * 4)[:3]:
        print(k)
        print("   OFF", A.get(k, (None,) * 4)[:3], (A.get(k, (None,) * 4)[3] or "")[:200])
        print("   ON ", B.get(k, (None,) * 4)[:3], (B.get(k, (None,) * 4)[3] or "")[:200])
