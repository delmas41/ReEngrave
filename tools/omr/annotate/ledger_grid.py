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
# A ledger printed THROUGH a head counts only where ink extends on BOTH
# sides of the head by at least this many spaces (DECISIONS 2026-10-01,
# Sean: "generally it should have a line that extends on either side of
# the notehead") -- a long band that is merely long, but lopsided (most of
# its length on one side, barely only just touching the probe column from
# the other), is not a stub on both sides and must not be accepted. Sized
# small deliberately: a detector box is not always perfectly centred on
# the printed head (2.39b), so a real rung's near side can sit a few px
# off the box's own x-centre; 0.45 (near a half notehead-width) measured
# WORSE on 2.44c's truth set than this value -- it rejected real rungs
# whose near-side stub was short but genuinely present, not merely a
# brush from one side (see FINDINGS).
RUNG_STUB_MIN_SPACES = 0.15
# When the walk cannot find the next rung within WALK_WINDOW of the
# current anchor but the head it is reading FOR is still farther out than
# that window reaches, the window is widened up to the head's own
# distance (plus this much slack) rather than stopping -- hand-drawn
# ledgers are not evenly spaced (DECISIONS 2026-10-01: "There is a larger
# space between the lower ledger lines and the one right underneath the
# note").
TARGET_SLACK_SPACES = 0.5
# Sean's 2026-10-01 convention for turning a rung count into a step: the
# head is placed by the GAP between the last CLEAN rung found and the
# head's own NEAR edge (the side of its box closest to the staff), not by
# matching the head's centre to a rung within a generic tolerance. Gaps
# this small (in staff spaces) are "touching" the last rung -> the head
# sits in the space just beyond it. Calibrated against Sean's two crop
# readings (`glyph/3/0/9/2/5`, ref 11: measured gap 0.12 sp -> touching;
# `glyph/3/0/7/6/2`, ref 12: measured gap 0.39 sp -> on the next ledger)
# rather than the literal "about half a space" wording, which overshoots
# the second example -- box/ink measurement slop (2.39b) means "about
# half" reads closer to a third in practice.
TOUCH_TOL_SPACES = 0.20
# Gaps at or beyond this are "on the next ledger, hidden under the head".
HALF_LEDGER_TOL_SPACES = 0.35


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
    stub = RUNG_STUB_MIN_SPACES * spacing
    stub_lo = cx_local - stub
    stub_hi = cx_local + stub

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
            # A rung must cross the probe column AND extend at least a
            # stub past the probed x on BOTH sides -- a span that is long
            # overall but lopsided (e.g. a merged bridge that pulled in
            # unrelated ink far to one side while barely touching the
            # other) is not a ledger drawn through this head (DECISIONS
            # 2026-10-01).
            if (e - s >= min_len and s <= hi and e >= lo
                    and s <= stub_lo and e >= stub_hi):
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
    edge_y: float, sign: float, bands: list[float], spacing: float,
    target_y: float | None = None,
) -> list[float]:
    """One rung per staff space outward from the staff's edge line, each
    accepted only inside WALK_WINDOW of the local pitch. Returns measured
    rung ys, nearest first — WITHOUT the edge line itself.

    `target_y`, when given, is the head this walk is ultimately reading
    FOR. Hand-drawn ledgers are not evenly spaced (DECISIONS 2026-10-01: a
    wider-than-usual gap between two lower ledgers made the walk stop
    before reaching the one right under the note). So where the normal
    WALK_WINDOW finds nothing but the target is still farther out than
    the window reaches, the window is widened — just far enough to catch
    the next rung before the target, never past it — rather than giving
    up. The widened step always takes the NEAREST candidate outward (never
    jumping straight to the target), so an irregular gap is still walked
    one rung at a time.
    """
    rungs: list[float] = []
    anchor = edge_y
    pitch = spacing
    while len(rungs) < int(MAX_SPACES):
        base_upper = WALK_WINDOW[1] * pitch
        cands = [
            b for b in bands
            if WALK_WINDOW[0] * pitch <= sign * (b - anchor) <= base_upper
        ]
        widened = False
        if not cands and target_y is not None:
            dist_to_target = sign * (target_y - anchor)
            if dist_to_target > base_upper:
                upper = dist_to_target + TARGET_SLACK_SPACES * spacing
                cands = [
                    b for b in bands
                    if WALK_WINDOW[0] * pitch <= sign * (b - anchor) <= upper
                ]
                widened = True
        if not cands:
            break
        if widened:
            best = min(cands, key=lambda b: sign * (b - anchor))
        else:
            expected = anchor + sign * pitch
            best = min(cands, key=lambda b: abs(b - expected))
        rungs.append(best)
        pitch = abs(best - anchor)
        anchor = best
    return rungs


def far_head_needs_ledger_read(pos_half_steps: float) -> bool:
    """A head on the staff's 5 lines (0..8 half-steps from the top line)
    OR in the first space just outside it (-1 or 9) is ON-STAFF and takes
    its position from the staff lines directly, never from a ledger read
    -- DECISIONS 2026-10-01 (Sean, on a reader that drew a rung through
    such a head): "there is no ledger line. It is the first space above
    the staff and should probably be treated as a note on the staff not
    as one that should be a part of ledger lines." Only a head beyond that
    first space needs `measure_ledger_rungs` at all; a caller that calls
    it anyway for an on-staff head risks exactly that false rung.
    """
    return pos_half_steps < -1 or pos_half_steps > 9


