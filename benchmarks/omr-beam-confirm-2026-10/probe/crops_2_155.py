"""ROADMAP 2.155 -- PROBE: diagnostic crops (ours, not Sean's) of the three 2.153 tiles 4/14/16. Raw page raster around the cell,
cell box (green), head box (blue), CV stems of the cell (red), beam strokes (orange). Canonical -> page by the head box's own scale.
usage: crops_2_155.py SLICE.json OUTDIR"""
import json
import sys

sys.path.insert(0, ".")
from PIL import Image, ImageDraw  # noqa: E402

from tools.omr.preprocessing import render_page  # noqa: E402

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
       "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf")
SL, OUT = sys.argv[1:3]
G = ["glyph/2/1/7/12/2", "glyph/1/0/8/2/0", "glyph/10/1/6/3/2"]
r = json.load(open(SL))
obs = r["observations"]
for n, g in zip((4, 14, 16), G):
    cell = "cell/" + "/".join(g.split("/")[1:5])
    cb = next(o["value"] for o in obs if o["subject"] == cell and o["quantity"] == "cell_box")
    gb = next(o for o in obs if o["subject"] == g and o["quantity"] == "glyph_box")
    can = gb["value"][1:]
    pg = gb["detail"]["bbox_page_px"]
    s = (pg[2] - pg[0]) / can[2]
    ox, oy = pg[0] - can[0] * s, pg[1] - can[1] * s
    page = render_page(PDF, int(g.split("/")[1]), dpi=600)
    img = Image.fromarray(page.binary).convert("RGB")
    x0, y0, x1, y1 = cb
    m = 60
    box = (int(x0 - m), int(y0 - m), int(x1 + m), int(y1 + m))
    d = ImageDraw.Draw(img)
    d.rectangle(cb, outline=(0, 160, 0))
    d.rectangle(pg, outline=(31, 111, 235))
    for o in obs:
        if o["subject"] == cell and o["quantity"] in ("stem", "beam_stroke"):
            x, y, w, h = o["value"]
            col = (220, 0, 0) if o["quantity"] == "stem" else (255, 140, 0)
            d.rectangle((ox + x * s, oy + y * s, ox + (x + w) * s, oy + (y + h) * s), outline=col)
    c = img.crop(box)
    c = c.resize((c.width * 4, c.height * 4), Image.NEAREST)
    c.save("%s/diag_tile%02d.png" % (OUT, n))
    raw = Image.fromarray(page.binary).crop(box)
    raw.resize((raw.width * 4, raw.height * 4), Image.NEAREST).save("%s/raw_tile%02d.png" % (OUT, n))
    print(n, g, "scale", round(s, 3), "cell", cb, "head", [round(v, 1) for v in pg])
