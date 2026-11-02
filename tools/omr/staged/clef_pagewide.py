"""ROADMAP 2.251 -- every clef on the page, read page-wide by its SHAPE, and the clef in force at each head (Sean 2026-11-01 "Build both").

PATH: STAGED. Step 1 (flag `OMR_CLEF_PAGEWIDE`, default OFF) is a GATHER reader on the page-wide pass: it looks over every staff of
the page for clef-shaped, clef-sized ink -- header clefs and clefs inside a system alike -- and CLAIMS that ink at kind `clef` in the
claimed-area register (`claims.py`, owner `clef`, standing READ, source `clef_pagewide`), so the head / rest consult refuses a box on it
(later readers may mark claimed ink, never take it; CLAUDE §3). Step 2 (flag `OMR_CLEF_CARRY`, default OFF) is EVALUATE: `restate_pitch`
pitches each head from the clef printed LAST before it on its staff (`clef_in_force`).

CONVENTION ASSUMED: a clef change is a clef glyph on ONE staff, at or just before a barline or before the first note it governs, often
smaller than the header clef; it holds on that staff until the next printed clef, and a new system reprints the clef in force in its
header. WHAT WOULD FALSIFY IT: a cautionary clef at a system's end that governs nothing, or a change that applies to several staves.
NOT CONFIRMED by Sean beyond "Build both" (DECISIONS 2026-11-01); benchmarks/clef-change-2026-11/FINDINGS.md.

Two witnesses, never the detector's word alone (2.144 / 2.181: false `clef*` boxes stood over real eighths and rests):
* a C clef: the THICK BAR -- a run of columns >= `C_BAR_MIN_WIDTH_SPACES` wide, each holding one unbroken vertical ink run of at least
  `C_BAR_MIN_RUN_SPACES` that stops within `C_BAR_REACH_SPACES` of the staff (a barline runs on to the next staff, a stem is one or two px
  wide), and the BOWLS -- ink right of the bar in both its upper and lower half, roughly mirror images about the bar's middle. The middle
  names the line (`clef_geometry.resolve_clef`, the header readers' own snap). Litolff's C clefs inside a system are never boxed as clefs,
  so this test needs no box; a `clefC*` box is one more witness.
* an F clef: a clef-sized `clefF` box (the detector) AND its two dots straddling the line it names (`clef_locator._has_f_clef_dots`, the
  header locator's own veto), the box's top near the top line. The line comes from the dot pair; a pair that names no allowed line
  (`KINDS_READ`) is no witness, so an F clef is either claimed with its kind READ or not claimed (the detector's NARROWED claim stands).
* a G clef: a clef-sized `clefG` box reaching past the staff both above and below (a G clef's curl and tail).
A C clef whose kind cannot be read (no allowed line within the snap) is still CLAIMED -- its bar and bowls are the shape -- and filed
with `kind: None`; step 2 marks the notes after it unread, never pitched from the header clef (rule 8).
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ENV = "OMR_CLEF_PAGEWIDE"
ENV_CARRY = "OMR_CLEF_CARRY"
SOURCE = "clef_pagewide"

#: the named line is searched this close to the bar's middle (under half a space: never a neighbouring line)
C_AXIS_SHIFT_SPACES = 0.45
#: the C clef's thick bar: this wide (staff spaces; a barline is ~0.3, a stem ~0.1; Litolff's small C clef bar measures 0.7-0.8)
C_BAR_MIN_WIDTH_SPACES = 0.45
C_BAR_MAX_WIDTH_SPACES = 1.3
#: ... each column holding one unbroken ink run this long (the small C clef spans 3.6-3.7 sp, a full one ~4.3)
C_BAR_MIN_RUN_SPACES = 3.0
#: ... that starts and ends within this of the staff's top / bottom line (a barline or a bracket runs on to the next staff)
C_BAR_REACH_SPACES = 1.3
#: the glyph ends at the first gap this wide (staff spaces) right of the bar (between the thick and thin bars stands at most ~0.3)
C_GLYPH_GAP_SPACES = 0.35
#: the bowls: ink right of the bar within this reach (staff spaces from the bar's right edge) ...
C_BOWL_REACH_SPACES = 2.2
#: ... in BOTH halves (above and below the bar's middle) at least this share of the half's area (a repeat sign's dots are far below it)
C_BOWL_MIN_FILL = 0.3
#: ... and the two halves mirror images: |upper - lower| / max at most this
C_BOWL_MAX_ASYMMETRY = 0.5
#: a G clef box reaches past the staff by this much above and below
G_REACH_SPACES = 0.6
#: a bar candidate is a G clef's spine where ink stands in BOTH bands this far past the staff (staff spaces, from .. to) beside it
G_PAST_SPACES = (1.4, 2.2)
G_PAST_MIN_FILL = 0.05
#: ... or the G clef's tail: ink in the band this far below the bottom line (from .. to, staff spaces), beside the spine, at least
#: this share (measured on Litolff pp. 2-16: header G clefs 0.42-0.56; every C clef, header or inside a system, at most 0.15)
G_TAIL_SPACES = (0.6, 1.6)
G_TAIL_MIN_FILL = 0.3
#: an F clef box's top stands this close to the top line
F_TOP_REACH_SPACES = 1.0
#: staff-line rows are cleared within this of each line (staff spaces) where a row's ink runs across this share of the window
LINE_HALF_SPACES = 0.3
#: ... and for the C clef's bowls, every row this close to the line measured at the clef (the bowls' fills were set with it)
BOWL_LINE_HALF_SPACES = 0.08
LINE_ROW_MIN_FILL = 0.5
#: the local line search: rows within this of the nominal line, over this many columns left of the clef
LOCAL_LINE_REACH_SPACES = 0.6
LOCAL_LINE_WINDOW_SPACES = 4.0
#: the lines a clef may name and be READ (a convention prior on these plates: the bass F clef, the alto and tenor C clefs); a clef
#: whose line comes out anywhere else is claimed but its kind UNREAD -- never a rare clef from a measurement near a cut
KINDS_READ = {"F": (4,), "C": (3, 4)}
#: a column of the dot window holding an unbroken raw ink run this long (staff spaces) is a stem / barline: cleared before the dots
DOT_STROKE_CLEAR_SPACES = 1.8
#: the F body: pieces starting at most this far (staff spaces) left of its largest piece
F_BODY_LEFT_REACH_SPACES = 0.6
#: a dot candidate whose centre column holds an unbroken ink run this long (staff spaces, lines included) is a stroke's piece
DOT_NOT_A_STROKE_SPACES = 1.5
#: a clef starting within this many staff spaces of the staff's first cell's left edge is the system's header clef
HEADER_WINDOW_SPACES = 6.0


def enabled() -> bool:
    """`OMR_CLEF_PAGEWIDE` (ROADMAP 2.251 step 1), default OFF: only 1/true/yes/on enables."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def carry_enabled() -> bool:
    """`OMR_CLEF_CARRY` (ROADMAP 2.251 step 2), default OFF: only 1/true/yes/on enables. Reads step 1's rows."""
    return os.environ.get(ENV_CARRY, "").strip().lower() in ("1", "true", "yes", "on")


