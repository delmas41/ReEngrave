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
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

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

# ───────────────────────────── ROADMAP 2.239: split fused ink at its joins (flag `OMR_SPLIT_JOINS`, default OFF) ─────────────────────────────
#: CAUSE (2.239, Brahms p0 against Sean's labels): the vertical opening is a column test -- a column run of ink at least `V_MIN_SPACES` tall is
#: "vertical" whatever its WIDTH. Two heads a third apart on one stem make columns ~2 sp tall across the whole oval, so the pair AND the stem
#: become one `vertical` stroke (197 of the 212 black heads that own no ink); a head on a ledger rung passes the horizontal opening with the
#: rung (19); a tie or slur touching a head is one remainder piece with it. The detector's head box then covers under half of that stroke and
#: no box owns it. The split below reads only the stroke's own geometry, in the reduced frame, and cuts only where the geometry shows a join;
#: every part keeps a `joined_to` link, so nothing is lost and a later reader still sees the join. Where it cannot tell, the piece stays whole
#: and the reason is counted (`CellStrokes.split_refused`).
SPLIT_JOINS_ENV = "OMR_SPLIT_JOINS"
#: a row run of a vertical stroke no wider than this is STEM (or barline) ink; wider is something fused to it (a head's oval, a beam).
#: Litolff's widest plain stem 0.43 sp, Brahms 0.37 at p90 (`STEM_TRUE_WIDTH_MAX_SPACES` note); a black head is >= 1.0 sp wide.
STEM_THIN_SPACES = 0.5
#: a thin part shorter than this is an oval's tip or a stem's stub beside a head: it goes back to the wide part it touches
STEM_PART_MIN_SPACES = 0.5
#: a wide part smaller than this is a blip on a stem (an erase scar), not a mark fused to it: it goes back to the stem
WIDE_PART_MIN_SP2 = 0.25
#: the height cap of ONE head (`head_ink.MAX_HEIGHT_SPACES_V2`, 2.220 fix 2, Sean "1.6"; a test pins that they are equal) and its width cap
#: (`head_ink.MAX_WIDTH_SPACES`): a wide part taller than this and no wider is a STACK of heads, cut at its waist
HEAD_HEIGHT_CAP_SPACES = 1.6
HEAD_WIDTH_CAP_SPACES = 1.75
#: a stack is at least a head wide (a black head is >= 1.0 sp wide; a bracket's or thick barline's line <= 0.7) and at most four heads tall
HEAD_MIN_WIDTH_SPACES = 0.8
STACK_MAX_SPACES = 5.0
#: a stack is cut only at a row this much narrower than the narrower of its two halves' widest rows (a real neck between two ovals);
#: a stack with no such row stays whole (`stack_no_waist`)
WAIST_SHARE_MAX = 0.75
#: ... or at a row where one edge steps in by at least this from both ovals' extremes (a notch; ~2 reduced px, above the +-1 px scan edge)
STACK_NOTCH_SPACES = 0.12
#: each band of a cut stack is at least this tall: a head (~1 sp), never a rung with the top of a head (2.239 tile 9, Sean "ledger line")
STACK_BAND_MIN_SPACES = 0.8
#: the oval edges of a stack are read on the cell's ink this far beside the part (the opening drops a notched column to the remainder)
STACK_EDGE_PAD_SPACES = 0.3
#: head|arc: a disk this wide survives in a head's body (a black head is ~1 sp tall) and not in a tie or slur (<= `CURVE_MAX_THICK_SPACES`)
HEAD_BODY_SPACES = 0.55
HEAD_BODY_MIN_SP2 = 0.4
#: head|ledger: a horizontal stroke's column run this much thicker than its own line is a head on the rung
LEDGER_HEAD_EXCESS_SPACES = 0.35
LEDGER_HEAD_MIN_WIDTH_SPACES = 0.6
#: ... and the rung sticks out at least this far beyond the oval on BOTH sides (a head at a rung's end, or a beam, is left whole)
LEDGER_STUB_MIN_SPACES = 0.15
#: a column belongs to the oval while its run is this much thicker than the rung's (the oval's edge, 2.239 tiles 6 and 9)
LEDGER_EDGE_EXCESS_SPACES = 0.2
#: an oval tip the horizontal opening left to the remainder is smaller than this
LEDGER_TIP_MAX_SP2 = 0.35
#: a ledger rung is level: its thin columns' centres fit a line no steeper than this (rise over run; ~3 degrees)
LEDGER_MAX_SLOPE = 0.05


