"""2.278 blind tiles: "What is the written value of the boxed note?" One staff, a thin blue box over the head AND its stem and
tip (head + 4.8 staff spaces along the stem), nothing else drawn. The bucket lives in key.json only.
usage: tiles.py PICKS.json OUTDIR   (PICKS = [{plate, sub, bbox, stem_dir, bucket, reason}...], in tile order)"""
import json, os, sys
import fitz
from PIL import Image, ImageDraw

PICKS, OUT = sys.argv[1:3]
PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
docs = {}
BLUE = (31, 111, 235)
picks = json.load(open(PICKS))
os.makedirs(OUT, exist_ok=True)
key = {}
HW, HH = 12.0, 7.5
for n, p in enumerate(picks, 1):
    pdf, SP = PDFS[p["plate"]]
    doc = docs.setdefault(p["plate"], fitz.open(pdf))
    bb = p["bbox"]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    r = (cx - HW * SP, cy - HH * SP, cx + HW * SP, cy + HH * SP)
    Z = 1300 / (2 * HW * SP)
    k = 72 / 600
    pg = int(p["sub"].split("/")[1])
    pix = doc[pg].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (r[2] - r[0]), im.height / (r[3] - r[1])
    x0, x1 = bb[0] - 0.3 * SP, bb[2] + 0.3 * SP
    y0, y1 = bb[1] - 0.1 * SP, bb[3] + 0.1 * SP
    sd = p.get("stem_dir")
    if sd == "up":
        y0 = bb[1] - 4.8 * SP
    elif sd == "down":
        y1 = bb[3] + 4.8 * SP
    box = [(x0 - r[0]) * sx, (y0 - r[1]) * sy, (x1 - r[0]) * sx, (y1 - r[1]) * sy]
    ImageDraw.Draw(im).rectangle(box, outline=BLUE, width=2)
    fn = "tile_%02d.png" % n
    im.save(os.path.join(OUT, fn))
    key[str(n)] = dict(file=fn, **{k2: v for k2, v in p.items()}, box_tile_px=[round(v, 1) for v in box])
json.dump(key, open(os.path.join(OUT, "key.json"), "w"), indent=1)
print(len(picks), "tiles ->", OUT)
