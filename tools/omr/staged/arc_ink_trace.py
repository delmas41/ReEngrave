"""ROADMAP 2.272 -- AN ARC TRACED ALONG ITS OWN INK, END TO END, ON THE PAGE (STAGED GATHER; flag `OMR_ARC_INK_TRACE`, default OFF).

Sean 2026-11-03 *"Read once. Claimed once."*, 2026-11-05 *"Arcs should be read page level so they shouldn't be reread and broken up later"*,
*"Often arcs stop short. Closest note works"*; his 2.271 closest-note tiles 2, 4, 5, 9, 10, 12: *"the orange box not capturing the full arc."*

THE CAUSE (2.271 lane, measured here -- `benchmarks/omr-arc-ink-trace-2026-11/FINDINGS.md`). `arcs_system.gather_system_arcs` seeds one trace per DETECTOR
box and lets it run `FREE_EXTEND_SPACES` (0.5 sp) past a box edge the crop did not cut (`CUT_EXTEND_SPACES`, 3 sp, past one it did). The trace is the
DETECTOR'S EXTENT PLUS A MARGIN, not the arc's ink followed to its end; where the detector boxed part of an arc (the box stops at a barline, a
hairpin, a word, a stem) the trace stops there, and every later stage that binds "from the curve's ends" binds from a half arc.

WHAT THIS DOES. After each piece is traced (`trace_arc`, unchanged), each END of it is walked on along the same ink (`arcs_system._follow`, the
stroke follower the trace already uses) until the INK ends, not until a box does. `join_traces` then folds pieces whose extended traces now share
the stroke, as it always did. Rules (CLAUDE §3, claim order):

  * a barline, a stem, a staff line the arc crosses is a CROSSING, not an end: the follower already bridges a column whose run is not a thin stroke
    (a gap of at most `GAP_MAX_SPACES`) and a run merged with something thicker (it keeps the stroke's own height and slope across it);
  * words, dynamics, hairpin legs and beams claim first and keep their ink: a column inside the box of one (or of a non-arc page stroke of the kind
    that makes a hairpin leg or a beam) is bridged on the arc's own predicted curvature and takes nothing from it;
  * another arc's traced run is never followed: reaching one STOPS the walk (`meets_arc`, counted -- two arcs end to end or crossing are never
    guessed, CLAUDE rule 8);
  * the walk stops where the ink does (`gap`), where it climbs steeper than an arc's end does (`slope`, a head's or a stem's outline), at the
    system's edge, or after `EXTEND_CAP_SPACES` (counted);
  * the erase (`OMR_SYSTEM_ARCS_ERASE`) and the detector boxes are untouched: only the curve, its ends and its claimed strokes change.

CONVENTION ASSUMED: an arc's end runs shallow into its note and its stroke is one thin run per column. WHAT WOULD FALSIFY IT: Sean reading a tile
whose box covers the arc's ink as a different arc, or a tail that took a beam / hairpin leg. NOT CONFIRMED: `EXTEND_CAP_SPACES` is a guard set on two
plates, not a measurement; the stop reasons are recorded per end so the cap can be read off the data.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

ENV = "OMR_ARC_INK_TRACE"
#: the farthest one end is walked past where the box trace stopped (spaces). A slur is at most ~25 sp; a half arc is missing a few. A cap is a guard.
EXTEND_CAP_SPACES = 24.0
#: rows around the end the walk may use
ROW_WINDOW_SPACES = 4.0
#: previous columns of the curve that seed the walk's slope
SEED_COLUMNS_SPACES = 1.5
#: detector classes whose ink is claimed before arcs and is never followed
AVOID_PREFIXES = ("dynamic", "artic", "fermata", "ornament", "tuplet", "grace", "tremolo", "fingering", "repeat", "beam")
#: a page stroke of these kinds is a beam / rung / hairpin leg / letter, not an arc, unless it is one of the arc's own
#: (none: a long flat slur's middle is itself a 'horizontal' page stroke -- measured on Litolff p6 -- so the kind says nothing; beams are the detector's
#: own `beam` boxes)
AVOID_STROKE_KINDS: Tuple[str, ...] = ()
#: far-end columns whose centre lies this close (spaces) to a staff line row are the line's stub, not the arc, and are trimmed
LINE_STUB_SPACES = 0.2
#: a 'curve' page stroke this straight (sagitta, spaces) and at least this long (spaces) is a hairpin leg, not an arc
STRAIGHT_SAGITTA_SPACES = 0.08
STRAIGHT_MIN_SPACES = 1.5


def enabled() -> bool:
    return os.environ.get(ENV, "").strip().lower() in ("1", "true", "yes", "on")


def avoid_boxes(named_boxes: Sequence[Tuple[str, Sequence[float]]], page_map: Any, own_ids: Sequence[int], sp: float,
                y_lo: float, y_hi: float, arc_boxes: Sequence[Sequence[float]]) -> List[Tuple[str, Tuple[float, float, float, float]]]:
    """`[(label, (x0, y0, x1, y1))]` of what claimed its ink before the arc, within the curve's rows `y_lo..y_hi` (page px)."""
    out: List[Tuple[str, Tuple[float, float, float, float]]] = []
    for name, b in named_boxes:
        if not str(name).startswith(AVOID_PREFIXES) or b[3] < y_lo or b[1] > y_hi:
            continue
        if str(name).startswith("beam"):
            area = max(1.0, (b[2] - b[0]) * (b[3] - b[1]))
            if any(max(0.0, min(b[2], a[2]) - max(b[0], a[0])) * max(0.0, min(b[3], a[3]) - max(b[1], a[1])) / area >= 0.5 for a in arc_boxes):
                continue            # a beam box that doubles the arc's own box is the arc's twin
        out.append((str(name), (float(b[0]), float(b[1]), float(b[2]), float(b[3]))))
    if page_map is not None:
        own = set(own_ids)
        for i, st in enumerate(page_map.strokes):
            if i in own:
                continue
            x, y, w, h = st.box
            if y + h < y_lo or y > y_hi:
                continue
            if st.kind in AVOID_STROKE_KINDS:
                out.append(("page_stroke:" + st.kind, (float(x), float(y), float(x + w), float(y + h))))
            elif st.kind == "curve" and st.sagitta_sp is not None and st.sagitta_sp <= STRAIGHT_SAGITTA_SPACES and st.length_sp >= STRAIGHT_MIN_SPACES:
                out.append(("page_stroke:straight_curve", (float(x), float(y), float(x + w), float(y + h))))
    return out