def split_joins_enabled() -> bool:
    """`OMR_SPLIT_JOINS` (ROADMAP 2.239), default OFF; `1/true/yes/on` enables."""
    return os.environ.get(SPLIT_JOINS_ENV, "").strip().lower() in ("1", "true", "yes", "on")


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
    #: ROADMAP 2.239 (`OMR_SPLIT_JOINS`): the strokes this one was cut from the same fused piece with, and the join -- (ordinal, "head|stem")
    joined_to: List[Tuple[int, str]] = field(default_factory=list)


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
    #: ROADMAP 2.239: pieces a join split looked at and left whole, by reason (empty with the flag off)
    split_refused: Dict[str, int] = field(default_factory=dict)


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


def _classify(m: np.ndarray, sp: float, lines: bool = True) -> str:
    """The kind of a part cut out of a fused piece, by the same rules `map_strokes` applies to whole pieces (no new cut). `lines` False: a
    part of the remainder, which the openings already refused, can only be a curve or a blob."""
    h, w = m.shape
    a = int(m.sum())
    longest = max(w, h)
    if lines and h >= V_MIN_SPACES * sp and w <= STEM_THIN_SPACES * sp:
        return "vertical"
    if lines and w >= H_MIN_SPACES * sp and w > h and a > 0 and (longest * longest) / float(a) >= H_MIN_ASPECT:
        return "horizontal"
    thick_mean = a / float(longest) if longest else 0.0
    if longest >= CURVE_MIN_SPACES * sp and thick_mean <= CURVE_MAX_THICK_SPACES * sp and longest / max(1.0, thick_mean) >= CURVE_MIN_ASPECT:
        return "curve"
    return "blob"


def _parts(full: np.ndarray, x0: int, y0: int, labels: np.ndarray, ids: Sequence[int]) -> List[Tuple[np.ndarray, int, int]]:
    """Each label id of `labels` (same frame as `full`) as a cropped (mask, x0, y0)."""
    out = []
    for i in ids:
        ys, xs = np.nonzero(labels == i)
        if ys.size == 0:
            continue
        a, b, c, d = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
        out.append(((labels[a:b, c:d] == i) & full[a:b, c:d], x0 + c, y0 + a))
    return out


def _merge_small(lab: np.ndarray, keep: Dict[int, bool]) -> np.ndarray:
    """Give every label NOT kept to the kept label it touches most (8-neighbourhood), repeatedly; a label touching no kept one stays (it is
    then kept: no ink is ever dropped). Returns the relabelled image."""
    import cv2
    lab = lab.copy()
    k3 = np.ones((3, 3), np.uint8)
    for _ in range(50):
        moved = False
        for i in [i for i, ok in keep.items() if not ok]:
            m = (lab == i)
            if not m.any():
                continue
            ring = cv2.dilate(m.astype(np.uint8), k3).astype(bool) & ~m
            nb = lab[ring]
            nb = nb[(nb > 0) & np.isin(nb, [j for j, ok in keep.items() if ok])]
            if nb.size:
                tgt = int(np.bincount(nb).argmax())
                lab[m] = tgt
                keep[i] = True          # merged away
                moved = True
        if not moved:
            break
    return lab


