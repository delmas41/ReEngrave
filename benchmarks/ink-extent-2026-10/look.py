"""2.248 private look (not evidence, not for Sean): crops with the detector box (orange) and another extent (blue).
usage: look.py PDF OUT.png PAGE:x0,y0,x1,y1:X0,Y0,X1,Y1 ...  (page px at 600 dpi)"""
import sys

import fitz
from PIL import Image, ImageDraw

_cache = {}


def page_img(pdf, page):
    k = (pdf, page)
    if k not in _cache:
        doc = fitz.open(pdf)
        pix = doc[page].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
        _cache[k] = Image.frombytes("L", (pix.width, pix.height), pix.samples).convert("RGB")
    return _cache[k]


def main(pdf, out, *items):
    tiles = []
    for it in items:
        pg, a, b = it.split(":")
        a = [float(v) for v in a.split(",")]
        b = [float(v) for v in b.split(",")]
        im = page_img(pdf, int(pg))
        cx, cy = (a[0] + a[2]) / 2, (a[1] + a[3]) / 2
        R = 70
        crop = im.crop((int(cx - R), int(cy - R), int(cx + R), int(cy + R))).copy()
        d = ImageDraw.Draw(crop)
        o = (int(cx - R), int(cy - R))
        d.rectangle([a[0] - o[0] - 1, a[1] - o[1] - 1, a[2] - o[0] + 1, a[3] - o[1] + 1], outline=(255, 140, 0))
        d.rectangle([b[0] - o[0] - 2, b[1] - o[1] - 2, b[2] - o[0] + 2, b[3] - o[1] + 2], outline=(0, 90, 255))
        tiles.append(crop.resize((280, 280)))
    W = 280 * min(5, len(tiles))
    H = 280 * ((len(tiles) + 4) // 5)
    sheet = Image.new("RGB", (W, H), "white")
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 5) * 280, (i // 5) * 280))
    sheet.save(out)


if __name__ == "__main__":
    main(*sys.argv[1:])
