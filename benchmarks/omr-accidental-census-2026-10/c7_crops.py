"""2.197 C7: crop sheets of chosen census items (rule 7: my own look at the misses). Each tile: the page ink around the truth box (+-3.5 staff spaces),
Sean's hand box in ORANGE (the truth), every accidental/key-class box the record holds on that ink in BLUE with its class letter and confidence.
usage: c7_crops.py CENSUS.json PDF OUTPNG IDX,IDX,...   (idx into the census list)  [unit]"""
import sys, json, fitz
sys.path.insert(0, __file__.rsplit("/", 1)[0])
from PIL import Image, ImageDraw, ImageFont
cen = json.load(open(sys.argv[1])); pdf = sys.argv[2]; outp = sys.argv[3]
idx = [int(x) for x in sys.argv[4].split(",")]; UNIT = float(sys.argv[5]) if len(sys.argv) > 5 else 32.0
doc = fitz.open(pdf); cache = {}
font = ImageFont.load_default()
tiles = []
for n, i in enumerate(idx):
    it = cen[i]; pg = it["page"]
    if pg not in cache:
        pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY); cache[pg] = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
    img = cache[pg]; tb = it["box"]; cx = (tb[0] + tb[2]) / 2; cy = (tb[1] + tb[3]) / 2
    R = 3.5 * UNIT
    a, b, c, d = int(cx - 2.2 * R), int(cy - R), int(cx + 1.8 * R), int(cy + R)
    SC = 1.8 if UNIT > 20 else 3.2
    crop = img.crop((a, b, c, d)).resize((int((c - a) * SC), int((d - b) * SC)), Image.LANCZOS)
    dr = ImageDraw.Draw(crop)
    dr.rectangle([(tb[0] - a) * SC, (tb[1] - b) * SC, (tb[2] - a) * SC, (tb[3] - b) * SC], outline=(255, 140, 0), width=2)
    for k, bx in enumerate(it.get("boxes_on_ink") or []):
        bb = bx["box"]; dr.rectangle([(bb[0] - a) * SC, (bb[1] - b) * SC, (bb[2] - a) * SC, (bb[3] - b) * SC], outline=(0, 90, 255), width=1)
    th = it.get("truth_head")
    if th: dr.rectangle([(th[0] - a) * SC, (th[1] - b) * SC, (th[2] - a) * SC, (th[3] - b) * SC], outline=(0, 160, 0), width=1)
    cap = "#%d %s %s %s | %s" % (n, it["src"], it.get("cell_label", ""), it["type"], it.get("G", ""))
    canvas = Image.new("RGB", (crop.width, crop.height + 30), (255, 255, 255)); canvas.paste(crop, (0, 30)); cd = ImageDraw.Draw(canvas)
    cd.text((2, 2), cap, fill=(0, 0, 0), font=font)
    cd.text((2, 14), "boxes: " + ", ".join("%s %.2f" % (bx["cls"].replace("accidental", "acc"), bx["conf"]) for bx in (it.get("boxes_on_ink") or [])[:4]) + (" | A: %s" % (it.get("A") or it.get("KS"))), fill=(0, 0, 160), font=font)
    tiles.append(canvas)
W = max(t.width for t in tiles); cols = 2
rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
H = sum(max(t.height for t in r) + 6 for r in rows)
sheet = Image.new("RGB", (W * cols + 6, H), (255, 255, 255)); y = 0
for r in rows:
    x = 0
    for t in r: sheet.paste(t, (x, y)); x += W + 6
    y += max(t.height for t in r) + 6
sheet.save(outp); print(outp, sheet.size)
