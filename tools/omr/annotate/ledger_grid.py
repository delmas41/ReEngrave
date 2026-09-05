"""Measure the ledger rungs actually printed at one x of a cell image.

Why this exists: `snap_to_staff` anchors on the cell's MEASURED staff line
positions inside the staff, but beyond the staff it used to extrapolate at
the median staff spacing — and ledger lines are printed at their own pitch.
Measured over the hollow-campaign labels (356 noteheads, 10 batches, 9
publishers — `benchmarks/omr-snap-ledger-2026-09/`), the real rung pitch is
publisher-dependent in BOTH directions: Litolff runs ~1.10x the staff
spacing, Peters/Breitkopf/Simrock ~0.975x. So no corrected constant can fix
the extrapolation; the rungs have to be read off the page, per cell, at the
clicked x — the same move the in-staff grid already makes with its own line
positions.

A rung, to this reader, is a thin horizontal band of ink that crosses the
probed x and runs wider than any notehead is tall:

  * the row's ink must cross x and span >= 1.30 staff spaces — ledger lines
    poke out past the head on both sides, and a HALF notehead is only ~1.17
    spaces wide (Bravura aspect), so its cap arcs never qualify. A WHOLE
    notehead is ~1.72 wide and its caps DO qualify — deliberately
    unfiltered, because a whole note's cap arcs sit exactly ON the line
    slots adjacent to its own position, so they vouch for the true local
    pitch rather than corrupting it;
  * white gaps up to 0.90 spaces inside the span are bridged, because the
    one rung that matters most — the one THROUGH an on-line hollow note —
    is broken in the middle by the head's own white counter, and requiring
    one contiguous run made exactly that rung invisible (the reader then
    latched onto the note's cap arcs instead). A WHOLE note's counter is a
    wide oval: 0.55 was tried first and still split that rung in two;
  * the band must be thin (<= 0.40 spaces) — beams and letterforms are
    thicker. A band that merged a rung with the head it runs through is
    taller than that, so what must be thin is the band's PEAK-SPAN subband
    (the rung is the widest thing in it — the ledger pokes past the head),
    and the band's centre is the span-weighted centre of those peak rows;
  * successive rungs must sit 0.65..1.35 of the local pitch apart, walking
    outward from the staff's own edge line. That window rejects half-pitch
    fakes (an on-line note's cap arcs) and stops the walk before it can
    latch onto a neighbouring staff's lines across the inter-staff gap.

Everything degrades to an abstention: no image, no ink, no qualifying band,
or a broken walk simply returns fewer (or no) rungs, and the caller falls
back to the constant-pitch extrapolation it always had.
"""

from __future__ import annotations

import numpy as np

# A rung must out-span a half notehead (1.167 spaces) with margin, while
# staying under the whole notehead's 1.72 — see the module docstring for why
# whole-note caps are safe to admit anyway.
RUNG_MIN_LEN_SPACES = 1.30
# White gaps this wide inside a span are bridged: a hollow notehead's white
# counter splits the one rung printed THROUGH the head. Sized for the widest
# counter — a whole note's oval — which 0.55 (a half's counter) failed on.
RUNG_BRIDGE_GAP_SPACES = 0.90
# Ledger lines print at roughly staff-line thickness; beams and text are
# fatter. Generous enough for a rung band merged with a notehead cap arc.
RUNG_MAX_THICKNESS_SPACES = 0.40
# The walk accepts the next rung only 0.65..1.35 local pitches out — wide
# enough for warp and publisher pitch, narrow enough to reject half-pitch
# cap fakes and the >=1.7-space jump to a neighbouring staff's lines.
WALK_WINDOW = (0.65, 1.35)
# How far beyond the staff to look. snap_to_staff's own grid reaches 6.0
# spaces (12 half-steps); a little slack costs nothing.
MAX_SPACES = 6.5
# The probed column: the click sits on the notehead, the rung reaches past
# it both ways.
WINDOW_HALF_WIDTH_SPACES = 1.1
CROSS_HALF_WIDTH_SPACES = 0.1