def _ink(binary: Any) -> Optional[np.ndarray]:
    if binary is None or getattr(binary, "ndim", 0) != 2:
        return None
    return np.asarray(binary) == 0


def _longest_run(col: np.ndarray) -> Tuple[int, int]:
    """(length, start) of the longest run of True in a 1-D array."""
    if not col.any():
        return 0, 0
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    i = int(np.argmax(ends - starts))
    return int(ends[i] - starts[i]), int(starts[i])


def _without_lines(sub: np.ndarray, line_rows: Sequence[int], half: int, *, full_rows_only: bool = False) -> np.ndarray:
    """A copy of `sub` with the staff lines cleared (a line is no part of a glyph): every row within `half` px of each line, or with
    `full_rows_only` (the F clef's dots: the line is as thick as the print made it) only those rows whose ink runs across at least
    `LINE_ROW_MIN_FILL` of the window -- so a dot beside a line keeps its own rows."""
    out = sub.copy()
    if out.size == 0:
        return out
    for y in line_rows:
        for yy in range(max(0, y - half), min(out.shape[0], y + half + 1)):
            if not full_rows_only or out[yy].mean() >= LINE_ROW_MIN_FILL:
                out[yy, :] = False
    return out


def c_bars(ink: np.ndarray, lines: Sequence[float], sp: float, x0: int, x1: int) -> List[Dict[str, Any]]:
    """Every C-clef thick bar on one staff between page columns x0..x1 (see the module doc), with its bowls measured. Measures;
    decides nothing beyond the shape test each candidate passed or failed (`passed`, `why`)."""
    H, W = ink.shape
    top, bot = float(lines[0]), float(lines[4])
    ya, yb = max(0, int(top - 3 * sp)), min(H, int(bot + 3 * sp) + 1)
    x0, x1 = max(0, int(x0)), min(W, int(x1))
    if x1 - x0 < 3 or yb - ya < 5:
        return []
    band = ink[ya:yb, x0:x1]
    ok = np.zeros(x1 - x0, dtype=bool)
    runs: List[Tuple[int, int]] = []
    for j in range(x1 - x0):
        n, s = _longest_run(band[:, j])
        runs.append((n, s))
        if n >= C_BAR_MIN_RUN_SPACES * sp:
            y_s, y_e = ya + s, ya + s + n
            if y_s >= top - C_BAR_REACH_SPACES * sp and y_e <= bot + C_BAR_REACH_SPACES * sp:
                ok[j] = True
    out: List[Dict[str, Any]] = []
    j = 0
    while j < len(ok):
        if not ok[j]:
            j += 1
            continue
        k = j
        while k < len(ok) and ok[k]:
            k += 1
        w = (k - j) / sp
        tops = [ya + runs[c][1] for c in range(j, k)]
        bots = [ya + runs[c][1] + runs[c][0] for c in range(j, k)]
        y_top, y_bot = float(np.median(tops)), float(np.median(bots))
        cand: Dict[str, Any] = {"x0": x0 + j, "x1": x0 + k, "y0": round(y_top, 1), "y1": round(y_bot, 1),
                                "bar_width_spaces": round(w, 3), "bar_run_spaces": round((y_bot - y_top) / sp, 3)}
        why = None
        if w < C_BAR_MIN_WIDTH_SPACES:
            why = "bar_too_thin"
        elif w > C_BAR_MAX_WIDTH_SPACES:
            why = "bar_too_wide"
        else:
            mid = (y_top + y_bot) / 2.0
            ll = local_lines(ink, lines, sp, x0 + j)
            cand["lines_local"] = [round(v, 1) for v in ll]
            bx0, bx1 = x0 + k, min(W, x0 + k + int(round(C_BOWL_REACH_SPACES * sp)))
            yt, ym, yb2 = int(round(y_top)), int(round(mid)), int(round(y_bot))
            half = max(1, int(round(BOWL_LINE_HALF_SPACES * sp)))
            region = _without_lines(ink[yt:yb2, bx0:bx1], [int(round(l)) - yt for l in ll], half)
            up, lo = region[: ym - yt], region[ym - yt:]
            fu = float(up.mean()) if up.size else 0.0
            fl = float(lo.mean()) if lo.size else 0.0
            asym = abs(fu - fl) / max(fu, fl, 1e-6)
            cand.update(bowl_fill_upper=round(fu, 3), bowl_fill_lower=round(fl, 3), bowl_asymmetry=round(asym, 3),
                        middle_y=round(mid, 1))
            # a G clef's spine passes the bar test too; its curl / tail stand past the staff, where a C clef has no ink
            gx0, gx1 = max(0, x0 + j - int(round(0.5 * sp))), min(W, x0 + k + int(round(0.8 * sp)))
            g_up = ink[max(0, int(top - G_PAST_SPACES[1] * sp)):max(0, int(top - G_PAST_SPACES[0] * sp)), gx0:gx1]
            g_lo = ink[min(H, int(bot + G_PAST_SPACES[0] * sp)):min(H, int(bot + G_PAST_SPACES[1] * sp)), gx0:gx1]
            g_shape = bool(g_up.size and g_up.mean() >= G_PAST_MIN_FILL) and bool(g_lo.size and g_lo.mean() >= G_PAST_MIN_FILL)
            # round 2 (Sean's tile 5: a header G clef claimed as a C clef): the spine of a small G clef stays inside the staff and its
            # curl and tail miss the far bands above; its TAIL below the bottom line beside the spine does not
            tx0, tx1 = max(0, x0 + j - int(round(1.0 * sp))), min(W, x0 + k + int(round(1.2 * sp)))
            tail = ink[min(H, int(ll[4] + G_TAIL_SPACES[0] * sp)):min(H, int(ll[4] + G_TAIL_SPACES[1] * sp)), tx0:tx1]
            cand["g_tail_fill"] = round(float(tail.mean()), 3) if tail.size else 0.0
            g_shape = g_shape or cand["g_tail_fill"] >= G_TAIL_MIN_FILL
            rows_ink = np.flatnonzero(region.any(axis=1))
            # the named line is the axis the WHOLE glyph (bar and bowls, lines cleared) balances about -- the header C-clef
            # locator's own measure (`clef_locator._refine_symmetry_axis`), searched within `C_AXIS_SHIFT_SPACES` of the bar's middle
            from ..clef_locator import _refine_symmetry_axis
            gx_0 = x0 + k     # the bowls only: the bar may run on into a stem or beam that touches it, the bowls do not
            glyph = _without_lines(ink[yt:yb2, gx_0:bx1], [int(round(l)) - yt for l in ll], half).astype(np.uint8)
            if glyph.size:
                axis, sym = _refine_symmetry_axis(glyph, (0, 0, glyph.shape[1], glyph.shape[0]), C_AXIS_SHIFT_SPACES * sp)
                cand["middle_y"] = round(float(yt + axis), 1)
                cand["symmetry"] = round(float(sym), 3)
            cand["g_shape"] = g_shape
            if g_shape:
                why = "g_clef_shape"
            elif min(fu, fl) < C_BOWL_MIN_FILL:
                why = "no_bowls"
            elif asym > C_BOWL_MAX_ASYMMETRY:
                why = "bowls_not_mirrored"
            elif rows_ink.size == 0:
                why = "no_bowls"
            else:
                # the glyph's right edge: walk right from the bar through the columns holding bowl ink, stopping at the first gap
                # wider than `C_GLYPH_GAP_SPACES` (round 2: a claim takes the clef's own ink, never a rest or note beside it)
                has = region.any(axis=0)
                gap, last, lim = 0, -1, int(round(C_GLYPH_GAP_SPACES * sp))
                for c in range(region.shape[1]):
                    if has[c]:
                        last, gap = c, 0
                    else:
                        gap += 1
                        if gap > lim:
                            break
                cand["x_right"] = int(bx0 + last + 1)
        cand["passed"] = why is None
        cand["why"] = why
        out.append(cand)
        j = k
    return out


