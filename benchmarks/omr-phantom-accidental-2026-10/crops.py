"""2.192 rule-7 crops for MY OWN check (not Sean's). usage: crops.py PLATE ROWS.json CLASS GROUP SEED N OUT.png
CLASS NOT-DS = every class but double sharp. GROUP = touch (iou>=.3) | onrest (iou>=.5 with a rest box) | norest (no rest box within iou .1). Draws one neutral dark-green box on the ACCIDENTAL box; nothing else."""
import json, random, sys
sys.path.insert(0, ".")
from PIL import Image, ImageDraw
from tools.omr.preprocessing import render_page
plate, rj, cls, grp, seed, n, out = sys.argv[1:8]; seed = int(seed); n = int(n)
PDFS = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
U = 15.75 if plate == "litolff" else 32.0
rows = [r for r in json.load(open(rj)) if (r["cls"] == cls or (cls == "NOT-DS" and r["cls"] != "accidentalDoubleSharp")) and ((grp == "onrest" and r["iou"] >= .5) or (grp == "touch" and r["iou"] >= .3) or (grp == "norest" and r["iou"] < .1))]
rows.sort(key=lambda r: r["acc"]); pick = random.Random(seed).sample(rows, min(n, len(rows)))
pick.sort(key=lambda r: int(r["acc"].split("/")[1]))
tiles = []; cache = {}
for k, r in enumerate(pick, 1):
    pg = int(r["acc"].split("/")[1]); bb = r["bbox"]
    if pg not in cache: cache.clear(); cache[pg] = Image.fromarray(render_page(PDFS[plate], pg, dpi=600).rgb).convert("RGB")
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    x0, y0, x1, y1 = int(cx - 5 * U), int(cy - 3.2 * U), int(cx + 5 * U), int(cy + 3.2 * U)
    c = cache[pg].crop((x0, y0, x1, y1)).copy()
    ImageDraw.Draw(c).rectangle([bb[0] - x0, bb[1] - y0, bb[2] - x0, bb[3] - y0], outline=(0, 120, 40), width=2)
    tiles.append((c, r))
TW = 420; cols = 2; rr = (len(tiles) + 1) // 2
th = [int(t.size[1] * TW / t.size[0]) for t, _ in tiles]; RH = max(th) + 4
sheet = Image.new("RGB", (cols * (TW + 8), rr * (RH + 18)), (255, 255, 255)); d = ImageDraw.Draw(sheet)
for k, (t, r) in enumerate(tiles):
    y_, x_ = divmod(k, cols); X, Y = x_ * (TW + 8), y_ * (RH + 18)
    d.text((X + 2, Y + 2), "%d  p%s  sc %.2f" % (k + 1, r["acc"].split("/")[1], r["score"]), fill=(200, 0, 0)); sheet.paste(t.resize((TW, th[k])), (X, Y + 14))
sheet.save(out); print(len(rows), "pool;", len(pick), "picked ->", out)
