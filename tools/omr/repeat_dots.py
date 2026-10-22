"""Find the two dots of a repeat sign beside a barline, on one staff.

ROADMAP 2.85. The detector has a `repeatDot` class but on Breitkopf Brahms 1
pdf p10-11 it fired twice, both spurious, and missed every one of the 28
dots of the backward repeat at the end of the 1st ending (system 1, 14
staves). This is the CV reader for them.

**What a repeat sign is on the page** (how a human reads it): a thin+thick
barline pair with TWO DOTS beside it on every staff of the system -- one in
the second space from the top, one in the third (either side of the middle
line), one above the other. Dots to the LEFT of the barline repeat BACK
(`:||`, the end of a repeated passage); dots to the RIGHT start one
(`||:`).

CONVENTION ASSUMED / WHAT WOULD FALSIFY IT / NOT CONFIRMED: each dot is a
compact blob 0.25-0.8 staff spaces across, centred in space 2 and space 3,
the two within 0.35 spaces of the same x, inside 2.6 staff spaces of the
barline the measure extractor cut -- measured on Breitkopf 317803 pdf p10
system 1 (11 of 14 staves read, at x 2559-2571 for a barline at 2584; zero
pairs at every other barline of the page; over both acceptance movements,
43 pages, the only edges reaching the staff vote are that repeat and the
exposition's forward repeat on p3). A dot touching a notehead, dynamic,
slur -- or, on Litolff's MERGING plate, the staff lines themselves -- merges
into a bigger component and is not read (3 of 14 on Brahms p10; Litolff's
exposition repeat entirely) -- a miss files nothing, never a wrong repeat.

GATHER decides nothing: which barlines ARE repeats is ADJUDICATE's
(`adjudicators/structure.adjudicate_repeat_barlines`), voting across the
staves of the system.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

#: How far from the barline the dots may stand, in staff spaces. The window
#: has to clear the thick stroke of a thin+thick pair when the extractor
#: cut at the thick one.
WINDOW_FAR_SPACES = 2.6
WINDOW_NEAR_SPACES = 0.15
DOT_MIN_SPACES = 0.25
DOT_MAX_SPACES = 0.8
#: A dot is filled: ink over its own bounding box.
DOT_MIN_FILL = 0.5
PAIR_X_TOL_SPACES = 0.35


def find_pair(binary, line_ys: Sequence[float], barline_x: float,
              side: str) -> Optional[Tuple[Tuple[float, float],
                                           Tuple[float, float]]]:
    """The two repeat dots on `side` ('left' or 'right') of `barline_x`.

    `binary` is the page as 0/1 ink (2-D); `line_ys` this staff's five lines.
    Returns `((x, y) upper dot, (x, y) lower dot)` in page pixels, or None.
    """
    import numpy as np
    import cv2

    ys = [float(v) for v in line_ys]
    if len(ys) != 5:
        return None
    space = (ys[-1] - ys[0]) / 4.0
    if space <= 0:
        return None
    H, W = binary.shape
    if side == "left":
        xa = int(barline_x - WINDOW_FAR_SPACES * space)
        xz = int(barline_x - WINDOW_NEAR_SPACES * space)
    elif side == "right":
        xa = int(barline_x + WINDOW_NEAR_SPACES * space)
        xz = int(barline_x + WINDOW_FAR_SPACES * space)
    else:
        raise ValueError(side)
    xa, xz = max(0, xa), min(W, xz)
    ya, yz = max(0, int(ys[1] - 0.2 * space)), min(H, int(ys[3] + 0.2 * space))
    if xz <= xa or yz <= ya:
        return None
    # ⚠️ THE STAFF LINES ARE *NOT* ERASED, AND THAT WAS MEASURED. Litolff's
    # dots touch the heavy lines and so are one component with the staff
    # (Beethoven 5 p5 system 0, the exposition repeat: missed). Erasing the
    # line rows inside the window finds them -- and over both acceptance
    # movements took the edges passing the staff vote from 2 (both real) to
    # 69, nearly all of them a key signature's flats right of a system's
    # first barline. A miss files nothing; a false repeat writes `:||` into
    # the file. The isolated-blob reader stays.
    win = np.ascontiguousarray(binary[ya:yz, xa:xz], dtype=np.uint8)
    n, _lab, stats, cents = cv2.connectedComponentsWithStats(win, 8)
    blobs: List[Tuple[float, float]] = []
    for i in range(1, n):
        _x, _y, w, h, area = (int(v) for v in stats[i])
        if not (DOT_MIN_SPACES * space <= w <= DOT_MAX_SPACES * space
                and DOT_MIN_SPACES * space <= h <= DOT_MAX_SPACES * space):
            continue
        if area < DOT_MIN_FILL * w * h:
            continue
        blobs.append((float(cents[i][0]) + xa, float(cents[i][1]) + ya))
    upper = [b for b in blobs if ys[1] < b[1] < ys[2]]
    lower = [b for b in blobs if ys[2] < b[1] < ys[3]]
    pairs = [(u, d) for u in upper for d in lower
             if abs(u[0] - d[0]) <= PAIR_X_TOL_SPACES * space]
    if len(pairs) != 1:
        # none, or more than one candidate pair: either way this reader has
        # no single answer (two pairs is a dotted-note column, not a repeat)
        return None
    return pairs[0]
