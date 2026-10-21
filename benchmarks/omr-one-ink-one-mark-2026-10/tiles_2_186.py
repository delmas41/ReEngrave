"""2.186 blind tiles: 9 inks the flag CHANGES, drawn at random (random.Random(2186), pools sorted before sampling, both plates pooled) -- 3 rests merged
from two classes, 3 accidentals merged from two classes, 3 accidentals whose ink changes hands (the copy in the other staff's cell no longer owns a head) --
plus 3 controls the flag does not touch (a lone rest, two lone accidentals that own a head in both arms). One NEUTRAL ORANGE box each (the union of the ink's
boxes +4 px); nothing else of ours drawn (orange so it cannot be read as the GUESSED blue). Key outside the tiles folder.
usage: tiles_2_186.py OUTROOT REPLAYDIR SLICEDIR"""
import collections, glob, json, os, random, sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
from tools.omr.staged import one_ink as OI
OUT, RD, SD = sys.argv[1:4]
TILES = os.path.join(OUT, "2.186-one-ink-one-mark"); KEY = os.path.join(OUT, "2.186-key.json")
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
ORANGE = (255, 140, 0)
pools = collections.defaultdict(list)
box_of = {}
for doc in ("litolff", "brahms"):
    off = json.load(open(os.path.join(RD, "%s.off.json" % doc)))["verdicts"]
    on = json.load(open(os.path.join(RD, "%s.on.json" % doc)))["verdicts"]
    cells = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(SD, doc, "p*.observations.jsonl"))):
        for l in open(p):
            if '"glyph_box"' not in l:
                continue
            o = json.loads(l)
            if o["quantity"] == "glyph_box" and o["reader"] == "detector" and isinstance(o["value"], list) and (o.get("detail") or {}).get("bbox_page_px"):
                box_of[(doc, o["subject"])] = o["detail"]["bbox_page_px"]
                cells["/".join(o["subject"].split("/")[:5])].append(o)
    plans = {}
    for cell, bs in cells.items():
        bs.sort(key=lambda o: int(o["subject"].split("/")[5]))
        pl = OI.plan([(o["value"][0], o["value"][1], o["value"][2], o["value"][3], o["value"][4], o["score"] or 0.0) for o in bs])
        for i, info in pl.items():
            plans[bs[i]["subject"]] = ([bs[i]["subject"]] + [bs[j]["subject"] for j in info["absorbed"]], info, bs[i]["value"][0])
    for g, v in sorted(on.get("rest_is_not_a_rest", {}).items()):
        if v[2] == "one_ink_merged" and g in plans:
            pools["rest_merged"].append((doc, plans[g][0], dict(winner=plans[g][2], rivals=plans[g][1]["rivals"], margin=plans[g][1]["margin"])))
    for g, v in sorted(on.get("accidental_owner", {}).items()):
        o = off.get("accidental_owner", {}).get(g)
        if v[4] and g in plans and v[0] == "deci":
            pools["acc_merged"].append((doc, plans[g][0], dict(winner=plans[g][2], rivals=plans[g][1]["rivals"], margin=plans[g][1]["margin"], off=o and o[:3])))
        elif v[0] == "abst" and v[2] in ("owned_by_another_staff", "ownership_undecided") and o and o[0] == "deci":
            pools["acc_changes_hands"].append((doc, [g], dict(on_reason=v[2], off=o[:3])))
    # controls: lone, untouched, same verdict both arms
    for g, v in sorted(on.get("rest_is_not_a_rest", {}).items()):
        o = off.get("rest_is_not_a_rest", {}).get(g)
        if v[0] == "deci" and v[1] is False and v[2] == "rest" and o and o[:3] == v[:3] and g not in plans and (doc, g) in box_of:
            pools["ctl_rest"].append((doc, [g], {}))
    for g, v in sorted(on.get("accidental_owner", {}).items()):
        o = off.get("accidental_owner", {}).get(g)
        if v[0] == "deci" and o and o[:3] == v[:3] and not v[4] and g not in plans and (doc, g) in box_of:
            pools["ctl_acc"].append((doc, [g], dict(cls=None)))
print({k: len(v) for k, v in pools.items()})
rnd = random.Random(2186)
items = []
for k, n in (("rest_merged", 3), ("acc_merged", 3), ("acc_changes_hands", 3)):
    for it in rnd.sample(pools[k], min(n, len(pools[k]))):
        items.append((k, "case") + it)
for k, n in (("ctl_rest", 1), ("ctl_acc", 2)):
    for it in rnd.sample(pools[k], n):
        items.append((k, "control") + it)
rnd.shuffle(items)
os.makedirs(TILES, exist_ok=True)
for f in os.listdir(TILES):
    if f.startswith("tile_"): os.remove(os.path.join(TILES, f))
cache, key = {}, []
for n, (k, kind, doc, subs, info) in enumerate(items, 1):
    bbs = [box_of[(doc, s)] for s in subs]
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
    key.append(dict(tile=n, stratum=k, kind=kind, doc=doc, page=pg, glyphs=subs, info=info, union_box_page_px=bb, crop_origin=[x0, y0], rect_in_tile=rect))
open(os.path.join(TILES, "README.md"), "w").write(
    "# 2.186 review\n\nEach picture is a piece of a scanned score page with ONE orange box on it and nothing else drawn. The orange box only says where to look.\n\n"
    "**Question, for every tile:** what is in the orange box -- an eighth / sixteenth / quarter / other rest, a sharp, a flat, a natural, or not a music symbol at all? "
    "If the mark stands between two staves, also say which staff it belongs to (upper or lower).\n\n"
    "Answer by tile number, for example `1 8th rest, 2 flat upper, 3 not a symbol`.\n")
json.dump(key, open(KEY, "w"), indent=1)
print("tiles", len(key), collections.Counter((k["stratum"], k["kind"]) for k in key))
