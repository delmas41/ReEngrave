"""Cut crops of arcs: one staff window, the WHOLE arc boxed (a thin orange box around the arc's ink extent), both ends and the notes in view,
nothing else of ours drawn. Measure only.

    python3 crops.py SPEC.json OUTDIR     SPEC = [{"n": 1, "plate": "litolff", "page": 4, "box": [x0,y0,x1,y1], "sp": 15.75, "note": "..."}, ...]

Writes OUTDIR/NN.png and OUTDIR/key.json (the notes stay out of the picture). The page is rendered from the library PDF at 600 dpi.
"""
import json
import pathlib
import sys

import fitz
from PIL import Image, ImageDraw

LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library")
PDF = {"litolff": "editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": "editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}
ORANGE = (255, 140, 0)
_cache = {}


def page_image(plate, page):
    k = (plate, page)
    if k not in _cache:
        if len(_cache) > 2:
            _cache.clear()
        doc = fitz.open(str(LIB / PDF[plate]))
        pix = doc[page].get_pixmap(matrix=fitz.Matrix(600 / 72, 600 / 72), colorspace=fitz.csRGB)
        _cache[k] = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return _cache[k]


def crop(plate, page, box, sp, pad_x=9.0, pad_y=8.0, max_w=1500):
    im = page_image(plate, page)
    x0, y0, x1, y1 = box
    W, H = im.size
    win = (max(0, int(x0 - pad_x * sp)), max(0, int((y0 + y1) / 2 - max(pad_y * sp, (y1 - y0) / 2 + 3 * sp))),
           min(W, int(x1 + pad_x * sp)), min(H, int((y0 + y1) / 2 + max(pad_y * sp, (y1 - y0) / 2 + 3 * sp))))
    c = im.crop(win).copy()
    d = ImageDraw.Draw(c)
    t = max(2, int(sp * 0.12))
    bx = (x0 - 0.3 * sp - win[0], y0 - 0.3 * sp - win[1], x1 + 0.3 * sp - win[0], y1 + 0.3 * sp - win[1])
    for i in range(t):
        d.rectangle((bx[0] - i, bx[1] - i, bx[2] + i, bx[3] + i), outline=ORANGE)
    if c.width > max_w:
        c = c.resize((max_w, int(c.height * max_w / c.width)), Image.LANCZOS)
    return c


def main():
    spec = json.load(open(sys.argv[1]))
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    key = []
    for s in spec:
        c = crop(s["plate"], s["page"], s["box"], s["sp"])
        name = "%02d.png" % s["n"]
        c.save(out / name)
        key.append(s)
    (out / "key.json").write_text(json.dumps(key, indent=1))
    print("wrote", len(spec), "crops to", out)


if __name__ == "__main__":
    main()
