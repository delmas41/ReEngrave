"""2.280: find a REAL whole note for the control tile. Candidates = noteheadWhole* boxes (not rest classes) outside cell 0 (the header cells hold the 6/8 loops), hollow head_ink, score >= 0.3.
Contact sheet (my look) -> pick by eye. usage: p10_whole.py plate OUT.png"""
import json
import sys
import fitz
from PIL import Image, ImageDraw

plate, out = sys.argv[1:3]
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/"
PDFS = {"litolff": (LIB + "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf", 15.75),
        "brahms": (LIB + "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf", 27.3)}
pdf, SP = PDFS[plate]
doc = fitz.open(pdf)
SL = LIB + "_shared-records/lane-report-slices-20261104-night/" + plate + "/observations.jsonl"
ink, box = {}, {}
for l in open(SL):
    o = json.loads(l)
    if o["quantity"] == "head_ink":
        ink[o["subject"]] = o["value"]
    elif o["quantity"] == "glyph_box" and "Whole" in o["value"][0] and "rest" not in o["value"][0].lower():
        box[o["subject"]] = o
cands = [s for s, o in box.items() if int(s.split("/")[4]) > 0 and ink.get(s) == "hollow" and (o["score"] or 0) >= 0.3]
print(plate, len(cands))
tiles = []
for i, s in enumerate(cands[:16]):
    o = box[s]
    x0, y0, x1, y1 = o["detail"]["bbox_page_px"]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    HW, HH = 6 * SP, 5.5 * SP
    clip = (cx - HW, cy - HH, cx + HW, cy + HH)
    Z = 330 / (2 * HW)
    pix = doc[int(s.split("/")[1])].get_pixmap(matrix=fitz.Matrix(600 / 72 * Z, 600 / 72 * Z), clip=fitz.Rect(*[v * 72 / 600 for v in clip]))
    im = Image.frombytes("RGB" if pix.n == 3 else "L", (pix.width, pix.height), pix.samples).convert("RGB")
    ImageDraw.Draw(im).text((3, 3), "%d %s" % (i, s), fill=(200, 0, 0))
    tiles.append(im)
    print(i, s, o["value"][0], round(o["score"], 2))
cols = 4
w, h = tiles[0].size
sheet = Image.new("RGB", (cols * w, ((len(tiles) + cols - 1) // cols) * h), "white")
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * w, (i // cols) * h))
sheet.save(out)
