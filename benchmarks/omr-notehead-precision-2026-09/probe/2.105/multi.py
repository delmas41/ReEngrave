"""One crop per cell with ALL notehead boxes of the cell drawn in distinct colours.
usage: multi.py RECORD MOVEMENT OUT.png CELLKEY... (cell/p/s/st/c)  -- exploration only"""
import sys

import cv2

from lib105 import crop, page_rgb, sheet, staff_spacing
from tools.omr.staged.readout import load_run

COL = [(220, 30, 30), (30, 90, 220), (20, 160, 60), (230, 140, 0), (160, 30, 200), (0, 170, 170)]
run = load_run(sys.argv[1])
mv, out, cells = sys.argv[2], sys.argv[3], sys.argv[4:]
sps = staff_spacing(run)
tiles = []
for ck in cells:
    gs = sorted([g for g in run.glyphs.values() if g.cell_key == ck and (g.cls or "").startswith("notehead")],
                key=lambda g: g.index)
    boxes = [(*g.box_page, COL[i % len(COL)]) for i, g in enumerate(gs)]
    lab = " ".join(f"{g.index}:{COL[i % 6] and ['red','blue','green','orange','purple','cyan'][i % 6]}" for i, g in enumerate(gs))
    tiles.append(crop(page_rgb(mv, gs[0].page), boxes, sps[gs[0].staff_key], half_h_sp=4.0, label=ck[5:] + " " + lab))
cv2.imwrite(out, cv2.cvtColor(sheet(tiles, cols=3), cv2.COLOR_RGB2BGR))
print("wrote", out)
