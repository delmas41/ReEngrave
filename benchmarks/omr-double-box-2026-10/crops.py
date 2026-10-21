"""2.185 rule-7 crops, for MY OWN check (not sent to Sean). One neutral dark-green box = union of the cluster's boxes; nothing else drawn.
usage: crops.py PLATE CENSUS.json SEED N OUTDIR NAME [--filter KEY=VAL ...]
  writes OUTDIR/NAME_tile_XX.png (one per cluster), OUTDIR/NAME_sheet.png (contact sheet, numbered), OUTDIR/key/NAME_key.json (classes, sources, fates)."""
import json, os, random, sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw, ImageFont
from tools.omr.preprocessing import render_page
plate, cj, seed, n, outdir, name = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6]
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
U = 15.75 if plate == "litolff" else 32.0
cl = json.load(open(cj))["clusters"]
flt = dict(a.split("=", 1) for a in sys.argv[7:] if "=" in a)
def passes(c):
    ms = c["members"]
    if "fam" in flt and flt["fam"] not in {m["fam"] for m in ms}: return False
    if "cls" in flt and flt["cls"] not in {m["cls"] for m in ms}: return False
    if "src" in flt and flt["src"] not in {m["src"] for m in ms}: return False
    if "fate" in flt and flt["fate"] not in {m["fate"] for m in ms}: return False
    if "kind" in flt and flt["kind"] == "same_cell" and c["cells"] != 1: return False
    if "kind" in flt and flt["kind"] == "cross_staff" and c["staffs"] == 1: return False
    return True
pool = [c for c in cl if passes(c)]
pool.sort(key=lambda c: c["members"][0]["subject"])
rnd = random.Random(seed)
pick = rnd.sample(pool, min(n, len(pool)))
os.makedirs(os.path.join(outdir, "key"), exist_ok=True)
tiles, key, cache = [], [], {}
for k, c in enumerate(pick, 1):
    ms = c["members"]
    bb = [min(m["bbox"][0] for m in ms) - 3, min(m["bbox"][1] for m in ms) - 3, max(m["bbox"][2] for m in ms) + 3, max(m["bbox"][3] for m in ms) + 3]
    pg = int(ms[0]["subject"].split("/")[1])
    if (plate, pg) not in cache:
        cache.clear(); cache[(plate, pg)] = Image.fromarray(render_page(PDFS[plate], pg, dpi=600).rgb).convert("RGB")
    im = cache[(plate, pg)]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    hw = max(5 * U, (bb[2] - bb[0]) / 2 + 2 * U); hh = max(3.5 * U, (bb[3] - bb[1]) / 2 + 1.5 * U)
    x0, y0, x1, y1 = int(cx - hw), int(cy - hh), int(cx + hw), int(cy + hh)
    crop = im.crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(crop).rectangle([bb[0] - x0, bb[1] - y0, bb[2] - x0, bb[3] - y0], outline=(0, 120, 40), width=2)
    crop.save(os.path.join(outdir, "%s_tile_%02d.png" % (name, k)))
    tiles.append(crop)
    key.append(dict(tile=k, plate=plate, page=pg, members=[{kk: m[kk] for kk in ("subject", "cls", "score", "src", "fate", "why", "bbox")} for m in ms]))
json.dump(key, open(os.path.join(outdir, "key", name + "_key.json"), "w"), indent=1)
TW = 420
cols = 2; rows = (len(tiles) + cols - 1) // cols
th = [int(t.size[1] * TW / t.size[0]) for t in tiles]
RH = max(th) + 4 if th else 0
sheet = Image.new("RGB", (cols * (TW + 8), rows * (RH + 22)), (255, 255, 255))
d = ImageDraw.Draw(sheet)
for k, t in enumerate(tiles):
    r_, c_ = divmod(k, cols)
    x, y = c_ * (TW + 8), r_ * (RH + 22)
    d.text((x + 2, y + 2), str(k + 1), fill=(200, 0, 0))
    sheet.paste(t.resize((TW, th[k])), (x, y + 16))
sheet.save(os.path.join(outdir, name + "_sheet.png"))
print(name, "pool", len(pool), "picked", len(pick))
