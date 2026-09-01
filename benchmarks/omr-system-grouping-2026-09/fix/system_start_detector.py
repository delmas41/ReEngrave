"""Phase-1 prototype: positive system-START cues, measured — never a live edit.

Three barline-independent left-anchored cues, each turning "does a new system
start at staff i?" into evidence, plus the raw measurements used to decide
between them:

  A. left_barline_crossing(gap)  — systemic-barline column continuity. Count
     crossing columns in a NARROW band at the page's median x_start (the shared
     left edge). Present at every interior gap (barline runs the system height),
     ~0 at a system boundary. This is the positive inverse of "a system starts
     where the left column stops".

  B. clef_header_starts(staff)   — clef-header column. Detect a clef-sized ink
     cluster in the header band just right of the staff's left edge. A run of
     consecutive staves that all carry one = a system; only DETECTION, no clef
     classification.

  C. bracket_restart(gap)        — left-margin bracket stack. Tall vertical ink
     LEFT of x_start (a family bracket spans consecutive staves). A new stack
     whose top begins below the previous stack's bottom = a system start.

Nothing here mutates a Staff or the pipeline. Detectors return per-gap / per-
staff measurements; the scorer composes them.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

import cv2
import numpy as np

# ── shared geometry ───────────────────────────────────────────────────────────


def page_scale(staves) -> tuple[int, int, float]:
    """(median x_start, median x_end, median line spacing) — robust anchors."""
    sp = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    x_start = int(statistics.median([s.x_start for s in staves]))
    x_end = int(statistics.median([s.x_end for s in staves]))
    return x_start, x_end, sp


def _closed_band(binary, top, bot, x0, x1, sp, gap_tol=0.6):
    """Binary band [top:bot, x0:x1] (0=ink), vertical-closed like the live rule,
    returned as a float coverage-per-column vector over [x0:x1)."""
    h, w = binary.shape
    top = max(0, top)
    bot = min(h, bot)
    x0 = max(0, x0)
    x1 = min(w, x1)
    if bot <= top or x1 <= x0:
        return None, (top, bot, x0, x1)
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    k = max(3, int(round(sp * gap_tol)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    return closed.mean(axis=0), (top, bot, x0, x1)


# ── Cue A: systemic-barline column ────────────────────────────────────────────


def left_barline_crossing(binary, staves, i, *, left_sp=1.5, right_sp=1.5,
                          ink_fraction=0.8, gap_tol=0.6) -> int:
    """Number of crossing columns in [x_start-left_sp, x_start+right_sp] over the
    GAP band between staff i and i+1. High at an interior gap (the systemic
    barline runs the system height); ~0 at a system boundary."""
    up, lo = staves[i], staves[i + 1]
    x_start, _, sp = page_scale(staves)
    x0 = int(x_start - left_sp * sp)
    x1 = int(x_start + right_sp * sp)
    top = up.bottom_y + 2
    bot = lo.top_y - 2
    spacing = max(up.line_spacing_px, lo.line_spacing_px)
    cov, _ = _closed_band(binary, top, bot, x0, x1, spacing, gap_tol)
    if cov is None:
        return -1
    return int((cov > ink_fraction).sum())


# ── Cue C: left-margin bracket vertical ink ───────────────────────────────────


def left_margin_vertical_runs(binary, staves, *, left_sp=2.5, right_sp=0.3,
                              ink_fraction=0.6):
    """For each staff, the height (in px) of the tallest vertical ink run in the
    left-margin band [x_start-left_sp, x_start+right_sp], measured over
    [staff.top_y, staff.bottom_y]. A bracket/brace spine makes this ~= staff
    span; blank margin makes it ~0. Returns a per-staff list."""
    x_start, _, sp = page_scale(staves)
    x0 = max(0, int(x_start - left_sp * sp))
    x1 = int(x_start - right_sp * sp)  # strictly LEFT of the staff content
    out = []
    h, w = binary.shape
    x1 = min(w, max(x1, x0 + 1))
    for s in staves:
        top = max(0, s.top_y)
        bot = min(h, s.bottom_y)
        if bot <= top:
            out.append(0.0)
            continue
        band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
        # vertical coverage per column; tallest column's inked fraction * span
        col_cov = band.mean(axis=0)
        out.append(float(col_cov.max()) * (bot - top))
    return out


def bracket_column_present(binary, staves, i, *, left_sp=2.5, right_sp=0.3,
                           ink_fraction=0.6, gap_tol=0.6) -> int:
    """Crossing columns of a vertical structure LEFT of x_start over the gap
    between staff i and i+1 — i.e. does a bracket/brace spine bridge this gap?"""
    up, lo = staves[i], staves[i + 1]
    x_start, _, sp = page_scale(staves)
    x0 = max(0, int(x_start - left_sp * sp))
    x1 = int(x_start - right_sp * sp)
    top = up.bottom_y + 2
    bot = lo.top_y - 2
    spacing = max(up.line_spacing_px, lo.line_spacing_px)
    cov, _ = _closed_band(binary, top, bot, x0, x1, spacing, gap_tol)
    if cov is None:
        return -1
    return int((cov > ink_fraction).sum())


# ── Cue B: clef-header cluster per staff ──────────────────────────────────────


def header_cluster_x(binary, staves, s, *, hdr_left_sp=0.0, hdr_width_sp=6.0,
                     min_ink_frac=0.18):
    """Detect a clef-sized ink cluster in the header band just right of the
    staff's left edge. Returns (has_cluster, cluster_center_x) — center_x is the
    x of the densest header column, for cross-staff alignment. hdr band spans the
    staff's own five lines vertically."""
    x_start, _, sp = page_scale(staves)
    x0 = max(0, int(x_start + hdr_left_sp * sp))
    x1 = int(x_start + hdr_width_sp * sp)
    top = max(0, s.top_y)
    bot = min(binary.shape[0], s.bottom_y)
    if bot <= top or x1 <= x0:
        return False, -1
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    col = band.mean(axis=0)
    if col.max() < min_ink_frac:
        return False, -1
    # densest column in the header = clef body
    return True, int(x0 + int(np.argmax(col)))


# ── raw per-gap measurement bundle ────────────────────────────────────────────


@dataclass
class GapMeasure:
    i: int
    gap_px: int
    wide_bridging: int          # the live rule's count
    left_barline: int           # cue A
    bracket_cross: int          # cue C
    is_gt_break: bool
    existing_break: bool


def measure_page(L, **kw) -> list[GapMeasure]:
    staves = L.staves
    out = []
    for i in range(len(staves) - 1):
        out.append(GapMeasure(
            i=i,
            gap_px=staves[i + 1].top_y - staves[i].bottom_y,
            wide_bridging=L.bridging[i] if i < len(L.bridging) else -1,
            left_barline=left_barline_crossing(L.binary, staves, i,
                                               **{k: v for k, v in kw.items()
                                                  if k in ("left_sp", "right_sp",
                                                           "ink_fraction", "gap_tol")}),
            bracket_cross=bracket_column_present(L.binary, staves, i),
            is_gt_break=(i in L.gt_breaks),
            existing_break=(i in L.existing_breaks),
        ))
    return out
