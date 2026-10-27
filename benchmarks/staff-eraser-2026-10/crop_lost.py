"""usage: crop_lost.py WORKDIR PLATE OUT.png RG [RG ...]  -- page crops (orange box) of notes OFF-present, from the OFF symbols file."""
import json, sys
from PIL import Image, ImageDraw
sys.path.insert(0, ".")
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
work, plate, out, rgs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
hosts = {h["rg"]: h for h in json.load(open(f"{work}/{plate}.off.symbols.json"))["hosts"] if h.get("kind") == "note"}
cache, tiles = {}, []
for rg in rgs:
    h = hosts[rg]; pg = h["page"]
    if pg not in cache:
        cache[pg] = Image.fromarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), pg, dpi=600).rgb).convert("RGB")
    x0, y0, x1, y1 = h["box"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = 170
    c = cache[pg].crop((int(cx - r), int(cy - r), int(cx + r), int(cy + r)))
    ImageDraw.Draw(c).rectangle((x0 - cx + r, y0 - cy + r, x1 - cx + r, y1 - cy + r), outline=(255, 140, 0), width=3)
    ImageDraw.Draw(c).text((4, 4), rg, fill=(200, 0, 0))
    tiles.append(c)
cols = 4; rows = (len(tiles) + cols - 1) // cols
sheet = Image.new("RGB", (cols * 340, rows * 340), "white")
for i, t in enumerate(tiles): sheet.paste(t, ((i % cols) * 340, (i // cols) * 340))
sheet.save(out)
