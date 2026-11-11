"""Numbered montage `sheet.png` of the blind tiles, and the key's 'ours' column.   python3 make_sheet.py TILES_DIR KEY.json CLS.json
Numbers are drawn in a white strip ABOVE each tile (never on the print); nothing of ours is drawn."""
import json
import sys

from PIL import Image, ImageDraw

tiles, keyp, clsp = sys.argv[1:4]
key = json.load(open(keyp))
cls = json.load(open(clsp))
ours = {}
for kind in ("keys", "clefs"):
    for r in cls[kind]:
        ours.setdefault((r["plate"], r["staff"]), {})
        if kind == "keys":
            ours[(r["plate"], r["staff"])].update(key_fill_fifths=r["fill"], key_cause=r["cause"][:2])
        else:
            ours[(r["plate"], r["staff"])].update(clef_fill=r["value"])
for n, k in key.items():
    k["ours"] = ours.get((k["plate"], k["staff"]), {})
json.dump(key, open(keyp, "w"), indent=1)
ims = []
for n in sorted(key, key=int):
    im = Image.open("%s/%s" % (tiles, key[n]["file"])).convert("RGB")
    W = 600
    im = im.resize((W, int(im.height * W / im.width)))
    strip = Image.new("RGB", (W, 34), (255, 255, 255))
    ImageDraw.Draw(strip).text((8, 8), "TILE %s" % n, fill=(0, 0, 0))
    both = Image.new("RGB", (W, strip.height + im.height), (255, 255, 255))
    both.paste(strip, (0, 0))
    both.paste(im, (0, strip.height))
    ims.append(both)
cols = 3
w = max(i.width for i in ims)
h = max(i.height for i in ims)
rows = (len(ims) + cols - 1) // cols
sheet = Image.new("RGB", (cols * (w + 10), rows * (h + 10)), (255, 255, 255))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * (w + 10), (i // cols) * (h + 10)))
sheet.save("%s/sheet.png" % tiles)
print("sheet", sheet.size)
