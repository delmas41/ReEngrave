"""Render a page of a score PDF at 600 dpi (grayscale, cached as .npy in out/2.278-micro/) and crop with thin boxes."""
import os
from pathlib import Path
import numpy as np
import cv2
import fitz

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "out/2.278-micro"
LIB = "/Users/seanjohnson/Desktop/ReEngrave/library/editions"
PDFS = {
    "brahms": LIB + "/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}


def page_image(pdf, page, dpi=600):
    tag = Path(pdf).stem[-20:] + f"_p{page}_{dpi}.npy"
    f = CACHE / tag
    if f.exists():
        return np.load(f)
    doc = fitz.open(pdf)
    pm = doc[page].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), colorspace=fitz.csGRAY)
    a = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width).copy()
    CACHE.mkdir(parents=True, exist_ok=True)
    np.save(f, a)
    return a


def crop(img, x0, y0, x1, y1, boxes=(), pad=0, scale=0.5, color=(0, 0, 255), thick=2):
    """crop [x0,y0,x1,y1] (page px) with `pad`, draw each rect in `boxes` (page px) thin; return BGR image scaled."""
    h, w = img.shape
    X0, Y0, X1, Y1 = int(max(0, x0 - pad)), int(max(0, y0 - pad)), int(min(w, x1 + pad)), int(min(h, y1 + pad))
    c = cv2.cvtColor(img[Y0:Y1, X0:X1], cv2.COLOR_GRAY2BGR)
    for b in boxes:
        r = b["rect"] if isinstance(b, dict) else b
        col = b.get("color", color) if isinstance(b, dict) else color
        cv2.rectangle(c, (int(r[0] - X0), int(r[1] - Y0)), (int(r[2] - X0), int(r[3] - Y0)), col, thick)
    if scale != 1:
        c = cv2.resize(c, (max(1, int(c.shape[1] * scale)), max(1, int(c.shape[0] * scale))), interpolation=cv2.INTER_AREA)
    return c