def c_area(cand: Dict[str, Any], sp: float) -> List[float]:
    """The page-px area a passing C bar candidate claims: from just left of its thick bar to the glyph's own right edge (`x_right`,
    the contiguous bowl ink), and the clef's height about its named line. ONE formula for the claim and for any tile drawn of it."""
    mid = float(cand.get("middle_y", (cand["y0"] + cand["y1"]) / 2.0))
    return [float(cand["x0"]) - 0.15 * sp, min(float(cand["y0"]), mid - 2.0 * sp) - 0.3 * sp,
            float(cand.get("x_right", cand["x1"] + 2.0 * sp)) + 0.1 * sp, max(float(cand["y1"]), mid + 2.0 * sp) + 0.3 * sp]


def local_lines(ink: np.ndarray, lines: Sequence[float], sp: float, x: float) -> List[float]:
    """The five staff lines measured AT x (CLAUDE §5: never a staff-wide value; a scanned staff tilts and ~1 px decides a line): the
    one vertical shift, within `LOCAL_LINE_REACH_SPACES`, that puts the most ink under all five nominal lines together over the
    `LOCAL_LINE_WINDOW_SPACES` of columns either side of x (one shift for five lines: a note or a stem beside one line cannot pull it)."""
    H, W = ink.shape
    xa, xb = max(0, int(x - LOCAL_LINE_WINDOW_SPACES * sp)), min(W, int(x + LOCAL_LINE_WINDOW_SPACES * sp))
    reach = int(round(LOCAL_LINE_REACH_SPACES * sp))
    if xb - xa < 3:
        return [float(v) for v in lines]
    best, best_d = -1.0, 0
    for dy in range(-reach, reach + 1):
        tot = 0.0
        for y in lines:
            yy = int(round(y)) + dy
            if 0 <= yy < H:
                tot += float(ink[yy, xa:xb].mean())
        if tot > best + 1e-9 or (abs(tot - best) <= 1e-9 and abs(dy) < abs(best_d)):
            best, best_d = tot, dy
    return [float(v) + best_d for v in lines]


