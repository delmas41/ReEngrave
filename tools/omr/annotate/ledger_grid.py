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
# A through-head rung's stub must extend this far BEYOND the subject's
# OWN detector box edges on each side (DECISIONS 2026-10-01, round 2,
# Sean on `glyph/3/0/9/2/0`: a rung was invented from the head's own
# widest row, which does not extend past its own box at all). Used only
# where the caller supplies the subject's own box (`head_box_local`).
# 0.25 (near the old cx-relative RUNG_STUB_MIN_SPACES margin) measured
# FAR worse on 2.44c's truth set -- real boxes already vary in width
# with the plate (Litolff merges, Breitkopf shatters, 2.39 standard-vs-
# raw box), and requiring clearance past the WIDEST of those on top of
# the box's own width abstained most real far heads. A real ledger only
# needs to poke a short, genuine amount past the note it runs through,
# not a further quarter space past whatever the box itself measures;
# small enough only to refuse ink that is merely coextensive with (or
# narrower than) the box -- the exact shape of the head's own widest row.
RUNG_BEYOND_BOX_MIN_SPACES = 0.05
# How far past the subject's own box the search window extends when
# `head_box_x` is given (round 3) -- sized to the largest genuine
# overhang measured in this lane's own data (~0.65 spaces) plus slack,
# not a second full probe window (`WINDOW_HALF_WIDTH_SPACES`): that was
# tried and refused -- in a dense chord it pulls in enough unrelated ink
# that a real rung's row-span grows too tall across consecutive rows and
# fails the thinness test instead.
RUNG_BOX_VISIBILITY_SPACES = 0.85
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
    ink: np.ndarray, cx_local: float, spacing: float, y_offset: int,
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


def _rung_row_clears_box(
    img_gray: np.ndarray, y: float, x: float,
    head_box_x: "tuple[float, float]", spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
) -> bool:
    """Does the ink crossing (y, x) extend past the subject's OWN box
    (`head_box_x`) by `RUNG_BEYOND_BOX_MIN_SPACES` on top of the box's
    own width? Measured in a DEDICATED, generously wide crop around the
    box -- never the narrow window the candidate-finding walk uses to
    locate rungs in the first place, which routinely clips a real rung's
    true extent a few px short of a length test (round 3: a genuine 28px
    overhang measured 23px once clipped there). Widening THAT window
    instead, so one pass could do both jobs, was tried and refused: in a
    dense chord it pulls in neighbouring stems/beams and makes a real
    rung's own row-span too TALL across consecutive rows, failing peak
    selection's thinness test before this check is ever reached.
    """
    h, w = img_gray.shape
    bx0, bx1 = head_box_x
    box_w = bx1 - bx0
    pad = RUNG_BOX_VISIBILITY_SPACES * spacing
    cx0 = max(0, int(bx0 - pad))
    cx1 = min(w, int(bx1 + pad))
    y_i = int(round(y))
    y0, y1 = max(0, y_i - 1), min(h, y_i + 2)
    if cx1 <= cx0 or y1 <= y0:
        return False
    window = img_gray[y0:y1, cx0:cx1]
    thr = _otsu_threshold(window)
    ink = window <= thr
    if exclude_boxes:
        # Another head's ink reaching into this verification crop (the
        # crop is wider than the main probe window specifically to see a
        # real overhang) can bridge into a false "clears the box" result
        # exactly as it could fake a stub in the main window -- same
        # exclusion, same reason (DECISIONS 2026-10-01, round 2 + 3).
        ink = _exclude_other_heads_ink(ink, exclude_boxes, cx0, y0, spacing)
    ink_cols = ink.any(axis=0)
    bridge = int(round(RUNG_BRIDGE_GAP_SPACES * spacing))
    runs: list[list[int]] = []
    n = len(ink_cols)
    i = 0
    while i < n:
        if ink_cols[i]:
            j = i
            while j < n and ink_cols[j]:
                j += 1
            if runs and i - runs[-1][1] <= bridge:
                runs[-1][1] = j
            else:
                runs.append([i, j])
            i = j
        else:
            i += 1
    probe_col = int(round(x)) - cx0
    containing = [r for r in runs if r[0] <= probe_col < r[1]]
    if not containing:
        return False
    s, e = containing[0]
    return (e - s) >= box_w + 2 * RUNG_BEYOND_BOX_MIN_SPACES * spacing


