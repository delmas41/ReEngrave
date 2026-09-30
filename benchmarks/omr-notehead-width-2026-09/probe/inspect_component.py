import sys
import fitz
import numpy as np
from PIL import Image
from scipy import ndimage

pdf_path, x0, y0, x1, y1 = sys.argv[1], *map(float, sys.argv[2:6])
page = int(sys.argv[6])
doc = fitz.open(pdf_path)
pm = doc[page].get_pixmap(dpi=600)
im = Image.frombytes("RGB", (pm.width, pm.height), pm.samples).convert("L")
arr = np.asarray(im)
ink = arr < 128
cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
pad = 60
wx0, wx1 = int(x0 - pad), int(x1 + pad)
wy0, wy1 = int(y0 - pad), int(y1 + pad)
sub = ink[wy0:wy1, wx0:wx1]
lbl, n = ndimage.label(sub)
cyi, cxi = int(cy - wy0), int(cx - wx0)
lab = lbl[cyi, cxi]
print("centre pixel ink:", bool(sub[cyi, cxi]), "label", lab, "n_components", n)
if lab != 0:
    ys, xs = np.nonzero(lbl == lab)
    print("component bbox x", xs.min() + wx0, xs.max() + wx0,
         "y", ys.min() + wy0, ys.max() + wy0, "area", len(xs))
    print("component centroid", xs.mean() + wx0, ys.mean() + wy0)
