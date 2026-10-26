"""Phase 1.4 — Staff line removal preserving symbol-crossing pixels.

The goal: produce an image where staff lines are erased, but the pixels
where notes/stems/ornaments cross those lines remain intact. Naive removal
(just erasing the staff line row) severs noteheads in half and disconnects
stems from their flags.

Algorithm: at each staff line, walk the vertical ink run through every column
and measure how tall it is. A run no taller than the line is printed IS the
line, and is erased along its real path; a taller one is something crossing —
a notehead, a stem, a beam, a barline — and is left entirely alone.

Two things make that safe without any appeal to how a symbol looks. The rows
considered are only those on a run through a staff line whose position Phase 1
already knows, and the height a run is compared against is the line's own
printed thickness, measured from this cell. Erasing the run along its real path
is also what handles a line that wanders, without needing to model the wander.

This is run per measure cell (smaller image, faster) and uses the staff
line y-coordinates that already came with the cell.

Why the run height and not a fixed neighbourhood
------------------------------------------------
The original test asked whether ink sat a FIXED 4px above and below a pixel,
and preserved it if so. On a line thicker than 8px that test is satisfied by
the line itself, so a thick line preserved itself and nothing was removed.
That is not an edge case — it is most orchestral scores. Measured share of
staff-line ink actually cleared, before this change:

    WTC p.5          6px lines   91.3%
    Boléro p.31      9px lines   72.5%
    Mahler 5 p.11   17px lines    0.9%
    Beethoven 5 p.10            0.0%

So on exactly the dense, thick-printed material where removal matters most,
this module was a no-op, and every consumer of `image_no_staff` — stem and
beam detection, template matching, the labeling UI's sparse-cell ranking —
was working on an image that still had its staff lines.

The line's printed thickness is measured from the cell rather than assumed,
because it varies from 0.06 to 0.31 staff spaces across the corpus. Comparing
a run against the page's own line thickness is scale-free in a way that a
pixel count can never be.

There is no longer a morphological opening. It was there to confirm that a
candidate pixel belonged to a long horizontal run, but a broken line fails that
test: only 37.7% of Beethoven 5 p.10's line-row ink survived an opening at 30%
of cell width, and 73.0% of Mahler's. Measured across four scores, dropping it
improves every number at once — more line ink cleared, a smaller largest
connected component, and FEWER stray specks, because a partly erased line
leaves its own fragments behind. Stem and beam counts from `line_detection`
move by under 5% either way, so the opening was not protecting anything.
"""

from __future__ import annotations

import math
import os

import cv2
import numpy as np

from .types import MeasureCell


# A printed staff line is never thicker than this share of a staff space. Used
# to cap the measured thickness, so a line buried under symbols for its whole
# length cannot talk the estimate up and start protecting itself again. The
# thickest line measured on the corpus is 0.31 spaces (Mahler 5, Beethoven 5).
MAX_LINE_THICKNESS_SPACES = 0.35

# A vertical ink run taller than this multiple of the line's own thickness is
# something crossing the line, not the line. Wide margin on purpose: the
# smallest real crossing is a stem or a notehead, both around a full staff
# space, which is 3-15x a line's thickness depending on the print.
LINE_CROSSING_FACTOR = 2.0

# ...but never treat anything as thick as a beam as erasable. On a page whose
# lines are already 0.28 staff spaces thick, 2x thickness reaches past a beam's
# ~0.5 spaces, and a beam lying along a staff line would be erased where it
# crosses. Measured, this cap changes almost nothing (Mahler 5 p.11 beam count
# 239 with or without it, and it does not bind at all on WTC or Boléro) — it is
# insurance against a case the corpus does not currently contain, not a fix for
# one it does.
MAX_ERASABLE_RUN_SPACES = 0.45

# How far from its nominal row a line may be looked for, in staff spaces.
# Phase 1 reports each line as one straight y, but a printed line drifts across
# a cell and deskew leaves a residual tilt, so at the ends of a wide cell the
# ink can sit clear of the nominal row. Anchoring to the nearest ink within
# this radius erases the line where it actually is. Kept well under half a
# staff space so the search can never reach the neighbouring line.
LINE_SEARCH_RADIUS_SPACES = 0.25

