"""Classical-CV detection of slur/tie ARCS in a measure cell.

Round 8 of the arcs work (2026-09). Rounds 3-7 closed the learning path:
production's arc precision on the adjudicated scan gauntlet is 0.232 at
recall 0.824 (`benchmarks/omr-queue-arcs-2026-09/ROUND7_FINDINGS.md`), a
frozen-head specialist cannot move it because the trunk's features do not
separate real arcs from the two certified fake families, and full fine-tuning
deletes whole classes. This module is the surviving lever — the same move
Phase 4f made for stems and beams: "YOLO bounding boxes are structurally bad
at thin lines", and a slur IS a thin curved line.

The reader works on STROKE GEOMETRY, in four steps:

  1. keep only THIN vertical ink runs, which cuts arc strokes free of the
     noteheads, beams and barlines they touch;
  2. connected components on that mask are candidate stroke fragments;
  3. CHAIN fragments whose facing endpoints continue each other — a scanned
     arc is routinely broken where staff-line removal crossed it or where a
     stem cut it (37 of the gauntlet's 176 real arcs are only recoverable
     merged);
  4. gate each chained stroke on the measured populations: long, continuous,
     smoothly curved one way, actually arcing, and not sliced by the crop's
     top or bottom.

Every constant is read off a measured population
(`benchmarks/omr-arc-cv-2026-09/`, over the 126 adjudicated cells: 176
human-verified real arcs, 260 human-certified fakes) — see FINDINGS.md
there for each population and its gap.

Output is `LineDetection` objects (quack-compatible with SymbolDetection)
with `smufl_name` "tie" or "slur" and category "structural", so they flow
into the SAME pairing machinery YOLO arcs do: `transcribe._pair_ties_in_cell`
/ `_pair_ties_in_staff` for ties, `export.annotate_slurs_in_slot` for slurs.
No parallel event model.
"""

from __future__ import annotations

import numpy as np
import cv2

from .line_detection import LineDetection, _binary_ink, _staff_line_spacing


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: An ink pixel belongs to a "thin" vertical run when the run is at most this
#: many staff spaces tall. Real arc strokes on the 600-dpi scans run a median
#: 0.20-0.37 spaces per column (p95 0.371); noteheads are ~1.0 and a beam
#: 0.4-0.6. This single cap is what separates stroke ink from solid symbols —
#: there is deliberately NO separate per-stroke thickness gate below, because
#: a gate at the population's p75 (0.32) was measured refusing 31 of the 176
#: real arcs (probe_recall_losses.py: `gate:thickness`) for no fake refused.
ARC_THIN_RUN_MAX_SPACES = 0.45

#: Fragment chaining: two fragments continue one arc when the horizontal gap
#: between their facing ends is at most this many spaces ...
ARC_CHAIN_MAX_GAP_SPACES = 0.8

#: ... and the facing endpoints' midline heights differ by at most this many
#: spaces. Both are plateaus, not peaks: the gauntlet score is identical for
#: the gap anywhere in 0.6-1.0 and the dy anywhere in 0.3-0.5 (see
#: FINDINGS.md).
ARC_CHAIN_MAX_DY_SPACES = 0.4

#: Smallest fragment worth chaining, in spaces. Below this a "fragment" is
#: dust the mask sheds everywhere.
ARC_FRAGMENT_MIN_WIDTH_SPACES = 0.5

#: Second-phase join for arcs DISSOLVED mid-stroke: a faded scan stroke can
#: crumble into sub-fragment dust for several spaces (measured up to ~7 on
#: the Brahms gauntlet), leaving two substantial end pieces no endpoint rule
#: can bridge. Two pieces are joined when each is at least
#: ARC_JOIN_MIN_FRAG_SPACES wide, the gap is at most ARC_JOIN_MAX_GAP_SPACES,
#: and the LEFT piece's fitted quadratic predicts the RIGHT piece's opening
#: midline within ARC_JOIN_PRED_TOL_SPACES — i.e. the right piece lies on the
#: left piece's own curve. A chain of DISTINCT consecutive ties does not join
#: this way: each tie's parabola dives after its end while the next tie opens
#: level with its start.
ARC_JOIN_MAX_GAP_SPACES = 8.0
ARC_JOIN_PRED_TOL_SPACES = 0.2
ARC_JOIN_MIN_FRAG_SPACES = 1.5

