"""Phase 1.5 — Visualization helper for sanity-checking detection.

Draws colored overlays on the original page image:
  - Green:   detected staff lines
  - Red:     detected barlines
  - Blue:    measure cell bounding boxes (one per (staff × measure))
  - Yellow:  system divider lines

Output goes to a PNG so you can flip through and verify visually.

Usage:
    python3 -m tools.omr.visualize <pdf> --page N --out <path.png>
    python3 -m tools.omr.visualize <pdf> --page N --out <path.png> --cells-dir <dir>
        also writes each extracted measure cell as a separate PNG
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .types import PageWithStaves


# BGR colors for cv2
COLOR_STAFF = (0, 200, 0)        # green
COLOR_BARLINE = (0, 0, 255)      # red
COLOR_CELL = (255, 150, 0)       # blue (BGR)
COLOR_SYSTEM = (0, 220, 220)     # yellow


def draw_overlay(pws: PageWithStaves, cells=None, alpha: float = 0.6) -> np.ndarray:
    """Render an annotated copy of pws.page.rgb. Returns BGR uint8 (ready for
    cv2.imwrite). If `cells` is provided, draws each cell's bbox."""
    rgb = pws.page.rgb
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).copy()
    h, w = bgr.shape[:2]

    # Staff lines: draw thin green lines across the staff x-extent
    for s in pws.staves:
        for y in s.line_ys:
            cv2.line(bgr, (s.x_start, y), (s.x_end, y), COLOR_STAFF, 2)
        # Staff index label
        cv2.putText(
            bgr, f"s{s.staff_index} sys{s.system_index}",
            (max(0, s.x_start - 110), s.line_ys[len(s.line_ys) // 2]),
            cv2.FONT_HERSHEY_SIMPLEX, 0.9, COLOR_STAFF, 2,
        )

    # Barlines: red vertical lines, numbered per system so we can spot
    # over-detection by inspecting the cluster pattern.
    bls_by_sys: dict[int, list] = {}
    for bl in pws.barlines:
        bls_by_sys.setdefault(bl.system_index, []).append(bl)
    for sys, bls in bls_by_sys.items():
        bls.sort(key=lambda b: b.x)
        for i, bl in enumerate(bls):
            cv2.line(bgr, (bl.x, bl.y_top), (bl.x, bl.y_bottom), COLOR_BARLINE, 3)
            cv2.putText(
                bgr, str(i),
                (bl.x + 4, bl.y_top + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, COLOR_BARLINE, 2,
            )

    # Measure cells: thin blue rectangles
    if cells:
        for c in cells:
            x0, y0, x1, y1 = c.bbox_page_px
            cv2.rectangle(bgr, (x0, y0), (x1, y1), COLOR_CELL, 1)

    # System dividers — draw a yellow dashed horizontal line between
    # systems
    systems: dict[int, list] = {}
    for s in pws.staves:
        systems.setdefault(s.system_index, []).append(s)
    sys_centers = sorted([(min(ss[0].top_y for ss in [g]), idx) for idx, g in systems.items()])
    sys_indices = sorted(systems.keys())
    for i in range(len(sys_indices) - 1):
        sys_a = systems[sys_indices[i]]
        sys_b = systems[sys_indices[i + 1]]
        a_bot = max(s.bottom_y for s in sys_a)
        b_top = min(s.top_y for s in sys_b)
        y_div = (a_bot + b_top) // 2
        # Dashed line
        x = 0
        while x < w:
            cv2.line(bgr, (x, y_div), (min(w, x + 30), y_div), COLOR_SYSTEM, 1)
            x += 60

    return bgr


def write_overlay(pws: PageWithStaves, out_path: str | Path, cells=None) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img = draw_overlay(pws, cells=cells)
    cv2.imwrite(str(out_path), img)


def write_cell_images(cells, out_dir: str | Path, with_staff_grid: bool = True) -> None:
    """Write each measure cell as <staff>_<measure>.png. If with_staff_grid,
    overlays the canonical-space staff lines so you can sanity-check the
    upscaling."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for c in cells:
        img = c.image.copy()
        if with_staff_grid:
            bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            for y in c.staff_line_ys_canonical:
                cv2.line(bgr, (0, y), (bgr.shape[1] - 1, y), (0, 200, 0), 1)
            img = bgr
        elif img.ndim == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        name = f"p{c.page_index}_sys{c.system_index}_s{c.staff_index}_m{c.measure_index}.png"
        cv2.imwrite(str(out_dir / name), img)


# ─── CLI ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse
    from .preprocessing import render_page
    from .staff_detector import detect_staves
    from .measure_extractor import detect_barlines, extract_measures

    ap = argparse.ArgumentParser(description="Draw detection overlay on a PDF page")
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out", required=True, help="Output PNG path for the overlay")
    ap.add_argument("--cells-dir", default=None, help="Optional: write each cell as a PNG to this dir")
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(pi)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)
    write_overlay(pws, args.out, cells=cells)
    print(f"wrote overlay: {args.out}")
    if args.cells_dir:
        write_cell_images(cells, args.cells_dir)
        print(f"wrote {len(cells)} cells to {args.cells_dir}")