def _cut_stack(m: np.ndarray, sp: float, prof: Optional[np.ndarray] = None) -> Tuple[List[np.ndarray], Optional[str]]:
    """A wide part taller than one head: cut at the waist between two ovals (head|head). Returns (row-bands as masks of `m`'s frame, why-not).
    `prof` (same rows as `m`, any columns) is the ink the edges are read on: the part's own ink plus the oval edges the vertical opening left
    to the remainder (a column broken by a notch is not in the opening), rungs left out; None = `m` itself."""
    h, w = m.shape
    prof = m if prof is None else prof
    if h <= HEAD_HEIGHT_CAP_SPACES * sp:
        return [m], None
    if w > HEAD_WIDTH_CAP_SPACES * sp:
        return [m], "stack_too_wide"
    lo, hi = int(round(STACK_BAND_MIN_SPACES * sp)), h - int(round(STACK_BAND_MIN_SPACES * sp))
    if hi <= lo:
        return [m], "stack_no_waist"
    # two convex ovals meet at a NOTCH: a row where the left or right edge steps in from both ovals' extremes (a ledger rung or a scan
    # between the heads can fill the middle, so a row's width alone misses it -- Brahms p0 q6)
    rows = np.nonzero(prof.any(axis=1))[0]
    L = np.full(h, np.nan)
    Rr = np.full(h, np.nan)
    for r in rows:
        xs = np.nonzero(prof[r])[0]
        L[r], Rr[r] = xs[0], xs[-1]
    widths = prof.sum(axis=1).astype(float)
    best = (0.0, -1)
    for r in range(lo, hi):
        if np.isnan(L[r]):
            continue
        dR = min(np.nanmax(Rr[:r]), np.nanmax(Rr[r + 1:])) - Rr[r]
        dL = L[r] - max(np.nanmin(L[:r]), np.nanmin(L[r + 1:]))
        dW = (1.0 - WAIST_SHARE_MAX) * sp if widths[r] <= WAIST_SHARE_MAX * min(widths[:r].max(), widths[r + 1:].max()) else 0.0
        depth = max(dR, dL, dW)
        if depth > best[0]:
            best = (float(depth), r)
    if best[1] < 0 or best[0] < STACK_NOTCH_SPACES * sp:
        return [m], "stack_no_waist"
    r = best[1]
    top, bot = m.copy(), m.copy()
    top[r + 1:] = False
    bot[:r + 1] = False
    out: List[np.ndarray] = []
    why = None
    for part in (top, bot):
        ys = np.nonzero(part.any(axis=1))[0]
        if ys.size == 0:
            continue
        sub, w2 = _cut_stack(part[ys[0]:ys[-1] + 1], sp, prof[ys[0]:ys[-1] + 1])
        for s_ in sub:
            full = np.zeros_like(m)
            full[ys[0]:ys[-1] + 1] = s_
            out.append(full)
        why = why or w2
    return out, why


def _split_vertical(m: np.ndarray, sp: float, refused: Dict[str, int], context: Optional[Tuple[np.ndarray, int, int]] = None
                    ) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """head|stem, stem|beam, stem|flag: a vertical piece whose rows are not all thin. The stem is its THIN rows (a row run no wider than
    `STEM_THIN_SPACES`); the rows where the run is wide are what is fused to it, cut where the stem leaves them. Returns [(kind, mask in m's
    frame, join)] with the stem first, or None (left whole)."""
    import cv2
    h, w = m.shape
    thin_px = STEM_THIN_SPACES * sp
    if w <= thin_px:
        return None                                    # all thin: a stem or a barline alone
    wide = np.zeros_like(m)
    for r in range(h):
        row = m[r]
        if not row.any():
            continue
        d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
        starts, ends = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        for a, b in zip(starts, ends):
            if b - a > thin_px:
                wide[r, a:b] = True
    if not wide.any():
        refused["vertical_all_thin_rows"] = refused.get("vertical_all_thin_rows", 0) + 1
        return None
    thin = m & ~wide
    if not thin.any():
        return _stack_or_whole(m, sp, refused, context)
    return _split_thin_wide(m, thin, wide, sp, refused, context)