#: Minimum width of a finished arc. Real arcs: p5 = 1.6 spaces (ties are the
#: short end); below ~1 space nothing distinguishes a dash.
ARC_MIN_WIDTH_SPACES = 1.4

#: Minimum fraction of a chained stroke's columns that carry its ink — an arc
#: is one continuous stroke, chained across cuts, not a constellation. A
#: stroke built by the dissolved-gap join is EXPECTED to be mostly gap, so it
#: answers to the lower floor instead (its evidence is the fit agreement).
ARC_MIN_COVERAGE = 0.8
ARC_MIN_COVERAGE_JOINED = 0.3

#: RMS residual of the midline's quadratic fit, in spaces. A real arc is a
#: smooth curve (p95 = 0.051); jagged staff-line remnants are not.
ARC_MAX_FIT_RESID_SPACES = 0.10

#: The stroke must actually ARC: max deviation of its midline from the chord
#: joining its endpoints, in spaces. The real population's p25 is 0.124 with
#: p5 = 0.042 — the flattest ties — while flat non-arcs (ledger lines, beam
#: fragments, staff residue) pile up below 0.073 (OTHER p75). The value keeps
#: the certified staff-jag family at zero fired (see FINDINGS.md).
ARC_MIN_RISE_SPACES = 0.12

#: ... and the deviation must be one-sided (an arch, not a wiggle): fraction
#: of total |deviation| on the majority side. Real arcs p25 = 0.992.
ARC_MIN_SIDE_FRACTION = 0.95

#: A stroke whose ink reaches the crop's TOP or BOTTOM edge is refused as the
#: neighbouring staff's ink sliced by the cell boundary. Strokes touching the
#: LEFT/RIGHT edges are kept — they are arcs continuing across a BARLINE,
#: which the cross-cell pairing machinery (`_pair_ties_in_staff`,
#: `_merge_arcs_across_barlines`) exists to rejoin. A finer sliced-vs-grazing
#: test was measured and REFUSED: real high arcs are genuinely cut by the
#: crop too (their stroke ends sit 0.01-0.28 spaces from the edge, same as
#: the fakes'), so the edge cannot decide ownership more finely than this.
ARC_EDGE_MARGIN_PX = 2

#: A stroke whose midline centre sits more than this many spaces BELOW the
#: staff's bottom line is the staff below's ink. The populations are
#: asymmetric and the asymmetry is an engraving fact: above the staff, real
#: arcs follow the ledger notes up (29 of 176 adjudicated real boxes sit 2.5+
#: spaces above, 15 beyond 4) — but BELOW, real arcs stop: 4 of 176 in
#: [2.5, 4) and none at 4+, because the space below a staff on a conductor's
#: page belongs to the next staff's own airspace. The certified fakes bloom
#: exactly there (68 of 260 at 2.5+ below). probe_box_positions.py.
ARC_MAX_BELOW_STAFF_SPACES = 2.5

#: Tie/slur split. On the adjudicated boxes the two width populations overlap
#: too much to separate alone (tie p50 4.4 spaces, slur p50 5.7); what
#: separates better is FLATNESS — rise relative to width. A tie is a shallow
#: arch; a slur climbs. Production's own kind accuracy on the gauntlet is
#: 0.717, the bar to meet.
ARC_TIE_MAX_WIDTH_SPACES = 6.0
ARC_TIE_MAX_RISE_RATIO = 0.11


def arc_cv_mode() -> str:
    """The `OMR_ARC_CV` arrangement. DEFAULT OFF — nothing changes unless set.

    Modes, each measured on the gauntlet (score_arrangements.py; production =
    recall 0.824 / precision 0.232 / kind 0.717, fires on 241 of 260 fakes):

        veto     — keep a YOLO tie/slur only where a CV arc overlaps it
                   (IoU >= 0.1, or x-overlap >= 0.5 of the shorter with any
                   y contact — a plateau: 0.3 and 0.7 score identically).
                   recall 0.602 / precision 0.573 / kind 0.726 / 37 fakes.
        veto+cv  — the veto, plus CV arcs no YOLO arc overlapped.
                   recall 0.648 / precision 0.496 / kind 0.702 / 38 fakes.
        replace  — CV arcs only. recall 0.551 / precision 0.542 / 33 fakes.

    Off ("0"/unset) leaves the detector's arcs untouched.
    """
    import os
    v = os.environ.get("OMR_ARC_CV", "0").strip().lower()
    if v in ("", "0", "false", "no", "off"):
        return "off"
    if v in ("1", "veto", "true", "yes", "on"):
        return "veto"
    if v in ("veto+cv", "vetocv", "veto_cv"):
        return "veto+cv"
    if v == "replace":
        return "replace"
    return "off"