def _otsu_threshold(values: np.ndarray) -> int:
    """Plain Otsu on a uint8 array — scans vary too much for a fixed cut."""
    hist = np.bincount(values.ravel(), minlength=256).astype(np.float64)
    total = float(values.size)
    if total == 0:
        return 127
    bins = np.arange(256, dtype=np.float64)
    weight_bg = np.cumsum(hist)
    weight_fg = total - weight_bg
    sum_bg = np.cumsum(hist * bins)
    sum_all = sum_bg[-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_bg = sum_bg / weight_bg
        mean_fg = (sum_all - sum_bg) / weight_fg
        between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    between[~np.isfinite(between)] = -1.0
    return int(np.argmax(between))


def _band_centers(
    ink: np.ndarray, cx_local: float, spacing: float, y_offset: int
) -> list[float]:
    """Thin bands of long ink spans crossing x=cx_local. Returns centre ys
    in image coordinates (y_offset is the window's top row).

    A row's span is its ink runs merged across white gaps up to
    RUNG_BRIDGE_GAP_SPACES — the rung printed THROUGH an on-line hollow
    notehead is split by the head's white counter and no single run crosses
    the probe column there.
    """
    h, w = ink.shape
    lo = int(cx_local - CROSS_HALF_WIDTH_SPACES * spacing)
    hi = int(cx_local + CROSS_HALF_WIDTH_SPACES * spacing)
    min_len = RUNG_MIN_LEN_SPACES * spacing
    bridge = RUNG_BRIDGE_GAP_SPACES * spacing

    span_len = np.zeros(h, dtype=np.float64)
    padded = np.zeros((h, w + 2), dtype=np.int8)
    padded[:, 1:-1] = ink
    edges = np.diff(padded, axis=1)
    for yi in range(h):
        starts = np.flatnonzero(edges[yi] == 1)
        if starts.size == 0:
            continue
        ends = np.flatnonzero(edges[yi] == -1)
        # Merge runs separated by bridgeable white gaps into spans.
        spans: list[list[float]] = []
        for s, e in zip(starts, ends):
            if spans and s - spans[-1][1] <= bridge:
                spans[-1][1] = e
            else:
                spans.append([s, e])
        best = 0.0
        for s, e in spans:
            if e - s >= min_len and s <= hi and e >= lo:
                best = max(best, float(e - s))
        span_len[yi] = best

    bands: list[float] = []
    yi = 0
    max_thick = RUNG_MAX_THICKNESS_SPACES * spacing
    while yi < h:
        if span_len[yi] > 0:
            j = yi
            while j < h and span_len[j] > 0:
                j += 1
            # A band that merged a rung with the notehead it runs through is
            # taller than a rung — a whole note's body rows all qualify once
            # gaps bridge. The rung is the WIDEST thing in its band (the
            # ledger pokes out past the head on both sides), so keep only
            # the contiguous peak-span subband around the maximum, and only
            # if THAT is rung-thin. A headless rung is its own peak and
            # passes unchanged; a head with no rung through it peaks on its
            # fat body rows, which fail the thinness test — no fake band.
            band = span_len[yi:j]
            k = int(np.argmax(band))
            floor = 0.95 * band[k]
            lo_i = k
            while lo_i > 0 and band[lo_i - 1] >= floor:
                lo_i -= 1
            hi_i = k
            while hi_i + 1 < band.shape[0] and band[hi_i + 1] >= floor:
                hi_i += 1
            if hi_i - lo_i + 1 <= max_thick:
                # Span-weighted centre of the peak rows. Recentring on "wing"
                # columns a notehead cannot reach was built and REFUSED: for
                # both wing zones tried (0.55..1.1 and 0.9..1.1 spaces out)
                # it measured worse on the hollow corpus than this — see
                # benchmarks/omr-snap-ledger-2026-09/FINDINGS.md.
                idx = np.arange(lo_i, hi_i + 1, dtype=np.float64)
                weights = band[lo_i : hi_i + 1]
                bands.append(
                    float(np.average(idx, weights=weights)) + yi + y_offset
                )
            yi = j
        else:
            yi += 1
    return bands


def _walk_ladder(
    edge_y: float, sign: float, bands: list[float], spacing: float
) -> list[float]:
    """One rung per staff space outward from the staff's edge line, each
    accepted only inside WALK_WINDOW of the local pitch. Returns measured
    rung ys, nearest first — WITHOUT the edge line itself."""
    rungs: list[float] = []
    anchor = edge_y
    pitch = spacing
    while len(rungs) < int(MAX_SPACES):
        cands = [
            b for b in bands
            if WALK_WINDOW[0] * pitch <= sign * (b - anchor) <= WALK_WINDOW[1] * pitch
        ]
        if not cands:
            break
        expected = anchor + sign * pitch
        best = min(cands, key=lambda b: abs(b - expected))
        rungs.append(best)
        pitch = abs(best - anchor)
        anchor = best
    return rungs


def measure_ledger_rungs(
    img_gray: np.ndarray, staff_line_ys: list[float], x: float
) -> dict[str, list[float]]:
    """Measured ledger rung ys above and below the staff at column x.

    img_gray is the cell image as a 2-D uint8 array in the SAME canonical
    frame as staff_line_ys. Returns {"above": [...], "below": [...]} with
    each list ordered nearest-rung-first; empty lists are abstentions.
    """
    ys = sorted(float(v) for v in staff_line_ys or [])
    if len(ys) < 2 or img_gray.ndim != 2:
        return {"above": [], "below": []}
    gaps = sorted(ys[i + 1] - ys[i] for i in range(len(ys) - 1))
    mid = len(gaps) // 2
    spacing = gaps[mid] if len(gaps) % 2 else (gaps[mid - 1] + gaps[mid]) / 2.0
    if spacing <= 0:
        return {"above": [], "below": []}

    h, w = img_gray.shape
    x0 = int(max(0, x - WINDOW_HALF_WIDTH_SPACES * spacing))
    x1 = int(min(w, x + WINDOW_HALF_WIDTH_SPACES * spacing))
    if x1 - x0 < spacing:
        return {"above": [], "below": []}

    out: dict[str, list[float]] = {"above": [], "below": []}
    for side, edge_y, sign in (("above", ys[0], -1.0), ("below", ys[-1], 1.0)):
        # From just outside the edge line (clear of the line's own ink) to
        # the search cap, clamped to the image.
        near = edge_y + sign * 0.30 * spacing
        far = edge_y + sign * MAX_SPACES * spacing
        yy0 = int(max(0, min(near, far)))
        yy1 = int(min(h, max(near, far)))
        if yy1 - yy0 < 2:
            continue
        window = img_gray[yy0:yy1, x0:x1]
        thr = _otsu_threshold(window)
        ink = window <= thr  # <=: Otsu labels the threshold bin itself ink (a
        # binary image splits at t=0, and `<` would then select nothing)
        bands = _band_centers(ink, x - x0, spacing, yy0)
        out[side] = _walk_ladder(edge_y, sign, bands, spacing)
    return out
