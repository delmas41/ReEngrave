"""2306 r6, MY look only (leads, never findings): crop around glyphs; head box blue, page-named stem box (Q.PAGE_STEM stem_box) green.
Reads the record as text (no full load). Usage (cwd = tree): crop.py REC.json PDF OUTDIR glyph ..."""
import sys, os, re, json
sys.path.insert(0, os.getcwd())
from tools.omr.preprocessing import render_page
from PIL import Image, ImageDraw
rec, pdf, out, keys = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]
os.makedirs(out, exist_ok=True)
txt = open(rec, encoding="utf-8").read()
info = {}
for k in keys:
    m = re.search(r'"subject":"%s","quantity":"glyph_box".{0,800}?"bbox_page_px":\[([^\]]*)\]' % re.escape(k), txt)
    hb = [float(v) for v in m.group(1).split(",")] if m else None
    m2 = re.search(r'"subject":"%s","quantity":"page_stem".{0,1500}?"direction":"?([a-z]*)"?.{0,600}?"stem_box":\[([^\]]*)\]' % re.escape(k), txt)
    sb = [float(v) for v in m2.group(2).split(",")] if m2 else None
    info[k] = (hb, sb, m2 and m2.group(1))
del txt
pages = {}
for k, (hb, sb, d) in info.items():
    print(k, "head", hb, "page stem", sb, d)
    if hb is None:
        continue
    p = int(k.split("/")[1])
    if p not in pages:
        pages[p] = Image.fromarray(render_page(pdf, p, dpi=600).rgb).convert("RGB")
    im = pages[p].copy()
    dr = ImageDraw.Draw(im)
    dr.rectangle(hb[:4], outline="blue", width=2)
    if sb:
        dr.rectangle(sb[:4], outline="green", width=2)
    cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
    im.crop((int(cx - 260), int(cy - 300), int(cx + 260), int(cy + 300))).save(os.path.join(out, k.replace("/", "_") + ".png"))