def _x_overlap_frac(a, b) -> float:
    ox = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    return max(0.0, float(ox)) / max(1, min(a[2], b[2]))


def _iou(a, b) -> float:
    ix = max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    return inter / (a[2] * a[3] + b[2] * b[3] - inter) if inter else 0.0


def _box_of(d) -> tuple[int, int, int, int]:
    return (d.x_canonical, d.y_canonical, d.width_canonical, d.height_canonical)


def apply_arc_cv(dets: list, cell, mode: str | None = None) -> list:
    """Arbitrate the detector's tie/slur detections against the CV arc reader.

    Returns a NEW detections list; every non-arc detection passes through
    untouched, in order. With mode "off" the input list is returned as-is.
    """
    mode = arc_cv_mode() if mode is None else mode
    if mode == "off":
        return dets
    arcs_yolo = [d for d in dets
                 if (getattr(d, "smufl_name", "") or "").lower() in ("tie", "slur")]
    arc_ids = {id(d) for d in arcs_yolo}
    others = [d for d in dets if id(d) not in arc_ids]
    cv_arcs = detect_arcs(cell)
    if mode == "replace":
        return others + cv_arcs
    cv_boxes = [_box_of(c) for c in cv_arcs]

    def confirmed(box) -> bool:
        for cb in cv_boxes:
            if _iou(box, cb) >= 0.1:
                return True
            oy = min(box[1] + box[3], cb[1] + cb[3]) - max(box[1], cb[1])
            if oy > 0 and _x_overlap_frac(box, cb) >= 0.5:
                return True
        return False

    kept = [d for d in arcs_yolo if confirmed(_box_of(d))]
    if mode == "veto":
        return others + kept
    # veto+cv: add the CV arcs no surviving YOLO arc already covers.
    kept_boxes = [_box_of(d) for d in kept]
    extra = [c for c in cv_arcs
             if not any(_iou(_box_of(c), kb) >= 0.3 for kb in kept_boxes)]
    return others + kept + extra


def _thin_run_mask(ink: np.ndarray, max_run: int) -> np.ndarray:
    """Boolean mask of ink pixels whose vertical run is <= max_run tall.

    Computed per column with a vectorised run-id trick (cumsum of run starts
    in column-major order), O(H*W) — a few ms on a 2048x1185 cell.
    """
    m = ink > 0
    h, w = m.shape
    if h == 0 or w == 0:
        return np.zeros_like(m)
    starts = m & ~np.vstack([np.zeros((1, w), bool), m[:-1]])
    run_id = np.cumsum(starts.ravel(order="F")).reshape((h, w), order="F")
    n_runs = int(run_id.max())
    if n_runs == 0:
        return np.zeros_like(m)
    run_id_masked = np.where(m, run_id, 0)
    lengths = np.bincount(run_id_masked.ravel(), minlength=n_runs + 1)
    lengths[0] = 0
    return m & (lengths[run_id_masked] <= max_run) & (run_id_masked > 0)


class _Stroke:
    """One candidate stroke: per-column midline + thickness over a column
    range. Fragments merge by overlaying their columns."""

    __slots__ = ("x0", "x1", "mid", "cnt", "joined")

    def __init__(self, x: int, w: int, mid: np.ndarray, cnt: np.ndarray):
        self.x0 = x
        self.x1 = x + w          # exclusive
        self.mid = mid           # float midline per column, NaN where absent
        self.cnt = cnt           # ink count per column
        self.joined = False      # True when built by _join_dissolved

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    def end_y(self, left: bool, sp: float) -> float:
        """Median midline height over the outermost ~0.25 spaces of columns."""
        n = max(1, int(round(0.25 * sp)))
        seg = self.mid[:n] if left else self.mid[-n:]
        seg = seg[~np.isnan(seg)]
        return float(np.median(seg)) if seg.size else float("nan")

    def merged(self, other: "_Stroke") -> "_Stroke":
        x0 = min(self.x0, other.x0)
        x1 = max(self.x1, other.x1)
        mid = np.full(x1 - x0, np.nan)
        cnt = np.zeros(x1 - x0)
        for s in (self, other):
            sl = slice(s.x0 - x0, s.x1 - x0)
            take = ~np.isnan(s.mid)
            mid[sl] = np.where(take, s.mid, mid[sl])
            cnt[sl] = np.maximum(cnt[sl], s.cnt)
        return _Stroke(x0, x1 - x0, mid, cnt)