def _exclude_other_heads_ink(
    ink: np.ndarray, exclude_boxes: "list[tuple[float, float, float, float]]",
    x0: int, yy0: int, spacing: float,
) -> np.ndarray:
    """Remove another notehead's own ink from `ink` (boolean, already
    thresholded) -- but NEVER a ledger row that continues past that
    notehead's box on BOTH sides (DECISIONS 2026-10-01, round 2: masking
    the whole box erased the real ledger printed straight through a
    neighbouring head). A row is "continuing" if ink is present in a
    short band immediately outside the box on both the left and the
    right; only then is it left alone. Otherwise (the head's own ink,
    which does not reach past its own box) it is blanked, as before.
    """
    out = ink.copy()
    check_px = max(2, int(round(0.10 * spacing)))
    h, w = out.shape
    for (bx0, by0, bx1, by1) in exclude_boxes:
        ex0, ey0 = max(int(bx0), x0), max(int(by0), yy0)
        ex1, ey1 = min(int(bx1) + 1, x0 + w), min(int(by1) + 1, yy0 + h)
        if ex1 <= ex0 or ey1 <= ey0:
            continue
        col0, col1 = ex0 - x0, ex1 - x0
        row0, row1 = ey0 - yy0, ey1 - yy0
        left_lo = max(0, col0 - check_px)
        right_hi = min(w, col1 + check_px)
        for r in range(row0, row1):
            has_left = col0 > left_lo and out[r, left_lo:col0].any()
            has_right = right_hi > col1 and out[r, col1:right_hi].any()
            if has_left and has_right:
                continue  # a real ledger continuing on both sides -- keep it
            out[r, col0:col1] = False
    return out


