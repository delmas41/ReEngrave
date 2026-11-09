import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
c = collections.Counter()
ex = {}
for r in R:
    if r["fate"] != "duration_narrowed": continue
    b = r.get("bfs")
    if not b or b.get("settled") != "disagree_narrowed": continue
    k = (r["reason"], tuple(b.get("before") or ()), tuple(b.get("after") or ()), b.get("tip_levels"), b.get("flag_levels"), len(b.get("boxes") or ()))
    c[k] += 1; ex.setdefault(k, (r["sub"], b))
for k, v in c.most_common(12): print(v, k)
print(json.dumps(next(iter(ex.values())), default=str)[:1500])
