"""2.209: classify the decided->moved rewrites by what moved (level / dots / base) and who voted."""
import json, sys, collections
def kind(r):
    w = r["was"]; n = r["now"]
    k = []
    if w["beam_levels"] != n["beam_levels"]: k.append("levels")
    if w["dots"] != n["dots"]: k.append("dots")
    wb = w["written"]/ (1.5 if w["dots"]==1 else 1.75 if w["dots"]==2 else 1) ; nb = n["written"]/(1.5 if n["dots"]==1 else 1.75 if n["dots"]==2 else 1)
    if abs(wb-nb) > 1e-6 and not (w["beam_levels"] != n["beam_levels"]): k.append("base")
    return "+".join(k) or "other"
for plate in sys.argv[1:]:
    d = json.load(open("out/2.209/%s.off.json" % plate))
    rs = [r for r in d["rewrites"] if (r["was"] or {}).get("outcome") == "decided"]
    print(plate, "rewrites", d["n_stem_value_rewrites"], "of a DECIDED value", len(rs))
    c = collections.Counter(kind(r) for r in rs); print("  by what moved", dict(c))
    for r in rs:
        k = kind(r)
        if "levels" not in k: continue
        lf = r["levels_from"]
        m = {x["key"]: x for x in r["member_info"]}
        t = m.get(lf, {})
        print("  LEVELS", r["head"], r["was"], "->", r["now"]["written"], "from", lf, "score", round(t.get("score") or -1, 2), t.get("cls"), "first", t.get("first"), "strokes", json.dumps(t.get("strokes"))[:200])
