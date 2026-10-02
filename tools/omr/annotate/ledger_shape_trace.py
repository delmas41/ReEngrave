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

This module fixes that by tracing the connected ink around the head row by
row, fitting the oval from the TRACE (not the box), and classifying each
candidate band against the oval's own fitted extent rather than the box's.
It produces a drop-in replacement evidence function
(`shape_trace_middle_rung_evidence`) with the SAME signature contract as
`ledger_grid.head_middle_rung_evidence` -- `derive_far_head_step` can take
either. Nothing here flips a product default; it is additive and measured
by the harness in `benchmarks/omr-local-staff-2026-09/`.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

import numpy as np

from .ledger_grid import _otsu_threshold

# A notehead oval (Bravura-ish aspect, matches `ledger_grid`'s own
# RUNG_MIN_LEN_SPACES commentary: a half note is ~1.17 spaces wide, a
# whole ~1.72, and both are "about one staff space" tall) is this many
# staff spaces tall at its widest point.
OVAL_HEIGHT_SPACES = 1.15

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
# ledger band.
STEM_MIN_RUN_SPACES = 1.3
# ...but only when that tall run's own horizontal footprint is narrow; a
# genuinely wide dark run that happens to be tall (a merged blob) is not a
# stem and must not be masked out.
STEM_MAX_WIDTH_SPACES = 0.24

# How far past the head to scan, in head-widths, when tracing rows -- "near
# the head" per the task brief ("within ~2 head-widths, excluding the stem
# column").
TRACE_X_PAD_WIDTHS = 2.0
# How far above/below the box to scan for rows at all.
TRACE_Y_PAD_SPACES = 1.75


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


def _mask_stem_columns(ink: np.ndarray, spacing: float) -> np.ndarray:
    """Zero out any column band that is a stem: taller than a notehead or
    ledger could ever be, and narrow. Returns a NEW array; `ink` itself is
    never mutated."""
    h, w = ink.shape
    out = ink.copy()
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


def trace_head_shape(
    img_gray: np.ndarray,
    head_box: Tuple[float, float, float, float],
    spacing: float,
    exclude_boxes: Optional[Sequence[Tuple[float, float, float, float]]] = None,
) -> Optional[ShapeTrace]:
    """Trace the ink around `head_box` row by row and fit its oval.

    Returns `None` where there is nothing to trace (no image, no ink, a
    degenerate spacing) -- never a guessed shape (CLAUDE.md rule 8)."""
    if img_gray is None or spacing is None or spacing <= 0:
        return None
    x0, y0, x1, y1 = head_box
    h, w = img_gray.shape
    head_w = max(1.0, x1 - x0)
    cx = (x0 + x1) / 2.0

    wx0 = max(0, int(round(cx - TRACE_X_PAD_WIDTHS * head_w)))
    wx1 = min(w, int(round(cx + TRACE_X_PAD_WIDTHS * head_w)))
    wy0 = max(0, int(round(y0 - TRACE_Y_PAD_SPACES * spacing)))
    wy1 = min(h, int(round(y1 + TRACE_Y_PAD_SPACES * spacing)))
    if wx1 <= wx0 or wy1 <= wy0:
        return None

    window = img_gray[wy0:wy1, wx0:wx1]
    thr = _otsu_threshold(window)
    ink = window <= thr
    if exclude_boxes:
        ink = _blank_excluded_boxes(ink, exclude_boxes, wx0, wy0)
    ink = _mask_stem_columns(ink, spacing)

    probe_col = int(round(cx)) - wx0
    probe_col = min(max(probe_col, 0), ink.shape[1] - 1)

    rows_y: List[float] = []
    left_x: List[Optional[float]] = []
    right_x: List[Optional[float]] = []
    for ry in range(ink.shape[0]):
        runs = _row_runs(ink[ry, :])
        containing = [r for r in runs if r[0] <= probe_col < r[1]]
        if not containing:
            # No run on the centre column this row -- nothing traced here
            # (an open half-note end, or genuinely blank); record a gap.
            rows_y.append(wy0 + ry)
            left_x.append(None)
            right_x.append(None)
            continue
        s, e = containing[0]
        rows_y.append(wy0 + ry)
        left_x.append(wx0 + s)
        right_x.append(wx0 + e - 1)

    widths = [
        (r - l + 1) if (l is not None and r is not None) else None
        for l, r in zip(left_x, right_x)
    ]

    oval = _fit_oval(rows_y, left_x, right_x, widths, head_box, spacing)
    if oval is None:
        return None
    oval_center_y, oval_top_y, oval_bottom_y, oval_half_width = oval

    bands = _find_ledger_bands(
        rows_y, left_x, right_x, oval_top_y, oval_bottom_y, oval_half_width,
        cx, spacing, ink=ink, wx0=wx0,
    )

    return ShapeTrace(
        rows_y=rows_y, left_x=left_x, right_x=right_x,
        oval_center_y=oval_center_y, oval_top_y=oval_top_y,
        oval_bottom_y=oval_bottom_y, oval_half_width=oval_half_width,
        ledger_bands=bands,
    )