def _stack_or_whole(m: np.ndarray, sp: float, refused: Dict[str, int], context) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """A vertical piece with no stem in it. A stack of heads (the stem a pixel apart, Brahms p0 q49) is cut at its notch (head|head); any
    other solid slab (a bracket, a thick barline, a beam bundle) stays whole."""
    prof = _profile(m, 0, 0, context, sp)
    if not _looks_like_heads(m, sp, prof):
        refused["vertical_no_thin_core"] = refused.get("vertical_no_thin_core", 0) + 1
        return None
    bands, why = _cut_stack(m, sp, prof)
    if len(bands) > 1:
        return [("blob" if _classify(_crop(b)[0], sp) == "vertical" else _classify(_crop(b)[0], sp), b, "head|head") for b in bands]
    refused[why or "stack_no_waist"] = refused.get(why or "stack_no_waist", 0) + 1
    return None


def _split_thin_wide(m: np.ndarray, thin: np.ndarray, wide: np.ndarray, sp: float, refused: Dict[str, int], context
                     ) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    import cv2
    # label: thin components 1..nt, wide components nt+1..
    nt, tl = cv2.connectedComponents(thin.astype(np.uint8), connectivity=8)
    nw, wl = cv2.connectedComponents(wide.astype(np.uint8), connectivity=8)
    lab = np.where(thin, tl, 0) + np.where(wide, wl + (nt - 1), 0)
    keep: Dict[int, bool] = {}
    kind_of: Dict[int, str] = {}
    for i in range(1, nt):
        ys = np.nonzero((tl == i).any(axis=1))[0]
        keep[i] = bool(ys.size) and (ys[-1] - ys[0] + 1) >= STEM_PART_MIN_SPACES * sp
        kind_of[i] = "thin"
    for j in range(1, nw):
        i = j + nt - 1
        keep[i] = int((wl == j).sum()) >= WIDE_PART_MIN_SP2 * sp * sp
        kind_of[i] = "wide"
    # small wide blips go to the stem first, then oval tips / stubs to the wide part
    lab = _merge_small(lab, {i: (keep[i] or kind_of[i] == "thin") for i in keep})
    lab = _merge_small(lab, {i: (keep[i] or kind_of[i] == "wide") for i in keep if (lab == i).any()})
    ids = [i for i in sorted(keep) if (lab == i).any()]
    if not any(kind_of[i] == "thin" for i in ids):
        return _stack_or_whole(m, sp, refused, context)        # only an oval's tips were thin: no stem in it
    if not any(kind_of[i] == "wide" for i in ids):
        refused["vertical_nothing_fused"] = refused.get("vertical_nothing_fused", 0) + 1
        return None
    out: List[Tuple[str, np.ndarray, str]] = []
    for i in sorted(ids, key=lambda i: (kind_of[i] != "thin", -int((lab == i).sum()))):
        part = lab == i
        if kind_of[i] == "thin":
            out.append(("vertical" if _extent_h(part) >= V_MIN_SPACES * sp else _classify(_crop(part)[0], sp), part, "stem"))
            continue
        pc, oy, ox = _crop(part)
        prof = _profile(pc, oy, ox, context, sp)
        bands, why = (_cut_stack(pc, sp, prof) if _looks_like_heads(pc, sp, prof) else ([pc], None))
        if why:
            refused[why] = refused.get(why, 0) + 1
        for b in bands:
            full = np.zeros_like(m)
            full[oy:oy + b.shape[0], ox:ox + b.shape[1]] = b
            k = _classify(_crop(full)[0], sp)
            out.append((k, full, "stem|" + {"blob": "head", "horizontal": "beam", "curve": "flag", "vertical": "stem"}[k]))
    return out


