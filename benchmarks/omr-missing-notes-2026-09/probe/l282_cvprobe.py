#!/usr/bin/env python3
"""l282_cvprobe: why does the classical-CV beam reader (`line_detection.detect_beams`) read, or not read, the
beam of a named truth beam on Sean's page (Brahms 317803 pdf 0)? Prepares the page the way the gather does
(`pipeline.prepare_pages`: render, staves, cells, staff-line removal), finds the cell(s) holding each truth
beam's centre, and runs the SAME `detect_stems` / `detect_beams` on it, printing every stem the stem reader
found (with its x and height against the 2.8-space anchor floor) and every beam, then draws the cell: the
original raster, the staff-erased raster (what the CV reader sees), the opened mask, the stems (green) and
beams (blue), the truth beam (magenta). ROADMAP 2.82. A reading probe: it decides nothing.

    python3 l282_cvprobe.py --ids q82,b4130,b4189 --out DIR
"""
import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from l281_tiles import PDFS  # noqa: E402
from l281_truth import Truth  # noqa: E402
from tools.omr import line_detection as LD  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--page", type=int, default=0)
    a = ap.parse_args()
    T = Truth()
    by = {b.id: b for b in T.beams}
    from tools.omr.staged.pipeline import prepare_pages
    (pws, cells), = prepare_pages(PDFS["brahms"], [a.page])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"{len(cells)} cells")
    for tid in a.ids.split(","):
        b = by[tid]
        cx, cy = (b.rect[0] + b.rect[2]) / 2, (b.rect[1] + b.rect[3]) / 2
        for c in cells:
            bb = getattr(c, "bbox_page_px", None)
            if not bb or not (bb[0] <= cx <= bb[2] and bb[1] <= cy <= bb[3]):
                continue
            up = c.upscale_factor
            sp = LD._staff_line_spacing(c)
            cand = []
            stems = LD.detect_stems(c, candidates_out=cand)
            beams = LD.detect_beams(c, stems=stems, rescue_tall=True)
            print(f"== truth {tid} rect {[round(v) for v in b.rect]} in cell staff_index={c.staff_index} "
                  f"measure={c.measure_index} bbox {[round(v) for v in bb]} up {up:.3f} spacing {sp:.1f}px "
                  f"(anchor floor {sp * 2.8:.0f}px)")
            for s in stems:
                print(f"   stem x={s.x_canonical} y={s.y_canonical} w={s.width_canonical} h={s.height_canonical} "
                      f"({s.height_canonical / sp:.1f} sp)" + ("  [anchor]" if s.height_canonical >= sp * 2.8 else ""))
            for bm in beams:
                print(f"   beam x={bm.x_canonical} y={bm.y_canonical} w={bm.width_canonical} h={bm.height_canonical}")
            src = c.image_no_staff if getattr(c, "image_no_staff", None) is not None else c.image
            ink = LD._binary_ink(src)
            kw = max(3, int(round(sp * 1.5)))
            opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (kw, 1)))
            n, lab, st, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
            print("   vertical-run candidates (accepted AND refused, first refusing filter):")
            for v in cand:
                print(f"      x {v.x} y {v.y} w {v.w} h {v.h} ({v.h / sp:.1f} sp) area {v.area} -> {v.outcome}")
            print("   opened components:", n - 1)
            for i in range(1, n):
                x, y, w, h, ar = st[i]
                print(f"      comp {i}: x {x} y {y} w {w} h {h} ({h / sp:.2f} sp) area {ar}"
                      f" ratio w/h {w / max(1, h):.1f}")

            def gray3(img):
                g = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
            orig = gray3(c.image)
            er = gray3(src)
            mk = cv2.cvtColor(opened, cv2.COLOR_GRAY2BGR)
            tb = [(b.rect[0] - bb[0]) * up, (b.rect[1] - bb[1]) * up, (b.rect[2] - bb[0]) * up, (b.rect[3] - bb[1]) * up]
            for im in (orig, er, mk):
                cv2.rectangle(im, (int(tb[0]), int(tb[1])), (int(tb[2]), int(tb[3])), (255, 0, 255), 3)
                for s in stems:
                    cv2.rectangle(im, (s.x_canonical, s.y_canonical),
                                  (s.x_canonical + s.width_canonical, s.y_canonical + s.height_canonical), (0, 200, 0), 2)
                for bm in beams:
                    cv2.rectangle(im, (bm.x_canonical, bm.y_canonical),
                                  (bm.x_canonical + bm.width_canonical, bm.y_canonical + bm.height_canonical),
                                  (255, 0, 0), 2)
            sheet = np.vstack([orig, er, mk])
            f = min(1.0, 1400.0 / sheet.shape[1])
            sheet = cv2.resize(sheet, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
            fn = out / f"cv_{tid}_m{c.measure_index}.png"
            cv2.imwrite(str(fn), sheet)
            print("   ->", fn)


if __name__ == "__main__":
    main()
