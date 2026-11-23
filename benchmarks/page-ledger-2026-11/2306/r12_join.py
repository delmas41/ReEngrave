"""2306 r12: the run joins in a fixture window -- every joined pair (upper, lower, kind) with whether the two pieces are CONNECTED BY INK (the page
map's contact: directly, or through one stroke touching both), and the reading of given glyphs before/after. Usage (cwd = tree): r12_join.py FX NAME glyph.."""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
c = json.load(open(sys.argv[1]))[sys.argv[2]]
gs = sys.argv[3:]
heads = [dict(h, box=tuple(h["box"])) for h in c["heads"]]
verts = [dict(v, box=tuple(v["box"])) for v in c["verticals"]]
cross = [dict(x, box=tuple(x["box"])) for x in c["crossers"]]
held = {int(k): v for k, v in c["held"].items()}
strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in c["strokes"].items()}
tch = {o: {int(j) for j, _c in (s.get("touches") or ())} for o, s in strokes.items()}
for o, ts in list(tch.items()):
    for j in ts:
        tch.setdefault(j, set()).add(o)
pairs = []
runs, cen = PS.join_runs(verts, heads, cross, held, pairs)
for a, b, k in pairs:
    if k.startswith("!"):
        continue
    direct = b in tch.get(a, set())
    via = sorted(tch.get(a, set()) & tch.get(b, set()))
    print("joined %s %s %-12s direct contact %s, through %s" % (a, b, k, direct, [(x, strokes[x]["kind"]) for x in via if x in strokes]))
res = PS.read(heads, verts, held, crossers=cross, strokes=strokes)
for g in gs:
    h = next(h for h in heads if g in h["members"])
    r = res["heads"][h["id"]]
    st = res["stems"].get(r.get("stroke"))
    print(g, r["how"], r.get("direction"), r.get("stroke"), st and (st["members"], st["box"]))