def _fit_oval(rows_y, left_x, right_x, widths, head_box, spacing):
    """Fit the oval's vertical centre and extent from the traced widths --
    a smooth profile rising then falling over ~`OVAL_HEIGHT_SPACES` rows.
    Falls back to the box's own extent where the trace found nothing at
    all (never invents ink), and handles an OPEN half-note oval (no run on
    one or more rows near an end) by using the OUTER outline -- the
    furthest traced extent on either side within the box's own y-range --
    rather than requiring every row to have closed ink.

    A row whose traced width is much wider than the box's own width is a
    LEDGER crossing the oval, not the oval itself (a ledger shoots past
    the head on at least one side by construction) -- such rows are
    excluded from the fit so a through-rung never inflates the oval's own
    measured half-width or drags its centre toward the rung's row. The
    box's own width is used as the width reference (never its height,
    which is exactly what this function must NOT trust) -- the task this
    lane fixes is a box cropped short vertically, not one sized wrong
    horizontally."""
    x0, y0, x1, y1 = head_box
    box_w = max(1.0, x1 - x0)
    max_oval_rows = max(3, int(round(OVAL_HEIGHT_SPACES * spacing)) + 2)

    # Rows plausibly INSIDE the oval: within the box's own y-range,
    # padded a little so an off-centre box still finds the real extent.
    pad = 0.4 * spacing
    core = [
        i for i, y in enumerate(rows_y)
        if (y0 - pad) <= y <= (y1 + pad) and widths[i] is not None
    ]
    if not core:
        # Nothing traced at all near the box -- fall back to the box's
        # own geometry rather than guessing a shape with no evidence.
        return ((y0 + y1) / 2.0, y0, y1, box_w / 2.0)

    # Oval rows vs. a ledger crossing through: a row far wider than the
    # box's own width is a rung, not the oval -- drop it from the fit.
    oval_rows = [i for i in core if widths[i] <= 1.35 * box_w]
    if not oval_rows:
        oval_rows = core  # every row looked inflated -- use them anyway

    oval_widths = sorted(widths[i] for i in oval_rows)
    half_width = oval_widths[len(oval_widths) // 2] / 2.0  # median

    # Weight each oval row by its width to find the oval's own vertical
    # centre (a true oval is widest at its own middle); rung rows are
    # already excluded so they cannot drag the centre toward themselves.
    ys = [rows_y[i] for i in oval_rows]
    ws = [widths[i] for i in oval_rows]
    total_w = sum(ws)
    if total_w <= 0:
        center_y = (y0 + y1) / 2.0
    else:
        center_y = sum(y * w for y, w in zip(ys, ws)) / total_w

    # Extent: walk outward from the centre ROW BY ROW (rows_y is a
    # contiguous run of consecutive pixel rows). A row whose own width is
    # "oval-sized" extends the extent; a row inflated past the box's own
    # width is a LEDGER CROSSING the oval -- skipped over (the oval
    # continues on the far side of a thin crossing line), never treated
    # as the oval's own edge. A row with NO ink at all is a genuine OPEN
    # end (a half-note's open oval, or simply the oval's true edge) and
    # stops the walk there, using the outline up to that point.
    oval_width_set = set(oval_rows)
    n_rows = len(rows_y)
    center_idx = min(range(n_rows), key=lambda i: abs(rows_y[i] - center_y))

    def _status(i: int) -> str:
        if widths[i] is None:
            return "none"
        return "oval" if i in oval_width_set else "ledger"

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
):
    """Bands of rows, each at most `LEDGER_BAND_MAX_SPACES` tall, where the
    traced run shoots out past the fitted oval on at least one side, the
    protrusion is THIN (confined to that band, not a tall shape growing
    into neighbouring rows), and STRAIGHT (left/right stay within a small
    tolerance across the band, i.e. a run of contiguous rows at near-
    constant extent) -- never a shape that keeps growing row to row, which
    is an accidental merged onto the end of the run, not the ledger
    itself."""
    max_band_rows = max(1, int(round(LEDGER_BAND_MAX_SPACES * spacing)))
    straight_tol = max(1.0, 0.15 * spacing)

    tall_cols = _column_tall_mask(ink, max_band_rows) if ink is not None else None

    protrudes = []
    for y, l, r in zip(rows_y, left_x, right_x):
        if l is None or r is None:
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
            # Cause: an accidental merged onto the run's end (DECISIONS
            # 2026-10-02) is NOT part of the thin, straight band -- trim
            # the extent inward from each end, column by column, stopping
            # at the first TALL column (one whose own ink keeps going well
            # past this band's own row range): that column, and everything
            # beyond it outward, is excluded from the ledger's own measured
            # extent.
            if tall_cols is not None:
                lo = max(0, int(round(band_left)) - wx0)
                hi = min(len(tall_cols) - 1, int(round(band_right)) - wx0)
                # Tallness is only evidence of an accidental OUTSIDE the
                # oval's own footprint -- inside it, the oval's own height
                # makes every column "tall", which is expected and not an
                # accidental. So the walk starts at the oval's own edge on
                # each side (never the centre column) and only trims the
                # PROTRUDING part of the band.
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
) -> bool:
    """Drop-in replacement for `ledger_grid.head_middle_rung_evidence`,
    same signature and same "no evidence possible -> False" contract
    (CLAUDE.md rule 8), but the probe row is the TRACED oval's own centre
    rather than the box's naive `(y0+y1)/2` -- the fix for the two
    truth-set heads that abstain with `no_rung_before_the_head` while
    geometry and the ledger-measured reader both already land on the
    reference position (module docstring)."""
    if img_gray is None or head_box is None or spacing is None or spacing <= 0:
        return False
    trace = trace_head_shape(img_gray, head_box, spacing, exclude_boxes)
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
) -> dict:
    """Task-brief step 5: decide ON/BEFORE/BEYOND a ledger, using the
    traced oval's own centre rather than the box's. Returns
    `{"decision": "on"|"space_before"|"space_beyond"|None, "band": dict|None,
    "reason": str}`. A ledger band crossing the oval within its own middle
    (`OVAL_MIDDLE_TOLERANCE_FRACTION`) places the head ON that ledger; a
    band touching only the oval's top or bottom names the ledger
    before/after it, and the head sits in the space beyond -- never a
    guess where no band is found at all."""
    trace = trace_head_shape(img_gray, head_box, spacing, exclude_boxes)
    if trace is None:
        return dict(decision=None, band=None, reason="no_trace")
    on_bands = [b for b in trace.ledger_bands if b["crosses_middle"]]
    if on_bands:
        return dict(decision="on", band=on_bands[0], reason="ledger_crosses_oval_middle")
    if trace.ledger_bands:
        return dict(decision="space_beyond", band=trace.ledger_bands[-1],
                    reason="ledger_touches_oval_edge_only")
    return dict(decision=None, band=None, reason="no_ledger_band_found")
