"""ROADMAP 2.193: a look sheet of target inks (shape says natural, natural not offered) cut from the cell raster, stratified by the natural score.
usage: natural_crops_2_193.py cause.json OUT.png [seed] [n_per_plate]   (a model's own look, rule 7 -- NOT blind evidence)"""
import json, random, sys
import numpy as np, cv2
from tools.omr.staged import lane_report as LR
from tools.omr.staged.pipeline import prepare_pages
R = json.load(open(sys.argv[1])); out = sys.argv[2]; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1; n = int(sys.argv[4]) if len(sys.argv) > 4 else 8
rng = random.Random(seed); sample = LR.load_sample(); tiles = []; meta = []
for plate in ("litolff", "brahms"):
    tg = [r for r in R[plate] if r["shape"] == "natural" and not r["has_natural"]]
    hi = [r for r in tg if r["nat_max"] >= 0.05]; lo = [r for r in tg if r["nat_max"] < 0.05]
    pick = rng.sample(hi, min(n // 2, len(hi))) + rng.sample(lo, min(n - n // 2, len(lo)))
    pdf = str(LR.LIB / LR.PLATES[plate]["pdf"]); pages = sorted({r["page"] for r in pick})
    want = {(tuple(r["cell"]), r["gi"]): r for r in pick}
    for pws, cells in prepare_pages(pdf, pages):
        for c in cells:
            for (cell, gi), r in want.items():
                bb = getattr(c, "bbox_page_px", None)
                if bb and c.page_index == int(cell[0]) and all(abs(a - b) < 1.5 for a, b in zip(r["bbox_page_px"], bb)):
                    x0, y0, x1, y1 = [int(v) for v in r["bbox"]]; h = y1 - y0
                    img = c.image if c.image.ndim == 2 else cv2.cvtColor(c.image, cv2.COLOR_BGR2GRAY)
                    crop = img[max(0, y0 - h): y1 + h, max(0, x0 - 2 * h): x1 + 3 * h]
                    crop = cv2.cvtColor(cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC), cv2.COLOR_GRAY2BGR)
                    bx = (3 * (x0 - max(0, x0 - 2 * h)), 3 * (y0 - max(0, y0 - h)), 3 * (x1 - max(0, x0 - 2 * h)), 3 * (y1 - max(0, y0 - h)))
                    cv2.rectangle(crop, bx[:2], bx[2:], (0, 140, 255), 1)
                    tiles.append(crop); meta.append((plate, r["page"], r["cls"], r["nat_max"]))
W = 360; H = 240; cols = 4; rows = (len(tiles) + cols - 1) // cols
sheet = np.full((rows * (H + 24), cols * W, 3), 255, np.uint8)
for i, t in enumerate(tiles):
    t = cv2.resize(t, None, fx=min(W / t.shape[1], H / t.shape[0]), fy=min(W / t.shape[1], H / t.shape[0]))
    r_, c_ = divmod(i, cols); y = r_ * (H + 24); x = c_ * W
    sheet[y + 24: y + 24 + t.shape[0], x: x + t.shape[1]] = t
    cv2.putText(sheet, "%d %s p%d nat%.2f" % (i + 1, meta[i][0][:3], meta[i][1], meta[i][3]), (x + 4, y + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
cv2.imwrite(out, sheet); print(len(tiles)); [print(i + 1, m) for i, m in enumerate(meta)]
