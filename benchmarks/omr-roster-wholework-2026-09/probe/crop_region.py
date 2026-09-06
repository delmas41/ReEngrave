"""Render an arbitrary fractional region of a PDF page. x0 y0 x1 y1 as fractions."""
import sys
import fitz

pdf, out, pi = sys.argv[1], sys.argv[2], int(sys.argv[3])
x0, y0, x1, y1 = (float(v) for v in sys.argv[4:8])
dpi = int(sys.argv[8]) if len(sys.argv) > 8 else 150
doc = fitz.open(pdf)
p = doc[pi]
r = p.rect
clip = fitz.Rect(r.x0 + r.width * x0, r.y0 + r.height * y0,
                 r.x0 + r.width * x1, r.y0 + r.height * y1)
pm = p.get_pixmap(dpi=dpi, clip=clip)
pm.save(out)
print(out, pm.width, "x", pm.height)
