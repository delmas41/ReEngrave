#!/usr/bin/env python3
"""Quick verifier — draw YOLO label boxes on a rendered training image and
write a side-by-side PNG. Used to confirm that the Phase H rendered image
dimensions match the Phase G label normalization."""

import sys
from pathlib import Path

import cv2


def overlay(image_path: Path, label_path: Path, out_path: Path) -> tuple[int, int, int]:
    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]
    n_boxes = 0
    with label_path.open() as f:
        for line in f:
            parts = line.split()
            if len(parts) != 5:
                continue
            cls, cx, cy, bw, bh = parts
            cx = float(cx) * w
            cy = float(cy) * h
            bw = float(bw) * w
            bh = float(bh) * h
            x0 = int(round(cx - bw / 2))
            y0 = int(round(cy - bh / 2))
            x1 = int(round(cx + bw / 2))
            y1 = int(round(cy + bh / 2))
            color = (0, 0, 255) if int(cls) >= 36 and int(cls) <= 47 else (0, 200, 0)
            cv2.rectangle(img, (x0, y0), (x1, y1), color, 1)
            n_boxes += 1
    cv2.imwrite(str(out_path), img)
    return n_boxes, w, h


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: phase_h_verify_overlay.py IMAGE LABEL [OUT]")
        return 2
    img = Path(sys.argv[1])
    lbl = Path(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) >= 4 else img.with_name(img.stem + "_overlay.png")
    n, w, h = overlay(img, lbl, out)
    print(f"wrote {out}  ({n} boxes on {w}x{h} image)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