def classify_stop(why: str, x: float, y: float, sp: float, ctx: Dict[str, Any]) -> str:
    """What stands at the place the walk stopped: head | stem | barline | word_or_mark:<class> | staff_line | system_edge | meets_arc | ink_end | slope | cap."""
    if why in ("meets_arc", "steep_end"):
        return why
    if why == "limit":
        return ctx.get("limit_kind", "cap")
    r = 1.0 * sp
    for hg, hb in ctx.get("heads", ()):
        if hb[0] - 1.6 * sp <= x <= hb[2] + 1.6 * sp and hb[1] - 2.5 * sp <= y <= hb[3] + 2.5 * sp:
            return "head"
    for sb in ctx.get("stems", ()):
        if sb[0] - r <= x <= sb[2] + r and sb[1] - r <= y <= sb[3] + r:
            return "stem"
    for bx in ctx.get("barlines", ()):
        if bx[0] - r <= x <= bx[2] + r and bx[1] - r <= y <= bx[3] + r:
            return "barline"
    for name, ab in ctx.get("avoid", ()):
        if ab[0] - r <= x <= ab[2] + r and ab[1] - r <= y <= ab[3] + r:
            return "word_or_mark:" + name
    for ly in ctx.get("line_ys", ()):
        if abs(ly - y) <= 0.35 * sp:
            return "staff_line"
    return "ink_end"


