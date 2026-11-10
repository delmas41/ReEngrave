import collections
import json
import sys

rows = json.load(open(sys.argv[1]))
c = collections.Counter()
for r in rows:
    if r["kind"] == "stroke":
        b, a = r["base"], r["arm"]
        c[("stroke", (b[0], b[1]) if b else None, (a[0], a[1]) if a else None)] += 1
    elif r["kind"] == "head":
        c[("head", tuple(r["base"] or ()), tuple(r["arm"] or ()))] += 1
    else:
        c[(r["kind"], tuple(map(str, (r["base"] or ())[:2])), tuple(map(str, (r["arm"] or ())[:2])))] += 1
for k, n in c.most_common(40):
    print(n, k)
