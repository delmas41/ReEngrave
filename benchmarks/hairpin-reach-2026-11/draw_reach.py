"""ROADMAP 2.254 lane look: draw reach_count.py's finds on the page (green = OFF and ON, blue = ON only), or crop one region.

    python3 benchmarks/hairpin-reach-2026-11/draw_reach.py DIR brahms 5            # DIR/brahms_p05_reach.png
    python3 benchmarks/hairpin-reach-2026-11/draw_reach.py DIR brahms 5 x0 y0 x1 y1  # DIR/brahms_p05_crop.png (page px)
"""
import json
import pathlib
import sys

import cv2
import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import probe_misses as P  # noqa: E402

from tools.omr.staged import cell_map  # noqa: E402


def main(d, plate, pg, region=None):
    (pws, _c), = cell_map.load_prepared(P.C.EDITIONS[plate][0], [pg])
    img = cv2.cvtColor(pws.page.binary.astype(np.uint8), cv2.COLOR_GRAY2BGR)
    res = json.loads((d / ("%s_p%02d_reach.json" % (plate, pg))).read_text())
    offs = {tuple(r["bbox"]) for r in res["off"]}
    for r in res["on"]:
        b = r["bbox"]
        col = (0, 160, 0) if tuple(b) in offs else (230, 90, 0)
        cv2.rectangle(img, (b[0] - 4, b[1] - 4), (b[2] + 4, b[3] + 4), col, 3)
    if region:
        x0, y0, x1, y1 = region
        cv2.imwrite(str(d / ("%s_p%02d_crop.png" % (plate, pg))), img[y0:y1, x0:x1])
    else:
        cv2.imwrite(str(d / ("%s_p%02d_reach.png" % (plate, pg))), cv2.resize(img, None, fx=0.3, fy=0.3, interpolation=cv2.INTER_AREA))


if __name__ == "__main__":
    a = sys.argv
    main(pathlib.Path(a[1]), a[2], int(a[3]), [int(v) for v in a[4:8]] if len(a) > 7 else None)
