"""Render the left margin strip of a PDF page, so a human can read the labels."""
import sys
import fitz

pdf, out = sys.argv[1], sys.argv[2]
pages = [int(x) for x in sys.argv[3].split(",")]
frac = float(sys.argv[4]) if len(sys.argv) > 4 else 0.22
doc = fitz.open(pdf)
for pi in pages:
    page = doc[pi]
    r = page.rect
    clip = fitz.Rect(r.x0, r.y0, r.x0 + r.width * frac, r.y1)
    pm = page.get_pixmap(dpi=170, clip=clip)
    p = f"{out}/p{pi}-margin.png"
    pm.save(p)
    print(p, pm.width, "x", pm.height)
