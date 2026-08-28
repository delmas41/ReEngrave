"""Ink primitives shared by the header readers.

`clef_locator` and `key_signature_locator` face the same picture: a strip at the
start of a staff, on old paper, where the staff lines have survived the upstream
removal and the initial barline sits a few pixels from the first glyph. Both have
to get from that to clean, glyph-sized ink clusters before they can measure
anything, and both must do it identically — a clef and a key signature are
neighbours in the same crop, and two different notions of "what counts as ink"
between them would put the boundary between clef and signature in two places.

These functions were written for the C-clef locator and are unchanged here; this
module is where they live now so there is one copy.

Phase 1's convention holds throughout: in a cell image 255 is paper and 0 is ink,
while in the masks these functions return 255 is ink.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from scipy.ndimage import median_filter

from .types import MeasureCell


@dataclass(frozen=True)
class InkMaskConfig:
    """Thresholds for turning a header crop into glyph ink. Lengths are in
    staff spaces.

    Any object with these three attributes will do — `ClefLocatorConfig`
    carries them itself, so the clef locator passes its own config straight
    through and keeps a single set of knobs.
    """

    vertical_rule_max_width_spaces: float = 0.5   # thinner ⇒ a rule, not a glyph
    vertical_rule_min_height_spaces: float = 2.0
    # A system barline or bracket is heavier than a plain rule and clears the
    # width test, so it is caught by LENGTH instead — it runs the height of the
    # system. Width cannot separate it from a clef's own strokes; length can.
    heavy_rule_max_width_spaces: float = 1.2
    heavy_rule_min_height_spaces: float = 5.0
    min_ink_height_spaces: float = 0.2


DEFAULT_INK_CONFIG = InkMaskConfig()


def strip_vertical_rules(
    mask: np.ndarray, spacing: float, config: InkMaskConfig
) -> np.ndarray:
    """Erase thin, tall vertical runs: the initial barline, the system bracket,
    and any long stem in the header.

    Necessary because the barline at the start of a system sits within a few
    pixels of the clef — far too close for any proximity-based grouping to keep
    them apart, so without this the clef arrives fused to a full-height rule
    and fails every shape test.

    Two signatures, because rules come in two weights. A plain barline is
    identified by **thinness**: a fraction of a staff space wide, where the
    narrowest part of a clef is comfortably wider. A system barline or bracket
    is heavier than that and clears the width test, so it is identified by
    **length** instead — it runs the full height of the system, joining staff
    to staff, and nothing that long belongs to a C clef. Note the clef's own
    vertical strokes are similar in width to a heavy rule and must survive, so
    width alone cannot separate them; length can.
    """
    tall = max(3, int(round(config.vertical_rule_min_height_spaces * spacing)))
    vert = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, tall))
    )
    n, labels, stats, _ = cv2.connectedComponentsWithStats(vert, connectivity=8)
    thin_w = config.vertical_rule_max_width_spaces * spacing
    heavy_w = config.heavy_rule_max_width_spaces * spacing
    heavy_h = config.heavy_rule_min_height_spaces * spacing
    rules = np.zeros_like(mask)
    for i in range(1, n):
        w_i = stats[i, cv2.CC_STAT_WIDTH]
        h_i = stats[i, cv2.CC_STAT_HEIGHT]
        if w_i <= thin_w or (w_i <= heavy_w and h_i >= heavy_h):
            rules[labels == i] = 255
    # Grow slightly so the rule's soft edges go too, instead of surviving as a
    # hairline that still bridges the clef to whatever is beside it.
    rules = cv2.dilate(rules, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)))
    return cv2.subtract(mask, rules)


def strip_horizontal_rules(mask: np.ndarray, spacing: float) -> np.ndarray:
    """Erase long horizontal runs — staff lines, and whatever the upstream
    staff-line removal left behind.

    Opening with a wide, one-pixel-tall kernel keeps only ink belonging to a
    run at least 1.5 staff spaces long, which no part of a clef is: even a
    broad archaic C clef's bars are about one space wide. The dilation clears
    anti-aliased edges that would otherwise survive as a dotted line and
    re-bridge the glyphs the stripping was meant to separate.
    """
    k = max(3, int(round(1.5 * spacing)))
    horiz = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))
    )
    horiz = cv2.dilate(horiz, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    return cv2.subtract(mask, horiz)


def drop_flat_residue(mask: np.ndarray, spacing: float, config: InkMaskConfig) -> np.ndarray:
    """Remove ink with no vertical substance — the dashes and hairlines that a
    staff line leaves once its long runs have been cut out.

    Without this the fragments act as stepping stones: each is individually
    tiny, but strung together they connect the clef to the barline, to the key
    signature, and to the first notehead, and the glyph never appears as a
    cluster of its own. Opening with a one-pixel-wide, short vertical kernel
    keeps only ink belonging to a vertical run of at least
    `min_ink_height_spaces`, which every stroke of a clef satisfies and no
    remnant of a line does.
    """
    k = max(3, int(round(config.min_ink_height_spaces * spacing)))
    return cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k))
    )


def ink_mask(
    cell: MeasureCell, spacing: float, config: InkMaskConfig
) -> np.ndarray | None:
    """Binary ink mask (255 = ink) for the cell, with rules removed.

    Starts from the staff-line-removed variant when there is one, but does not
    rely on it: on old engravings with thick, uneven lines it leaves most of
    the staff behind — which is exactly the material this locator exists for.
    Vertical rules go first, while the barline is still whole; stripping the
    horizontals first would cut it into short pieces that no longer look like
    a rule.
    """
    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    # Phase 1 convention: 255 = paper, 0 = ink.
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    mask = strip_vertical_rules(mask, spacing, config)
    mask = strip_horizontal_rules(mask, spacing)
    return drop_flat_residue(mask, spacing, config)


def staff_metrics(cell: MeasureCell) -> tuple[float, float, float] | None:
    """(line_spacing, top_line_y, bottom_line_y) in canonical pixels, or None
    when the cell has no usable 5-line staff."""
    ys = cell.staff_line_ys_canonical
    if not ys or len(ys) != 5:
        return None
    s = sorted(float(y) for y in ys)
    gaps = [s[i + 1] - s[i] for i in range(4)]
    spacing = sum(gaps) / len(gaps)
    if spacing <= 0:
        return None
    return spacing, s[0], s[-1]


def cluster_components(
    boxes: list[tuple[int, int, int, int, int]], max_gap: float
) -> list[tuple[int, int, int, int]]:
    """Merge components into glyph-sized clusters by horizontal proximity.

    An archaic C clef is drawn as a stack of separate bars, and stripping the
    staff lines cuts even a solid glyph into pieces, so a clef is routinely
    several components that belong together. Grouping by x-gap rejoins them
    without assuming how many pieces the engraver — or the morphology — left.

    `boxes` are (x, y, w, h, area); returns merged (x, y, w, h), left to right.
    """
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: b[0])
    clusters: list[list[tuple[int, int, int, int, int]]] = [[ordered[0]]]
    for b in ordered[1:]:
        cur_right = max(c[0] + c[2] for c in clusters[-1])
        if b[0] - cur_right <= max_gap:
            clusters[-1].append(b)
        else:
            clusters.append([b])
    merged: list[tuple[int, int, int, int]] = []
    for cl in clusters:
        x0 = min(c[0] for c in cl)
        y0 = min(c[1] for c in cl)
        x1 = max(c[0] + c[2] for c in cl)
        y1 = max(c[1] + c[3] for c in cl)
        merged.append((int(x0), int(y0), int(x1 - x0), int(y1 - y0)))
    return merged


# ─── tracing the printed staff lines ────────────────────────────────────────
#
# `strip_horizontal_rules` above removes staff lines the generic way — open with
# a wide kernel, subtract what survives. That works when the lines are thin
# relative to the glyphs. On 19th-century prints they are not: measured on
# Beethoven 5 (IMSLP 575951) the printed lines are 0.15–0.31 staff spaces thick,
# against roughly 0.08 for a modern engraving, and they wander by a pixel or two
# across the width of a header. Opening wide enough to catch them takes the
# accidentals with it; opening narrow enough to spare the accidentals leaves the
# lines, and either way the header comes back as one connected mass — connected
# components merge into a single window-spanning blob and a column projection
# finds ink in every column.
#
# So these functions don't guess at the lines: they follow them. The nominal y
# of each line is already known from Phase 1, which is enough to trace the ink
# run at that height column by column, measure how thick the line actually is,
# and erase exactly that band along its real path. What a glyph loses is the
# sliver the line was drawn over, which is all it ever had.


def _nearest_ink_row(window: np.ndarray, target: int) -> np.ndarray:
    """For each column of `window` (a bool array, rows × columns), the row
    nearest `target` that carries ink, or -1 where the column is blank.

    Searched outward from the target rather than by distance transform: the
    window is only a fraction of a staff space tall, so a handful of vectorised
    passes settles it.
    """
    height, width = window.shape
    found = np.full(width, -1, dtype=np.int32)
    for offset in range(height):
        for row in {target - offset, target + offset}:
            if not 0 <= row < height:
                continue
            hit = (found < 0) & window[row]
            found[hit] = row
        if (found >= 0).all():
            break
    return found


def _run_extent(window: np.ndarray, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Top and bottom of the vertical ink run through `rows[x]` in each column.

    Columns with no ink (`rows < 0`) come back as (-1, -1).
    """
    height, width = window.shape
    top = rows.copy()
    bottom = rows.copy()
    live = rows >= 0
    for _ in range(height):
        moved = False
        above = top - 1
        can = live & (above >= 0)
        if can.any():
            step = can.copy()
            step[can] = window[above[can], np.flatnonzero(can)]
            if step.any():
                top[step] -= 1
                moved = True
        below = bottom + 1
        can = live & (below < height)
        if can.any():
            step = can.copy()
            step[can] = window[below[can], np.flatnonzero(can)]
            if step.any():
                bottom[step] += 1
                moved = True
        if not moved:
            break
    return top, bottom


