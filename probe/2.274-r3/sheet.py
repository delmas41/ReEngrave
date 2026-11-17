"""python3 sheet.py NAME N N N ... : stack look/P<N>.png vertically into look/NAME.png (make them first with look.py)"""
import sys
import cv2
import numpy as np

name = sys.argv[1]
ims = [cv2.imread("look/P%s.png" % n) for n in sys.argv[2:]]
W = max(i.shape[1] for i in ims)
rows = []
for i in ims:
    pad = np.full((i.shape[0], W - i.shape[1], 3), 255, np.uint8)
    rows.append(np.hstack([i, pad]))
    rows.append(np.full((6, W, 3), 0, np.uint8))
cv2.imwrite("look/%s.png" % name, np.vstack(rows))
print(np.vstack(rows).shape)
