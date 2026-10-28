"""usage: crop_pitch.py WORKDIR PLATE OUT.png RG [RG ...]  -- wide crops (clef + key at the system's left, note with ONE orange box)
from the OFF symbols file; the left edge is the first cell of the note's staff (cell box in the OFF gathered record)."""
import json, sys
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
work, plate, out, rgs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
hosts = {h["rg"]: h for h in json.load(open(f"{work}/{plate}.off.symbols.json"))["hosts"] if h.get("kind") == "note"}
obs = json.load(open(f"{work}/{plate}.off.gathered.record.json"))["record"]["observations"]
boxes = {o["subject"]: o["value"] for o in obs if o["quantity"] == "cell_box"}
cache, tiles = {}, []
for rg in rgs:
    h = hosts[rg]; pg = h["page"]
    if pg not in cache:
        cache[pg] = Image.fromarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    x0, y0, x1, y1 = h["box"]; cx = (x0 + x1) / 2
    _, p, s, st = rg.split("/")[:4]
    cells = [b for k, b in boxes.items() if k.startswith(f"cell/{p}/{s}/{st}/")]
    left = min(b[0] for b in cells); top = min(b[1] for b in cells); bot = max(b[3] for b in cells)
    box = (int(left - 15), int(top - 30), int(cx + 220), int(bot + 30))
    c = cache[pg].crop(box)
    ImageDraw.Draw(c).rectangle((x0 - box[0], y0 - box[1], x1 - box[0], y1 - box[1]), outline=(255, 140, 0), width=3)
    tiles.append(c)
W = max(t.width for t in tiles); H = sum(t.height + 30 for t in tiles)
sheet = Image.new("RGB", (W, H), "white"); y = 0
for i, t in enumerate(tiles):
    ImageDraw.Draw(sheet).text((4, y + 8), str(i + 1), fill=(200, 0, 0)); sheet.paste(t, (0, y + 30)); y += t.height + 30
sheet.save(out); print(sheet.size)
