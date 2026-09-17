"""Regenerate the crops in `out/print/` — the evidence for §6, the cell
correction.

⚠️ THE CROPS ARE COMMITTED AND THE DIRECTORY IS NOT `crops/`, DELIBERATELY.
`.gitignore:112` excludes `benchmarks/**/crops/`, and CLAUDE.md records a
commit message that said "the crops are committed under `crops/`" when they had
never been in the tree at all. `git check-ignore` was run on these before the
commit that added them.

⚠️ THE CLAIM THEY SUPPORT IS ABOUT INK ON A PLATE, so it can only be settled by
looking. `ASSUMPTIONS.md` A-DUR-5 says the printed `3/4` on Litolff Beethoven 5
p.62 is at cell 8; `p62-staff0-cells-4-to-9.png` shows it at the head of cell 6
with the double barline, and `p62-cell8-head-staves-0-5.png` shows cell 8's
head holding nothing but staff lines.

    python3 probe/print_evidence.py <pdf>
"""
from __future__ import annotations

import pathlib
import sys

import cv2
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
OUT = pathlib.Path(__file__).resolve().parents[1] / "out" / "print"

PAGE = 62


def page_crop(pdf, out, dpi, box=None):
    from tools.omr.preprocessing import render_page
    img = render_page(pdf, PAGE, dpi=dpi).rgb
    if box:
        x0, y0, x1, y1 = box
        h, w = img.shape[:2]
        img = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    cv2.imwrite(str(out), img)
    print("wrote", out)


def cell_heads(pdf, out, staff, cells, *, width_sp=3.0, band_sp=8.0, px=60.0):
    from tools.omr.staged.pipeline import prepare_pages
    _pws, all_cells = prepare_pages(pdf, [PAGE], dpi=600)[0]
    tiles = []
    for ci in cells:
        c = next((c for c in all_cells if c.staff_index == staff
                  and c.measure_index == ci), None)
        if c is None:
            continue
        ys = list(c.staff_line_ys_canonical or [])
        sp = (ys[-1] - ys[0]) / 4.0
        img = c.image
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        mid = (ys[0] + ys[-1]) / 2.0
        t = img[max(0, int(mid - band_sp / 2 * sp)):
                min(img.shape[0], int(mid + band_sp / 2 * sp)),
                :min(img.shape[1], int(width_sp * sp))]
        s = px / sp
        t = cv2.resize(t, (int(t.shape[1] * s), int(t.shape[0] * s)),
                       interpolation=cv2.INTER_NEAREST)
        tiles.append((ci, cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)))
    h = max(t.shape[0] for _i, t in tiles) + 24
    w = max(t.shape[1] for _i, t in tiles) + 8
    canvas = np.full((h, w * len(tiles), 3), 255, np.uint8)
    for i, (ci, t) in enumerate(tiles):
        x = i * w
        canvas[24:24 + t.shape[0], x:x + t.shape[1]] = t
        cv2.putText(canvas, f"cell {ci}", (x + 4, 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
        cv2.line(canvas, (x, 0), (x, h), (0, 180, 0), 2)
    cv2.imwrite(str(out), canvas)
    print("wrote", out)


def staff_heads(pdf, out, cell, staves, *, width_sp=3.0, band_sp=8.0, px=80.0):
    """One cell's head on several staves — the cross-staff view."""
    from tools.omr.staged.pipeline import prepare_pages
    _pws, all_cells = prepare_pages(pdf, [PAGE], dpi=600)[0]
    tiles = []
    for st in staves:
        c = next((c for c in all_cells if c.staff_index == st
                  and c.measure_index == cell), None)
        if c is None:
            continue
        ys = list(c.staff_line_ys_canonical or [])
        sp = (ys[-1] - ys[0]) / 4.0
        img = c.image
        if img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        mid = (ys[0] + ys[-1]) / 2.0
        t = img[max(0, int(mid - band_sp / 2 * sp)):
                min(img.shape[0], int(mid + band_sp / 2 * sp)),
                :min(img.shape[1], int(width_sp * sp))]
        s = px / sp
        t = cv2.resize(t, (int(t.shape[1] * s), int(t.shape[0] * s)),
                       interpolation=cv2.INTER_NEAREST)
        tiles.append((st, cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)))
    h = max(t.shape[0] for _i, t in tiles) + 24
    w = max(t.shape[1] for _i, t in tiles) + 8
    canvas = np.full((h, w * len(tiles), 3), 255, np.uint8)
    for i, (st, t) in enumerate(tiles):
        x = i * w
        canvas[24:24 + t.shape[0], x:x + t.shape[1]] = t
        cv2.putText(canvas, f"staff {st}", (x + 4, 17),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 200), 2)
        cv2.line(canvas, (x, 0), (x, h), (0, 180, 0), 2)
    cv2.imwrite(str(out), canvas)
    print("wrote", out)


def main() -> int:
    pdf = sys.argv[1]
    OUT.mkdir(parents=True, exist_ok=True)
    page_crop(pdf, OUT / "p62-page.png", 130)
    page_crop(pdf, OUT / "p62-meter-change-six-staves.png", 400,
              (0.56, 0.09, 0.72, 0.42))
    cell_heads(pdf, OUT / "p62-staff0-cells-4-to-9.png", 0, [4, 5, 6, 7, 8, 9])
    staff_heads(pdf, OUT / "p62-cell8-head-staves-0-5.png", 8, range(6))
    staff_heads(pdf, OUT / "p62-cell6-head-staves-0-5.png", 6, range(6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
