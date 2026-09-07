"""Crop one system's left edge into a legible strip, for a human to read.

A system's left edge is ~30-100 px wide and 1500-7000 px tall, so it cannot be
shown at its own aspect.  This slices it into N equal chunks and lays them side
by side with a grey separator, keeping every pixel at its own scale.

    crop_left_edge.py PDF --page 2 --system 0 --out out/crops/foo.png
"""
from __future__ import annotations

import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import cv2                                              # noqa: E402
import numpy as np                                      # noqa: E402
from tools.omr.preprocessing import render_page         # noqa: E402
from tools.omr.staff_detector import detect_staves      # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, required=True)
    ap.add_argument("--system", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--left", type=float, default=14.0, help="spacings left of anchor")
    ap.add_argument("--right", type=float, default=6.0)
    ap.add_argument("--chunks", type=int, default=4)
    ap.add_argument("--scale", type=float, default=2.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    staves = sorted(detect_staves(pi).staves, key=lambda s: s.top_y)
    members = [s for s in staves if s.system_index == args.system]
    if not members:
        raise SystemExit(f"no system {args.system}; "
                         f"have {sorted({s.system_index for s in staves})}")
    sp = statistics.median([s.line_spacing_px for s in members])
    anchor = statistics.median([s.x_start for s in members])
    x0 = max(0, int(anchor - args.left * sp))
    x1 = min(pi.binary.shape[1], int(anchor + args.right * sp))
    y0 = max(0, members[0].top_y - int(sp))
    y1 = min(pi.binary.shape[0], members[-1].bottom_y + int(sp))

    col = pi.binary[y0:y1, x0:x1]
    n = args.chunks
    h = col.shape[0] // n
    parts = []
    for i in range(n):
        parts.append(col[i * h:(i + 1) * h])
        parts.append(np.full((h, 10), 128, np.uint8))
    out = np.hstack(parts[:-1])
    s = args.scale
    out = cv2.resize(out, (int(out.shape[1] * s), int(out.shape[0] * s)),
                     interpolation=cv2.INTER_NEAREST)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(args.out, out)
    print(f"{args.out}  {out.shape}  {len(members)} staves  spacing={sp:.1f}  "
          f"band x={x0}-{x1} y={y0}-{y1}  chunk={h}px "
          f"(~{h/ (y1-y0) * len(members):.1f} staves per strip)")
    for i, st in enumerate(members):
        print(f"  staff {i}: y {st.top_y}-{st.bottom_y}")


if __name__ == "__main__":
    main()
