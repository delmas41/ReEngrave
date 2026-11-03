"""ROADMAP 2.260a M2 -- THE PAGE STROKE MAP, filed beside the cell strokes and read by NOTHING (STAGED GATHER; flag `OMR_PAGE_STROKES`, default OFF).

    docs/plan-2026-11-03-page-ledger.md §B.1, §C M2.

WHAT. Every stroke of the PAGE, measured once, in page pixels: the same finders as the cell map (`stroke_map.map_strokes`, nothing re-tuned), run on
ONE raster assembled from what the pipeline already holds --

  * inside each staff's own BAND (top line - `BAND_MARGIN_SPACES` .. bottom line + `BAND_MARGIN_SPACES`): that staff's `cell.image_no_staff` (the frozen
    eraser's output, so the staff lines are gone), sampled onto the page by the same centre-aligned nearest rule `page_marks.seen_on_page` uses;
  * everywhere else: `page.binary` (a stem, a hairpin or a slur between staves has no lines on it to erase; a neighbour's lines are erased by the
    neighbour's own band, so they are no longer flat strokes on another staff's line).

A band pixel no cell covers (left of the first cell, right of the last) is COUNTED (`band_uncovered_px`) and its long level runs (the staff line the
eraser never saw there, `line_ink_removed_px`) are taken out; what else stands there (a brace, the system's opening rule) stays and is read page-wide
already (2.221 m1b).

THE BARLINE COLUMN IS CARVED OUT FIRST (M1's tilted line, `barline_columns`): along each column the ink within the rule's own measured width is taken
out of the raster and filed as ONE `barline` stroke, so a head or a stem that touches a barline does not fuse with it, and the rule is no longer two
half-strokes cut at the cell edge (78% of Litolff and 83% of Brahms staff-barlines on the cell map, `half_barline_cells`). Only rows whose core is
inked, in runs of at least `CARVE_RUN_MIN_SPACES`, are carved: a slur crossing the column is not a rule.

THE STAFF A STROKE IS READ AGAINST is chosen by its own y (`PageStaff.lines_at(x, y)`), and its ends are given in steps from THAT staff's lines
at their own x -- the cell map's rule, one `LocalStaff` per staff. The detector's clef / key / meter and accidental / head / ledger / stem boxes are
mapped to page pixels and handed to the same splitter (`keep_whole`, `touch_boxes`), twins from two cells de-duplicated.

WHAT IT FILES. One `Q.PAGE_STROKE` row per stroke on the page's subject (`value` = kind, or `barline`); `detail` mirrors `Q.STROKE` in PAGE px. It
decides nothing, NOTHING READS IT, and the exported file is byte-identical with the flag on (the proof is the lane report). No claim names a page stroke
yet (M3 translates `[[cell, ordinal]]`).

CONVENTION ASSUMED: a band of +-0.5 sp around the lines holds everything the eraser touched (the staff line, the ink a note on a line shares with it);
what lies outside is never altered by it. WHAT WOULD FALSIFY IT: parity (below) failing at the band edge, not in the middle. NOT CONFIRMED beyond
the two plates.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_STROKES"
BAND_MARGIN_SPACES = 0.5
#: the carve is the rule's own measured width (+ this many px each side), never a fixed fraction of a space: a head touching the rule keeps its ink
CARVE_PAD_PX = 1
#: how far from the fitted line the rule's core is looked for (px either side of the line), and the widest run that can still be a rule (spaces)
CARVE_CORE_PX = 2
CARVE_MAX_WIDTH_SPACES = 0.9
#: a carved stretch is a rule only in runs this long (a slur crossing the column is ink on the line for a few rows); gaps up to this are bridged
CARVE_RUN_MIN_SPACES = 1.0
CARVE_GAP_BRIDGE_SPACES = 0.25
#: a level run at least this long (spaces) in a band no cell covers is a staff line, taken out
LINE_RUN_MIN_SPACES = 3.0
#: twin detector boxes (the same mark boxed by two cells) closer than this many px at every edge are one box for the splitter
BOX_DEDUP_PX = 2
#: a PageStaff owns the rows this many spaces beyond its lines; a stroke further than that from every staff takes the nearest
STAFF_REACH_SPACES = 3.0


def enabled() -> bool:
    """`OMR_PAGE_STROKES` (ROADMAP 2.260a M2), default OFF."""
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def _centre_index(a: int, b: int, n_dst: int, n_src: int) -> np.ndarray:
    """Source indices for destination rows/cols a..b-1 of an n_dst-long axis resampled centre-aligned nearest from n_src (`page_marks._centre_index`)."""
    return np.minimum(((np.arange(a, b) + 0.5) * n_src / float(n_dst)).astype(np.int64), n_src - 1)


# ───────────────────────────── the staves, one lines_at(x, y) ─────────────────────────────

class PageStaff:
    """Every staff of the page behind the `lines_at(x, y)` the stroke measurer calls (reduced frame): one `stroke_map.LocalStaff` per staff, on that
    staff's own strip of the reduced RAW raster, chosen by y."""

    def __init__(self, raw_small: Optional[np.ndarray], staves: Sequence[Any], scale: float, sp_small: float):
        from .stroke_map import LocalStaff
        self.scale = float(scale)
        self.local = False
        self._staves: List[Any] = []
        self._tops: List[float] = []
        self._bots: List[float] = []
        self._ls: List[Any] = []
        self._ya: List[int] = []
        for s in sorted(staves, key=lambda s: s.top_y):
            sp = float(s.line_spacing_px) * scale
            ya = max(0, int(round(s.top_y * scale - STAFF_REACH_SPACES * sp)))
            yb = int(round(s.bottom_y * scale + STAFF_REACH_SPACES * sp))
            nominal = [float(y) * scale - ya for y in s.line_ys]
            strip = None if raw_small is None else raw_small[ya:yb]
            ls = LocalStaff(strip, nominal, sp_small)
            self._staves.append(s)
            self._tops.append(s.top_y * scale)
            self._bots.append(s.bottom_y * scale)
            self._ls.append(ls)
            self._ya.append(ya)
            self.local = self.local or ls.local

    def index_at(self, y: float) -> int:
        """The staff whose lines `y` (reduced frame) is read against: the one it lies within (or within `STAFF_REACH_SPACES`), else the nearest."""
        best, bd = 0, float("inf")
        for i, (t, b) in enumerate(zip(self._tops, self._bots)):
            d = 0.0 if t <= y <= b else min(abs(y - t), abs(y - b))
            if d < bd:
                best, bd = i, d
        return best

    def lines_at(self, x: float, y: Optional[float] = None) -> List[float]:
        i = self.index_at(0.0 if y is None else float(y))
        return [v + self._ya[i] for v in self._ls[i].lines_at(x)]

    def staff_at(self, y_page: float) -> Any:
        return self._staves[self.index_at(y_page * self.scale)]


