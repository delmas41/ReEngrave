"""2.201: crops of Sean's answered tiles: left = the cell's staff-erased raster with the detector box (orange); right = the same with the
stroke boxes (blue vertical, green horizontal, red blob, grey curve). usage: crops_cut.py OUT_DIR cause.json [set:tile ...]"""
import json, sys, os
sys.path.insert(0, "."); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2
from collections import defaultdict
from tools.omr.staged import pipeline, gather as G, stroke_map as SM
import truth_tiles as TT, cause_cut as CC
COL = {"vertical": (255, 0, 0), "horizontal": (0, 160, 0), "blob": (0, 0, 255), "curve": (128, 128, 128)}
if __name__ == "__main__":
    out, rows = sys.argv[1], json.load(open(sys.argv[2]))
    want = set(sys.argv[3:])
    os.makedirs(out, exist_ok=True)
    by = defaultdict(list)
    for r in rows:
        if not want or "%s:%d" % (r["set"], r["tile"]) in want:
            by[(r["plate"], r["page"])].append(r)
    for (plate, page), rs in by.items():
        pws, cells = pipeline.prepare_pages(CC.PDF[plate], [page], dpi=600)[0]
        for r in rs:
            c = next(c for c in cells if c.staff_index == r["staff"] and c.measure_index == r["measure"])
            grid = G._cell_grid(c); sp = grid[1] * 2
            res = SM.map_strokes(c.image_no_staff, sp, list(c.staff_line_ys_canonical), c.binary)
            img = c.image_no_staff
            x0, y0, x1, y1 = r["cbox"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            R = int(5 * sp)
            ax0, ay0 = int(max(0, cx - R)), int(max(0, cy - R)); ax1, ay1 = int(min(img.shape[1], cx + R)), int(min(img.shape[0], cy + R))
            tiles = []
            for mode in (0, 1):
                v = cv2.cvtColor(img[ay0:ay1, ax0:ax1].astype(np.uint8), cv2.COLOR_GRAY2BGR)
                if mode == 0:
                    cv2.rectangle(v, (int(x0 - ax0), int(y0 - ay0)), (int(x1 - ax0), int(y1 - ay0)), (0, 140, 255), 1)
                else:
                    for i, s in enumerate(res.strokes):
                        bx, by_, bw, bh = s.box
                        if bx + bw < ax0 or bx > ax1 or by_ + bh < ay0 or by_ > ay1:
                            continue
                        cv2.rectangle(v, (bx - ax0, by_ - ay0), (bx + bw - ax0, by_ + bh - ay0), COL[s.kind], 1)
                tiles.append(v)
            sheet = np.concatenate(tiles, axis=1)
            lab = "%s t%d %s p%d sean=%s" % (r["set"], r["tile"], plate, page, r["sean"])
            sheet = cv2.copyMakeBorder(sheet, 18, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            cv2.putText(sheet, lab, (2, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
            cv2.imwrite(os.path.join(out, "%s_t%02d.png" % (r["set"], r["tile"])), sheet)
