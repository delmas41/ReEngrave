"""case 3: for the glyphs the exporter refused as ink_is_a_whole_rest, list class, conf, and every verdict/observation about them."""
import json, pickle, collections, sys
pl, pk = sys.argv[1], sys.argv[2]
d = pickle.load(open("out/lane-report/whole-rest/%s.pkl" % pk, "rb"))
F = json.load(open("out/lane-report/whole-rest/fates.%s.json" % pl))
subs = []
for b in F["bars"]:
    for g in b["glyphs"]:
        if g[2] == "ink_is_a_whole_rest":
            subs.append("glyph/%s/%s" % (b["key"], g[0]))
print(len(subs), "glyphs")
obs = collections.defaultdict(list); ver = collections.defaultdict(list)
for o in d["observations"]:
    obs[o["subject"]].append(o)
for v in d["verdicts"]:
    ver[v["subject"]].append(v)
cls = collections.Counter(); conf = []
rs = collections.Counter(); hr = collections.Counter(); nn = collections.Counter()
rows = []
for s in subs:
    gb = [o for o in obs[s] if o["quantity"] == "glyph_box"][0]
    c = gb["value"][0]; cls[c] += 1
    cf = [o["value"] for o in obs[s] if o["quantity"] == "glyph_conf"]
    conf.append(cf[0] if cf else None)
    vs = {v["quantity"]: (v["outcome"], v["reason"], v.get("value")) for v in ver[s]}
    rs[vs.get("notehead_is_a_whole_rest", ("-", "-"))[:2]] += 1
    hr[vs.get("head_ink_is_a_rest", ("-", "-"))[:2]] += 1
    nn[vs.get("notehead_is_not_a_notehead", ("-", "-"))[:2]] += 1
    rows.append((s, c, cf[0] if cf else None, vs, [o["quantity"] for o in obs[s]]))
print("classes", dict(cls))
print("conf", sorted(round(x, 2) for x in conf if x is not None))
print("notehead_is_a_whole_rest", dict(rs))
print("head_ink_is_a_rest", dict(hr))
print("notehead_is_not_a_notehead", dict(nn))
for r in rows[:3]:
    print(r[0], r[1], r[2]); print("  ", json.dumps(r[3])[:700]); print("  ", sorted(set(r[4])))
json.dump([(r[0], r[1], r[2]) for r in rows], open("out/lane-report/whole-rest/c3_%s.json" % pl, "w"))