def name_c(mid_y: float, lines: Sequence[float]) -> Tuple[Optional[str], Optional[int], Optional[float]]:
    """The C clef's name from its middle (the header readers' own snap, `clef_geometry.resolve_clef`): (name, line, residual) or
    (None, None, residual) where it lands on no line a C clef uses."""
    from ..clef_geometry import resolve_clef
    r = resolve_clef("cClef", anchor_y=float(mid_y), staff_line_ys=[float(v) for v in lines])
    if r is None or r.line is None or r.line not in KINDS_READ["C"]:
        return None, None, (round(float(r.residual), 3) if r is not None and r.residual is not None else None)
    return r.name, r.line, (round(float(r.residual), 3) if r.residual is not None else None)


def _dot_mask(ink: np.ndarray, y0: int, y1: int, x0: int, x1: int, lines: Sequence[float], sp: float) -> np.ndarray:
    """The window's ink as the dot readers see it: the staff lines cleared (rows a line runs across, as thick as the print made it),
    and every column holding an unbroken RAW ink run of `DOT_STROKE_CLEAR_SPACES` or more cleared too -- a stem or barline that the
    dots touch (Brahms p5 s1 staff 3: thick lines and a stem fuse the lower dot) is no part of a dot, and an F clef's own body never
    runs that far down one column."""
    half = max(1, int(round(LINE_HALF_SPACES * sp)))
    sub = _without_lines(ink[y0:y1, x0:x1], [int(round(l)) - y0 for l in lines], half, full_rows_only=True)
    for j in range(sub.shape[1]):
        if _longest_run(ink[y0:y1, x0 + j])[0] >= DOT_STROKE_CLEAR_SPACES * sp:
            sub[:, j] = False
    return sub.astype(np.uint8)


