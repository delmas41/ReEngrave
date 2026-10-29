"""2.222 cause: draw the black-notehead TRAINING labels of one version on its cell images (a look, not a count).
    python3 benchmarks/notehead-box-cap-2026-10/cause/label_look.py v4-2026-06-10-la-mer OUT.png
"""
import pathlib, sys
import cv2, numpy as np, yaml

ROOT = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/data/user-labeled")
names = yaml.safe_load((ROOT / "catalog.yaml").read_text())["names"]
HEAD = {i for i, n in enumerate(names) if n.startswith("noteheadBlack")}
v = ROOT / sys.argv[1]
tiles = []
for lab in sorted((v / "labels").glob("*.txt")):
    rows = [l.split() for l in lab.read_text().splitlines() if l.strip()]
    rows = [r for r in rows if int(r[0]) in HEAD]
    if len(rows) < 3:
        continue
    p = next((v / "images" / (lab.stem + e) for e in (".png", ".jpg") if (v / "images" / (lab.stem + e)).exists()), None)
    if p is None:
        continue
    im = cv2.imread(str(p)); H, W = im.shape[:2]
    for r in rows:
        cx, cy, w, h = [float(x) for x in r[1:5]]
        cv2.rectangle(im, (int((cx - w / 2) * W), int((cy - h / 2) * H)), (int((cx + w / 2) * W), int((cy + h / 2) * H)), (0, 0, 255), 3)
    s = 600 / H
    tiles.append(cv2.resize(im, (int(W * s), 600)))
    if len(tiles) == 4:
        break
w = sum(t.shape[1] for t in tiles)
cv2.imwrite(sys.argv[2], np.hstack(tiles) if w < 6000 else np.hstack(tiles[:2]))