def _line_runs(
    mask: np.ndarray, nominal_y: float, spacing: float, search_spaces: float
):
    """The vertical ink run through each column at the height of one staff
    line: `(top, bottom, live, lo, width)`, or None when too few columns carry
    ink to be tracing a line at all.

    Shared by `trace_staff_line`, which turns the runs into a path to erase
    along, and `measure_staff_line`, which turns them into a description of how
    the line is printed. Both need exactly this much and neither should compute
    it twice — the two must agree on which columns are the line, or a thickness
    and a path measured a moment apart would describe different ink.
    """
    height, width = mask.shape
    lo = int(max(0, nominal_y - search_spaces * spacing))
    hi = int(min(height, nominal_y + search_spaces * spacing + 1))
    if hi - lo < 2:
        return None
    window = mask[lo:hi] > 0
    rows = _nearest_ink_row(window, int(round(nominal_y)) - lo)
    top, bottom = _run_extent(window, rows)
    live = rows >= 0
    if live.sum() < max(3, width // 10):
        return None
    return top, bottom, live, lo, width


# How far above the measured thickness a column's ink run may reach and still
# count as the bare line. A notehead or stem sitting on the line makes a run
# many times taller — but `_run_extent` stops at the search window, so some
# arrive CLIPPED to a plausible-looking height, which is why the half-a-staff-
# space bound used for thickness is too loose to also decide position.
LINE_ONLY_HEIGHT_MULT = 2.0

# Wander is reported at this quantile rather than as a maximum. Over the few
# thousand columns of a staff, a maximum is guaranteed to find the single worst
# artifact: where the printed line drops out, the nearest ink can be a beam or
# a slur passing a third of a staff space away, and that column is thin enough
# to pass every height test while being the wrong ink entirely. Measured on
# Bach WTC p.1, whose lines are straight to within half a pixel, the maximum
# reports 13.5 px and this quantile reports 0.5. A line that genuinely bends
# bends across many columns, so the quantile still sees it: on synthetic lines
# bowed by 3 px and 6 px it returns 3.00 and 6.00.
WANDER_QUANTILE = 99.0


def measure_staff_line(
    mask: np.ndarray, nominal_y: float, spacing: float, search_spaces: float = 0.35
) -> tuple[float, float] | None:
    """Describe how one staff line is actually printed: `(thickness, wander)`
    in pixels, or None when the line cannot be traced.

    `thickness` is how much ink the line occupies — the median run height over
    columns no taller than half a staff space, the same robust estimate
    `trace_staff_line` erases by. `wander` is how far the line departs from
    `nominal_y`, the single row the rest of the pipeline models it as.

    Together they say what modelling this staff as five straight rows costs.
    On a modern engraving the answer is nearly nothing. On the 19th-century
    prints this pipeline exists for it is not: lines run 0.15–0.31 staff spaces
    thick against roughly 0.08 for a modern one, and a removal band sized for
    the modern case leaves most of an old line behind, in pieces, which is the
    difference between a staff that comes off cleanly and one that arrives as
    a single connected mass.
    """
    runs = _line_runs(mask, nominal_y, spacing, search_spaces)
    if runs is None:
        return None
    top, bottom, live, lo, _width = runs

    heights = (bottom - top + 1).astype(float)
    measurable = live & (heights <= 0.5 * spacing)
    if not measurable.any():
        return None
    thickness = float(np.median(heights[measurable]))

    # Position needs the tighter bound: thickness survives contamination by
    # taking a median, a departure-from-nominal figure cannot.
    line_only = live & (heights <= max(2.0, thickness * LINE_ONLY_HEIGHT_MULT))
    if not line_only.any():
        return None
    centres = (top[line_only] + bottom[line_only]) / 2.0 + lo
    wander = float(np.percentile(np.abs(centres - nominal_y), WANDER_QUANTILE))
    return thickness, wander


def trace_staff_line(
    mask: np.ndarray, nominal_y: float, spacing: float, search_spaces: float = 0.35
) -> tuple[np.ndarray, float] | None:
    """Follow one printed staff line across `mask`.

    Returns `(centre_y_per_column, thickness)` — the line's measured path and
    how thick it is printed, both in pixels — or None when there is too little
    ink at that height to trace.

    Thickness is the median of the run heights, taking only runs no more than
    half a staff space tall: a column where a glyph sits on the line has a much
    taller run, and including those would inflate the estimate and erase the
    glyph along with the line.
    """
    traced = _line_runs(mask, nominal_y, spacing, search_spaces)
    if traced is None:
        return None
    top, bottom, live, lo, width = traced
    centres = np.full(width, np.nan)
    centres[live] = (top[live] + bottom[live]) / 2.0 + lo
    runs = (bottom - top + 1).astype(float)
    plausible = runs[live & (runs <= 0.5 * spacing)]
    thickness = float(np.median(plausible)) if plausible.size else 0.12 * spacing

    # Fill the blank columns from their neighbours and take a running median, so
    # a few speckled columns can't kink the path.
    #
    # `median_filter` with an odd window and edge handling is exactly the
    # centre-padded rolling median this used to spell out as a comprehension,
    # and returns bit-identical values — but in C, ~120× faster at page width.
    # That difference is what makes tracing every line of every staff on a page
    # affordable rather than a tripling of Phase 1.
    xs = np.arange(width)
    filled = np.interp(xs, xs[live], centres[live])
    k = max(3, int(round(0.5 * spacing)) | 1)
    smoothed = median_filter(filled, size=k, mode="nearest")
    return smoothed, thickness


def erase_staff_lines(
    mask: np.ndarray,
    staff_line_ys: list[int] | list[float],
    spacing: float,
    *,
    max_bridge_spaces: float = 1.2,
) -> np.ndarray:
    """Erase the printed staff lines from `mask` along their traced paths, and
    give back the glyph ink the erasure cut through.

    The bridging rule is what makes this usable. Ink immediately above AND below
    an erased band means something continues through it — but on a line thicker
    than the band that is true along its whole length, so proximity alone would
    simply redraw the line. What separates the two is how FAR it holds: a glyph
    crosses a staff line over a narrow x-range, while a line's own leftover ink
    crosses for as far as the line runs. Only runs shorter than
    `max_bridge_spaces` are bridged.
    """
    out = mask.copy()
    height, width = mask.shape
    bands: list[tuple[np.ndarray, float]] = []
    for nominal_y in staff_line_ys:
        traced = trace_staff_line(mask, float(nominal_y), spacing)
        if traced is None:
            continue
        path, thickness = traced
        bands.append((path, thickness / 2.0 + max(1.0, 0.06 * spacing)))

    xs = np.arange(width)
    for path, half in bands:
        tops = np.clip(np.floor(path - half).astype(int), 0, height)
        bottoms = np.clip(np.ceil(path + half).astype(int) + 1, 0, height)
        for x in xs:
            out[tops[x] : bottoms[x], x] = 0

    max_run = max(3, int(round(max_bridge_spaces * spacing)))
    for path, half in bands:
        tops = np.clip(np.floor(path - half).astype(int), 0, height)
        bottoms = np.clip(np.ceil(path + half).astype(int) + 1, 0, height)
        crosses = np.zeros(width, dtype=bool)
        for x in xs:
            above = mask[max(0, tops[x] - 3) : tops[x], x]
            below = mask[bottoms[x] : bottoms[x] + 3, x]
            crosses[x] = bool(above.size and below.size and above.max() > 0 and below.max() > 0)
        start = None
        for x in range(width + 1):
            inside = x < width and crosses[x]
            if inside and start is None:
                start = x
            elif not inside and start is not None:
                if x - start <= max_run:
                    for col in range(start, x):
                        out[tops[col] : bottoms[col], col] = 255
                start = None
    return out


def header_ink_mask(
    cell: MeasureCell,
    spacing: float,
    staff_line_ys: list[int] | list[float],
    config: InkMaskConfig = DEFAULT_INK_CONFIG,
) -> np.ndarray | None:
    """Glyph ink for a staff header: vertical rules stripped, staff lines traced
    off, and the flat residue that survives both removed.

    The counterpart to `ink_mask` for callers that know where the staff lines
    are. It starts from the RAW cell image rather than the staff-line-removed
    variant, because on the material this exists for that variant is the problem
    — it leaves most of the line behind, in pieces, which is worse to work with
    than the untouched print.
    """
    img = cell.image
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    mask = strip_vertical_rules(mask, spacing, config)
    mask = erase_staff_lines(mask, staff_line_ys, spacing)
    return drop_flat_residue(mask, spacing, config)


def cluster_components_2d(
    boxes: list[tuple[int, int, int, int, int]],
    max_gap: float,
    min_y_overlap: float = 0.25,
) -> list[tuple[int, int, int, int]]:
    """Merge components into glyph clusters by horizontal proximity AND vertical
    overlap.

    `cluster_components` groups on the x-gap alone, which is right for a clef —
    it is the only thing in its strip, so anything nearby belongs to it. It is
    wrong for a key signature, where the accidentals stand in a column of other
    ink: a flat merges with the stem or ledger fragment directly above it and
    the cluster comes out four staff spaces tall, far too big to be an
    accidental, and is thrown away. Fragments of ONE glyph overlap vertically;
    a glyph and the thing above it do not.

    `min_y_overlap` is a fraction of the shorter box's height. `boxes` are
    (x, y, w, h, area); returns merged (x, y, w, h), left to right.
    """
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: b[0])
    clusters: list[list[tuple[int, int, int, int, int]]] = [[ordered[0]]]
    for b in ordered[1:]:
        current = clusters[-1]
        near = b[0] - max(c[0] + c[2] for c in current) <= max_gap
        overlaps = False
        for c in current:
            top, bottom = max(b[1], c[1]), min(b[1] + b[3], c[1] + c[3])
            shorter = max(1, min(b[3], c[3]))
            if (bottom - top) / shorter >= min_y_overlap:
                overlaps = True
                break
        if near and overlaps:
            current.append(b)
        else:
            clusters.append([b])
    merged: list[tuple[int, int, int, int]] = []
    for cl in clusters:
        x0 = min(c[0] for c in cl)
        y0 = min(c[1] for c in cl)
        x1 = max(c[0] + c[2] for c in cl)
        y1 = max(c[1] + c[3] for c in cl)
        merged.append((int(x0), int(y0), int(x1 - x0), int(y1 - y0)))
    return sorted(merged, key=lambda m: m[0])
