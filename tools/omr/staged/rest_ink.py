"""Does a rest box's own ink run on into a notehead? -- ROADMAP 2.150b (STAGED GATHER measurement; decides nothing).

Sean, 2026-10-16: "a rest box whose stroke runs on into a notehead is a stem; a real rest stands free". A pure
measurement over a staff-ERASED ink mask (True = ink), in whatever frame the caller holds (the cell's canonical pixels
in production, the page's pixels in a probe): everything is in staff spaces, so the frame never matters.

What it measures, around ONE box the detector called a rest:
  * the DOMINANT connected piece of ink under the box (the piece with the most ink inside it), after a vertical
    closing of ~0.25 space so the hair of gap staff-line erasure leaves does not cut a stem in two;
  * `thin_run_sp`: the longest stretch of rows over which that piece is never wider than `THIN_SP` (0.45 space) --
    a stem, however thickly the plate prints it, is one long thin stroke; a quarter rest is not (measured: stems
    1.45-2.98 spaces, real quarter rests 0.40-0.70);
  * `blob_sp`: the longest stretch of rows over which the piece is at least `BLOB_WIDTH_SP` (0.7 space) wide -- a
    solid head standing on the stroke inside the box (real rests 0.22-0.70, stems with a head 0.87-1.48);
  * per notehead box that is NOT this box: `ink_sp2`, the area (square spaces) of that same piece that lies inside
    the head's box and OUTSIDE the rest box (grown by `OUTSIDE_MARGIN_SP`): ink contact, not box contact. A twin head
    box beside a free-standing rest owns none of the rest's ink, so it measures ~0.

It names nothing. The consumer (`family_precision._rest_stroke_into_head_refusal`) weighs the numbers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

import os

ENV = "OMR_REST_STROKE_INTO_HEAD"


def enabled() -> bool:
    """`OMR_REST_STROKE_INTO_HEAD`, default OFF (ROADMAP 2.150b); only an explicit `1/true/yes/on` enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


CLOSE_SP = 0.25          # vertical closing, spaces: bridges erased-staff-line gaps in a stem
COLUMN_SLACK_SP = 0.2    # columns searched beyond the box's own x-range
OUTSIDE_MARGIN_SP = 0.2  # the rest box is grown by this before "outside the box" ink is counted
THIN_SP = 0.45           # a row where the piece's widest horizontal run is at most this is a "thin" row
BLOB_WIDTH_SP = 0.7      # a row where it is at least this wide is a "solid" row
ROW_MARGIN_SP = 0.7      # rows searched beyond the box's top and bottom
ROW_SLACK_SP = 1.2       # columns searched beyond the box's own x-range when taking a row's widest run
WINDOW_X_SP = 2.0
WINDOW_Y_SP = 4.5


def _runs(col) -> Tuple[int, int, int]:
    """(longest run length, its first row, its last row) of True in a 1-D bool array; (0, -1, -1) if none."""
    import numpy as np
    if not col.any():
        return 0, -1, -1
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    s, e = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
    k = int(np.argmax(e - s))
    return int(e[k] - s[k]), int(s[k]), int(e[k] - 1)


def measure(ink, box: Sequence[float], heads: Sequence[Tuple[Any, str, float, float, float, float]],
            space: float) -> Optional[Dict[str, Any]]:
    """The ink contact of `box` (x0, y0, x1, y1) against `heads` [(id, class, x0, y0, x1, y1)]; None when it cannot
    be measured (no mask, no staff space, a box off the mask, no ink under the box)."""
    import cv2
    import numpy as np
    if ink is None or getattr(ink, "ndim", 0) != 2 or not space or space <= 0:
        return None
    H, W = ink.shape
    bx0, by0, bx1, by1 = (float(v) for v in box)
    wx0, wx1 = max(0, int(bx0 - WINDOW_X_SP * space)), min(W, int(bx1 + WINDOW_X_SP * space) + 1)
    wy0, wy1 = max(0, int(by0 - WINDOW_Y_SP * space)), min(H, int(by1 + WINDOW_Y_SP * space) + 1)
    if wx1 - wx0 < 2 or wy1 - wy0 < 2:
        return None
    win = np.ascontiguousarray(ink[wy0:wy1, wx0:wx1]).astype(np.uint8)
    kv = max(1, int(round(CLOSE_SP * space)))
    closed = cv2.morphologyEx(win, cv2.MORPH_CLOSE, np.ones((kv, 1), np.uint8)) if kv > 1 else win
    n, lab = cv2.connectedComponents(closed, connectivity=8)
    ix0, iy0 = max(0, int(round(bx0)) - wx0), max(0, int(round(by0)) - wy0)
    ix1, iy1 = min(win.shape[1], int(round(bx1)) - wx0), min(win.shape[0], int(round(by1)) - wy0)
    if ix1 <= ix0 or iy1 <= iy0:
        return None
    under = lab[iy0:iy1, ix0:ix1]
    under = under[win[iy0:iy1, ix0:ix1] > 0]          # real ink only, not closing fill
    under = under[under > 0]
    if under.size == 0:
        return None
    counts = np.bincount(under)
    dom = int(np.argmax(counts))
    cc = (lab == dom) & (win > 0)
    ra, rb = max(0, iy0 - int(ROW_MARGIN_SP * space)), min(win.shape[0], iy1 + int(ROW_MARGIN_SP * space))
    ca, cb = max(0, ix0 - int(ROW_SLACK_SP * space)), min(win.shape[1], ix1 + int(ROW_SLACK_SP * space))
    widths = np.array([_runs(cc[y, ca:cb])[0] for y in range(ra, rb)], dtype=float) / space
    thin, thin_lo, thin_hi = _runs((widths > 0) & (widths <= THIN_SP))
    blob, _, _ = _runs(widths >= BLOB_WIDTH_SP)
    thin_beyond = max(0, iy0 - (ra + thin_lo), (ra + thin_hi + 1) - iy1) if thin else 0
    out_m = int(round(OUTSIDE_MARGIN_SP * space))
    gx0, gy0, gx1, gy1 = ix0 - out_m, iy0 - out_m, ix1 + out_m, iy1 + out_m
    per: List[Dict[str, Any]] = []
    for hid, hcls, hx0, hy0, hx1, hy1 in heads:
        a0, b0 = int(round(hx0)) - wx0, int(round(hy0)) - wy0
        a1, b1 = int(round(hx1)) - wx0, int(round(hy1)) - wy0
        a0, b0, a1, b1 = max(a0, 0), max(b0, 0), min(a1, win.shape[1]), min(b1, win.shape[0])
        if a1 <= a0 or b1 <= b0:
            continue
        sub = cc[b0:b1, a0:a1].copy()
        # blank the rest box (grown) out of the head's window
        ox0, oy0, ox1, oy1 = max(gx0 - a0, 0), max(gy0 - b0, 0), min(gx1 - a0, sub.shape[1]), min(gy1 - b0, sub.shape[0])
        if ox1 > ox0 and oy1 > oy0:
            sub[oy0:oy1, ox0:ox1] = False
        per.append({"head": hid, "class": hcls, "ink_sp2": round(float(sub.sum()) / (space * space), 3)})
    per.sort(key=lambda d: -d["ink_sp2"])
    return {"thin_run_sp": round(thin / space, 3),
            "thin_beyond_sp": round(thin_beyond / space, 3),
            "blob_sp": round(blob / space, 3),
            "box_height_sp": round((by1 - by0) / space, 3),
            "head_ink_sp2": per[0]["ink_sp2"] if per else 0.0,
            "head": per[0]["head"] if per else None,
            "heads": per[:3]}
