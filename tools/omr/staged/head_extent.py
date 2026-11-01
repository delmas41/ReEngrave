"""A notehead's EXTENT and CENTRE from its own ink, the detector box only the seed -- ROADMAP 2.248 (STAGED GATHER).

Flag `OMR_HEAD_INK_EXTENT` (default OFF; allow-list until Sean's tiles: "1"/"true"/"yes"/"on" turns it on).

CAUSE (benchmarks/ink-extent-2026-10/FINDINGS.md): Sean's "box too small" heads on the 2.240/2.241 tiles are all (9 of 9) CELL-EDGE
TWINS -- the detector reads one staff's cell at a time, a head of the next staff pokes over the cell's edge, and the cut-off piece is
boxed as a head; the same head is boxed whole in its own staff's cell, and the reading refuses the piece (`clipped_fragment`). The tile
tool drew the piece's detector box. That alone is not a reading change. What IS read from the detector box is the head's STAFF
POSITION (`gather_notehead_positions`: the box's centre, rounded), and an only box cut short of its head moves its centre a step.

What this does (with the flag): the head's ink is read by 2.220's `head_ink.trim_head` (page raster, nothing erased; the box rows widened
by `ROW_SLACK_SPACES`, head-tall columns, bare line pixels out; it never takes a stem, a ledger -- a run longer than a head -- or a foreign
mark's ink). Where that ink is ONE head (`not_one_head` None), no taller than `MAX_INK_HEIGHT_SPACES`, holds the box's own centre row,
and runs into no other notehead box of the same cell (a chord-mate), the position is read from the INK's centre -- but only where the
rounded position differs from the box centre's (otherwise nothing moves). The detector's own position is kept on the row.

CONVENTION ASSUMED: a printed notehead is one oval about one staff space tall (SMuFL noteheadBlack 1.18 x 1.0 sp; Litolff 1.0-1.3,
Brahms 1.0-1.2 measured, 2.39); its staff position is its oval's centre. WHAT WOULD FALSIFY IT: Sean's tiles where the ink-centred
pitch is wrong and the box-centred one right (a head merged with a tie or slur end that the head-tall column test keeps).
NOT CONFIRMED: the height cap is read off our two plates and only narrows which heads may move.
"""
import os
from typing import Any, Dict, Optional, Sequence

ENV = "OMR_HEAD_INK_EXTENT"
#: A head's own ink at most this tall to move its position (SMuFL 1.0 sp; Litolff tilted heads to ~1.3; two stacked heads a second
#: apart measure ~1.5). A cut-off from two plates: it only NARROWS which heads may move.
MAX_INK_HEIGHT_SPACES = 1.35
#: Another notehead box of the cell overlapping the ink rows by more than this (sp) is a chord-mate the ink ran into.
MATE_OVERLAP_SPACES = 0.15
#: How many times the trimmed extent is fed back as the seed (each pass reaches 0.45 sp past the last).
MAX_PASSES = 4


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def ink_extent(page_binary: Any, box: Sequence[float], space_px: float,
               foreign_boxes: Sequence[Sequence[float]] = (),
               other_heads: Sequence[Sequence[float]] = ()) -> Dict[str, Any]:
    """The head's own ink extent grown from the detector page box `box` (x0, y0, x1, y1). Returns `extent` [x0, y0, x1, y1] (page px)
    or None, and `why` (None = usable as the head's extent for its centre): 'no_raster', 'no_head_ink', 'not_one_head:<why>',
    'too_tall', 'box_centre_outside', 'runs_into_another_head'."""
    from . import head_ink
    out: Dict[str, Any] = {"extent": None, "why": None, "height_sp": None, "passes": 0}
    if page_binary is None or not space_px:
        out["why"] = "no_raster"
        return out
    # GROWN FROM THE SEED: 2.220's trim reads the box's rows widened by `ROW_SLACK_SPACES` (0.45 sp) a side, so a box holding
    # half a head reaches only part of the rest. The trimmed extent is fed back as the next seed until it stops growing (a head
    # is at most ~1.3 sp, so `MAX_PASSES` passes reach any head from any piece of it); ink still growing past a head's height
    # is not one head (too_tall below).
    seed = tuple(float(v) for v in box)
    t = None
    for _ in range(MAX_PASSES):
        t2 = head_ink.trim_head(page_binary, seed, space_px, foreign_boxes)
        if t2 is None or t2.get("trimmed") is None:
            break
        t = t2
        out["passes"] += 1
        nxt = tuple(float(v) for v in t["trimmed"])
        if nxt == seed or (nxt[1] >= seed[1] and nxt[3] <= seed[3] and out["passes"] > 1):
            break
        if (nxt[3] - nxt[1]) > MAX_INK_HEIGHT_SPACES * float(space_px):
            break
        seed = nxt
    if t is None:
        out["why"] = "no_raster" if out["passes"] == 0 and head_ink.trim_head(page_binary, box, space_px) is None else "no_head_ink"
        return out
    x0, y0, x1, y1 = (float(v) for v in t["trimmed"])
    out["extent"] = [x0, y0, x1, y1]
    out["height_sp"] = round((y1 - y0) / float(space_px), 3)
    if t.get("not_one_head"):
        out["why"] = "not_one_head:%s" % t["not_one_head"]
        return out
    if (y1 - y0) > MAX_INK_HEIGHT_SPACES * float(space_px):
        out["why"] = "too_tall"
        return out
    cy = (float(box[1]) + float(box[3])) / 2.0
    if not (y0 <= cy <= y1):
        out["why"] = "box_centre_outside"
        return out
    for b in other_heads:
        if b[1] >= float(box[1]) - 1 and b[3] <= float(box[3]) + 1 and b[0] >= float(box[0]) - 1 and b[2] <= float(box[2]) + 1:
            continue                       # a box inside this one (a twin or a piece of the same head)
        ix = min(x1, b[2]) - max(x0, b[0])
        iy = min(y1, b[3]) - max(y0, b[1])
        if ix > 0 and iy > MATE_OVERLAP_SPACES * float(space_px):
            out["why"] = "runs_into_another_head"
            return out
    return out


def ink_position(pos_box: float, box: Sequence[float], extent: Sequence[float], half_step_page: float) -> Optional[float]:
    """The staff position of the ink's centre, from the box centre's position `pos_box` and the page-px offset between the centres
    (positions grow downward, one per half staff space). None where the rounded position does not change (nothing moves)."""
    if not half_step_page or half_step_page <= 0:
        return None
    d = ((float(extent[1]) + float(extent[3])) / 2.0 - (float(box[1]) + float(box[3])) / 2.0) / float(half_step_page)
    p = float(pos_box) + d
    return p if int(round(p)) != int(round(float(pos_box))) else None