def extend_ends(ink: np.ndarray, raw: np.ndarray, t: Dict[str, Any], sp: float, *, x_lo: float, x_hi: float,
                avoid: Sequence[Tuple[str, Sequence[float]]], others: Dict[int, List[Tuple[int, int]]], ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Walk both ends of trace `t` (`arcs_system.trace_arc`'s dict) on along their own ink; `t["points"]` / `x0` / `x1` / `y_left` / `y_right` are
    replaced, and `t["ink_ext"]` records per end: columns added, where and why it stopped, and what it crossed. The box-only extent stays on
    `t["ink_ext"]["box_x"]`. A trace with no points is returned as it is."""
    from . import arcs_system as AS
    pts: Dict[int, Tuple[int, int]] = dict(t["points"])
    if not pts:
        return t
    H, W = ink.shape
    xs0 = sorted(pts)
    info: Dict[str, Any] = {"box_x": [xs0[0], xs0[-1]], "left": None, "right": None}
    look = max(3, int(round(0.5 * sp)))
    seed_n = max(look * 2, int(round(SEED_COLUMNS_SPACES * sp)))
    cap = int(round(EXTEND_CAP_SPACES * sp))
    for side, step in (("left", -1), ("right", 1)):
        xs = sorted(pts)
        xe = xs[0] if side == "left" else xs[-1]
        seed_cols = sorted(xs, key=lambda v: abs(v - xe))[:seed_n]
        seed_cols = sorted(seed_cols, key=lambda v: -abs(v - xe))   # farthest first, the end column last (walking order)
        hist0 = [(x, sum(pts[x]) / 2.0) for x in seed_cols]
        yc = sum(pts[xe]) / 2.0
        r0, r1 = max(0, int(yc - ROW_WINDOW_SPACES * sp)), min(H, int(yc + ROW_WINDOW_SPACES * sp) + 1)
        cols = AS._Columns(ink, r0, r1, AS.STROKE_MAX_SPACES * sp, raw, (AS.STROKE_MAX_SPACES + AS.RAW_LINE_ALLOWANCE_SPACES) * sp)
        limit = min(x_hi, xe + cap) if step > 0 else max(x_lo, xe - cap)
        limit_kind = "cap"
        if (step > 0 and limit == x_hi and x_hi <= xe + cap) or (step < 0 and limit == x_lo and x_lo >= xe - cap):
            limit_kind = "system_edge"
        new: Dict[int, Tuple[int, int]] = {xe: pts[xe]}
        for x in seed_cols[-look:]:
            new[x] = pts[x]
        raw_pts: set = set()
        stop: Dict[str, Any] = {}
        gaps: List[Tuple[int, str]] = []
        av = [b for _n, b in avoid]
        AS._follow(cols, xe, yc, step, int(limit), sp, new, (xs[0], xs[-1]), raw_pts, hist0=hist0, stop=stop, avoid=av, others=others, gaps=gaps)
        for order in (sorted(new), sorted(new, reverse=True)):      # a raw-only point at the far end is a line, not the arc
            for xx in order:
                if xx in pts or xx not in raw_pts:
                    break
                del new[xx]
        added = {x: r for x, r in new.items() if x not in pts}
        lys = ctx.get("line_ys", ())
        for xx in sorted(added, reverse=(step > 0)):               # farthest first: trim a staff line's stub off the far end
            yy = sum(added[xx]) / 2.0
            if any(abs(ly - yy) <= LINE_STUB_SPACES * sp for ly in lys):
                del added[xx]
            else:
                break
        if added:
            far = max(added) if step > 0 else min(added)
            # trim the gap columns past the last added point
            gaps = [g for g in gaps if (g[0] > xe and g[0] < far) or (g[0] < xe and g[0] > far)]
            pts.update(added)
            yfar = sum(added[far]) / 2.0
            stop_x = far
        else:
            far, yfar, stop_x = xe, yc, xe
            gaps = []
        why = stop.get("why", "limit")
        c2 = dict(ctx)
        c2["limit_kind"] = limit_kind
        c2["avoid"] = [(n, b) for n, b in avoid]
        kind = classify_stop(why, float(stop.get("x", stop_x)), yfar, sp, c2)
        crossed: Dict[str, int] = {}
        for gx, gk in gaps:
            label = "word_or_mark" if gk == "avoid" else classify_crossing(gx, yfar, sp, c2)
            crossed[label] = crossed.get(label, 0) + 1
        info[side] = dict(added_px=len(added), x=int(far), y=round(yfar, 1), stop=kind, raw_stop=why,
                          crossed=crossed)
    out = AS._finish(pts, t["coverage"])
    t.update(points=out["points"], x0=out["x0"], x1=out["x1"], y_left=out["y_left"], y_right=out["y_right"], ink_ext=info)
    return t


def classify_crossing(x: float, y: float, sp: float, ctx: Dict[str, Any]) -> str:
    """What a bridged gap column crossed (a count, not a decision): barline | stem | staff_line | head | gap."""
    r = 0.6 * sp
    for bx in ctx.get("barlines", ()):
        if bx[0] - r <= x <= bx[2] + r and bx[1] - r <= y <= bx[3] + r:
            return "barline"
    for sb in ctx.get("stems", ()):
        if sb[0] - r <= x <= sb[2] + r and sb[1] - sp <= y <= sb[3] + sp:
            return "stem"
    for hg, hb in ctx.get("heads", ()):
        if hb[0] - r <= x <= hb[2] + r and hb[1] - r <= y <= hb[3] + r:
            return "head"
    for ly in ctx.get("line_ys", ()):
        if abs(ly - y) <= 0.35 * sp:
            return "staff_line"
    return "gap"
