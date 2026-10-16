"""ROADMAP 2.144 -- diff the OFF and ON arms of replay_2_144.py: every verdict that changes."""
import json, sys, collections
d = json.load(open(sys.argv[1]))
off, on = d["off"], d["on"]
chg = collections.Counter(); rows = []
for s in sorted(set(off) | set(on)):
    for q in set(off.get(s, {})) | set(on.get(s, {})):
        a, b = off.get(s, {}).get(q), on.get(s, {}).get(q)
        if a != b:
            chg[(q, tuple(a or ()) [::2] if a else None, tuple(b or ())[::2] if b else None)] += 1
            rows.append((s, q, a, b))
print("verdicts compared", sum(len(v) for v in off.values()), "changed", len(rows))
for k, n in chg.most_common(): print(n, k)
for r in rows: print(r)