# ───────────────────────────── 1. assemble ─────────────────────────────

@dataclass
class Assembly:
    canvas: np.ndarray                                   # uint8, 0 = ink, page-sized
    stats: Dict[str, Any] = field(default_factory=dict)


def bands(pws: Any) -> List[Tuple[Any, int, int]]:
    """`(staff, y0, y1)` page rows of each staff's band (half-open), clipped to the page."""
    h = pws.page.binary.shape[0]
    out = []
    for s in pws.staves:
        sp = float(s.line_spacing_px)
        out.append((s, max(0, int(round(s.top_y - BAND_MARGIN_SPACES * sp))), min(h, int(round(s.bottom_y + BAND_MARGIN_SPACES * sp)) + 1)))
    return out


def assemble(pws: Any, cells: Sequence[Any]) -> Assembly:
    """The page raster of the module doc, before the carve. `stats`: band pixels placed, placed TWICE (two cells over one pixel: the first wins),
    uncovered (blanked), per staff."""
    page = pws.page.binary
    canvas = page.copy()
    by_staff: Dict[int, List[Any]] = {}
    for c in cells:
        by_staff.setdefault(c.staff_index, []).append(c)
    placed = twice = uncovered = lines_removed = 0
    per_staff: Dict[int, Dict[str, int]] = {}
    H, W = canvas.shape
    for s, y0, y1 in bands(pws):
        if y1 <= y0:
            continue
        written = np.zeros((y1 - y0, W), bool)
        n_twice = 0
        for c in by_staff.get(s.staff_index, ()):
            img = getattr(c, "image_no_staff", None)
            rect = getattr(c, "bbox_page_px", None)
            if img is None or getattr(img, "ndim", 0) != 2 or not rect:
                continue
            rx0, ry0, rx1, ry1 = (int(v) for v in rect)
            rx0, rx1 = max(0, rx0), min(W, rx1)
            ya, yb = max(y0, ry0), min(y1, ry1)
            if rx1 <= rx0 or yb <= ya:
                continue
            h, w = ry1 - ry0, int(rect[2]) - int(rect[0])
            ri = _centre_index(ya - ry0, yb - ry0, h, img.shape[0])
            ci = _centre_index(rx0 - int(rect[0]), rx1 - int(rect[0]), w, img.shape[1])
            sampled = img[np.ix_(ri, ci)]
            sub = written[ya - y0:yb - y0, rx0:rx1]
            n_twice += int(sub.sum())
            put = ~sub
            region = canvas[ya:yb, rx0:rx1]
            region[put] = sampled[put]
            sub |= True
        n_band = int(written.shape[0] * W)
        n_cov = int(written.sum())
        gap = ~written
        n_line = 0
        if gap.any():
            # the raster where no cell stands still holds the staff LINES (left of the first cell, right of the last); take out the long level runs
            # there and nothing else -- what else stands in that margin (a brace, the system's opening rule) is read page-wide, and stays
            import cv2
            view = canvas[y0:y1]
            ink_u = ((view == 0) & gap).astype(np.uint8)
            k = max(3, int(round(LINE_RUN_MIN_SPACES * float(s.line_spacing_px))))
            lines = cv2.morphologyEx(ink_u, cv2.MORPH_OPEN, np.ones((1, k), np.uint8))
            lines = cv2.dilate(lines, np.ones((3, 1), np.uint8)).astype(bool) & (ink_u > 0)
            n_line = int(lines.sum())
            view[lines] = 255
        placed += n_cov
        twice += n_twice
        uncovered += n_band - n_cov
        per_staff[int(s.staff_index)] = dict(band_px=n_band, covered_px=n_cov, twice_px=n_twice, uncovered_px=n_band - n_cov, line_ink_removed_px=n_line)
        lines_removed += n_line
    return Assembly(canvas, dict(band_placed_px=placed, band_placed_twice_px=twice, band_uncovered_px=uncovered, line_ink_removed_px=lines_removed,
                                 per_staff=per_staff,
                                 canvas_nbytes=int(canvas.nbytes)))


