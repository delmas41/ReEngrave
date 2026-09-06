"""Find the pages that print FULL instrument names in the margin.

A movement opening names its orchestra in full ('Clarinetti in B.'); every page
after it prints an abbreviation ('Cl.') or nothing. So the left margin of an
opening carries several times the ink of an ordinary page, and the openings fall
out of a per-page ink profile with no OCR and no model.

Reports the ranked profile; the caller eyeballs the top rows against the print.
"""
import sys
import fitz

pdf = sys.argv[1]
frac = float(sys.argv[2]) if len(sys.argv) > 2 else 0.085
doc = fitz.open(pdf)
rows = []
for pi in range(doc.page_count):
    page = doc[pi]
    r = page.rect
    clip = fitz.Rect(r.x0, r.y0, r.x0 + r.width * frac, r.y1)
    pm = page.get_pixmap(dpi=72, clip=clip, colorspace=fitz.csGRAY)
    buf = pm.samples
    dark = sum(1 for b in buf if b < 160)
    rows.append((pi, dark / max(1, len(buf))))

mean = sum(v for _, v in rows) / len(rows)
print(f"pages={len(rows)} margin-ink mean={mean:.5f}")
print("ranked by margin ink (a movement opening prints full names):")
for pi, v in sorted(rows, key=lambda t: -t[1])[:16]:
    print(f"  page_index {pi:4d}   ink {v:.5f}   x{v/mean:5.2f} mean")
print()
print("profile:")
for pi, v in rows:
    print(f"  {pi:4d} {v:.5f} {'#' * int(v / mean * 20)}")
