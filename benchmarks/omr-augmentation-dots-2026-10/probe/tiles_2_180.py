"""ROADMAP 2.180 -- Sean's blind tiles, tiles AND key from ONE run, checked equal.
Each tile: the print around one note, ONE blue box on the NOTEHEAD, nothing else of ours. Key (glyph, kind, our OFF/ON value)
goes OUTSIDE the tiles folder. usage: tiles_2_180.py PICKS.json X1_BRA.json X1_LIT.json OUTROOT
PICKS = [{"plate": "bra", "note": "glyph/...", "kind": "changed|control_plain|control_dotted", "off": "...", "on": "..."}]"""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw

PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
SP = {"lit": 20.0, "bra": 32.0}
BLUE = (31, 111, 235)
picks, xb, xl, root = sys.argv[1:5]
P = json.load(open(picks))
X = {"bra": json.load(open(xb)), "lit": json.load(open(xl))}
tiles_dir = os.path.join(root, "tiles")
key_dir = os.path.join(root, "_key")
os.makedirs(tiles_dir, exist_ok=True)
os.makedirs(key_dir, exist_ok=True)
for f in os.listdir(tiles_dir):
    if f.endswith(".png"):
        os.remove(os.path.join(tiles_dir, f))
random.Random(2180).shuffle(P)
docs = {}
key = []
for i, p in enumerate(P, 1):
    plate = p["plate"]
    bb = X[plate][p["note"]]["bb"]
    page = int(p["note"].split("/")[1])
    sp = SP[plate]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    r = (cx - 7 * sp, cy - 5 * sp, cx + 7 * sp, cy + 5 * sp)
    doc = docs.setdefault(plate, fitz.open(PDF[plate]))
    z = 2.0
    pix = doc[page].get_pixmap(matrix=fitz.Matrix(600 / 72 * z / 2.5, 600 / 72 * z / 2.5),
                               clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    kx = im.width / (r[2] - r[0])
    ky = im.height / (r[3] - r[1])
    pad = 0.35 * sp
    ImageDraw.Draw(im).rectangle([(bb[0] - pad - r[0]) * kx, (bb[1] - pad - r[1]) * ky,
                                  (bb[2] + pad - r[0]) * kx, (bb[3] + pad - r[1]) * ky], outline=BLUE, width=3)
    name = "tile_%02d.png" % i
    im.save(os.path.join(tiles_dir, name))
    key.append(dict(tile=i, file=name, **p))
json.dump(key, open(os.path.join(key_dir, "key.json"), "w"), indent=1)
made = sorted(f for f in os.listdir(tiles_dir) if f.endswith(".png"))
assert made == sorted(k["file"] for k in key), (made, key)
print("tiles", len(made), "key rows", len(key), "EQUAL")
