"""ROADMAP 2.166 -- arcs read ONCE per staff across the SYSTEM on page pixels, then their own stroke erased.

STAGED GATHER. Flag `OMR_SYSTEM_ARCS`, default OFF (an allow-list: only an explicit on-word turns it on).

Sean 2026-10-17: *"Can we treat arcs the way we treat hairpins - taking into account the system or page view and then
erasing them?"*, then *"Open the system level arc"*.

WHY. The detector reads one measure cell at a time and a measure cell has no horizontal padding, so a tie crossing a
barline is CUT there and the next bar's crop sees its tail with no context -- 2.164 found 20 Litolff / 12+ Brahms tails
boxed as heads (`benchmarks/omr-head-fill-2026-09/FINDINGS.md` Sec.17). Hairpins and dynamics are already read once
per staff on the page raster (2.68, DECISIONS 2026-10-09); this does the same for ties and slurs.

WHAT IT DOES, per page (detector already run on the ORIGINAL cells -- CLAUDE.md §7; nothing here touches `cell.image`):

1. Builds the page's ink with staff lines removed (`composite_ink`): every cell's own `image_no_staff`, scaled back to
   page pixels and AND-ed where cells overlap (a cell's padding still carries the NEIGHBOUR staff's lines; the
   neighbour's own cell removed them), the raw page raster where no cell reaches.
2. Seeds one TRACE per detector `slur`/`tie` box (`trace_arc`): a thin-stroke follower over page columns that crosses
   barlines and short gaps, and runs past a box edge the crop cut (the box ends at its cell's edge) into the next bar.
3. JOINS traces on one (page, system, staff) that are the same curve (`join_traces`): they share columns at one y, or
   one ends where the other begins. A tie cut at a barline is then ONE arc.
4. ANCHORS its two ends to noteheads on its staff (`anchor_ends`): the head just beside each end; whether the two sit
   at one staff position with no head between (page-facts §1, DECISIONS 2026-10-01: the shape of a tie) or not. A
   MEASUREMENT: GATHER names nothing; `Q.ARC_KIND` / `Q.TIE_PAIR` are untouched.
5. ERASES only the traced stroke from each cell's `image_no_staff` (`erase_in_cell`): the pixel runs the trace
   followed, never the box (the hairpin probe's box erase wiped what lay under it --
   `benchmarks/omr-hairpin-cv-2026-09/FINDINGS.md` §5), never a run taller than a stroke (a head, stem or barline the
   arc touches), never a pixel inside a non-arc detector box (`protected_boxes`) -- EXCEPT a notehead box whose ink is
   all stroke (2.164's tail boxed as a head; its residual ink off the stroke is under `STROKE_ONLY_RESIDUAL_SPACES2`).
   The original is kept on `cell.image_no_staff_with_arcs`.

Every later reader that reads `cell.image_no_staff` (notehead ink/fill gates, rests, dots, flags, stems) therefore
reads the erased raster while the flag is on. Readers that read `pws.page.binary` (hairpins, `Q.ARC_INK_SHAPE`,
`Q.HEAD_OVAL`) are unchanged. ⚠️ `gather_empty_bar_rest_search` runs BEFORE this (it must precede the rescue, which
must precede this so a rescued head is protected), so it still reads the un-erased raster.

CONVENTION ASSUMED: an arc's stroke is one thin run per column (under `STROKE_MAX_SPACES`), smooth from column to
column; a notehead, stem, barline or accidental is taller than a stroke where the arc meets it. WHAT WOULD FALSIFY IT:
a head, rest, dot or accidental that Sean values losing ink to the erase (a tile asking "note or not?" near erased
ink), or a trace Sean reads as two arcs. NOT CONFIRMED: the cut-offs are set on Litolff 984073 and Brahms 317803 only.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ENV = "OMR_SYSTEM_ARCS"

#: A column's ink run no taller than this is a candidate for an arc's stroke. A tie's middle is 0.3-0.46 sp thick on Litolff; a
#: notehead is ~1 sp tall and a beam ~0.5 sp, so neither is followed.
STROKE_MAX_SPACES = 0.6
#: On the RAW page (staff lines in) a stroke's run may be this much taller than `STROKE_MAX_SPACES` (the stroke
#: crossing a staff line). A stem or barline the staff-line removal cut into short pieces is far taller there.
RAW_LINE_ALLOWANCE_SPACES = 0.35
#: A trace this flat (spaces of y range over its whole length) whose columns mostly sit on staff-line rows is the
#: residue of a staff line, not an arc (2.60's fakes): abstained, never erased.
FLAT_SPACES = 0.35
ON_LINE_SHARE = 0.6
#: Past its own box a trace may not climb steeper than this (dy/dx).
EXT_MAX_SLOPE = 1.0
#: A column bridged on the RAW page costs this much of a gap column (`GAP_MAX_SPACES`): at most ~3 sp along a line.
RAW_BRIDGE_COST = 0.25
#: A trace at least this long (spaces) that stays within `STRAIGHT_SPACES` of a straight line is not an arc.
STRAIGHT_MIN_SPACES = 2.0
STRAIGHT_SPACES = 0.15
#: ... and only a straight trace at least this thick (a beam's stroke) is refused: a long flat slur is straight but
#: thin, and left on the page the beam reader takes it for a beam (Brahms 317803 pdf 1, cell 1/0/0/0).
STRAIGHT_BEAM_THICK_SPACES = 0.4
#: A traced column is erased only where its run is at most this many times the trace's median stroke (+1 px).
THICK_FACTOR = 1.6
#: Along a trace, a run thicker than this many times the stroke's recent median (+2 px) is the stroke merged with
#: something else, and bridges as a gap (tile 11).
THICK_CONTINUE_FACTOR = 1.6
#: How many seed columns a trace tries (the best coverage wins).
SEED_COLUMNS = 3
#: The trace may cross this many spaces of columns with no stroke (a barline, a removed staff line, a stem).
GAP_MAX_SPACES = 0.75
#: How far past a box edge the CROP CUT (the box ends within `CUT_EDGE_SPACES` of its cell's edge) the trace may run.
CUT_EXTEND_SPACES = 3.0
#: How far past an edge the crop did not cut.
FREE_EXTEND_SPACES = 0.5
#: A box ends this close to its cell's edge -> the crop cut the arc there (2.164: all 226 candidates <= 0.357).
CUT_EDGE_SPACES = 0.4
#: The rows a trace may use around its seed box.
ROW_PAD_SPACES = 1.0
#: How far the next run's centre may sit from the predicted y.
TOL_SPACES = 0.12
#: A trace must ink at least this share of its own box's columns to be read; under it the box abstains (no erase).
MIN_COVER = 0.5
#: Two traces are one curve where they share columns with centres this close.
SAME_Y_SPACES = 0.12
#: ... at least this many columns.
SAME_MIN_COLS = 2
#: One ends where the other begins: an x gap no wider than `GAP_MAX_SPACES` and the ends this close in y.
END_JOIN_Y_SPACES = 0.35
#: Over the columns two traces share, at least this share must agree in y for them to be one curve.
SAME_SHARE = 0.6
#: End-to-start: the two end tangents (dy/dx) may differ by at most this.
END_JOIN_SLOPE = 0.35
#: A merge (the stroke's run thicker than the stroke) is a run no taller than this; the erase keeps clear of it by
#: `MERGE_KEEP_SPACES` on both sides.
MERGE_MAX_SPACES = 1.5
MERGE_KEEP_SPACES = 1.0
#: Erase: a canonical ink run taller than this is not the stroke (a head, stem or barline it touches) and is kept.
ERASE_RUN_MAX_SPACES = 0.75
#: A notehead box whose ink OFF the traced stroke is under this (square spaces) holds nothing but the stroke -- a tail
#: boxed as a head -- and is not protected. A real filled head is ~0.8 sp^2, a hollow ring ~0.35, a dot ~0.1.
STROKE_ONLY_RESIDUAL_SPACES2 = 0.06
#: A vertical run longer than this (spaces) passes THROUGH a box (a barline, a stem): not the box's own ink.
PASS_THROUGH_SPACES = 1.3
#: Anchors: a head's centre within this many spaces OUTSIDE an end, or this many inside it.
ANCHOR_OUT_SPACES = 1.6
ANCHOR_IN_SPACES = 0.8
#: ... and within this many spaces of the end in y.
ANCHOR_DY_SPACES = 2.5
#: A tie's two heads sit at one staff position (page-facts §1; the staged tolerance `TIE_SAME_POSITION_MAX_SPACES`).
SAME_POSITION_SPACES = 0.25

_ARC_CLASSES = ("tie", "slur")
_NOTEHEAD_PREFIX = "notehead"
#: The detector classes whose ink is never erased where the arc touches them (heads, stems, accidentals and every
#: other printed symbol, hairpins included). NOT protected: `staff` (a whole-staff box, not a mark), `slur`/`tie`
#: themselves, and a `beam` box that doubles an arc box (the detector reads one curve as both, IoU >= `BEAM_TWIN_IOU`).
PROTECTED_PREFIXES = ("notehead", "accidental", "stem", "flag", "rest", "augmentationDot", "clef", "timeSig",
                      "keySig", "key", "dynamic", "artic", "fermata", "ornament", "tuplet", "grace", "ledgerLine",
                      "beam", "tremolo", "repeat", "fingering", "brace", "bracket", "barline")
BEAM_TWIN_IOU = 0.6
#: A beam box can hold nothing but the stroke only where this share of it lies inside one of the arc's own boxes.
BEAM_TWIN_OVERLAP = 0.5
#: The erase is confined to the arc's own boxes padded by this (plus boxes holding nothing but its stroke).
ERASE_BOX_PAD_SPACES = 0.25


def _overlap_share(a: Sequence[float], b: Sequence[float]) -> float:
    """Share of box `a`'s area inside box `b`."""
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    area = (a[2] - a[0]) * (a[3] - a[1])
    return (ix1 - ix0) * (iy1 - iy0) / area if area > 0 else 0.0