def f_dots(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> bool:
    """The F clef's two dots right of its body (`clef_locator._has_f_clef_dots`, the header locator's own veto) on the page ink with
    the staff lines cleared."""
    from ..clef_locator import DEFAULT_LOCATOR_CONFIG, _has_f_clef_dots
    H, W = ink.shape
    x0, y0 = max(0, int(box[0] - sp)), max(0, int(box[1] - sp))
    x1, y1 = min(W, int(box[2] + 2 * sp)), min(H, int(box[3] + sp))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return False
    sub = _dot_mask(ink, y0, y1, x0, x1, lines, sp)
    bb = (int(box[0]) - x0, int(box[1]) - y0, int(box[2] - box[0]), int(box[3] - box[1]))
    try:
        return bool(_has_f_clef_dots(sub, bb, float(sp), DEFAULT_LOCATOR_CONFIG))
    except Exception:                                   # noqa: BLE001 -- a reader that cannot run is no witness
        return False


#: the right edge (page px) of the dot pair the last `f_line` call read -- the F claim's own right edge
F_LAST_DOTS: Dict[str, float] = {}


def f_line(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> Tuple[Optional[str], Optional[int], Optional[float]]:
    """The F clef's name from its DOTS: they straddle the line the clef names (`clef_locator._has_f_clef_dots`' own reason), so the
    midpoint of the dot pair right of the body's middle (sizes and spacing from the header locator's config) snaps to that line
    (`clef_geometry._snap_to_staff_line`). (None, None, residual) where no pair or no F line fits."""
    import cv2
    from ..clef_geometry import CLEF_BY_FAMILY_LINE, DEFAULT_CONFIG, _snap_to_staff_line
    from ..clef_locator import DEFAULT_LOCATOR_CONFIG as C
    H, W = ink.shape
    x0, y0 = max(0, int((box[0] + box[2]) / 2.0)), max(0, int(box[1] - sp))
    x1, y1 = min(W, int(box[2] + C.dot_search_right_spaces * sp)), min(H, int(box[3] + sp))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None, None, None
    sub = _dot_mask(ink, y0, y1, x0, x1, lines, sp)
    n, _lab, st, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    dots = []
    for i in range(1, n):
        bw, bh = st[i, cv2.CC_STAT_WIDTH] / sp, st[i, cv2.CC_STAT_HEIGHT] / sp
        if C.dot_min_size_spaces <= bw <= C.dot_max_size_spaces and C.dot_min_size_spaces <= bh <= C.dot_clear_max_height_spaces:
            cx = x0 + st[i, cv2.CC_STAT_LEFT] + bw * sp / 2.0
            # a piece of a stem or barline the line clearing cut is no dot: its column runs on through the lines in the raw ink
            if _longest_run(ink[y0:y1, int(cx)])[0] >= DOT_NOT_A_STROKE_SPACES * sp:
                continue
            dots.append((cx, y0 + st[i, cv2.CC_STAT_TOP] + bh * sp / 2.0, x0 + st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH]))
    best = None
    for a in range(len(dots)):
        for b in range(a + 1, len(dots)):
            dx, dy = abs(dots[a][0] - dots[b][0]) / sp, abs(dots[a][1] - dots[b][1]) / sp
            if dx <= C.dot_max_dx_spaces and C.dot_min_dy_spaces <= dy <= C.dot_max_dy_spaces:
                # the dots stand at the body's right edge: the pair nearest the box's right edge (a key flat's or a note's pieces stand
                # further right; round 2: on Brahms headers the rightmost pair was a key flat's bowl)
                cand = (round(abs((dots[a][0] + dots[b][0]) / 2.0 - float(box[2])) / sp, 1), abs(dy - 1.0),
                        (dots[a][1] + dots[b][1]) / 2.0,
                        max(dots[a][2], dots[b][2]))
                if best is None or cand < best:
                    best = cand
    if best is None:
        return None, None, None
    F_LAST_DOTS["right"] = float(best[3])
    snapped = _snap_to_staff_line(best[2], [float(v) for v in lines])
    if snapped is None:
        return None, None, None
    line, residual = snapped
    name = CLEF_BY_FAMILY_LINE["F"].get(line) if line in KINDS_READ["F"] else None
    if name is None or residual > DEFAULT_CONFIG.max_residual:
        return None, None, round(float(residual), 3)
    return name, line, round(float(residual), 3)


def f_body(ink: np.ndarray, box: Sequence[float], lines: Sequence[float], sp: float) -> Optional[List[float]]:
    """The F clef's BODY inside its detector box (page px [x0, y0, x1, y1]): the largest piece of the box's ink with the staff lines
    and the long strokes cleared (`_dot_mask`). Round 2 (Sean's r1 tile 10, Litolff p16): the detector's `clefF` box also held the
    quarter rest standing just left of the clef, so the claim is cut to the clef's own ink, never the box."""
    import cv2
    H, W = ink.shape
    x0, y0, x1, y1 = max(0, int(box[0])), max(0, int(box[1])), min(W, int(round(box[2]))), min(H, int(round(box[3])))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    sub = _dot_mask(ink, y0, y1, x0, x1, lines, sp)
    n, _lab, st, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
    if n <= 1:
        return None
    i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    # the line clearing cuts the body into pieces: the body is the largest piece and every sizeable piece starting no further left
    # than `F_BODY_LEFT_REACH_SPACES` before it (a rest or note standing left of the clef starts further left)
    lo = st[i, cv2.CC_STAT_LEFT] - F_BODY_LEFT_REACH_SPACES * sp
    keep = [j for j in range(1, n) if st[j, cv2.CC_STAT_AREA] >= 0.15 * st[i, cv2.CC_STAT_AREA] and st[j, cv2.CC_STAT_LEFT] >= lo]
    return [float(x0 + min(st[j, cv2.CC_STAT_LEFT] for j in keep)), float(y0 + min(st[j, cv2.CC_STAT_TOP] for j in keep)),
            float(x0 + max(st[j, cv2.CC_STAT_LEFT] + st[j, cv2.CC_STAT_WIDTH] for j in keep)),
            float(y0 + max(st[j, cv2.CC_STAT_TOP] + st[j, cv2.CC_STAT_HEIGHT] for j in keep))]


def f_claim_area(got: Dict[str, Any], box: Sequence[float], sp: float) -> List[float]:
    """The page-px area a passing F clef claims: its body's left edge (else the box's) to its dots' right edge, the box's height.
    ONE formula for the claim and for any tile drawn of it."""
    body = got.get("body")
    left = float(body[0]) - 0.1 * sp if body else float(box[0])
    right = max(float(body[2]) if body else float(box[2]), float(got.get("dots_right") or 0.0)) + 0.05 * sp
    return [max(float(box[0]), left), float(box[1]), right, float(box[3])]


def read_box(name: str, box: Sequence[float], ink: np.ndarray, lines: Sequence[float], sp: float) -> Dict[str, Any]:
    """The second witness for a clef-sized detector `clef*` box: {passed, why, kind, family, line, residual}."""
    from ..clef_geometry import clef_family, resolve_clef
    fam = clef_family(name)
    top, bot = float(lines[0]), float(lines[4])
    out: Dict[str, Any] = {"family": fam, "cls": str(name), "kind": None, "line": None, "residual": None}
    if fam == "F":
        if abs(float(box[1]) - top) > F_TOP_REACH_SPACES * sp:
            return dict(out, passed=False, why="f_top_off_the_top_line")
        # round 2: the witness is the DOT PAIR that straddles the F line (`f_line`, the header locator's dot sizes and spacing), read on
        # the window with lines AND the strokes the dots touch cleared; the locator's own whole-glyph test (`_has_f_clef_dots`) is
        # kept as the first chance but no longer required -- on Breitkopf's thick lines it fails real clefs (Sean r1 tile 11)
        dots_ok = f_dots(ink, box, lines, sp)
        F_LAST_DOTS.clear()
        nm, ln, res = f_line(ink, box, lines, sp)
        out["dots_right"] = F_LAST_DOTS.get("right")
        out["body"] = f_body(ink, box, lines, sp)
        out["locator_dots"] = bool(dots_ok)
        if nm is None and not dots_ok and "right" not in F_LAST_DOTS:
            return dict(out, passed=False, why="f_no_dots")
        if nm is None:
            # the dot PAIR must straddle the F line: dots that name no allowed line are no second witness (a false `clefF` box over
            # a half note and a barline passed the looser dot test on Brahms p25) -- the box alone never claims
            return dict(out, passed=False, why="f_dots_name_no_line", residual=res)
        return dict(out, passed=True, why=None, kind=nm, line=ln, residual=res)
    elif fam == "G":
        # no second witness for a G clef inside a system is built (none is printed on the two plates; 2.144's false `clefG` boxes over
        # real eighths are the risk): the box alone never claims (the register's NARROWED claim stands)
        if not (float(box[1]) <= top - G_REACH_SPACES * sp and float(box[3]) >= bot + G_REACH_SPACES * sp):
            return dict(out, passed=False, why="g_not_past_the_staff")
        return dict(out, passed=False, why="g_no_second_witness")
    elif fam == "C":
        bars = [b for b in c_bars(ink, lines, sp, box[0] - 0.5 * sp, box[2]) if b["passed"]]
        if not bars:
            return dict(out, passed=False, why="c_no_bar_and_bowls")
        nm, ln, res = name_c(bars[0]["middle_y"], lines)
        return dict(out, passed=True, why=None, kind=nm, line=ln, residual=res)
    else:
        return dict(out, passed=False, why="not_a_pitched_clef")
    r = resolve_clef(name, y_top=float(box[1]), height=float(box[3] - box[1]), staff_line_ys=[float(v) for v in lines])
    if r is None or r.line is None:
        return dict(out, passed=True, why=None, residual=(round(float(r.residual), 3) if r is not None and r.residual is not None else None))
    return dict(out, passed=True, why=None, kind=r.name, line=r.line, residual=(round(float(r.residual), 3) if r.residual is not None else None))


# --------------------------------------------------------------------------------------------------------------------------------------
# 2.251 carry: an F clef with NO detector box (Litolff bars 38 / 111 / 115, Brahms bass clefs whose box failed its dots)
# --------------------------------------------------------------------------------------------------------------------------------------
#: the dot-pair scan runs in windows this wide (staff spaces), overlapping by `F_SCAN_OVERLAP_SPACES`, each with its own local lines
F_SCAN_WINDOW_SPACES = 8.0
F_SCAN_OVERLAP_SPACES = 3.0


#: a no-box dot may be this wide (staff spaces; the header locator allows 0.75): the body's tip touches the upper dot (Litolff bar 38,
#: 0.76 sp fused) -- the body template is the second witness that keeps a looser dot honest
NOBOX_DOT_MAX_WIDTH_SPACES = 0.9
#: a horizontal ink run this long (staff spaces) is a staff line or a beam, never part of a dot
DOT_LINE_RUN_SPACES = 1.2


def _dot_mask_runs(ink: np.ndarray, y0: int, y1: int, x0: int, x1: int, sp: float) -> np.ndarray:
    """The window's ink as the no-box dot reader sees it: every HORIZONTAL run of `DOT_LINE_RUN_SPACES` or more cleared (a staff line,
    however it tilts, or a beam) and every column holding an unbroken vertical run of `DOT_STROKE_CLEAR_SPACES` or more cleared (a
    stem, a barline). Unlike `_dot_mask` it does not depend on where the window starts (the row-share line test did: Litolff bar 38's
    dots were seen from 5 of 22 window starts)."""
    import cv2
    sub = ink[y0:y1, x0:x1].astype(np.uint8)
    if sub.size == 0:
        return sub
    k = max(3, int(round(DOT_LINE_RUN_SPACES * sp)))
    lines_only = cv2.morphologyEx(sub, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1)))
    out = sub & (1 - lines_only)
    kv = max(3, int(round(DOT_STROKE_CLEAR_SPACES * sp)))
    strokes = cv2.morphologyEx(ink[y0:y1, x0:x1].astype(np.uint8), cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, kv)))
    cols = strokes.any(axis=0)
    out[:, cols] = 0
    return out


