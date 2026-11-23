"""2306 r11 debug: for a fixture tile, the head's ink strokes, the runs near it, each run's column chain (does it reach the head?), margin, reach,
head-end test. Usage (cwd = tree): r11_dbg.py FX.json NAME"""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.staged import page_stems as PS
c = json.load(open(sys.argv[1]))[sys.argv[2]]
heads = [dict(h, box=tuple(h["box"])) for h in c["heads"]]
verts = [dict(v, box=tuple(v["box"])) for v in c["verticals"]]
cross = [dict(x, box=tuple(x["box"])) for x in c["crossers"]]
held = {int(k): v for k, v in c["held"].items()}
strokes = {int(k): dict(v, box=tuple(v["box"])) for k, v in c["strokes"].items()}
h = next(h for h in heads if c["glyph"] in h["members"])
print("head", h["id"], [round(v) for v in h["box"]], "ink?", h["ink"], "claim strokes", h["strokes"])
x0, y0, x1, y1 = h["box"]
ink = set(h["strokes"])
for o, s in strokes.items():
    b = s["box"]
    if s["kind"] not in ("vertical", "barline") and o not in held and x0 <= (b[0] + b[2]) / 2 <= x1 and y0 <= (b[1] + b[3]) / 2 <= y1:
        ink.add(o)
print("ink strokes", sorted(ink), [(o, strokes[o]["kind"], [round(v) for v in strokes[o]["box"]], strokes[o]["touches"]) for o in sorted(ink) if o in strokes])
runs, _ = PS.join_runs(verts, heads, cross, held)
for r in runs + [dict(ord=v["ord"], box=v["box"], sp=v["sp"], members=[v["ord"]]) for v in verts if not any(v["ord"] in rr["members"] for rr in runs)]:
    b = r["box"]
    if b[2] < x0 - 40 or b[0] > x1 + 40:
        continue
    print("run", r["ord"], r["members"], [round(v) for v in b], "held" if r["ord"] in held else "",
          "touches of members:", [(m, strokes.get(m, {}).get("touches")) for m in r["members"]])
for o, s in strokes.items():
    b = s["box"]
    if b[2] >= x0 - 20 and b[0] <= x1 + 20 and b[3] >= y0 - 60 and b[1] <= y1 + 60:
        print("   stroke", o, s["kind"], [round(v) for v in b], "held:" + str(held.get(o)) if o in held else "", s["touches"])