# ROADMAP 2.206 (flag OMR_ERASER_FIX, default OFF). The walk through each column
# was bounded at `cap + 2` rows either side -- `cap` is the THICKNESS cap
# (0.35 sp), a different quantity from the crossing cut it feeds (up to 0.45 sp,
# `MAX_ERASABLE_RUN_SPACES`). Where the cut is taller than the walk (a fat line:
# 2 x thickness > cap + 2, Litolff's 0.25-0.32 sp lines), a run that continues
# past the walk on ONE side reads as (walk + the other side) and can fall under
# the cut: the column is erased, and with it up to `cap + 2` rows of whatever
# hangs from or sits on the line -- a beam, a whole rest, a quarter rest's body,
# the top of a head in the space below (benchmarks/staff-eraser-2026-10/
# FINDINGS.md). With the flag ON the walk reaches past the cut on each side, so
# "taller than the cut" is measured, never truncated: a column is erased iff its
# whole run is no taller than the cut, which is what this module always said.
ENV_ERASER_FIX = "OMR_ERASER_FIX"


def eraser_fix_enabled() -> bool:
    """ROADMAP 2.206: OFF unless `OMR_ERASER_FIX` is 1/true/yes/on."""
    return os.environ.get(ENV_ERASER_FIX, "").strip().lower() in ("1", "true", "yes", "on")


def walk_for_cut(cap: int, crossing_cut: float) -> int:
    """`max_search` for `_vertical_runs_through` such that a run longer than the
    walk on either side is already taller than `crossing_cut` (ROADMAP 2.206).

    The walk goes `max_search + 2` rows each side; a run that reaches that bound
    measures at least `max_search + 3` rows, so `max_search >= ceil(cut)` makes
    every truncated run read taller than the cut. Never shorter than `cap`, so
    every run the thickness estimate reads (<= cap) is unchanged.
    """
    return max(int(cap), int(math.ceil(crossing_cut)))


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
    ink_bool = binary == 0
    line_ys = list(getattr(cell, "staff_line_ys_canonical", None) or [])
    # A one-line staff has no gap to divide, and spacing 0 lifts the run-height
    # cap to the whole cell — so a stem crossing the rule is a candidate for
    # erasure. The canonical spacing is stated on the cell for exactly that
    # case (`measure_extractor._build_measure_cell`); absent on five-line
    # cells, so this is inert unless `OMR_ONE_LINE_STAVES` admitted one.
    spacing = (
        (line_ys[-1] - line_ys[0]) / 4.0 if len(line_ys) >= 2
        else float(getattr(cell, "staff_line_spacing_canonical", 0.0) or 0.0)
    )
    cap = max(1, int(round(MAX_LINE_THICKNESS_SPACES * spacing))) if spacing > 0 else h

    to_erase = np.zeros((h, w), dtype=bool)
    fix = eraser_fix_enabled()
    for y in line_ys:
        y = int(round(y))
        if not (0 <= y < h):
            continue
        search = int(round(LINE_SEARCH_RADIUS_SPACES * spacing)) if spacing > 0 else 0
        heights, tops, bottoms, present = _vertical_runs_through(
            ink_bool, y, cap, radius=search
        )
        if not present.any():
            continue
        thickness = _line_thickness(heights[present], cap)
        crossing_cut = thickness * LINE_CROSSING_FACTOR
        if spacing > 0:
            crossing_cut = min(crossing_cut, MAX_ERASABLE_RUN_SPACES * spacing)
        crossing_cut = max(crossing_cut, thickness + 1.0)
        if fix:
            walk = walk_for_cut(cap, crossing_cut)
            if walk > cap:
                # Same anchor, same rows up to the old bound; only runs the old
                # walk truncated read longer. The thickness above is unchanged
                # (it reads runs <= cap, which no walk >= cap truncates).
                heights, tops, bottoms, present = _vertical_runs_through(
                    ink_bool, y, walk, radius=search
                )
        # A run no taller than the line is the line; anything taller crosses it.
        erase_cols = present & (heights <= crossing_cut)
        if not erase_cols.any():
            continue
        rows = np.arange(h)[:, None]
        band = (rows >= tops[None, :]) & (rows <= bottoms[None, :]) & erase_cols[None, :]
        to_erase |= band

    out = binary.copy()
    out[to_erase] = 255  # set to paper
    if in_place:
        cell.image_no_staff = out
    return out


