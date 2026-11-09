import sys, cv2, numpy as np
from pathlib import Path
src = Path(sys.argv[1]); out = sys.argv[2]; cols = int(sys.argv[3]) if len(sys.argv) > 3 else 3
files = sorted(src.glob("tile_*.png"))
ims = []
for f in files:
    im = cv2.imread(str(f))
    s = 420.0 / max(im.shape[0], im.shape[1]); im = cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA)
    cv2.putText(im, f.stem[-2:], (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 128, 0), 1)
    ims.append(im)
H = max(i.shape[0] for i in ims); W = max(i.shape[1] for i in ims)
rows = []
for i in range(0, len(ims), cols):
    row = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, W - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in ims[i:i + cols]]
    while len(row) < cols: row.append(np.full((H, W, 3), 255, np.uint8))
    rows.append(np.hstack(row))
cv2.imwrite(out, np.vstack(rows)); print(np.vstack(rows).shape)
