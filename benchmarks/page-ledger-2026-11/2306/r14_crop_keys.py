"""2.306 r14, MY look: crops around glyph keys of a record (head box blue), 4 per row, labelled. Pages rendered at 600 dpi.
Usage: r14_crop_keys.py REC.json PLATE OUT.png key,key,..."""
import sys

from PIL import Image, ImageDraw

from tools.omr.preprocessing import render_page
from tools.omr.staged.record_io import load_record

PDF = {"litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
rec_p, plate, out_p, keys = sys.argv[1:5]
keys = keys.split(",")
rec = load_record(rec_p)["record"]
box = {o["subject"]: (o.get("detail") or {}).get("bbox_page_px") for o in rec["observations"] if o["quantity"] == "glyph_box" and o["subject"] in keys}
del rec
pages = {}
tiles = []
for k in keys:
    p = int(k.split("/")[1])
    if p not in pages:
        pages[p] = Image.fromarray(render_page(PDF[plate], p, dpi=600).rgb).convert("RGB")
    b = box.get(k)
    if not b:
        continue
    im = pages[p].copy()
    sp = (b[3] - b[1]) / 1.1
    ImageDraw.Draw(im).rectangle([b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3], outline=(0, 0, 255), width=3)
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    c = im.crop((int(cx - 6 * sp), int(cy - 6 * sp), int(cx + 6 * sp), int(cy + 6 * sp))).resize((300, 300))
    ImageDraw.Draw(c).text((3, 3), k, fill=(220, 0, 0))
    tiles.append(c)
cols = 4
out = Image.new("RGB", (300 * cols, 300 * ((len(tiles) + cols - 1) // cols)), "white")
for i, c in enumerate(tiles):
    out.paste(c, ((i % cols) * 300, (i // cols) * 300))
out.save(out_p)
print(len(tiles))
