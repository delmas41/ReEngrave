"""Read the STROKES standing at a system's left edge, as objects.

The incumbent (`system_grouping.gap_bridging_counts`, and the
`OMR_BRACKET_COLUMNS` repair on top of it) never looks at the left edge as
such: it scans the whole staff width and asks how much ink crosses each gap.
Family boundaries are then INFERRED from where the interior barlines stop.

This module asks the other question. At the left edge of a system stand a
small number of tall vertical objects — the systemic barline, the family
brackets, sometimes a brace — and a bracket STATES its family: it begins at
the top line of the family's first staff and ends at the bottom line of its
last.  Its endpoints would be boundaries directly, with no ratio and no
threshold on incidental ink.

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
   single staff crosses no gap, and a single-staff family is not bracketed by
   convention anyway.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, asdict

import cv2
import numpy as np

# Band around the system's own left edge.  Wide enough to take in a brace
# (which stands furthest left) without reaching the instrument names.
BAND_LEFT_SPACINGS = 9.0
BAND_RIGHT_SPACINGS = 3.0

# Printed rules break; the same closing `gap_bridging_counts` performs, for the
# same reason (a bracket solid at 300 dpi resolves into a dotted line at 600).
CLOSE_SPACINGS = 0.6

# A run must be at least this tall to be a candidate stroke fragment.
MIN_RUN_SPACINGS = 2.0

# Two runs in adjacent columns belong to one stroke when they overlap by this
# fraction of the shorter one.
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
    """ALL maximal ink runs per column, as (top, bottom) in band-local y."""
    h, w = closed.shape
    out: list[list[tuple[int, int]]] = []
    for x in range(w):
        col = closed[:, x]
        runs: list[tuple[int, int]] = []
        start: int | None = None
        for y in range(h):
            if col[y] and start is None:
                start = y
            elif not col[y] and start is not None:
                if y - start >= min_len:
                    runs.append((start, y - 1))
                start = None
        if start is not None and h - start >= min_len:
            runs.append((start, h - 1))
        out.append(runs)
    return out


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> float:
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

    gaps = [(a.bottom_y, b.top_y) for a, b in
            zip(system_staves, system_staves[1:])]

    strokes: list[Stroke] = []
    for members in comps.values():
        xs = sorted({nodes[i][0] for i in members})
        tops = [nodes[i][1][0] for i in members]
        bots = [nodes[i][1][1] for i in members]
        y_top = int(statistics.median(tops)) + y0
        y_bot = int(statistics.median(bots)) + y0
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
# A bracket runs from the TOP LINE of its family's first staff to the BOTTOM
# LINE of its last.  Real ink overshoots (the terminals curl outward) and a
# scan's warp moves both ends, so coverage is decided by overlap rather than
# by matching endpoints exactly.
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