def measure_ledger_rungs(
    img_gray: np.ndarray, staff_line_ys: list[float], x: float,
    head_y: float | None = None,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
) -> dict[str, list[float]]:
    """Measured ledger rung ys above and below the staff at column x.

    img_gray is the cell image as a 2-D uint8 array in the SAME canonical
    frame as staff_line_ys. Returns {"above": [...], "below": [...]} with
    each list ordered nearest-rung-first; empty lists are abstentions.

    `head_y`, when given, is the y of the head this read is ultimately
    FOR (same frame as `img_gray`/`staff_line_ys`). It only widens the
    walk on the side the head actually sits on (DECISIONS 2026-10-01, the
    wide-gap fix in `_walk_ladder`) so the walk does not give up before
    reaching that head; it never invents a rung the ink does not show.

    `exclude_boxes`, when given, is a list of OTHER noteheads' own boxes
    (x0, y0, x1, y1, same frame) -- their ink is blanked out before any
    span is measured, so a neighbouring head's ink can no longer supply
    one side of a "both sides" stub (DECISIONS 2026-10-01, Sean: "a
    second rung... accepted because its left stub is the neighbouring
    head's ink"). Never includes the subject's own box -- that is real
    evidence, not noise.
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
        if exclude_boxes:
            window = window.copy()
            for (bx0, by0, bx1, by1) in exclude_boxes:
                ex0, ey0 = max(int(bx0), x0), max(int(by0), yy0)
                ex1, ey1 = min(int(bx1) + 1, x1), min(int(by1) + 1, yy1)
                if ex1 > ex0 and ey1 > ey0:
                    window[ey0 - yy0:ey1 - yy0, ex0 - x0:ex1 - x0] = 255
        thr = _otsu_threshold(window)
        ink = window <= thr  # <=: Otsu labels the threshold bin itself ink (a
        # binary image splits at t=0, and `<` would then select nothing)
        bands = _band_centers(ink, x - x0, spacing, yy0)
        side_target = (
            head_y if head_y is not None and sign * (head_y - edge_y) > 0
            else None
        )
        out[side] = _walk_ladder(edge_y, sign, bands, spacing, side_target)
    return out


def derive_far_head_step(
    rungs_y: "list[float]", edge_y: float, sign: float, head_near_y: float,
    spacing: float,
) -> dict:
    """Sean's 2026-10-01 convention for turning a rung count into a step.

    `rungs_y` is one side's list from `measure_ledger_rungs` (nearest-edge
    first). `head_near_y` is the edge of the head's OWN box closest to the
    staff (its bottom for a head ABOVE the staff, its top for a head
    BELOW) -- never its centre; the gap is measured from there, not from
    wherever the box happens to be centred.

    Walks the SAME ladder arithmetic the reader already uses (2 half-steps
    per rung from the edge) and places the head by the gap, in staff
    spaces, between the LAST rung found and that near edge:

      * no rung found at all -> ABSTAIN (nothing to count from).
      * the last rung is beyond the near edge by `TOUCH_TOL_SPACES` or
        less (the rung passes through the head's own ink, not merely
        near it) -> the head sits ON that rung.
      * the near edge sits within `TOUCH_TOL_SPACES` of the last rung,
        on the staff side -> "touching" -> the head sits in the SPACE
        just beyond that rung.
      * the near edge is `HALF_LEDGER_TOL_SPACES` or more beyond the last
        rung -> the head is on the NEXT ledger line, hidden under it.
      * anything between the two tolerances is ambiguous -> ABSTAIN,
        never guessed (CLAUDE.md rule 8).

    Returns `{"offset": int|None, "kind": "line"|"space"|None,
    "reason": str}`. `offset` is in half-steps outward from the edge; the
    caller adds it to (or subtracts it from, by `sign`) the edge's own
    staff position.
    """
    if not rungs_y or spacing <= 0:
        return dict(offset=None, kind=None, reason="no_rungs")
    half_step = spacing / 2.0
    last = rungs_y[-1]
    last_half_steps = int(round(abs(last - edge_y) / half_step))
    gap_spaces = (sign * (head_near_y - last)) / spacing
    if gap_spaces <= -TOUCH_TOL_SPACES:
        return dict(offset=last_half_steps, kind="line",
                   reason=f"last rung passes through the head itself "
                          f"(gap {gap_spaces:.2f} sp)")
    if gap_spaces <= TOUCH_TOL_SPACES:
        return dict(offset=last_half_steps + 1, kind="space",
                   reason=f"touching the last clean rung (gap "
                          f"{gap_spaces:.2f} sp)")
    if gap_spaces >= HALF_LEDGER_TOL_SPACES:
        return dict(offset=last_half_steps + 2, kind="line",
                   reason=f"{gap_spaces:.2f} sp beyond the last clean rung "
                          f"-- on the next ledger, hidden under the head")
    return dict(offset=None, kind=None,
               reason=f"ambiguous gap {gap_spaces:.2f} sp "
                      f"(between touching and half a space)")
