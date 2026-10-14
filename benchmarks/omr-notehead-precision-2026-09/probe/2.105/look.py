"""Contact sheet of record glyphs. usage: look.py RECORD MOVEMENT OUT.png KEY [KEY...]
(a KEY may be `glyph/p/s/st/c/g`; every other gathered box in the window is NOT drawn)"""
import sys

import cv2

from lib105 import crop, page_rgb, sheet, staff_spacing
from tools.omr.staged.readout import load_run

run = load_run(sys.argv[1])
mv, out, keys = sys.argv[2], sys.argv[3], sys.argv[4:]
sps = staff_spacing(run)
tiles = []
for k in keys:
    g = run.glyphs[k]
    tiles.append(crop(page_rgb(mv, g.page), [(*g.box_page, (220, 30, 30))], sps[g.staff_key],
                      label=f"{k[6:]} {g.cls}"))
cv2.imwrite(out, cv2.cvtColor(sheet(tiles), cv2.COLOR_RGB2BGR))
print("wrote", out, len(tiles))
