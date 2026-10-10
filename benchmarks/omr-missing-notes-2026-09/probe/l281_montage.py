#!/usr/bin/env python3
"""l281_montage: a contact sheet of the tile directory, for the person cutting the tiles to LOOK at
them before sending (is the bracket on the head, is the stem's far end in the window). Writes
`montage_NN.png` beside the tiles; hidden fields are NOT printed on the image (only the tile id).

    python3 l281_montage.py --dir OUT_DIR [--per 12] [--cols 6] [--scale 0.5]
"""
import argparse
import sys
from pathlib import Path

import cv2
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--per", type=int, default=12)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = Path(a.dir)
    files = sorted(list(d.glob("tile_*.png")) + list(d.glob("control_*.png")))
    tiles = []
    for f in files:
        im = cv2.imread(str(f))
        im = cv2.resize(im, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_AREA)
        bar = np.full((18, im.shape[1], 3), 235, np.uint8)
        cv2.putText(bar, f.stem, (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(np.vstack([bar, im]))
    h = max(t.shape[0] for t in tiles)
    w = max(t.shape[1] for t in tiles)
    outd = Path(a.out) if a.out else d
    outd.mkdir(parents=True, exist_ok=True)
    for s in range(0, len(tiles), a.per):
        chunk = tiles[s:s + a.per]
        rows = []
        for j in range(0, len(chunk), a.cols):
            line = chunk[j:j + a.cols]
            line = [np.pad(t, ((0, h - t.shape[0]), (0, w - t.shape[1]), (0, 0)), constant_values=255) for t in line]
            while len(line) < a.cols:
                line.append(np.full((h, w, 3), 255, np.uint8))
            rows.append(np.hstack(line))
        p = outd / f"montage_{s // a.per:02d}.png"
        cv2.imwrite(str(p), np.vstack(rows))
        print("wrote", p)


if __name__ == "__main__":
    main()
