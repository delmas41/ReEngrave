"""12 blind barline tiles, cut to the bar (+-0.75 bar around a column): 6 columns x (upper half, lower half) of the system. Nothing drawn.
usage: barline_tiles.py PDF OUT_DIR KEY.json ; tiles shuffled with a fixed seed, key written outside the tiles folder."""
import json
import os
import random
import sys
sys.path.insert(0, ".")
import cv2
from tools.omr.preprocessing import render_page
from tools.omr.staff_detector import detect_staves

pdf, out, keyp = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)
# (page, system, x, role): changed columns (2559 removed, 1526 removed, 1470 added) and controls (real columns kept)
COLS = [(6, 1, 2559, "removed"), (9, 1, 1470, "added"), (9, 1, 1526, "removed"),
        (9, 1, 1343, "control_kept"), (6, 1, 2489, "control_kept"), (9, 1, 1800, "control_kept")]
tiles, cache = [], {}
for page, sysi, x, role in COLS:
    if page not in cache:
        cache[page] = detect_staves(render_page(pdf, page, dpi=600))
    pws = cache[page]
    st = sorted([s for s in pws.staves if s.system_index == sysi], key=lambda s: s.top_y)
    half = len(st) // 2
    for part, grp in (("upper", st[:half]), ("lower", st[half:])):
        y0, y1 = grp[0].top_y - 30, grp[-1].bottom_y + 30
        img = pws.page.binary[max(0, y0):y1, max(0, x - 160):x + 160]
        tiles.append((img, dict(page=page, system=sysi, x=x, role=role, part=part)))
random.Random(1029).shuffle(tiles)
key = []
for i, (img, meta) in enumerate(tiles, 1):
    cv2.imwrite(os.path.join(out, "tile_%02d.png" % i), img)
    key.append(dict(tile=i, **meta))
json.dump(key, open(keyp, "w"), indent=1)
print(len(tiles))
