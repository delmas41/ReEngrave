"""ROADMAP 2.94 print crops: the margin label, boxed on ITS OWN INK.

The record gives only the label's y centre (600 dpi), not its x. So the box is
FOUND: dark pixels left of the system's thick barline, within +-110 px of y.
Frame control (it can fail): the box must hold >= MIN_INK ink pixels, and the
same box shifted 250 px left (blank margin) must hold < 10% of that -- which is
exactly what the first cut of these crops did, and `--shift-test` proves the
control rejects it.

    python3 crop_label.py PDF PAGE Y OUT [--shift-test]
"""
import sys

import fitz
import numpy as np
from PIL import Image, ImageDraw

MIN_INK = 150


def render(pdf, page, y, out, shift_test=False):
    pix = fitz.open(pdf)[page].get_pixmap(dpi=600)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    top, bot, right = int(y - 260), int(y + 260), 2200
    crop = im.crop((0, top, right, bot))
    dark = np.asarray(crop.convert("L")) < 110
    h = dark.shape[0]
    # system barline: first column dark over most of the crop height
    bar = next(x for x in range(200, right) if dark[:, x].sum() > 0.8 * h)
    band = dark[260 - 110:260 + 110, :bar - 15]
    ys, xs = np.nonzero(band)
    x0, x1 = int(xs.min()) - 12, int(xs.max()) + 12
    y0, y1 = int(ys.min()) + 150 - 12, int(ys.max()) + 150 + 12
    if shift_test:
        x0, x1 = x0 - 250, x1 - 250

    def ink(a, b, c, d):
        return int(dark[max(c, 0):d, max(a, 0):b].sum())

    inside = ink(x0, x1, y0, y1)
    left = ink(x0 - 250, x1 - 250, y0, y1)
    if inside < MIN_INK or left > 0.1 * inside:
        raise SystemExit(f"FRAME CONTROL FAILED {out}: ink inside {inside}, "
                         f"shifted-left {left}")
    d = ImageDraw.Draw(crop)
    d.rectangle((x0, y0, x1, y1), outline=(255, 0, 0), width=4)
    crop.save(out)
    print(out, "ink inside", inside, "shifted-left", left)


if __name__ == "__main__":
    render(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4],
           "--shift-test" in sys.argv)
