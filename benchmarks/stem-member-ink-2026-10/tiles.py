"""2.210: the 12 blind tiles. 8 boxes the ownership layer (2.205) refuses as a tremolo slash (Sean has named two of them), the "ff" box of Litolff p4,
the real note of Brahms p12 that the flag turns red, and 2 controls (real heads on a multi-head stem, seed 2210). ONE orange box, nothing of ours drawn,
a crop 16 x 10 staff spaces so the whole stem shows. MEMBERS=pickle {plate: [rows]} from the replay (see FINDINGS), writes out/print/2.210/."""
import json, os, pickle, pathlib, random, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from PIL import Image, ImageDraw
from tools.omr.staged import lane_report as LR
from tools.omr.preprocessing import render_page
out = pathlib.Path("out/print/2.210"); (out / "tiles").mkdir(parents=True, exist_ok=True)
M = pickle.load(open(os.environ["MEMBERS"], "rb")); BV = pickle.load(open(os.environ["BV"], "rb"))
full = {"lit": "litolff", "bra": "brahms"}
by = {(p, r["key"]): r for p in M for r in M[p]}
items = []
def add(p, k, role, what):
    r = by[(p, k)]
    items.append(dict(plate=full[p], page=int(k.split("/")[1]), box=r["bb"], rg=k, role=role, what=what))
for p in M:
    for r in M[p]:
        x = BV[p].get(r["key"])
        if x and any(str(l[3]).startswith("tremolo") for l in x[1]):
            add(p, r["key"], "case", "ownership refuses as a tremolo slash")
add("lit", "glyph/4/1/1/4/17", "case", "ff, joins a stem")
add("bra", "glyph/12/0/10/5/2", "case", "real note the flag turns unwritten")
rng = random.Random(2210)
pool = sorted((p, r["key"]) for p in M for r in M[p] if r["n"] >= 2 and any(s["own"] == "owned" for s in r["strokes"]) and r["src"] is None)
for p, k in rng.sample(pool, 2):
    add(p, k, "control", "ordinary head on a multi-head stem")
rng.shuffle(items)
tiles, key, cache = [], [], {}
W = 520
for n, it in enumerate(items, 1):
    pk = (it["plate"], it["page"])
    if pk not in cache:
        cache.clear(); cache[pk] = Image.fromarray(render_page(str(LR.LIB / LR.PLATES[it["plate"]]["pdf"]), it["page"], dpi=600).rgb).convert("RGB")
    im = cache[pk]; u = LR.PLATES[it["plate"]]["unit"]; bb = [it["box"][0] - 4, it["box"][1] - 4, it["box"][2] + 4, it["box"][3] + 4]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    x0, y0, x1, y1 = max(0, int(cx - 5 * u)), max(0, int(cy - 8 * u)), int(cx + 5 * u), int(cy + 8 * u)
    c = im.crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(c).rectangle([round(bb[0] - x0), round(bb[1] - y0), round(bb[2] - x0), round(bb[3] - y0)], outline=LR.ORANGE, width=max(2, int(u / 8)))
    c = c.resize((W, int(W * c.height / c.width))); c.save(out / "tiles" / ("tile_%02d.png" % n)); tiles.append(c)
    key.append(dict(it, tile=n))
cols = 4; rows = (len(tiles) + cols - 1) // cols; h = max(t.height for t in tiles)
sheet = Image.new("RGB", (cols * (W + 8) + 8, rows * (h + 30) + 8), "white"); d = ImageDraw.Draw(sheet)
for n, t in enumerate(tiles):
    x, y = 8 + (n % cols) * (W + 8), 8 + (n // cols) * (h + 30); d.text((x, y + 2), str(n + 1), fill=(0, 0, 0)); sheet.paste(t, (x, y + 18))
sheet.save(out / "tiles" / "sheet.png")
(out / "tiles" / "README.md").write_text("Each picture is a piece of a scanned score page with ONE orange box and nothing else drawn. The box only says where "
    "to look. Question, for every tile: what does the print show at the orange box (a note, a slash across a stem, a letter, a clef, a beam...)? "
    "Answer by tile number.\n")
(out / "key.json").write_text(json.dumps(key, indent=1, default=str)); print(len(key))
