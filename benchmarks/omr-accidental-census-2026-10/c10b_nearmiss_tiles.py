"""2.197 C10b: a look (mine) at 8 random Brahms accidentals whose owner abstained no_candidate because the nearest head right of them was 1.4-2.0 positions off
(the owner's own |dy| bound is 1.4). Tile = page ink; ORANGE = the accidental's box; GREEN = the nearest head that reaches past it.
usage: c10b_nearmiss_tiles.py VIEW.json XML PDF OUT.png"""
import sys, json, random, collections, fitz
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View, fam
from PIL import Image, ImageDraw, ImageFont
v = View(sys.argv[1], sys.argv[2]); UNIT = 32.25
pos = {o["subject"]: float(o["value"]) for o in v.obs if o["quantity"] == "notehead_staff_position" and isinstance(o["value"], (int, float))}
heads = collections.defaultdict(list)
for pg, bs in v.boxes.items():
    for g in bs:
        if g["category"] == "notehead" and g["reader"] == "detector": heads[(g["page"], g["system"], g["staff"], g["cell"])].append(g)
cases = []
for pg, bs in v.boxes.items():
    for g in bs:
        if g["reader"] != "detector" or fam(g["cls"]) != "accidental": continue
        own = v.verdict(g["key"], "accidental_owner")
        if not own or own["reason"] != "no_candidate": continue
        b = g["box"]; row = v.accpos.get(g["key"])
        if (b[3] - b[1]) / UNIT < 1.6 or not row: continue
        apos = float(row["value"]); best = None
        for h in heads.get((g["page"], g["system"], g["staff"], g["cell"]), ()):
            nv = v.verdict(h["key"], "notehead_is_not_a_notehead")
            if nv and nv["outcome"] == "decided" and nv["value"] is True: continue
            if h["box"][2] < b[2] or (h["box"][0] - b[2]) / UNIT > 1.75 or h["key"] not in pos: continue
            dy = abs(pos[h["key"]] - apos)
            if best is None or dy < best[0]: best = (dy, h)
        if best and 1.4 < best[0] <= 2.0: cases.append((g, best[1], best[0]))
random.Random(197).shuffle(cases); pick = cases[:8]
doc = fitz.open(sys.argv[3]); cache = {}; tiles = []; font = ImageFont.load_default(); key = []
for i, (g, h, dy) in enumerate(pick):
    pg = g["page"]
    if pg not in cache:
        pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY); cache[pg] = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
    b = g["box"]; cx = (b[0] + h["box"][2]) / 2; cy = (b[1] + b[3]) / 2; R = 3.5 * UNIT
    a, t, c, d = int(cx - 2.0 * R), int(cy - R), int(cx + 2.0 * R), int(cy + R); SC = 1.8
    crop = cache[pg].crop((a, t, c, d)).resize((int((c - a) * SC), int((d - t) * SC)), Image.LANCZOS); dr = ImageDraw.Draw(crop)
    dr.rectangle([(b[0] - a) * SC, (b[1] - t) * SC, (b[2] - a) * SC, (b[3] - t) * SC], outline=(255, 140, 0), width=2)
    hb = h["box"]; dr.rectangle([(hb[0] - a) * SC, (hb[1] - t) * SC, (hb[2] - a) * SC, (hb[3] - t) * SC], outline=(0, 160, 0), width=2)
    cv = Image.new("RGB", (crop.width, crop.height + 14), (255, 255, 255)); cv.paste(crop, (0, 14)); ImageDraw.Draw(cv).text((3, 2), "N%d %s dy=%.1f pos" % (i, g["cls"].replace("accidental", "acc"), dy), fill=(0, 0, 0), font=font)
    tiles.append(cv); key.append(dict(tile=i, key=g["key"], cls=g["cls"], dy=round(dy, 2), head=h["key"]))
W = max(t.width for t in tiles); rows = [tiles[j:j + 2] for j in range(0, len(tiles), 2)]; H = sum(max(t.height for t in r) + 4 for r in rows)
sh = Image.new("RGB", (W * 2 + 4, H), (255, 255, 255)); y = 0
for r in rows:
    x = 0
    for t in r: sh.paste(t, (x, y)); x += W + 4
    y += max(t.height for t in r) + 4
sh.save(sys.argv[4]); json.dump(dict(n_cases=len(cases), key=key), open(sys.argv[4] + ".json", "w")); print(len(cases), "cases; tiles", len(tiles))
