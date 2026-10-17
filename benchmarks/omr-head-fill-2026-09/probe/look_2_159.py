"""ROADMAP 2.159 -- a look crop (for us, not a tile): page raster around a head, the detector box (red) and the located box
(green), x4. usage: look_2_159.py DOC SUBJECT OUT.png [OUTDIR]"""
import json
import os
import sys

sys.path.insert(0, ".")
import fitz  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

PDFS = {
    "litolff": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
               "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
              "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}
DOC, S, PNG = sys.argv[1:4]
OUT = sys.argv[4] if len(sys.argv) > 4 else "out/2.159"
H = json.load(open(os.path.join(OUT, "heads_%s.json" % DOC)))
L = json.load(open(os.path.join(OUT, "located_%s.json" % DOC)))
bb = H[S]["glyph_box"]["detail"]["bbox_page_px"]
sp = L[S]["sp_page"] if S in L else (bb[3] - bb[1])
pad = 3 * sp
r = (bb[0] - pad, bb[1] - pad, bb[2] + pad, bb[3] + pad)
k = 72 / 600
pix = fitz.open(PDFS[DOC])[int(S.split("/")[1])].get_pixmap(matrix=fitz.Matrix(600 / 72, 600 / 72),
                                                            clip=fitz.Rect(*[v * k for v in r]))
im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
Z = 4
im = im.resize((im.width * Z, im.height * Z), Image.NEAREST)
d = ImageDraw.Draw(im)
d.rectangle([(bb[0] - r[0]) * Z, (bb[1] - r[1]) * Z, (bb[2] - r[0]) * Z, (bb[3] - r[1]) * Z], outline=(220, 0, 0), width=2)
if S in L:
    x, y, w, h = L[S]["box_page"]
    d.rectangle([(x - r[0]) * Z, (y - r[1]) * Z, (x + w - r[0]) * Z, (y + h - r[1]) * Z], outline=(0, 160, 0), width=2)
im.save(PNG)
print(PNG, im.size)
