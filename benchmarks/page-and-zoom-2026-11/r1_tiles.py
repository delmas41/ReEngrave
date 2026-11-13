"""ROADMAP 2.307 r1 -- 12 blind tiles for Sean on the row-vs-cells disagreement (filled noteheads only, pages other than Brahms p0).

    python3 benchmarks/page-and-zoom-2026-11/r1_tiles.py WORK_DIR OUT_DIR KEY.json [--seed 2307]

6 places where ONLY CELLS box a filled head and 6 where ONLY THE ROW does (same merge and matching as `t2_score.py`), drawn by seed from
both plates, no exclusions, shuffled. Each tile: the 600 dpi page (`render_page(...).binary`), the box's own staff (nearest by its lines) with
3 spaces above and below and about 6 spaces either side, one thin orange box exactly on the detector box, nothing else. Sheet: 3 x 4, big
numbers. The key is written OUTSIDE the tile folder.
"""
import os as _os
import sys as _sys
_sys.path.insert(0, _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..")))
_sys.path.insert(0, _os.path.dirname(__file__))

import glob
import json
import os
import random
import sys

import cv2
import numpy as np

from t2_crops import page_image  # noqa: E402
from t2_score import fam_boxes, iou, merged  # noqa: E402

QUESTION = "Is there a notehead in the orange box?"


def main():
    work, out, keyp = sys.argv[1], sys.argv[2], sys.argv[3]
    seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 2307
    pools = {"only_cells": [], "only_row": []}
    for f in sorted(glob.glob(os.path.join(work, "*.p*.json"))):
        d = json.load(open(f))
        if d["plate"] == "brahms" and d["page"] == 0:
            continue
        cells = [it["bbox"] for it in d["ways"]["cells"]["items"]]
        c = fam_boxes(merged(d["ways"]["cells"]["items"])).get("head_filled", [])
        r = fam_boxes(merged(d["ways"]["row"]["items"])).get("head_filled", [])
        for way, mine, other in (("only_cells", c, r), ("only_row", r, c)):
            for b in mine:
                if not any(iou(b[2:], o[2:]) >= 0.3 for o in other):
                    pools[way].append(dict(plate=d["plate"], page=d["page"], cls=b[0], conf=b[1], box=b[2:],
                                           staves=d["staves"], edges=sorted({e for cb in cells for e in (cb[0], cb[2])})))
    rng = random.Random(seed)
    picks = [dict(p, way=w) for w in ("only_cells", "only_row") for p in rng.sample(pools[w], 6)]
    rng.shuffle(picks)
    os.makedirs(out, exist_ok=True)
    key, tiles = [], []
    for n, p in enumerate(picks, 1):
        x0, y0, x1, y1 = p["box"]
        cy = (y0 + y1) / 2
        st = min(p["staves"].values(), key=lambda s: 0 if s["top"] <= cy <= s["bottom"] else min(abs(cy - s["top"]), abs(cy - s["bottom"])))
        sp = st["sp"]
        img = page_image(p["plate"], p["page"])
        T = int(min(st["top"] - 3 * sp, y0 - sp))
        B = int(max(st["bottom"] + 3 * sp, y1 + sp))
        L = int(min((x0 + x1) / 2 - 6 * sp, x0 - sp))
        R = int(max((x0 + x1) / 2 + 6 * sp, x1 + sp))
        T, L = max(0, T), max(0, L)
        B, R = min(img.shape[0], B), min(img.shape[1], R)
        t = img[T:B, L:R].copy()
        cv2.rectangle(t, (int(round(x0 - L)), int(round(y0 - T))), (int(round(x1 - L)), int(round(y1 - T))), (0, 140, 255), 2)
        assert T <= y0 and y1 <= B and L <= x0 and x1 <= R, "box cut by the tile edge"
        cv2.imwrite(os.path.join(out, "tile-%02d.png" % n), t)
        cx = (x0 + x1) / 2
        key.append(dict(tile=n, way=p["way"], plate=p["plate"], page=p["page"], page_box=[round(v, 1) for v in p["box"]], cls=p["cls"],
                        confidence=p["conf"], staff_space_px=round(sp, 1),
                        nearest_barline_spaces=round(min(abs(cx - e) for e in p["edges"]) / sp, 2)))
        h = 300
        w = int(t.shape[1] * h / t.shape[0])
        th = cv2.resize(t, (w, h), interpolation=cv2.INTER_AREA)
        canvas = np.full((h + 70, 460, 3), 255, np.uint8)
        if w > 460:
            th = cv2.resize(t, (460, int(t.shape[0] * 460 / t.shape[1])), interpolation=cv2.INTER_AREA)
        canvas[70:70 + th.shape[0], :th.shape[1]] = th[: h, :460]
        cv2.putText(canvas, str(n), (8, 58), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 220), 4)
        tiles.append(canvas)
    rows = [np.hstack(tiles[i:i + 3]) for i in range(0, 12, 3)]
    cv2.imwrite(os.path.join(out, "sheet.png"), np.vstack(rows))
    with open(os.path.join(out, "README.txt"), "w") as fh:
        fh.write("2.307 r1 -- 12 tiles. Question: %s\nEach tile shows one staff of the printed page; the thin orange box is the only "
                 "thing drawn. Answer per tile: yes / no / part of one (say which).\n" % QUESTION)
    json.dump(dict(question=QUESTION, seed=seed, pools={k: len(v) for k, v in pools.items()}, tiles=key), open(keyp, "w"), indent=1)
    print({k: len(v) for k, v in pools.items()})


if __name__ == "__main__":
    main()
