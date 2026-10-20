"""The claimed-area REGISTER -- ROADMAP 2.181 (docs/plan-2026-10-20-claimed-area.md §3, §7 step 2). Flag `OMR_CLAIMED_REGISTER`, default OFF.

PATH: STAGED. PURE helpers (a page raster and boxes in, numbers out; no log, no cell, no quantity named): `gather.gather_claimed_register`
is the GATHER stage that files the rows, `adjudicators/claimed_by.py` is the one ADJUDICATE consult. Registered in `reach.NOT_A_STAGE`.

## What the register is, in plain words

A mark read from the big picture (a clef, the system's header column, a printed meter) CLAIMS the space it is printed in. The claim is
ONE quantity, `Q.CLAIMED_AREA`, filed on the STAFF, one row per claim, every row the same shape:

    value   the claimed area, page px [x0, y0, x1, y1]
    detail  owner      `clef` | `leading_column` | `meter` (2.177 files `meter`)
            owner_row  the read the claim rests on (a `Q.CLEF_LOCATED` / `Q.GLYPH_BOX` row id), or None
            unit       `area`
            standing   READ (the owner was read) or NARROWED (one witness only: the claim may narrow a box, never refuse it)
            prior      True where the claim rests on a convention Sean called "not normally" (the header column, 2026-10-20):
                       a box there is refused only where ITS OWN INK is line-shaped (barline / bracket / brace stroke); else narrowed
            cell       the cell the claim stands in
            boxes_inside {glyph subject key: {ink_share_inside, inside_px, ink_px, cls[, named][, through]}}
                       for every other box of that cell whose box meets the area -- MEASURED here, read by the consult

`covering(rows, key)` lists the claims that hold a box's ink; it decides nothing. The consult (ADJUDICATE) asks the plan's EVALUATE
question -- does a refusal FOLLOW? -- and answers REFUSE (`claimed_by:<owner>`), NARROW (written blue, both readings carried) or
nothing. A claim is consulted, never erased: no raster is changed.

CONVENTION ASSUMED: nothing but a clef's own ink stands inside the clef's box; nothing but the system barline, bracket, brace and
instrument name stands left of the first clef (Sean 2026-10-20: "idk possibly but not normally" -- a PRIOR, so it narrows unless the
box's own ink is a line). WHAT WOULD FALSIFY IT: a print-confirmed note inside a READ clef area, or a note left of the first clef
whose ink passes the line test. NOT CONFIRMED beyond the two plates; blind tiles `out/print/2.181-review/`.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ENV = "OMR_CLAIMED_REGISTER"

#: share of a box's own ink (bare staff-line runs left out) that must lie inside a claim for the claim to hold the box
#: (the 2.177 meter cut, one cut for every owner: a mark's own piece is wholly inside, ~1.0; a neighbour shares a sliver)
INSIDE_SHARE_MIN = 0.5
#: a detector clef box claims only where it is clef-sized (2.144: the short wide `clef*` boxes, 0.5-1.1 sp, lie on arcs and clutter)
CLEF_BOX_MIN_HEIGHT_SPACES = 2.0
#: a detector clef box is READ where it starts this close to its cell's left edge (a clef stands at a bar's start; 2.176's window);
#: farther into the bar it is the detector's word alone (2.144's mid-bar case, Sean's tile 4 a real eighth in a false clefG box): NARROWED
CLEF_WINDOW_SPACES = 6.0
#: the header column reaches this far left of the staff's start (the bracket and brace stand left of the system barline)
COLUMN_LEFT_REACH_SPACES = 2.0
#: the line test: a column of the box's ink covering this share of the box's own rows ...
THROUGH_COVER_MIN = 0.9
#: ... that goes on past the box's top or bottom edge for this many staff spaces (a barline / bracket / brace stroke runs on; a head stops)
THROUGH_BEYOND_SPACES = 0.5

OWNER_CLEF = "clef"
OWNER_COLUMN = "leading_column"
OWNER_METER = "meter"
OWNERS = (OWNER_CLEF, OWNER_COLUMN, OWNER_METER)
#: classes that are owners' own ink, never measured as a box inside a claim
OWNER_CLASS_PREFIXES = ("clef", "gClef", "fClef", "cClef", "timeSig", "key", "brace", "bracket")


def enabled() -> bool:
    """`OMR_CLAIMED_REGISTER`, default OFF (ROADMAP 2.181, until Sean's blind tiles); only an explicit 1/true/yes/on enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def is_owner_class(name: Any) -> bool:
    return str(name).startswith(OWNER_CLASS_PREFIXES)


def is_clef_box(name: Any, box: Optional[Sequence[float]], spacing: float) -> bool:
    """A detector box the register may file as a clef claim: a `clef*` class, clef-sized."""
    if not str(name).startswith("clef") or not box or not spacing:
        return False
    return (box[3] - box[1]) / spacing >= CLEF_BOX_MIN_HEIGHT_SPACES


def clef_box_standing(box: Sequence[float], cell_box: Sequence[float], spacing: float) -> str:
    """READ where the clef box starts within `CLEF_WINDOW_SPACES` of its cell's left edge, else NARROWED."""
    return "READ" if (box[0] - cell_box[0]) / spacing <= CLEF_WINDOW_SPACES else "NARROWED"


def overlaps(a: Sequence[float], b: Sequence[float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def leading_column(cell_box: Sequence[float], clef_left_x: float, spacing: float) -> Optional[List[float]]:
    """The header column of ONE staff: from `COLUMN_LEFT_REACH_SPACES` left of the staff's start (cell 0's left edge) to the first
    clef's left edge, the cell's own height. None where the clef stands at or left of the staff's start (nothing to claim)."""
    x0 = float(cell_box[0]) - COLUMN_LEFT_REACH_SPACES * spacing
    if clef_left_x <= float(cell_box[0]):
        return None
    return [round(x0, 1), float(cell_box[1]), round(float(clef_left_x), 1), float(cell_box[3])]


def through_stroke(binary: Any, box: Sequence[float], spacing: float) -> Optional[Dict[str, Any]]:
    """The line test on a box's OWN ink: the best column inside the box, its ink cover of the box's rows, and how far (staff spaces)
    the ink runs on past the box's top and bottom edges in that column (gaps of up to 2 px bridged). `through` is True where the cover
    is at least `THROUGH_COVER_MIN` and the stroke runs on at least `THROUGH_BEYOND_SPACES` past one edge. None off the raster."""
    import numpy as np
    if binary is None or getattr(binary, "ndim", 0) != 2 or not spacing:
        return None
    H, W = binary.shape
    x0, y0 = max(0, int(box[0])), max(0, int(box[1]))
    x1, y1 = min(W, int(round(box[2]))), min(H, int(round(box[3])))
    if x1 - x0 < 1 or y1 - y0 < 2:
        return None
    reach = int(round(3 * spacing))
    ink = binary[:, x0:x1] == 0
    inner = ink[y0:y1]
    cover = inner.mean(axis=0)
    best = None
    for c in np.argsort(-cover)[:6]:
        col = ink[:, c]

        def _run(start: int, step: int) -> int:
            n, gap, y = 0, 0, start
            while 0 <= y < H and n + gap < reach:
                if col[y]:
                    n += gap + 1
                    gap = 0
                else:
                    gap += 1
                    if gap > 2:
                        break
                y += step
            return n
        up, down = _run(y0 - 1, -1), _run(y1, 1)
        beyond = max(up, down) / spacing
        cand = (float(cover[c]), beyond, up / spacing, down / spacing, int(c) + x0)
        if best is None or (cand[0] >= THROUGH_COVER_MIN, cand[1]) > (best[0] >= THROUGH_COVER_MIN, best[1]):
            best = cand
    cov, beyond, up, down, cx = best
    return {"through": bool(cov >= THROUGH_COVER_MIN and beyond >= THROUGH_BEYOND_SPACES), "column_cover": round(cov, 3),
            "beyond_up_spaces": round(up, 2), "beyond_down_spaces": round(down, 2), "column_x": cx}


def covering(rows: Iterable[Any], key: str) -> List[Tuple[Any, Dict[str, Any]]]:
    """Every `Q.CLAIMED_AREA` row (any owner) that holds the box `key`: its entry names the box (`named`, the owner itself said this
    box is its ink) or measured at least `INSIDE_SHARE_MIN` of the box's own ink inside the area. Decides nothing."""
    out = []
    for r in rows:
        d = getattr(r, "detail", None) or {}
        if d.get("unit") != "area" or d.get("owner") not in OWNERS:
            continue
        got = (d.get("boxes_inside") or {}).get(key)
        if not got:
            continue
        if got.get("named") or float(got.get("ink_share_inside", 0.0)) >= INSIDE_SHARE_MIN:
            out.append((r, got))
    return out
