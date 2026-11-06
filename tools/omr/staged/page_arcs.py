"""ROADMAP 2.274 step 1 -- ARCS READ FROM THE PAGE'S INK, ONE RUN EACH, FILED AND NOT YET READ (STAGED GATHER; decides nothing).

    flag `OMR_PAGE_ARCS`, default OFF (allow-list). Files `Q.PAGE_ARC` rows only; NOTHING READS THEM. The exported file is byte-identical with it ON.

WHY (docs/plan-2026-11-06-page-ink-arcs.md). On STAGED an arc's identity is a detector box, and the detector runs per cell, barline to barline, so everything
after it inherits the cut. page-facts (2026-10-30): "a detector box in a cell is only a witness to it, never the mark". This reader starts from the INK.

WHAT IT READS. The page raster the page map is built on (`page_strokes.Assembly.canvas`: each staff's own erased band + the page raster outside, the tilted
barline columns carved) -- the staff lines and barlines are claimed first. CLAIM ORDER (CLAUDE §3): what claims before an arc or is not arc ink is blanked --
the page claims of brackets / clef / key / meter / leading column / words (`Q.CLAIMED_AREA` AREAS, which take the ink COMPONENTS wholly inside them, as
`stroke_owner._areas` does, never the rectangle) and every compact detector mark (heads, ledgers, rests, accidentals, flags, dots, dynamics, fermatas,
articulations ...: their box). Beam and hairpin boxes are NOT blanked as rectangles (a false `beam` box over a slur took half of one). Then:
  1. THIN COLUMN RUNS at ~16 px/sp: a vertical ink run taller than `RUN_MAX_SP` (a stem, a head, a beam end-on) is not arc ink and is a HOLE;
  2. TRACK left to right on each track's own recent slope, bridging a hole up to `GAP_SP` (a carved rule, a blanked stem or head) -- so a run CROSSES a
     barline, a stem and a head without being cut; one column run feeds one track;
  3. SPLIT a track at a bridged hole where its slope turns from one sign to the other (a V at a claimed head: two arcs meeting);
  4. KEEP a track that is long enough, thin, inked over most of its span, smooth (off its own running mean), bowed ONE way, not a stub on a staff-line row,
     and not (longer than 4 sp AND straighter than 0.1 sp: a hairpin leg, a beam or a line).
It reads NO cell and needs no detector pass. Cost: about a second a page.

WHAT IT FILES (`Q.PAGE_ARC`, one row per run, on the page's subject). `value` = `run` (read from the ink alone) | `seeded` (no run existed under a
DETECTOR arc box that a bounded local read of its ink found: the box SEEDED it, so it is not ink-first; counted apart) | `census` (one per page: counts,
seconds, peak memory). `detail`: `ordinal`, `bbox_page_px`, `points` (page px, about one per quarter space), `width_spaces`, `sagitta_spaces` (signed:
positive = the middle is LOWER than the chord), `thickness_spaces`, `resid_spaces`, `inked`, `chord_deg`, `ends` ([[x, y, tangent_deg], [x, y, tangent_deg]],
left then right), `page_strokes` ([[Q.PAGE_STROKE ordinal, share]]: the strokes the run runs along -- what it WOULD claim; nothing is claimed in step 1, so no
`Q.CLAIMED_AREA` row is added), `witnesses` (glyph keys of the detector slur/tie boxes it overlaps, a witness only), `staff` ([system, staff]).
A detector arc box no run witnesses is a `Q.PAGE_ARC` row of value `box_without_run` (its glyph key, box, and `seeded` outcome) so both counts are in the record.

CONVENTIONS ASSUMED / WHAT WOULD FALSIFY / NOT CONFIRMED: the run parameters were tuned four times on Brahms p0 (in-sample) and are NOT confirmed beyond it;
step 1 measures them on other pages (benchmarks/omr-arc-binding-2026-10/page-ink-2026-11/step1/FINDINGS-step1.md). They are lengths in staff spaces
(a convention of the print, not a number fitted to a plate) except the cut-offs named below, which are measurements. Sean's tiles are the judge.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

DERIVED_CHECK = False
ENV = "OMR_PAGE_ARCS"

TARGET_SP_PX = 16.0
RUN_MAX_SP = 0.62         # a column run thicker than this is not arc ink (arc middles ~0.15-0.35 sp; a steep arc end is cut off here)
TOL_SP = 0.30             # how far from the predicted centre the next run may lie
GAP_SP = 1.25             # the widest hole a track bridges (a carved rule ~0.2 sp, a blanked stem ~0.3 sp, a head box ~1.3 sp)
SLOPE_SP = 1.5            # the stretch of its own recent points a track predicts from
MIN_WIDTH_SP = 1.4
MAX_THICK_SP = 0.42       # median run thickness
MIN_INKED = 0.6           # inked columns / span
MAX_CHORD_DEG = 40.0
JAG_SP = 0.08             # rms off the 1-sp running mean
CUSP_SP = 0.75            # the stretch each side of a hole the slope is read over
CUSP_GAP_SP = 0.3         # a bridged hole at least this wide (a blanked head is ~1.2 sp)
CUSP_SLOPE = 0.15         # both sides at least this steep, opposite signs
LINE_STUB_SP = 0.14       # a run whose centre sits this close to a staff line row over most of its length is the eraser's leftover
STRAIGHT_SAG_SP = 0.10    # a run straighter than this ...
STRAIGHT_MAX_SP = 4.0     # ... and longer than this is a line, not an arc
WITNESS_SHARE = 0.5       # a detector arc box witnesses a run when the run covers this share of the box's width inside the box (grown 0.5 sp)
POINT_STEP_SP = 0.25      # one filed point per this many staff spaces

NOT_ARC_SKIP = ("staff", "slur", "tie", "brace", "bracket", "barline", "arpeggiato", "systemicBarline")
CLAIM_OWNERS = ("meter", "clef", "key_signature", "leading_column", "word", "bracket")


def enabled() -> bool:
    """`OMR_PAGE_ARCS` (ROADMAP 2.274 step 1), default OFF: allow-list, so an empty value or a typo cannot switch a document onto an unpriced change."""
    return os.environ.get(ENV, "0").strip().lower() in ("1", "true", "yes", "on")


# ───────────────────────────── 1. the rows the reader needs (any source) ─────────────────────────────

def _cls_of(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value.replace("'", '"'))
        except ValueError:
            return value
    if isinstance(value, (list, tuple)) and value:
        return str(value[0])
    return str(value)


def inputs_from_rows(rows: Sequence[Tuple[str, str, Any, Dict[str, Any]]]
                     ) -> Tuple[List[Tuple[str, List[float]]], List[Tuple[str, List[float]]], List[Dict[str, Any]]]:
    """`(blank_boxes, claim_areas, arc_boxes)` from `(quantity, subject, value, detail)` rows of ONE page: `blank_boxes` = `(class, [x0, y0, x1, y1])` of every
    detector box that is neither an arc nor a staff / brace / barline box nor a long stroke (beam / hairpin); `claim_areas` = `(owner, rect)` of the page
    claims that are not the arc's own; `arc_boxes` = the detector's slur / tie boxes `{subject, cls, box}`."""
    boxes: List[Tuple[str, List[float]]] = []
    areas: List[Tuple[str, List[float]]] = []
    arc_boxes: List[Dict[str, Any]] = []
    for q, subject, value, det in rows:
        det = det or {}
        if q == "glyph_box":
            cls = _cls_of(value)
            bb = det.get("bbox_page_px")
            if not bb:
                continue
            if cls in ("slur", "tie"):
                arc_boxes.append(dict(subject=subject, cls=cls, box=[float(v) for v in bb]))
            elif cls.startswith("beam") or "airpin" in cls:
                continue
            elif not any(cls.startswith(k) for k in NOT_ARC_SKIP):
                boxes.append((cls, [float(v) for v in bb]))
        elif q == "claimed_area" and det.get("owner") in CLAIM_OWNERS and det.get("unit") == "area":
            v = value
            if isinstance(v, str):
                v = json.loads(v)
            areas.append((det["owner"], [float(t) for t in v]))
    return boxes, areas, arc_boxes


# ───────────────────────────── 2. the run reader (pure; page raster in, runs out) ─────────────────────────────

def _column_runs(ink: np.ndarray, max_run: int) -> List[List[Tuple[int, int]]]:
    """Per column: the (top, bottom) ink runs no taller than `max_run`."""
    H, W = ink.shape
    pad = np.zeros((H + 2, W), np.int8)
    pad[1:-1] = ink
    d = np.diff(pad, axis=0)
    out = []
    for x in range(W):
        starts = np.flatnonzero(d[:, x] == 1)
        ends = np.flatnonzero(d[:, x] == -1)
        out.append([(int(a), int(b)) for a, b in zip(starts, ends) if b - a <= max_run])
    return out


def _track(runs: List[List[Tuple[int, int]]], sp: float, W: int) -> List[Dict[str, Any]]:
    tol, gap, look = TOL_SP * sp, int(round(GAP_SP * sp)), SLOPE_SP * sp
    active: List[Dict[str, Any]] = []
    done: List[Dict[str, Any]] = []
    for x in range(W):
        cand = [((a + b - 1) / 2.0, b - a) for a, b in runs[x]]
        preds = []
        for t in active:
            pts = t["pts"]
            lx, ly = pts[-1][0], pts[-1][1]
            k = len(pts) - 1
            while k > 0 and lx - pts[k - 1][0] <= look:
                k -= 1
            slope = (ly - pts[k][1]) / float(lx - pts[k][0]) if lx - pts[k][0] >= 3 else 0.0
            preds.append(ly + slope * (x - lx))
        pairs = []
        for ti, py in enumerate(preds):
            for ci, (cy, th) in enumerate(cand):
                dy = abs(cy - py)
                if dy <= tol + 0.5 * th:
                    pairs.append((dy, ti, ci))
        pairs.sort()
        used_t, used_c = set(), set()
        for dy, ti, ci in pairs:
            if ti in used_t or ci in used_c:
                continue
            used_t.add(ti)
            used_c.add(ci)
            active[ti]["pts"].append((x, cand[ci][0], cand[ci][1]))
        nxt = []
        for ti, t in enumerate(active):
            if ti in used_t or x - t["pts"][-1][0] <= gap:
                nxt.append(t)
            else:
                done.append(t)
        for ci, (cy, th) in enumerate(cand):
            if ci not in used_c:
                nxt.append(dict(pts=[(x, cy, th)]))
        active = nxt
    return done + active


def _split_at_cusps(t: Dict[str, Any], sp: float) -> List[Dict[str, Any]]:
    """Two arcs that meet at a note bridge the blanked head between them and chain into one track; an arc turns smoothly through ONE apex, so where two
    meet the track crosses a HOLE and turns the other way in a V. Split at a bridged hole of at least `CUSP_GAP_SP` where the slope either side has
    opposite signs, each at least `CUSP_SLOPE` steep."""
    p = t["pts"]
    if len(p) < 8:
        return [t]
    x = np.array([q[0] for q in p], float)
    y = np.array([q[1] for q in p], float)
    w = CUSP_SP * sp
    cuts = []
    for i in range(1, len(p)):
        if x[i] - x[i - 1] < CUSP_GAP_SP * sp:
            continue
        lo = int(np.searchsorted(x, x[i - 1] - w))
        hi = int(np.searchsorted(x, x[i] + w, side="right"))
        if i - lo < 3 or hi - i < 3:
            continue
        sl = np.polyfit(x[lo:i], y[lo:i], 1)[0]
        sr = np.polyfit(x[i:hi], y[i:hi], 1)[0]
        if sl * sr < 0 and min(abs(sl), abs(sr)) >= CUSP_SLOPE:
            cuts.append(i)
    if not cuts:
        return [t]
    out, a = [], 0
    for c in cuts:
        out.append(dict(pts=p[a:c]))
        a = c
    out.append(dict(pts=p[a:]))
    return out


def _judge(t: Dict[str, Any], sp: float, lines: np.ndarray, *, min_width_sp: float = MIN_WIDTH_SP, allow_on_line: bool = False
           ) -> Tuple[str, Optional[Dict[str, Any]]]:
    p = np.array(t["pts"], float)
    x, y, th = p[:, 0], p[:, 1], p[:, 2]
    width = x[-1] - x[0] + 1
    if width < min_width_sp * sp:
        return "short", None
    inked = len(np.unique(x)) / width
    if inked < MIN_INKED:
        return "sparse", None
    if np.median(th) > MAX_THICK_SP * sp:
        return "thick", None
    k = max(3, int(round(sp)))
    ys_ = np.convolve(y, np.ones(k) / k, mode="same")
    inner = slice(k, len(y) - k) if len(y) > 2 * k + 2 else slice(0, len(y))
    resid = float(np.sqrt(np.mean((ys_[inner] - y[inner]) ** 2)))
    if resid > JAG_SP * sp:
        return "rough", None
    deg = 4 if width > 8 * sp else 2
    c = np.polyfit(x, y, deg)
    fit = np.polyval(c, x)
    chord = np.degrees(np.arctan2(abs(fit[-1] - fit[0]), width))
    if chord > MAX_CHORD_DEG:
        return "steep", None
    line_y = fit[0] + (fit[-1] - fit[0]) * (x - x[0]) / max(1.0, x[-1] - x[0])
    dev = fit - line_y
    sag = float(dev[np.argmax(np.abs(dev))])
    if len(lines) and not allow_on_line:
        dist = np.min(np.abs(y[:, None] - lines[None, :]), axis=1)
        if np.mean(dist < LINE_STUB_SP * sp) > 0.7:
            return "on_a_line", None
    if abs(sag) < STRAIGHT_SAG_SP * sp and width > STRAIGHT_MAX_SP * sp:
        return "straight", None
    if abs(sag) >= STRAIGHT_SAG_SP * sp:
        inn = np.abs(dev) > 0.03 * sp
        if inn.sum() >= 5 and np.mean(np.sign(dev[inn]) == np.sign(sag)) < 0.85:
            return "two_bows", None
    return "arc", dict(width_sp=round(width / sp, 2), sagitta_sp=round(sag / sp, 3), thick_sp=round(float(np.median(th)) / sp, 3),
                       resid_sp=round(resid / sp, 3), inked=round(inked, 2), chord_deg=round(float(chord), 1))


def blank_mask(ink: np.ndarray, boxes: Sequence[Tuple[str, Sequence[float]]], areas: Sequence[Tuple[str, Sequence[float]]]) -> np.ndarray:
    """What claims first or is not arc ink: the compact detector boxes' rectangles, and the ink COMPONENTS wholly inside a page claim's area (+1 px)."""
    import cv2
    H, W = ink.shape
    blank = np.zeros_like(ink)
    for _cls, (x0, y0, x1, y1) in boxes:
        blank[max(0, int(y0) - 1):min(H, int(np.ceil(y1)) + 1), max(0, int(x0) - 1):min(W, int(np.ceil(x1)) + 1)] = True
    if areas:
        n, lab, st, _c = cv2.connectedComponentsWithStats(ink.astype(np.uint8), connectivity=8)
        take = np.zeros(n, bool)
        bx, by, bw, bh = st[:, 0], st[:, 1], st[:, 2], st[:, 3]
        for _own, (x0, y0, x1, y1) in areas:
            take |= (bx >= x0 - 1) & (by >= y0 - 1) & (bx + bw <= x1 + 1) & (by + bh <= y1 + 1)
        take[0] = False
        blank |= take[lab]
    return blank


def read_runs(canvas: np.ndarray, sp_page: float, line_ys: Sequence[float], boxes: Sequence[Tuple[str, Sequence[float]]],
              areas: Sequence[Tuple[str, Sequence[float]]], *, blank: Optional[np.ndarray] = None) -> Dict[str, Any]:
    """The runs of the page ink (module doc). `canvas`: 0 = ink, page px. Returns `{runs, why, tracks, scale, sp, blanked}`; each run has `pts` (page px,
    ~one per 2 reduced px), `box`, `width_sp`, `sagitta_sp`, `thick_sp`, `resid_sp`, `inked`, `chord_deg`, `half` (half its thickness, page px)."""
    import cv2
    ink = canvas == 0
    if blank is None:
        blank = blank_mask(ink, boxes, areas)
    ink2 = ink & ~blank
    scale = min(1.0, TARGET_SP_PX / sp_page)
    small = cv2.resize(ink2.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else ink2
    sp = sp_page * scale
    cols = _column_runs(small.astype(np.int8), int(round(RUN_MAX_SP * sp)))
    tracks = _track(cols, sp, small.shape[1])
    lines = np.array(sorted(y * scale for y in line_ys))
    tracks = [q for t in tracks for q in _split_at_cusps(t, sp)]
    why: Dict[str, int] = {}
    out: List[Dict[str, Any]] = []
    for t in tracks:
        if len(t["pts"]) < 3:
            why["tiny"] = why.get("tiny", 0) + 1
            continue
        v, info = _judge(t, sp, lines)
        why[v] = why.get(v, 0) + 1
        if v != "arc":
            continue
        out.append(_run_row(t, info, scale, len(out)))
    return dict(runs=out, why=why, tracks=len(tracks), scale=scale, sp=sp, blanked=int(blank.sum()))


def _run_row(t: Dict[str, Any], info: Dict[str, Any], scale: float, ordinal: int) -> Dict[str, Any]:
    p = np.array(t["pts"], float)
    pts = [[round(px / scale, 1), round(py / scale, 1)] for px, py, _ in p[::max(1, int(2 * scale))]]
    pts.append([round(p[-1, 0] / scale, 1), round(p[-1, 1] / scale, 1)])
    xs, ys = p[:, 0] / scale, p[:, 1] / scale
    half = float(p[:, 2].max() / scale / 2)
    info = dict(info)
    info.update(id=ordinal, pts=pts, half=round(half, 1), box=[float(xs.min()), float(ys.min() - half), float(xs.max()), float(ys.max() + half)])
    return info


# ───────────────────────────── 3. witnesses, ends, the detector boxes no run answers ─────────────────────────────

def thin_points(pts: Sequence[Sequence[float]], sp_page: float) -> List[List[float]]:
    """About one point per `POINT_STEP_SP` along x, always keeping the two ends."""
    step = POINT_STEP_SP * sp_page
    out = [list(pts[0])]
    for p in pts[1:-1]:
        if p[0] - out[-1][0] >= step:
            out.append(list(p))
    out.append(list(pts[-1]))
    return out


def ends_of(pts: Sequence[Sequence[float]], sp_page: float) -> List[List[float]]:
    """`[[x, y, tangent_deg], [x, y, tangent_deg]]`, left then right; the tangent is the slope over the last space of the run (positive = running DOWN the page)."""
    a = np.array(pts, float)
    out = []
    for end, sel in ((a[0], a[:, 0] <= a[0, 0] + sp_page), (a[-1], a[:, 0] >= a[-1, 0] - sp_page)):
        s = a[sel]
        sl = float(np.polyfit(s[:, 0], s[:, 1], 1)[0]) if len(s) >= 3 and np.ptp(s[:, 0]) > 1 else 0.0
        out.append([round(float(end[0]), 1), round(float(end[1]), 1), round(float(np.degrees(np.arctan(sl))), 1)])
    return out


def witness_share(pts: np.ndarray, box: Sequence[float], sp_page: float) -> float:
    """The share of the detector box's width that the run covers INSIDE the box grown by half a space (a witness test, not a verdict)."""
    g = 0.5 * sp_page
    x0, y0, x1, y1 = box
    if x1 <= x0:
        return 0.0
    sel = pts[(pts[:, 0] >= x0 - g) & (pts[:, 0] <= x1 + g) & (pts[:, 1] >= y0 - g) & (pts[:, 1] <= y1 + g)]
    if len(sel) < 2:
        return 0.0
    return float(min(sel[:, 0].max(), x1) - max(sel[:, 0].min(), x0)) / (x1 - x0)


