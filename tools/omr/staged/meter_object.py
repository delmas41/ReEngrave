"""The printed meter as ONE object -- ROADMAP 2.177 (STAGED GATHER measurement; decides nothing).

Sean, 2026-10-20: *"we need a real fix for digit meter- Something that sees the meter as 2 numbers and blocks the whole thing out
and thepulls out the 2 numbers and doesnt allow anything else to box that area."*

CONVENTION: a printed time signature is two bold numerals standing one above the other in ONE column -- the upper in the staff's
upper two spaces, the lower in its lower two -- or one C / cut-C; it stands between the key signature and the first note (or right
after a barline, for a change). WHAT WOULD FALSIFY IT: a print-confirmed note head standing on numeral ink; numerals printed side by
side. NOT CONFIRMED beyond the two plates measured in `benchmarks/omr-meter-object-2026-10/FINDINGS.md`.

PURE: a page raster (0 == ink, staff lines in), the staff's five line rows and a staff space in, numbers out. No log, no cell, no
quantity named -- `gather.gather_meter_object` is its stage; `notehead_precision` / `family_precision` read its row's constants.

`find(...)`: the numeral pair's ink and the area drawn around it, or a named reason it could not be drawn (never a guess). The
area is the union box of the numerals' own ink pieces (staff lines taken out), padded by one stroke width -- not a detector box, not a
column rule. `ink_inside(...)`: of another box's own ink (bare staff-line rows left out), the share that lies inside that area.
"""
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

#: ROADMAP 2.177 flag, default OFF: GATHER files `Q.METER_OBJECT` and ADJUDICATE refuses a box whose ink lies inside the area.
ENV = "OMR_METER_OBJECT"