def _extract_strokes(thin: np.ndarray, sp: float,
                     edge_margin: int) -> tuple[list[_Stroke], list[_Stroke]]:
    """Connected components of the thin mask -> strokes.

    Returns (usable, cut): `cut` strokes touch the crop's top or bottom —
    they are recorded so chaining can refuse a chain that includes one, and
    are never emitted themselves.
    """
    num, labels, stats, _ = cv2.connectedComponentsWithStats(
        thin.astype(np.uint8), connectivity=8)
    H, _W = thin.shape
    usable: list[_Stroke] = []
    cut: list[_Stroke] = []
    min_w = max(3, int(round(ARC_FRAGMENT_MIN_WIDTH_SPACES * sp)))
    for i in range(1, num):
        x, y, w, h, _a = stats[i]
        if w < min_w:
            continue
        comp = labels[y:y + h, x:x + w] == i
        cnt = comp.sum(axis=0).astype(float)
        have = cnt > 0
        mid = np.full(w, np.nan)
        ys_sum = (comp * np.arange(h)[:, None]).sum(axis=0)
        mid[have] = ys_sum[have] / cnt[have] + y
        s = _Stroke(int(x), int(w), mid, cnt)
        if y <= edge_margin or y + h >= H - edge_margin:
            cut.append(s)
        else:
            usable.append(s)
    return usable, cut


def _chain_strokes(strokes: list[_Stroke], sp: float) -> list[_Stroke]:
    """Merge fragments whose facing ends continue each other."""
    max_gap = ARC_CHAIN_MAX_GAP_SPACES * sp
    max_dy = ARC_CHAIN_MAX_DY_SPACES * sp
    strokes = sorted(strokes, key=lambda s: s.x0)
    changed = True
    while changed:
        changed = False
        out: list[_Stroke] = []
        used = [False] * len(strokes)
        for i, s in enumerate(strokes):
            if used[i]:
                continue
            cur = s
            for j in range(i + 1, len(strokes)):
                if used[j]:
                    continue
                t = strokes[j]
                gap = t.x0 - cur.x1
                if gap > max_gap:
                    break
                # facing ends: cur's right against t's left. Overlapping
                # fragments are two strokes stacked (e.g. a stroke and its
                # shadow), not one cut arc — only join across a genuine cut.
                if gap < -0.25 * sp:
                    continue
                dy = abs(cur.end_y(False, sp) - t.end_y(True, sp))
                if np.isnan(dy) or dy > max_dy:
                    continue
                cur = cur.merged(t)
                used[j] = True
                changed = True
            out.append(cur)
            used[i] = True
        strokes = sorted(out, key=lambda s: s.x0)
    return _join_dissolved(strokes, sp)


def _join_dissolved(strokes: list[_Stroke], sp: float) -> list[_Stroke]:
    """Second-phase join across long dissolved gaps — see ARC_JOIN_*."""
    min_w = ARC_JOIN_MIN_FRAG_SPACES * sp
    max_gap = ARC_JOIN_MAX_GAP_SPACES * sp
    tol = ARC_JOIN_PRED_TOL_SPACES * sp
    strokes = sorted(strokes, key=lambda s: s.x0)
    changed = True
    while changed:
        changed = False
        for i, cur in enumerate(strokes):
            if cur.width < min_w:
                continue
            have = ~np.isnan(cur.mid)
            if have.sum() < 6:
                continue
            xs = np.flatnonzero(have).astype(float) + cur.x0
            ms = cur.mid[have]
            A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
            coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
            best = None
            for j, t in enumerate(strokes):
                if j == i or t.width < min_w:
                    continue
                gap = t.x0 - cur.x1
                if not (0 < gap <= max_gap):
                    continue
                t_have = ~np.isnan(t.mid)
                if not t_have.any():
                    continue
                # the right piece's opening span, against the left's curve
                n = max(1, min(int(round(sp)), int(t_have.sum())))
                t_xs = (np.flatnonzero(t_have).astype(float) + t.x0)[:n]
                t_ms = t.mid[t_have][:n]
                pred = coef[0] * t_xs ** 2 + coef[1] * t_xs + coef[2]
                err = float(np.sqrt(np.mean((pred - t_ms) ** 2)))
                if err <= tol and (best is None or gap < best[0]):
                    best = (gap, j)
            if best is not None:
                j = best[1]
                merged = cur.merged(strokes[j])
                merged.joined = True
                strokes = [s for k, s in enumerate(strokes) if k not in (i, j)]
                strokes.append(merged)
                strokes.sort(key=lambda s: s.x0)
                changed = True
                break
    return strokes