def witnesses_of(runs: Sequence[Dict[str, Any]], arc_boxes: Sequence[Dict[str, Any]], sp_page: float
                 ) -> Tuple[Dict[int, List[str]], List[Dict[str, Any]]]:
    """`({run id: [witness subjects]}, [arc boxes no run witnesses])`."""
    by_run: Dict[int, List[str]] = {r["id"]: [] for r in runs}
    pts = {r["id"]: np.array(r["pts"], float) for r in runs}
    alone = []
    for b in arc_boxes:
        hit = False
        for r in runs:
            bb = r["box"]
            g = sp_page
            if bb[2] < b["box"][0] - g or bb[0] > b["box"][2] + g or bb[3] < b["box"][1] - g or bb[1] > b["box"][3] + g:
                continue
            if witness_share(pts[r["id"]], b["box"], sp_page) >= WITNESS_SHARE:
                by_run[r["id"]].append(b["subject"])
                hit = True
        if not hit:
            alone.append(b)
    return by_run, alone


def seed_read(canvas: np.ndarray, sp_page: float, line_ys: Sequence[float], box: Sequence[float], blank: np.ndarray) -> Optional[Dict[str, Any]]:
    """A BOUNDED local read under a detector arc box no run answers (the plan's §3.3 seeded witness): the same tracker on the box grown by `SEED_PAD_SP`,
    with the short-run floor lowered to a tie's and a staff-line row allowed. Returns the run that spans most of the box, or None. Marked `seeded`: the
    box chose where to look, so it is not an ink-first run and is counted apart."""
    import cv2
    H, W = canvas.shape
    pad = SEED_PAD_SP * sp_page
    x0, y0, x1, y1 = max(0, int(box[0] - pad)), max(0, int(box[1] - pad)), min(W, int(box[2] + pad)), min(H, int(box[3] + pad))
    if x1 - x0 < 8 or y1 - y0 < 4:
        return None
    sub = (canvas[y0:y1, x0:x1] == 0) & ~blank[y0:y1, x0:x1]
    scale = min(1.0, TARGET_SP_PX / sp_page)
    small = cv2.resize(sub.astype(np.uint8) * 255, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) > 96 if scale < 1 else sub
    sp = sp_page * scale
    cols = _column_runs(small.astype(np.int8), int(round(RUN_MAX_SP * sp)))
    tracks = [q for t in _track(cols, sp, small.shape[1]) for q in _split_at_cusps(t, sp)]
    lines = np.array(sorted((y - y0) * scale for y in line_ys))
    best, best_w = None, 0.0
    for t in tracks:
        if len(t["pts"]) < 3:
            continue
        v, info = _judge(t, sp, lines, min_width_sp=SEED_MIN_WIDTH_SP, allow_on_line=True)
        if v != "arc":
            continue
        w = (t["pts"][-1][0] - t["pts"][0][0]) / scale
        if w > best_w:
            best, best_w = (t, info), w
    if best is None or best_w < 0.6 * (box[2] - box[0]):
        return None
    t, info = best
    t = dict(pts=[(px + x0 * scale, py + y0 * scale, th) for px, py, th in t["pts"]])
    return _run_row(t, info, scale, -1)


