"""l283_scan_view: run the candidate shape reading (`l283_shape.read`) over EVERY stem end of a cached page of another plate
(no hand truth there), clip the window by the stem's own length (the head's edge is not available offline: far = min(FAR,
length - 0.7)), count the verdicts, and cut a montage of the erased rasters of the stems read as flags and of a sample of the
near-declines, tip row in red, for a look. ROADMAP 2.83 probe: QA by eye, not evidence of accuracy.

    python3 l283_scan_view.py CELLS.pkl.gz --out montage.png [--n 24] [--seed 1] [--which flag|decline|none]
"""
import argparse
import collections
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l283_common import cell_space, load_cells  # noqa: E402
import l283_shape as SH  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cells")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--which", default="flag")
    ap.add_argument("--why", default=None)
    a = ap.parse_args()
    cells = load_cells(a.cells)
    res = []
    for key, c in cells.items():
        s = cell_space(c)
        if not s:
            continue
        for i, (x, y, w, h) in enumerate(c["stems"]):
            L = h / s
            if L < 1.9:
                continue
            for end, tip_y, sign in (("top", y, 1.0), ("bottom", y + h, -1.0)):
                m = SH.read(c["img"], x, x + w, tip_y, sign, s, head_t=max(0.0, L - 0.7))
                res.append((key, i, end, m, c, (x, y, w, h), s))
    cnt = collections.Counter(m["v"] + ":" + m["why"] for *_a, m, _c, _b, _s in res)
    print(dict(cnt))
    pick = [r for r in res if r[3]["v"] == a.which and (a.why is None or r[3]["why"] == a.why)]
    random.Random(a.seed).shuffle(pick)
    tiles = []
    for key, i, end, m, c, (x, y, w, h), s in pick[:a.n]:
        tip_y, sign = (y, 1.0) if end == "top" else (y + h, -1.0)
        x0, x1 = int(x - 1.0 * s), int(x + w + 2.6 * s)
        ya, yb = sorted((tip_y - sign * 0.6 * s, tip_y + sign * 4.2 * s))
        ya, yb, x0 = max(0, int(ya)), int(yb), max(0, x0)
        sub = np.where(c["img"][ya:yb, x0:x1], 0, 255).astype(np.uint8)
        rgb = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
        ty = int(tip_y - ya)
        cv2.line(rgb, (0, ty), (rgb.shape[1] - 1, ty), (0, 0, 255), 1)
        rgb = cv2.resize(rgb, (150, 200), interpolation=cv2.INTER_AREA)
        rgb = cv2.copyMakeBorder(rgb, 0, 0, 0, 4, cv2.BORDER_CONSTANT, value=(0, 200, 0))
        cv2.putText(rgb, f"{key[0]}.{key[1]}.{key[2]}", (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 0, 0), 1)
        tiles.append(rgb)
    per = 12
    rows = []
    for k in range(0, len(tiles), per):
        r = tiles[k:k + per]
        while len(r) < per:
            r.append(np.full((200, 154, 3), 255, np.uint8))
        rows.append(np.concatenate(r, axis=1))
    cv2.imwrite(a.out, np.concatenate(rows, axis=0))
    print("wrote", a.out, len(tiles))


if __name__ == "__main__":
    main()
