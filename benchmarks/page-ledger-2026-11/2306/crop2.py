"""2306 r11, MY look (leads): crop around glyphs; head box blue, the page stem the record filed (Q.PAGE_STEM stem_box) green, json-loaded.
Usage (cwd = tree): crop2.py REC.json PDF OUT.png glyph ..."""
import sys, os, json
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw
rec, pdf, outp, keys = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
R = json.load(open(rec))["record"]
ks = set(keys)
hb, sb = {}, {}
for o in R["observations"]:
    if o["subject"] in ks:
        if o["quantity"] == "glyph_box":
            hb[o["subject"]] = o["detail"]["bbox_page_px"]
        elif o["quantity"] == "page_stem":
            sb[o["subject"]] = (o["detail"].get("stem_box"), o["detail"].get("how"), o["detail"].get("direction"))
del R
pages, tiles = {}, []
for k in keys:
    p = int(k.split("/")[1])
    if p not in pages:
        pages[p] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    im = pages[p].copy()
    W, H = im.size
    dr = ImageDraw.Draw(im)
    b = hb[k]
    dr.rectangle([b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2], outline=(0, 0, 255), width=2)
    s = sb.get(k)
    if s and s[0]:
        dr.rectangle([s[0][0] - 2, s[0][1], s[0][2] + 2, s[0][3]], outline=(0, 170, 0), width=2)
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    x0, y0 = max(0, int(cx - 90)), max(0, int(cy - 130))
    t = im.crop((x0, y0, min(W, x0 + 180), min(H, y0 + 260))).resize((360, 520))
    ImageDraw.Draw(t).text((3, 3), "%s %s" % (k, s and s[1:]), fill=(255, 0, 0))
    tiles.append(t)
sheet = Image.new("RGB", (370 * len(tiles), 520), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, (i * 370, 0))
sheet.save(outp)
print(outp)
