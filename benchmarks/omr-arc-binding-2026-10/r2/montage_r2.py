"""arcs-r2: stack the crops of a folder into sheets (cv2), N per sheet, each scaled to a common width.   python3 montage_r2.py DIR OUT_PREFIX [N=6] [WIDTH=900] [file ...]"""
import pathlib
import sys

import cv2
import numpy as np

d = pathlib.Path(sys.argv[1])
pre = sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
w = int(sys.argv[4]) if len(sys.argv) > 4 else 900
files = [d / f for f in sys.argv[5:]] or sorted(d.glob("*.png"))
for k in range(0, len(files), n):
    ims = []
    for f in files[k:k + n]:
        im = cv2.imread(str(f))
        if im is None:
            continue
        s = w / im.shape[1]
        ims.append(cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        ims.append(np.full((4, w, 3), 90, np.uint8))
    if ims:
        cv2.imwrite("%s-%02d.png" % (pre, k // n), np.vstack(ims))
        print("%s-%02d.png" % (pre, k // n))
