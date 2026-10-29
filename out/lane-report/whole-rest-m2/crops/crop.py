"""usage: crop.py PLATE PAGE x0 y0 x1 y1 OUT   (page px at 600 dpi), nothing drawn"""
import sys
from PIL import Image
from tools.omr.staged import lane_report as L
from tools.omr.preprocessing import render_page
plate, pg, x0, y0, x1, y1, out = sys.argv[1:8]
im = Image.fromarray(render_page(str(L.LIB / L.PLATES[plate]["pdf"]), int(pg), dpi=600).rgb).convert("RGB")
c = im.crop((int(float(x0)), int(float(y0)), int(float(x1)), int(float(y1))))
c = c.resize((c.width * 2, c.height * 2), Image.LANCZOS)
c.save(out); print(out, c.size)
