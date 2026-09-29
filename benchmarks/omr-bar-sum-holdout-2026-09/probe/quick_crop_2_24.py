"""Scratch: quick single-region crop at 600dpi for visual inspection, ROADMAP 2.24."""
import sys
import fitz
from PIL import Image

PDF = ("/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/"
       "symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--"
       "imslp317803.pdf")


def main():
    page = int(sys.argv[1])
    x0, y0, x1, y1 = (float(v) for v in sys.argv[2:6])
    out = sys.argv[6]
    pad = float(sys.argv[7]) if len(sys.argv) > 7 else 60.0
    doc = fitz.open(PDF)
    pm = doc[page].get_pixmap(dpi=600)
    im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples)
    cx0, cy0 = max(0, int(x0 - pad)), max(0, int(y0 - pad))
    cx1, cy1 = min(im.width, int(x1 + pad)), min(im.height, int(y1 + pad))
    crop = im.crop((cx0, cy0, cx1, cy1))
    z = 3
    crop = crop.resize((crop.width * z, crop.height * z), Image.LANCZOS)
    crop.save(out)
    print("saved", out, "orig box", (cx0, cy0, cx1, cy1))


if __name__ == "__main__":
    main()
