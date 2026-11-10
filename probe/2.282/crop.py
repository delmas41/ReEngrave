"""2.282: contact sheet for MY OWN LOOK (CLAUDE rule 7; not evidence): crops around page boxes, one thin orange box, label under each.
usage: crop.py OUT.png ITEMS.json     ITEMS = [{"plate","page","box":[x0,y0,x1,y1],"sp":float,"label":str}, ...]"""
import json
import sys

import fitz
from PIL import Image, ImageDraw

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
_docs = {}


def crop(plate, page, box, sp, hw=6.0, hh=5.0, width=420, draw=True, boxes=()):
    doc = _docs.setdefault(plate, fitz.open(PDFS[plate]))
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    clip = (cx - hw * sp, cy - hh * sp, cx + hw * sp, cy + hh * sp)
    z = width / (2 * hw * sp)
    pix = doc[page].get_pixmap(matrix=fitz.Matrix(600 / 72 * z, 600 / 72 * z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
    d = ImageDraw.Draw(im)
    if draw:
        d.rectangle([(x0 - clip[0]) * sx, (y0 - clip[1]) * sy, (x1 - clip[0]) * sx, (y1 - clip[1]) * sy], outline=(255, 110, 0), width=1)
    for b, col in boxes:
        d.rectangle([(b[0] - clip[0]) * sx, (b[1] - clip[1]) * sy, (b[2] - clip[0]) * sx, (b[3] - clip[1]) * sy], outline=col, width=1)
    return im


if __name__ == "__main__":
    out, items = sys.argv[1], json.load(open(sys.argv[2]))
    ims = []
    for it in items:
        im = crop(it["plate"], it["page"], it["box"], it["sp"], boxes=[(b, tuple(c)) for b, c in it.get("boxes", [])])
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, im.width, 12], fill=(255, 255, 255))
        d.text((2, 0), it["label"][:70], fill=(0, 0, 0))
        ims.append(im)
    cols = 3
    w, h = ims[0].width, max(i.height for i in ims)
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h), (255, 255, 255))
    for i, im in enumerate(ims):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    sheet.save(out)
    print(out, len(ims))
