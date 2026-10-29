"""ROADMAP 2.195 -- the shared ink map, STEP 1: every stroke of a cell, measured ONCE (`Q.STROKE`).

STAGED GATHER, PURE: this module imports numpy and cv2 and nothing from the pipeline. `gather.gather_stroke_map` is the only
caller; it files what is returned here as `Q.STROKE` rows and decides nothing (plan `docs/plan-2026-10-22-shared-ink-map.md`
§2.1, §5 step 1). Nothing reads the rows yet (the `Q.INK` discipline: a producer and its first consumer in one change make the
reach measurement circular), so with `OMR_STROKE_MAP` on the exported file is byte-identical to flag off.

WHAT A STROKE IS. One piece of ink in one cell, found on the staff-ERASED raster (`cell.image_no_staff`, the one the CV readers
read -- the detector keeps reading the original). Not a connected component (Litolff MERGES a head, an accidental and a beam into
one; Breitkopf SHATTERS a rest into three): run analysis separates it, in this order, each ink pixel claimed by the first kind
that fits it --

  vertical    a run-stack at least `V_MIN_SPACES` tall (stem, barline, accidental stem; a vertical opening)
  horizontal  a run-stack at least `H_MIN_SPACES` long and thin (beam, ledger rung, rest bar; a horizontal opening, then the
              piece must be long against its thickness, else it is a head's lens and goes back to the remainder)
  curve       what is left, long and thin (tie, slur, hairpin line, flag hook)
  blob        what is left, otherwise (head, rest body, accidental bowl, dot, letter)

The two openings may SHARE the pixels where a stem crosses a beam (a crossing belongs to both strokes and is reported as
contact); the remainder is cut one pixel away from them so a head beside a stem does not keep a sliver of it.

THE SAME FINDERS' POPULATIONS, NOT A NEW DETECTOR: the vertical opening is `detect_stems`' first step, the horizontal one
`detect_beams`', the components `_ink_components`'. The cell is first reduced to `TARGET_SP_PX` pixels per staff space (a canonical
cell is 90-100 px per space; the kernels cost O(kernel) per pixel), which makes every field scale-free.

THE STAFF IS MEASURED LOCALLY (CLAUDE §5: a scanned staff tilts and ~1 px decides a near-boundary pitch). One class,
`LocalStaff.lines_at(x)`, finds the five lines in windows on the RAW raster and interpolates; a stroke's two ends are given in staff
steps from the lines AT THEIR OWN x. Where it cannot place all five it says so (`staff_local` false) and uses the nominal lines.

WHAT IS NOT FILED. A piece under `MIN_AREA_SP2` staff-space-squared is counted (`n_below_floor`), not filed: each of the ~30 specks a
Breitkopf cell shatters into would cost more bytes than all other quantities together. 0.05 sits under an augmentation dot (~0.12).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

TARGET_SP_PX = 16.0
#: A reduced pixel is ink when this much (of 255) of its source was. A tie's end / ledger rung is ~2 px thick at this scale.
COVER_THRESHOLD = 96
V_MIN_SPACES = 1.5
H_MIN_SPACES = 1.0
#: length^2 / area of a horizontal piece: beam 5-30, rung 8+, filled head's lens 1.3-1.8.
H_MIN_ASPECT = 2.5
CURVE_MIN_SPACES = 1.5
CURVE_MAX_THICK_SPACES = 0.5
CURVE_MIN_ASPECT = 2.0
MIN_AREA_SP2 = 0.05
PROFILE_SAMPLES = 12
ANCHOR_STRIDE_SPACES = 3.0
ANCHOR_HALF_WINDOW_SPACES = 1.5
LINE_SEARCH_SPACES = 0.4
LINE_MIN_INK = 0.5
#: ROADMAP 2.202b. A horizontal / curve stroke's thickness is read on the UNERASED raster (CLAUDE §7: a thickness must not be read off an erased
#: line). `tools/omr/staff_line_removal.py` erases a whole vertical run through a line row when the run it WALKS (bounded at `cap + 2` rows each side)
#: is <= its crossing cut (0.45 sp): a beam 0.6 sp thick lying on a line is walked for ~37 rows, looks like 44 <= 45, and is erased from the line to
#: 37 rows below it, leaving a 0.19 sp sliver (Litolff p16, the 2.202 tile). The ink the eraser took is `raw & ~erased`; the stroke's own pixels plus
#: the erased pixels CONTIGUOUS to them in a column are what was printed there (the eraser only ever takes line rows and the run it walked with them,
#: never a neighbour's ink). False: the 2.202 reading (erased raster only); the control test turns it off to prove the fix is what moves the number.
THICKNESS_FROM_UNERASED = True

KINDS = ("vertical", "horizontal", "curve", "blob")


@dataclass
class Stroke:
    kind: str
    box: Tuple[int, int, int, int]            # x, y, w, h -- canonical cell px (the Q.STEM spelling)
    area_sp2: float
    length_sp: float
    angle_deg: float                          # principal axis: 0 horizontal, 90 vertical, counter-clockwise on the page
    thickness_sp: float                       # median run across the axis, slope-corrected
    thickness_spread_sp: float                # inter-quartile range of the same
    fill: float                               # area / box area
    sagitta_sp: Optional[float]               # centre-line bow (None for a blob)
    hole_share: Optional[float]               # blob only: enclosed paper / (ink + enclosed paper)
    ends: Tuple[Tuple[int, int], Tuple[int, int]]   # extreme pixels along the axis, canonical (x, y)
    profile: List[int]                        # thickness along the axis, sixteenths of a space
    component: int = -1
    component_n_strokes: int = 1
    touches: List[Tuple[int, float]] = field(default_factory=list)   # (other stroke's ordinal in the cell, contact in spaces)
    lines_left: Optional[List[int]] = None    # the five staff-line rows at the box's left / right x, canonical px
    lines_right: Optional[List[int]] = None
    staff_space_local: Optional[float] = None  # canonical px per space at the stroke's centre
    end_steps: Optional[Tuple[float, float]] = None   # ends in steps from the TOP line (0) to the bottom (8), local lines


class LocalStaff:
    """The five staff lines at any x of one cell, measured on the RAW reduced raster (reduced-frame rows)."""

    def __init__(self, raw_small: Optional[np.ndarray], nominal_small: Sequence[float], sp_small: float):
        self.sp = float(sp_small)
        self.nominal = [float(y) for y in nominal_small]
        self.local = False
        self._xs: List[float] = []
        self._rows: List[List[float]] = []
        if raw_small is None or len(self.nominal) != 5 or sp_small <= 0 or raw_small.ndim != 2:
            return
        h, w = raw_small.shape
        half = max(2, int(round(ANCHOR_HALF_WINDOW_SPACES * sp_small)))
        stride = max(2, int(round(ANCHOR_STRIDE_SPACES * sp_small)))
        search = max(1, int(round(LINE_SEARCH_SPACES * sp_small)))
        prev = list(self.nominal)
        for cx in range(half, max(half + 1, w - half + stride), stride):
            cx = min(cx, w - 1)
            a, b = max(0, cx - half), min(w, cx + half + 1)
            if b - a < 3:
                continue
            prof = raw_small[:, a:b].mean(axis=1)
            rows: List[float] = []
            ok = True
            for y in prev:
                lo, hi = max(0, int(round(y)) - search), min(h, int(round(y)) + search + 1)
                if hi - lo < 2:
                    ok = False
                    break
                seg = prof[lo:hi]
                peak = float(seg.max())
                if peak < LINE_MIN_INK:
                    ok = False
                    break
                band = np.nonzero(seg >= 0.5 * peak)[0]
                wts = seg[band]
                rows.append(float(lo + (band * wts).sum() / wts.sum()))
            if not ok or any(rows[i + 1] - rows[i] <= 0 for i in range(4)):
                continue
            self._xs.append(float(cx))
            self._rows.append(rows)
            prev = rows
        self.local = bool(self._xs)

    def lines_at(self, x: float) -> List[float]:
        if not self._xs:
            return list(self.nominal)
        xs = self._xs
        if x <= xs[0]:
            return list(self._rows[0])
        if x >= xs[-1]:
            return list(self._rows[-1])
        j = int(np.searchsorted(xs, x))
        t = (x - xs[j - 1]) / (xs[j] - xs[j - 1])
        return [self._rows[j - 1][i] * (1 - t) + self._rows[j][i] * t for i in range(5)]


def _reduce(img: np.ndarray, scale: float) -> np.ndarray:
    import cv2
    ink = (img == 0).astype(np.uint8) * 255
    if scale >= 1.0:
        return ink >= COVER_THRESHOLD
    return cv2.resize(ink, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) >= COVER_THRESHOLD


def _reduce_float(img: np.ndarray, scale: float) -> np.ndarray:
    import cv2
    ink = (img == 0).astype(np.float32)
    return ink if scale >= 1.0 else cv2.resize(ink, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)


def _components(mask: np.ndarray, connectivity: int = 8):
    import cv2
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=connectivity)
    return n, lab, stats


def _hole_share(m: np.ndarray) -> float:
    """Enclosed paper of a blob's mask over (ink + enclosed paper)."""
    import cv2
    h, w = m.shape
    pad = np.zeros((h + 2, w + 2), np.uint8)
    pad[1:-1, 1:-1] = m
    ff = (1 - pad).astype(np.uint8)
    cv2.floodFill(ff, np.zeros((h + 4, w + 4), np.uint8), (0, 0), 2)
    holes = int((ff == 1).sum())
    area = int(m.sum())
    return holes / float(area + holes) if area + holes else 0.0


