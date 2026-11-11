"""2.294: my own crop look at sites (rule 7: a look, NOT evidence). Ink drawn black on white from the 2.293 canvas, thin orange box on the site, a small caption
(plate page pair class refused). usage: look.py SCRATCH OUT.png SEED N CLASSES [PAIRFILTER]"""
import json, sys, random, pathlib
import numpy as np, cv2
d = pathlib.Path(sys.argv[1]); out = sys.argv[2]; seed = int(sys.argv[3]); n = int(sys.argv[4]); classes = sys.argv[5]
pf = sys.argv[6] if len(sys.argv) > 6 else ""
sites = [s for s in json.load(open(d / "sites.json")) if s["scope"] == "test" and s["class"] in classes and pf in ("%s x %s " % tuple(s["pair"]) + " ".join(s["refused"]))]
random.Random(seed).shuffle(sites)
sites = sites[:n]
tiles = []
cache = {}
for s in sites:
    key = (s["plate"], s["page"])
    if key not in cache:
        cache.clear()
        cache[key] = np.load(d / "off" / ("%s.p%d.npz" % key))["ink"]
    ink = cache[key]
    x0, y0, x1, y1 = s["bbox"]
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    R = 90
    X0, Y0 = max(0, cx - R), max(0, cy - R)
    im = np.where(ink[Y0:Y0 + 2 * R, X0:X0 + 2 * R], 0, 255).astype(np.uint8)
    im = np.pad(im, ((0, 2 * R - im.shape[0]), (0, 2 * R - im.shape[1])), constant_values=255)
    im = cv2.cvtColor(cv2.resize(im, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST), cv2.COLOR_GRAY2BGR)
    cv2.rectangle(im, (2 * (x0 - X0) - 2, 2 * (y0 - Y0) - 2), (2 * (x1 - X0) + 2, 2 * (y1 - Y0) + 2), (0, 140, 255), 1)
    cap = "%d %s p%d %s-%s %s %s" % (len(tiles) + 1, s["plate"][:2], s["page"], s["pair"][0][:5], s["pair"][1][:5], s["class"], ",".join(sorted(set(s["refused"])))[:34])
    cv2.putText(im, cap, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 200), 1)
    tiles.append(im)
cols = 4
rows = [np.hstack(tiles[i:i + cols] + [np.full_like(tiles[0], 255)] * (cols - len(tiles[i:i + cols]))) for i in range(0, len(tiles), cols)]
cv2.imwrite(out, np.vstack(rows))
print(len(tiles), "tiles")
for i, s in enumerate(sites):
    print(i + 1, s["plate"], s["page"], s["pair"], s["class"], s["bbox"], s["refused"], s["none_px"])
