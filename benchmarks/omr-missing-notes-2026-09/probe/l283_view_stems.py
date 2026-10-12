"""l283_view_stems: crops of the page-0 print around given truth item ids with Sean's boxes drawn (stem orange, notehead
green, beam magenta, flag blue). Diagnostic only. ROADMAP 2.83 probe.

    python3 l283_view_stems.py --cache p0_rgb.npy --out m.png id1 id2 ...
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_truth import Truth  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pad", type=int, default=100)
    ap.add_argument("--scale", type=float, default=0.9)
    ap.add_argument("ids", nargs="+")
    a = ap.parse_args()
    T = Truth()
    img = np.load(a.cache)
    by = {i.id: i for i in T.items}
    tiles = []
    for i in a.ids:
        r = by[i].rect
        x0, y0, x1, y1 = [int(v) for v in r]
        ya, yb, xa, xb = y0 - a.pad, y1 + a.pad, x0 - a.pad, x1 + a.pad + 30
        crop = img[max(0, ya):yb, max(0, xa):xb].copy()
        xa, ya = max(0, xa), max(0, ya)
        for it in T.items:
            rr = it.rect
            if rr[2] < xa or rr[0] > xb or rr[3] < ya or rr[1] > yb:
                continue
            fam = "stem" if it.cls == "stem" else it.family
            col = {"stem": (255, 120, 0), "beam": (255, 0, 255), "flag": (0, 0, 255), "notehead": (0, 170, 0)}.get(fam)
            if col is None:
                continue
            th = 2 if it.id == i else 1
            cv2.rectangle(crop, (int(rr[0] - xa), int(rr[1] - ya)), (int(rr[2] - xa), int(rr[3] - ya)), col, th)
        crop = cv2.resize(crop, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
        tiles.append(crop)
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 6, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    m = np.concatenate(tiles, axis=1)
    cv2.imwrite(a.out, cv2.cvtColor(m, cv2.COLOR_RGB2BGR))
    print(m.shape)


if __name__ == "__main__":
    main()
