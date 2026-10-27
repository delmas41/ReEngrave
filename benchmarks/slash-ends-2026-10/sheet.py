"""usage: sheet.py P.pkl OUT.png [ncol]   crop around each case's box (cell px), covered non-vertical strokes tinted, box in orange."""
import pickle, sys
import cv2, numpy as np
recs = pickle.load(open(sys.argv[1], "rb"))
ncol = int(sys.argv[3]) if len(sys.argv) > 3 else 4
tiles = []
for r in recs:
    im = cv2.cvtColor(r["image"], cv2.COLOR_GRAY2BGR)
    x0, y0, x1, y1 = [int(v) for v in r["canon"]]
    sp = r["sp"]
    pad = int(1.5 * sp)
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - int(2.5 * sp)), min(im.shape[1], x1 + pad), min(im.shape[0], y1 + int(2.5 * sp))
    ov = im.copy()
    for s in r["strokes"]:
        if s["kind"] == "vertical" or s["share"] < 0.5:
            continue
        ov[s["mask"]] = (0, 0, 255) if s["kind"] != "blob" else (255, 120, 0)
    im = cv2.addWeighted(ov, 0.5, im, 0.5, 0)
    crop = im[Y0:Y1, X0:X1].copy()
    cv2.rectangle(crop, (x0 - X0, y0 - Y0), (x1 - X0, y1 - Y0), (0, 140, 255), 1)
    f = 260.0 / max(crop.shape[:2])
    crop = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_NEAREST)
    cv2.putText(crop, "%s %s" % (r["id"], str(r["label"])[:18]), (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 200), 1)
    can = np.full((270, 270, 3), 255, np.uint8)
    can[:crop.shape[0], :crop.shape[1]] = crop
    tiles.append(can)
while len(tiles) % ncol:
    tiles.append(np.full((270, 270, 3), 255, np.uint8))
rows = [np.hstack(tiles[i:i + ncol]) for i in range(0, len(tiles), ncol)]
cv2.imwrite(sys.argv[2], np.vstack(rows))