def measure_ledger_rungs(
    img_gray: np.ndarray, staff_line_ys: list[float], x: float,
    head_y: float | None = None,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    head_box_x: "tuple[float, float] | None" = None,
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
    (x0, y0, x1, y1, same frame) -- their ink is removed before any span
    is measured, so a neighbouring head's ink can no longer supply one
    side of a "both sides" stub (DECISIONS 2026-10-01, Sean: "a second
    rung... accepted because its left stub is the neighbouring head's
    ink"). A row whose ink continues past that OTHER box on both sides
    (a real ledger drawn straight through it) is left alone (round 2:
    the whole-box blank used to erase exactly such a ledger). Never
    includes the subject's own box -- that is real evidence, not noise.

    `head_box_x`, when given, is the SUBJECT's own box (x0, x1), same
    frame. Every rung this function finds is then re-checked (round 3,
    DECISIONS 2026-10-01, Sean on `glyph/3/0/9/2/0`): its own row-span,
    measured generously wide (never clipped to the narrow probe window
    that finds candidate rungs in the first place -- clipping it there
    was tried and refused, see `_rung_row_clears_box`'s own docstring),
    must be LONGER than the subject's box width by
    `RUNG_BEYOND_BOX_MIN_SPACES` on each side combined -- otherwise it is
    simply the head's own widest row (which, by definition, reaches no
    wider than its own box) and is dropped, never counted as a rung.
    Checked AFTER candidate-finding, not folded into the stub/min-length
    test that finds candidates: boosting that test's own floor was tried
    first and refused -- in a dense chord it silently drops the shorter
    rows a genuine peak's own floor test depends on, breaking peak
    selection for a real, taller rung nearby (see FINDINGS).
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
        if exclude_boxes:
            ink = _exclude_other_heads_ink(ink, exclude_boxes, x0, yy0, spacing)
        bands = _band_centers(ink, x - x0, spacing, yy0)
        side_target = (
            head_y if head_y is not None and sign * (head_y - edge_y) > 0
            else None
        )
        rungs = _walk_ladder(edge_y, sign, bands, spacing, side_target)
        if head_box_x is not None:
            # Only a LATERAL neighbour (no x-overlap with the subject's
            # own box) is excluded from this verification crop -- a
            # chord stacks several noteheads at nearly the SAME x on one
            # stem, and one of those sitting just above/below the
            # subject is not "a neighbour's ink beside the rung" (what
            # exclusion exists for); blindly excluding it can wipe out
            # the subject's own real ledger ink across the whole shared
            # column (round 3, found verifying `glyph/3/0/9/2/0`'s real
            # ledger). The MAIN window's own exclusion (above) is
            # unaffected -- narrowing it the same way regressed a
            # different, already-fixed head (`glyph/3/0/0/2/3`).
            lateral = [
                b for b in (exclude_boxes or [])
                if b[2] <= head_box_x[0] or b[0] >= head_box_x[1]
            ]
            rungs = [
                ry for ry in rungs
                if _rung_row_clears_box(img_gray, ry, x, head_box_x, spacing,
                                        lateral)
            ]
        out[side] = rungs
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
    # ROUND 2 BUG (DECISIONS 2026-10-01, Sean on `glyph/3/0/0/2/3`, his C6:
    # "Fix the one line change that allowed the code to step further out"):
    # this used to RECOMPUTE the last rung's own step from its raw pixel
    # distance to the edge (`round(abs(last-edge_y)/half_step)`), rounding
    # against the NOMINAL half-step -- but hand-drawn ledgers are not
    # evenly spaced (same fact that motivated the wide-gap walk fix), so a
    # rung the walk correctly placed as the 2nd one out could measure
    # 4.9 half-steps from the edge instead of 4, and round UP to 5,
    # stepping one further out than the rung the walk actually found.
    # `_walk_ladder` already KNOWS each rung's step: it is simply 2
    # half-steps per rung, by the ladder's own construction (one rung per
    # staff space) -- the COUNT of rungs found, not a re-measurement of
    # the last one's raw position, is what must be trusted here.
    last_half_steps = 2 * len(rungs_y)
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


def ledger_measured_geometry(
    rungs_y: "list[float]", edge_y: float, sign: float, box_center_y: float,
    spacing: float,
) -> dict:
    """A THIRD far-head reader (2026-10-01, Sean on the outward-bias
    measurement: hand-drawn ledgers print wider than the staff spacing,
    so dividing a far head's raw pixel distance by the staff spacing
    overshoots outward by one step on every measured miss). Builds a
    ladder of KNOWN steps from the outer staff line (step 0) through each
    measured ledger (`rungs_y`, nearest-first -- step 2, 4, 6, ... by the
    ladder's own construction, never re-measured from raw pixels, same
    reasoning as `derive_far_head_step`'s own count-not-distance fix),
    then places the head's box CENTRE on that ladder by LINEAR
    INTERPOLATION between the two nearest measured rows -- never by
    dividing its distance by the nominal staff spacing. A head beyond the
    last measured ledger is placed by EXTRAPOLATING the LAST measured
    gap, not the staff spacing (the same fact that motivated the
    interpolation in the first place: a later gap is not reliably the
    same width as an earlier one, let alone the staff's own spacing).

    `rungs_y` must already reflect Sean's own rules for a real rung
    (both-side stubs beyond the head's own box, another head's ink is
    never a stub) -- i.e. the SAME list `measure_ledger_rungs(...,
    exclude_boxes=..., head_box_x=...)` returns; this function does no
    ink reading of its own, only the ladder arithmetic.

    No ledgers measured at all -> `offset=None`, reason `no_ledger_
    ladder` -- the caller falls back to plain geometry and counts it;
    never guessed.
    """
    if not rungs_y:
        return dict(offset=None, reason="no_ledger_ladder")
    ladder_y = [edge_y] + list(rungs_y)
    ladder_step = [2 * i for i in range(len(ladder_y))]
    dist = [sign * (y - edge_y) for y in ladder_y]
    target = sign * (box_center_y - edge_y)

    if target <= dist[-1]:
        for i in range(len(dist) - 1):
            if dist[i] <= target <= dist[i + 1]:
                if dist[i + 1] != dist[i]:
                    frac = (target - dist[i]) / (dist[i + 1] - dist[i])
                else:
                    frac = 0.0
                step = ladder_step[i] + frac * (ladder_step[i + 1] - ladder_step[i])
                return dict(offset=int(round(step)),
                           reason=f"interpolated between measured step "
                                  f"{ladder_step[i]} and {ladder_step[i + 1]}")
        # target is before the edge itself (an on-staff box centre) --
        # clamp to the edge rather than guess a negative ladder index.
        return dict(offset=0, reason="target at or before the staff edge")

    # Beyond the last measured ledger: extrapolate by the LAST measured
    # gap, never the nominal staff spacing.
    last_gap = dist[-1] - dist[-2] if len(dist) >= 2 else dist[-1]
    if last_gap <= 0:
        return dict(offset=ladder_step[-1],
                   reason="degenerate last gap -- cannot extrapolate")
    extra_steps = (target - dist[-1]) / last_gap * 2.0
    step = ladder_step[-1] + extra_steps
    return dict(offset=int(round(step)),
               reason=f"extrapolated beyond the last measured ledger "
                      f"(gap {last_gap:.1f}px, {extra_steps:.2f} steps out)")
