"""A hollow head's staff position from its own HOLE where its detector box does not centre on it -- ROADMAP 2.252 r4 (STAGED GATHER).

Flag `OMR_HEAD_HOLE_POSITION` (default OFF; "1"/"true"/"yes"/"on" turns it on).

CAUSE (benchmarks/omr-arc-binding-2026-10/FINDINGS.md, 2.252 r4 census): of the printed ties we still write as slurs or refuse, the
largest share have a head whose STAFF POSITION was read at its detector BOX's centre while the box does not centre on the head: a box
cut short of the head (CLIPPED, the box holds the lower or upper part of the oval) or a box drawn round the head AND its stem (TALL,
Litolff p10 `10/0/4/0/9`, 3.2 heads tall). `gather_notehead_positions` reads the position at the box centre; 2.39b's re-centre trusts
any box at least 0.7 of a head in width and height (`box_already_head_sized`), and 2.248's ink extent (OFF) refuses Litolff hollow heads
(their ink with the lines through it measures 1.4-1.5 sp, `too_tall`) and every TALL box (`box_centre_outside`). The tie's two heads
then read two positions, and the tie is written as a slur (`page_binding_different_pitch`) or refused (`tie_pitch_contradiction`).

What this does (with the flag), only for a REGULAR HOLLOW head box (`noteheadHalf*`): the white HOLES inside the box are read the way
2.252's tall-box split reads them (`box_kind.head_holes`, cell raster WITH its staff lines; two slit pieces either side of one line are
one hole at that line). Where there is exactly ONE hole on the position grid, and the head's own ink (2.220's `head_ink.trim_head`, page
raster) has its centre at the same rounded position (a second reading of the same ink: it can only NARROW), and that position differs
from the box centre's, the hole's position is the head's. Nothing moves sideways; nothing moves outside the staff (first space above to
first space below, 2.248's `STAFF_POSITIONS`: a far head is placed by its ledger lines only, page-facts); 2.73's line-cut position is
never overridden; the detector's own position stays on the row (`detector_position_float`, `from_head_hole`).

CONVENTION ASSUMED: a hollow head's hole is at its centre (2.252 r1); its staff position is its oval's centre (page-facts, 2.248).
WHAT WOULD FALSIFY IT: Sean's tiles where a moved head was right at the box centre; a hole that is paper enclosed by a stem, an arc or
a neighbour (not the head's own). NOT CONFIRMED: measured on two plates.
"""
import os
from typing import Any, Dict, Optional, Sequence

ENV = "OMR_HEAD_HOLE_POSITION"
#: how far past the box's top and bottom (staff spaces) a hole's centre may stand (a clipped box can stop at the hole)
REACH_SPACES = 0.25


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def is_hollow(cls: Any) -> bool:
    from .geometry import is_regular_notehead
    c = str(cls or "")
    return c.startswith("noteheadHalf") and is_regular_notehead(c)


def hole_position(cell_image: Any, box_c: Sequence[float], half_step_c: float, staff_top_c: float,
                  line_ys_c: Sequence[float], pos_box: float, page_binary: Any, page_box: Optional[Sequence[float]],
                  half_step_page: Optional[float]) -> Dict[str, Any]:
    """`{"position": float or None, "why": None or the refusal, ...the numbers}`. `box_c` (x0, y0, x1, y1) and the grid are the cell's
    canonical frame; `page_box` / `half_step_page` the same box on the page raster (for the ink witness). `position` is None where nothing
    moves: 'no_raster', 'holes:<n>' (not exactly one), 'off_grid', 'same_position', 'off_staff', 'ink_unread', 'ink_disagrees'."""
    from . import box_kind as K
    from .head_extent import STAFF_POSITIONS
    out: Dict[str, Any] = {"position": None, "why": None}
    if cell_image is None or not half_step_c or half_step_c <= 0:
        out["why"] = "no_raster"
        return out
    # a CLIPPED box can stop at its head's hole: the hole's centre is looked for up to `REACH_SPACES` past the box's top and bottom
    # (a neighbour's hole a step away is then a SECOND hole, and nothing is read)
    reach = REACH_SPACES * 2.0 * float(half_step_c)
    grown = (float(box_c[0]), float(box_c[1]) - reach, float(box_c[2]), float(box_c[3]) + reach)
    holes = K.head_holes(K.cell_ink(cell_image), grown, 2.0 * float(half_step_c), float(staff_top_c), list(line_ys_c or ()))
    out["holes"] = [h["step"] for h in holes]
    if len(holes) != 1:
        out["why"] = "holes:%d" % len(holes)
        return out
    step = float(holes[0]["step"])
    if abs(step - round(step)) > K.HOLE_GRID_TOL_STEPS:
        out["why"] = "off_grid"
        return out
    if int(round(step)) == int(round(float(pos_box))):
        out["why"] = "same_position"
        return out
    lo, hi = STAFF_POSITIONS
    if not (lo - 0.5 < step < hi + 0.5):
        out["why"] = "off_staff"
        return out
    # the second reading of the same ink: the head's own ink centre (page raster) at the same rounded position
    from . import head_ink
    t = head_ink.trim_head(page_binary, page_box, 2.0 * float(half_step_page or 0.0)) \
        if (page_binary is not None and page_box is not None and half_step_page) else None
    if not t or t.get("trimmed") is None:
        out["why"] = "ink_unread"
        return out
    tr = t["trimmed"]
    ink_pos = float(pos_box) + ((float(tr[1]) + float(tr[3])) / 2.0 - (float(page_box[1]) + float(page_box[3])) / 2.0) / float(half_step_page)
    out["ink_position"] = round(ink_pos, 3)
    if int(round(ink_pos)) != int(round(step)):
        out["why"] = "ink_disagrees"
        return out
    out["position"] = step
    return out
