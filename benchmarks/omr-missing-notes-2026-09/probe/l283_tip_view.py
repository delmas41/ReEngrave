"""l283_tip_view: the erased cell raster around the TIP of given truth stems (the pixels the reader sees), tip row in red,
0.5-space ticks down the left edge. Diagnostic only. ROADMAP 2.83 probe.

    python3 l283_tip_view.py CELLS.pkl.gz --out m.png stemid ...
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l283_common import cell_space  # noqa: E402
from l283_dataset import build  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=0.6)
    ap.add_argument("ids", nargs="+")
    a = ap.parse_args()
    T, cells, rows = build(a.cells)
    by = {r["stem"]: r for r in rows}
    tiles = []
    for sid in a.ids:
        r = by.get(sid)
        if r is None or r["cv"] is None:
            print(sid, "no CV stem")
            continue
        c = r["cv"]["cell"]
        s = cell_space(c)
        x, y, w, h = r["cv"]["stem"]
        tip_y, sign = (y, 1.0) if r["tip_end"] == "top" else (y + h, -1.0)
        x0, x1 = int(x - 1.0 * s), int(x + w + 2.6 * s)
        ya, yb = sorted((tip_y - sign * 0.6 * s, tip_y + sign * 4.2 * s))
        ya, yb, x0 = max(0, int(ya)), int(yb), max(0, x0)
        sub = np.where(c["img"][ya:yb, x0:x1], 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
        ty = int(tip_y - ya)
        cv2.line(rgb, (0, ty), (rgb.shape[1] - 1, ty), (0, 0, 255), 1)
        for k in range(1, 9):
            yy = int(ty + sign * k * 0.5 * s)
            if 0 <= yy < rgb.shape[0]:
                cv2.line(rgb, (0, yy), (10, yy), (0, 160, 0), 1)
        sx = int(x1 - x0 - 2.6 * s)
        cv2.line(rgb, (sx, 0), (sx, 6), (255, 0, 0), 1)
        rgb = cv2.resize(rgb, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
        rgb = cv2.copyMakeBorder(rgb, 0, 0, 0, 5, cv2.BORDER_CONSTANT, value=(0, 200, 0))
        tiles.append(rgb)
    H = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    cv2.imwrite(a.out, np.concatenate(tiles, axis=1))
    print("wrote", a.out)


if __name__ == "__main__":
    main()