# ───────────────────────────── 2. carve the barline columns ─────────────────────────────

def carve_columns(canvas: np.ndarray, columns: Sequence[Dict[str, Any]], sp: float) -> List[Dict[str, Any]]:
    """Take each column's rule out of `canvas` (in place); return one dict per column that had one: `box` (x0, y0, x1, y1 page px, half-open),
    `ink_px`, `width_px`, `rows`, plus the column's `system`, `slope`, `intercept`. See the module doc for what is carved."""
    H, W = canvas.shape
    out: List[Dict[str, Any]] = []
    gap = max(1, int(round(CARVE_GAP_BRIDGE_SPACES * sp)))
    run_min = max(3, int(round(CARVE_RUN_MIN_SPACES * sp)))
    max_w = max(3, int(round(CARVE_MAX_WIDTH_SPACES * sp)))
    for col in columns:
        y0, y1 = max(0, int(col["y0"])), min(H, int(col["y1"]) + 1)
        if y1 - y0 < run_min:
            continue
        slope, icpt = float(col["slope"]), float(col["intercept"])
        ys = np.arange(y0, y1)
        xc = np.rint(slope * ys + icpt).astype(np.int64)
        reach = max_w // 2 + CARVE_CORE_PX + 1
        runs = np.zeros(len(ys), np.int64)
        left = np.zeros(len(ys), np.int64)
        has = np.zeros(len(ys), bool)
        for k, (y, x) in enumerate(zip(ys, xc)):
            xa, xb = max(0, x - reach), min(W, x + reach + 1)
            if xb - xa < 3:
                continue
            seg = canvas[y, xa:xb] == 0
            cx = x - xa
            core = np.nonzero(seg[max(0, cx - CARVE_CORE_PX):cx + CARVE_CORE_PX + 1])[0]
            if not core.size:
                continue
            i = int(core[len(core) // 2]) + max(0, cx - CARVE_CORE_PX)
            a = i
            while a > 0 and seg[a - 1]:
                a -= 1
            b = i
            while b + 1 < len(seg) and seg[b + 1]:
                b += 1
            has[k] = True
            left[k] = xa + a
            runs[k] = b - a + 1
        # rows with a core, bridged over short gaps, kept in vertical runs of at least `run_min`
        keep = np.zeros(len(ys), bool)
        i = 0
        n = len(ys)
        while i < n:
            if not has[i]:
                i += 1
                continue
            j = i
            last = i
            while j + 1 < n and (has[j + 1] or (j + 1 - last) <= gap):
                j += 1
                if has[j]:
                    last = j
            if last - i + 1 >= run_min:
                keep[i:last + 1] = True
            i = last + 1
        sel = has & keep & (runs <= max_w)
        if int(sel.sum()) < run_min // 2:
            continue
        width = int(np.median(runs[sel]))
        half = width / 2.0 + CARVE_PAD_PX
        removed = 0
        x_lo, x_hi = W, 0
        y_lo, y_hi = H, 0
        for k in np.nonzero(keep)[0]:
            y, x = int(ys[k]), int(xc[k])
            a, b = max(0, int(np.floor(x - half))), min(W, int(np.ceil(x + half)) + 1)
            seg = canvas[y, a:b]
            n_ink = int((seg == 0).sum())
            if n_ink:
                removed += n_ink
                seg[:] = 255
                x_lo, x_hi = min(x_lo, a), max(x_hi, b)
                y_lo, y_hi = min(y_lo, y), max(y_hi, y + 1)
        if removed:
            out.append(dict(system=int(col["system"]), slope=slope, intercept=icpt, box=(x_lo, y_lo, x_hi, y_hi), ink_px=removed,
                            width_px=width, rows=int(keep.sum())))
    return out


# ───────────────────────────── 3. the detector boxes, in page px ─────────────────────────────

def _dedup(rows: List[List[Any]], first: int, last: int) -> List[List[Any]]:
    out: List[List[Any]] = []
    for r in rows:
        if not any(o[0] == r[0] and all(abs(o[i] - r[i]) <= BOX_DEDUP_PX for i in range(first, last)) and o[last:] == r[last:] for o in out):
            out.append(r)
    return out


def split_inputs(cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]]
                 ) -> Tuple[List[List[Any]], List[List[Any]]]:
    """`(keep_whole, touch_boxes)` for `map_strokes` in PAGE px: each cell's own (`gather._split_keep_whole`, `_split_touch_boxes`, canonical) mapped
    by the cell's box and scale, then twins de-duplicated. A cell with no page box or detections contributes nothing."""
    from . import record as R
    from .gather import _split_keep_whole, _split_touch_boxes
    keep: List[List[Any]] = []
    touch: List[List[Any]] = []
    for c in cells:
        key = local.get(c.staff_index)
        rect, up = getattr(c, "bbox_page_px", None), getattr(c, "upscale_factor", None)
        if key is None or not rect or not up:
            continue
        sub = R.cell(c.page_index, key[0], key[1], c.measure_index)

        def to_page(r: Sequence[float]) -> List[float]:
            return [rect[0] + r[0] / up, rect[1] + r[1] / up, rect[0] + r[2] / up, rect[1] + r[3] / up]
        for r in _split_keep_whole(detections, sub):
            keep.append([int(round(v)) for v in to_page(r[:4])] + list(r[4:]))
        for r in _split_touch_boxes(detections, sub):
            touch.append([r[0]] + [int(round(v)) for v in to_page(r[1:5])] + list(r[5:]))
    return (sorted(_dedup(keep, 0, 4), key=lambda r: (r[:4], len(r))),
            sorted(_dedup(touch, 1, 5), key=lambda r: [str(t) for t in r]))


