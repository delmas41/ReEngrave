"""Read the bracket at a system's left edge, as an OBJECT.

`system_grouping.gap_bridging_counts` — and the `OMR_BRACKET_COLUMNS` repair on
top of it — never look at the left edge as such: they scan the whole staff
width and ask how much ink crosses each gap.  Family boundaries are then
INFERRED from where the interior barlines stop.  Nothing in this pipeline
detects a bracket; `bracket` is not in the 208-class space either.

This module asks the other question.  At the left edge of a system stand a
small number of tall vertical objects — the systemic barline, the section
brackets, sometimes a brace — and a bracket STATES its block: it begins at the
top line of the block's first staff and ends at the bottom line of its last.
Its endpoints are boundaries directly, with no ratio and no threshold on
incidental ink.

Model-free classical CV on the binarized page.  The search is BOUNDED (a
narrow band at a known x), never erased — the pattern `CLAUDE.md` records for
CV consumers.

⚠️ TWO MEASUREMENT TRAPS, both found the hard way and both handled here.

1. **The closing merges the staff lines.**  `BRIDGE_GAP_TOLERANCE_SPACINGS`
   (0.6) is tuned to bridge a dotted rule; the white gap between two staff
   lines is about 0.8 spacings and the closing kernel is 2*round(0.6*sp)+1,
   which on a 15.75 px spacing is 19 px against a 12.75 px gap.  So every
   column standing INSIDE the staff lines produces one solid run per staff.
   `gap_bridging_counts` never sees this because it only ever looks at the
   band BETWEEN two staves.  A left-edge reader does, and the artefact is
   indistinguishable from a one-staff bracket.

2. **A stroke that crosses no gap cannot be evidence either way.**  So strokes
   are filtered to those crossing at least one inter-staff gap.  That removes
   trap 1 exactly, and it costs nothing the hypothesis needs: a bracket over a
   single staff crosses no gap, and a single-staff block is not bracketed by
   convention anyway.

⚠️ AND ONE FACT ABOUT THE OBJECT ITSELF.  A bracket block is an ENGRAVING
unit, not an instrument family.  Measured over five publishers
(`benchmarks/omr-bracket-reading-2026-09/FINDINGS.md`): Breitkopf brackets
winds+brass+timpani as ONE block against strings, and Litolff and Simrock
print a SINGLE bracket over the whole orchestra, marking the families only by
stopping the interior barlines.  So this reader answers a NARROWER question
than `_assign_groups` does, and where the page states nothing it says so
rather than guessing.

Nothing in the pipeline consumes this module.  It is a measured signal with no
consumer, in the arrangement `OMR_SLOT_STITCH` and `OMR_CONDENSED_PARTS` sit
in — see the benchmark's FINDINGS.md §Recommendation.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, asdict

import cv2
import numpy as np

# Band around the system's own left edge.  Wide enough to take in a brace
# (which can stand furthest left) without reaching the instrument names.
BAND_LEFT_SPACINGS = 9.0
BAND_RIGHT_SPACINGS = 3.0

# Printed rules break; the same closing `gap_bridging_counts` performs, for the
# same reason (a bracket solid at 300 dpi resolves into a dotted line at 600).
CLOSE_SPACINGS = 0.6

# A run must be at least this tall to be a candidate stroke fragment.
MIN_RUN_SPACINGS = 2.0

# Two runs in adjacent columns belong to one stroke when their IoU reaches
# this.  See `_overlap` for why it is IoU and not containment.
COLUMN_LINK_OVERLAP = 0.7


@dataclass
class Stroke:
    x_left: int
    x_right: int
    x_centre: float
    thickness_px: int
    thickness_spacings: float
    y_top: int
    y_bot: int
    height_spacings: float
    straightness: float
    offset_spacings: float
    n_columns: int


def _column_runs(closed: np.ndarray, min_len: int) -> list[list[tuple[int, int]]]:
    """ALL maximal ink runs per column, as (top, bottom) in band-local y.

    Vectorised: the band is up to 300 x 7000 px and a per-pixel Python loop
    over it cost ~50 s per system on the widest edition.
    """
    h, w = closed.shape
    out: list[list[tuple[int, int]]] = [[] for _ in range(w)]
    b = closed.astype(bool)
    pad = np.zeros((1, w), dtype=np.int8)
    d = np.diff(np.vstack([pad, b.astype(np.int8), pad]), axis=0)
    sy, sx = np.nonzero(d == 1)
    ey, ex = np.nonzero(d == -1)
    order_s = np.lexsort((sy, sx))
    order_e = np.lexsort((ey, ex))
    sy, sx = sy[order_s], sx[order_s]
    ey = ey[order_e]
    keep = (ey - sy) >= min_len
    for x, y0_, y1_ in zip(sx[keep], sy[keep], ey[keep]):
        out[int(x)].append((int(y0_), int(y1_) - 1))
    return out


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Intersection over the SHORTER of two runs.

    ⚠️ IoU WAS TRIED AND IS WORSE, and the two failures pull opposite ways, so
    both are recorded.  Containment alone links a staff-height run into the
    systemic barline's full-height run (it scores 1.00 by containment), and
    the stroke's median y then follows the many short runs rather than the one
    long one — a 6-staff synthetic system reported ONE stroke "covering staves
    2-3".  IoU refuses that link (50/690 = 0.07) and also refuses REAL ones: a
    scanned rule's columns have ragged runs, so at 0.7 IoU a warped bracket
    fragments into two-staff pieces and the reader asserts a boundary at
    nearly every gap — measured on the Peters Bach, where a printed 3|3|3 read
    back as `[0,1,2,3,4,5,6,7,8,9,10]`.

    So the artefact is removed where it comes from instead: a run crossing no
    inter-staff gap is dropped BEFORE linking (see `strokes_at_left_edge`).
    Containment is then safe, because every surviving run is a candidate piece
    of something that spans a gap.
    """
    lo, hi = max(a[0], b[0]), min(a[1], b[1])
    if hi < lo:
        return 0.0
    shorter = min(a[1] - a[0], b[1] - b[0]) + 1
    return (hi - lo + 1) / max(1, shorter)