def _profile(pc: np.ndarray, oy: int, ox: int, context: Optional[Tuple[np.ndarray, int, int]], sp: float) -> Optional[np.ndarray]:
    """The edge-reading ink of a head stack (`_cut_stack`): `context` = (cell ink minus rungs, piece x0, piece y0) in the reduced frame; the ink
    within `STACK_EDGE_PAD_SPACES` of the part, in the part's rows, connected to it. None without a context."""
    import cv2
    if context is None:
        return None
    ink, px0, py0 = context
    pad = max(1, int(round(STACK_EDGE_PAD_SPACES * sp)))
    H, W = ink.shape
    y0, x0 = py0 + oy, px0 + ox
    y1, x1 = y0 + pc.shape[0], x0 + pc.shape[1]
    xa, xb = max(0, x0 - pad), min(W, x1 + pad)
    win = ink[y0:y1, xa:xb].copy()
    win[:, x0 - xa:x0 - xa + pc.shape[1]] |= pc
    n, lab = cv2.connectedComponents(win.astype(np.uint8), connectivity=8)
    own = np.unique(lab[:, x0 - xa:x0 - xa + pc.shape[1]][pc])
    return np.isin(lab, own[own > 0])


def _crop(m: np.ndarray) -> Tuple[np.ndarray, int, int]:
    ys, xs = np.nonzero(m)
    a, b, c, d = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    return m[a:b, c:d], a, c


def _extent_h(m: np.ndarray) -> int:
    ys = np.nonzero(m.any(axis=1))[0]
    return int(ys[-1] - ys[0] + 1) if ys.size else 0


def _looks_like_heads(m: np.ndarray, sp: float, prof: Optional[np.ndarray] = None) -> bool:
    """Taller than one head, no wider than one, at least a head's width (a bracket's or a thick barline's line is narrower), at most a few
    heads tall. The width is read on `prof` (`_profile`) when given: the opening drops a notched oval's edge columns."""
    c, _a, _b = _crop(m)
    wd = _crop(prof)[0].shape[1] if prof is not None and prof.any() else c.shape[1]
    return (HEAD_MIN_WIDTH_SPACES * sp <= wd <= HEAD_WIDTH_CAP_SPACES * sp
            and HEAD_HEIGHT_CAP_SPACES * sp < c.shape[0] <= STACK_MAX_SPACES * sp)


def _split_horizontal(m: np.ndarray, sp: float, refused: Dict[str, int]) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """ledger|head: a horizontal piece that is a LEVEL rung with ONE head on it. The head is ONE part -- every column of the oval, all its
    rows, the rung's rows through the oval included (Sean 2026-10-30, 2.239 tile 6: "just the top of an eighth note on a ledger line"
    was the fault); the rung is cut off only where it sticks out beyond the oval, left and right, and those stubs are LEDGER strokes
    (`horizontal`), never a blob (tile 9). The rung's thickness is read on its own stubs, never on the oval's columns.
    Longest column RUN, never the column count (a hairpin's two lines stack in one column)."""
    h, w = m.shape
    runs = np.zeros(w, int)
    cent = np.zeros(w, float)
    for c in range(w):
        col = m[:, c]
        if col.any():
            d = np.diff(np.concatenate(([0], col.astype(np.int8), [0])))
            st_, en_ = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
            k = int(np.argmax(en_ - st_))
            runs[c] = int(en_[k] - st_[k])
            cent[c] = (st_[k] + en_[k] - 1) / 2.0
    cols = np.nonzero(runs > 0)[0]
    if cols.size < 3:
        return None
    # the rung's own thickness: the thinnest runs at its two ends (a stub sticks out at least `LEDGER_STUB_MIN_SPACES` each side)
    stub = max(2, int(round(LEDGER_STUB_MIN_SPACES * sp)))
    ends = np.concatenate((runs[cols[:stub]], runs[cols[-stub:]]))
    line_t = float(np.median(ends))
    thick = runs > line_t + LEDGER_HEAD_EXCESS_SPACES * sp
    if not thick.any():
        return None
    a = int(np.nonzero(thick)[0][0])
    b = int(np.nonzero(thick)[0][-1]) + 1
    if int((~thick[a:b]).sum()) > 1:                     # two heads, or a beam that thickens twice: not one head on a rung
        refused["horizontal_two_thick_stretches"] = refused.get("horizontal_two_thick_stretches", 0) + 1
        return None
    # the oval's EDGE: widen the stretch while a column is still clearly thicker than the rung (`LEDGER_EDGE_EXCESS_SPACES`; a scanned rung
    # thickens a little toward the head, Brahms p5 tile 6), so the cut follows the oval's edge and never runs through the head
    edge = line_t + LEDGER_EDGE_EXCESS_SPACES * sp
    while a > 0 and runs[a - 1] > edge:
        a -= 1
    while b < w and runs[b] > edge:
        b += 1
    if b - a < LEDGER_HEAD_MIN_WIDTH_SPACES * sp or b - a > HEAD_WIDTH_CAP_SPACES * sp:
        refused["horizontal_thick_not_a_head"] = refused.get("horizontal_thick_not_a_head", 0) + 1
        return None
    left, right = (runs[:a] > 0), (runs[b:] > 0)
    if int(left.sum()) < stub or int(right.sum()) < stub:
        refused["horizontal_no_stub_both_sides"] = refused.get("horizontal_no_stub_both_sides", 0) + 1
        return None
    # a rung is LEVEL: its stub centres (both sides) fit a line no steeper than `LEDGER_MAX_SLOPE`
    xs = np.concatenate((np.nonzero(left)[0], b + np.nonzero(right)[0])).astype(float)
    slope = float(np.polyfit(xs, cent[xs.astype(int)], 1)[0])
    if abs(slope) > LEDGER_MAX_SLOPE:
        refused["horizontal_line_not_level"] = refused.get("horizontal_line_not_level", 0) + 1
        return None
    head = np.zeros_like(m)
    head[:, a:b] = m[:, a:b]
    lstub, rstub = m.copy(), m.copy()
    lstub[:, a:] = False
    rstub[:, :b] = False
    return [("blob", head, "head"), ("horizontal", lstub, "ledger|head"), ("horizontal", rstub, "ledger|head")]