def _centres(m: np.ndarray, idx: np.ndarray, axis: int) -> np.ndarray:
    mf = m.astype(np.float64)
    if axis == 0:
        rows = np.arange(m.shape[0], dtype=np.float64)[:, None]
        return (mf[:, idx] * rows).sum(axis=0) / mf[:, idx].sum(axis=0)
    cols = np.arange(m.shape[1], dtype=np.float64)[None, :]
    return (mf[idx, :] * cols).sum(axis=1) / mf[idx, :].sum(axis=1)


def _measure(m: np.ndarray, x0: int, y0: int) -> dict:
    ys, xs = np.nonzero(m)
    cx, cy = float(xs.mean()), float(ys.mean())
    dx, dy = xs - cx, ys - cy
    theta = 0.5 * math.atan2(2 * float((dx * dy).mean()), float((dx * dx).mean()) - float((dy * dy).mean()))
    c, s = math.cos(theta), math.sin(theta)
    t = dx * c + dy * s
    i0, i1 = int(np.argmin(t)), int(np.argmax(t))
    if abs(c) >= abs(s):
        counts, axis, factor = m.sum(axis=0), 0, abs(c)
    else:
        counts, axis, factor = m.sum(axis=1), 1, abs(s)
    idx = np.nonzero(counts)[0]
    runs = counts[idx].astype(np.float64)
    centres = _centres(m, idx, axis)
    sag = None
    if idx.size >= 3 and idx[-1] > idx[0]:
        along = idx.astype(np.float64)
        chord = centres[0] + (along - along[0]) * (centres[-1] - centres[0]) / (along[-1] - along[0])
        sag = float(np.abs(centres - chord).max())
    sel = np.linspace(0, runs.size - 1, PROFILE_SAMPLES).round().astype(int)
    return dict(area=int(xs.size), theta=theta, length=float(t[i1] - t[i0]) + 1.0,
                thick=float(np.median(runs)) * factor,
                spread=float(np.percentile(runs, 75) - np.percentile(runs, 25)) * factor, sag=sag,
                profile=[int(runs[i]) for i in sel],
                end0=(x0 + int(xs[i0]), y0 + int(ys[i0])), end1=(x0 + int(xs[i1]), y0 + int(ys[i1])))


