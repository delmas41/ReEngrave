"""ROADMAP 2.190 cause step: a numbered, nothing-drawn sheet of merged accidental inks (random, seed), tight crops at 600 dpi, enlarged.
usage: cropsheet_2_190.py PAIRS.json OUT_DIR SEED N_LITOLFF N_BRAHMS  -> OUT_DIR/sheet_<plate>.png, OUT_DIR/key.json (the detector's winner/rivals)"""
import json, random, sys, pathlib
from PIL import Image, ImageDraw
from tools.omr.staged.lane_report import LIB, PLATES
from tools.omr.preprocessing import render_page
pairs = json.load(open(sys.argv[1])); out = pathlib.Path(sys.argv[2]); seed = int(sys.argv[3]); ns = dict(litolff=int(sys.argv[4]), brahms=int(sys.argv[5]))
out.mkdir(parents=True, exist_ok=True)
rng = random.Random(seed); key = []
for plate in ("litolff", "brahms"):
    items = [p for p in pairs[plate] if p["bbox"]]
    pick = rng.sample(items, min(ns[plate], len(items)))
    u = PLATES[plate]["unit"]; tiles = []; cache = {}
    for n, it in enumerate(pick, 1):
        pg = int(it["subject"].split("/")[1])
        if pg not in cache:
            cache.clear(); cache[pg] = Image.fromarray(render_page(str(LIB / PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
        x0, y0, x1, y1 = it["bbox"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        crop = cache[pg].crop((int(cx - 2.2 * u), int(cy - 2.6 * u), int(cx + 2.2 * u), int(cy + 2.6 * u)))
        crop = crop.resize((crop.width * 100 // int(u) * 2 // 1, crop.height * 100 // int(u) * 2 // 1)) if False else crop.resize((int(crop.width * 6), int(crop.height * 6)), Image.LANCZOS)
        tiles.append(crop); key.append(dict(plate=plate, n=n, **{k: it[k] for k in ("winner", "wconf", "rivals", "margin", "subject", "bbox")}))
    W, H = max(t.width for t in tiles), max(t.height for t in tiles); cols = 5; rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (cols * (W + 10), rows * (H + 24)), "white"); d = ImageDraw.Draw(sh)
    for i, t in enumerate(tiles):
        x, y = (i % cols) * (W + 10), (i // cols) * (H + 24); d.text((x + 4, y + 4), str(i + 1), fill=(200, 0, 0)); sh.paste(t, (x, y + 20))
    sh.save(out / ("sheet_%s.png" % plate))
json.dump(key, open(out / "key.json", "w"), indent=1)
