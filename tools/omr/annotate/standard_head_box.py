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