@dataclass
class CellStrokes:
    strokes: List[Stroke]
    n_below_floor: int
    scale: float
    sp_canonical: float
    staff_local: bool
    #: ROADMAP 2.198: each stroke's mask in the REDUCED frame, parallel to `strokes` -- (mask, x0, y0). Never filed; it is what lets
    #: `strokes_in_box` say how much of a stroke's ink lies inside a detector box.
    masks: List[Tuple[np.ndarray, int, int]] = field(default_factory=list, repr=False, compare=False)


#: A box COVERS a stroke when at least this share of the stroke's ink lies inside the box. Not tuned: it is the register's one cut
#: (`claims.INSIDE_SHARE_MIN`, 2.177: "a mark's own piece is wholly inside, ~1.0; a neighbour shares a sliver"), and the measured
#: distribution of the share (benchmarks/shared-ink-map-2026-10/FINDINGS.md 2.198 section) is what says it sits in a gap.
COVER_SHARE_MIN = 0.5


def strokes_in_box(res: "CellStrokes", box: Sequence[float]) -> List[Tuple[int, float]]:
    """ROADMAP 2.198: `[(stroke ordinal, share)]` for every stroke of the cell with any ink inside `box` = (x0, y0, x1, y1) in CANONICAL cell
    px (the frame of `Stroke.box` and of the detector's boxes); `share` = the stroke's ink inside the box / the stroke's ink, in [0, 1].
    Pure; ordered by ordinal. A caller applies `COVER_SHARE_MIN` (covered) and keeps the rest as partial."""
    out: List[Tuple[int, float]] = []
    if not res.masks:
        return out
    s = res.scale
    bx0, by0, bx1, by1 = (float(v) * s for v in box)
    for i, (m, x0, y0) in enumerate(res.masks):
        h, w = m.shape
        lx0, ly0 = max(0, int(round(bx0)) - x0), max(0, int(round(by0)) - y0)
        lx1, ly1 = min(w, int(round(bx1)) - x0), min(h, int(round(by1)) - y0)
        if lx1 <= lx0 or ly1 <= ly0:
            continue
        total = int(m.sum())
        if total <= 0:
            continue
        inside = int(m[ly0:ly1, lx0:lx1].sum())
        if inside:
            out.append((i, round(inside / float(total), 3)))
    return out


def _restored_thickness(m: np.ndarray, x0: int, y0: int, scale: float, erased: np.ndarray, raw: np.ndarray, sp_canonical: float,
                        factor: float) -> Optional[float]:
    """ROADMAP 2.202b: the median column run of one horizontal / curve stroke with the ink the staff-line erase took out of its columns put back, in
    REDUCED px (the unit of `_measure`'s `thick`) times the axis `factor`; None when no column of the stroke touches erased ink (the erased reading IS the
    printed one). Done at CANONICAL resolution (the 16 px/sp reduction would let a line 0.06 sp clear of a beam join it).

    `erased` / `raw` are the canonical rasters (0 = ink). Per column: a run of (the stroke's own pixels + pixels the erase removed) that contains a pixel
    of the stroke. The eraser only ever removes line rows and the run it walked with them, so the added pixels are never a neighbour's ink."""
    import cv2
    H, W = erased.shape
    inv = 1.0 / scale
    h, w = m.shape
    cx0, cy0 = int(round(x0 * inv)), int(round(y0 * inv))
    cw, ch = max(1, int(round(w * inv))), max(1, int(round(h * inv)))
    pad = int(math.ceil(0.5 * sp_canonical))
    ya, yb = max(0, cy0 - pad), min(H, cy0 + ch + pad)
    xa, xb = max(0, cx0), min(W, cx0 + cw)
    if yb <= ya or xb <= xa:
        return None
    up = cv2.resize(m.astype(np.uint8), (cw, ch), interpolation=cv2.INTER_NEAREST).astype(bool)
    S = np.zeros((yb - ya, xb - xa), bool)
    ry0, rx0 = cy0 - ya, max(0, cx0) - cx0
    sub = up[:, rx0:rx0 + (xb - xa)]
    hh = min(sub.shape[0], S.shape[0] - ry0)
    if hh <= 0:
        return None
    S[ry0:ry0 + hh, :sub.shape[1]] = sub[:hh]
    ink_e = erased[ya:yb, xa:xb] == 0
    E = (raw[ya:yb, xa:xb] == 0) & ~ink_e
    # the stroke's footprint is one reduced pixel coarse: its erased ink is the ink within one reduced pixel (`inv` canonical px) of it, up and down
    k = max(1, int(round(inv)))
    foot = cv2.dilate(S.astype(np.uint8), np.ones((2 * k + 1, 1), np.uint8)).astype(bool)
    S = foot & ink_e
    if not E.any() or not S.any():
        return None
    T = S | E
    start = T.copy()
    start[1:] &= ~T[:-1]
    seg = np.cumsum(start, axis=0) * T
    nseg = int(seg.max()) + 1
    key = seg + np.arange(T.shape[1])[None, :] * nseg
    has = np.unique(key[S])
    G = np.isin(key, has) & T
    cols = foot.any(axis=0)
    if not cols.any() or not (G & E).any():
        return None          # no column of the stroke touches ink the erase took: the erased reading IS the printed one, keep it exactly
    return float(np.median(G.sum(axis=0)[cols])) * scale * factor