SEED_PAD_SP = 0.5
SEED_MIN_WIDTH_SP = 0.9


# ───────────────────────────── 4. file it ─────────────────────────────

def gather_page_arcs(log: Any, pws: Any, cells: Sequence[Any], local: Dict[int, Tuple[int, int]], page_map: Any, *, progress: bool = False
                     ) -> Optional[Dict[str, Any]]:
    """ROADMAP 2.274 step 1 (flag `OMR_PAGE_ARCS`, default OFF), STAGED GATHER: `Q.PAGE_ARC` (module doc). AFTER the page-wide claims (words, clef / key /
    meter, brackets), the page claim names and the page heads, and after the page beams: the last page-wide reader of ink. Reads rows and the page map's
    canvas; files rows only; decides nothing, claims nothing."""
    if not enabled():
        return None
    from . import record as R
    from .record import Q, READERS, ABSTAIN, Scope
    from .gather import FRAME_PAGE
    from . import run_meter
    p = int(getattr(pws.page, "page_index", 0))
    sub = R.page(p)
    asm = getattr(page_map, "assembly", None)
    canvas = getattr(asm, "canvas", None)
    if page_map is None or canvas is None:
        log.abstain(sub, Q.PAGE_ARC, reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, reason=ABSTAIN.NO_MASK, note="no page stroke map")
        return None
    t0 = time.time()
    rows = []
    for r in log.rows(Q.GLYPH_BOX, sub, scope=Scope.SELF_AND_DESCENDANTS):
        rows.append(("glyph_box", r.subject.to_key() if hasattr(r.subject, "to_key") else str(r.subject), r.value, r.detail))
    for r in log.rows(Q.CLAIMED_AREA, sub, scope=Scope.SELF_AND_DESCENDANTS):
        rows.append(("claimed_area", "", r.value, r.detail))
    boxes, areas, arc_boxes = inputs_from_rows(rows)
    sp_page = float(page_map.sp)
    line_ys = [float(y) for s in pws.staves for y in s.line_ys]
    res = read_runs(canvas, sp_page, line_ys, boxes, areas)
    runs = res["runs"]
    by_run, alone = witnesses_of(runs, arc_boxes, sp_page)
    t_runs = time.time()
    # staff of a run: the staff whose lines are nearest its middle
    staves = list(pws.staves)

    def staff_of(y: float) -> List[int]:
        best = min(staves, key=lambda s: abs((s.line_ys[0] + s.line_ys[-1]) / 2.0 - y))
        return [local.get(best.staff_index, (0, 0))[0], local.get(best.staff_index, (0, 0))[1]]
    from . import arc_claim as _AC
    n = 0
    for r in runs:
        pts = np.array(r["pts"], float)
        thin = thin_points(r["pts"], sp_page)
        trace = {}
        for x, y in pts:
            trace[int(round(x))] = (y - r["half"], y + r["half"])
        along = _AC.page_strokes_along(page_map, trace, sp_page)
        mid_y = float(np.median(pts[:, 1]))
        log.observe(sub, Q.PAGE_ARC, "run", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, ordinal=n, bbox_page_px=[round(v, 1) for v in r["box"]],
                    points=thin, width_spaces=r["width_sp"], sagitta_spaces=r["sagitta_sp"], thickness_spaces=r["thick_sp"], resid_spaces=r["resid_sp"],
                    inked=r["inked"], chord_deg=r["chord_deg"], ends=ends_of(r["pts"], sp_page), page_strokes=[[int(i), s] for i, s in along],
                    witnesses=by_run[r["id"]], staff=staff_of(mid_y))
        n += 1
    blank = None
    n_seeded = 0
    if alone:
        ink = canvas == 0
        blank = blank_mask(ink, boxes, areas)
    for b in alone:
        s = seed_read(canvas, sp_page, line_ys, b["box"], blank)
        if s is not None:
            n_seeded += 1
            log.observe(sub, Q.PAGE_ARC, "seeded", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, ordinal=n, bbox_page_px=[round(v, 1) for v in s["box"]],
                        points=thin_points(s["pts"], sp_page), width_spaces=s["width_sp"], sagitta_spaces=s["sagitta_sp"], thickness_spaces=s["thick_sp"],
                        resid_spaces=s["resid_sp"], inked=s["inked"], chord_deg=s["chord_deg"], ends=ends_of(s["pts"], sp_page), page_strokes=[],
                        witnesses=[b["subject"]], staff=staff_of(float(np.median(np.array(s["pts"])[:, 1]))))
            n += 1
        else:
            log.observe(sub, Q.PAGE_ARC, "box_without_run", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, ordinal=n, bbox_page_px=[round(v, 1) for v in b["box"]],
                        witnesses=[b["subject"]], box_class=b["cls"])
            n += 1
    census = dict(runs=len(runs), seeded=n_seeded, boxes_without_run=len(alone) - n_seeded, arc_boxes=len(arc_boxes),
                  runs_with_witness=sum(1 for v in by_run.values() if v), runs_without_witness=sum(1 for v in by_run.values() if not v),
                  tracks=res["tracks"], rejected=res["why"], blanked_px=res["blanked"], seconds=round(time.time() - t0, 2),
                  seconds_runs=round(t_runs - t0, 2), peak_rss_gb=round(run_meter.peak_rss_bytes() / 1e9, 2))
    log.observe(sub, Q.PAGE_ARC, "census", reader=READERS.CV_PAGE_ARCS, frame=FRAME_PAGE, **census)
    if progress:
        print("  gather page arcs p%s: %s" % (p, census))
    return census


def rows_of(rec: Any, page: Optional[int] = None) -> List[Any]:
    """The record's own `Q.PAGE_ARC` rows (empty when the gather ran with the flag OFF), of `page` when given. The measurement readout reads the record
    through this (benchmarks/omr-arc-binding-2026-10/page-ink-2026-11/step1); no stage reads it in step 1."""
    from .record import Q
    out = []
    for o in rec.obs_of(Q.PAGE_ARC):
        sub = str(getattr(o, "subject", "") or "")
        if page is None or sub == "page/%d" % page or sub.startswith("page/%d/" % page):
            out.append(o)
    return out

