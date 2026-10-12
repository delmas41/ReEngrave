"""join why (reconcile's own landing search) with shape (the unique-by-candidates
test) for the single-head unique bars.  python3 join_2_97.py WHY.json SHAPE.json"""
import collections
import json
import sys

why = json.load(open(sys.argv[1]))
shape = json.load(open(sys.argv[2]))
cnt = collections.Counter()
ex = collections.defaultdict(list)
for k, s in shape.items():
    if s.get("shape") != "1 head" or s.get("landings") != 1:
        continue
    w = why.get("cell/" + k) or why.get(k) or {}
    land = w.get("landings") or []
    key = (w.get("why"), "fits_now" if w.get("fits_now") else
           ("short" if (w.get("total") or 0) < (w.get("expected") or 0) else "long"),
           tuple(sorted((l[0], l[2]) for l in land)))
    cnt[key[:2] + (len(land), "decided_moved" if any(l[0] == "decided" for l in land) else "narrowed_only")] += 1
    ex[key[:2]].append((k, w.get("total"), w.get("expected"), land))
for k, v in sorted(cnt.items(), key=lambda kv: -kv[1]):
    print(v, k)
for k, v in ex.items():
    print(k)
    for e in v[:4]:
        print("   ", e)
