"""2.292: header crops from the print.
  crops.py sheet SEL.json OUT.png          my-look contact sheet (labels drawn, margin label included), 3 columns
  crops.py tiles SEL.json OUTDIR           BLIND tiles: the START of one staff (clef, key, meter if printed, up to the first note); one thin
                                           box around the clef+key region; nothing else drawn; no text; key in key.json
SEL = [{plate, json, staff, bucket?}]   (staff = "staff/PAGE/SYSTEM/INDEX"; json = analyze.py output)
Geometry: page px at 600 dpi (staff lines / extent from the record's GATHER rows, first note from glyph_box detail.bbox_page_px).
"""
import json
import os
import sys

import fitz
from PIL import Image, ImageDraw

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
        "brahms": LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
BLUE = (31, 111, 235)
_cache = {}


def geometry(js, staff):
    d = _cache.setdefault(js, json.load(open(js)))
    ev = d["staffs"][staff]["evidence"]
    lines = ev["staff_lines"][0]["value"]
    SP = float(ev["staff_spacing"][0]["value"])
    x0, x1 = ev["staff_extent"][0]["value"]
    p = staff.split("/")
    first = None
    for s in d["symbols"]:
        sp = s["sub"].split("/")
        if sp[1:4] == p[1:4] and s.get("page_box"):
            x = s["page_box"][0]
            first = x if first is None else min(first, x)
    return int(p[1]), lines, SP, x0, first


def crop(doc, staff, js, blind=True):
    pg, lines, SP, x0, first = geometry(js, staff)
    top, bot = lines[0], lines[-1]
    right = x0 + 22 * SP
    if first is not None:
        right = min(right, first - 0.4 * SP)
    left = x0 - (0.7 * SP if blind else 11 * SP)
    clip = (left, top - 3.0 * SP, right, bot + 3.0 * SP)
    width_px = 900 if blind else 560
    Z = width_px / (clip[2] - clip[0])
    pix = doc[pg].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    sx, sy = im.width / (clip[2] - clip[0]), im.height / (clip[3] - clip[1])
    # box: clef + key region = from the staff start to ~ 13 spaces (clef ~3, up to 3 flats ~5, meter room) or the first note, whichever is first
    bx1 = min(x0 + 13 * SP, right - 0.2 * SP)
    box = [(x0 - 0.3 * SP - clip[0]) * sx, (top - 1.3 * SP - clip[1]) * sy, (bx1 - clip[0]) * sx, (bot + 1.3 * SP - clip[1]) * sy]
    ImageDraw.Draw(im).rectangle(box, outline=BLUE, width=2)
    return im


def main():
    mode, selp, out = sys.argv[1:4]
    sel = json.load(open(selp))
    docs = {}
    if mode == "sheet":
        ims = []
        for s in sel:
            doc = docs.setdefault(s["plate"], fitz.open(PDFS[s["plate"]]))
            im = crop(doc, s["staff"], s["json"], blind=False)
            ImageDraw.Draw(im).text((4, 3), "%s %s %s" % (s["plate"][:3], s["staff"].replace("staff/", "p"), s.get("bucket", "")), fill=(200, 0, 0))
            ims.append(im)
        cols = 3
        w = max(i.width for i in ims)
        h = max(i.height for i in ims)
        rws = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * w, rws * h), (255, 255, 255))
        for i, im in enumerate(ims):
            sheet.paste(im, ((i % cols) * w, (i // cols) * h))
        sheet.save(out)
        print("sheet", out, len(ims))
    else:
        os.makedirs(out, exist_ok=True)
        key = {}
        for n, s in enumerate(sel, 1):
            doc = docs.setdefault(s["plate"], fitz.open(PDFS[s["plate"]]))
            im = crop(doc, s["staff"], s["json"], blind=True)
            fn = "tile_%02d.png" % n
            im.save(os.path.join(out, fn))
            key[str(n)] = dict(file=fn, **{k: v for k, v in s.items() if k != "json"})
        json.dump(key, open(os.path.join(out, "key.json"), "w"), indent=1)
        print("tiles", out, len(sel))


if __name__ == "__main__":
    main()