def map_strokes(erased: np.ndarray, sp_canonical: float, nominal_lines_canonical: Sequence[float],
                raw: Optional[np.ndarray] = None) -> Optional[CellStrokes]:
    """Every stroke of one cell. `erased` = `cell.image_no_staff` (0 = ink); `raw` = `cell.binary` (0 = ink) for the local staff.
    None for a cell that cannot be reduced. Deterministic: strokes ordered by (x, y, kind)."""
    import cv2
    if erased is None or erased.ndim != 2 or sp_canonical <= 0:
        return None
    scale = min(1.0, TARGET_SP_PX / float(sp_canonical))
    sp = TARGET_SP_PX if scale < 1.0 else float(sp_canonical)
    inv = 1.0 / scale
    ink = _reduce(erased, scale)
    if not ink.any():
        return CellStrokes([], 0, scale, float(sp_canonical), False)
    u8 = ink.astype(np.uint8)
    kh, kw = max(3, int(round(V_MIN_SPACES * sp))), max(3, int(round(H_MIN_SPACES * sp)))
    V = cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((kh, 1), np.uint8))
    H0 = cv2.morphologyEx(u8, cv2.MORPH_OPEN, np.ones((1, kw), np.uint8))
    claimed = V.astype(bool)
    _n, ink_lab, _ = _components(ink)

    pieces: List[Tuple[str, np.ndarray, int, int]] = []
    nv, vlab, vst = _components(V)
    for i in range(1, nv):
        x, y, w, h, _a = (int(v) for v in vst[i])
        pieces.append(("vertical", vlab[y:y + h, x:x + w] == i, x, y))
    nh, hlab, hst = _components(H0)
    for i in range(1, nh):
        x, y, w, h, a = (int(v) for v in hst[i])
        longest = max(w, h)
        if a > 0 and (longest * longest) / float(a) >= H_MIN_ASPECT:
            pieces.append(("horizontal", hlab[y:y + h, x:x + w] == i, x, y))
            claimed |= (hlab == i)
    rem = ink & ~cv2.dilate(claimed.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    nr, rlab, rst = _components(rem)
    floor_px = MIN_AREA_SP2 * sp * sp
    below = 0
    for i in range(1, nr):
        x, y, w, h, a = (int(v) for v in rst[i])
        if a < floor_px:
            below += 1
            continue
        longest = max(w, h)
        thick_mean = a / float(longest)
        curve = (longest >= CURVE_MIN_SPACES * sp and thick_mean <= CURVE_MAX_THICK_SPACES * sp
                 and longest / max(1.0, thick_mean) >= CURVE_MIN_ASPECT)
        pieces.append(("curve" if curve else "blob", rlab[y:y + h, x:x + w] == i, x, y))

    staff = LocalStaff(_reduce_float(raw, scale) if raw is not None else None,
                       [y * scale for y in nominal_lines_canonical], sp)
    restore = THICKNESS_FROM_UNERASED and raw is not None and raw.ndim == 2 and raw.shape == erased.shape

    built: List[Tuple[Tuple[int, int, int, int], Stroke, np.ndarray, int, int]] = []
    for kind, m, x0, y0 in pieces:
        h, w = m.shape
        mm = _measure(m, x0, y0)
        if restore and kind in ("horizontal", "curve") and abs(math.cos(mm["theta"])) >= abs(math.sin(mm["theta"])):
            rt = _restored_thickness(m, x0, y0, scale, erased, raw, float(sp_canonical), abs(math.cos(mm["theta"])))
            if rt is not None:
                mm["thick"] = max(mm["thick"], rt)
        ang = -math.degrees(mm["theta"])
        ang = ang + 180.0 if ang <= -90.0 else (ang - 180.0 if ang > 90.0 else ang)
        mid = staff.lines_at(x0 + w / 2.0)
        steps = []
        for (ex, ey) in (mm["end0"], mm["end1"]):
            ln = staff.lines_at(ex)
            half = (ln[4] - ln[0]) / 8.0
            steps.append(round((ey - ln[0]) / half, 2) if half > 0 else 0.0)
        ys_, xs_ = np.nonzero(m)
        box = (int(round(x0 * inv)), int(round(y0 * inv)), int(round(w * inv)), int(round(h * inv)))
        e0, e1 = mm["end0"], mm["end1"]
        st = Stroke(
            kind=kind, box=box, area_sp2=round(mm["area"] / (sp * sp), 3), length_sp=round(mm["length"] / sp, 3),
            angle_deg=round(ang, 1), thickness_sp=round(mm["thick"] / sp, 3),
            thickness_spread_sp=round(mm["spread"] / sp, 3), fill=round(mm["area"] / float(w * h), 3),
            sagitta_sp=None if kind == "blob" or mm["sag"] is None else round(mm["sag"] / sp, 3),
            hole_share=round(_hole_share(m), 3) if kind == "blob" else None,
            ends=((int(round(e0[0] * inv)), int(round(e0[1] * inv))), (int(round(e1[0] * inv)), int(round(e1[1] * inv)))),
            profile=mm["profile"], component=int(ink_lab[y0 + int(ys_[0]), x0 + int(xs_[0])]),
            lines_left=[int(round(v * inv)) for v in staff.lines_at(x0)],
            lines_right=[int(round(v * inv)) for v in staff.lines_at(x0 + w)],
            staff_space_local=round((mid[4] - mid[0]) / 4.0 * inv, 2), end_steps=(steps[0], steps[1]))
        built.append((box, st, m, x0, y0))

    built.sort(key=lambda r: (r[0][0], r[0][1], KINDS.index(r[1].kind)))
    k3 = np.ones((3, 3), np.uint8)       # contact = within 2 px: the remainder was cut 1 px clear of the openings
    n = len(built)
    for i in range(n):
        _b, si, mi, xi, yi = built[i]
        hi_, wi_ = mi.shape
        for j in range(i + 1, n):
            _b2, sj, mj, xj, yj = built[j]
            hj, wj = mj.shape
            if xi + wi_ + 1 < xj or xj + wj + 1 < xi or yi + hi_ + 1 < yj or yj + hj + 1 < yi:
                continue
            gx0, gy0 = min(xi, xj) - 1, min(yi, yj) - 1
            gx1, gy1 = max(xi + wi_, xj + wj) + 1, max(yi + hi_, yj + hj) + 1
            A = np.zeros((gy1 - gy0, gx1 - gx0), np.uint8)
            B = np.zeros_like(A)
            A[yi - gy0:yi - gy0 + hi_, xi - gx0:xi - gx0 + wi_] = mi
            B[yj - gy0:yj - gy0 + hj, xj - gx0:xj - gx0 + wj] = mj
            ca = int((A.astype(bool) & cv2.dilate(B, k3, iterations=2).astype(bool)).sum())
            cb = int((B.astype(bool) & cv2.dilate(A, k3, iterations=2).astype(bool)).sum())
            if ca == 0 and cb == 0:
                continue
            contact = round((min(ca, cb) or max(ca, cb)) / sp, 2)
            si.touches.append((j, contact))
            sj.touches.append((i, contact))
    out = [r[1] for r in built]
    per: Dict[int, int] = {}
    for s in out:
        per[s.component] = per.get(s.component, 0) + 1
    for s in out:
        s.component_n_strokes = per[s.component]
    return CellStrokes(out, below, scale, float(sp_canonical), staff.local, masks=[(r[2], r[3], r[4]) for r in built])


#: ROADMAP 2.206d (flag `OMR_STEM_TIP_TRUE_EDGE`, default ON since 2026-10-27). The stem finder's box can be a thin core of a thick stem (Brahms p14: 4 px
#: of a 25 px stem); the stroke map holds the stem's whole width. Measured over the rows this far from either end of the stem (L7: head and
#: stem fuse up to 1.2 sp beside a head) and refused where the stroke is wider than `STEM_TRUE_WIDTH_MAX_SPACES` (Litolff's widest plain stem
#: 0.43 sp, Brahms 0.37 at p90; a fused or doubled stroke is not a stem's width).
STEM_TRUE_END_MARGIN_SPACES = 1.5
STEM_TRUE_WIDTH_MAX_SPACES = 0.7


def stem_true_edges(res: "CellStrokes", stem_box: Sequence[float]) -> Optional[Tuple[float, float]]:
    """ROADMAP 2.206d: `(x0, x1)` in canonical cell px of the stroke the finder's stem box lies on, measured mid-stem; `None` where no stroke
    carries the box's centre at the mid rows or the measured width is not a stem's. The finder says WHICH stroke; the stroke says how wide."""
    if res is None or isinstance(res, str) or not getattr(res, "masks", None):
        return None
    x, y, w, h = (float(v) for v in stem_box)
    sp = float(res.sp_canonical)
    s = float(res.scale)
    margin = STEM_TRUE_END_MARGIN_SPACES * sp
    ya, yb = y + margin, y + h - margin
    if yb - ya < 0.5 * sp:                      # a short stem: the middle half
        ya, yb = y + 0.25 * h, y + 0.75 * h
    cx = (x + w / 2.0) * s
    best = None
    for m, mx0, my0 in res.masks:
        mh, mw = m.shape
        r0, r1 = max(0, int(round(ya * s)) - my0), min(mh, int(round(yb * s)) - my0)
        c = int(round(cx)) - mx0
        if r1 <= r0 or not (0 <= c < mw):
            continue
        hits = int(m[r0:r1, c].sum())
        if hits and (best is None or hits > best[0]):
            best = (hits, m, mx0, r0, r1)
    if best is None:
        return None
    _, m, mx0, r0, r1 = best
    lefts, rights = [], []
    for r in range(r0, r1):
        row = m[r]
        c = int(round(cx)) - mx0
        if not row[c]:
            nz = np.flatnonzero(row)
            if nz.size == 0:
                continue
            c = int(nz[np.argmin(np.abs(nz - c))])
        a = c
        while a > 0 and row[a - 1]:
            a -= 1
        b = c
        while b < row.size - 1 and row[b + 1]:
            b += 1
        lefts.append(a); rights.append(b + 1)
    if len(lefts) < 3:
        return None
    x0, x1 = (mx0 + float(np.median(lefts))) / s, (mx0 + float(np.median(rights))) / s
    if x1 - x0 > STEM_TRUE_WIDTH_MAX_SPACES * sp:
        return None
    return x0, x1


# ─────────────────────────────────────────────────────────────────────────────
# ROADMAP 2.220, step 6 of the shared ink map: ONE head's own ink, its fill read on it (`Q.HEAD_INK`, flag `OMR_FILL_FROM_STROKES`)
# ─────────────────────────────────────────────────────────────────────────────
#
# WHY (benchmarks/ink-map-fill-2026-10/FINDINGS.md): `map_strokes` claims verticals and horizontals before it looks for blobs, so a hollow
# head's ring falls apart into lunes and rims and `Stroke.hole_share` is 0.0 on every written half. `head_mask` puts ONE head back together
# from the strokes a detector head box covers, minus the strokes another mark owns (a stem: `vertical`; a beam or a ledger rung: a
# `horizontal` at least `HEAD_OWNED_HORIZONTAL_SPACES` long; any stroke an accidental / key / flag / dynamic box of the same cell covers),
# at CANONICAL resolution, with the staff-line pixels the eraser took put back only inside the head's own convex hull (the eraser's cut
# through a ring tangent to a line is mended, the line outside is left alone). Every number is then measured on that one mask.
# PURE: numpy + cv2, nothing from the pipeline; `gather.gather_head_ink` is the only caller.

#: A `horizontal` stroke at least this long is a beam or a ledger rung, not a head's rim (plan 2026-10-28 §2: "longer than about 2 sp").
HEAD_OWNED_HORIZONTAL_SPACES = 2.0
#: ... and nowhere as thick as this (a beam is ~0.5 sp, a rung ~0.15; a head in the horizontal opening ~0.65-0.7; the thickest sample of the profile): a long `horizontal`
#: that is somewhere as thick as a head is a head MERGED with its neighbour (Litolff merges a head with an accidental's bar or a beam
#: end); it is kept, and its extent then says `not_one_head`.
HEAD_OWNED_HORIZONTAL_MAX_THICK_SPACES = 0.6
#: The canonical crop around the kept pieces, each side. It only bounds the crop: the mask is the pieces' own ink, so the extent does not
#: depend on it (fix D, 2.115's lesson: a centre that moves with the window is not a measurement; pinned by the window-stability test).
HEAD_WINDOW_MARGIN_SPACES = 0.3
#: An enclosed paper component smaller than this is a scan speck inside a filled head, not a hole (sp^2; ~30 canonical px at 100 px/sp).
HEAD_HOLE_MIN_SP2 = 0.003
#: Fix A (DECISIONS 2026-10-28): ONE head's ink is at most this wide / tall. A printed notehead is ~1.3-1.4 sp wide and ~1 sp tall
#: (benchmarks/omr-notehead-width-2026-09). An ink extent past these holds more than one head's ink (a sharp, a flag, a dynamic's letters,
#: a chord): `not_one_head`. Filed with its margin (`size_margin_sp`); the consumer (milestone 2) keeps its own cut.
HEAD_INK_MAX_WIDTH_SPACES = 1.75
HEAD_INK_MAX_HEIGHT_SPACES = 1.4
#: ... and at least this, both ways (a fragment of a letter, or a rim alone, is not a head).
HEAD_INK_MIN_SPACES = 0.6
#: Fix C (2.129/2.132): a stacked pair makes an ink column two heads tall over a head-sized box. The mask is clipped to the box's own rows
#: widened by this, and the clip filed (`stack_clipped`), BEFORE the extent is judged. Never applied to a box itself taller than one head.
HEAD_STACK_CLIP_SPACES = 0.15
#: 2.148's cuts on the slit (`rhythm.HEAD_INTERIOR_WHITE_HOLLOW_MIN` / `_FILLED_MAX`), restated only so the producer's own reading files a
#: margin; the consumer keeps its own cut (plan 10-22 §4: the measurement is shared, the cut stays per consumer).
HEAD_SLIT_HOLLOW_MIN = 0.18
HEAD_SLIT_FILLED_MAX = 0.06
#: Detector classes whose box, covering a stroke, says that stroke is not a head's ink (fix A: "holds a sharp, a flag or an ff").
FOREIGN_PREFIXES = ("accidental", "key", "flag", "dynamic")
FOREIGN_EXCLUDE = ("dynamiccrescendohairpin", "dynamicdiminuendohairpin", "keyboard")


def is_foreign_class(name: Optional[str]) -> bool:
    n = str(name or "").lower()
    return n.startswith(FOREIGN_PREFIXES) and not n.startswith(FOREIGN_EXCLUDE)


def _upsample_into(dst: np.ndarray, m: np.ndarray, x0: int, y0: int, scale: float, wx0: int, wy0: int) -> None:
    """OR the reduced-frame mask `m` (origin x0, y0) into `dst`, a canonical window whose origin is (wx0, wy0)."""
    import cv2
    inv = 1.0 / scale
    h, w = m.shape
    cx0, cy0 = int(round(x0 * inv)), int(round(y0 * inv))
    cw, ch = max(1, int(round(w * inv))), max(1, int(round(h * inv)))
    up = cv2.resize(m.astype(np.uint8), (cw, ch), interpolation=cv2.INTER_NEAREST).astype(bool)
    H, W = dst.shape
    ax0, ay0 = cx0 - wx0, cy0 - wy0
    sx0, sy0 = max(0, -ax0), max(0, -ay0)
    dx0, dy0 = max(0, ax0), max(0, ay0)
    dx1, dy1 = min(W, ax0 + cw), min(H, ay0 + ch)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    dst[dy0:dy1, dx0:dx1] |= up[sy0:sy0 + (dy1 - dy0), sx0:sx0 + (dx1 - dx0)]


def mask_holes(M: np.ndarray, sp: float) -> Tuple[float, int, float]:
    """`(hole_share, n_holes, hole_sp2)` of a boolean mask after a 1-px close: enclosed paper components of at least `HEAD_HOLE_MIN_SP2`,
    over (ink + those holes). The mask is padded with paper, so a line crossing the crop never encloses the paper beside it."""
    import cv2
    if M is None or not M.any():
        return 0.0, 0, 0.0
    pad = np.zeros((M.shape[0] + 2, M.shape[1] + 2), np.uint8)
    pad[1:-1, 1:-1] = M
    pad = cv2.morphologyEx(pad, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    pad[0, :] = pad[-1, :] = 0
    pad[:, 0] = pad[:, -1] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats((1 - pad).astype(np.uint8), connectivity=4)
    outside = int(lab[0, 0])
    floor = HEAD_HOLE_MIN_SP2 * sp * sp
    holes = [int(st[i, cv2.CC_STAT_AREA]) for i in range(1, n) if i != outside and st[i, cv2.CC_STAT_AREA] >= floor]
    ink = int(pad.sum())
    tot = float(sum(holes))
    return (round(tot / (ink + tot), 4) if ink + tot else 0.0), len(holes), round(tot / (sp * sp), 4)


def head_mask(res: "CellStrokes", erased: np.ndarray, raw: Optional[np.ndarray], box: Sequence[float],
              foreign: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """ROADMAP 2.220: ONE head's own ink under the detector head box `box` = (x0, y0, x1, y1) (canonical cell px), from the cell's stroke
    map `res`. `erased` = `cell.image_no_staff`, `raw` = `cell.binary` (0 = ink, canonical). `foreign` = {stroke ordinal: class} for the
    strokes an accidental / key / flag / dynamic box of the same cell covers (fix A).

    Always returns `pieces` (kept stroke ordinals), `dropped` ([ordinal, why]), `why` and `not_one_head`; when a mask was built also `mask`
    (bool, the crop), `origin` (crop x0, y0), `extent` [x0, y0, x1, y1] canonical, `extent_sp` [w, h], `centre` (the extent's midpoint --
    fix D: never a centroid), `hole_share`, `n_holes`, `hole_sp2`, `line_px_restored`, `stem_cut` ('left' / 'right' / None),
    `stack_clipped`, `size_margin_sp`. `why`: None (a mask of one head), 'not_one_head', 'no_head_ink', 'no_stroke_map'."""
    import cv2
    out: Dict[str, Any] = {"pieces": [], "dropped": [], "why": None, "not_one_head": None}
    if res is None or isinstance(res, str) or not getattr(res, "masks", None) or erased is None:
        out["why"] = "no_stroke_map"
        return out
    foreign = dict(foreign or {})
    sp = float(res.sp_canonical)
    got = strokes_in_box(res, box)
    covered = [i for i, sh in got if sh >= COVER_SHARE_MIN]
    partial = [i for i, sh in got if sh < COVER_SHARE_MIN]
    kept: List[int] = []
    owned: List[int] = []
    stems: List[int] = []

    def _owned_by(i: int) -> Optional[str]:
        st = res.strokes[i]
        if st.kind == "vertical":
            return "stem_or_vertical"
        if (st.kind == "horizontal" and st.length_sp >= HEAD_OWNED_HORIZONTAL_SPACES
                and max(st.profile or [0]) / TARGET_SP_PX < HEAD_OWNED_HORIZONTAL_MAX_THICK_SPACES):
            return "beam_or_rung"
        if i in foreign:
            return "foreign:" + str(foreign[i])
        return None

    for i in covered:
        why = _owned_by(i)
        if why is None:
            kept.append(i)
        else:
            out["dropped"].append([i, why])
            owned.append(i)
    kept_set = set(kept)
    for i in partial:            # a sliver of a head piece the box cut: kept only when it is a blob / rim touching a kept piece
        st = res.strokes[i]
        if _owned_by(i) is not None:
            owned.append(i)
            continue
        if st.kind in ("blob", "horizontal") and any(j in kept_set for j, _c in st.touches):
            kept.append(i)
    # every owned stroke TOUCHING a kept piece is owned elsewhere too, even where the box does not reach it (the stem beside a head)
    for i in list(kept):
        for j, _c in res.strokes[i].touches:
            if j not in owned and _owned_by(j) is not None:
                owned.append(j)
            if res.strokes[j].kind == "vertical" and j not in stems:
                stems.append(j)
    out["pieces"] = sorted(kept)
    if not kept:
        if any(w.startswith("foreign:") for _i, w in out["dropped"]):
            out["why"], out["not_one_head"] = "not_one_head", "ink_is_another_marks"
        else:
            out["why"] = "no_head_ink"
        return out

    H, W = erased.shape
    xs0 = [res.strokes[i].box[0] for i in kept] + [float(box[0])]
    ys0 = [res.strokes[i].box[1] for i in kept] + [float(box[1])]
    xs1 = [res.strokes[i].box[0] + res.strokes[i].box[2] for i in kept] + [float(box[2])]
    ys1 = [res.strokes[i].box[1] + res.strokes[i].box[3] for i in kept] + [float(box[3])]
    mg = int(math.ceil(HEAD_WINDOW_MARGIN_SPACES * sp))
    wx0, wy0 = max(0, int(min(xs0)) - mg), max(0, int(min(ys0)) - mg)
    wx1, wy1 = min(W, int(math.ceil(max(xs1))) + mg), min(H, int(math.ceil(max(ys1))) + mg)
    if wx1 - wx0 < 4 or wy1 - wy0 < 4:
        out["why"] = "no_head_ink"
        return out
    E = np.asarray(erased[wy0:wy1, wx0:wx1]) == 0
    Rw = (np.asarray(raw[wy0:wy1, wx0:wx1]) == 0) if raw is not None and getattr(raw, "shape", None) == erased.shape else None
    K = np.zeros_like(E)
    for i in kept:
        m, x0, y0 = res.masks[i]
        _upsample_into(K, m, x0, y0, res.scale, wx0, wy0)
    O = np.zeros_like(E)
    for i in sorted(set(owned)):
        m, x0, y0 = res.masks[i]
        _upsample_into(O, m, x0, y0, res.scale, wx0, wy0)
    def _hull(mask: np.ndarray) -> np.ndarray:
        pts = np.column_stack(np.nonzero(mask)[::-1]).astype(np.int32)
        hh = np.zeros(mask.shape, np.uint8)
        cv2.fillConvexPoly(hh, cv2.convexHull(pts), 1)
        return hh.astype(bool)

    k = max(1, int(round(1.0 / res.scale)))
    # The pieces are the SEED, not the mask: `map_strokes` cut the remainder a reduced pixel clear of the openings and does not file a
    # piece under its floor (a half's lune beside its stem is often one), so the head's own ink is the erased ink, outside every owned
    # stroke's footprint, connected to the seed within a fifth of a space of its hull.
    seed = cv2.dilate(K.astype(np.uint8), np.ones((2 * k + 1, 2 * k + 1), np.uint8)).astype(bool) & E & ~O
    if not seed.any():
        out["why"] = "no_head_ink"
        return out
    r = max(1, int(round(0.2 * sp)))
    region = cv2.dilate(_hull(seed).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))).astype(bool)
    cand = (E & ~O & region).astype(np.uint8)
    n_c, lab_c = cv2.connectedComponents(cand, connectivity=8)
    keep_l = np.unique(lab_c[seed & cand.astype(bool)])
    K = np.isin(lab_c, keep_l[keep_l > 0])
    # The ink the staff-line erase took (`raw & ~erased`, never an owned stroke's) comes back only within the head's own columns and only
    # where it touches the head: the eraser's walk through a ring tangent to a line takes the line AND the rim under it as one flat band,
    # which this mends; the line beyond the head, and a line that does not touch it, are left alone.
    restored = 0
    M = K
    if Rw is not None:
        L = Rw & ~E & ~O
        kc = np.nonzero(K.any(axis=0))[0]
        L[:, :int(kc[0])] = False
        L[:, int(kc[-1]) + 1:] = False
        if L.any():
            n_l, lab_l = cv2.connectedComponents(L.astype(np.uint8), connectivity=8)
            touch = cv2.dilate(K.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
            ids = np.unique(lab_l[touch & L])
            back = np.isin(lab_l, ids[ids > 0])
            restored = int(back.sum())
            M = K | back
    # Inside the head's own outline every ink pixel is the head's (the stem's ink fused along its side, a rung through it).
    M = M | (E & _hull(M))
    clipped = False
    ys, xs = np.nonzero(M)
    ex0, ey0, ex1, ey1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    box_h = (float(box[3]) - float(box[1])) / sp
    if (ey1 - ey0) / sp > HEAD_INK_MAX_HEIGHT_SPACES and box_h <= HEAD_INK_MAX_HEIGHT_SPACES:
        c = int(math.ceil(HEAD_STACK_CLIP_SPACES * sp))
        r0, r1 = max(0, int(float(box[1])) - wy0 - c), min(M.shape[0], int(math.ceil(float(box[3]))) - wy0 + c)
        M2 = np.zeros_like(M)
        M2[r0:r1] = M[r0:r1]
        if M2.any():
            M, clipped = M2, True
            ys, xs = np.nonzero(M)
            ex0, ey0, ex1, ey1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    w_sp, h_sp = (ex1 - ex0) / sp, (ey1 - ey0) / sp
    hole, n_holes, hole_sp2 = mask_holes(M[ey0:ey1, ex0:ex1], sp)
    stem_cut = None
    if stems:
        cx = wx0 + (ex0 + ex1) / 2.0
        sx = [res.strokes[j].box[0] + res.strokes[j].box[2] / 2.0 for j in stems]
        stem_cut = "left" if min(sx, key=lambda v: abs(v - cx)) < cx else "right"
    noh = None
    foreign_dropped = any(wd.startswith("foreign:") for _i, wd in out["dropped"])
    if w_sp > HEAD_INK_MAX_WIDTH_SPACES or h_sp > HEAD_INK_MAX_HEIGHT_SPACES:
        noh = "holds_another_marks_ink" if foreign_dropped else ("too_wide" if w_sp > HEAD_INK_MAX_WIDTH_SPACES else "too_tall")
    elif w_sp < HEAD_INK_MIN_SPACES or h_sp < HEAD_INK_MIN_SPACES:
        noh = "too_small"
    out.update(mask=M, origin=(wx0, wy0), extent=[wx0 + ex0, wy0 + ey0, wx0 + ex1, wy0 + ey1],
               extent_sp=[round(w_sp, 3), round(h_sp, 3)],
               centre=[round(wx0 + (ex0 + ex1) / 2.0, 1), round(wy0 + (ey0 + ey1) / 2.0, 1)],
               hole_share=hole, n_holes=n_holes, hole_sp2=hole_sp2, line_px_restored=restored, stem_cut=stem_cut,
               stack_clipped=clipped, not_one_head=noh,
               size_margin_sp=round(min(HEAD_INK_MAX_WIDTH_SPACES - w_sp, HEAD_INK_MAX_HEIGHT_SPACES - h_sp,
                                        w_sp - HEAD_INK_MIN_SPACES, h_sp - HEAD_INK_MIN_SPACES), 3))
    if noh:
        out["why"] = "not_one_head"
    return out


def head_ink_value(hm: Dict[str, Any], slit: Optional[float]) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """`(value, why, margin)`: the producer's own reading of one head mask. `hollow` where the mask ENCLOSES paper and 2.148's slit (on the
    mask's extent) reads hollow; `filled` where it encloses none and the slit reads filled. Otherwise None and why: 'not_one_head' (fix A),
    'no_head_ink' / 'no_stroke_map', 'ring_open' (white inside but not enclosed), 'readers_split' (the two disagree, or the slit sits between
    its cuts). `margin` = the slit's signed distance past the cut it passed (hollow: slit - 0.18; filled: 0.06 - slit); None with no value."""
    if hm.get("why") in ("not_one_head", "no_head_ink", "no_stroke_map") or hm.get("not_one_head"):
        return None, hm.get("why") or "not_one_head", None
    if slit is None:
        return None, "readers_split", None
    hole = float(hm.get("hole_share") or 0.0)
    if hole > 0 and slit >= HEAD_SLIT_HOLLOW_MIN:
        return "hollow", None, round(slit - HEAD_SLIT_HOLLOW_MIN, 4)
    if hole == 0 and slit <= HEAD_SLIT_FILLED_MAX:
        return "filled", None, round(HEAD_SLIT_FILLED_MAX - slit, 4)
    if hole == 0 and slit >= HEAD_SLIT_HOLLOW_MIN:
        return None, "ring_open", None
    return None, "readers_split", None
