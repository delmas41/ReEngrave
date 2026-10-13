"""Sheet of head(red)+rest(blue) pairs. usage: pairs.py RECORD MOVEMENT OUT HEAD REST [HEAD REST ...]"""
import sys

import cv2

from lib105 import crop, page_rgb, sheet, staff_spacing
from tools.omr.staged.readout import load_run

run = load_run(sys.argv[1])
mv, out, ks = sys.argv[2], sys.argv[3], sys.argv[4:]
sps = staff_spacing(run)
tiles = []
for i in range(0, len(ks), 2):
    h, r = run.glyphs[ks[i]], run.glyphs[ks[i + 1]]
    tiles.append(crop(page_rgb(mv, h.page), [(*h.box_page, (220, 30, 30)), (*r.box_page, (30, 90, 220))],
                      sps[h.staff_key], half_h_sp=4.0, label=ks[i][6:] + " " + r.cls))
cv2.imwrite(out, cv2.cvtColor(sheet(tiles, cols=4), cv2.COLOR_RGB2BGR))
