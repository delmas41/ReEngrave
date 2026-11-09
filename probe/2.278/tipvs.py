import json, sys, collections
R = [json.loads(l) for l in open(sys.argv[1])]
c = collections.Counter()
for r in R:
    if r["fate"] != "duration_narrowed" or r["reason"] != "beams_ambiguous": continue
    b = r.get("bfs") or {}
    d = r["d"]
    c[("have_bfs" if b else "no_bfs", "tip_levels=%s" % b.get("tip_levels"), "stem_beamed=%s" % (b.get("tip") or {}).get("stem_beamed"), "cert/poss=%s/%s" % (d.get("levels_certain"), d.get("levels_possible")))] += 1
for k, v in c.most_common(): print(v, k)