# ───────────────────────────── 4. the map ─────────────────────────────

@dataclass
class PageMap:
    strokes: List[Any]                                   # stroke_map.Stroke, in PAGE px, ordinal = index
    barlines: List[Dict[str, Any]]
    staff_of: List[Tuple[int, int]]                      # per stroke: (page-wide staff index, local staff index in system) read against
    scale: float
    sp: float
    assembly: Assembly
    masks: List[Any] = field(default_factory=list, repr=False)
    split_refused: Dict[str, int] = field(default_factory=dict)
    seconds: Dict[str, float] = field(default_factory=dict)
    nbytes: Dict[str, int] = field(default_factory=dict)


def page_spacing(pws: Any) -> float:
    return float(np.median([s.line_spacing_px for s in pws.staves]))


def map_page(pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Optional[Dict[str, List[Any]]] = None,
             columns: Optional[Sequence[Dict[str, Any]]] = None, assembly: Optional[Assembly] = None) -> Optional[PageMap]:
    """The page stroke map (module doc). None where the page has no staves or no raster."""
    from . import stroke_map as SM
    from . import barline_columns as BC
    if getattr(getattr(pws, "page", None), "binary", None) is None or not pws.staves:
        return None
    t0 = time.time()
    asm = assembly or assemble(pws, cells)
    t1 = time.time()
    sp = page_spacing(pws)
    cols = list(columns) if columns is not None else BC.fit_columns(pws)
    barlines = carve_columns(asm.canvas, cols, sp)
    t2 = time.time()
    keep, touch = split_inputs(cells, local, detections or {})
    scale = min(1.0, SM.TARGET_SP_PX / float(sp))
    sp_small = SM.TARGET_SP_PX if scale < 1.0 else float(sp)
    raw = pws.page.binary
    staff = PageStaff(SM._reduce_float(raw, scale), pws.staves, scale, sp_small)
    res = SM.map_strokes(asm.canvas, sp, [], raw, keep_whole=keep, touch_boxes=touch, staff_override=staff)
    t3 = time.time()
    if res is None:
        return None
    staff_of = []
    for st in res.strokes:
        s = staff.staff_at(st.box[1] + st.box[3] / 2.0)
        staff_of.append((int(s.staff_index), local.get(s.staff_index, (s.system_index, 0))[1]))
    return PageMap(res.strokes, barlines, staff_of, scale, sp, asm, masks=res.masks, split_refused=res.split_refused,
                   seconds=dict(assemble=round(t1 - t0, 2), carve=round(t2 - t1, 2), map=round(t3 - t2, 2)),
                   nbytes=dict(canvas=int(asm.canvas.nbytes), masks=int(sum(m.nbytes for m, _x, _y in res.masks))))


