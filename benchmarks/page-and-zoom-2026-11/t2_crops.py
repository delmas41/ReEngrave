"""ROADMAP 2.307 T2 -- crops of the 20 seeded "only this way" boxes per way, for the manager (LEADS, never called right or wrong).

    python3 benchmarks/page-and-zoom-2026-11/t2_crops.py LEADS.json OUT_DIR

Each crop: 6 staff spaces around the box (about), the box drawn in orange, nothing else. Names: <way>-<nn>-<plate>p<page>-<class>.png, and a
sheet per way.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))

import json
import os
import sys

import cv2
import numpy as np

ROOT = "/Users/seanjohnson/Desktop/ReEngrave/"
PDF = {
    "litolff": "library/editions/beethoven/symphony-5-op67/beethoven--symphony-5-op67--henry-litolff-s-verlag-1870--imslp984073.pdf",
    "brahms": "library/editions/brahms/symphony-1-op68/brahms--symphony-1-op68--breitkopf-hartel-brahms--imslp317803.pdf",
}


def page_image(plate, page, cache={}):
    k = (plate, page)
    if k not in cache:
        from tools.omr.preprocessing import render_page
        img = np.asarray(render_page(ROOT + PDF[plate], page, dpi=600).binary)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cache[k] = img
    return cache[k]


def main():
    leads, out = json.load(open(sys.argv[1])), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for way, lst in leads.items():
        tiles = []
        for n, L in enumerate(lst):
            plate, page = L["page"].split("/")
            img = page_image(plate, int(page))
            x0, y0, x1, y1 = [int(round(v)) for v in L["box"]]
            pad = 160
            X0, Y0 = max(0, x0 - pad), max(0, y0 - pad)
            X1, Y1 = min(img.shape[1], x1 + pad), min(img.shape[0], y1 + pad)
            c = img[Y0:Y1, X0:X1].copy()
            cv2.rectangle(c, (x0 - X0, y0 - Y0), (x1 - X0, y1 - Y0), (0, 140, 255), 2)
            name = "%s-%02d-%sp%s-%s.png" % (way, n + 1, plate, page, L["cls"])
            cv2.imwrite(os.path.join(out, name), c)
            t = cv2.resize(c, (240, 240))
            cv2.putText(t, str(n + 1), (4, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            tiles.append(t)
        while len(tiles) % 5:
            tiles.append(np.full((240, 240, 3), 255, np.uint8))
        rows = [np.hstack(tiles[i:i + 5]) for i in range(0, len(tiles), 5)]
        if rows:
            cv2.imwrite(os.path.join(out, "sheet-%s.png" % way), np.vstack(rows))


if __name__ == "__main__":
    main()