def _anchor_rows(ink: np.ndarray, y: int, radius: int) -> tuple[np.ndarray, np.ndarray]:
    """Per column, the ink row nearest `y` within `radius`, and whether one exists.

    A staff line is not where Phase 1 says it is, exactly. Phase 1 fits one
    straight y per line, while the printed line drifts and any residual skew
    tilts it, so across a wide cell the ink wanders off that row and back. Where
    it has wandered, sampling the nominal row alone finds paper and the line
    survives. Searching a short way for it costs nothing and follows it.
    """
    h, w = ink.shape
    anchor = np.full(w, y, dtype=int)
    found = np.zeros(w, dtype=bool)
    for d in range(0, radius + 1):
        for row in ({y} if d == 0 else {y - d, y + d}):
            if not (0 <= row < h):
                continue
            hit = ink[row] & ~found
            if hit.any():
                anchor[hit] = row
                found |= hit
        if found.all():
            break
    return anchor, found


def _vertical_runs_through(
    ink: np.ndarray, y: int, max_search: int, radius: int = 0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """For every column, the contiguous vertical ink run at the staff line `y`.

    The run is taken through the nearest ink row within `radius` of `y`, so a
    line that has drifted off its nominal row is still followed. Returns
    (heights, tops, bottoms, present), each of length w; `present` is False
    where the column has no ink near `y` at all. The walk is bounded at
    `max_search + 2` rows either side, since a run longer than that is a crossing
    symbol and its exact extent does not matter — only that it is too tall.

    ⚠️ That holds only if the bound is at least the cut the heights are compared
    with. A truncated run reads as (bound + the other side's length), which can
    be SHORTER than the cut: main passes the thickness cap (0.35 sp) while the
    cut reaches 0.45 sp, so on fat-lined plates a mark hanging from a line was
    erased up to the bound (ROADMAP 2.206; `walk_for_cut`, `OMR_ERASER_FIX`).
    """
    h, w = ink.shape
    reach = int(max(2, max_search + 2))
    cols = np.arange(w)
    anchor, present = _anchor_rows(ink, y, int(radius))

    up_len = np.ones(w, dtype=int)
    alive = present.copy()
    for k in range(1, reach + 1):
        row = anchor - k
        ok = alive & (row >= 0)
        if not ok.any():
            break
        step = np.zeros(w, dtype=bool)
        step[ok] = ink[row[ok], cols[ok]]
        alive &= step
        up_len += alive

    down_len = np.ones(w, dtype=int)
    alive = present.copy()
    for k in range(1, reach + 1):
        row = anchor + k
        ok = alive & (row < h)
        if not ok.any():
            break
        step = np.zeros(w, dtype=bool)
        step[ok] = ink[row[ok], cols[ok]]
        alive &= step
        down_len += alive

    heights = np.where(present, up_len + down_len - 1, 0).astype(float)
    tops = np.where(present, anchor - (up_len - 1), y).astype(int)
    bottoms = np.where(present, anchor + (down_len - 1), y).astype(int)
    return heights, tops, bottoms, present


def _line_thickness(heights: np.ndarray, cap: int) -> float:
    """How thick the staff line is actually printed, in pixels.

    Taken as the median over the columns where the run is line-shaped, i.e.
    no taller than a staff line could possibly be. Columns carrying a notehead
    or a beam are excluded by that cap rather than by a percentile, so the
    estimate does not drift on a dense cell where most columns carry ink.
    """
    line_like = heights[heights <= cap]
    if line_like.size == 0:
        return float(cap)
    return float(np.median(line_like))


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
