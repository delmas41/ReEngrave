"""Trace the shape around a far head: fit the notehead's own OVAL from its
ink outline (never the detector box), and read ledger lines as bands that
shoot past that oval -- rather than past the box.

Why this exists (ROADMAP shape-trace lane, DECISIONS 2026-10-02): the
round-8 reader's "is there a line at the head's own middle" probe
(`ledger_grid.head_middle_rung_evidence`) always samples at the detector
BOX's naive centre, `(y0 + y1) / 2`. Two heads on the Litolff truth set
(`glyph/3/0/7/0/7`, `glyph/3/0/7/2/4`) abstain with reason
`no_rung_before_the_head` even though geometry and the ledger-measured
reader both already land on the reference position -- every candidate rung
the plain walk found sits at or past the box's near edge, and the box-centre
probe finds no jut there, so `derive_far_head_step` drops each one as "the
head's own outline" and runs out of rungs. The box's naive centre is not
reliably the printed oval's own centre (a box that covers only the top of
a half note, is a half-pixel off after rounding, or is simply the
detector's own imprecise fit), so probing there is probing the wrong row.

This module fixes that by tracing the ink around the head row by row,
fitting the oval from the TRACE (not the box), and classifying each
candidate band against the oval's own fitted extent rather than the box's.
It produces a drop-in replacement evidence function
(`shape_trace_middle_rung_evidence`) with the SAME 4-positional-argument
contract as `ledger_grid.head_middle_rung_evidence` -- `derive_far_head_step`
can take either. Nothing here flips a product default; it is additive and
measured by the harness in `benchmarks/omr-local-staff-2026-09/`.

⚠️ 2026-10-02, manager review of `out/print/ledgers/shape_regressions.jpg`:
the FIRST cut of this module traced the whole CONNECTED ink component
around a head -- on real plate ink that component routinely includes every
staff line the stem crosses and a neighbouring head or printed text fused
to it (tiles 2/5/6 traced along full staff lines; tile 4 fit a tall thin
oval onto the stem; tile 1 fit an oval bigger than the real head and missed
the clear line through its middle). The trace is now LOCAL, not connected-
component: a small window sized from the STANDARD notehead box (ROADMAP
2.39, `tools.omr.staged.geometry.STANDARD_HEAD_WIDTH_SPACES`/
`_HEIGHT_SPACES`), the per-row run nearest the head's own column (never the
whole row), the stem column masked by its own `Q.STEM` box where given (a
heuristic tall-narrow-column fallback otherwise), the staff lines' own rows
masked OUT of the oval fit (never out of ledger detection -- those rows are
inside the staff, ledgers are not), and one re-centring iteration on the
freshly fitted oval.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np

from .ledger_grid import _otsu_threshold
from ..staged.geometry import STANDARD_HEAD_WIDTH_SPACES, STANDARD_HEAD_HEIGHT_SPACES

# A ledger band is at most this many staff spaces tall -- same cap
# `ledger_grid.RUNG_MAX_THICKNESS_SPACES` already uses for a rung's own
# thinness, repeated here because this module reasons about raw traced
# rows rather than a pre-found band.
LEDGER_BAND_MAX_SPACES = 0.35

# A ledger crossing the oval "within its middle" means within this
# fraction of the oval's own fitted height of its fitted centre --
# touching only the oval's top or bottom is the ledger before/after it,
# per the task brief ("+/- ~0.2 of the oval height -- state it").
OVAL_MIDDLE_TOLERANCE_FRACTION = 0.2

# A column whose own longest vertical ink run exceeds this many staff
# spaces is a stem, not part of the oval or a ledger -- a stem runs the
# full distance from the head to a beam/flag, far taller than any oval or
# ledger band. Used only as a FALLBACK where no real `Q.STEM` box is given.
STEM_MIN_RUN_SPACES = 1.3
# ...but only when that tall run's own horizontal footprint is narrow; a
# genuinely wide dark run that happens to be tall (a merged blob) is not a
# stem and must not be masked out.
STEM_MAX_WIDTH_SPACES = 0.24

# The LOCAL window, sized from the standard notehead box (manager review
# 2026-10-02 -- "not connected-component"): columns within this many
# STANDARD head-widths of the head's own column centre...
WINDOW_HALF_WIDTH_HEAD_WIDTHS = 1.5
# ...rows within this many STANDARD head-heights of the head's own
# (provisional, then re-centred) row centre, plus half a staff space.
WINDOW_HALF_HEIGHT_HEAD_HEIGHTS = 0.6
WINDOW_HALF_HEIGHT_EXTRA_SPACES = 0.5

# A row's run is "oval-sized" up to this many STANDARD head-widths; wider
# than that, for up to `LEDGER_BAND_MAX_SPACES` of rows, is a LINE band
# (manager review 2026-10-02's own numbers).
OVAL_ROW_WIDTH_CAP_HEAD_WIDTHS = 1.6

# A row within this many staff spaces of a (locally measured) staff line
# is "on the staff" and excluded from the oval FIT -- never from ledger
# detection, which only ever looks outside the staff anyway.
STAFF_LINE_ROW_TOLERANCE_SPACES = 0.3

# How far a per-row run may sit from the probe column and still count as
# "nearest" (never a genuinely different symbol -- a neighbour head or
# text sitting beyond this is excluded, never bridged).
NEAREST_RUN_MAX_GAP_HEAD_WIDTHS = 0.5


def _row_runs(row_ink: np.ndarray) -> List[Tuple[int, int]]:
    """Contiguous `True` runs in a 1-D boolean row, as [start, end)."""
    runs: List[Tuple[int, int]] = []
    n = len(row_ink)
    i = 0
    while i < n:
        if row_ink[i]:
            j = i
            while j < n and row_ink[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    return runs


def _nearest_run(runs: Sequence[Tuple[int, int]], probe_col: int,
                  max_gap: float) -> Optional[Tuple[int, int]]:
    """The run CONTAINING `probe_col`, or else the NEAREST one within
    `max_gap` columns -- never a run further away (a neighbouring head or
    printed text), which is simply "no ink here" for this head's own
    trace."""
    containing = [r for r in runs if r[0] <= probe_col < r[1]]
    if containing:
        return containing[0]
    best, best_gap = None, None
    for (s, e) in runs:
        gap = (s - probe_col) if probe_col < s else (probe_col - (e - 1))
        if gap <= max_gap and (best_gap is None or gap < best_gap):
            best, best_gap = (s, e), gap
    return best


def _mask_stem_columns(ink: np.ndarray, spacing: float,
                        stem_box: "tuple[float, float, float, float] | None" = None,
                        wx0: int = 0) -> np.ndarray:
    """Zero out the stem column. With `stem_box` (`Q.STEM`'s own
    `[x, y, w, h]`, converted here to an absolute `(x0, y0, x1, y1)` box
    before calling), that EXACT column range is masked -- real evidence,
    never a guess. Without one (no stem quantity on record, or a synthetic
    caller with no record at all), falls back to a heuristic: a column
    band taller than a notehead or ledger could ever be, and narrow.
    Returns a NEW array; `ink` itself is never mutated."""
    h, w = ink.shape
    out = ink.copy()
    if stem_box is not None:
        sx0, sy0, sx1, sy1 = stem_box
        lx0 = max(0, int(round(sx0)) - wx0)
        lx1 = min(w, int(round(sx1)) - wx0 + 1)
        if lx1 > lx0:
            out[:, lx0:lx1] = False
        return out
    max_run = np.zeros(w, dtype=int)
    for c in range(w):
        best = cur = 0
        for v in ink[:, c]:
            if v:
                cur += 1
                if cur > best:
                    best = cur
            else:
                cur = 0
        max_run[c] = best
    is_tall = max_run > STEM_MIN_RUN_SPACES * spacing
    max_stem_w = max(1, int(round(STEM_MAX_WIDTH_SPACES * spacing)))
    c = 0
    while c < w:
        if is_tall[c]:
            c0 = c
            while c < w and is_tall[c]:
                c += 1
            if (c - c0) <= max_stem_w:
                out[:, c0:c] = False
        else:
            c += 1
    return out


def _blank_excluded_boxes(
    ink: np.ndarray, exclude_boxes: Sequence[Tuple[float, float, float, float]],
    wx0: int, wy0: int,
) -> np.ndarray:
    out = ink.copy()
    h, w = out.shape
    for (bx0, by0, bx1, by1) in exclude_boxes or ():
        lx0 = max(0, int(bx0) - wx0)
        lx1 = min(w, int(bx1) - wx0 + 1)
        ly0 = max(0, int(by0) - wy0)
        ly1 = min(h, int(by1) - wy0 + 1)
        if lx1 > lx0 and ly1 > ly0:
            out[ly0:ly1, lx0:lx1] = False
    return out


class ShapeTrace:
    """The result of tracing one head's own ink outline.

    `rows_y`: absolute y for each traced row (ascending).
    `left_x`/`right_x`: absolute x extent of the run nearest the head's own
    centre column, per row (``None`` where that row has no qualifying ink).
    `oval_center_y`, `oval_top_y`, `oval_bottom_y`: fitted from the trace.
    `oval_half_width`: the oval's own measured half-width (used to decide
    whether a row's run protrudes PAST it).
    `ledger_bands`: list of dicts `{y, left_x, right_x, sides}` -- one per
    detected ledger band, ordered by y.
    """

    def __init__(self, rows_y, left_x, right_x, oval_center_y, oval_top_y,
                 oval_bottom_y, oval_half_width, ledger_bands):
        self.rows_y = rows_y
        self.left_x = left_x
        self.right_x = right_x
        self.oval_center_y = oval_center_y
        self.oval_top_y = oval_top_y
        self.oval_bottom_y = oval_bottom_y
        self.oval_half_width = oval_half_width
        self.ledger_bands = ledger_bands


def _trace_window(img_gray, cx, cy, spacing, exclude_boxes, stem_box):
    """One pass: extract the LOCAL window around `(cx, cy)`, trace rows,
    return `(rows_y, left_x, right_x, widths, wx0)`."""
    h, w = img_gray.shape
    head_w = STANDARD_HEAD_WIDTH_SPACES * spacing
    head_h = STANDARD_HEAD_HEIGHT_SPACES * spacing
    half_w = WINDOW_HALF_WIDTH_HEAD_WIDTHS * head_w
    half_h = (WINDOW_HALF_HEIGHT_HEAD_HEIGHTS * head_h
              + WINDOW_HALF_HEIGHT_EXTRA_SPACES * spacing)

    wx0 = max(0, int(round(cx - half_w)))
    wx1 = min(w, int(round(cx + half_w)))
    wy0 = max(0, int(round(cy - half_h)))
    wy1 = min(h, int(round(cy + half_h)))
    if wx1 <= wx0 or wy1 <= wy0:
        return None

    window = img_gray[wy0:wy1, wx0:wx1]
    thr = _otsu_threshold(window)
    ink = window <= thr
    if exclude_boxes:
        ink = _blank_excluded_boxes(ink, exclude_boxes, wx0, wy0)
    ink = _mask_stem_columns(ink, spacing, stem_box=stem_box, wx0=wx0)

    probe_col = int(round(cx)) - wx0
    probe_col = min(max(probe_col, 0), ink.shape[1] - 1)
    max_gap = NEAREST_RUN_MAX_GAP_HEAD_WIDTHS * head_w

    rows_y: List[float] = []
    left_x: List[Optional[float]] = []
    right_x: List[Optional[float]] = []
    for ry in range(ink.shape[0]):
        runs = _row_runs(ink[ry, :])
        nearest = _nearest_run(runs, probe_col, max_gap)
        rows_y.append(wy0 + ry)
        if nearest is None:
            left_x.append(None)
            right_x.append(None)
            continue
        s, e = nearest
        left_x.append(wx0 + s)
        right_x.append(wx0 + e - 1)

    widths = [
        (r - l + 1) if (l is not None and r is not None) else None
        for l, r in zip(left_x, right_x)
    ]
    return rows_y, left_x, right_x, widths, wx0, ink


def trace_head_shape(
    img_gray: np.ndarray,
    head_box: Tuple[float, float, float, float],
    spacing: float,
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
    staff_lines: Optional[Sequence[float]] = None,
    stem_box: Optional[Tuple[float, float, float, float]] = None,
) -> Optional[ShapeTrace]:
    """Trace the ink LOCALLY around `head_box` row by row and fit its oval.

    `staff_lines`, if given, is this head's own LOCALLY measured staff
    line y's (e.g. `frame_lines_for_head`'s own output) -- rows that sit
    on one of them are excluded from the oval FIT (never from ledger
    detection: a staff line is inside the staff, a ledger never is).
    `stem_box`, if given, is this head's own `Q.STEM` box as an absolute
    `(x0, y0, x1, y1)` -- masked exactly, never guessed.

    Returns `None` where there is nothing to trace (no image, no ink, a
    degenerate spacing) -- never a guessed shape (CLAUDE.md rule 8)."""
    if img_gray is None or spacing is None or spacing <= 0:
        return None
    x0, y0, x1, y1 = head_box
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0

    extracted = _trace_window(img_gray, cx, cy, spacing, exclude_boxes, stem_box)
    if extracted is None:
        return None
    rows_y, left_x, right_x, widths, wx0, ink = extracted

    oval = _fit_oval(rows_y, left_x, right_x, widths, cy, spacing, staff_lines)
    if oval is None:
        return None
    oval_center_y, _, _, _ = oval

    # Re-centre once on the freshly fitted oval centre and re-fit --
    # manager review 2026-10-02's own "iterate once" step: the box's own
    # centre is only a PROVISIONAL starting point.
    extracted2 = _trace_window(img_gray, cx, oval_center_y, spacing,
                                exclude_boxes, stem_box)
    if extracted2 is not None:
        rows_y, left_x, right_x, widths, wx0, ink = extracted2
        oval2 = _fit_oval(rows_y, left_x, right_x, widths, oval_center_y,
                          spacing, staff_lines)
        if oval2 is not None:
            oval = oval2

    oval_center_y, oval_top_y, oval_bottom_y, oval_half_width = oval

    bands = _find_ledger_bands(
        rows_y, left_x, right_x, oval_top_y, oval_bottom_y, oval_half_width,
        cx, spacing, ink=ink, wx0=wx0, staff_lines=staff_lines,
    )

    return ShapeTrace(
        rows_y=rows_y, left_x=left_x, right_x=right_x,
        oval_center_y=oval_center_y, oval_top_y=oval_top_y,
        oval_bottom_y=oval_bottom_y, oval_half_width=oval_half_width,
        ledger_bands=bands,
    )


def _on_staff_line_row(y: float, staff_lines: "Sequence[float] | None",
                       spacing: float) -> bool:
    if not staff_lines:
        return False
    tol = STAFF_LINE_ROW_TOLERANCE_SPACES * spacing
    return any(abs(y - ly) <= tol for ly in staff_lines)


def _fit_oval(rows_y, left_x, right_x, widths, provisional_center_y, spacing,
              staff_lines: "Sequence[float] | None" = None):
    """Fit the oval's vertical centre and extent from the traced widths.

    A row whose traced width is much wider than a STANDARD head width is a
    LEDGER (or a staff line) crossing the oval, not the oval itself -- such
    rows are excluded from the fit so a through-rung never inflates the
    oval's own measured half-width or drags its centre toward the rung's
    row. A row sitting ON a (locally measured) staff line is ALSO excluded
    from the fit regardless of its own width -- the oval never grows a
    staff line into part of itself -- but staff-line rows are never fed to
    ledger detection either way (`_find_ledger_bands` only ever sees what
    this function returns as "oval" vs "ledger", and a staff-line row is
    neither)."""
    head_w = STANDARD_HEAD_WIDTH_SPACES * spacing
    head_h = STANDARD_HEAD_HEIGHT_SPACES * spacing
    max_oval_rows = max(3, int(round(head_h)) + 2)
    width_cap = OVAL_ROW_WIDTH_CAP_HEAD_WIDTHS * head_w

    pad = 0.4 * spacing
    core = [
        i for i, y in enumerate(rows_y)
        if (provisional_center_y - head_h / 2 - pad) <= y
           <= (provisional_center_y + head_h / 2 + pad)
        and widths[i] is not None
        and not _on_staff_line_row(y, staff_lines, spacing)
    ]
    if not core:
        return (provisional_center_y,
                provisional_center_y - head_h / 2,
                provisional_center_y + head_h / 2,
                head_w / 2.0)

    oval_rows = [i for i in core if widths[i] <= width_cap]
    if not oval_rows:
        oval_rows = core  # every row looked inflated -- use them anyway

    oval_widths = sorted(widths[i] for i in oval_rows)
    half_width = oval_widths[len(oval_widths) // 2] / 2.0  # median

    ys = [rows_y[i] for i in oval_rows]
    ws = [widths[i] for i in oval_rows]
    total_w = sum(ws)
    center_y = (sum(y * w for y, w in zip(ys, ws)) / total_w
                if total_w > 0 else provisional_center_y)

    # Extent: walk outward from the centre ROW BY ROW. A row whose own
    # width is "oval-sized" (and not ON a staff line) extends the extent;
    # a row inflated past the width cap, OR sitting on a staff line, is
    # SKIPPED OVER (the oval continues on the far side), never treated as
    # the oval's own edge. A row with NO ink at all is a genuine OPEN end
    # and stops the walk there.
    oval_row_set = set(oval_rows)
    n_rows = len(rows_y)
    center_idx = min(range(n_rows), key=lambda i: abs(rows_y[i] - center_y))

    def _status(i: int) -> str:
        if widths[i] is None:
            return "none"
        if i in oval_row_set:
            return "oval"
        return "ledger"  # inflated, or on a staff line -- either way "skip"

    top_idx = center_idx
    i = center_idx
    while i - 1 >= 0 and abs(rows_y[i - 1] - center_y) <= max_oval_rows:
        st_ = _status(i - 1)
        if st_ == "none":
            break
        i -= 1
        if st_ == "oval":
            top_idx = i
    bot_idx = center_idx
    j = center_idx
    while j + 1 < n_rows and abs(rows_y[j + 1] - center_y) <= max_oval_rows:
        st_ = _status(j + 1)
        if st_ == "none":
            break
        j += 1
        if st_ == "oval":
            bot_idx = j
    return center_y, rows_y[top_idx], rows_y[bot_idx], half_width


def _column_tall_mask(ink: np.ndarray, max_band_rows: int) -> np.ndarray:
    """Per column: does this column's own ink include a vertical run
    taller than a ledger band could ever be (`> 2x` the band cap, same
    margin `rung_is_thin_and_flat`'s own thinness test gives a genuine
    line)? Used to find where an accidental fused onto a ledger's end
    begins -- that column's own run is tall there, the ledger's own
    columns are not."""
    h, w = ink.shape
    cap = max(2, 2 * max_band_rows)
    tall = np.zeros(w, dtype=bool)
    for c in range(w):
        best = cur = 0
        for v in ink[:, c]:
            if v:
                cur += 1
                if cur > best:
                    best = cur
            else:
                cur = 0
        tall[c] = best > cap
    return tall


def _find_ledger_bands(
    rows_y, left_x, right_x, oval_top_y, oval_bottom_y, oval_half_width,
    cx, spacing, ink: "np.ndarray | None" = None, wx0: int = 0,
    staff_lines: "Sequence[float] | None" = None,
):
    """Bands of rows, each at most `LEDGER_BAND_MAX_SPACES` tall, where the
    traced run shoots out past the fitted oval on at least one side, the
    protrusion is THIN (confined to that band, not a tall shape growing
    into neighbouring rows), and STRAIGHT (left/right stay within a small
    tolerance across the band, i.e. a run of contiguous rows at near-
    constant extent) -- never a shape that keeps growing row to row, which
    is an accidental merged onto the end of the run, not the ledger
    itself.

    A row sitting ON a (locally measured) staff line is NEVER a ledger
    candidate, however wide its run -- a staff line is inside the staff,
    a ledger is never inside it (manager review 2026-10-02: the trace
    must not follow a staff line the stem happens to touch)."""
    max_band_rows = max(1, int(round(LEDGER_BAND_MAX_SPACES * spacing)))
    straight_tol = max(1.0, 0.15 * spacing)

    tall_cols = _column_tall_mask(ink, max_band_rows) if ink is not None else None

    protrudes = []
    for y, l, r in zip(rows_y, left_x, right_x):
        if l is None or r is None or _on_staff_line_row(y, staff_lines, spacing):
            protrudes.append(False)
            continue
        past_left = (cx - l) > (oval_half_width + straight_tol)
        past_right = (r - cx) > (oval_half_width + straight_tol)
        protrudes.append(past_left or past_right)

    bands = []
    n = len(rows_y)
    i = 0
    while i < n:
        if not protrudes[i]:
            i += 1
            continue
        j = i
        while j < n and protrudes[j] and (rows_y[j] - rows_y[i]) < max_band_rows:
            j += 1
        band_rows = list(range(i, j))
        lefts = [left_x[k] for k in band_rows if left_x[k] is not None]
        rights = [right_x[k] for k in band_rows if right_x[k] is not None]
        if lefts and rights and (max(rights) - min(lefts)) > 0:
            band_left, band_right = min(lefts), max(rights)
            if tall_cols is not None:
                lo = max(0, int(round(band_left)) - wx0)
                hi = min(len(tall_cols) - 1, int(round(band_right)) - wx0)
                left_edge_c = min(hi, max(lo, int(round(cx - oval_half_width)) - wx0))
                right_edge_c = max(lo, min(hi, int(round(cx + oval_half_width)) - wx0))
                left_c = left_edge_c
                while left_c - 1 >= lo and not tall_cols[left_c - 1]:
                    left_c -= 1
                right_c = right_edge_c
                while right_c + 1 <= hi and not tall_cols[right_c + 1]:
                    right_c += 1
                band_left = max(band_left, wx0 + left_c)
                band_right = min(band_right, wx0 + right_c)
            band_y = sum(rows_y[k] for k in band_rows) / len(band_rows)
            mid = (oval_top_y + oval_bottom_y) / 2.0
            oval_h = max(1.0, oval_bottom_y - oval_top_y)
            tol = OVAL_MIDDLE_TOLERANCE_FRACTION * oval_h
            crosses_middle = abs(band_y - mid) <= tol
            bands.append(dict(
                y=band_y, left_x=band_left, right_x=band_right,
                left_juts=(cx - band_left) > (oval_half_width + straight_tol),
                right_juts=(band_right - cx) > (oval_half_width + straight_tol),
                crosses_middle=crosses_middle,
            ))
        i = j

    return bands


def shape_trace_middle_rung_evidence(
    img_gray: Optional[np.ndarray],
    head_box: Optional[Tuple[float, float, float, float]],
    spacing: Optional[float],
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
    staff_lines: Optional[Sequence[float]] = None,
    stem_box: Optional[Tuple[float, float, float, float]] = None,
) -> bool:
    """Drop-in replacement for `ledger_grid.head_middle_rung_evidence` --
    the first 4 positional arguments are the SAME signature contract
    (`derive_far_head_step` calls it that way), and `staff_lines`/
    `stem_box` are optional extras a caller can bind with
    `functools.partial` per head (this evidence function's own call site
    in `ledger_grid.py` is unchanged and still passes only 4 args).
    Same "no evidence possible -> False" contract (CLAUDE.md rule 8)."""
    if img_gray is None or head_box is None or spacing is None or spacing <= 0:
        return False
    trace = trace_head_shape(img_gray, head_box, spacing, exclude_boxes,
                             staff_lines=staff_lines, stem_box=stem_box)
    if trace is None:
        return False
    for band in trace.ledger_bands:
        if band["crosses_middle"] and (band["left_juts"] or band["right_juts"]):
            return True
    return False


def decide_head_position_from_shape(
    img_gray: np.ndarray,
    head_box: Tuple[float, float, float, float],
    spacing: float,
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
    staff_lines: Optional[Sequence[float]] = None,
    stem_box: Optional[Tuple[float, float, float, float]] = None,
) -> dict:
    """Task-brief step 5: decide ON/BEFORE/BEYOND a ledger, using the
    traced oval's own centre rather than the box's. Returns
    `{"decision": "on"|"space_before"|"space_beyond"|None, "band": dict|None,
    "reason": str}`. A ledger band crossing the oval within its own middle
    (`OVAL_MIDDLE_TOLERANCE_FRACTION`) places the head ON that ledger; a
    band touching only the oval's top or bottom names the ledger
    before/after it, and the head sits in the space beyond -- never a
    guess where no band is found at all."""
    trace = trace_head_shape(img_gray, head_box, spacing, exclude_boxes,
                             staff_lines=staff_lines, stem_box=stem_box)
    if trace is None:
        return dict(decision=None, band=None, reason="no_trace")
    on_bands = [b for b in trace.ledger_bands if b["crosses_middle"]]
    if on_bands:
        return dict(decision="on", band=on_bands[0], reason="ledger_crosses_oval_middle")
    if trace.ledger_bands:
        return dict(decision="space_beyond", band=trace.ledger_bands[-1],
                    reason="ledger_touches_oval_edge_only")
    return dict(decision=None, band=None, reason="no_ledger_band_found")