def _split_remainder(m: np.ndarray, sp: float, refused: Dict[str, int]) -> Optional[List[Tuple[str, np.ndarray, str]]]:
    """head|arc: a remainder piece holding a head's body (a disk `HEAD_BODY_SPACES` wide survives in it) and a long thin tail (a tie or slur
    leaving the head). Each body no taller than one head is a head part; the thin ink at least `CURVE_MIN_SPACES` long is the arc."""
    import cv2
    h, w = m.shape
    if max(h, w) < CURVE_MIN_SPACES * sp:
        return None
    d = max(3, int(round(HEAD_BODY_SPACES * sp)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))
    pad = d
    mp = np.pad(m.astype(np.uint8), pad)
    body0 = cv2.morphologyEx(mp, cv2.MORPH_OPEN, disk)[pad:-pad, pad:-pad].astype(bool)
    if not body0.any():
        return None
    body = m & cv2.dilate(body0.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    nb, bl = cv2.connectedComponents(body.astype(np.uint8), connectivity=8)
    heads = []
    for i in range(1, nb):
        part = bl == i
        c, _a, _b = _crop(part)
        if int(part.sum()) >= HEAD_BODY_MIN_SP2 * sp * sp and c.shape[0] <= HEAD_HEIGHT_CAP_SPACES * sp and c.shape[1] <= HEAD_WIDTH_CAP_SPACES * sp:
            heads.append(part)
    if not heads:
        return None
    rest = m.copy()
    for hd in heads:
        rest &= ~hd
    nr, rl = cv2.connectedComponents(rest.astype(np.uint8), connectivity=8)
    lab = np.zeros(m.shape, np.int32)
    for k, hd in enumerate(heads, 1):
        lab[hd] = k
    keep: Dict[int, bool] = {k: True for k in range(1, len(heads) + 1)}
    arcs = []
    for i in range(1, nr):
        part = rl == i
        c, _a, _b = _crop(part)
        lid = len(heads) + i
        lab[part] = lid
        ok = max(c.shape) >= CURVE_MIN_SPACES * sp
        keep[lid] = ok
        if ok:
            arcs.append(lid)
    if not arcs:
        refused["remainder_no_long_tail"] = refused.get("remainder_no_long_tail", 0) + 1
        return None
    lab = _merge_small(lab, dict(keep))
    out: List[Tuple[str, np.ndarray, str]] = []
    for lid in arcs:
        if (lab == lid).any():
            part = lab == lid
            out.append((_classify(_crop(part)[0], sp, lines=False), part, "arc"))
    for k in range(1, len(heads) + 1):
        if (lab == k).any():
            out.append(("blob", lab == k, "arc|head"))
    return out if len(out) > 1 else None


def _inside_share(m: np.ndarray, x0: int, y0: int, rects: Sequence[Tuple[float, float, float, float]]) -> float:
    """The largest share of a piece's ink inside one of `rects` (reduced frame)."""
    tot = int(m.sum())
    best = 0.0
    if not tot:
        return 0.0
    h, w = m.shape
    for (a, b, c, d) in rects:
        lx0, ly0 = max(0, int(round(a)) - x0), max(0, int(round(b)) - y0)
        lx1, ly1 = min(w, int(round(c)) - x0), min(h, int(round(d)) - y0)
        if lx1 > lx0 and ly1 > ly0:
            best = max(best, int(m[ly0:ly1, lx0:lx1].sum()) / float(tot))
    return best


def split_pieces(pieces: List[Tuple[str, np.ndarray, int, int]], sp: float, ink: Optional[np.ndarray] = None,
                 keep_whole: Sequence[Tuple[float, float, float, float]] = ()
                 ) -> Tuple[List[Tuple[str, np.ndarray, int, int]], List[Tuple[int, int, str]], Dict[str, int]]:
    """ROADMAP 2.239: every piece cut at its joins (module constants above). Returns (pieces, joins [(part, first part of the same piece,
    join name)], refused {reason: n}). A piece left whole is returned unchanged; the union of a piece's parts is exactly the piece.
    `keep_whole` (reduced frame): the clef / key / meter boxes of the cell -- a piece mostly inside one is never cut (their ink is claimed
    whole by its area; the page has no join there, Sean's 2.239 tiles 2 and 5). A head cut off a rung takes back the oval's tips the
    horizontal opening left to the remainder, so a head on a ledger line is ONE stroke."""
    out: List[Tuple[str, np.ndarray, int, int]] = []
    joins: List[Tuple[int, int, str]] = []
    refused: Dict[str, int] = {}
    rung_heads: List[int] = []
    loose: List[int] = []
    lines_out = None
    if ink is not None:
        lines_out = ink.copy()
        for kind, m, x0, y0 in pieces:            # rungs and beams are left out of a stack's edges (a rung between two heads sticks out)
            if kind == "horizontal":
                h, w = m.shape
                lines_out[y0:y0 + h, x0:x0 + w] &= ~m
    for kind, m, x0, y0 in pieces:
        if keep_whole and _inside_share(m, x0, y0, keep_whole) >= 0.5:
            refused["inside_clef_key_meter"] = refused.get("inside_clef_key_meter", 0) + 1
            parts = None
        elif kind == "vertical":
            parts = _split_vertical(m, sp, refused, (lines_out, x0, y0) if lines_out is not None else None)
        elif kind == "horizontal":
            parts = _split_horizontal(m, sp, refused)
        else:
            parts = _split_remainder(m, sp, refused)
        if parts and int(sum(int(p_.sum()) for _k, p_, _j in parts)) != int(m.sum()):
            refused["parts_do_not_add_up"] = refused.get("parts_do_not_add_up", 0) + 1   # never lose or double ink: leave it whole
            parts = None
        if not parts:
            if kind == "blob" and int(m.sum()) < LEDGER_TIP_MAX_SP2 * sp * sp:
                loose.append(len(out))
            out.append((kind, m, x0, y0))
            continue
        first = len(out)
        for k, part, join in parts:
            if not part.any():
                continue
            c, oy, ox = _crop(part)
            if kind == "horizontal" and k == "blob":
                rung_heads.append(len(out))
            out.append((k, c, x0 + ox, y0 + oy))
            if len(out) - 1 != first:
                joins.append((len(out) - 1, first, join))
    # the oval's tips: a small remainder blob within the head's columns, touching it above or below, joins the head
    gone = set()
    for hi in rung_heads:
        k, hm, hx, hy = out[hi]
        for li in loose:
            if li in gone:
                continue
            _k2, lm, lx, ly = out[li]
            lh, lw = lm.shape
            if lx < hx - 1 or lx + lw > hx + hm.shape[1] + 1:
                continue
            if ly > hy + hm.shape[0] + 2 or ly + lh < hy - 2:
                continue
            X0, Y0 = min(hx, lx), min(hy, ly)
            X1, Y1 = max(hx + hm.shape[1], lx + lw), max(hy + hm.shape[0], ly + lh)
            u = np.zeros((Y1 - Y0, X1 - X0), bool)
            u[hy - Y0:hy - Y0 + hm.shape[0], hx - X0:hx - X0 + hm.shape[1]] |= hm
            u[ly - Y0:ly - Y0 + lh, lx - X0:lx - X0 + lw] |= lm
            out[hi] = (k, u, X0, Y0)
            hm, hx, hy = u, X0, Y0
            gone.add(li)
    if gone:
        keep = [i for i in range(len(out)) if i not in gone]
        new_of = {old: new for new, old in enumerate(keep)}
        out = [out[i] for i in keep]
        joins = [(new_of[a], new_of[b], j) for a, b, j in joins]
    return out, joins, refused


def map_strokes(erased: np.ndarray, sp_canonical: float, nominal_lines_canonical: Sequence[float],
                raw: Optional[np.ndarray] = None, split_joins: Optional[bool] = None,
                keep_whole: Sequence[Sequence[float]] = ()) -> Optional[CellStrokes]:
    """Every stroke of one cell. `erased` = `cell.image_no_staff` (0 = ink); `raw` = `cell.binary` (0 = ink) for the local staff.
    None for a cell that cannot be reduced. Deterministic: strokes ordered by (x, y, kind). `split_joins` None = the flag
    `OMR_SPLIT_JOINS` (ROADMAP 2.239): fused pieces are cut at their joins (`split_pieces`) and each part carries `joined_to`."""
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
    joins: List[Tuple[int, int, str]] = []
    refused: Dict[str, int] = {}
    if split_joins if split_joins is not None else split_joins_enabled():
        kw = [tuple(float(v) * scale for v in r) for r in keep_whole]      # canonical (x0, y0, x1, y1) -> reduced
        pieces, joins, refused = split_pieces(pieces, sp, ink, kw)

    staff = LocalStaff(_reduce_float(raw, scale) if raw is not None else None,
                       [y * scale for y in nominal_lines_canonical], sp)
    restore = THICKNESS_FROM_UNERASED and raw is not None and raw.ndim == 2 and raw.shape == erased.shape

    built: List[Tuple[Tuple[int, int, int, int], Stroke, np.ndarray, int, int, int]] = []
    for pidx, (kind, m, x0, y0) in enumerate(pieces):
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
        built.append((box, st, m, x0, y0, pidx))

    built.sort(key=lambda r: (r[0][0], r[0][1], KINDS.index(r[1].kind)))
    k3 = np.ones((3, 3), np.uint8)       # contact = within 2 px: the remainder was cut 1 px clear of the openings
    n = len(built)
    for i in range(n):
        _b, si, mi, xi, yi, _pi = built[i]
        hi_, wi_ = mi.shape
        for j in range(i + 1, n):
            _b2, sj, mj, xj, yj, _pj = built[j]
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
    if joins:
        ordinal = {r[5]: o for o, r in enumerate(built)}
        for part, first, join in joins:
            a, b = ordinal[part], ordinal[first]
            out[a].joined_to.append((b, join))
            out[b].joined_to.append((a, join))
    per: Dict[int, int] = {}
    for s in out:
        per[s.component] = per.get(s.component, 0) + 1
    for s in out:
        s.component_n_strokes = per[s.component]
    return CellStrokes(out, below, scale, float(sp_canonical), staff.local, masks=[(r[2], r[3], r[4]) for r in built],
                       split_refused=refused)


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
