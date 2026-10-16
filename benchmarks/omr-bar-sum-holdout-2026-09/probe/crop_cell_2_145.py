"""2.145 -- a plain crop of one bar (our own look, NOT for Sean): doc page system staff cell OUT.png [HEADBOX x0,y0,x1,y1]
Boxes go through out/2.145/{lit,brah}-geom.json."""
import json
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, ".")
from tools.omr.preprocessing import render_page  # noqa: E402

LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/"
PDFS = {
    "brah": LIB + "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
    "lit": LIB + "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
}
tag, page, system, staff, cell, out = sys.argv[1], *(int(x) for x in sys.argv[2:6]), sys.argv[6]
g = json.load(open(f"out/2.145/{tag}-geom.json"))
cb = g["cell_box"][f"{page}/{system}/{staff}/{cell}"]
ln = g["staff_lines"][f"{page}/{system}/{staff}"]
img = np.asarray(Image.fromarray(render_page(PDFS[tag], page, dpi=600).rgb).convert("RGB"))
f = 1.0      # geometry is at 600 dpi
sp = float(np.mean(np.diff(ln))) * f
x0, x1 = int(cb[0] * f - 3 * sp), int(cb[2] * f + 3 * sp)
y0, y1 = int(ln[0] * f - 5 * sp), int(ln[-1] * f + 5 * sp)
Image.fromarray(img[y0:y1, x0:x1]).save(out)
print(out, x1 - x0, y1 - y0)
