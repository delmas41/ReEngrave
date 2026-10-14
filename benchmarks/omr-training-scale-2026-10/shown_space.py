"""ROADMAP 2.110 Step A.5 -- the staff space the model is SHOWN, from one tool.

measure_space(img): staff space in pixels of an image, from the image alone (row-ink projection: the five staff
lines are the rows whose dark fraction stands far above the rest; the space is the median gap between adjacent line
rows). It is the same function for a canonical cell, a cell after ultralytics' load-time resize, and a cell at the
size the product's detector is given at inference -- so training and inference come out of one ruler.

Cross-checked against the cell's own recorded `staff_line_ys_canonical` where the metadata has them (cells.json).
"""
from __future__ import annotations

import cv2
import numpy as np


def measure_space(img: np.ndarray):
    """Staff space in pixels of `img` (BGR or gray) by a 5-line COMB fit on the row-darkness profile: choose spacing d
    and first-line row y0 maximising  mean(profile at y0+k*d, k=0..4) - mean(profile at the 5 half-way rows).
    Uses darkness (255-gray), not a threshold, so a downscaled image whose lines are gray hairlines is measured by
    the same code as a canonical cell. Returns (space_px, comb_score) or None if the comb has no contrast."""
    g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h = g.shape[0]
    if h < 20:
        return None
    prof = (255.0 - g.astype(np.float32)).mean(axis=1) / 255.0
    ys = np.arange(h, dtype=np.float32)
    best = (0.0, None)
    for d in np.arange(2.5, (h - 2) / 4.2, 0.25):
        n = int(h - 4 * d)
        if n < 1:
            break
        y0 = np.arange(0, n, 0.5, dtype=np.float32)
        on = np.zeros_like(y0)
        off = np.zeros_like(y0)
        for k in range(5):
            on += np.interp(y0 + k * d, ys, prof)
        for k in range(4):
            off += np.interp(y0 + (k + 0.5) * d, ys, prof)
        sc = on / 5.0 - off / 4.0
        j = int(sc.argmax())
        if sc[j] > best[0]:
            best = (float(sc[j]), (float(d), float(y0[j])))
    if best[1] is None or best[0] < 0.02:
        return None
    return best[1][0], best[0]
