"""2.280 r3: crops of heads from the print. Two modes.
  crops.py sheet HEADS.jsonl PLATE OUT.png sub [sub ...]      my-look contact sheet (labels drawn: sub, fate), 5 columns
  crops.py tiles HEADS.jsonl PLATE OUTDIR SEL.json            blind tiles: ONE thin box the size of the head, nothing else drawn, no text; key beside
The crop is wide enough for the whole stem and any beam / flag (+-9 sp above and below the head, +-9 sp left/right). Page px at 600 dpi both ways.
"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
BLUE = (31, 111, 235)
HWX, HWY = 9.0, 8.0


def crop(doc, pg, SP, box, width_px=420, thin=True, mark=True):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    clip = (cx - HWX * SP, cy - HWY * SP, cx + HWX * SP, cy + HWY * SP)
    Z = width_px / (2 * HWX * SP)
    pix = doc[pg].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    if mark:
        sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
        pad = 0.12 * SP
        b = [(x0 - pad - clip[0]) * sx, (y0 - pad - clip[1]) * sy, (x1 + pad - clip[0]) * sx, (y1 + pad - clip[1]) * sy]
        ImageDraw.Draw(im).rectangle(b, outline=BLUE, width=2)
    return im


def main():
    mode, heads, plate, out = sys.argv[1:5]
    if mode == "sheet":
        rows = {}
        for l in open(heads):
            r = json.loads(l)
            rows[r["sub"]] = r
        pdf, SP = PDFS[plate]
        doc = fitz.open(pdf)
        subs = sys.argv[5:]
        ims = []
        for s in subs:
            r = rows[s]
            im = crop(doc, r["page"], SP, r["page_box"], 360)
            d = ImageDraw.Draw(im)
            d.text((3, 3), "%s %s" % (s.replace("glyph/", ""), r["fate"][:22]), fill=(200, 0, 0))
            ims.append(im)
        cols = 5
        w, h = ims[0].size
        rws = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, rws * h), (255, 255, 255))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(out)
        print("sheet", out, len(ims))
    else:
        # tiles OUTDIR SEL.json : SEL = [{plate, heads, sub, bucket}], blind, one thin head-sized box, nothing else
        sel = json.load(open(sys.argv[5]))
        os.makedirs(out, exist_ok=True)
        key = {}
        docs = {}
        cache = {}
        for n, p in enumerate(sel, 1):
            if p["heads"] not in cache:
                cache[p["heads"]] = {json.loads(l)["sub"]: json.loads(l) for l in open(p["heads"])}
            r = cache[p["heads"]][p["sub"]]
            pdf, SP = PDFS[p["plate"]]
            doc = docs.setdefault(p["plate"], fitz.open(pdf))
            im = crop(doc, r["page"], SP, r["page_box"], 700)
            fn = "tile_%02d.png" % n
            im.save(os.path.join(out, fn))
            key[str(n)] = dict(file=fn, plate=p["plate"], page=r["page"], sub=p["sub"], page_box=r["page_box"], bucket=p.get("bucket"),
                               ours=dict(fate=r["fate"], n_stem=r["n_stem"], head_stem=r["head_stem"], stem_dir=r["stem_dir"],
                                         duration=r["duration"], d=r["d"]))
        json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1)
        print("tiles", out, len(sel))

main()
