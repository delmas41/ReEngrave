"""2.138 helper: index the cached p24 rows by glyph subject; list what stands near a page-px point (600 dpi). STAGED GATHER/ADJUDICATE rows."""
import json, sys, collections
D = json.load(open(__file__.rsplit("/",1)[0] + "/out/p24_slim.json"))
obs = collections.defaultdict(list)
for o in D["observations"]: obs[o["subject"]].append(o)
ver = collections.defaultdict(list)
for v in D["verdicts"]: ver[v["subject"]].append(v)
absn = collections.defaultdict(list)
for a in D["abstentions"]: absn[a["subject"]].append(a)
def box(subj):
    for o in obs[subj]:
        if o["quantity"] == "glyph_box":
            b = o["detail"]["bbox_page_px"]; return b, o["value"][0], o["score"]
    for a in absn[subj]:
        pass
    return None
def near(x, y, r=120):
    out = []
    for s in set(list(obs) + list(ver)):
        if not s.startswith("glyph/"): continue
        b = box(s)
        if not b: continue
        bb = b[0]; cx, cy = (bb[0]+bb[2])/2, (bb[1]+bb[3])/2
        if abs(cx-x) <= r and abs(cy-y) <= r: out.append((s, b[1], [round(v) for v in bb], round(b[2],2)))
    return sorted(out, key=lambda t: (t[2][0], t[2][1]))
def describe(s):
    d = {"subject": s}
    for o in obs[s]:
        if o["quantity"] in ("aug_dot","articulation_mark","mark_shape","glyph_box","notehead_class"):
            d[o["quantity"]] = (o["value"], o.get("score"), {k:v for k,v in o["detail"].items() if k!="bbox_page_px"})
    for v in ver[s]:
        if v["quantity"] in ("dot_role","articulation_owner","articulation_is_not_an_articulation"):
            d[v["quantity"]] = (v["outcome"], v["value"], v["reason"], v["margin"], v["candidates"], {k:v2 for k,v2 in v["detail"].items()})
    d["abstain"] = [(a["quantity"], a["reason"]) for a in absn[s]]
    return d
if __name__ == "__main__":
    x, y = float(sys.argv[1]), float(sys.argv[2]); r = float(sys.argv[3]) if len(sys.argv) > 3 else 120
    for t in near(x, y, r): print(t)
