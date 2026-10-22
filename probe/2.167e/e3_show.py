"""2.167e probe 3: print one cell's glyphs (class, conf, bbox) with their verdicts, plus stems/beams/events. READ-ONLY.
usage: e3_show.py CELLS.json CELLKEY"""
import json
import sys

d = json.load(open(sys.argv[1]))[sys.argv[2]]
G = {}
for o in d["obs"]:
    if o["subject"].startswith("glyph/"):
        g = G.setdefault(o["subject"], {})
        g.setdefault(o["quantity"], []).append(o)
V = {}
for v in d["verd"]:
    V.setdefault(v["subject"], []).append(v)


def short(x, n=170):
    s = json.dumps(x, default=str)
    return s if len(s) <= n else s[:n] + "..."


print("== cell-level")
for o in d["obs"]:
    if o["subject"].startswith("cell/") and o["quantity"] in ("cell_box", "cell_staff_space", "stem", "beam_stroke", "beam_stem_join", "beam_stem_levels", "stem_tip_ink", "stem_slash"):
        print(" OBS", o["id"], o["quantity"], short(o["value"]), short(o.get("detail"), 150))
for v in d["verd"]:
    if v["subject"].startswith("cell/"):
        vv = {a: b for a, b in v.items() if a not in ("considered", "correlated", "basis")}
        print(" VERD", short(vv, 400))
for sub in sorted(G, key=lambda s: int(s.split("/")[-1])):
    g = G[sub]
    box = g["glyph_box"][0]
    print("==", sub, box["value"], "conf", round(g["glyph_conf"][0]["value"], 3), "reader", box["reader"])
    for q, rows in g.items():
        if q in ("glyph_box", "glyph_conf"):
            continue
        for r in rows:
            print("    obs", q, short(r["value"], 100), short(r.get("detail"), 120))
    for v in V.get(sub, []):
        print("    VERD", v["quantity"], v["outcome"], "|", v.get("decider"), "|", v.get("reason"), "|", short(v.get("value"), 220))