def f_dot_pairs(ink: np.ndarray, lines: Sequence[float], sp: float, x0: float, x1: float) -> List[Dict[str, Any]]:
    """Every dot PAIR on one staff between page columns x0..x1 that straddles the F line (line 4 from the bottom: the second line from
    the top) -- the F clef's dots by the header locator's own sizes and spacing (`clef_locator.DEFAULT_LOCATOR_CONFIG`), read on the ink
    with the staff lines and long strokes cleared (`_dot_mask`), the lines measured locally per window. Measures; decides nothing.
    Each: {x_left, x_right, y_mid, residual, dots}."""
    import cv2
    from ..clef_geometry import DEFAULT_CONFIG, _snap_to_staff_line
    from ..clef_locator import DEFAULT_LOCATOR_CONFIG as C
    H, W = ink.shape
    out: List[Dict[str, Any]] = []
    step = max(1, int(round((F_SCAN_WINDOW_SPACES - F_SCAN_OVERLAP_SPACES) * sp)))
    xa = int(x0)
    while xa < int(x1):
        xb = min(W, int(xa + F_SCAN_WINDOW_SPACES * sp))
        ll = local_lines(ink, lines, sp, (xa + xb) / 2.0)
        y0, y1 = max(0, int(ll[1] - 1.4 * sp)), min(H, int(ll[1] + 1.4 * sp))
        sub = _dot_mask_runs(ink, y0, y1, xa, xb, sp)
        n, _lab, st, _c = cv2.connectedComponentsWithStats(sub, connectivity=8)
        dots = []
        for i in range(1, n):
            bw, bh = st[i, cv2.CC_STAT_WIDTH] / sp, st[i, cv2.CC_STAT_HEIGHT] / sp
            if not (C.dot_min_size_spaces <= bw <= NOBOX_DOT_MAX_WIDTH_SPACES and C.dot_min_size_spaces <= bh <= C.dot_clear_max_height_spaces):
                continue
            cx = xa + st[i, cv2.CC_STAT_LEFT] + bw * sp / 2.0
            if _longest_run(ink[y0:y1, int(cx)])[0] >= DOT_NOT_A_STROKE_SPACES * sp:
                continue
            dots.append((cx, y0 + st[i, cv2.CC_STAT_TOP] + bh * sp / 2.0, xa + st[i, cv2.CC_STAT_LEFT],
                         xa + st[i, cv2.CC_STAT_LEFT] + st[i, cv2.CC_STAT_WIDTH]))
        for a in range(len(dots)):
            for b in range(a + 1, len(dots)):
                up, lo = (dots[a], dots[b]) if dots[a][1] < dots[b][1] else (dots[b], dots[a])
                dx, dy = abs(up[0] - lo[0]) / sp, (lo[1] - up[1]) / sp
                if not (dx <= C.dot_max_dx_spaces and C.dot_min_dy_spaces <= dy <= C.dot_max_dy_spaces):
                    continue
                if not (up[1] < ll[1] < lo[1]):
                    continue                                   # the pair straddles the line, one dot either side
                mid = (up[1] + lo[1]) / 2.0
                snapped = _snap_to_staff_line(mid, ll)
                if snapped is None or snapped[0] != 4 or snapped[1] > DEFAULT_CONFIG.max_residual:
                    continue
                xl, xr = min(up[2], lo[2]), max(up[3], lo[3])
                if any(abs(p["x_left"] - xl) < 0.3 * sp and abs(p["y_mid"] - mid) < 0.3 * sp for p in out):
                    continue                                   # the same pair seen from two overlapping windows
                out.append({"x_left": float(xl), "x_right": float(xr), "y_mid": float(mid), "residual": float(snapped[1]),
                            "dots": [[round(float(v), 1) for v in up], [round(float(v), 1) for v in lo]], "lines_local": ll})
        if xb >= int(x1):
            break
        xa += step
    out.sort(key=lambda p: p["x_left"])
    return out


