"""render Brahms p0 at 600 dpi once (cached as a png) and crop helpers"""
import pathlib
import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
PNG = HERE / "p0_600.png"
PDF = "/Users/seanjohnson/Desktop/ReEngrave/library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"


def page():
    if not PNG.exists():
        import fitz
        d = fitz.open(PDF)
        pix = d[0].get_pixmap(dpi=600, colorspace=fitz.csGRAY)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        cv2.imwrite(str(PNG), img)
    return cv2.imread(str(PNG), 0)


def crop(img, box, pad=60, scale=0.5):
    x0, y0, x1, y1 = [int(v) for v in box]
    H, W = img.shape
    a, b, c, d = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    return cv2.cvtColor(img[b:d, a:c], cv2.COLOR_GRAY2BGR), (a, b)
