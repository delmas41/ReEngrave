#!/usr/bin/env python3
"""l282_celllook: every stroke filed in one record cell (and its neighbours' overlap on the page), with
its ink reading, drawn on the 600 dpi page crop around a named head: the head's box in GREEN, CV strokes
BLUE, detector strokes RED. ROADMAP 2.82. A reading probe.

    python3 l282_celllook.py --ext ext.json --pdf brahms|litolff --page 20 --head "2156,3563,2193,3596" --out x.png
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402

from l281_tiles import PDFS  # noqa: E402
from l282_beamlook import strokes_page  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", required=True)
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--head", required=True, help="x0,y0,x1,y1 page px")
    ap.add_argument("--sp", type=float, default=27.5)
    ap.add_argument("--halfw", type=float, default=7.0)
    ap.add_argument("--up", type=float, default=7.0, help="spaces above the head")
    ap.add_argument("--down", type=float, default=3.0, help="spaces below the head")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ext = json.load(open(a.ext))
    hb = [float(v) for v in a.head.split(",")]
    sp = a.sp
    cx = (hb[0] + hb[2]) / 2
    X0, X1 = int(cx - a.halfw * sp), int(cx + a.halfw * sp)
    Y0, Y1 = int(hb[1] - a.up * sp), int(hb[3] + a.down * sp)
    from tools.omr.preprocessing import render_page
    img = render_page(PDFS[a.pdf], a.page, dpi=600).rgb
    crop = img[max(0, Y0):Y1, max(0, X0):X1].copy()
    ox, oy = max(0, X0), max(0, Y0)
    for s in strokes_page(ext, a.page):
        pb = s["pb"]
        if pb[2] < X0 or pb[0] > X1 or pb[3] < Y0 or pb[1] > Y1:
            continue
        i = s["ink"] or {}
        print(f"{s['id']:12s} {s['reader']:9s} {s['cell']} box {[round(v) for v in pb]} "
              f"({pb[2]-pb[0]:.0f}x{pb[3]-pb[1]:.0f}) ratio={i.get('thickness_ratio')} thick={i.get('thickness_px')} "
              f"line={i.get('line_px')} sag={i.get('sagitta_spaces')} "
              f"ends={[e.get('found') for e in (i.get('end_stems') or [])]} cover={i.get('cover')}"
              f"{(' ABSTAINED ' + str(s['ab'])) if s['ab'] else ''}")
        col = (255, 0, 0) if s["reader"] == "detector" else (0, 90, 255)
        cv2.rectangle(crop, (int(pb[0] - ox), int(pb[1] - oy)), (int(pb[2] - ox), int(pb[3] - oy)), col, 2)
    cv2.rectangle(crop, (int(hb[0] - ox), int(hb[1] - oy)), (int(hb[2] - ox), int(hb[3] - oy)), (0, 170, 0), 2)
    cv2.imwrite(a.out, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
    print("->", a.out)


if __name__ == "__main__":
    main()
