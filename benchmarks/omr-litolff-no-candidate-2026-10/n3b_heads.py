"""2.200 N3b: like n3_tiles but draws the cell's head boxes too (BLUE = live head, RED = refused head) and prints apos/hpos. usage: n3b_heads.py FEATURES.json PDF OUTPREFIX SPEC.json"""
import sys, json, fitz
from PIL import Image, ImageDraw, ImageFont
F = json.load(open(sys.argv[1]))["boxes"]; by = {b["key"]: b for b in F}
doc = fitz.open(sys.argv[2]); spec = json.load(open(sys.argv[4])); cache = {}; font = ImageFont.load_default()
UNIT = 16.0; SC = 3
for name, keys in spec.items():
    tiles = []
    for i, k in enumerate(keys):
        b = by[k]; pg = b["page"]
        if pg not in cache:
            pix = doc[pg].get_pixmap(dpi=600, colorspace=fitz.csGRAY); cache[pg] = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
        x0, y0, x1, y1 = b["pb"]; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        a, t, c, d = int(cx - 6 * UNIT), int(cy - 4.5 * UNIT), int(cx + 6 * UNIT), int(cy + 4.5 * UNIT)
        crop = cache[pg].crop((a, t, c, d)).resize(((c - a) * SC, (d - t) * SC), Image.LANCZOS); dr = ImageDraw.Draw(crop)
        for h in b["heads"]:
            if not h.get("pb"): continue
            hx0, hy0, hx1, hy1 = h["pb"]; col = (0, 90, 255) if h["status"] == "live" else (230, 0, 0)
            dr.rectangle([(hx0 - a) * SC, (hy0 - t) * SC, (hx1 - a) * SC, (hy1 - t) * SC], outline=col, width=1)
        dr.rectangle([(x0 - a) * SC, (y0 - t) * SC, (x1 - a) * SC, (y1 - t) * SC], outline=(255, 120, 0), width=2)
        cv = Image.new("RGB", (crop.width, crop.height + 14), (255, 255, 255)); cv.paste(crop, (0, 14))
        ImageDraw.Draw(cv).text((3, 1), "%s-%02d %s apos %.1f" % (name, i, b["cls"][8:], b["apos"]), fill=(0, 0, 0), font=font); tiles.append(cv)
    W, H = tiles[0].size; cols = 3; rows = (len(tiles) + cols - 1) // cols
    sh = Image.new("RGB", (W * cols + 4 * (cols - 1), H * rows + 4 * (rows - 1)), (255, 255, 255))
    for j, tl in enumerate(tiles): sh.paste(tl, ((j % cols) * (W + 4), (j // cols) * (H + 4)))
    sh.save("%s_%s.png" % (sys.argv[3], name)); print(name, len(tiles), sh.size)
