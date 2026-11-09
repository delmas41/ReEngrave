"""stack crops into sheets: python3 stack.py OUT.png W IMG [IMG ...]   (each image scaled to width W, stacked vertically)"""
import sys

import cv2
import numpy as np

out, w = sys.argv[1], int(sys.argv[2])
ims = []
for p in sys.argv[3:]:
    im = cv2.imread(p)
    s = w / im.shape[1]
    ims.append(cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
    ims.append(np.full((6, w, 3), 90, np.uint8))
cv2.imwrite(out, np.vstack(ims))
