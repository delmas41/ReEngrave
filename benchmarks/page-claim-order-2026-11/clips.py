"""ROADMAP 2.253 step 0 -- the lane's own look: page grids and high-resolution clips of the frozen pages (no claims drawn).

    python3 benchmarks/page-claim-order-2026-11/clips.py grid PLATE OUT.png          # the 8 frozen pages in one image
    python3 benchmarks/page-claim-order-2026-11/clips.py clip PLATE PAGE x0 y0 x1 y1 OUT.png   # page fraction box (0..1), 300 dpi
    python3 benchmarks/page-claim-order-2026-11/clips.py px PLATE PAGE x0 y0 x1 y1 OUT.png [BOX x0 y0 x1 y1]  # 600-dpi page px
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import count as C  # noqa: E402


def grid(plate, out):
    import fitz
    from PIL import Image
    f, pages = C.EDITIONS[plate]
    d = fitz.open(f)
    ims = []
    for p in pages:
        pix = d[p].get_pixmap(dpi=55)
        ims.append(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    w, h = ims[0].size
    G = Image.new("RGB", (4 * w, 2 * h), "white")
    for i, im in enumerate(ims):
        G.paste(im, ((i % 4) * w, (i // 4) * h))
    G.save(out)


def clip(plate, page, x0, y0, x1, y1, out, dpi=300):
    import fitz
    f, _ = C.EDITIONS[plate]
    d = fitz.open(f)
    r = d[int(page)].rect
    rect = fitz.Rect(r.x0 + float(x0) * r.width, r.y0 + float(y0) * r.height, r.x0 + float(x1) * r.width, r.y0 + float(y1) * r.height)
    d[int(page)].get_pixmap(dpi=dpi, clip=rect).save(out)


def px(plate, page, x0, y0, x1, y1, out, *box):
    """A clip in the pipeline's 600-dpi page pixels (the record's bbox_page_px), optional thin box drawn."""
    import fitz
    from PIL import Image, ImageDraw
    f, _ = C.EDITIONS[plate]
    d = fitz.open(f)
    s = 72.0 / 600.0
    rect = fitz.Rect(float(x0) * s, float(y0) * s, float(x1) * s, float(y1) * s)
    pix = d[int(page)].get_pixmap(dpi=300, clip=rect)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    if box:
        b = [float(v) for v in box]
        k = 0.5
        ImageDraw.Draw(im).rectangle([(b[0] - float(x0)) * k - 2, (b[1] - float(y0)) * k - 2, (b[2] - float(x0)) * k + 2,
                                      (b[3] - float(y0)) * k + 2], outline=(255, 120, 0), width=2)
    im.save(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "grid":
        grid(a[1], a[2])
    elif a[0] == "clip":
        clip(a[1], a[2], *a[3:7], a[7])
    else:
        px(a[1], a[2], *a[3:7], a[7], *a[8:12])
