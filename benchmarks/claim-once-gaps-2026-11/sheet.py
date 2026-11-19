"""contact sheet of PNGs: python3 sheet.py DIR GLOB OUT COLS"""
import glob
import sys

import cv2
import numpy as np

d, pat, out, cols = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
H, W = 300, 420
ims = []
for f in sorted(glob.glob(d + "/" + pat)):
    im = cv2.imread(f)
    c = np.full((H, W, 3), 255, np.uint8)
    s = min(H / im.shape[0], W / im.shape[1], 1.0)
    im = cv2.resize(im, None, fx=s, fy=s)
    c[:im.shape[0], :im.shape[1]] = im
    cv2.putText(c, f.split("/")[-1][:40], (3, 11), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
    ims.append(c)
while len(ims) % cols:
    ims.append(np.full((H, W, 3), 255, np.uint8))
cv2.imwrite(out, np.vstack([np.hstack(ims[i:i + cols]) for i in range(0, len(ims), cols)]))
