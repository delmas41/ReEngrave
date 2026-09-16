"""Cut a rectangle out of one extracted system crop, so a bar can be LOOKED at.

⚠️ The fractions are of the crop's own width/height, because the crops are
different sizes and a pixel rectangle would be a property of one of them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--img", required=True)
    ap.add_argument("--x0", type=float, default=0.0)
    ap.add_argument("--x1", type=float, default=1.0)
    ap.add_argument("--y0", type=float, default=0.0)
    ap.add_argument("--y1", type=float, default=1.0)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    im = Image.open(a.img)
    W, H = im.size
    box = (int(a.x0 * W), int(a.y0 * H), int(a.x1 * W), int(a.y1 * H))
    if box[2] <= box[0] or box[3] <= box[1]:
        print("DEAD: empty rectangle", file=sys.stderr)
        return 2
    cut = im.crop(box)
    if a.scale != 1.0:
        cut = cut.resize((int(cut.width * a.scale), int(cut.height * a.scale)),
                         Image.LANCZOS)
    cut.save(a.out)
    print(f"{a.img} {W}x{H} -> {box} -> {cut.size} -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
