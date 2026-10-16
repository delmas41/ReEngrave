"""2.138 blind tiles. python3 tiles_2_138.py ON_RECORD.json P24_SLIM.json TILE_DIR KEY_JSON
Sean's four misses (head boxes), 4 other newly read wedges, 2 plain-staccato controls. 600 dpi, RED corners on the NOTE only,
nothing of ours drawn. Key (what each is) goes to KEY_JSON, never beside the tiles. Shuffled (seed 2138)."""
import json, random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.omr.staged.record_io import load_record
ON, SLIM, OUT, KEY = sys.argv[1:5]
Image.MAX_IMAGE_PIXELS = None
page = Image.open(str(Path(__file__).parent / "out/p24_600.png")).convert("RGB")
r = load_record(ON); r = r.get("record", r)
box = {o["subject"]: o for o in r["observations"] if o["quantity"] == "glyph_box"}
dec = {}
for v in r["verdicts"]:
    if v["subject"] in box and v["outcome"] == "decided":
        if v["quantity"] == "articulation_owner": dec[v["subject"]] = ("art", v["value"])
        if v["quantity"] == "dot_role" and v["value"] == "staccatissimo": dec[v["subject"]] = ("dot", v["detail"].get("owner"))
def bb(s): return box[s]["detail"]["bbox_page_px"]
tiles = []
# the four misses: (label, owner head subject)
for lab, head in (("miss_crop2_last_eighth", "glyph/24/1/2/3/0"), ("miss_crop3_second_eighth", "glyph/24/0/1/4/10"),
                  ("miss_crop3_third_eighth", "glyph/24/0/1/4/11"), ("miss_crop6_second_eighth_NOT_RESCUED", "glyph/24/0/1/5/8")):
    tiles.append({"kind": lab, "head": head, "mark": None})
# other newly read wedges: rescued glyphs with a decided owner, spread across the page, mixed class path
resc = [s for s, o in box.items() if o["reader"] == "yolo_rescue_wedge" and s in dec and dec[s][1] in box]
skip = {"glyph/24/1/2/3/24", "glyph/24/0/1/4/14", "glyph/24/0/1/4/15"}
resc = sorted(s for s in resc if s not in skip)
random.Random(2138).shuffle(resc)
above = [s for s in resc if "Above" in box[s]["value"][0]][:2]
below = [s for s in resc if "Below" in box[s]["value"][0]][:2]
for s in above + below:
    tiles.append({"kind": "new_wedge", "head": dec[s][1], "mark": s, "score": round(box[s]["score"], 3), "class": box[s]["value"][0], "path": dec[s][0]})
# controls: production-floor decided staccato, round (h/w near 1, equal ends), high detector score
S = json.load(open(SLIM))
sb = {o["subject"]: o for o in S["observations"] if o["quantity"] == "glyph_box"}
ms = {o["subject"]: o for o in S["observations"] if o["quantity"] == "mark_shape"}
cands = []
for v in S["verdicts"]:
    if v["quantity"] == "dot_role" and v["outcome"] == "decided" and v["value"] == "staccato" and v["subject"] in ms and v["subject"] in sb:
        m = ms[v["subject"]]; d = m["detail"]
        if sb[v["subject"]]["score"] >= 0.6 and 0.9 <= m["value"] <= 1.1 and abs(d["top"] - d["bot"]) <= 2 and v["detail"].get("owner") in sb:
            cands.append((v["subject"], v["detail"]["owner"]))
random.Random(7).shuffle(cands)
ca = [c for c in cands if "Above" in sb[c[0]]["value"][0]][:1]; cb = [c for c in cands if "Below" in sb[c[0]]["value"][0]][:1]
for s, h in ca + cb:
    tiles.append({"kind": "control_plain_staccato", "head": h, "mark": s, "class": sb[s]["value"][0], "_slim": True})
def head_box(t):
    src = sb if t.get("_slim") else box
    return src[t["head"]]["detail"]["bbox_page_px"]
random.Random(2138).shuffle(tiles)
font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 110)
Path(OUT).mkdir(parents=True, exist_ok=True)
pub = {"dpi": 600, "question": "Above or below the note in the red corners: is there a wedge (staccatissimo), a dot (staccato), or nothing?", "tiles": []}
key = {"note": "hidden key; Sean's tiles carry no key", "tiles": []}
for n, t in enumerate(tiles, 1):
    b = head_box(t); cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    x0, y0, x1, y1 = int(cx - 300), int(cy - 250), int(cx + 300), int(cy + 250)
    im = page.crop((x0, y0, x1, y1)).copy(); dr = ImageDraw.Draw(im)
    bx0, by0, bx1, by1 = b[0] - x0 - 10, b[1] - y0 - 10, b[2] - x0 + 10, b[3] - y0 + 10
    for (px, py, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        dr.line([(px, py), (px + dx * 22, py)], fill=(220, 0, 0), width=5); dr.line([(px, py), (px, py + dy * 22)], fill=(220, 0, 0), width=5)
    im = im.resize((900, int(im.height * 900 / im.width)), Image.LANCZOS)
    tile = Image.new("RGB", (900, 150 + im.height), (255, 255, 255))
    ImageDraw.Draw(tile).text((20, 12), f"Tile {n}", fill=(0, 0, 0), font=font); tile.paste(im, (0, 150))
    name = f"tile_{n:02d}.png"; tile.save(Path(OUT) / name)
    pub["tiles"].append({"tile": n, "file": name}); key["tiles"].append({"tile": n, **{k: v for k, v in t.items() if k != "_slim"}})
json.dump(pub, open(Path(OUT) / "manifest.json", "w"), indent=1); json.dump(key, open(KEY, "w"), indent=1)
print(len(tiles), "tiles")
