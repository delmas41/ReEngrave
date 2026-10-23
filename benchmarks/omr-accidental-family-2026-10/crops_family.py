"""2.201: crop look at the detector's accidental box (orange) and the family's grown box (blue, only if it grew) on Sean's answered tiles.
usage: crops_family.py evalfam.json OUT.png [set:tile ...]"""
import json, sys, os
sys.path.insert(0, "."); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from collections import defaultdict
from tools.omr.preprocessing import render_page
from tools.omr.staged import pipeline
import cause_cut as CC

rows = json.load(open(sys.argv[1]))
want = set(sys.argv[3:])
sel = [r for r in rows if r["acc"] and (not want or "%s:%d" % (r["set"], r["tile"]) in want)]
by = defaultdict(list)
for r in sel:
    by[(r["plate"], r["page"])].append(r)
tiles = []
for (plate, page), rs in by.items():
    pws, cells = pipeline.prepare_pages(CC.PDF[plate], [page], dpi=600)[0]
    pg = render_page(CC.PDF[plate], page, dpi=600).rgb
    for r in rs:
        # locate the cell by the tile's head/box centre: reuse cause_cut's rule through the stored cell index
        c = next(c for c in cells if c.staff_index == r.get("staff", -1) and c.measure_index == r.get("measure", -1)) if "staff" in r else None
        if c is None:
            continue
        up, cb = c.upscale_factor, c.bbox_page_px
        x0, y0, x1, y1 = [v for v in r["acc"]["fam"]["box"]]
        d0 = r["acc"].get("det_box")
        px = lambda x, y: (cb[0] + x / up, cb[1] + y / up)
        fb = [*px(x0, y0), *px(x1, y1)]
        sp = r["sp"] / up
        cx, cy = (fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2
        crop = pg[int(cy - 3.2 * sp):int(cy + 3.2 * sp), int(cx - 3.2 * sp):int(cx + 4.8 * sp)].copy()
        ox, oy = cx - 3.2 * sp, cy - 3.2 * sp
        if d0:
            a, b = px(d0[0], d0[1]), px(d0[2], d0[3])
            cv2.rectangle(crop, (int(a[0] - ox), int(a[1] - oy)), (int(b[0] - ox), int(b[1] - oy)), (255, 140, 0), 1)
        if r["acc"]["fam"]["grown"]:
            cv2.rectangle(crop, (int(fb[0] - ox) - 2, int(fb[1] - oy) - 2), (int(fb[2] - ox) + 2, int(fb[3] - oy) + 2), (0, 90, 255), 1)
        crop = cv2.resize(crop, (240, int(240 * crop.shape[0] / crop.shape[1])))
        f = r["acc"]["fam"]
        lab = "%s %d %s det=%s str=%s" % (r["set"], r["tile"], r["sean"][:3], (f["detector_type"] or "-")[:3], f["type"][:3])
        crop = cv2.copyMakeBorder(crop, 14, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
        cv2.putText(crop, lab, (1, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
        tiles.append(crop)
h = max(t.shape[0] for t in tiles)
cols = 5
rowsimg = []
for i in range(0, len(tiles), cols):
    chunk = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles[i:i + cols]]
    while len(chunk) < cols:
        chunk.append(np.full_like(chunk[0], 255))
    rowsimg.append(np.concatenate(chunk, axis=1))
cv2.imwrite(sys.argv[2], cv2.cvtColor(np.concatenate(rowsimg, axis=0), cv2.COLOR_RGB2BGR))
print(len(tiles), "crops")
