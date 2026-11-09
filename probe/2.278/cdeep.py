import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
N = [r for r in R if r["fate"] == "duration_narrowed" and r["reason"] == "beams_ambiguous" and r["d"].get("stems_attached")]
print(len(N), "beams_ambiguous with an own stem")
c = collections.Counter()
for r in N:
    d = r["d"]; b = (r.get("bfs") or {}).get("settled")
    c[("by_stem=%s" % min(d.get("beams_by_stem") or 0, 2), "bfs=%s" % b, "cert/poss=%s/%s" % (d.get("levels_certain"), d.get("levels_possible")))] += 1
for k, v in c.most_common(): print(v, k)
D = [r for r in R if r["fate"] == "duration_narrowed" and r["reason"] == "beam_discounted_uncertain" and r["d"].get("stems_attached")]
print(len(D), "beam_discounted_uncertain with an own stem")
w = collections.Counter()
for r in D:
    y = r["d"].get("beams_not_by_ink_why") or {}
    w[json.dumps(y, sort_keys=True)] += 1
for k, v in w.most_common(8): print(v, k)
