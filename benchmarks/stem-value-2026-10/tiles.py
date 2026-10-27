"""2.209: the 12 blind tiles. 3 changed notes (the lane_report's own key), 5 boxes the flag takes out of a stem that change nothing in the
file, 4 controls drawn at random (seed 2209) from the decided notes the stem rule still rewrites with the flag ON. Orange box only."""
import json, pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from tools.omr.staged import lane_report as LR
out = pathlib.Path("out/print/2.209"); out.mkdir(parents=True, exist_ok=True)
slices = pathlib.Path("out/2.209/slices-full")
def bbox(plate, g):
    for l in open(slices / plate / "observations.jsonl"):
        if g in l and '"glyph_box"' in l:
            o = json.loads(l)
            if o["subject"] == g and o["quantity"] == "glyph_box":
                return o["detail"]["bbox_page_px"]
items = [dict(it) for it in json.load(open("out/lane-report/2.209/key.json"))]
for it in items:
    it["role"] = "case"; it["what"] = "value changed ON (stem value no longer taken from a box on the beam end)"
for g in ("glyph/2/0/7/1/9", "glyph/4/1/8/5/19", "glyph/6/1/7/4/7", "glyph/6/1/7/6/15", "glyph/9/0/7/14/9"):
    items.append(dict(plate="litolff", page=int(g.split("/")[1]), box=bbox("litolff", g), rg=g, role="case", kind="excluded_box",
                      what="box taken out of its stem by the flag; nothing changes in the exported file"))
on = {p: {r["head"] for r in json.load(open("out/2.209/%s.on2.json" % p))["rewrites"] if (r["was"] or {}).get("outcome") == "decided"} for p in ("litolff", "brahms")}
pool = sorted((p, h) for p in on for h in on[p])
rng = random.Random(2209)
for p, h in rng.sample(pool, 4):
    items.append(dict(plate=p, page=int(h.split("/")[1]), box=bbox(p, h), rg=h, role="control", kind="still_rewritten", what="decided note the stem rule still rewrites"))
rng.shuffle(items)
print(LR.cut_tiles(items, out))
