"""A hollow head's staff position from its own HOLE where its detector box does not centre on it -- ROADMAP 2.252 r4 (STAGED GATHER).

Flag `OMR_HEAD_HOLE_POSITION` (default ON since 2.252 r6, 2026-11-03; "0"/"false"/"no"/"off" turns it off).

CAUSE (benchmarks/omr-arc-binding-2026-10/FINDINGS.md, 2.252 r4 census): of the printed ties we still write as slurs or refuse, the
largest share have a head whose STAFF POSITION was read at its detector BOX's centre while the box does not centre on the head: a box
cut short of the head (CLIPPED, the box holds the lower or upper part of the oval) or a box drawn round the head AND its stem (TALL,
Litolff p10 `10/0/4/0/9`, 3.2 heads tall). `gather_notehead_positions` reads the position at the box centre; 2.39b's re-centre trusts
any box at least 0.7 of a head in width and height (`box_already_head_sized`), and 2.248's ink extent (OFF) refuses Litolff hollow heads
(their ink with the lines through it measures 1.4-1.5 sp, `too_tall`) and every TALL box (`box_centre_outside`). The tie's two heads
then read two positions, and the tie is written as a slur (`page_binding_different_pitch`) or refused (`tie_pitch_contradiction`).

What this does (with the flag), only for a REGULAR head box (half or black class -- the detector calls hollow heads black; a black
head has no hole, so the hole is the evidence): the white HOLES inside the box are read the way
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
#: the head's own ink at least this wide (staff spaces; a Litolff/Brahms head is 1.3-1.7 wide): a narrower mark is not a head
MIN_INK_WIDTH_SPACES = 1.0


def enabled() -> bool:
    # ROADMAP 2.252 r6 (Sean, 2026-11-03): default ON, deny-list ("0"/"false"/"no"/"off" turns it off)
    return os.environ.get(ENV, "").strip().lower() not in ("0", "false", "no", "off")


#: ROADMAP 2.252 r5: the round-5 revisions ride on the same flag (default ON since r6; Sean's r4 tiles 4, 6, 7, 9 and the r4 loss census)
def r5_enabled() -> bool:
    return enabled()


#: ROADMAP 2.252 r6: the round-6 revisions ride on the same flag (default ON): the neighbour-piece refusal removed; an arc box's staff
#: line found locally (`gather.arc_ink_shape(local_lines=)`); a tie whose one end's position is unsure (`export`, `ownership`)
def r6_enabled() -> bool:
    return enabled()


def contested_position(detail: Optional[Dict[str, Any]], value: Any = None) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.252 r6: a head whose OWN two readings name two adjacent positions -- its box (or ink) centre wrote one, its single
    hole (refused as a move: off the grid, or the ink witness disagreeing) stands at the other. `{"why", "own", "alternative", "hole"}`,
    or None where the head's position is not contested by its own ink (no hole read, a hole on the written position, a head placed BY
    its hole or by 2.73's line cut). Reads `Q.NOTEHEAD_STAFF_POSITION`'s detail only; decides nothing (the tie is not a witness here)."""
    d = detail or {}
    if "from_head_hole" in d or "from_head_cut" in d or not d.get("hole_refused"):
        return None
    hs = d.get("hole_steps") or ()
    if len(hs) != 1:
        return None
    try:
        own = int(d["rounded"]) if d.get("rounded") is not None else int(round(float(value)))
        alt = int(round(float(hs[0])))
    except (TypeError, ValueError):
        return None
    if abs(alt - own) != 1:
        return None
    return {"why": "hole_disagrees_with_box:" + str(d.get("hole_refused")), "own": own, "alternative": alt,
            "hole": round(float(hs[0]), 3)}


#: r5: a head's own ink at most this tall (staff spaces) is ONE head even where an arc's end makes it too wide (2.248's own cut-off)
ONE_HEAD_TALL_SPACES = 1.35


def is_candidate(cls: Any) -> bool:
    """A REGULAR head class, half or black: the detector calls hollow heads black (Litolff p11 `11/1/3/12/1`), and a black head has
    no hole, so the hole itself is the evidence; never a grace/cue or whole class."""
    from .geometry import is_regular_notehead
    return is_regular_notehead(str(cls or ""))


def hole_position(cell_image: Any, box_c: Sequence[float], half_step_c: float, staff_top_c: float,
                  line_ys_c: Sequence[float], pos_box: float, page_binary: Any, page_box: Optional[Sequence[float]],
                  half_step_page: Optional[float], other_heads_c: Sequence[Sequence[float]] = ()) -> Dict[str, Any]:
    """`{"position": float or None, "why": None or the refusal, ...the numbers}`. `box_c` (x0, y0, x1, y1) and the grid are the cell's
    canonical frame; `page_box` / `half_step_page` the same box on the page raster (for the ink witness). `position` is None where nothing
    moves: 'no_raster', 'holes:<n>' (not exactly one), 'off_grid', 'same_position', 'off_staff', 'ink_unread', 'ink_disagrees',
    ('cut_piece_in_another_head', r5, removed in r6). `other_heads_c`: the cell's OTHER head boxes, canonical (x0, y0, x1, y1)."""
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
    # ROADMAP 2.252 r6: r5's refusal of a cut slit one of whose two pieces another head box of the cell holds
    # (`cut_piece_in_another_head`) is GONE. Its premise -- that second box is a neighbour head a third away -- was wrong on every
    # firing Sean judged: Litolff p3 `3/1/2/7/0` (r5 tile 8) is ON the top line, p2 `2/1/4/0/8` (tile 9) on the top line, p3
    # `3/1/5/5/4` (tile 10) on the second line from the bottom: each second box is a DUPLICATE cut over the same head (the detector
    # boxed its upper or lower half), and the hole the line cut was the head's. `other_heads_c` is kept on the signature (callers).
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
    # ... and that ink is ONE head, about a head wide (r4 move sheet: a gap between two black heads of a second, and a narrow mark,
    # each held one "hole"; 2.220's own `not_one_head` and the width refuse both)
    ext = t.get("extent_sp") or [0.0, 0.0]
    out["ink_extent_sp"] = ext
    if t.get("not_one_head") and not (r5_enabled() and t.get("not_one_head") == "too_wide"
                                      and float(ext[1] or 99.0) <= ONE_HEAD_TALL_SPACES):
        # r5: ink one head TALL but too WIDE is a head with an arc's end or a neighbour run into its side (Litolff p10 `10/0/3/1/7`,
        # a tie's end on the head: 1.84 sp wide, 1.14 tall) -- its height still says one head, and its centre is still read
        out["why"] = "ink_not_one_head"
        return out
    if float(ext[0]) < MIN_INK_WIDTH_SPACES:
        out["why"] = "ink_too_narrow"
        return out
    tr = t["trimmed"]
    ink_pos = float(pos_box) + ((float(tr[1]) + float(tr[3])) / 2.0 - (float(page_box[1]) + float(page_box[3])) / 2.0) / float(half_step_page)
    out["ink_position"] = round(ink_pos, 3)
    if int(round(ink_pos)) != int(round(step)):
        out["why"] = "ink_disagrees"
        return out
    out["position"] = step
    return out