def _gate_stroke(s: _Stroke, sp: float) -> dict | None:
    """Apply the arc gates to one chained stroke; None when refused."""
    w = s.width
    if w < ARC_MIN_WIDTH_SPACES * sp:
        return None
    have = ~np.isnan(s.mid)
    n_cols = int(have.sum())
    min_cov = ARC_MIN_COVERAGE_JOINED if s.joined else ARC_MIN_COVERAGE
    if n_cols < 4 or n_cols / w < min_cov:
        return None
    xs = np.flatnonzero(have).astype(float)
    ms = s.mid[have]
    A = np.vstack([xs ** 2, xs, np.ones_like(xs)]).T
    coef, *_ = np.linalg.lstsq(A, ms, rcond=None)
    resid = float(np.sqrt(np.mean((A @ coef - ms) ** 2)))
    if resid > ARC_MAX_FIT_RESID_SPACES * sp:
        return None
    chord = np.interp(xs, [xs[0], xs[-1]], [ms[0], ms[-1]])
    dev = ms - chord
    rise = float(np.max(np.abs(dev)))
    # An arc cut at the barline is HALF an arch, and half an arch's chord
    # deviation under-reads its curvature about 4x — so the fitted quadratic's
    # own deviation over the stroke's width stands in wherever it is larger.
    curve_rise = float(abs(coef[0]) * w ** 2 / 8.0)
    if max(rise, curve_rise) < ARC_MIN_RISE_SPACES * sp:
        return None
    pos = float(np.sum(np.clip(dev, 0, None)))
    neg = float(np.sum(np.clip(-dev, 0, None)))
    if max(pos, neg) / max(1e-6, pos + neg) < ARC_MIN_SIDE_FRACTION:
        return None
    y0 = float(np.min(ms - s.cnt[have] / 2.0))
    y1 = float(np.max(ms + s.cnt[have] / 2.0))
    return {"x": s.x0, "y": int(round(y0)), "w": w,
            "h": max(1, int(round(y1 - y0))), "rise": rise,
            "mid_mean": float(np.mean(ms))}


def detect_arcs(cell) -> list[LineDetection]:
    """Find slur/tie arcs in `cell` by stroke geometry. See module docstring."""
    if cell is None:
        return []
    src = (cell.image_no_staff
           if getattr(cell, "image_no_staff", None) is not None
           else getattr(cell, "image", None))
    if src is None or getattr(src, "size", 0) == 0:
        return []
    sp = _staff_line_spacing(cell)
    if sp <= 1.0:
        return []
    ink = _binary_ink(src)
    thin = _thin_run_mask(ink, max(2, int(round(ARC_THIN_RUN_MAX_SPACES * sp))))
    usable, _cut = _extract_strokes(thin, sp, ARC_EDGE_MARGIN_PX)
    line_ys = getattr(cell, "staff_line_ys_canonical", None) or []
    staff_bottom = max(line_ys) if len(line_ys) >= 2 else None
    out: list[LineDetection] = []
    for s in _chain_strokes(usable, sp):
        cand = _gate_stroke(s, sp)
        if cand is None:
            continue
        if (staff_bottom is not None
                and cand["mid_mean"] - staff_bottom > ARC_MAX_BELOW_STAFF_SPACES * sp):
            continue
        is_tie = (cand["w"] <= ARC_TIE_MAX_WIDTH_SPACES * sp
                  and cand["rise"] / max(1.0, cand["w"]) <= ARC_TIE_MAX_RISE_RATIO)
        out.append(LineDetection(
            smufl_name="tie" if is_tie else "slur",
            category="structural",
            x_canonical=cand["x"],
            y_canonical=cand["y"],
            width_canonical=cand["w"],
            height_canonical=cand["h"],
            confidence=1.0,
        ))
    return out
