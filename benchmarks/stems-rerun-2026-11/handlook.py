"""2.280 r3: my look at where Sean's p0 hand stems and our stem rows disagree. Draws (for ME, not for Sean) our head box in blue and every hand
stem box in green. usage: handlook.py HEADS.jsonl OUT.png KIND   KIND = hand_only (hand stem, ours no row) | ours_only (ours row, hand no stem)"""
import json
import random
import sys

import fitz
from PIL import Image, ImageDraw

sys.argv += []
heads, out, kind = sys.argv[1:4]
SP = 27.3
hand = json.load(open("data/hand-truth/pages/imslp317803/0.json"))
HB = [b for b in hand["boxes"] if str(b["cls"]).startswith("notehead")]
HS = [b["rect"] for b in hand["boxes"] if b["cls"] == "stem"]
rows = [json.loads(l) for l in open(heads)]
COPY = ("owned_by_another_staff", "mark_group_duplicate")


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u else 0


sel = []
for r in rows:
    if r["page"] != 0 or not r["kept"] or r["fate"] in COPY or not r["page_box"]:
        continue
    hb = max(HB, key=lambda b: iou(b["rect"], r["page_box"]))
    if iou(hb["rect"], r["page_box"]) < 0.4:
        continue
    h = hb["rect"]
    tol = 0.35 * (h[3] - h[1])
    has = any(max(0.0, s[0] - h[2], h[0] - s[2]) <= tol and max(0.0, s[1] - h[3], h[1] - s[3]) <= tol for s in HS)
    if kind == "hand_only" and has and r["n_stem"] == 0:
        sel.append(r)
    if kind == "ours_only" and not has and r["n_stem"] > 0:
        sel.append(r)
random.Random(7).shuffle(sel)
sel = sel[:15]
doc = fitz.open("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf")
ims = []
for r in sel:
    x0, y0, x1, y1 = r["page_box"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    clip = (cx - 7 * SP, cy - 8 * SP, cx + 7 * SP, cy + 8 * SP)
    Z = 330 / (14 * SP)
    pix = doc[0].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
    d = ImageDraw.Draw(im)
    for s in HS:
        if s[2] > clip[0] and s[0] < clip[2] and s[3] > clip[1] and s[1] < clip[3]:
            d.rectangle([(s[0] - clip[0]) * sx, (s[1] - clip[1]) * sy, (s[2] - clip[0]) * sx, (s[3] - clip[1]) * sy], outline=(0, 170, 0), width=1)
    d.rectangle([(x0 - clip[0]) * sx, (y0 - clip[1]) * sy, (x1 - clip[0]) * sx, (y1 - clip[1]) * sy], outline=(31, 111, 235), width=1)
    d.text((3, 3), r["sub"].replace("glyph/", "") + " " + r["fate"][:16], fill=(200, 0, 0))
    ims.append(im)
w, h = ims[0].size
cols = 5
sheet = Image.new("RGB", (cols * w, ((len(ims) + cols - 1) // cols) * h), (255, 255, 255))
for i, im in enumerate(ims):
    sheet.paste(im, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
print(kind, len(sel), "shown")