def enabled() -> bool:
    """`OMR_METER_OBJECT`, default OFF (ROADMAP 2.177, until Sean's blind tiles); only an explicit 1/true/yes/on enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


# --- the numeral pair, in staff spaces (stated before the count; measured on the two plates, FINDINGS) ---
#: one numeral piece: height / width windows (a bold digit is ~1.6-2.2 tall and ~0.8-1.6 wide; a two-digit numeral doubles the width)
NUMERAL_H_SPACES = (1.0, 2.7)
NUMERAL_W_SPACES = (0.35, 1.9)
#: the two numerals' centres stand in one column
PAIR_X_TOL_SPACES = 0.55
#: ... and the whole pair spans this many spaces (4 for a digit pair; a single C is shorter)
PAIR_H_SPACES = (2.6, 4.8)
#: a pair whose pieces fused (the staff-line erase leaves a thin join): one piece of this size, with a waist (see `_has_waist`)
MERGED_H_SPACES = (3.0, 4.8)
MERGED_W_SPACES = (1.2, 2.8)
#: ink pixels / box pixels of a fused pair (measured Litolff 2/4: 0.66; flats 0.46, stemmed notes ~0.2)
MERGED_FILL_MIN = 0.5
#: one C / cut-C piece
COMMON_H_SPACES = (1.8, 3.4)
COMMON_W_SPACES = (1.0, 2.4)
#: the area is padded by this many staff-line thicknesses
PAD_STROKES = 1.0
#: a piece that fills more than this width is a merged neighbour (clef, key accidental, barline, bar's first note)
AREA_W_MAX_SPACES = 2.8
#: the vertical band read: this far above the top line and below the bottom line
BAND_SPACES = 1.25
#: a pixel run lying wholly within this many pixels of a staff line, at most this long, is bare line (not numeral ink)
LINE_RUN_SLACK_PX = 2
LINE_TILT_PX = 3


def _line_thickness(binary: Any, line_ys: Sequence[float], x_lo: int, x_hi: int) -> float:
    """Median vertical run of ink through the five line rows over the window's columns (a stroke's thickness in px)."""
    import numpy as np
    runs = []
    H = binary.shape[0]
    for ly in line_ys:
        y = int(round(ly))
        if not (2 <= y < H - 2):
            continue
        cols = np.nonzero(binary[y, x_lo:x_hi] == 0)[0]
        for c in cols[:: max(1, len(cols) // 40)]:
            c = x_lo + int(c)
            top = y
            while top > 0 and binary[top - 1, c] == 0:
                top -= 1
            bot = y
            while bot < H - 1 and binary[bot + 1, c] == 0:
                bot += 1
            runs.append(bot - top + 1)
    if not runs:
        return 3.0
    runs.sort()
    return float(runs[len(runs) // 2])


def _ink_without_bare_lines(binary: Any, line_ys: Sequence[float], y0: int, y1: int, x0: int, x1: int, thick: float):
    """Boolean ink of the window with every vertical ink run that lies WHOLLY on a staff line left out (a stroke crossing the line
    is kept whole: a digit's strokes merge with the line it crosses)."""
    import numpy as np
    ink = (binary[y0:y1, x0:x1] == 0).copy()
    lines = [float(v) - y0 for v in line_ys]
    reach = thick / 2.0 + LINE_RUN_SLACK_PX + LINE_TILT_PX
    for c in range(ink.shape[1]):
        col = ink[:, c]
        ys = np.nonzero(col)[0]
        if len(ys) == 0:
            continue
        start = prev = int(ys[0])
        for y in list(ys[1:]) + [None]:
            if y is not None and int(y) == prev + 1:
                prev = int(y)
                continue
            n = prev - start + 1
            mid = (start + prev) / 2.0
            if n <= thick + 2 * LINE_RUN_SLACK_PX and any(abs(mid - ly) <= reach and start >= ly - reach and prev <= ly + reach
                                                          for ly in lines):
                col[start:prev + 1] = False
            if y is not None:
                start = prev = int(y)
    return ink


def _pieces(ink: Any):
    """Connected pieces (8-connected, after a 1-px close) of a boolean image: [(x0, y0, x1, y1, area)] in window pixels."""
    import cv2
    import numpy as np
    img = ink.astype("uint8")
    img = cv2.morphologyEx(img, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    n, labels, stats, _c = cv2.connectedComponentsWithStats(img, connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, a = (int(v) for v in stats[i])
        out.append((x, y, x + w, y + h, a))
    return out


def _is_dense(piece: Tuple[int, int, int, int, int]) -> bool:
    """A fused numeral pair is MASS (bold digits fill ~0.6 of their box); a stemmed note (a thin stem and one head), a flat or a sharp
    fill ~0.2-0.45. Used only on pieces of a pair's size."""
    x0, y0, x1, y1, a = piece
    box = max(1, (x1 - x0) * (y1 - y0))
    return a / float(box) >= MERGED_FILL_MIN


def find(binary: Any, line_ys: Sequence[float], spacing: float, x_lo: float, x_hi: float,
         *, keep_left_of: Optional[float] = None, common_box: Optional[Sequence[float]] = None) -> Dict[str, Any]:
    """The meter's numeral pair inside the page-pixel column `[x_lo, x_hi)` of ONE staff, or a named reason it could not be drawn.

    Returns `{"found": True, "form", "area": [x0, y0, x1, y1] (page px), "pieces": [[x0, y0, x1, y1], ...], "thickness_px", ...}` or
    `{"found": False, "reason": "no_pair" | "no_raster" | "no_staff_geometry" | "merged_with_neighbour", ...}`. The leftmost pair wins (the
    numerals stand before every note of the bar). `keep_left_of`: a page x; a pair whose area would start left of it is not drawn.
    `common_box`: the detector's `timeSigCommon` / `timeSigCutCommon` box (page px); only with it is a lone C-sized piece taken, and only the
    piece lying on that box (a C is not told from a flat or a clef by shape alone).
    """
    if binary is None or getattr(binary, "ndim", 0) != 2:
        return {"found": False, "reason": "no_raster"}
    if len(line_ys) < 5 or not spacing or spacing <= 0:
        return {"found": False, "reason": "no_staff_geometry"}
    H, W = binary.shape
    sp = float(spacing)
    ly = [float(v) for v in line_ys]
    x0 = max(0, int(round(x_lo)))
    x1 = min(W, int(round(x_hi)))
    y0 = max(0, int(round(ly[0] - BAND_SPACES * sp)))
    y1 = min(H, int(round(ly[-1] + BAND_SPACES * sp)))
    if x1 - x0 < 4 or y1 - y0 < 8:
        return {"found": False, "reason": "no_raster"}
    thick = _line_thickness(binary, ly, x0, x1)
    ink = _ink_without_bare_lines(binary, ly, y0, y1, x0, x1, thick)
    pcs = _pieces(ink)
    mid_y = (ly[0] + ly[-1]) / 2.0 - y0

    def dims(p):
        return (p[2] - p[0]) / sp, (p[3] - p[1]) / sp

    numerals, merged, commons, too_wide = [], [], [], []
    for p in pcs:
        w, h = dims(p)
        if h > 5.2 or w > AREA_W_MAX_SPACES + 1.0:
            too_wide.append(p)
            continue
        if NUMERAL_H_SPACES[0] <= h <= NUMERAL_H_SPACES[1] and NUMERAL_W_SPACES[0] <= w <= NUMERAL_W_SPACES[1]:
            numerals.append(p)
        if MERGED_H_SPACES[0] <= h <= MERGED_H_SPACES[1] and MERGED_W_SPACES[0] <= w <= MERGED_W_SPACES[1] and _is_dense(p):
            merged.append(p)
        if common_box is not None and COMMON_H_SPACES[0] <= h <= COMMON_H_SPACES[1] and COMMON_W_SPACES[0] <= w <= COMMON_W_SPACES[1]:
            cx0, cy0, cx1, cy1 = p[0] + x0, p[1] + y0, p[2] + x0, p[3] + y0
            if cx0 < common_box[2] and cx1 > common_box[0] and cy0 < common_box[3] and cy1 > common_box[1]:
                commons.append(p)
    cands: List[Tuple[float, str, List[Tuple[int, int, int, int, int]]]] = []
    # two pieces: one centred in the upper half of the staff, one in the lower, one column
    ups = [p for p in numerals if (p[1] + p[3]) / 2.0 < mid_y]
    lows = [p for p in numerals if (p[1] + p[3]) / 2.0 >= mid_y]
    for u in ups:
        for lo in lows:
            if abs((u[0] + u[2]) / 2.0 - (lo[0] + lo[2]) / 2.0) / sp > PAIR_X_TOL_SPACES:
                continue
            top, bot = min(u[1], lo[1]), max(u[3], lo[3])
            if not (PAIR_H_SPACES[0] <= (bot - top) / sp <= PAIR_H_SPACES[1]):
                continue
            gap = (lo[1] - u[3]) / sp
            if gap > 1.0:
                continue
            cands.append((min(u[0], lo[0]), "stacked_pair", [u, lo]))
    for m in merged:
        cands.append((m[0], "merged_pair", [m]))
    if not cands:
        for c in commons:
            cands.append((c[0], "common", [c]))
    if not cands:
        return {"found": False, "reason": "no_pair", "pieces_seen": len(pcs), "too_big_pieces": len(too_wide)}
    cands.sort(key=lambda t: t[0])
    x_left, form, parts = cands[0]
    ax0 = min(p[0] for p in parts) + x0
    ay0 = min(p[1] for p in parts) + y0
    ax1 = max(p[2] for p in parts) + x0
    ay1 = max(p[3] for p in parts) + y0
    pad = PAD_STROKES * thick
    area = [ax0 - pad, ay0 - pad, ax1 + pad, ay1 + pad]
    if (area[2] - area[0]) / sp > AREA_W_MAX_SPACES:
        return {"found": False, "reason": "merged_with_neighbour", "width_spaces": round((area[2] - area[0]) / sp, 3)}
    if keep_left_of is not None and area[0] < keep_left_of:
        return {"found": False, "reason": "merged_with_neighbour", "left_of_limit_px": round(keep_left_of - area[0], 1)}
    # a wider neighbouring piece touching the area's edge is the clef / key accidental / barline this area must not swallow
    for p in too_wide:
        px0, py0, px1, py1 = p[0] + x0, p[1] + y0, p[2] + x0, p[3] + y0
        if px0 < ax1 and px1 > ax0 and py0 < ay1 and py1 > ay0:
            return {"found": False, "reason": "merged_with_neighbour", "note": "a piece too big for a numeral overlaps the pair"}
    return {"found": True, "form": form, "area": [round(v, 1) for v in area],
            "pieces": [[p[0] + x0, p[1] + y0, p[2] + x0, p[3] + y0] for p in parts],
            "thickness_px": round(thick, 2), "width_spaces": round((area[2] - area[0]) / sp, 3),
            "height_spaces": round((area[3] - area[1]) / sp, 3)}


def ink_inside(binary: Any, box: Sequence[float], area: Sequence[float], line_ys: Sequence[float], spacing: float) -> Optional[Dict[str, Any]]:
    """Of the ink inside `box` (page px; bare staff-line runs left out), the share that lies inside `area`, or None (off the raster / no ink)."""
    if binary is None or getattr(binary, "ndim", 0) != 2 or len(line_ys) < 5 or not spacing:
        return None
    H, W = binary.shape
    bx0, by0 = max(0, int(box[0])), max(0, int(box[1]))
    bx1, by1 = min(W, int(round(box[2]))), min(H, int(round(box[3])))
    if bx1 - bx0 < 1 or by1 - by0 < 1:
        return None
    thick = _line_thickness(binary, line_ys, bx0, bx1)
    ink = _ink_without_bare_lines(binary, line_ys, by0, by1, bx0, bx1, thick)
    total = int(ink.sum())
    if total < 4:
        return None
    ax0, ay0, ax1, ay1 = (float(v) for v in area)
    cx0, cx1 = max(0, int(ax0) - bx0), min(ink.shape[1], int(round(ax1)) - bx0)
    cy0, cy1 = max(0, int(ay0) - by0), min(ink.shape[0], int(round(ay1)) - by0)
    inside = int(ink[cy0:cy1, cx0:cx1].sum()) if cx1 > cx0 and cy1 > cy0 else 0
    return {"ink_px": total, "inside_px": inside, "ink_share_inside": round(inside / total, 4)}


#: a meter stands at one x on every staff of its system: candidates whose area centres lie within this many spaces are one column
COLUMN_X_TOL_SPACES = 0.6
#: the column is real when this share of the system's staves (and at least `COLUMN_MIN_STAVES`) have a pair in it
COLUMN_MIN_SHARE = 0.4
COLUMN_MIN_STAVES = 2
#: a staff with no pair of its own is searched again inside the column, this many spaces either side of the column's centre
COLUMN_SEARCH_SPACES = 1.8


def find_column(binary: Any, staves: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The meter object on every staff of ONE system at ONE place (the header, or a bar's head), found as a COLUMN.

    `staves`: `[{"key", "lines": [5 page y], "spacing": px, "x_lo", "x_hi", "common_box": box or None}]` in page px, the window being where
    a meter may stand on that staff (the header cell, or the first spaces after a barline). Each staff is searched alone (`find`); the
    pairs that stand in ONE column on at least `COLUMN_MIN_SHARE` of the system's staves are the printed meter -- a clef's body, a key
    accidental or a first note that happened to pass `find` stands at its own x and is dropped. A staff left with no pair in the column
    is searched again inside it. Returns `{"column_x", "n_staves", "n_in_column", "by_staff": {key: find-result + "in_column"}}`;
    `column_x` is None where no column reached the share (nothing is claimed)."""
    first = {}
    for st in staves:
        first[st["key"]] = find(binary, st["lines"], st["spacing"], st["x_lo"], st["x_hi"], common_box=st.get("common_box"))
    cands = []
    for st in staves:
        r = first[st["key"]]
        if r.get("found"):
            cands.append(((r["area"][0] + r["area"][2]) / 2.0, st["key"], st["spacing"]))
    cands.sort()
    best: List[Tuple[float, str, float]] = []
    for i in range(len(cands)):
        grp = [c for c in cands[i:] if c[0] - cands[i][0] <= COLUMN_X_TOL_SPACES * cands[i][2]]
        if len(grp) > len(best):
            best = grp
    n = len(staves)
    if len(best) < max(COLUMN_MIN_STAVES, int(COLUMN_MIN_SHARE * n + 0.999)):
        return {"column_x": None, "n_staves": n, "n_in_column": len(best),
                "by_staff": {k: dict(v, in_column=False) for k, v in first.items()}}
    xc = sum(c[0] for c in best) / len(best)
    in_col = {c[1] for c in best}
    out: Dict[str, Any] = {}
    for st in staves:
        k = st["key"]
        if k in in_col:
            out[k] = dict(first[k], in_column=True)
            continue
        sp = st["spacing"]
        r = find(binary, st["lines"], sp, max(st["x_lo"], xc - COLUMN_SEARCH_SPACES * sp), min(st["x_hi"], xc + COLUMN_SEARCH_SPACES * sp),
                 common_box=st.get("common_box"))
        if r.get("found"):
            r = dict(r, in_column=True, found_again_in_column=True)
        else:
            r = dict(r, in_column=False)
        out[k] = r
    return {"column_x": round(xc, 1), "n_staves": n, "n_in_column": sum(1 for v in out.values() if v.get("in_column")), "by_staff": out}
