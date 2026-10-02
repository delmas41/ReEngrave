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
# FAULT 1 (round 5, DECISIONS 2026-10-0x): round 1's widen trigger only
# fired when the TARGET itself sat beyond `base_upper` -- but on
# `glyph/1/0/10/8/1` (Litolff p1) the target (the head's own y) sits
# WITHIN base_upper by a hair (21.24 vs 21.26 px) while the only real
# candidate band sits just OUTSIDE it (22.5 vs 21.26 px): the window never
# widens at all, the walk finds nothing, and the head abstains even though
# a real rung is one pixel away. Widen whenever the strict window comes up
# EMPTY and a target is known, regardless of whether the target itself
# would have fit -- the widened upper bound is never less than the old
# one, so this can only ADD candidates the strict window missed, never
# remove one it already had.
NEIGHBOR_CONTINUES_MARGIN_SPACES = 0.30
# FAULT 1 (round 5): the "does this other head's ink continue past its
# OWN box on both sides" check (round 2's `_exclude_other_heads_ink`) used
# a fixed `check_px` margin measured ONLY within the already-cropped
# candidate window -- for a chord stacking several heads at nearly the
# same x (`glyph/3/0/9/2/0`, `glyph/3/0/9/3/5`, Litolff p3), the excluded
# neighbour's own box is nearly as wide as that window, leaving only a
# few px of margin on each side: not enough room for the old fixed check
# to prove the real ledger between the two heads continues past it, so a
# genuine CLEAN MIDDLE LEDGER between two stacked heads was dropped
# entirely (abstain, never a false rung). Reading directly off the FULL
# page image -- never the window's own crop, same lesson as round 3's
# `_rung_row_clears_box` -- with this wider margin finds it (measured:
# 0.30 spacing margin, read on the full image, recovers both real cases;
# the window's own ~0.10-spacing check_px could not, however widened,
# because the window itself ran out of room first).
DRIFT_FOLLOW_MIN_PX_SPACES = 0.15
# FAULT 2 (round 5): the plain candidate window (+-WINDOW_HALF_WIDTH_SPACES,
# 2.2 spacing wide total) cannot fit a one-sided span long enough to pass
# RUNG_MIN_LEN_SPACES (1.3) while failing the OTHER side's stub
# (RUNG_STUB_MIN_SPACES, 0.15) at all -- the arithmetic is exact: a span
# starting just past the near-side stub (1.1 - 0.15 = 0.95 spacing from
# centre) and 1.3 spacing long would need to reach 1.15 spacing from
# centre, 0.05 spacing PAST the plain window's own edge (1.1). So a one-
# sided rung can never be seen at all without more room. Only when
# `head_box_y` is supplied (a caller that knows the subject and wants
# the one-sided rule) is the ink window widened to make room for it --
# every pre-existing caller (`head_box_y=None`) keeps the old, narrower
# window and is completely unaffected.
ONE_SIDED_WINDOW_HALF_WIDTH_SPACES = WINDOW_HALF_WIDTH_SPACES + RUNG_MIN_LEN_SPACES
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
    head_box_y: "tuple[float, float] | None" = None,
) -> list[float]:
    """Thin bands of long ink spans crossing x=cx_local. Returns centre ys
    in image coordinates (y_offset is the window's top row).

    A row's span is its ink runs merged across white gaps up to
    RUNG_BRIDGE_GAP_SPACES — the rung printed THROUGH an on-line hollow
    notehead is split by the head's white counter and no single run crosses
    the probe column there.

    `head_box_y`, when given, is the SUBJECT's own box (y0, y1) in the
    SAME image coordinates as `y_offset`. FAULT 2 (round 5, DECISIONS
    2026-10-0x, Sean: "a ledger above/below the head sitting in a space
    may extend on ONE side only"): the both-sides stub test applies only
    to a row that runs THROUGH the head (its y falls inside `head_box_y`)
    -- there, both sides are required exactly as before, because a
    one-sided span there is indistinguishable from the head's own
    outline. A row whose y falls OUTSIDE the head's own box cannot be the
    head's outline by construction, so a long enough span reaching past
    the probe column on EITHER side alone (never neither) is accepted as
    a real ledger beside the head. `head_box_y=None` (the default, and
    every pre-existing caller) keeps the old both-sides-always behaviour.
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
        through_head = (
            head_box_y is not None
            and head_box_y[0] <= (yi + y_offset) <= head_box_y[1]
        )
        best = 0.0
        for s, e in spans:
            if e - s < min_len or s > hi or e < lo:
                continue
            both_sides = s <= stub_lo and e >= stub_hi
            # A rung must cross the probe column AND extend at least a
            # stub past the probed x on BOTH sides -- a span that is long
            # overall but lopsided (e.g. a merged bridge that pulled in
            # unrelated ink far to one side while barely touching the
            # other) is not a ledger drawn through this head (DECISIONS
            # 2026-10-01). FAULT 2 (round 5): that requirement is for a
            # row THROUGH the head only -- a row outside the head's own
            # box cannot be the head's outline, so one real side is
            # enough (Sean: a ledger beside a head in a space "may extend
            # on ONE side only").
            one_side = (not through_head and head_box_y is not None
                        and (s <= stub_lo or e >= stub_hi))
            if both_sides or one_side:
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


def _select_next_candidate(
    anchor: float, sign: float, bands: list[float], pitch: float,
    spacing: float, target_y: float | None,
) -> "tuple[float | None, bool]":
    """One step of `_walk_ladder`'s own selection rule, factored out so
    the drift-following rescan (`measure_ledger_rungs`, round 5) can reuse
    it against a freshly-probed `bands` list without duplicating the
    window/widen arithmetic. Returns (candidate_y_or_None, widened).
    """
    base_upper = WALK_WINDOW[1] * pitch
    cands = [
        b for b in bands
        if WALK_WINDOW[0] * pitch <= sign * (b - anchor) <= base_upper
    ]
    widened = False
    if not cands and target_y is not None:
        # FAULT 1 (round 5, DECISIONS 2026-10-0x, `glyph/1/0/10/8/1`):
        # widen whenever the strict window is empty and a target is
        # known -- not only when the target ITSELF sits beyond
        # `base_upper`. The target can sit just inside the window while
        # the only real candidate band sits a hair past it (hand-drawn
        # ledger spacing is not exact); `upper` never shrinks below the
        # old `base_upper`, so this only ever ADDS candidates the old,
        # narrower trigger would have missed.
        dist_to_target = sign * (target_y - anchor)
        upper = max(base_upper, dist_to_target) + TARGET_SLACK_SPACES * spacing
        cands = [
            b for b in bands
            if WALK_WINDOW[0] * pitch <= sign * (b - anchor) <= upper
        ]
        if cands:
            widened = True
    if not cands:
        return None, False
    if widened:
        best = min(cands, key=lambda b: sign * (b - anchor))
    else:
        expected = anchor + sign * pitch
        best = min(cands, key=lambda b: abs(b - expected))
    return best, widened


def _row_ink_center(
    img_gray: np.ndarray, y: float, x_guess: float, spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
) -> "float | None":
    """The x-centre of the widest ink run crossing row `y` near
    `x_guess`, read directly off the full page image (round 5, FAULT 3) --
    used only to tell the drift-following rescan in `measure_ledger_rungs`
    WHERE a just-found rung is actually centred, so the NEXT step's probe
    column can follow it instead of staying fixed at the original `x`.
    Returns None where no ink crosses there at all.
    """
    h, w = img_gray.shape
    y_i = int(round(y))
    if not (0 <= y_i < h):
        return None
    margin = int(round(WINDOW_HALF_WIDTH_SPACES * spacing))
    x0 = max(0, int(round(x_guess)) - margin)
    x1 = min(w, int(round(x_guess)) + margin)
    if x1 <= x0:
        return None
    row_band = img_gray[max(0, y_i - 1):min(h, y_i + 2), x0:x1]
    if row_band.size == 0:
        return None
    thr = _otsu_threshold(row_band)
    ink = img_gray[y_i, x0:x1] <= thr
    if exclude_boxes:
        ink2d = ink.reshape(1, -1).copy()
        ink2d = _exclude_other_heads_ink(ink2d, exclude_boxes, x0, y_i, spacing)
        ink = ink2d[0]
    cols = np.flatnonzero(ink)
    if cols.size == 0:
        return None
    bridge = RUNG_BRIDGE_GAP_SPACES * spacing
    runs: list[list[int]] = [[int(cols[0]), int(cols[0])]]
    for c in cols[1:]:
        c = int(c)
        if c - runs[-1][1] <= bridge:
            runs[-1][1] = c
        else:
            runs.append([c, c])
    s, e = max(runs, key=lambda r: r[1] - r[0])
    return x0 + (s + e) / 2.0


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
        best, _widened = _select_next_candidate(
            anchor, sign, bands, pitch, spacing, target_y
        )
        if best is None:
            break
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
    img_gray: "np.ndarray | None" = None, thr: "int | None" = None,
) -> np.ndarray:
    """Remove another notehead's own ink from `ink` (boolean, already
    thresholded) -- but NEVER a ledger row that continues past that
    notehead's box on BOTH sides (DECISIONS 2026-10-01, round 2: masking
    the whole box erased the real ledger printed straight through a
    neighbouring head). A row is "continuing" if ink is present in a
    short band immediately outside the box on both the left and the
    right; only then is it left alone. Otherwise (the head's own ink,
    which does not reach past its own box) it is blanked, as before.

    `img_gray`/`thr`, when given (round 5, FAULT 1, DECISIONS
    2026-10-0x): when the narrow local margin inside `ink`'s own crop
    finds no ink on one side, re-check a WIDER margin read directly off
    the full page image before giving up. A chord stacking several
    noteheads at nearly the same x (`glyph/3/0/9/2/0`, `glyph/3/0/9/3/5`,
    Litolff p3) can leave an excluded neighbour's box nearly as wide as
    the candidate window itself, with only a couple of px of margin
    inside the crop on each side -- not enough for the narrow check to
    prove a real ledger between the two heads continues past it, so it
    was dropped as "the neighbour's own ink" even though it is the
    subject's own real rung. Measured: a 0.30-spacing margin read off the
    full image (never the window's own narrower crop) recovers both
    cases. `img_gray=None` keeps the exact old behaviour (every
    pre-existing caller).
    """
    out = ink.copy()
    check_px = max(2, int(round(0.10 * spacing)))
    wide_margin = int(round(NEIGHBOR_CONTINUES_MARGIN_SPACES * spacing))
    h, w = out.shape
    img_h, img_w = img_gray.shape if img_gray is not None else (0, 0)
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
            if not (has_left and has_right) and img_gray is not None and thr is not None:
                abs_y = yy0 + r
                # Read against the box's TRUE (un-clipped) edges, never
                # `ex0`/`ex1` -- those are clamped to the candidate
                # window's own x-range, and when the window happens to
                # start partway through the excluded neighbour's real
                # box (as a window can, near a page/cell edge), checking
                # a margin "before ex0" would look INSIDE that neighbour's
                # own ink and wrongly call it a continuation.
                true_x0, true_x1 = int(bx0), int(bx1) + 1
                if 0 <= abs_y < img_h:
                    wl0, wl1 = max(0, true_x0 - wide_margin), true_x0
                    wr0, wr1 = true_x1, min(img_w, true_x1 + wide_margin)
                    wide_left = img_gray[abs_y, wl0:wl1] if wl1 > wl0 else None
                    wide_right = img_gray[abs_y, wr0:wr1] if wr1 > wr0 else None
                    has_left = bool(wide_left is not None and wide_left.size
                                    and (wide_left <= thr).any())
                    has_right = bool(wide_right is not None and wide_right.size
                                      and (wide_right <= thr).any())
            if has_left and has_right:
                continue  # a real ledger continuing on both sides -- keep it
            out[r, col0:col1] = False
    return out


def measure_ledger_rungs(
    img_gray: np.ndarray, staff_line_ys: list[float], x: float,
    head_y: float | None = None,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    head_box_x: "tuple[float, float] | None" = None,
    head_box_y: "tuple[float, float] | None" = None,
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

    `head_box_y`, when given (round 5, FAULT 2), is the SUBJECT's own box
    (y0, y1), same frame -- passed through to `_band_centers` so a row
    beside the head (outside its own box) may qualify as a rung with a
    real span on only ONE side, never both (Sean: a ledger "above/below
    the head sitting in a space may extend on ONE side only"). A row
    through the head (inside `head_box_y`) still needs both sides, as
    always. `head_box_y=None` keeps the old both-sides-everywhere rule.
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
            ink = _exclude_other_heads_ink(
                ink, exclude_boxes, x0, yy0, spacing, img_gray, thr
            )
        bands = _band_centers(ink, x - x0, spacing, yy0, head_box_y)
        side_target = (
            head_y if head_y is not None and sign * (head_y - edge_y) > 0
            else None
        )
        rungs = _walk_ladder(edge_y, sign, bands, spacing, side_target)

        # FAULT 3 (round 5, DECISIONS 2026-10-0x, Sean: "the rungs of one
        # vertical stack are not aligned in x (hand-drawn)... let the
        # probe window for each successive rung follow the previous
        # rung's measured x-extent... rather than one fixed column
        # window"). One extra, drift-corrected step: if at least one rung
        # was found at the FIXED column `x`, re-measure that rung's own
        # ink run to see where it is actually centred, and -- only if it
        # has genuinely drifted -- retry the NEXT step's search at THAT
        # x instead of `x`, so a rung the fixed column cannot reach (it
        # has wandered past the probe window entirely) is not silently
        # lost. Never invents a rung the ink does not show: if nothing
        # qualifies at the drifted column either, the plain-column result
        # stands unchanged.
        if rungs:
            drift_x = _row_ink_center(img_gray, rungs[-1], x, spacing, exclude_boxes)
            if (drift_x is not None
                    and abs(drift_x - x) >= DRIFT_FOLLOW_MIN_PX_SPACES * spacing):
                anchor = rungs[-1]
                pitch = abs(rungs[-1] - (rungs[-2] if len(rungs) > 1 else edge_y))
                nx0 = int(max(0, drift_x - WINDOW_HALF_WIDTH_SPACES * spacing))
                nx1 = int(min(w, drift_x + WINDOW_HALF_WIDTH_SPACES * spacing))
                upper = WALK_WINDOW[1] * pitch + TARGET_SLACK_SPACES * spacing
                ny0 = int(max(0, min(anchor, anchor + sign * upper)))
                ny1 = int(min(h, max(anchor, anchor + sign * upper)))
                if nx1 > nx0 and ny1 - ny0 >= 2:
                    nwindow = img_gray[ny0:ny1, nx0:nx1]
                    nthr = _otsu_threshold(nwindow)
                    nink = nwindow <= nthr
                    if exclude_boxes:
                        nink = _exclude_other_heads_ink(
                            nink, exclude_boxes, nx0, ny0, spacing, img_gray, nthr
                        )
                    nbands = _band_centers(
                        nink, drift_x - nx0, spacing, ny0, head_box_y
                    )
                    extra, _ = _select_next_candidate(
                        anchor, sign, nbands, pitch, spacing, side_target
                    )
                    if extra is not None and all(
                        abs(extra - ry) > 1.0 for ry in rungs
                    ):
                        rungs.append(extra)

        # FAULT 2 (round 5, DECISIONS 2026-10-0x, Sean: "a ledger
        # above/below the head sitting in a space may extend on ONE side
        # only"). A one-sided span cannot satisfy RUNG_MIN_LEN_SPACES
        # within the plain window at all (see
        # ONE_SIDED_WINDOW_HALF_WIDTH_SPACES's own docstring -- it is 0.05
        # spacing too narrow, by construction), so widening the PRIMARY
        # window was tried and refused here: it pulls extra ink into the
        # bands the ordinary both-sides walk already depends on and
        # regressed real heads (Litolff 33->27 right on the truth set).
        # Instead, one extra SUPPLEMENTARY step, exactly like the FAULT 3
        # drift step above: only a WIDER crop, only for the one step past
        # the current anchor, only ever ADDING a rung the plain window
        # could not represent at all -- it can never remove or change one
        # the plain walk already found.
        if head_box_y is not None:
            anchor = rungs[-1] if rungs else edge_y
            pitch = abs(rungs[-1] - (rungs[-2] if len(rungs) > 1 else edge_y)) \
                if rungs else spacing
            wide_half = ONE_SIDED_WINDOW_HALF_WIDTH_SPACES * spacing
            wx0 = int(max(0, x - wide_half))
            wx1 = int(min(w, x + wide_half))
            upper = WALK_WINDOW[1] * pitch + TARGET_SLACK_SPACES * spacing
            wy0 = int(max(0, min(anchor, anchor + sign * upper)))
            wy1 = int(min(h, max(anchor, anchor + sign * upper)))
            if wx1 > wx0 and wy1 - wy0 >= 2:
                wwindow = img_gray[wy0:wy1, wx0:wx1]
                wthr = _otsu_threshold(wwindow)
                wink = wwindow <= wthr
                if exclude_boxes:
                    wink = _exclude_other_heads_ink(
                        wink, exclude_boxes, wx0, wy0, spacing, img_gray, wthr
                    )
                wbands = _band_centers(wink, x - wx0, spacing, wy0, head_box_y)
                one_sided_target = side_target if not rungs else None
                extra2, _ = _select_next_candidate(
                    anchor, sign, wbands, pitch, spacing, one_sided_target
                )
                if extra2 is not None and all(
                    abs(extra2 - ry) > 1.0 for ry in rungs
                ):
                    rungs.append(extra2)

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


# ─────────────────────────────────────────────────────────────────────────
# round 6 (2026-10-0x) — stacked thirds imply a ledger between them
# ─────────────────────────────────────────────────────────────────────────
#
# DECISIONS 2026-10-0x, Sean, on round 5's flute chords (`glyph/3/0/0/2/1`,
# `/2/4`, `/2/9`, `/6/2` — the ledger hidden inside the merged blob between
# two stacked heads was never found): "when there are multiple note heads
# stacked in thirds and neither of them has a line through them then there
# must be a line between them and to go looking for it."
#
# Measured on the three real Litolff p3 chord-mate pairs this round names
# (`glyph/3/0/0/2/4`+`/2/9`, `/2/1`+`/2/3`, `/6/1`+`/6/2`): centre-to-centre
# distance 0.81, 0.915 and 1.12 staff spaces — a THIRD (both heads land in
# a SPACE; the ladder's own even/odd half-step spelling makes two spaces
# one rung apart exactly a third in pitch). The range below is that
# measured spread with slack on each side for hand-drawn variance, never
# literal "exactly 1.0".
THIRD_STACK_SPACING_RANGE = (0.70, 1.25)
# A row at the implied rung's own y need only clear the UNION blob's own
# width by this margin on ONE side (not both) -- the convention itself
# already guarantees the ledger exists ("there must be a line between
# them"), so finding it is a confirmation, not the usual two-sided proof
# a stand-alone candidate needs. Same scale as RUNG_STUB_MIN_SPACES.
THIRD_STACK_STUB_MARGIN_SPACES = 0.15
# How close an existing rung must sit to a head's own box to count as
# "a line through it" (DECISIONS: a pair where EITHER head already has a
# line through it gets nothing implied) -- a few px of slack for the
# box/ink measurement slop already documented elsewhere in this module.
THROUGH_HEAD_TOL_PX = 2.0


def heads_are_a_third_apart(
    box_a: "tuple[float, float, float, float]",
    box_b: "tuple[float, float, float, float]",
    spacing: float,
    tol: "tuple[float, float]" = THIRD_STACK_SPACING_RANGE,
) -> bool:
    """True if two notehead boxes belong to the same chord/stem (their x
    ranges overlap) and their centres sit `tol` staff spaces apart
    (DECISIONS 2026-10-0x) -- the geometric half of Sean's "stacked in
    thirds" guard. Says nothing about which side of the staff they are
    on, or whether either already has a line through it -- callers check
    those separately (`far_head_needs_ledger_read`, `has_through_head_
    rung`), per the rule's own guards (CLAUDE.md rule 8: only outside the
    staff, only when both qualify)."""
    ax0, _ay0, ax1, _ay1 = box_a
    bx0, _by0, bx1, _by1 = box_b
    if ax1 <= bx0 or bx1 <= ax0:
        return False  # no x-overlap -- not one chord/stem
    cy_a = (box_a[1] + box_a[3]) / 2.0
    cy_b = (box_b[1] + box_b[3]) / 2.0
    if spacing <= 0:
        return False
    dist_sp = abs(cy_a - cy_b) / spacing
    return tol[0] <= dist_sp <= tol[1]


def third_stack_rung(
    img_gray: np.ndarray,
    box_outer: "tuple[float, float, float, float]",
    box_inner: "tuple[float, float, float, float]",
    spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    require_thin_flat: bool = False,
) -> dict:
    """The ledger that MUST run between two chord-mates stacked a third
    apart outside the staff (DECISIONS 2026-10-0x), when NEITHER already
    has a line through it. Looks for it at the exact MIDPOINT between
    their centres: a thin band there that clears the UNION of the two
    boxes' own width by `THIRD_STACK_STUB_MARGIN_SPACES` on AT LEAST ONE
    side is ink-CONFIRMED (returned at the midpoint y -- this module does
    not re-centre within the small probe band, the convention already
    names where to look); otherwise the rung is IMPLIED at that exact
    midpoint and never guessed at a different y (CLAUDE.md rule 8).

    `exclude_boxes`, when given, blanks any OTHER (non-pair) notehead's
    own ink that is laterally outside the union blob -- never a box that
    overlaps the blob in x, which could only be one of the pair's own
    heads or genuinely continuing ink, same reasoning as the rest of
    this module's exclusion logic.

    Returns `{"y": float, "confirmed": bool}` -- always returns a value
    (the convention states the ledger EXISTS; "confirmed" only says
    whether this reader's own ink check happened to see it).
    """
    cy_outer = (box_outer[1] + box_outer[3]) / 2.0
    cy_inner = (box_inner[1] + box_inner[3]) / 2.0
    mid_y = (cy_outer + cy_inner) / 2.0
    blob_x0 = min(box_outer[0], box_inner[0])
    blob_x1 = max(box_outer[2], box_inner[2])
    margin = THIRD_STACK_STUB_MARGIN_SPACES * spacing
    h, w = img_gray.shape
    y_i = int(round(mid_y))
    y0, y1 = max(0, y_i - 2), min(h, y_i + 3)
    x0 = max(0, int(blob_x0 - margin - 2))
    x1 = min(w, int(blob_x1 + margin + 2))
    if y1 <= y0 or x1 <= x0:
        return dict(y=mid_y, confirmed=False)
    window = img_gray[y0:y1, x0:x1].copy()
    if exclude_boxes:
        lateral = [
            b for b in exclude_boxes
            if b[2] <= blob_x0 or b[0] >= blob_x1
        ]
        for (bx0, by0, bx1, by1) in lateral:
            ex0, ey0 = max(int(bx0), x0), max(int(by0), y0)
            ex1, ey1 = min(int(bx1) + 1, x1), min(int(by1) + 1, y1)
            if ex1 > ex0 and ey1 > ey0:
                window[ey0 - y0:ey1 - y0, ex0 - x0:ex1 - x0] = 255
    thr = _otsu_threshold(window)
    ink = window <= thr
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
    blob_local0, blob_local1 = blob_x0 - x0, blob_x1 - x0
    for s, e in runs:
        if s <= blob_local0 - margin or e >= blob_local1 + margin:
            if require_thin_flat:
                # round 7: a run merely clearing the blob's own width can
                # still be a STEM passing near the midpoint, not the
                # ledger -- measured on `glyph/3/0/0/2/4`+`/2/9` (Litolff
                # p3): the column directly under the chord's shared stem
                # reads 37-39px thick at this exact y, nowhere near a
                # printed line's 4-5px. Re-validate at the OVERHANGING
                # side's own outer edge (where the run clears the blob --
                # a one-sided ledger's overhang, never the blob's own
                # centre, which the stem can occupy instead) with the
                # same one-sided-OK thin+flat test used elsewhere in this
                # module before calling it CONFIRMED; a run that clears
                # the blob's width but fails this still COUNTS the
                # position (the convention states the ledger exists with
                # no ink required) -- it is simply reported IMPLIED, not
                # falsely ink-confirmed.
                beyond_right = e >= blob_local1 + margin
                probe_x = (x0 + e - 2) if beyond_right else (x0 + s + 2)
                if not rung_is_thin_and_flat(img_gray, mid_y, probe_x, spacing,
                                             require_all_sides=False):
                    continue
            return dict(y=mid_y, confirmed=True)
    return dict(y=mid_y, confirmed=False)


def insert_rung(
    rungs_y: "list[float]", sign: float, new_y: float, tol_px: float = 3.0,
) -> "list[float]":
    """Insert `new_y` into a nearest-edge-first rung list (round 6) at
    its correct sorted position, unless a rung already sits within
    `tol_px` of it (never a duplicate). Nearest-edge-first means
    DESCENDING y above the staff (sign=-1) and ASCENDING y below it
    (sign=+1); `sign * y` sorts ascending for both cases."""
    if any(abs(new_y - ry) <= tol_px for ry in rungs_y):
        return list(rungs_y)
    out = list(rungs_y) + [new_y]
    out.sort(key=lambda ry: sign * ry)
    return out


# ─────────────────────────────────────────────────────────────────────────
# round 7 (2026-10-01) -- one-sided ledgers re-validated by FLATNESS, the
# two-edges-of-one-ledger merge, the duplicate-half-spacing fault, and a
# wide-gap "look here" search
# ─────────────────────────────────────────────────────────────────────────
#
# Sean's verdicts on round 6's three diagnostic crops (`out/print/ledgers/
# r6/`), DECISIONS 2026-10-01:
#
#   (a) `glyph/3/0/0/2/4`+`/2/9`: a real ledger between/under the pair
#       extends on ONE side only, past a "weird ink blotch" -- "the thin
#       horizontal line is clearly there". Measured directly off the real
#       page (`beethoven5-litolff`, p3, 600 dpi, `_render_page_gray` --
#       pure PDF rendering, no gather): the column crossing `/2/4`'s own
#       probe x is SOLID ink from y=383 to y=435 (53px, unbroken) -- the
#       "through-head" rung round 6 found at y=395 sits inside that 53px
#       blob. A clean staff line on the SAME page, SAME raster, measures
#       4-5px thick (sampled at x=700, y 500-750, clear of ink) against a
#       15.5-16px line spacing -- a real line is ~0.29 of the spacing, not
#       53/15.5=3.4. The round-5 one-sided span test (`head_box_y` in
#       `_band_centers`) already exists but was never re-checked for this:
#       its 95%-of-peak RELATIVE floor can mistake a flag's curl or a
#       merged chord's own widest row -- locally narrower than its very
#       wide neighbours -- for a thin isolated line. `rung_is_thin_and_
#       flat` re-validates a candidate by its ABSOLUTE vertical ink run at
#       several x offsets across its own claimed length: thin (near the
#       page's own measured line thickness) AND flat (the same thickness
#       at each sampled x -- a curve or a flag's taper is not flat).
#   (b) `glyph/3/0/0/2/1`+`/2/3`: already correct -- a CONTROL. Its own
#       printed ledgers (DECISIONS 2026-09-30: 396.6/413.3/433.2) are
#       19.9px and 16.7px apart on a 15.5px spacing (1.28 and 1.08
#       spacings) -- an ordinary ladder, nothing for round 7's merge or
#       duplicate-drop to touch; round 7 must leave this pair's answer
#       unchanged.
#   (c) `glyph/3/0/0/6/1`+`/6/2`: the two existing rungs at 417.5 and
#       414.5 (3px apart -- UNDER the page's own measured ~4-5px line
#       thickness) are the TOP and BOTTOM edge of ONE thick ledger, not
#       two separate ones. `merge_close_rungs` folds any two rungs closer
#       than `MERGE_THICKNESS_RATIO` x the measured thickness into one, at
#       their centre.
#
#   Plus, same session: a rung sitting close to HALF a local spacing from
#   its neighbour is a duplicate of one of that neighbour's own edges, not
#   a separate ledger a half-step out (every real ledger the walk accepts
#   is a FULL space from the last one, `WALK_WINDOW` 0.65-1.35) --
#   `drop_duplicate_half_spacing_rung`.
#
#   And (Sean, final wording this session): "A gap should have a ledger
#   line but it is possible for it not to be there due to hand drawn
#   spacing." A wide gap (~2 local spacings) between two found rungs is a
#   place to LOOK -- a RELAXED, one-sided-OK, thin-flat search
#   (`find_rung_in_gap`) -- and if ink confirms it, it is counted
#   (`found_in_gap`); a clean gap implies NOTHING (unlike the stacked-
#   thirds convention, a gap alone never forces a ledger to exist -- only
#   two heads of ONE CHORD a third apart do that, round 6, unchanged: "The
#   gap doesn't require a ledger line but in between notes a 3rd apart
#   does").
#
# Every round-7 function is additive and opt-in: the existing, already
# print-verified both-sides walk (`_walk_ladder`/`_band_centers` with
# `head_box_y=None`) is untouched, and the primary real-data score's own
# `measure_ledger_rungs` call keeps `head_box_y=None` exactly as round 5
# measured (a net negative there). Round 7 is wired ONLY into the round-6
# stacked-thirds path and its own `has_through_head_rung` guard
# (`score_truth_set_rungs.reader_absolute_position`).

# A real printed line on this corpus measures 4-5px against a 15.5-16px
# spacing (~0.29), measured directly off the page (see docstring above) --
# matches `staff_line_removal.MAX_LINE_THICKNESS_SPACES` (0.35) already
# used elsewhere for the same quantity; kept distinct here (ledgers are
# hand-drawn, slightly more variable than engraved staff lines) with the
# same order-of-magnitude slack.
LEDGER_THICKNESS_MAX_SPACES = 0.35
# Flatness is checked at the centre and at +-0.35 spacing either side of
# it -- far enough to clear a single notehead's own narrow cap but short
# enough to stay within one claimed rung's own length.
FLATNESS_SAMPLE_OFFSETS_SPACES = (0.0, -0.35, 0.35)
# Two rungs this close (relative to the page's own measured thickness) are
# the top and bottom edge of ONE thick ledger, not two (`glyph/3/0/0/6/1`
# measured 3px apart against a 4-5px thickness -- comfortably under 1.5x).
MERGE_THICKNESS_RATIO = 1.5
# A rung whose gap to its neighbour falls in this band (centred on 0.5
# spacing) is that neighbour's own duplicate edge, not a ledger a
# half-step out -- every real ledger this module's walk accepts is a FULL
# space (`WALK_WINDOW` 0.65-1.35) from the last one.
DUPLICATE_HALF_SPACING_RANGE = (0.35, 0.65)
# A gap this wide between two consecutive found rungs is worth a relaxed
# look -- centred on 2 local spacings (one skipped ledger), with slack for
# hand-drawn variance on each side.
GAP_FILL_RANGE_SPACINGS = (1.65, 2.35)


def _column_ink_run(
    img_gray: np.ndarray, y: float, x: float, spacing: float,
) -> "float | None":
    """The vertical thickness, in px, of the ink run crossing (y, x) at
    this SINGLE column -- the contiguous span of inked rows containing
    row y. `None` where (y, x) is not inked at all. A genuine printed
    line measures near its own print thickness regardless of which
    column it is sampled at; a row sitting inside a taller continuous
    blob (a flag's curl, a merged/oversized box's own ink) measures the
    FULL height of that blob instead, however locally `_band_centers`'
    own row-span happened to narrow at that one row (round 6's confound)."""
    h, w = img_gray.shape
    x_i, y_i = int(round(x)), int(round(y))
    if not (0 <= x_i < w and 0 <= y_i < h):
        return None
    margin = max(2, int(round(1.5 * spacing)))
    y0, y1 = max(0, y_i - margin), min(h, y_i + margin + 1)
    col = img_gray[y0:y1, x_i]
    thr = _otsu_threshold(col.reshape(-1, 1))
    ink = col <= thr
    yy = y_i - y0
    if not (0 <= yy < ink.size) or not ink[yy]:
        return None
    top = yy
    while top > 0 and ink[top - 1]:
        top -= 1
    bot = yy
    while bot + 1 < ink.size and ink[bot + 1]:
        bot += 1
    return float(bot - top + 1)


def rung_is_thin_and_flat(
    img_gray: np.ndarray, y: float, x_center: float, spacing: float,
    offsets: "tuple[float, ...]" = FLATNESS_SAMPLE_OFFSETS_SPACES,
    max_thickness_spaces: float = LEDGER_THICKNESS_MAX_SPACES,
    require_all_sides: bool = True,
) -> bool:
    """THIN: every sampled column's own vertical ink run at `y` measures
    no more than `max_thickness_spaces` of the local spacing. FLAT: those
    measurements agree with each other within HALF that tolerance -- a
    curved head edge or a flag's taper thickens steadily across x even
    while each individual sample stays under the thin cap; a genuine
    printed line's own thickness barely moves between two points on the
    same stroke. The CENTRE offset (0.0, always first in `offsets`) must
    always qualify; a column with no ink at all there fails outright.

    `require_all_sides=True` (the default, used by `has_through_head_rung`'s
    re-validation) requires every non-centre offset to qualify too -- a
    through-head rung has ink on both sides of the head by construction,
    so demanding both here costs nothing and only tightens the test.
    `require_all_sides=False` (used by `find_rung_in_gap`'s relaxed,
    one-sided-OK search) accepts the centre plus AT LEAST ONE side, same
    "one real side is enough" convention `_band_centers`'/`third_stack_
    rung`'s own one-sided logic already uses elsewhere in this module --
    a missing or disqualified side is simply dropped from the flatness
    comparison, never treated as a failure on its own.

    Used to re-validate a candidate BEFORE it is trusted as a real
    ledger -- never to find one (that is still `_band_centers`'/
    `third_stack_rung`'s own job)."""
    cap = max_thickness_spaces * spacing
    centre_off, side_offs = offsets[0], offsets[1:]
    t0 = _column_ink_run(img_gray, y, x_center + centre_off * spacing, spacing)
    if t0 is None or t0 > cap:
        return False
    measured = [t0]
    sides_ok = 0
    for off in side_offs:
        t = _column_ink_run(img_gray, y, x_center + off * spacing, spacing)
        if t is None or t > cap:
            if require_all_sides:
                return False
            continue
        measured.append(t)
        sides_ok += 1
    if not require_all_sides and sides_ok == 0:
        return False  # centre alone never confirms a HORIZONTAL line
    return (max(measured) - min(measured)) <= 0.5 * cap


def has_through_head_rung(
    rungs_y: "list[float]", box: "tuple[float, float, float, float]",
    tol_px: float = THROUGH_HEAD_TOL_PX,
    img_gray: "np.ndarray | None" = None, spacing: "float | None" = None,
) -> bool:
    """Does any already-found rung in `rungs_y` pass through this head's
    OWN box? (DECISIONS 2026-10-0x's guard: a pair where either head
    already has a line through it gets NOTHING implied -- the convention
    only forces a ledger between two heads that both lack one.)

    `img_gray`/`spacing`, when given (round 7): a candidate that sits in
    range is also re-validated by `rung_is_thin_and_flat` at the box's own
    x-centre before it counts -- round 6 measured that a confound (flag
    ink, an oversized merged box's own widest row) can register a false
    "through" rung and wrongly block the stacked-thirds guard on exactly
    the pairs it was built for. `img_gray=None` (the default, and every
    pre-existing caller) keeps the old proximity-only behaviour."""
    y0, y1 = box[1], box[3]
    cx = (box[0] + box[2]) / 2.0
    for ry in rungs_y:
        if not (y0 - tol_px <= ry <= y1 + tol_px):
            continue
        if img_gray is not None and spacing is not None:
            if not rung_is_thin_and_flat(img_gray, ry, cx, spacing):
                continue
        return True
    return False


def merge_close_rungs(
    rungs_y: "list[float]", sign: float, thickness_px: float,
    ratio: float = MERGE_THICKNESS_RATIO,
) -> "list[float]":
    """Folds any two ADJACENT rungs (in nearest-edge-first order) closer
    than `ratio` x `thickness_px` into one, at their centre -- the two
    edges of one thick ledger read as a top rung and a bottom rung
    (`glyph/3/0/0/6/1`: 417.5/414.5, 3px apart against a 4-5px measured
    line thickness). `rungs_y` is walked in nearest-edge-first order
    (ascending `sign * y`, same convention as `insert_rung`) so a merge
    cannot reorder the ladder."""
    if not rungs_y:
        return []
    ordered = sorted(rungs_y, key=lambda ry: sign * ry)
    cap = ratio * thickness_px
    out: "list[float]" = [ordered[0]]
    for ry in ordered[1:]:
        if abs(ry - out[-1]) <= cap:
            out[-1] = (out[-1] + ry) / 2.0
        else:
            out.append(ry)
    return out


def drop_duplicate_half_spacing_rung(
    rungs_y: "list[float]", sign: float, spacing: float,
    tol_range: "tuple[float, float]" = DUPLICATE_HALF_SPACING_RANGE,
    edge: "float | None" = None,
) -> "list[float]":
    """Drops a rung whose gap to the PREVIOUS (nearer-edge) rung in the
    ladder -- or to the staff EDGE itself, for the first rung, when `edge`
    is given -- falls within `tol_range` of a staff spacing. A half-
    spacing gap is that neighbour's own duplicate edge, never a genuine
    ledger a half-step out (every real ledger `_walk_ladder` accepts is a
    full space, 0.65-1.35, from the one before it). Without `edge`, the
    first rung (no predecessor to be a duplicate of) is never dropped."""
    if not rungs_y or spacing <= 0:
        return list(rungs_y)
    ordered = sorted(rungs_y, key=lambda ry: sign * ry)
    out: "list[float]" = []
    anchor = edge
    for ry in ordered:
        if anchor is not None:
            gap_sp = abs(ry - anchor) / spacing
            if tol_range[0] <= gap_sp <= tol_range[1]:
                continue  # duplicate edge of the anchor -- drop it
        out.append(ry)
        anchor = ry
    return out


def find_rung_in_gap(
    img_gray: np.ndarray, y_lo: float, y_hi: float, x_center: float,
    spacing: float, head_box_x: "tuple[float, float] | None" = None,
) -> "float | None":
    """A RELAXED search for a thin, flat, one-sided-OK ledger strictly
    between `y_lo` and `y_hi` (a wide gap between two already-found
    rungs) -- the convention is "look here", not "it must be there"
    (Sean: a gap "should have a ledger line but it is possible for it not
    to be there due to hand drawn spacing"). Scans row by row for the
    thinnest, most isolated candidate and returns it only if
    `rung_is_thin_and_flat` confirms it at the box's own probe column (or
    `x_center` when no box is given); returns `None` on a clean gap --
    never guessed (CLAUDE.md rule 8)."""
    lo, hi = sorted((y_lo, y_hi))
    if hi - lo < 2:
        return None
    h, w = img_gray.shape
    x_i = int(round(x_center))
    if not (0 <= x_i < w):
        return None
    best_y: "float | None" = None
    best_thickness = float("inf")
    y = int(lo) + 1
    while y < int(hi):
        t = _column_ink_run(img_gray, float(y), x_i, spacing)
        if t is not None and t < best_thickness:
            best_thickness, best_y = t, float(y)
        y += 1
    if best_y is None:
        return None
    if not rung_is_thin_and_flat(img_gray, best_y, x_i, spacing,
                                 require_all_sides=False):
        return None
    return best_y
