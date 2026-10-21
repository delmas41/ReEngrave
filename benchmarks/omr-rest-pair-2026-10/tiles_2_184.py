"""2.184 blind tiles: 9 cases drawn at RANDOM (random.Random(2184)) from the inks the ON arm WRITES (pair winners, verdict
`rest_pair_stronger`, both plates pooled, excluding every ink already in 2.182a's tiles), + 3 controls (single-box rests the reader
kept, one each eighth/sixteenth/quarter, no other rest box in the cell, not 2.182a's). One NEUTRAL orange box each (the union of the
ink's boxes, +4 px; orange so it cannot be read as the GUESSED blue), nothing else of ours drawn. Key outside the tiles folder.
usage: tiles_2_184.py OUTROOT REPLAYDIR EX_LIT EX_BRA     (REPLAYDIR holds litolff.on.json / brahms.on.json from replay_2_184.py;
EX_* the extract184.py json of the SAME record)"""
import collections, json, os, random, sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
OUT, RD, XL, XB = sys.argv[1:5]
TILES = os.path.join(OUT, "2.184-rest-pair"); KEY = os.path.join(OUT, "2.184-key.json")
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
ORANGE = (255, 140, 0)
prev = json.load(open("out/print/2.182a-key.json"))
prev_glyphs = {(k["doc"], g) for k in prev for g in k["glyphs"]}
ext = {}
for doc, p in (("litolff", XL), ("brahms", XB)):
    e = json.load(open(p)); ext[doc] = dict(boxes={b["subject"]: b for b in e["boxes"]}, byid={b["id"]: b for b in e["boxes"]})
rnd = random.Random(2184)
cases, ctrl_pool = [], collections.defaultdict(list)
for doc in ("litolff", "brahms"):
    on = json.load(open(os.path.join(RD, "%s.on.json" % doc)))["rest_verdicts"]
    byid = ext[doc]["byid"]
    for g, v in sorted(on.items()):
        if v[0] == "narr" and v[2] == "rest_pair_stronger":
            subs = [g] + [ext[doc]["byid"][c["row"]]["subject"] for c in v[3]["candidates"][1:] if c["row"] in byid]
            if any((doc, s) in prev_glyphs for s in subs):
                continue
            cases.append((doc, g, subs, v))
    cell = lambda s: tuple(s.split("/")[:5])
    bycell = collections.Counter(cell(s) for s in ext[doc]["boxes"])
    for s, b in sorted(ext[doc]["boxes"].items()):
        v = on.get(s)
        if v and v[0] == "deci" and v[1] is False and v[2] == "rest" and bycell[cell(s)] == 1 and b["value"][0] in ("rest8th", "rest16th", "restQuarter") \
                and b["reader"] == "detector" and (doc, s) not in prev_glyphs:
            ctrl_pool[b["value"][0]].append((doc, s))
print("changed inks (excluding 2.182a's):", len(cases), "by plate", collections.Counter(c[0] for c in cases))
pick = rnd.sample(cases, 9)
controls = [rnd.choice(ctrl_pool[w]) for w in ("rest8th", "rest16th", "restQuarter")]
items = [("case", d, subs, v) for d, g, subs, v in pick] + [("control", d, [s], None) for d, s in controls]
rnd.shuffle(items)
os.makedirs(TILES, exist_ok=True)
for f in os.listdir(TILES):
    if f.startswith("tile_"): os.remove(os.path.join(TILES, f))
cache, key = {}, []
for n, (kind, doc, subs, v) in enumerate(items, 1):
    bs = [ext[doc]["boxes"][s] for s in subs]
    bbs = [b["detail"]["bbox_page_px"] for b in bs]
    bb = [min(b[0] for b in bbs) - 4, min(b[1] for b in bbs) - 4, max(b[2] for b in bbs) + 4, max(b[3] for b in bbs) + 4]
    pg = int(subs[0].split("/")[1])
    if (doc, pg) not in cache:
        cache.clear(); cache[(doc, pg)] = Image.fromarray(render_page(PDFS[doc], pg, dpi=600).rgb).convert("RGB")
    im = cache[(doc, pg)]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    u = 32.0 if doc == "brahms" else 15.75
    x0, y0, x1, y1 = int(cx - 6 * u), int(cy - 5 * u), int(cx + 6 * u), int(cy + 5 * u)
    crop = im.crop((x0, y0, x1, y1)).copy()
    rect = [round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)]
    ImageDraw.Draw(crop).rectangle(rect, outline=ORANGE, width=2)
    crop.save(os.path.join(TILES, "tile_%02d.png" % n))
    key.append(dict(tile=n, kind=kind, doc=doc, page=pg, glyphs=subs, winner=subs[0] if kind == "case" else None,
                    detector=[dict(glyph=s, cls=b["value"][0], conf=round(b["score"], 3), bbox=b["detail"]["bbox_page_px"]) for s, b in zip(subs, bs)],
                    margin=(v[4] if v else None), union_box_page_px=bb, crop_origin=[x0, y0], rect_in_tile=rect))
open(os.path.join(TILES, "README.md"), "w").write(
    "# 2.184 review\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn. The orange box only says where to look.\n\n"
    "**Question, for every tile:** what is in the orange box -- an eighth rest, a sixteenth rest, a quarter rest, some other rest, or not a rest at all?\n\n"
    "Answer by tile number, for example `1 8th rest, 2 16th rest, 3 not a rest`.\n")
json.dump(key, open(KEY, "w"), indent=1)
assert len(key) == 12
print("tiles", len(key), "cases", sum(k["kind"] == "case" for k in key), "controls", sum(k["kind"] == "control" for k in key))
