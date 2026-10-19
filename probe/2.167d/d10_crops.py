"""2.167d probe 10: the 8 crops for Sean (out/print/2.167d/). One BLUE box = the item; thin GREY frame = the bar crop the detector was given.
Nothing else drawn. usage: d10_crops.py"""
import json
import os

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = ROOT + "/probe/2.167d/"
OUT = ROOT + "/out/print/2.167d/"
os.makedirs(OUT, exist_ok=True)
PDF = {"lit": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "bra": "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
BLUE = (31, 111, 235)
GREY = (140, 140, 140)
# (plate, bar index, source of the blue box, caption)
PICKS = [
    ("bra", 16, ("new", "wide", "rest8th"), "Brahms p9 flute: an eighth rest the detector never boxed at all (no box at 0.05)"),
    ("bra", 7, ("ref", 7), "Brahms p20 contrabass: the flag of this eighth was seen at 0.22, under the 0.25 floor; written as a quarter"),
    ("bra", 30, ("ref", 5), "Brahms p8 violin: this dot was seen at 0.24, under the floor; the quarter is written plain"),
    ("lit", 2, ("ref", 2), "Litolff p1 violin: this black head was boxed as a whole rest (0.35) and refused as a rest; never a head"),
    ("lit", 25, ("ref", 3), "Litolff p13 bassoon: this quarter rest was boxed as 'arpeggiato' (0.54), not as a rest"),
    ("bra", 14, ("fate", "rest8th"), "Brahms p3 oboe: this eighth rest was boxed 0.81, decided a rest, then dropped as a meter digit (header bar)"),
    ("bra", 39, ("fate", "noteheadBlackI"), "Brahms p15 contrabass: this head was boxed 0.73 and kept, then left out (duration narrowed)"),
    ("lit", 37, ("ref", 2), "Litolff p1 flute: this printed '0' above the staff was boxed as a hollow head (0.30) and written as a half note"),
]
rr = {pl: json.load(open(D + "data/%s_rerun.json" % pl)) for pl in ("lit", "bra")}
rec = {pl: json.load(open(D + "data/%s_rec.json" % pl)) for pl in ("lit", "bra")}
samp = {pl: json.load(open(D + "data/%s_sample.json" % pl)) for pl in ("lit", "bra")}
bfs = {pl: json.load(open(D + "data/%s_boxfates.json" % pl)) for pl in ("lit", "bra")}
docs = {pl: fitz.open(PDF[pl]) for pl in PDF}
try:
    fnt = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
except Exception:
    fnt = ImageFont.load_default()
index = []
for k, (pl, bar, src, cap) in enumerate(PICKS, 1):
    p, s, st, c = samp[pl][bar]
    key = "%d/%d/%d/%d" % (p, s, st, c)
    R = rr[pl][key]
    sp = R["spacing"]
    nmap = json.load(open(D + "sheets/%s_%02d.json" % (pl, bar)))
    if src[0] == "ref":
        bb = nmap[str(src[1])]["bbox"]
    elif src[0] == "new":
        bb = [b[2:6] for b in R["variants"][src[1]]["boxes"] if b[0] == src[2] and b[1] >= 0.25][0]
    else:
        g = [g for g in rec[pl]["cells"][key]["glyphs"] if g["cls"].startswith(src[1]) and any(r["sub"] == g["sub"] and r["fate"] != "written" for r in bfs[pl][key])]
        bb = g[0]["bbox"]
    x0, y0, x1, y1 = R["cell"]
    top = R["lines"][0]
    r = (min(x0, bb[0]) - 2 * sp, top - 4 * sp, max(x1, bb[2]) + 2 * sp, top + 9 * sp)
    z = 3.0 if pl == "lit" else 1.8
    pix = docs[pl][p].get_pixmap(matrix=fitz.Matrix(600 / 72 * z, 600 / 72 * z), clip=fitz.Rect(*[v * 72 / 600 for v in r]))
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    f = im.width / (r[2] - r[0])
    d = ImageDraw.Draw(im)
    d.rectangle([(x0 - r[0]) * f, (y0 - r[1]) * f, (x1 - r[0]) * f, (y1 - r[1]) * f], outline=GREY, width=1)
    d.rectangle([(bb[0] - r[0]) * f - 2, (bb[1] - r[1]) * f - 2, (bb[2] - r[0]) * f + 2, (bb[3] - r[1]) * f + 2], outline=BLUE, width=3)
    t = Image.new("RGB", (max(im.width, 700), im.height + 24), "white")
    t.paste(im, (0, 24))
    ImageDraw.Draw(t).text((4, 4), "%d  %s" % (k, cap), fill=(0, 0, 0), font=fnt)
    fn = "crop_%d.png" % k
    t.save(OUT + fn)
    index.append(dict(file=fn, plate=pl, sample_bar=bar, page=p, system=s, staff=st, cell=c, caption=cap, item_box_page_px=[round(v, 1) for v in bb], bar_crop_page_px=R["cell"]))
json.dump(index, open(OUT + "index.json", "w"), indent=1)
print(len(index), "crops")
