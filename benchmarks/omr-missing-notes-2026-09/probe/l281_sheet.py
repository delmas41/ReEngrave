#!/usr/bin/env python3
"""l281_sheet: contact sheets of scored page-0 members, CLEAN crops (a corner bracket on the head
and nothing else of ours), a one-line caption per tile -- to LOOK at whether the derived truth
verdict (`l281_score.py --json`) matches the print. A diagnostic for a reader of the print; the
verdict read off these sheets is the agent's, not Sean's (rule 7), and is labelled so.

    python3 l281_sheet.py --scored scored.json --out-dir DIR [--judge right,wrong_beam] [--per 16]
                          [--keys K1,K2] [--cell-prefix 9,10,11] [--scale 0.9]

`--cell-prefix` keeps heads whose staff index is in the list (the third number of the key).
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_view import PDF, page_rgb  # noqa: E402

SP = 32.0   # staff space in page px on this plate (l281_truth.Truth.space)


def tile(img, box, caption, sx=3.6, sy=6.5, scale=1.0, truth_rect=None, stem_rect=None):
    """`stem_rect` (Sean's stem box, if the head has one) only SIZES the window so the stem's far
    end (where a beam or flag hangs) is inside it; nothing of his is drawn."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    X0, X1 = int(cx - sx * SP), int(cx + sx * SP)
    Y0, Y1 = int(cy - sy * SP), int(cy + sy * SP)
    if stem_rect:
        Y0 = int(min(Y0, stem_rect[1] - 2.2 * SP))
        Y1 = int(max(Y1, stem_rect[3] + 2.2 * SP))
    H, W = img.shape[:2]
    pad = np.full((Y1 - Y0, X1 - X0, 3), 255, np.uint8)
    xa, ya, xb, yb = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
    pad[ya - Y0:yb - Y0, xa - X0:xb - X0] = img[ya:yb, xa:xb]
    # corner bracket on the head, 14 px arms
    bx0, by0, bx1, by1 = int(x0 - X0), int(y0 - Y0), int(x1 - X0), int(y1 - Y0)
    n = 12
    for (x, y, dx, dy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
        cv2.line(pad, (x, y), (x + dx * n, y), (220, 30, 30), 3)
        cv2.line(pad, (x, y), (x, y + dy * n), (220, 30, 30), 3)
    if scale != 1.0:
        pad = cv2.resize(pad, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    bar = np.full((22, pad.shape[1], 3), 245, np.uint8)
    cv2.putText(bar, caption, (3, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, pad])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--judge", default="right,wrong_beam,wrong_fill")
    ap.add_argument("--per", type=int, default=16)
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--scale", type=float, default=0.9)
    ap.add_argument("--cache", default=None)
    ap.add_argument("--keys", default=None)
    ap.add_argument("--staves", default=None, help="comma list of staff indices to keep")
    a = ap.parse_args()
    rows = json.loads(Path(a.scored).read_text())
    want = set(a.judge.split(","))
    rows = [r for r in rows if r["judge"] in want and r.get("page_box")]
    if a.keys:
        ks = set(a.keys.split(","))
        rows = [r for r in rows if r["key"] in ks]
    if a.staves:
        ss = {int(x) for x in a.staves.split(",")}
        rows = [r for r in rows if int(r["key"].split("/")[3]) in ss]
    img = page_rgb(PDF, a.cache)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tiles = []
    for i, r in enumerate(rows):
        cap = f"{i} {r['key'].replace('glyph/', 'g')} {r['tip'][:6]} {r['judge']} L{r.get('truth_levels')}"
        tiles.append(tile(img, r["page_box"], cap, scale=a.scale, stem_rect=r.get("truth_stem_rect")))
    h = max(t.shape[0] for t in tiles)
    w = max(t.shape[1] for t in tiles)
    for s in range(0, len(tiles), a.per):
        chunk = tiles[s:s + a.per]
        rws = []
        for j in range(0, len(chunk), a.cols):
            line = chunk[j:j + a.cols]
            line = [np.pad(t, ((0, h - t.shape[0]), (0, w - t.shape[1]), (0, 0)), constant_values=255) for t in line]
            while len(line) < a.cols:
                line.append(np.full((h, w, 3), 255, np.uint8))
            rws.append(np.hstack(line))
        sheet = np.vstack(rws)
        p = out / f"sheet_{s // a.per:02d}.png"
        cv2.imwrite(str(p), cv2.cvtColor(sheet, cv2.COLOR_RGB2BGR))
        print("wrote", p, sheet.shape)


if __name__ == "__main__":
    main()
