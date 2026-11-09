"""2.275 pattern tiles for Sean: heads NOT in the file, seeded-random, proportional to bucket size (largest remainder), per plate.
Wide crop of ONE staff around the head (neighbours, stems, beams, barlines visible), a thin box on the head, NO text or label on the image.
The bucket lives in key.json only.

usage: tiles.py INK.json PART.rows.jsonl PLATE N SEED OUTDIR KEY_PART.json [START]
"""
import json
import os
import random
import sys

import fitz
from PIL import Image, ImageDraw

INK, ROWS, PLATE, N, SEED, OUT, KEYP = sys.argv[1:8]
N, SEED = int(N), int(SEED)
START = int(sys.argv[8]) if len(sys.argv) > 8 else 1
PDFS = {"litolff": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/"
                    "beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/"
                   "brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
PDF, SP = PDFS[PLATE]
doc = fitz.open(PDF)
BLUE = (31, 111, 235)
ink = json.load(open(INK))
rows = {r["sub"]: r for r in (json.loads(l) for l in open(ROWS))}
mem = {b: sorted(v) for b, v in ink["members"].items()}
tot = sum(len(v) for v in mem.values())
quota = {b: N * len(v) / tot for b, v in mem.items()}
take = {b: int(q) for b, q in quota.items()}
for b in sorted(quota, key=lambda b: -(quota[b] - take[b]))[: N - sum(take.values())]:
    take[b] += 1
rng = random.Random(SEED)
pick = []
for b in sorted(mem):
    pick += [(s, b) for s in rng.sample(mem[b], take[b])]
rng.shuffle(pick)
os.makedirs(OUT, exist_ok=True)
key = {}
HALF_W, HALF_H = 14.0, 4.5     # staff spaces either side of the head's centre
Z = 1300 / (2 * HALF_W * SP)   # output about 1300 px wide
for i, (s, b) in enumerate(pick):
    n = START + i
    bb = rows[s]["bbox"]
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    r = (cx - HALF_W * SP, cy - HALF_H * SP, cx + HALF_W * SP, cy + HALF_H * SP)
    k = 72 / 600
    pix = doc[int(s.split("/")[1])].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z),
                                               clip=fitz.Rect(*[v * k for v in r]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (r[2] - r[0]), im.height / (r[3] - r[1])
    pad = 0.15 * SP
    box = [(bb[0] - pad - r[0]) * sx, (bb[1] - pad - r[1]) * sy, (bb[2] + pad - r[0]) * sx, (bb[3] + pad - r[1]) * sy]
    ImageDraw.Draw(im).rectangle(box, outline=BLUE, width=2)
    fn = "tile_%02d.png" % n
    im.save(os.path.join(OUT, fn))
    p = s.split("/")
    key[str(n)] = dict(file=fn, plate=PLATE, page=int(p[1]), system=int(p[2]), staff=int(p[3]), cell=int(p[4]),
                       subject=s, bucket=b, page_box=bb, box_tile_px=[round(v, 1) for v in box],
                       class_=rows[s]["cls"])
json.dump(key, open(KEYP, "w"), indent=1)
print(PLATE, "picked", {b: take[b] for b in take if take[b]})