def f_template(ink: np.ndarray, lines: Sequence[float], sp: float, body: Sequence[float], dots_left: float) -> Optional[Dict[str, Any]]:
    """The F body of a READ F clef (`f_body`, page px) as a template: its ink with the staff lines cleared, cut to the body, and where it
    stands against its own dots (the body's right edge to the dots' left edge) and its own F line, in staff spaces."""
    ll = local_lines(ink, lines, sp, body[0])
    x0, y0, x1, y1 = int(body[0]), int(body[1]), int(round(body[2])), int(round(body[3]))
    if x1 - x0 < 3 or y1 - y0 < 3:
        return None
    half = max(1, int(round(BOWL_LINE_HALF_SPACES * sp)))
    m = _without_lines(ink[y0:y1, x0:x1], [int(round(l)) - y0 for l in ll], half)
    return {"mask": m, "sp": float(sp), "dx_to_dots": (float(dots_left) - float(body[2])) / sp, "dy_line": (float(body[1]) - ll[1]) / sp}


#: the template is tried at these sizes (a change is often printed smaller than the header's clef) ...
F_TEMPLATE_SCALES = (0.8, 0.9, 1.0)
#: ... and shifted this far (staff spaces) each way from where its own dots put it
F_TEMPLATE_SHIFT_SPACES = 0.35


