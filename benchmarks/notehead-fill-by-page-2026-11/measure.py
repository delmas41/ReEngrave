"""ROADMAP 2.326 small test (read-only, scratch): candidate fill measures cut straight from the page raster.

For every notehead box in work/pages-<doc>.json (frozen sample) and work/judged-<doc>.json (Sean's judged duration tiles),
render its page with the SAME shared reader the pipeline uses (`preprocessing.render_page`, 600 dpi, binarised + deskewed:
the frame of `bbox_page_px`), cut the head (Q.HEAD_INK's trimmed box where it has one, else the detector box) and measure:

  in_dark      ink share inside the head's inner ellipse (half its width and height), line rows left out
  hull_paper   paper share inside the convex hull of the head's own ink (line rows kept as ink)
  hole_paper   paper ENCLOSED by ink (filled holes) as a share of the head's filled outline
  hole_big     the largest single enclosed piece, as a share of the filled outline

Each is filed raw; the page-relative forms are computed later (analyse.py) against the page's own confidently-solid heads.
Writes work/measures-<doc>.json.  python3 benchmarks/notehead-fill-by-page-2026-11/measure.py litolff
"""
import json
import pathlib
import sys

import cv2
import numpy as np
from scipy import ndimage as nd

from tools.omr.preprocessing import render_page

W = pathlib.Path(__file__).parent / "work"
LIB = pathlib.Path("/Users/seanjohnson/Desktop/ReEngrave/library/editions")
PDF = {"litolff": LIB / "beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
       "brahms": LIB / "brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf"}


def head_box(h):
    hi = ((h.get("obs") or {}).get("head_ink") or {}).get("detail") or {}
    t = hi.get("trimmed")
    if isinstance(t, list) and len(t) == 4 and t[2] > t[0] and t[3] > t[1]:
        return [float(v) for v in t], "trimmed"
    b = h.get("bbox_page_px") or ((h.get("obs") or {}).get("glyph_box") or {}).get("detail", {}).get("bbox_page_px")
    return ([float(v) for v in b], "detector") if b else (None, None)


def line_rows(ink, y0, y1, x0, x1):
    """Rows of the head crop that a staff/ledger line crosses: ink across >= 80% of a window 1.5 head-widths either side."""
    w = x1 - x0
    H, Wd = ink.shape
    a, b = max(0, int(x0 - 1.5 * w)), min(Wd, int(x1 + 1.5 * w))
    rows = ink[y0:y1, a:b]
    left = ink[y0:y1, a:x0].mean(axis=1) if x0 > a else np.zeros(y1 - y0)
    right = ink[y0:y1, x1:b].mean(axis=1) if b > x1 else np.zeros(y1 - y0)
    return (left >= 0.8) & (right >= 0.8)


def measure(ink, box):
    x0, y0, x1, y1 = int(round(box[0])), int(round(box[1])), int(round(box[2])), int(round(box[3]))
    H, Wd = ink.shape
    if x0 < 0 or y0 < 0 or x1 > Wd or y1 > H or x1 - x0 < 5 or y1 - y0 < 5:
        return None
    c = ink[y0:y1, x0:x1]
    hh, ww = c.shape
    lr = line_rows(ink, y0, y1, x0, x1)
    yy, xx = np.mgrid[0:hh, 0:ww]
    ell = ((xx - (ww - 1) / 2) / (ww * 0.25)) ** 2 + ((yy - (hh - 1) / 2) / (hh * 0.25)) ** 2 <= 1.0
    m = ell & ~lr[:, None]
    in_dark = float(c[m].mean()) if m.any() else None
    pts = np.column_stack(np.nonzero(c))[:, ::-1].astype(np.int32)
    hull_paper = None
    if len(pts) >= 3:
        hull = cv2.convexHull(pts)
        mask = np.zeros_like(c, dtype=np.uint8)
        cv2.fillConvexPoly(mask, hull, 1)
        hm = mask.astype(bool)
        hull_paper = float((~c[hm]).mean()) if hm.any() else None
    pad = np.pad(c, 1)
    filled = nd.binary_fill_holes(pad)[1:-1, 1:-1]
    holes = filled & ~c
    area = filled.sum()
    lab, k = nd.label(holes)
    big = max((int((lab == i).sum()) for i in range(1, k + 1)), default=0)
    return {"in_dark": None if in_dark is None else round(in_dark, 4),
            "hull_paper": None if hull_paper is None else round(hull_paper, 4),
            "hole_paper": round(float(holes.sum()) / area, 4) if area else None,
            "hole_big": round(big / area, 4) if area else None,
            "line_rows": int(lr.sum()), "crop_hw": [hh, ww]}


def main(doc):
    groups = {}
    pages = json.load(open(W / ("pages-%s.json" % doc)))["heads"]
    for h in pages:
        groups.setdefault(int(h["subject"].split("/")[1]), []).append(("page", h))
    jp = W / ("judged-%s.json" % doc)
    if jp.exists():
        for h in json.load(open(jp))["heads"]:
            groups.setdefault(int(h["subject"].split("/")[1]), []).append(("judged", h))
    out = {}
    for p in sorted(groups):
        img = render_page(str(PDF[doc]), p, dpi=600)
        ink = np.asarray(img.binary) == 0
        del img
        for src, h in groups[p]:
            box, how = head_box(h)
            if box is None:
                continue
            r = measure(ink, box)
            if r is not None:
                out.setdefault(h["subject"], {**r, "box": [round(v, 1) for v in box], "box_from": how})
        print(doc, "page", p, len(groups[p]), flush=True)
        del ink
    json.dump(out, open(W / ("measures-%s.json" % doc), "w"))


if __name__ == "__main__":
    main(sys.argv[1])
