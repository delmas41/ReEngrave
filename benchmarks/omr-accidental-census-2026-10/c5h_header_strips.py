"""2.197 C5h: BLIND header strips (no detections drawn) of every staff of a page: cell 0 of each staff, with a ruler in staff spaces, 12 per sheet (2 x 6),
for counting the PRINTED key-signature accidentals by eye. usage: c5h_header_strips.py VIEW.json PDF PAGE UNIT OUTDIR"""
import sys, collections, pathlib, json, fitz
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from census_lib import View
from PIL import Image, ImageDraw, ImageFont
view = View(sys.argv[1]); doc = fitz.open(sys.argv[2]); page = int(sys.argv[3]); UNIT = float(sys.argv[4]); out = pathlib.Path(sys.argv[5]); out.mkdir(parents=True, exist_ok=True)
pix = doc[page].get_pixmap(dpi=600, colorspace=fitz.csGRAY); img = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
font = ImageFont.load_default(); SC = 1.6
tiles = []; meta = []
for (p, s, st, c), b in sorted(view.cellbox.items()):
    if p != page or c != 0: continue
    x0, y0, x1, y1 = b[0], b[1], min(b[2], b[0] + 17 * UNIT), b[3]
    crop = img.crop((int(x0), int(y0), int(x1), int(y1))).resize((int((x1 - x0) * SC), int((y1 - y0) * SC)), Image.LANCZOS)
    cv = Image.new("RGB", (crop.width, crop.height + 14), (255, 255, 255)); cv.paste(crop, (0, 14)); d = ImageDraw.Draw(cv)
    for k in range(0, 18, 2):
        X = k * UNIT * SC; d.line([(X, 8), (X, 14)], fill=(200, 0, 0)); d.text((X + 1, 0), str(k), fill=(200, 0, 0), font=font)
    d.text((crop.width - 60, 0), "S%d-st%d" % (s, st), fill=(0, 120, 0), font=font)
    tiles.append(cv); meta.append(dict(tile=len(tiles) - 1, system=s, staff=st))
json.dump(meta, open(out / ("p%d_hdr_meta.json" % page), "w"))
PER = 12
for i in range(0, len(tiles), PER):
    grp = tiles[i:i + PER]; W = max(t.width for t in grp); rows = [grp[j:j + 2] for j in range(0, len(grp), 2)]
    H = sum(max(t.height for t in r) + 4 for r in rows); sh = Image.new("RGB", (W * 2 + 4, H), (255, 255, 255)); y = 0
    for r in rows:
        x = 0
        for t in r: sh.paste(t, (x, y)); x += W + 4
        y += max(t.height for t in r) + 4
    sh.save(out / ("p%d_hdr%d.png" % (page, i // PER)))
print(len(tiles), "headers")