def f_body_match(ink: np.ndarray, sp: float, pair: Dict[str, Any], templates: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The second witness for a dot pair with no box: the plate's OWN F body (a read F clef of the same page, `f_template`) laid left of
    the pair where its own dots put it, at the best size and shift. `cover`: the share of the template's ink the page has there; `extra`:
    the share of the page's ink in the template's box that the template does not explain (a stem or head through it). Measures."""
    import cv2
    ll = pair["lines_local"]
    half = max(1, int(round(BOWL_LINE_HALF_SPACES * sp)))
    best = {"cover": 0.0, "extra": 1.0, "score": 0.0}
    H, W = ink.shape
    shift = int(round(F_TEMPLATE_SHIFT_SPACES * sp))
    for t in templates:
        for s in F_TEMPLATE_SCALES:
            k = s * sp / t["sp"]
            th, tw = max(3, int(round(t["mask"].shape[0] * k))), max(3, int(round(t["mask"].shape[1] * k)))
            tm = cv2.resize(t["mask"].astype(np.uint8), (tw, th), interpolation=cv2.INTER_NEAREST).astype(bool)
            if tm.sum() == 0:
                continue
            bx1 = pair["x_left"] - t["dx_to_dots"] * s * sp
            by0 = ll[1] + t["dy_line"] * s * sp
            for dy in range(-shift, shift + 1, max(1, shift // 3)):
                for dx in range(-shift, shift + 1, max(1, shift // 3)):
                    x0, y0 = int(round(bx1 - tw + dx)), int(round(by0 + dy))
                    if x0 < 0 or y0 < 0 or x0 + tw > W or y0 + th > H:
                        continue
                    im = _without_lines(ink[y0:y0 + th, x0:x0 + tw], [int(round(l)) - y0 for l in ll], half)
                    inter = float((tm & im).sum())
                    cover = inter / float(tm.sum())
                    extra = float((im & ~tm).sum()) / max(1.0, float(im.sum()))
                    score = cover - extra
                    if score > best["score"]:
                        best = {"cover": round(cover, 3), "extra": round(extra, 3), "score": round(score, 3), "scale": s,
                                "box": [x0, y0, x0 + tw, y0 + th]}
    return best


def f_body_shape(ink: np.ndarray, lines: Sequence[float], sp: float, pair: Dict[str, Any],
                 templates: Sequence[Dict[str, Any]] = ()) -> Dict[str, Any]:
    """Exploration wrapper: `f_body_match` against `templates`."""
    return f_body_match(ink, sp, pair, templates)


#: the no-box F clef is READ (kind bass, claimed) at this body score (cover - extra) and above. MEASURED on Litolff pp. 1-16 (1472 dot
#: pairs; every non-clef pair <= 0.61, the 2.251 count's no-box bass clefs 0.83 (bar 38), 0.75 (Vc bar 411)); Brahms pp. 1,3,4,5 every
#: non-clef pair <= 0.42. A CUT-OFF on two plates (CLAUDE §4: a measurement, not a convention) -- Sean's tiles judge it.
F_TEMPLATE_READ_SCORE = 0.70
#: ... and at this score and above (but below READ) it is a CLEF-SHAPED CANDIDATE: claimed nothing, but a carried clef stops there
#: (Litolff bars 115 0.66 and 111 0.55: real bass clefs with a head / stem through the body)
F_TEMPLATE_CANDIDATE_SCORE = 0.50
#: a `clef*` box too small for a clef-sized claim, at this detector score and above, is still a clef-shaped CANDIDATE (b)
SMALL_CLEF_BOX_MIN_SCORE = 0.5
#: an F clef's body and dots span at most this far (staff spaces) left of its dots' left edge
F_BODY_MAX_REACH_SPACES = 2.6
#: a dot's width (staff spaces): the template's dots start this far left of the dot pair's right edge `f_line` reports
F_DOT_WIDTH_SPACES = 0.45


def f_templates(ink: np.ndarray, staves: Sequence[Tuple[Sequence[float], float, Sequence[Sequence[float]]]]) -> List[Dict[str, Any]]:
    """The page's own F bodies: every clef-sized `clefF` box (per staff: lines, staff space, the boxes) whose dots read an F line
    (`read_box` passes), its body cut at its dots -- the template the no-box reader lays over a dot pair."""
    out: List[Dict[str, Any]] = []
    for lines, sp, boxes in staves:
        for pb in boxes:
            ll = local_lines(ink, lines, sp, pb[0])
            got = read_box("clefF", pb, ink, ll, sp)
            if not got.get("passed") or not got.get("body") or not got.get("dots_right"):
                continue
            dl = float(got["dots_right"]) - F_DOT_WIDTH_SPACES * sp
            body = list(got["body"])
            body[2] = min(float(body[2]), dl - 1.0)
            if body[2] - body[0] < sp:
                continue
            t = f_template(ink, lines, sp, body, dl)
            if t is not None:
                out.append(t)
    return out


def f_nobox(ink: np.ndarray, lines: Sequence[float], sp: float, x0: float, x1: float,
            templates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every F clef with no detector box between page columns x0..x1 on one staff: a dot pair straddling the F line (`f_dot_pairs`,
    witness 1) AND the page's own F body where those dots put it (`f_body_match`, witness 2). Each: {pair, match, read (score >=
    `F_TEMPLATE_READ_SCORE`), candidate (score >= `F_TEMPLATE_CANDIDATE_SCORE`), area}. Two witnesses, never one; nothing without a
    template (a page with no read F clef reads none)."""
    if not templates:
        return []
    out = []
    for p in f_dot_pairs(ink, lines, sp, x0, x1):
        m = f_body_match(ink, sp, p, templates)
        if m.get("score", 0.0) < F_TEMPLATE_CANDIDATE_SCORE or "box" not in m:
            continue
        b = m["box"]
        # the clef's left edge: the matched body's, but never further left of its dots than a body is wide (a template laid over a C
        # clef standing just before it -- Litolff bar 110/111 -- must not put this clef before that one)
        left = max(float(b[0]), float(p["x_left"]) - F_BODY_MAX_REACH_SPACES * sp)
        area = [left - 0.05 * sp, float(min(b[1], p["dots"][0][1] - 0.4 * sp)), float(p["x_right"]) + 0.05 * sp,
                float(max(b[3], p["dots"][1][1] + 0.4 * sp))]
        out.append({"pair": p, "match": m, "read": m["score"] >= F_TEMPLATE_READ_SCORE, "area": area})
    return out


# --------------------------------------------------------------------------------------------------------------------------------------
# Step 2: the clef in force at a head
# --------------------------------------------------------------------------------------------------------------------------------------
def changes_of(rows: Sequence[Any]) -> List[Tuple[float, Optional[str], Any]]:
    """The clefs printed INSIDE a staff (not its header), as (left x page px, kind or None, row), left to right, from step 1's
    `Q.CLAIMED_AREA` rows (source `clef_pagewide`, `change: True`)."""
    out = []
    for r in rows:
        d = getattr(r, "detail", None) or {}
        if d.get("source") != SOURCE or not d.get("change"):
            continue
        v = r.value
        if not (isinstance(v, (list, tuple)) and len(v) == 4):
            continue
        # a change governs from its LEFT edge. (Tried 2026-11-02: from its right edge, so a false head box on the clef's own ink -- Litolff
        # bar 38 -- is not pitched from it; but a C claim's area runs on into the heads it touches, and 12 heads right after a C clef
        # went right -> wrong on the frozen sample. Reverted; the false head is an ink-claim question, not the carry's.)
        out.append((float(v[0]), d.get("kind"), r))
    out.sort(key=lambda t: t[0])
    return out


def candidates_of(refusals: Sequence[Any]) -> List[Tuple[float, None, Any]]:
    """The CLEF-SHAPED CANDIDATES inside a staff that were not claimed with a read kind (step 1's abstentions, source `clef_pagewide`,
    `candidate: True`): (left x page px, None, row), left to right. ROADMAP 2.251 carry (b): a carried clef stops at one."""
    out = []
    for r in refusals:
        d = getattr(r, "detail", None) or {}
        if d.get("source") != SOURCE or not d.get("candidate") or d.get("x_page") is None:
            continue
        out.append((float(d["x_page"]), None, r))
    out.sort(key=lambda t: t[0])
    return out


def clef_in_force(head_x: float, changes: Sequence[Tuple[float, Optional[str], Any]],
                  candidates: Sequence[Tuple[float, None, Any]] = (), header: Optional[str] = None
                  ) -> Optional[Tuple[Optional[str], Any]]:
    """The clef printed LAST before `head_x` on the staff: (kind or None for unread, row) of the last change whose left edge is left of
    the head, or None where no change stands before it (the header clef governs).

    ROADMAP 2.251 carry (b) (CLAUDE rule 8, §4): a clef-shaped CANDIDATE (`candidates_of`: ink that may be a clef, not read) standing
    after a change whose kind differs from the header clef `header` and before the head STOPS the carry -- the head is unread (None,
    the candidate's row), never carried past ink that might be the return. A candidate where the header's own kind is in force (no
    change yet, or a return to it) changes nothing: the clef the head is pitched from is then the one the no-carry reading uses too."""
    got = None
    events = sorted([(x, 0, k, r) for x, k, r in changes] + [(x, 1, None, r) for x, _k, r in candidates], key=lambda t: (t[0], t[1]))
    for x, is_cand, kind, r in events:
        if x >= head_x:
            break
        if is_cand:
            if got is not None and got[0] is not None and got[0] != header:
                got = (None, r)
            continue
        got = (kind, r)
    return got
