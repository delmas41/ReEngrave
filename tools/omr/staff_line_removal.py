"""Phase 1.4 — Staff line removal preserving symbol-crossing pixels.

The goal: produce an image where staff lines are erased, but the pixels
where notes/stems/ornaments cross those lines remain intact. Naive removal
(just erasing the staff line row) severs noteheads in half and disconnects
stems from their flags.

Algorithm:
  1. Isolate the staff lines via horizontal morphological opening: erode
     with a long horizontal kernel → keeps only pixels that are part of a
     horizontal run at least as long as the kernel.
  2. For each candidate staff-line pixel: check whether anything is on top
     of it (ink in the rows immediately above OR below). If yes → preserve
     it (symbol crosses here). If no → erase it.

This is run per measure cell (smaller image, faster) and uses the staff
line y-coordinates that already came with the cell.
"""

from __future__ import annotations

import cv2
import numpy as np

from .types import MeasureCell


# How long a horizontal ink run must be (in px in the canonical-size image)
# to count as a staff-line fragment. ~30% of cell width is generous; staff
# lines almost always span the full cell.
STAFF_LINE_MIN_LEN_FRAC = 0.30

# When checking for a "symbol crosses here", how far above and below the
# staff line row to look. In the canonical image, line spacing is roughly
# CANONICAL_STAFF_SPAN_PX / 4 ≈ 100px. A symbol crossing a line should
# leave ink 2-5 px above or below the line row.
SYMBOL_NEIGHBOR_RADIUS_PX = 3


def remove_staff_lines_from_cell(cell: MeasureCell, in_place: bool = True) -> np.ndarray:
    """Compute a staff-line-removed grayscale image for the cell.

    Sets `cell.image_no_staff` if in_place=True and returns it.
    """
    # Work on a grayscale binary version (255=paper, 0=ink).
    img = cell.image
    if img.ndim == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    # Stash 'binary' from extraction if available, else re-binarize on the fly.
    binary = getattr(cell, "binary", None)
    if binary is None:
        from .preprocessing import binarize
        binary = binarize(gray)

    h, w = binary.shape
    # 1. Isolate horizontal runs (potential staff line fragments) via opening
    kernel_len = max(15, int(w * STAFF_LINE_MIN_LEN_FRAC))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_len, 1))
    # cv2.morphologyEx expects ink=255, paper=0 for "open" to keep horizontal
    # ink runs — so invert before, invert back after.
    ink = cv2.bitwise_not(binary)
    horizontal_runs = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    # horizontal_runs == 255 where a staff-line fragment exists.

    # 2. Build a "preserve" mask: pixels where the immediate vertical
    # neighbourhood (excluding the line itself) contains ink → a symbol
    # crosses here.
    r = SYMBOL_NEIGHBOR_RADIUS_PX
    above_offset = -r - 1
    below_offset = r + 1

    above_ink = np.zeros_like(ink)
    below_ink = np.zeros_like(ink)
    if h > abs(above_offset):
        above_ink[abs(above_offset):, :] = ink[:above_offset, :]
    if h > below_offset:
        below_ink[:-below_offset, :] = ink[below_offset:, :]
    # Any ink in the ±r vicinity outside the immediate line band counts as
    # "something is here" — preserve.
    preserve = (above_ink > 0) & (below_ink > 0)

    # 3. The pixels to erase = staff-line fragments AND NOT preserved
    to_erase = (horizontal_runs > 0) & (~preserve)

    out = binary.copy()
    out[to_erase] = 255  # set to paper
    if in_place:
        cell.image_no_staff = out
    return out


def remove_staff_lines(cells: list[MeasureCell]) -> list[MeasureCell]:
    """Run staff-line removal across an entire list of cells (in place)."""
    for c in cells:
        remove_staff_lines_from_cell(c, in_place=True)
    return cells


# ─── CLI smoke test ──────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    from .preprocessing import render_page
    from .staff_detector import detect_staves
    from .measure_extractor import detect_barlines, extract_measures

    ap = argparse.ArgumentParser(description="Run staff line removal on extracted cells")
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(pi)
    pws = detect_barlines(pws)
    cells = extract_measures(pws)
    remove_staff_lines(cells)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for c in cells:
        if c.image_no_staff is None:
            continue
        name = f"p{c.page_index}_sys{c.system_index}_s{c.staff_index}_m{c.measure_index}_nostaff.png"
        cv2.imwrite(str(out_dir / name), c.image_no_staff)
    print(f"wrote {len(cells)} no-staff cell images to {out_dir}")