#: Only these classes can be found to hold nothing but the stroke (the crop cut the arc and the detector boxed its tail
#: as a head -- 2.164 -- or as a beam). A dot, an articulation, an accidental or a ledger line the trace runs through
#: stays protected whatever its residual: a dot is as short as a stroke and is never the arc's own ink.
STROKE_ONLY_CLASSES = ("notehead", "beam")


def _iou(a: Sequence[float], b: Sequence[float]) -> float:
    ix0, iy0, ix1, iy1 = max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    return inter / ((a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter)


def is_protected_class(name: str) -> bool:
    return str(name).startswith(PROTECTED_PREFIXES)


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


# ─────────────────────────────────────────────────────────────────────────────
# The page's ink with staff lines removed
# ─────────────────────────────────────────────────────────────────────────────

def _cell_ink_on_page(cell: Any) -> Optional[Tuple[Tuple[int, int, int, int], np.ndarray]]:
    """`((x0, y0, x1, y1), ink)` -- the cell's `image_no_staff` (0 = ink) scaled to its page box, True = ink."""
    img = getattr(cell, "image_no_staff", None)
    bbox = getattr(cell, "bbox_page_px", None)
    if img is None or getattr(img, "ndim", 0) != 2 or not bbox or len(bbox) != 4:
        return None
    x0, y0, x1, y1 = (int(round(float(v))) for v in bbox)
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return None
    import cv2
    ink = (img < 128).astype(np.float32)
    small = cv2.resize(ink, (w, h), interpolation=cv2.INTER_AREA)
    return (x0, y0, x1, y1), small >= 0.35


def composite_ink(page_binary: np.ndarray, cells: Sequence[Any]) -> np.ndarray:
    """Page ink (True), staff lines removed wherever a cell covers: AND of every covering cell's erased ink."""
    raw = page_binary < 128
    H, W = raw.shape
    cover = np.zeros((H, W), np.uint8)
    inked = np.zeros((H, W), np.uint8)
    for c in cells:
        got = _cell_ink_on_page(c)
        if got is None:
            continue
        (x0, y0, x1, y1), ink = got
        cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
        if cx1 <= cx0 or cy1 <= cy0:
            continue
        sub = ink[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
        cover[cy0:cy1, cx0:cx1] += 1
        inked[cy0:cy1, cx0:cx1] += sub.astype(np.uint8)
    out = raw.copy()
    m = cover > 0
    out[m] = (inked[m] == cover[m]) & raw[m]
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The trace
# ─────────────────────────────────────────────────────────────────────────────

def _runs(col: np.ndarray) -> List[Tuple[int, int]]:
    """Inclusive (start, end) of every True run in a 1-D bool array."""
    if not col.any():
        return []
    d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
    s = np.flatnonzero(d == 1)
    e = np.flatnonzero(d == -1) - 1
    return list(zip(s.tolist(), e.tolist()))


def _raw_run_len(raw: np.ndarray, x: int, r: Tuple[int, int]) -> int:
    """The length of the RAW page run (staff lines IN) holding the composite run `r` at column `x`: a stem or barline
    that staff-line removal cut into short pieces is one long run here."""
    col = raw[:, x]
    a, b = r
    if not col[a:b + 1].any():
        return b - a + 1
    while a > 0 and col[a - 1]:
        a -= 1
    while b < len(col) - 1 and col[b + 1]:
        b += 1
    return b - a + 1


class _Columns:
    """Thin runs per page column inside a row window, cached."""

    def __init__(self, ink: np.ndarray, r0: int, r1: int, max_len: float,
                 raw: Optional[np.ndarray] = None, raw_max: float = 0.0):
        self.ink, self.r0, self.r1, self.max_len = ink, r0, r1, max_len
        self.raw, self.raw_max = raw, raw_max
        self._cache: Dict[int, List[Tuple[int, int]]] = {}

    def thin(self, x: int) -> List[Tuple[int, int]]:
        got = self._cache.get(x)
        if got is None:
            if x < 0 or x >= self.ink.shape[1]:
                got = []
            else:
                got = [(a + self.r0, b + self.r0) for a, b in _runs(self.ink[self.r0:self.r1, x])
                       if (b - a + 1) <= self.max_len]
                if self.raw is not None:
                    got = [r for r in got if _raw_run_len(self.raw, x, r) <= self.raw_max]
            self._cache[x] = got
        return got

    def raw_thin(self, x: int) -> List[Tuple[int, int]]:
        """Fallback where the composite has no stroke: the RAW page's short runs (an arc lying ALONG a staff line
        merges with it, and the staff-line removal took it with the line)."""
        if self.raw is None or x < 0 or x >= self.raw.shape[1]:
            return []
        return [(a + self.r0, b + self.r0) for a, b in _runs(self.raw[self.r0:self.r1, x])
                if (b - a + 1) <= self.raw_max]


def _follow(cols: _Columns, x: int, yc: float, step: int, x_stop: int, sp: float,
            pts: Dict[int, Tuple[int, int]], box_x: Tuple[int, int] = (-1 << 30, 1 << 30),
            raw_pts: Optional[set] = None) -> None:
    """Greedy: from the run at (x, yc) walk `step` (+1/-1) to `x_stop`, adding the run nearest the predicted y."""
    hist: List[Tuple[int, float]] = [(x, yc)]
    seed = pts.get(x)
    thick: List[int] = [seed[1] - seed[0] + 1] if seed else []
    gap = 0
    gap_max = max(2, int(round(GAP_MAX_SPACES * sp)))
    tol0 = max(2.0, TOL_SPACES * sp)
    look = max(3, int(round(0.5 * sp)))
    xx = x + step
    while (xx <= x_stop) if step > 0 else (xx >= x_stop):
        lx, ly = hist[-1]
        k = hist[0]
        for h in reversed(hist):
            if abs(lx - h[0]) >= look:
                k = h
                break
        slope = (ly - k[1]) / float(lx - k[0]) if lx != k[0] else 0.0
        slope = max(-2.0, min(2.0, slope))
        # past its own box the trace is a TAIL the crop cut: a tie's or slur's end runs shallow into its head; a steep
        # climb there is the outline of a head or a stem, not the arc
        if not (box_x[0] <= xx <= box_x[1]) and abs(slope) > EXT_MAX_SLOPE:
            return
        dx = xx - lx
        pred = ly + slope * dx
        tol = tol0 + 0.5 * abs(slope) * abs(dx) + 0.25 * abs(dx) * (1 if gap else 0)
        best = None
        from_raw = False
        # THE STROKE CONTINUES (Sean's tile 11, 2026-10-17: our trace left a tie at the barline and carried on along
        # the slur beside it). A run much thicker than the stroke so far is the stroke MERGED with something -- a
        # barline, or the other arc where the two touch -- and its centre is not the stroke's height: it bridges as
        # a gap, so the prediction keeps the stroke's own height and slope across it.
        thick_max = THICK_CONTINUE_FACTOR * float(np.median(thick[-look:])) + 2.0 if thick else float("inf")
        for source in (cols.thin, cols.raw_thin):
            for a, b in source(xx):
                if (b - a + 1) > thick_max:
                    continue
                c = (a + b) / 2.0
                d = abs(c - pred)
                if d <= tol and (best is None or d < best[0]):
                    best = (d, a, b, c)
            if best is not None:
                break
            from_raw = True
        if best is None:
            gap += 1
            if gap > gap_max:
                return
        else:
            # a run found only on the RAW page (the stroke merged with a staff line) BRIDGES, at a quarter of a gap's
            # cost, so a trace can never ride a staff line far; such points are trimmed off the trace's two ends
            gap = gap + RAW_BRIDGE_COST if from_raw else 0
            if gap > gap_max:
                return
            if from_raw and raw_pts is not None:
                raw_pts.add(xx)
            pts[xx] = (best[1], best[2])
            hist.append((xx, best[3]))
            thick.append(best[2] - best[1] + 1)
            if len(hist) > 4 * look:
                hist = hist[-2 * look:]
        xx += step


def trace_arc(ink: np.ndarray, box: Sequence[float], sp: float, *, x_min: float, x_max: float,
              raw: Optional[np.ndarray] = None
              ) -> Optional[Dict[str, Any]]:
    """Follow the thin stroke inside `box` (page px) out to `x_min..x_max`. `None` off the raster / no unit.

    Returns {points: {x: (y0, y1)}, coverage (share of the box's own columns inked), x0, x1, y_left, y_right}."""
    if ink is None or getattr(ink, "ndim", 0) != 2 or not sp or sp <= 0:
        return None
    H, W = ink.shape
    bx0, by0, bx1, by1 = (int(round(float(v))) for v in box)
    bx0, bx1 = max(0, bx0), min(W - 1, bx1)
    if bx1 <= bx0 or by1 <= by0:
        return None
    pad = int(round(ROW_PAD_SPACES * sp))
    r0, r1 = max(0, by0 - pad), min(H, by1 + pad + 1)
    cols = _Columns(ink, r0, r1, STROKE_MAX_SPACES * sp, raw, (STROKE_MAX_SPACES + RAW_LINE_ALLOWANCE_SPACES) * sp)
    lo, hi = max(0, int(round(x_min))), min(W - 1, int(round(x_max)))
    mid = (bx0 + bx1) // 2
    half = max(2, int(round(0.3 * sp)))
    # seed columns: nearest the box's middle first, anywhere in the box (an arc lying along a staff line loses its
    # middle to the staff-line removal); up to SEED_COLUMNS columns at least `half` apart
    seeds: List[Tuple[int, int, int]] = []
    used: List[int] = []
    for x in sorted(range(bx0, bx1 + 1), key=lambda v: abs(v - mid)):
        if len(used) >= SEED_COLUMNS:
            break
        if any(abs(x - u) < half for u in used):
            continue
        rs = [(a, b) for a, b in cols.thin(x) if a >= by0 - 2 and b <= by1 + 2]
        if rs:
            used.append(x)
            seeds += [(x, a, b) for a, b in rs]
    best = None
    width = float(bx1 - bx0 + 1)
    for x, a, b in seeds:
        pts: Dict[int, Tuple[int, int]] = {x: (a, b)}
        yc = (a + b) / 2.0
        raw_pts: set = set()
        _follow(cols, x, yc, +1, hi, sp, pts, (bx0, bx1), raw_pts)
        _follow(cols, x, yc, -1, lo, sp, pts, (bx0, bx1), raw_pts)
        for order in (sorted(pts), sorted(pts, reverse=True)):     # trim raw-only points off both ends
            for xx in order:
                if xx not in raw_pts:
                    break
                del pts[xx]
        inside = sum(1 for xx in pts if bx0 <= xx <= bx1)
        cov = inside / width
        if best is None or cov > best["coverage"]:
            best = {"points": pts, "coverage": round(cov, 3)}
    if best is None:
        return {"points": {}, "coverage": 0.0, "x0": None, "x1": None, "y_left": None, "y_right": None}
    return _finish(best["points"], best["coverage"])


def _finish(pts: Dict[int, Tuple[int, int]], coverage: float) -> Dict[str, Any]:
    xs = sorted(pts)
    if not xs:
        return {"points": {}, "coverage": coverage, "x0": None, "x1": None, "y_left": None, "y_right": None}
    return {"points": pts, "coverage": coverage, "x0": xs[0], "x1": xs[-1],
            "y_left": sum(pts[xs[0]]) / 2.0, "y_right": sum(pts[xs[-1]]) / 2.0}


# ─────────────────────────────────────────────────────────────────────────────
# One curve from its pieces
# ─────────────────────────────────────────────────────────────────────────────

def is_straight(pts: Dict[int, Tuple[int, int]], sp: float) -> bool:
    """A trace at least `STRAIGHT_MIN_SPACES` long whose centres never leave a straight line by `STRAIGHT_SPACES`: a
    beam or a line. An arc curves (a tie three spaces long rises ~0.4 sp in the middle)."""
    xs = np.asarray(sorted(pts), float)
    if len(xs) < 3 or (xs[-1] - xs[0]) < STRAIGHT_MIN_SPACES * sp:
        return False
    ys = np.asarray([(pts[int(x)][0] + pts[int(x)][1]) / 2.0 for x in xs])
    k, c = np.polyfit(xs, ys, 1)
    return float(np.max(np.abs(ys - (k * xs + c)))) < STRAIGHT_SPACES * sp


def on_a_staff_line(pts: Dict[int, Tuple[int, int]], line_ys: Sequence[float], sp: float) -> bool:
    """A flat trace whose columns mostly sit on a staff line's rows: a line's residue, not an arc."""
    if not pts or not line_ys:
        return False
    cs = [(a + b) / 2.0 for a, b in pts.values()]
    if max(cs) - min(cs) > FLAT_SPACES * sp:
        return False
    ys = np.asarray(line_ys)
    near = sum(1 for c in cs if np.min(np.abs(ys - c)) <= 0.2 * sp)
    return near >= ON_LINE_SHARE * len(cs)


def _end_slope(pts: Dict[int, Tuple[int, int]], side: str, sp: float) -> float:
    """dy/dx over the last half space of the trace at `side` ("left" / "right")."""
    xs = sorted(pts)
    n = max(2, int(round(0.5 * sp)))
    sel = xs[:n] if side == "left" else xs[-n:]
    if len(sel) < 2 or sel[-1] == sel[0]:
        return 0.0
    ys = [(pts[x][0] + pts[x][1]) / 2.0 for x in sel]
    return float(np.polyfit(np.asarray(sel, float), np.asarray(ys), 1)[0])


def end_join_cost(left: Dict[str, Any], right: Dict[str, Any], sp: float) -> Optional[float]:
    """How well `left`'s right end continues into `right`'s left end, or None where it does not: the gap is short,
    the HEIGHT continues (the left end's tangent carried across the gap lands on the right start) and the TANGENTS
    agree. Sean's tile 11 (2026-10-17): a tie on one side of a barline and a slur on the other meet at a barline at
    nearly one height but turn opposite ways."""
    gap = right["x0"] - left["x1"]
    if not (0 < gap <= GAP_MAX_SPACES * sp):
        return None
    sl, sr = _end_slope(left["points"], "right", sp), _end_slope(right["points"], "left", sp)
    if abs(sl - sr) > END_JOIN_SLOPE:
        return None
    dy = abs(left["y_right"] + sl * gap - right["y_left"])
    if dy > END_JOIN_Y_SPACES * sp:
        return None
    return dy / sp + abs(sl - sr)


def same_curve(a: Dict[str, Any], b: Dict[str, Any], sp: float) -> bool:
    """Two traces are one curve: they agree at one y over most of the columns they share, or one ends where the other
    begins and continues it (`end_join_cost`)."""
    pa, pb = a["points"], b["points"]
    if not pa or not pb:
        return False
    tol = max(2.0, SAME_Y_SPACES * sp)
    shared = [x for x in pa if x in pb]
    if shared:
        n = sum(1 for x in shared if abs(sum(pa[x]) / 2.0 - sum(pb[x]) / 2.0) <= tol)
        return n >= min(SAME_MIN_COLS, len(shared)) and n >= SAME_SHARE * len(shared)
    left, right = (a, b) if a["x1"] < b["x0"] else (b, a)
    return end_join_cost(left, right, sp) is not None


def join_traces(traces: Sequence[Dict[str, Any]], sp: float) -> List[List[int]]:
    """Groups of indices into `traces` that are one curve, left to right: union-find over the shared-column agreements
    and, for end-to-start meetings, each end joined only to the ONE piece that continues it best."""
    parent = list(range(len(traces)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    ends: List[Tuple[float, int, int]] = []
    for i in range(len(traces)):
        for j in range(len(traces)):
            if i == j or not traces[i]["points"] or not traces[j]["points"]:
                continue
            if any(x in traces[j]["points"] for x in traces[i]["points"]):
                if i < j and same_curve(traces[i], traces[j], sp):
                    parent[find(i)] = find(j)
                continue
            if traces[i]["x1"] < traces[j]["x0"]:
                c = end_join_cost(traces[i], traces[j], sp)
                if c is not None:
                    ends.append((c, i, j))
    used_right, used_left = set(), set()
    for c, i, j in sorted(ends):                 # best continuation first; each end takes one partner
        if i in used_right or j in used_left:
            continue
        used_right.add(i)
        used_left.add(j)
        parent[find(i)] = find(j)
    groups: Dict[int, List[int]] = {}
    for i in range(len(traces)):
        groups.setdefault(find(i), []).append(i)
    out = list(groups.values())
    out.sort(key=lambda g: min(traces[i]["x0"] if traces[i]["x0"] is not None else 1 << 30 for i in g))
    return out


def merge_columns(ink: np.ndarray, pts: Dict[int, Tuple[int, int]], thick_cap: float, sp: float) -> List[int]:
    """Columns along the trace where the stroke is MERGED with other ink: its own run there (a traced run, or the run
    under the interpolated stroke where the trace bridged a gap) is thicker than `thick_cap` but no taller than
    `MERGE_MAX_SPACES` (a barline or a stem is taller, and is not a merge)."""
    xs = sorted(pts)
    out: List[int] = []
    if len(xs) < 2:
        return out
    H = ink.shape[0]
    for i, x in enumerate(xs):
        r = pts[x]
        if (r[1] - r[0] + 1) > thick_cap:
            out.append(x)
        if i + 1 < len(xs) and xs[i + 1] - x > 1:                 # a bridged gap: look under the stroke
            x2 = xs[i + 1]
            y1, y2 = sum(pts[x]) / 2.0, sum(pts[x2]) / 2.0
            for g in range(x + 1, x2):
                y = int(round(y1 + (y2 - y1) * (g - x) / float(x2 - x)))
                if not (0 <= y < H) or not ink[y, g]:
                    continue
                a = b = y
                while a > 0 and ink[a - 1, g]:
                    a -= 1
                while b < H - 1 and ink[b + 1, g]:
                    b += 1
                if thick_cap < (b - a + 1) <= MERGE_MAX_SPACES * sp:
                    out.append(g)
    return out


def merge_points(traces: Sequence[Dict[str, Any]]) -> Dict[int, Tuple[int, int]]:
    pts: Dict[int, Tuple[int, int]] = {}
    for t in traces:
        for x, r in t["points"].items():
            if x not in pts or (r[1] - r[0]) < (pts[x][1] - pts[x][0]):
                pts[x] = r
    return pts


# ─────────────────────────────────────────────────────────────────────────────
# Which boxes the stroke runs through; which notes its ends sit beside
# ─────────────────────────────────────────────────────────────────────────────

def stroke_share(ink: np.ndarray, box: Sequence[float], pts: Dict[int, Tuple[int, int]], sp: float
                 ) -> Optional[Dict[str, float]]:
    """How much of a box's ink is the traced stroke: {stroke_px, residual_spaces2}; None when the stroke misses it."""
    H, W = ink.shape
    x0, y0, x1, y1 = (int(round(float(v))) for v in box)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1 + 1), min(H, y1 + 1)
    if x1 <= x0 or y1 <= y0:
        return None
    region = ink[y0:y1, x0:x1].copy()
    # a vertical line passing THROUGH the box (a barline, a stem) is not the box's own mark: its runs, measured on the
    # whole column, are left out of the residual
    reach = int(round(PASS_THROUGH_SPACES * sp))
    wy0, wy1 = max(0, y0 - reach), min(H, y1 + reach)
    for x in range(x0, x1):
        for a, b in _runs(ink[wy0:wy1, x]):
            if (b - a + 1) > reach:
                ra, rb = max(y0, a + wy0), min(y1 - 1, b + wy0)
                if rb >= ra:
                    region[ra - y0:rb - y0 + 1, x - x0] = False
    stroke = 0
    for x in range(x0, x1):
        r = pts.get(x)
        if r is None:
            continue
        a, b = max(y0, r[0] - 1), min(y1 - 1, r[1] + 1)
        if b < a:
            continue
        col = region[a - y0:b - y0 + 1, x - x0]
        stroke += int(col.sum())
        col[:] = False
    if stroke == 0:
        return None
    return {"stroke_px": stroke, "residual_spaces2": round(float(region.sum()) / (sp * sp), 4)}


def anchor_ends(pts: Dict[int, Tuple[int, int]], heads: Sequence[Tuple[str, Tuple[float, float, float, float]]],
                sp: float) -> Dict[str, Any]:
    """The head beside each end of the curve (page px), and the shape of the two: one staff position, nothing between."""
    xs = sorted(pts)
    out: Dict[str, Any] = {"left": None, "right": None, "dy_spaces": None, "heads_between": None,
                           "shape": "end_unanchored"}
    if not xs:
        return out
    ends = {"left": (xs[0], sum(pts[xs[0]]) / 2.0, -1), "right": (xs[-1], sum(pts[xs[-1]]) / 2.0, +1)}
    centres = [(g, (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0) for g, b in heads]
    picked: Dict[str, Tuple[str, float, float]] = {}
    for side, (ex, ey, sgn) in ends.items():
        best = None
        for g, cx, cy in centres:
            out_by = (cx - ex) * sgn            # > 0: the head lies beyond the end
            if out_by > ANCHOR_OUT_SPACES * sp or out_by < -ANCHOR_IN_SPACES * sp:
                continue
            if abs(cy - ey) > ANCHOR_DY_SPACES * sp:
                continue
            d = abs(cx - ex) + abs(cy - ey)
            if best is None or d < best[0]:
                best = (d, g, cx, cy)
        if best is not None:
            picked[side] = (best[1], best[2], best[3])
            out[side] = best[1]
    if "left" in picked and "right" in picked and picked["left"][0] != picked["right"][0]:
        (_, lx, ly), (_, rx, ry) = picked["left"], picked["right"]
        dy = abs(ly - ry) / sp
        between = sum(1 for g, cx, cy in centres
                      if lx + 0.5 * sp < cx < rx - 0.5 * sp and g not in (picked["left"][0], picked["right"][0]))
        out["dy_spaces"] = round(dy, 3)
        out["heads_between"] = between
        if dy <= SAME_POSITION_SPACES and between == 0:
            out["shape"] = "two_heads_one_position_adjacent"
        elif dy <= SAME_POSITION_SPACES:
            out["shape"] = "one_position_heads_between"
        else:
            out["shape"] = "two_positions"
    elif "left" in picked and "right" in picked:
        out["shape"] = "one_head_both_ends"
    return out


# ─────────────────────────────────────────────────────────────────────────────
# The erase, in a cell's own canonical frame
# ─────────────────────────────────────────────────────────────────────────────

def run_is_stroke(s: float, e: float, lo: float, hi: float, slack: float, max_run: float) -> bool:
    """A canonical ink run is the stroke's own only when it lies INSIDE the traced rows (+- `slack`) and is no taller
    than `max_run`: a run reaching past them is a head, stem or barline the arc touches, and is kept whole."""
    return s >= lo - slack and e <= hi + slack and (e - s + 1) <= max_run


def erase_in_cell(img: np.ndarray, cell_box: Sequence[float], up: float, pts: Dict[int, Tuple[int, int]],
                  protected: np.ndarray, sp_page: float) -> int:
    """Erase (set to paper, IN PLACE) the traced stroke from a cell's `image_no_staff` (0 = ink). Returns pixels erased.

    Per page column of the trace, every canonical column it maps to: an ink run that lies inside the stroke's own rows
    (+-1 page px) and is no taller than `ERASE_RUN_MAX_SPACES` is erased, minus `protected` pixels. A run that reaches
    past the stroke's rows (a head, stem or barline the arc touches) is kept whole."""
    Hc, Wc = img.shape
    x0, y0 = float(cell_box[0]), float(cell_box[1])
    max_run = ERASE_RUN_MAX_SPACES * sp_page * up
    slack = max(1.0, float(up))
    n = 0
    for x, (a, b) in pts.items():
        c0 = int(np.floor((x - x0) * up))
        c1 = int(np.ceil((x + 1 - x0) * up))
        if c1 <= 0 or c0 >= Wc:
            continue
        lo = (a - 1 - y0) * up
        hi = (b + 2 - y0) * up
        if hi <= 0 or lo >= Hc:
            continue
        for cx in range(max(0, c0), min(Wc, c1)):
            col = img[:, cx] < 128
            for s, e in _runs(col):
                if e < lo or s > hi:
                    continue
                if not run_is_stroke(s, e, lo, hi, slack, max_run):
                    continue
                keep = protected[s:e + 1, cx]
                rows = np.arange(s, e + 1)[~keep]
                if rows.size:
                    img[rows, cx] = 255
                    n += int(rows.size)
    return n


def protected_mask(shape: Tuple[int, int], cell_box: Sequence[float], up: float,
                   boxes: Sequence[Sequence[float]]) -> np.ndarray:
    """Canonical-frame mask of every protected page box (a non-arc detection) that reaches this cell."""
    Hc, Wc = shape
    m = np.zeros((Hc, Wc), bool)
    x0, y0 = float(cell_box[0]), float(cell_box[1])
    for b in boxes:
        c0 = int(np.floor((b[0] - x0) * up))
        c1 = int(np.ceil((b[2] - x0) * up))
        r0 = int(np.floor((b[1] - y0) * up))
        r1 = int(np.ceil((b[3] - y0) * up))
        if c1 <= 0 or r1 <= 0 or c0 >= Wc or r0 >= Hc:
            continue
        m[max(0, r0):min(Hc, r1 + 1), max(0, c0):min(Wc, c1 + 1)] = True
    return m


# ─────────────────────────────────────────────────────────────────────────────
# The GATHER step
# ─────────────────────────────────────────────────────────────────────────────

def _page_box(cell: Any, det: Any) -> Optional[Tuple[float, float, float, float]]:
    bbox = getattr(cell, "bbox_page_px", None)
    up = getattr(cell, "upscale_factor", None)
    if not bbox or not up:
        return None
    x0, y0 = bbox[0], bbox[1]
    return (x0 + det.x_canonical / up, y0 + det.y_canonical / up,
            x0 + (det.x_canonical + det.width_canonical) / up,
            y0 + (det.y_canonical + det.height_canonical) / up)


def _space_page(cell: Any) -> Optional[float]:
    lines = list(getattr(cell, "staff_line_ys_canonical", None) or [])
    up = getattr(cell, "upscale_factor", None)
    if len(lines) < 2 or not up:
        return None
    gaps = [lines[i + 1] - lines[i] for i in range(len(lines) - 1)]
    return (sum(gaps) / len(gaps)) / float(up)


def gather_system_arcs(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]],
                       detections: Dict[str, List[Any]], *, progress: bool = False) -> Dict[str, Any]:
    """`Q.SYSTEM_ARC` per joined arc, then the traced strokes erased from every cell's `image_no_staff`.

    No-op (returns {}) unless `OMR_SYSTEM_ARCS` is on. Returns a small summary (for probes)."""
    if not enabled():
        return {}
    from . import record as R
    from .record import ABSTAIN, Q, READERS

    binary = getattr(getattr(pws, "page", None), "binary", None)
    staffed = []
    for c in cells:
        key = local.get(c.staff_index)
        if key is not None:
            staffed.append((c, key))
    arcs_by_staff: Dict[Tuple[int, int, int], List[Dict[str, Any]]] = {}
    heads_by_staff: Dict[Tuple[int, int, int], List[Tuple[str, Tuple[float, float, float, float]]]] = {}
    marks_by_staff: Dict[Tuple[int, int, int], List[Tuple[str, str, Tuple[float, float, float, float]]]] = {}
    others: List[Tuple[str, str, Tuple[float, float, float, float]]] = []
    cell_of: Dict[Tuple[int, int, int, int], Any] = {}
    for c, key in staffed:
        cell_of[(c.page_index, key[0], key[1], c.measure_index)] = c
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)
        sp = _space_page(c)
        for gi, d in enumerate(detections.get(sub.to_key(), ())):
            pb = _page_box(c, d)
            if pb is None:
                continue
            g = R.glyph(c.page_index, key[0], key[1], c.measure_index, gi)
            name = str(d.smufl_name)
            if name in _ARC_CLASSES:
                arcs_by_staff.setdefault((c.page_index, key[0], key[1]), []).append(
                    {"glyph": g, "cell": c, "box": pb, "sp": sp, "cls": name})
            else:
                if name.lower().startswith(_NOTEHEAD_PREFIX):
                    heads_by_staff.setdefault((c.page_index, key[0], key[1]), []).append((g.to_key(), pb))
                others.append((g.to_key(), name, pb))
                if is_protected_class(name):
                    marks_by_staff.setdefault((c.page_index, key[0], key[1]), []).append((g.to_key(), name, pb))

    summary: Dict[str, Any] = {"pieces": 0, "read": 0, "abstained": 0, "arcs": 0, "joined_across_barline": 0,
                               "erased_px": 0, "stroke_only_heads": [], "arcs_detail": []}
    if not arcs_by_staff:
        return summary
    if binary is None or getattr(binary, "ndim", 0) != 2 or float((binary < 128).mean()) > 0.5:
        for pieces in arcs_by_staff.values():
            for p in pieces:
                log.abstain(p["glyph"], Q.SYSTEM_ARC, reader=READERS.CV_SYSTEM_ARC, frame="page",
                            reason=ABSTAIN.NO_MASK, note="no page raster (0 = ink), or its polarity is wrong")
        return summary

    ink = composite_ink(binary, [c for c, _ in staffed])
    raw = binary < 128
    line_ys = sorted(float(y) for st in (getattr(pws, "staves", None) or ()) for y in st.line_ys)
    # the system's own x extent per (page, system): a trace never leaves its system
    sys_x: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for c, key in staffed:
        b = getattr(c, "bbox_page_px", None)
        if b:
            lo, hi = sys_x.get((c.page_index, key[0]), (float("inf"), float("-inf")))
            sys_x[(c.page_index, key[0])] = (min(lo, float(b[0])), max(hi, float(b[2])))

    erase_plan: List[Tuple[Dict[int, Tuple[int, int]], float]] = []
    stroke_only: set = set()
    for (pg, sy, st), pieces in sorted(arcs_by_staff.items()):
        sx0, sx1 = sys_x.get((pg, sy), (0.0, float(ink.shape[1] - 1)))
        traces: List[Dict[str, Any]] = []
        kept: List[Dict[str, Any]] = []
        for p in pieces:
            summary["pieces"] += 1
            sp = p["sp"]
            cb = getattr(p["cell"], "bbox_page_px", None)
            if not sp or not cb:
                log.abstain(p["glyph"], Q.SYSTEM_ARC, reader=READERS.CV_SYSTEM_ARC, frame="page",
                            reason=ABSTAIN.NO_STAFF_GEOMETRY)
                summary["abstained"] += 1
                continue
            bx0, _, bx1, _ = p["box"]
            cut_left = (bx0 - float(cb[0])) <= CUT_EDGE_SPACES * sp
            cut_right = (float(cb[2]) - bx1) <= CUT_EDGE_SPACES * sp
            x_min = max(sx0, bx0 - (CUT_EXTEND_SPACES if cut_left else FREE_EXTEND_SPACES) * sp)
            x_max = min(sx1, bx1 + (CUT_EXTEND_SPACES if cut_right else FREE_EXTEND_SPACES) * sp)
            t = trace_arc(ink, p["box"], sp, x_min=x_min, x_max=x_max, raw=raw)
            if t is not None and t["points"] and on_a_staff_line(
                    {x: r for x, r in t["points"].items() if bx0 <= x <= bx1}, line_ys, sp):
                log.abstain(p["glyph"], Q.SYSTEM_ARC, reader=READERS.CV_SYSTEM_ARC, frame="page",
                            reason=ABSTAIN.BELOW_THRESHOLD, note="the trace lies flat along a staff line")
                summary["abstained"] += 1
                summary["on_a_staff_line"] = summary.get("on_a_staff_line", 0) + 1
                continue
            if t is not None and t["points"] and is_straight(t["points"], sp) and float(
                    np.median([r[1] - r[0] + 1 for r in t["points"].values()])) >= STRAIGHT_BEAM_THICK_SPACES * sp:
                log.abstain(p["glyph"], Q.SYSTEM_ARC, reader=READERS.CV_SYSTEM_ARC, frame="page",
                            reason=ABSTAIN.BELOW_THRESHOLD, note="the trace is straight and as thick as a beam: not an arc")
                summary["abstained"] += 1
                summary["straight"] = summary.get("straight", 0) + 1
                continue
            if t is None or t["coverage"] < MIN_COVER or not t["points"]:
                log.abstain(p["glyph"], Q.SYSTEM_ARC, reader=READERS.CV_SYSTEM_ARC, frame="page",
                            reason=ABSTAIN.BELOW_THRESHOLD,
                            note="trace inks %.2f of the box's columns (needs %.2f)"
                                 % ((t or {}).get("coverage", 0.0), MIN_COVER))
                summary["abstained"] += 1
                continue
            t.update(piece=p, cut_left=cut_left, cut_right=cut_right)
            traces.append(t)
            kept.append(p)
            summary["read"] += 1
        if not traces:
            continue
        sp_staff = float(np.median([t["piece"]["sp"] for t in traces]))
        heads = heads_by_staff.get((pg, sy, st), [])
        for grp in join_traces(traces, sp_staff):
            members = sorted((traces[i] for i in grp), key=lambda t: t["x0"])
            pts = merge_points(members)
            cells_in = sorted({m["piece"]["cell"].measure_index for m in members})
            xs = sorted(pts)
            # which protected boxes the stroke runs through, and whether their own ink is all stroke (a tail the
            # cut crop boxed as a head -- 2.164 -- or as a beam)
            through = []
            for hg, hname, hb in marks_by_staff.get((pg, sy, st), []):
                if hb[2] < xs[0] or hb[0] > xs[-1]:
                    continue
                sh = stroke_share(ink, hb, pts, sp_staff)
                if sh is None:
                    continue
                only = (sh["residual_spaces2"] < STROKE_ONLY_RESIDUAL_SPACES2
                        and str(hname).startswith(STROKE_ONLY_CLASSES)
                        # a beam box is the arc's twin only where it overlaps one of the arc's own boxes
                        and (not str(hname).startswith("beam")
                             or any(_overlap_share(hb, m["piece"]["box"]) >= BEAM_TWIN_OVERLAP for m in members)))
                through.append({"glyph": hg, "class": hname, "residual_spaces2": sh["residual_spaces2"],
                                "stroke_only": only})
                if only:
                    stroke_only.add(hg)
            anchor_heads = [(hg, hb) for hg, hb in heads if hg not in stroke_only]
            anc = anchor_ends(pts, anchor_heads, sp_staff)
            first = members[0]["piece"]
            boxed_x0 = min(m["piece"]["box"][0] for m in members)
            boxed_x1 = max(m["piece"]["box"][2] for m in members)
            detail = dict(
                pieces=[m["piece"]["glyph"].to_key() for m in members],
                piece_classes=[m["piece"]["cls"] for m in members],
                cells=cells_in,
                x_left_page=xs[0], x_right_page=xs[-1],
                y_left_page=round(sum(pts[xs[0]]) / 2.0, 1), y_right_page=round(sum(pts[xs[-1]]) / 2.0, 1),
                width_spaces=round((xs[-1] - xs[0]) / sp_staff, 2),
                inked_columns=len(xs),
                coverage=[m["coverage"] for m in members],
                cut_at_barline=any(m["cut_left"] or m["cut_right"] for m in members),
                beyond_boxes_spaces=round(max(0.0, boxed_x0 - xs[0], xs[-1] - boxed_x1) / sp_staff, 2),
                through_boxes=through,
                anchor_left=anc["left"], anchor_right=anc["right"],
                anchor_dy_spaces=anc["dy_spaces"], heads_between=anc["heads_between"],
                space_page_px=round(sp_staff, 3),
            )
            log.observe(first["glyph"], Q.SYSTEM_ARC, anc["shape"], reader=READERS.CV_SYSTEM_ARC,
                        frame="page", score=None, **detail)
            summary["arcs"] += 1
            if len(cells_in) > 1:
                summary["joined_across_barline"] += 1
            summary["arcs_detail"].append(dict(subject=first["glyph"].to_key(), shape=anc["shape"], **detail))
            # ERASE only where the detector itself boxed this arc (its pieces' boxes, padded) or where a box holds
            # nothing but its stroke: the trace past that is evidence for the join and the anchors, not ink to remove
            pad = ERASE_BOX_PAD_SPACES * sp_staff
            zones = [(b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad) for b in (m["piece"]["box"] for m in members)]
            zones += [hb for hg, hname, hb in marks_by_staff.get((pg, sy, st), []) if hg in stroke_only]
            # and never a column whose run is much thicker than the stroke's own (a beam the trace ran onto)
            thick_cap = THICK_FACTOR * float(np.median([b - a + 1 for a, b in pts.values()])) + 1.0
            # ... and never within `MERGE_KEEP_SPACES` of where the stroke MERGES with other ink (its run there thicker
            # than the stroke, but no taller than a mark): erasing up to a merge leaves the other mark's share of the
            # merged run standing alone as a short straight bar, which the beam reader then reads as a beam
            # (Brahms 317803 pdf 1, cell 1/0/0/0: 8 eighths read as sixteenths)
            merges = merge_columns(ink, pts, thick_cap, sp_staff)
            keep = MERGE_KEEP_SPACES * sp_staff
            pts_erase = {x: r for x, r in pts.items()
                         if (r[1] - r[0] + 1) <= thick_cap
                         and not any(abs(x - mx) <= keep for mx in merges)
                         and any(z[0] <= x <= z[2] and r[1] >= z[1] and r[0] <= z[3] for z in zones)}
            erase_plan.append((pts_erase, sp_staff))
            if progress:
                print(f"  gather system arc {first['glyph'].to_key()} {anc['shape']} cells={cells_in}")

    summary["stroke_only_heads"] = sorted(stroke_only)
    # ── the erase: every cell the traced strokes reach, minus every protected box ──
    arc_boxes = [p["box"] for ps in arcs_by_staff.values() for p in ps]
    protect = [b for g, name, b in others
               if g not in stroke_only and is_protected_class(name)
               and not (name == "beam" and any(_iou(b, ab) >= BEAM_TWIN_IOU for ab in arc_boxes))]
    for c, key in staffed:
        img = getattr(c, "image_no_staff", None)
        cb = getattr(c, "bbox_page_px", None)
        up = getattr(c, "upscale_factor", None)
        if img is None or not cb or not up:
            continue
        reach = [(pts, sp) for pts, sp in erase_plan
                 if pts and min(pts) <= float(cb[2]) and max(pts) >= float(cb[0])]
        if not reach:
            continue
        out = img.copy()
        pm = protected_mask(out.shape, cb, float(up), protect)
        n = 0
        for pts, sp in reach:
            sub = {x: r for x, r in pts.items() if float(cb[0]) - 1 <= x <= float(cb[2]) + 1
                   and r[1] >= float(cb[1]) and r[0] <= float(cb[3])}
            if sub:
                n += erase_in_cell(out, cb, float(up), sub, pm, sp)
        if n:
            if getattr(c, "image_no_staff_with_arcs", None) is None:
                c.image_no_staff_with_arcs = img
            c.image_no_staff = out
            summary["erased_px"] += n
    return summary
