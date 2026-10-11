#!/usr/bin/env python3
"""l282_montage: a contact sheet of strokes the 2.74 thickness cut refuses (median < 1.75 lines) that a
thick PLATEAU says may hold a beam, each cut from the page raster (600 dpi, the gather's own) with the
stroke's box outlined (CV blue, detector red) and its numbers printed under it. ROADMAP 2.82. A reading
probe: the sheet is for the agent's eye (and the findings' crops), never Sean's blind tiles.

    python3 l282_montage.py --ext ext.json --prof prof.json --pdf brahms --key pl2 --min 2.0 --n 24 \
        --seed 282 --out sheet.png [--max-median 1.75] [--ids a,b,c]
"""
import argparse
import json
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_tiles import PDFS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--prof", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--key", default="pl2")
    ap.add_argument("--min", type=float, default=2.0)
    ap.add_argument("--max", type=float, default=None, help="upper bound on --key")
    ap.add_argument("--max-median", type=float, default=1.75)
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--seed", type=int, default=282)
    ap.add_argument("--ids", default=None)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--width", type=float, default=360.0, help="tile width in px")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    prof = json.load(open(a.prof))
    where = {}
    for ck, ss in ext["strokes"].items():
        calib = ext["calib"].get(ck)
        if not calib:
            continue
        x0, y0, up = calib[:3]
        for sid, s in ss.items():
            bx, by, bw, bh = s["box"][:4]
            where[sid] = (int(ck.split("/")[1]), (x0 + bx / up, y0 + by / up, x0 + (bx + bw) / up, y0 + (by + bh) / up),
                          s["reader"], ck)
    if a.ids:
        sel = [i for i in a.ids.split(",") if i in prof and i in where]
    else:
        pool = [k for k, p in prof.items() if k in where and p["rec_ratio"] is not None
                and p["rec_ratio"] < a.max_median and p[a.key] >= a.min
                and (a.max is None or p[a.key] < a.max)]
        pool.sort()
        print(f"pool: {len(pool)} strokes with median < {a.max_median} and {a.key} in [{a.min}, {a.max}]")
        rng = random.Random(a.seed)
        sel = rng.sample(pool, min(a.n, len(pool)))
    from tools.omr.preprocessing import render_page
    cache = {}
    tiles = []
    for sid in sel:
        page, pb, reader, ck = where[sid]
        if page not in cache:
            if len(cache) > 1:
                cache.pop(next(iter(cache)))
            cache[page] = render_page(PDFS[a.pdf], page, dpi=600).rgb
        img = cache[page]
        p = prof[sid]
        sp = p["space_page"]
        X0, X1 = int(pb[0] - 1.5 * sp), int(pb[2] + 1.5 * sp)
        Y0, Y1 = int(pb[1] - 3.0 * sp), int(pb[3] + 3.0 * sp)
        # cap the tile width at 26 spaces around the stroke's centre; the strokes are up to 20 spaces wide
        crop = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8)
        xa, ya, xb, yb = max(0, X0), max(0, Y0), min(img.shape[1], X1), min(img.shape[0], Y1)
        crop[ya - Y0:yb - Y0, xa - X0:xb - X0] = img[ya:yb, xa:xb]
        f = a.width / max(crop.shape[1], 1)
        f = min(f, 1.6)
        crop = cv2.resize(crop, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        col = (255, 0, 0) if reader == "detector" else (0, 90, 255)
        cv2.rectangle(crop, (int((pb[0] - X0) * f), int((pb[1] - Y0) * f)), (int((pb[2] - X0) * f), int((pb[3] - Y0) * f)), col, 1)
        cap = f"{sid} p{page} {reader[:3]} med {p['rec_ratio']} pl2 {p['pl2']} run2 {p['run2']}sp w {p['w_sp']}sp"
        h = crop.shape[0] + 16
        tile = np.full((h, max(crop.shape[1], int(a.width)), 3), 255, np.uint8)
        tile[:crop.shape[0], :crop.shape[1]] = crop
        cv2.putText(tile, cap, (2, h - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(tile)
    rows = []
    for i in range(0, len(tiles), a.cols):
        grp = tiles[i:i + a.cols]
        H = max(t.shape[0] for t in grp)
        rows.append(np.hstack([np.pad(t, ((0, H - t.shape[0]), (0, 4), (0, 0)), constant_values=200) for t in grp]))
    W = max(r.shape[1] for r in rows)
    sheet = np.vstack([np.pad(r, ((0, 4), (0, W - r.shape[1]), (0, 0)), constant_values=200) for r in rows])
    cv2.imwrite(a.out, cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
    print("->", a.out, sheet.shape, "ids:", ",".join(sel))


if __name__ == "__main__":
    main()
