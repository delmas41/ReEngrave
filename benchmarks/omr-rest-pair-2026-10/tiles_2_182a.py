"""2.182a blind tiles: 9 cases drawn at RANDOM (random.Random(2182)) from the counted different-class duplicate-box clusters
(both plates pooled), + 3 controls (single-box rests the reader KEPT: one each eighth, sixteenth, quarter; no overlapping rest box in
the cell). One blue box each (the union of the cluster's boxes, +4 px), nothing else of ours drawn. Key outside the tiles folder.
usage: tiles_2_182a.py OUTROOT LIT_EXTRACT LIT_CASES BRAH_EXTRACT BRAH_CASES"""
import collections, json, os, random, sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
OUT, LE, LC, BE, BC = sys.argv[1:6]
TILES = os.path.join(OUT, "2.182a-rest-pairs"); KEY = os.path.join(OUT, "2.182a-key.json")
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
rnd = random.Random(2182)
ext = {"litolff": json.load(open(LE)), "brahms": json.load(open(BE))}
cases = []
for doc, p in (("litolff", LC), ("brahms", BC)):
    for c in json.load(open(p)):
        cases.append((doc, c))
cases.sort(key=lambda t: (t[0], t[1]["cluster"]))
pick = rnd.sample(cases, 9)
def cell(s): return tuple(s.split("/")[:5])
controls = []
for want in ("rest8th", "rest16th", "restQuarter"):
    pool = []
    for doc in ("litolff", "brahms"):
        e = ext[doc]; sup = {v["supersedes"] for v in e["verdicts"] if v.get("supersedes")}
        live = {v["subject"]: v for v in e["verdicts"] if v["id"] not in sup}
        bycell = collections.defaultdict(list)
        for s in e["boxes"]: bycell[cell(s)].append(s)
        for s, b in sorted(e["boxes"].items()):
            if b["value"][0] == want and live.get(s, {}).get("reason") == "rest" and live[s]["value"] is False and len(bycell[cell(s)]) == 1 and b["bbox"]:
                pool.append((doc, s))
    controls.append(rnd.choice(pool))
items = [("case", d, c["cluster"], c) for d, c in pick] + [("control", d, [s], None) for d, s in controls]
rnd.shuffle(items)
os.makedirs(TILES, exist_ok=True)
for f in os.listdir(TILES):
    if f.startswith("tile_"): os.remove(os.path.join(TILES, f))
cache, key = {}, []
for n, (kind, doc, subs, c) in enumerate(items, 1):
    bs = [ext[doc]["boxes"][s] for s in subs]
    bb = [min(b["bbox"][0] for b in bs) - 4, min(b["bbox"][1] for b in bs) - 4, max(b["bbox"][2] for b in bs) + 4, max(b["bbox"][3] for b in bs) + 4]
    pg = int(subs[0].split("/")[1])
    if (doc, pg) not in cache:
        cache.clear(); cache[(doc, pg)] = Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB")
    im = cache[(doc, pg)]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    u = 32.0 if doc == "brahms" else 15.75
    x0, y0, x1, y1 = int(cx - 6 * u), int(cy - 5 * u), int(cx + 6 * u), int(cy + 5 * u)
    crop = im.crop((x0, y0, x1, y1)).copy()
    rect = [round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)]
    ImageDraw.Draw(crop).rectangle(rect, outline=(31, 111, 235), width=2)
    crop.save(os.path.join(TILES, "tile_%02d.png" % n))
    key.append(dict(tile=n, kind=kind, doc=doc, page=pg, glyphs=subs,
                    detector=[dict(glyph=s, cls=b["value"][0], conf=round(b["score"], 3) if b["score"] is not None else None, bbox=b["bbox"]) for s, b in zip(subs, bs)],
                    union_box_page_px=bb, crop_origin=[x0, y0], rect_in_tile=rect))
open(os.path.join(TILES, "README.md"), "w").write(
    "# 2.182a review\n\nEach picture is a piece of a scanned score page with ONE blue box on it and nothing else drawn. The box only says where to look.\n\n"
    "**Question, for every tile:** what is in the blue box -- an eighth rest, a sixteenth rest, a quarter rest, some other rest, or not a rest at all?\n\n"
    "Answer by tile number, for example `1 8th rest, 2 16th rest, 3 not a rest`.\n")
json.dump(key, open(KEY, "w"), indent=1)
tiles = sorted(f for f in os.listdir(TILES) if f.startswith("tile_"))
assert len(tiles) == len(key) == 12
print("tiles", len(tiles), "cases", sum(k["kind"] == "case" for k in key), "controls", sum(k["kind"] == "control" for k in key))
