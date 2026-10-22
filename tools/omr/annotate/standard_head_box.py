"""A STANDARD-SIZE notehead box, placed by the geometry template (lane
`lane-standard-head-box`, 2026-10-04; Sean: *"Shouldn't the boxes for notes
heads be standardized in size?"*, *"Could we use our template work to
determine size of notes?"*).

The detector's box is the wrong size for POSITION purposes in both directions
on a scan (too small on a half note -- it grabs the upper half; too big on a
head beside a stem or a partner -- and open-ended on a half note with a
printing gap). The head on a page is one size. So:

  size    = the page's MEASURED head, from clean, isolated, ON-LINE heads
            (`benchmarks/.../shape_from_page.py`: long / short axis and tilt
            by second moments) -- the axis-aligned extent of that oval; a
            hollow head takes the same outer size.
  centre  = where the template's FREE position search lands
            (`head_template.match_head_template`, decide="staged": the
            variant-free head template slid +-`DX_RANGE_SPACES` sideways and
            +-1.5 sp vertically on the head term alone, stems and staff-line
            remnants opened away). NOT the round-7 ledger-constrained height:
            that would make the box a consequence of the ledger read.

Pure construction, nothing wired in; the default reader path is unchanged
(this module is imported by no product code).
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Sequence, Tuple

from . import head_template as ht

DX_RANGE_SPACES = 0.4          # sideways search, +- (round 3's setting)
# the template fit's OWN pre-set gate (set 2026-10-04, BEFORE any scoring):
FIT_IOU_MIN = 0.70
FIT_OFFSET_MAX_SPACES = 0.15


def oval_extents_spaces(width_sp: float, height_sp: float,
                        tilt_deg: float) -> Tuple[float, float]:
    """Axis-aligned (width, height) in staff spaces of an oval with the given
    long (`width_sp`) and short (`height_sp`) axes, its long axis tilted
    `tilt_deg` up-and-right from horizontal (the sign does not change the
    extents)."""
    a, b = width_sp / 2.0, height_sp / 2.0
    t = math.radians(tilt_deg)
    c, s = math.cos(t), math.sin(t)
    return (2.0 * math.hypot(a * c, b * s), 2.0 * math.hypot(a * s, b * c))


def standard_box_at(cx: float, cy: float, spacing: float, width_sp: float,
                    height_sp: float, tilt_deg: float
                    ) -> Tuple[float, float, float, float]:
    """The standard box (x0, y0, x1, y1), page px, centred at (cx, cy)."""
    w_sp, h_sp = oval_extents_spaces(width_sp, height_sp, tilt_deg)
    hw, hh = w_sp * spacing / 2.0, h_sp * spacing / 2.0
    return (cx - hw, cy - hh, cx + hw, cy + hh)


def search_centre(gray, detector_box: Sequence[float], spacing: float,
                  templates, kind: Optional[str],
                  exclude_boxes: Optional[Sequence[tuple]] = None
                  ) -> Optional[Dict]:
    """The template's free position search (no ledger input, no refine)."""
    return ht.match_head_template(
        gray, tuple(detector_box), spacing, templates,
        exclude_boxes=list(exclude_boxes) if exclude_boxes else None,
        kind=kind, dx_range_spaces=DX_RANGE_SPACES, head_ink_mode="opening",
        decide="staged", line_term="coverage")


def standard_head_box(gray, detector_box: Sequence[float], spacing: float,
                      templates, shape: Dict, kind: Optional[str],
                      exclude_boxes: Optional[Sequence[tuple]] = None
                      ) -> Dict:
    """`shape` = dict(width_sp, height_sp, tilt_deg) measured on the page.
    Returns dict(box, centre, size_sp, match). Where the search returns
    nothing the centre stays the detector box's own (`placed=False`)."""
    x0, y0, x1, y1 = detector_box
    dcx, dcy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    match = search_centre(gray, detector_box, spacing, templates, kind,
                          exclude_boxes)
    placed = bool(match) and match.get("center_y") is not None
    cx = match.get("center_x", dcx) if placed else dcx
    cy = match["center_y"] if placed else dcy
    box = standard_box_at(cx, cy, spacing, shape["width_sp"],
                          shape["height_sp"], shape["tilt_deg"])
    return dict(box=box, centre=(cx, cy), placed=placed,
                size_sp=oval_extents_spaces(shape["width_sp"],
                                            shape["height_sp"],
                                            shape["tilt_deg"]),
                match=match)


# ---------------------------------------------------------------------------
# Hollow heads (lane `lane-standard-box-hollow`, 2026-10-04): a half note's
# ink has a white COUNTER, and the template, its fit gate and the IoU are all
# FILLED-oval things. Fill the counter first; where the ring is OPEN (a gap in
# the wall -- Sean: a common printing error) close it first.
#
# Every size is a measured quantity (page staff-line thickness `t`, the page's
# measured head axes, the staff spacing):
#   closing disc diameter  2*t + 1 px   -- a gap in the ring's wall that the
#                          wall's own stroke could span twice over; wider is
#                          not a gap in a wall, it is a different mark. Used
#                          ONLY for a head the detector called hollow (a head
#                          that is black has no wall to repair).
#   counter's largest inscribed radius <= (short_axis*spacing - 2*t) / 2 --
#                          the head's short axis less its two wall strokes; a
#                          bigger white pocket is the space between head and
#                          stem / ledger, never a counter.
#   counter's smallest inscribed radius >= t/4 + 0.5 px -- an inscribed
#                          diameter of half a stroke plus a pixel; below that
#                          is scan speckle (a 1-pixel hole has r = 1.0 on the
#                          distance transform, a real counter 1.9-2.9).
#   counter area <= the inner oval's area (long-2t)(short-2t)/(long*short) of
#                          the head's oval.
#   position: a head the detector called HOLLOW -- the pocket centre within
#                          0.5 spacing of the detector box (its box may hold
#                          only half the head) if the counter is enclosed as
#                          printed, inside the box itself if it exists only
#                          after closing (slivers closing adds next to a stem
#                          are not counters); a head it called FILLED -- the
#                          pocket centre inside the box itself, enclosed
#                          WITHOUT closing (the detector's black class is
#                          overridden only by a counter that is plainly there).
# A head with no qualifying pocket gets its own `gray` object back, untouched.
# ---------------------------------------------------------------------------
try:  # cv2 is a product dependency; keep the oval helpers importable without it
    import cv2
    import numpy as np