# ───────────────────────────── 5. file it ─────────────────────────────

def gather_page_strokes(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], detections: Dict[str, List[Any]],
                        columns: Optional[Sequence[Dict[str, Any]]] = None, *, progress: bool = False) -> Optional[PageMap]:
    """ROADMAP 2.260a M2 (flag `OMR_PAGE_STROKES`, default OFF), STAGED GATHER: `Q.PAGE_STROKE`, one row per page stroke (module doc), on the page's
    subject. Reads the cells' erased bands, the page raster and the barline columns; files rows only and decides nothing."""
    if not enabled():
        return None
    from . import record as R
    from .record import Q, READERS
    from .gather import FRAME_PAGE
    from . import run_meter
    pm = map_page(pws, cells, local, detections, columns)
    if pm is None:
        return None
    t = time.time()
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    n = 0
    for i, (st, (sidx, lidx)) in enumerate(zip(pm.strokes, pm.staff_of)):
        x, y, w, h = st.box
        opt: Dict[str, Any] = {}
        if st.sagitta_sp is not None:
            opt["sagitta_spaces"] = st.sagitta_sp
        if st.hole_share is not None:
            opt["hole_share"] = st.hole_share
        if st.kind != "blob":
            opt["profile_sixteenths"] = st.profile
        if st.joined_to:
            opt["joined_to"] = [[j, how] for j, how in st.joined_to]
        log.observe(sub, Q.PAGE_STROKE, st.kind, reader=READERS.CV_PAGE_STROKES, frame=FRAME_PAGE, ordinal=i,
                    stroke_box=[x, y, w, h], bbox_page_px=[float(x), float(y), float(x + w), float(y + h)],
                    length_spaces=st.length_sp, angle_deg=st.angle_deg, thickness_spaces=st.thickness_sp,
                    thickness_spread_spaces=st.thickness_spread_sp, fill=st.fill,
                    ends=[st.ends[0][0], st.ends[0][1], st.ends[1][0], st.ends[1][1]], end_steps_from_top=list(st.end_steps),
                    touches=[[j, ct] for j, ct in st.touches], component=st.component, staff_space_local_px=st.staff_space_local,
                    staff=[local.get(sidx, (0, 0))[0], lidx], **opt)
        n += 1
    for b in pm.barlines:
        x0, y0, x1, y1 = b["box"]
        log.observe(sub, Q.PAGE_STROKE, "barline", reader=READERS.CV_PAGE_STROKES, frame=FRAME_PAGE, ordinal=n,
                    stroke_box=[x0, y0, x1 - x0, y1 - y0], bbox_page_px=[float(x0), float(y0), float(x1), float(y1)],
                    system=b["system"], slope=b["slope"], intercept=b["intercept"], ink_px=b["ink_px"], width_px=b["width_px"], rows=b["rows"])
        n += 1
    pm.seconds["file"] = round(time.time() - t, 2)
    if progress:
        print("  gather page strokes p%s: %d strokes + %d barline rules; %s s; canvas %.0f MB, masks %.0f MB; uncovered band %d px, twice %d px; peak rss %.1f GB"
              % (p, len(pm.strokes), len(pm.barlines), pm.seconds, pm.nbytes["canvas"] / 1e6, pm.nbytes["masks"] / 1e6,
                 pm.assembly.stats["band_uncovered_px"], pm.assembly.stats["band_placed_twice_px"], run_meter.peak_rss_bytes() / 1e9))
    return pm
