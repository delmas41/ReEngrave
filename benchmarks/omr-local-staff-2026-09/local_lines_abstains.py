"""lane-local-staff-lines probe: montage of fits the new read ABSTAINED on (old red, global green).
  python3 local_lines_abstains.py <scratch dir> <audit.json> <doc> <out.png> [n]"""
import json, sys, random
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import cv2, numpy as np
import offbox_measured as OM

S, aj, doc, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
n = int(sys.argv[5]) if len(sys.argv) > 5 else 12
data = json.load(open(S / "x" / f"{doc}-20261006-night-combined.json"))
rows = json.load(open(aj))["rows"]
cand = [(r, k, v) for r in rows for k, v in r["cand"].items() if v["new_flag"]]
random.Random(7).shuffle(cand)
rep = OM.CachedReplay(doc, data)
tiles = []
for r, k, v in cand[:n]:
    g = rep.gray_of(r["page"])
    x0, y0, x1, y1 = r["box"]
    ys = v["gl"] + (v["old"] or [])
    Y0, Y1 = int(min(ys + [y0]) - 25), int(max(ys + [y1]) + 25)
    X0, X1 = int(x0 - 90), int(x1 + 90)
    im = cv2.cvtColor(g[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    sc = 3
    im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    for y in v["old"]:
        cv2.line(im, (0, int((y - Y0) * sc)), (im.shape[1], int((y - Y0) * sc)), (0, 0, 255), 1)
    for y in v["gl"]:
        cv2.line(im, (0, int((y - Y0) * sc) + 3), (im.shape[1], int((y - Y0) * sc) + 3), (0, 160, 0), 1)
    cv2.rectangle(im, (int((x0 - X0) * sc), int((y0 - Y0) * sc)), (int((x1 - X0) * sc), int((y1 - Y0) * sc)), (0, 140, 255), 2)
    cv2.putText(im, "%s %s %s old=%s why=%s" % (r["subject"], k[-5:], "own" if k == r["own"] else "nb", v["old_flag"], v["why"]),
                (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 200), 1)
    tiles.append(im)
W = max(t.shape[1] for t in tiles)
rowsimg = []
for i in range(0, len(tiles), 3):
    grp = tiles[i:i + 3]
    h = max(t.shape[0] for t in grp)
    rowsimg.append(np.hstack([cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in grp]))
Wm = max(r_.shape[1] for r_ in rowsimg)
cv2.imwrite(out, np.vstack([cv2.copyMakeBorder(r_, 0, 6, 0, Wm - r_.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for r_ in rowsimg]))
print("wrote", out, len(cand))
