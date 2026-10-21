"""2.180 probe 4: contact sheet of dot crops for MY look (blue box = the dot box; red box = the head the role names, if any).
usage: x4_sheet.py PLATE X1.json FATES.json OUT.png FATE[,FATE] N SEED [WHY]
PLATE lit|bra; FATE matches row["fate"] (prefix ok); WHY filters row["why"]. Writes OUT.png and OUT.json (tile -> row)."""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw, ImageFont

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SP = {"lit": 20.0, "bra": 32.0}
plate, x1, fates, out, fsel, n, seed = sys.argv[1:8]
why = sys.argv[8] if len(sys.argv) > 8 else None
G = json.load(open(x1))
F = json.load(open(fates))
sel = [f for f in F if any(f["fate"].startswith(s) for s in fsel.split(",")) and (why is None or f.get("why") == why)
       and (not os.environ.get("KEY") or f.get("key", "").startswith(os.environ["KEY"]))]
random.Random(int(seed)).shuffle(sel)
sel = sel[:int(n)]
doc = fitz.open(PDF[plate])
fnt = ImageFont.load_default()
TW, TH = 300, 210
cols = 6
rows = (len(sel) + cols - 1) // cols
sheet = Image.new("RGB", (cols * TW, rows * TH), "white")
meta = []
for i, f in enumerate(sel):
    bb = f["bb"]
    page = int(f["dot"].split("/")[1])
    sp = SP[plate]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    r = (cx - 4.0 * sp, cy - 2.8 * sp, cx + 3.0 * sp, cy + 2.8 * sp)
    pix = doc[page].get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).resize((TW, TH - 14))
    k = TW / (r[2] - r[0])
    ky = (TH - 14) / (r[3] - r[1])
    d = ImageDraw.Draw(im)
    d.rectangle([(bb[0] - r[0]) * k - 2, (bb[1] - r[1]) * ky - 2, (bb[2] - r[0]) * k + 2, (bb[3] - r[1]) * ky + 2], outline=(31, 111, 235), width=2)
    hk = f.get("head") or f.get("owner") or f.get("near")
    hk = "/".join(hk.split("/")[:6]) if isinstance(hk, str) else None
    if hk and G.get(hk, {}).get("bb"):
        hb = G[hk]["bb"]
        d.rectangle([(hb[0] - r[0]) * k, (hb[1] - r[1]) * ky, (hb[2] - r[0]) * k, (hb[3] - r[1]) * ky], outline=(220, 30, 30), width=1)
    t = Image.new("RGB", (TW, TH), "white")
    t.paste(im, (0, 14))
    ImageDraw.Draw(t).text((2, 1), "%d %s %s" % (i, f["fate"][:22], (f.get("why") or "")[:18]), fill=(0, 0, 0), font=fnt)
    sheet.paste(t, ((i % cols) * TW, (i // cols) * TH))
    ImageDraw.Draw(sheet).rectangle([(i % cols) * TW, (i // cols) * TH, (i % cols + 1) * TW - 1, (i // cols + 1) * TH - 1], outline=(180, 180, 180))
    meta.append(dict(tile=i, **f))
sheet.save(out)
json.dump(meta, open(out[:-4] + ".json", "w"), default=str)
print(out, len(sel), "of", sum(1 for f in F if any(f["fate"].startswith(s) for s in fsel.split(","))))