def strokes_at_left_edge(
    binary: np.ndarray,
    system_staves: list,
    *,
    band_left: float = BAND_LEFT_SPACINGS,
    band_right: float = BAND_RIGHT_SPACINGS,
    require_gap_crossing: bool = True,
) -> tuple[list[Stroke], dict]:
    """Tall vertical strokes standing at this system's left edge.

    `system_staves` are one system's staves, sorted by `top_y`.  Returns the
    strokes (left to right) and the band geometry, so a caller can crop the
    same pixels for a human to look at.
    """
    height, width = binary.shape
    spacing = statistics.median([s.line_spacing_px for s in system_staves]) or 1.0
    anchor = statistics.median([s.x_start for s in system_staves])

    x0 = max(0, int(anchor - band_left * spacing))
    x1 = min(width, int(anchor + band_right * spacing))
    y0 = max(0, system_staves[0].top_y - int(round(spacing)))
    y1 = min(height, system_staves[-1].bottom_y + int(round(spacing)))
    geom = {"x0": x0, "x1": x1, "y0": y0, "y1": y1,
            "spacing": spacing, "anchor": anchor}
    if x1 <= x0 or y1 <= y0:
        return [], geom

    band = (binary[y0:y1, x0:x1] < 128).astype(np.uint8)
    k = max(3, int(round(spacing * CLOSE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    runs = _column_runs(closed, int(round(MIN_RUN_SPACINGS * spacing)))

    gaps = [(a.bottom_y, b.top_y) for a, b in
            zip(system_staves, system_staves[1:])]

    # ⚠️ TRAP 1, removed at the RUN level rather than the stroke level.  A run
    # confined to one staff is the closing bridging that staff's five lines,
    # not a piece of any rule — a printed rule spans its whole block in every
    # column it is inked in.  Dropping it here is what makes containment
    # linking safe (see `_overlap`); dropping it only at the stroke level left
    # it free to be absorbed into a neighbouring rule and corrupt that rule's
    # extent.
    if require_gap_crossing:
        runs = [[r for r in rs
                 if any(r[0] + y0 <= g0 and r[1] + y0 >= g1 for g0, g1 in gaps)]
                for rs in runs]

    # Link runs across adjacent columns into strokes (union-find over runs).
    nodes: list[tuple[int, tuple[int, int]]] = []
    index: list[list[int]] = []
    for x, rs in enumerate(runs):
        index.append([])
        for r in rs:
            index[x].append(len(nodes))
            nodes.append((x, r))
    parent = list(range(len(nodes)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for x in range(len(runs) - 1):
        for i in index[x]:
            for j in index[x + 1]:
                if _overlap(nodes[i][1], nodes[j][1]) >= COLUMN_LINK_OVERLAP:
                    union(i, j)

    comps: dict[int, list[int]] = {}
    for i in range(len(nodes)):
        comps.setdefault(find(i), []).append(i)

    strokes: list[Stroke] = []
    for members in comps.values():
        xs = sorted({nodes[i][0] for i in members})
        y_top = int(statistics.median([nodes[i][1][0] for i in members])) + y0
        y_bot = int(statistics.median([nodes[i][1][1] for i in members])) + y0
        if require_gap_crossing and not any(
                y_top <= g0 and y_bot >= g1 for g0, g1 in gaps):
            continue
        med = (y_top - y0, y_bot - y0)
        straight = statistics.median(
            [_overlap(med, nodes[i][1]) for i in members])
        strokes.append(Stroke(
            x_left=xs[0] + x0,
            x_right=xs[-1] + x0,
            x_centre=(xs[0] + xs[-1]) / 2.0 + x0,
            thickness_px=xs[-1] - xs[0] + 1,
            thickness_spacings=round((xs[-1] - xs[0] + 1) / spacing, 3),
            y_top=y_top,
            y_bot=y_bot,
            height_spacings=round((y_bot - y_top + 1) / spacing, 2),
            straightness=round(straight, 3),
            offset_spacings=round(
                ((xs[0] + xs[-1]) / 2.0 + x0 - anchor) / spacing, 2),
            n_columns=len(xs),
        ))
    strokes.sort(key=lambda s: (s.x_left, s.y_top))
    return strokes, geom


# ── Which staves a stroke covers ─────────────────────────────────────────────
# A bracket runs from the TOP LINE of its block's first staff to the BOTTOM
# LINE of its last.  Real ink overshoots (the terminals curl outward) and a
# scan's warp moves both ends, so coverage is decided by overlap rather than by
# matching endpoints exactly.
def covered_staves(stroke: Stroke, system_staves: list) -> list[int]:
    """Indices (within the system) of the staves this stroke runs beside.

    A staff counts as covered when the stroke overlaps most of its height — a
    stroke that merely grazes a staff's top line is not bracketing it.
    """
    out = []
    for i, s in enumerate(system_staves):
        lo = max(stroke.y_top, s.top_y)
        hi = min(stroke.y_bot, s.bottom_y)
        if hi - lo >= 0.6 * (s.bottom_y - s.top_y):
            out.append(i)
    return out


def stroke_dict(s: Stroke) -> dict:
    return asdict(s)


# ── From strokes to a bracket READING ────────────────────────────────────────

# A rule wider than this is not a printed rule — it is a beam, a clef body or a
# blob of music ink reaching left of the staff.  Measured over 380 strokes on
# five publishers: rules run 0.28-1.62 staff spacings, the junk 2.2-3.5.
MAX_RULE_THICKNESS_SPACINGS = 1.75

# A printed rule is straight.  `Stroke.straightness` is the median agreement
# between each column's run and the stroke's median run, so a rule scores ~1.0
# and a curve much less.
MIN_RULE_STRAIGHTNESS = 0.85

# Rules standing at the same x are one NESTING LEVEL — the brackets of one
# depth, or the braces of the next.  Same tolerance, for the same "is this the
# same column" question, as `system_grouping.BRACKET_COLUMN_TOL_SPACINGS`.
# ⚠️ Not wider: the section brackets and the systemic barline stand about 1.1
# staff spacings apart on the Peters Bach, so a 1.5-spacing tolerance folds
# them into one level.
LEVEL_TOL_SPACINGS = 0.75


def is_rule(st: Stroke) -> bool:
    return (st.thickness_spacings <= MAX_RULE_THICKNESS_SPACINGS
            and st.straightness >= MIN_RULE_STRAIGHTNESS)


def _levels(rules: list[Stroke], spacing: float) -> list[list[Stroke]]:
    """Group rules into nesting levels by x."""
    out: list[list[Stroke]] = []
    tol = LEVEL_TOL_SPACINGS * spacing
    for st in sorted(rules, key=lambda s: s.x_centre):
        if out and st.x_centre - out[-1][-1].x_centre <= tol:
            out[-1].append(st)
        else:
            out.append([st])
    return out


def read_brackets(binary: np.ndarray, system_staves: list) -> dict:
    """What the left edge of this system STATES about its blocks.

    Returns a dict with

        blocks       list of staff-index lists, or None when nothing is stated
        boundaries   gap indices the brackets assert a boundary AT
        interior     gap indices the brackets assert are NOT boundaries
        verdict      'no_rule'       nothing rule-shaped at the left edge
                     'spanning_only' one bracket over the whole system — it
                                     states that there are no BRACKET
                                     boundaries, and nothing about families
                     'partial'       rules that stop; blocks are stated
        levels       every nesting level, for a caller that wants braces too

    ⚠️ `interior` is the half worth having and the half a boundary-only
    reading throws away: a bracket running PAST a gap is positive evidence
    that the gap is not a block edge — evidence the barline-stop rule cannot
    supply, since incidental ink can only push its count UP.
    """
    n = len(system_staves)
    spacing = statistics.median([s.line_spacing_px for s in system_staves]) or 1.0
    strokes, geom = strokes_at_left_edge(binary, system_staves)
    rules = [s for s in strokes if is_rule(s)]
    base: dict = {"blocks": None, "boundaries": [], "interior": [],
                  "levels": [], "geom": geom, "n_staves": n}

    if not rules:
        return {**base, "verdict": "no_rule"}

    levels = []
    for lv in _levels(rules, spacing):
        covers = [c for c in (covered_staves(s, system_staves) for s in lv) if c]
        levels.append({
            "x_centre": round(statistics.median([s.x_centre for s in lv]), 1),
            "offset_spacings": round(
                statistics.median([s.offset_spacings for s in lv]), 2),
            "covers": covers,
            "n_partial": sum(1 for c in covers if len(c) < n),
            "n_spanning": sum(1 for c in covers if len(c) == n),
            "staves_covered": len({i for c in covers if len(c) < n for i in c}),
        })
    base["levels"] = levels

    # ⚠️ WHICH LEVEL IS THE BRACKET is decided by REACH, not by x.  A brace and
    # a bracket both stand at the left edge and both are thin straight rules,
    # and the brace is not reliably on either side: on Bach / Peters the
    # section brackets stand LEFT of the systemic barline, on the Mahler scan
    # the brace stands left of the bracket.  What separates them is what they
    # account for — a brace groups a pair of staves, a bracket a section, so
    # the bracket level covers most of the system and the brace level a small
    # fraction of it.  Choosing by BLOCK COUNT first was measured and refused:
    # it read Brahms's braces as the bracket level on 6 of 24 systems (blocks
    # [3,4,5] against the printed 9|5), because a page whose brace pairs
    # happen to be fewer than its bracket blocks wins the wrong tie.
    # ⚠️ A SPANNING rule inside a level is DROPPED, not a disqualification —
    # exactly what `system_grouping.systemic_column_counts` does with a cluster
    # crossing every gap, and for the same reason: an object drawn through the
    # whole system distinguishes no gap from any other.  Disqualifying the
    # level instead was measured and refused: the systemic barline stands
    # within a spacing of the section brackets, so on a clean page it took the
    # brackets down with it and the reading came back `spanning_only`.
    cands = [lv for lv in levels if lv["n_partial"] >= 2]
    if not cands:
        if any(lv["n_spanning"] for lv in levels):
            return {**base, "verdict": "spanning_only",
                    "interior": list(range(n - 1))}
        return {**base, "verdict": "no_rule"}

    best = max(cands, key=lambda lv: (lv["staves_covered"], -lv["n_partial"]))
    blocks = sorted([c for c in best["covers"] if len(c) < n],
                    key=lambda c: c[0])
    boundaries: list[int] = []
    interior: list[int] = []
    for b in blocks:
        if b[0] > 0:
            boundaries.append(b[0] - 1)
        if b[-1] < n - 1:
            boundaries.append(b[-1])
        interior.extend(range(b[0], b[-1]))
    return {**base, "blocks": blocks, "verdict": "partial",
            "boundaries": sorted(set(boundaries)),
            "interior": sorted(set(interior) - set(boundaries))}