except Exception:  # pragma: no cover
    cv2 = None
    np = None

CLOSE_DIAMETER_STROKES = 2       # closing disc = 2 strokes + 1 px
COUNTER_SEARCH_MARGIN_SPACES = 1.5
HOLLOW_CENTRE_MARGIN_SPACES = 0.5


def _enclosed_white(ink_u8):
    """White (0) regions of `ink_u8` that do not touch the window's border."""
    inv = (1 - ink_u8).astype(np.uint8)
    n, lab = cv2.connectedComponents(inv, connectivity=4)
    border = set(np.unique(np.concatenate([lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])).tolist())
    enc = np.zeros(ink_u8.shape, bool)
    for i in range(1, n):
        if i not in border:
            enc |= lab == i
    return enc


def counter_pockets(gray, detector_box: Sequence[float], spacing: float,
                    thickness: float, head_short_sp: float,
                    head_long_sp: float, hollow_class: bool) -> Dict:
    """Find the white counter of the head in `detector_box`. Returns
    dict(mask, window, pockets=[dict(area, r_max, centre)], close_diameter,
    r_cap, r_floor); `pockets` empty = this head has no counter."""
    x0, y0, x1, y1 = [float(v) for v in detector_box]
    H, W = gray.shape
    m = int(round(COUNTER_SEARCH_MARGIN_SPACES * spacing))
    wx0, wy0 = max(0, int(x0) - m), max(0, int(y0) - m)
    wx1, wy1 = min(W, int(x1) + m + 1), min(H, int(y1) + m + 1)
    win = gray[wy0:wy1, wx0:wx1]
    ink = (win <= float(ht._otsu_threshold(win))).astype(np.uint8)
    t = max(1, int(round(thickness)))
    d = CLOSE_DIAMETER_STROKES * t + 1
    enclosed = _enclosed_white(ink)
    raw_enc = enclosed
    if hollow_class:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
        closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, k)
        newly = ((closed.astype(bool) | _enclosed_white(closed)) & ~ink.astype(bool))
    else:
        newly = enclosed
    newly = newly.astype(np.uint8)
    white_r = cv2.distanceTransform((1 - ink).astype(np.uint8), cv2.DIST_L2, 3)
    nn, cl, stats, cen = cv2.connectedComponentsWithStats(newly, connectivity=4)
    long_px, short_px = head_long_sp * spacing, head_short_sp * spacing
    r_cap = max(0.0, (short_px - 2.0 * t) / 2.0)
    r_floor = t / 4.0 + 0.5
    area_cap = math.pi * (long_px / 2.0) * (short_px / 2.0) \
        * max(0.0, (long_px - 2 * t) * (short_px - 2 * t)) / (long_px * short_px)
    cm = (HOLLOW_CENTRE_MARGIN_SPACES * spacing) if hollow_class else 0.0
    bx0, by0, bx1, by1 = x0 - wx0, y0 - wy0, x1 - wx0, y1 - wy0
    mask = np.zeros(ink.shape, bool)
    pockets = []
    for i in range(1, nn):
        comp = cl == i
        area = int(stats[i, cv2.CC_STAT_AREA])
        r_c = float(white_r[comp].max())
        cx, cy = float(cen[i][0]), float(cen[i][1])
        # a pocket that exists only AFTER closing (an open ring) must be centred
        # inside the detector box itself: the slivers closing adds between a
        # head and its stem lie outside it
        is_raw = bool(raw_enc[comp].all())
        cmi = cm if is_raw else 0.0
        inside = (bx0 - cmi <= cx <= bx1 + cmi) and (by0 - cmi <= cy <= by1 + cmi)
        if inside and 0 < area <= area_cap and r_floor <= r_c <= r_cap:
            mask |= comp
            pockets.append(dict(area=area, r_max=round(r_c, 2),
                                centre=(round(cx + wx0, 1), round(cy + wy0, 1)),
                                raw_enclosed=is_raw))
    return dict(mask=mask, window=(wx0, wy0, wx1, wy1), pockets=pockets,
                close_diameter=d if hollow_class else None,
                r_cap=round(r_cap, 2), r_floor=round(r_floor, 2))


def fill_counter(gray, detector_box: Sequence[float], spacing: float,
                 thickness: float, head_short_sp: float, head_long_sp: float,
                 hollow_class: bool):
    """`gray` with the head's counter painted as ink; the SAME object where
    the head has no counter (filled heads are bit-identical). Returns
    (gray_out, info)."""
    if cv2 is None or gray is None:
        return gray, dict(pockets=[])
    info = counter_pockets(gray, detector_box, spacing, thickness, head_short_sp,
                           head_long_sp, hollow_class)
    if not info["pockets"]:
        return gray, info
    wx0, wy0, wx1, wy1 = info["window"]
    out = gray.copy()
    out[wy0:wy1, wx0:wx1][info["mask"]] = 0
    return out, info
