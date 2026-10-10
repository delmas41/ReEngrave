#!/usr/bin/env python3
"""l281_unmatched: for the page-0 members the matcher left without a truth head (`no_truth_head`) or
without a truth stem, print the record box beside the nearest truth head (IoU, centre offset in
spaces), so a mismatch caused by the MATCHER (a box a little off Sean's) is told from a record box
that is not a head at all.

    python3 l281_unmatched.py --scored scored.json
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from l281_truth import Truth, cx, cy  # noqa: E402


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / u if u > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scored", required=True)
    ap.add_argument("--judge", default="no_truth_head")
    a = ap.parse_args()
    T = Truth()
    rows = json.loads(Path(a.scored).read_text())
    for r in rows:
        if r["judge"] not in a.judge.split(","):
            continue
        b = r["page_box"]
        best = max(T.heads, key=lambda h: iou(b, h.rect))
        o = iou(b, best.rect)
        dx = (cx(b) - cx(best.rect)) / T.space
        dy = (cy(b) - cy(best.rect)) / T.space
        print(f"{r['key']:18s} {r['judge']:14s} tip={r['tip']:14s} box w,h={b[2]-b[0]:.0f},{b[3]-b[1]:.0f} "
              f"nearest truth head {best.id} cls={best.cls} iou={o:.2f} offset=({dx:+.2f},{dy:+.2f}) sp "
              f"truth w,h={best.rect[2]-best.rect[0]:.0f},{best.rect[3]-best.rect[1]:.0f}")


if __name__ == "__main__":
    main()
