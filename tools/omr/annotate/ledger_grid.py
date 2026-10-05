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
# RETIRED as a line-vs-space decision (DECISIONS 2026-10-01, four causes,
# cause D): a gap this size or larger used to be read as "on the next
# ledger, hidden under the head" by distance alone -- that guess put
# three real heads (tiles 6-8 of the neither-right sheet) one ledger too
# far out. `derive_far_head_step` now decides line-vs-space by direct
# evidence (`head_middle_rung_evidence`) for every positive gap, never by
# this threshold. Kept only as a historical constant (old tests import
# it); no code path still reads it.
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
    collapse_edges_box: "tuple[float, float, float, float] | None" = None,
    head_center_y: "float | None" = None,
    restore_masked_staff_side_rungs: bool = False,
) -> dict[str, list[float]]:
    """Measured ledger rung ys above and below the staff at column x.

    `restore_masked_staff_side_rungs` (lane-ledger-edge-fix, 2026-10-04;
    default False = bit-identical): see `restore_masked_staff_side_ledgers`.
    Needs `exclude_boxes` and `collapse_edges_box` (the
    subject's full box); otherwise it changes nothing.

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

    `collapse_edges_box`, when given (cause C, DECISIONS 2026-10-01,
    four causes), is the SUBJECT's own full box (x0, y0, x1, y1), same
    frame -- a SEPARATE, independent knob from `head_box_y` above (that
    one gates the one-sided rule, MEASURED NET NEGATIVE and held back;
    this one must not re-enable it by accident). After the walk, any two
    found rungs that are each merely this box's own top/bottom edge are
    dropped and, only where the ink itself shows a real line there, put
    back as the one genuine rung through the box's own middle
    (`collapse_head_edge_rungs_to_middle`). `collapse_edges_box=None`
    (the default) changes nothing.

    `head_center_y`, when given (2026-10-04), is the head's own traced
    centre row (page px, same frame as `collapse_edges_box`); it is only
    forwarded to the collapse's middle-row probe and replaces the box
    middle there. `None` = today's behaviour.
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
        if (restore_masked_staff_side_rungs and exclude_boxes
                and collapse_edges_box is not None):
            rungs = restore_masked_staff_side_ledgers(
                img_gray, ys, x, head_y, rungs, side, sign, spacing,
                collapse_edges_box, exclude_boxes)
        if collapse_edges_box is not None:
            # Cause C (DECISIONS 2026-10-01, four causes): accidental or
            # broken half-note ink beside the head can make two of the
            # rows above pass as rungs at the head's own top/bottom
            # edges -- never real ledgers (the box is ~1 staff space
            # tall; a genuine ledger pair never flanks it this close).
            # Drop them, and put back the one real rung at the head's
            # own middle only if the ink itself (with the same exclusions)
            # shows it there. A SEPARATE knob from `head_box_y` above --
            # see `collapse_edges_box`'s own docstring for why.
            rungs = collapse_head_edge_rungs_to_middle(
                rungs, sign, collapse_edges_box, img_gray, spacing,
                exclude_boxes, head_center_y,
            )
        out[side] = rungs
    return out


def derive_far_head_step(
    rungs_y: "list[float]", edge_y: float, sign: float, head_near_y: float,
    spacing: float,
    img_gray: "np.ndarray | None" = None,
    head_box: "tuple[float, float, float, float] | None" = None,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    head_center_y: "float | None" = None,
    near_edge_ledgers: bool = False,
) -> dict:
    """Sean's 2026-10-01 convention for turning a rung count into a step.

    `rungs_y` is one side's list from `measure_ledger_rungs` (nearest-edge
    first). `head_near_y` is the edge of the head's OWN box closest to the
    staff (its bottom for a head ABOVE the staff, its top for a head
    BELOW) -- never its centre; the gap is measured from there, not from
    wherever the box happens to be centred.

    Walks the SAME ladder arithmetic the reader already uses (2 half-steps
    per rung from the edge), but the THROUGH decision itself is now
    GOVERNED by evidence, not merely the decision between a further
    ledger and the space beyond it (coordinator, DECISIONS 2026-10-0x,
    on round 8's own gap: 5 of Sean's 8 named heads took the OLD
    "passes through" branch on distance alone BEFORE cause D's evidence
    check ever ran -- exactly the false through-head reading tiles 4-5
    (accidental ink) and 6-8 (a head just past a real ledger) describe):

      * no rung found at all -> ABSTAIN (nothing to count from).
      * the last rung sits at or beyond the head's near edge (by
        `TOUCH_TOL_SPACES` or more) -> a CANDIDATE through-rung, never
        taken on distance alone. It counts as passing through the head
        ONLY where `head_middle_rung_evidence` confirms a thin, flat
        line with stubs on BOTH sides at the head's own MIDDLE row
        (accidental/other-head ink excluded via `exclude_boxes`). Not
        evidenced -> this candidate is not a ledger at all (the head's
        own outline, or an accidental's edge) -- drop it and test the
        rung before it the SAME way (recursing outward toward the
        staff), never simply accepting it on the gap's raw size.
      * once a rung is reached that sits properly between the staff and
        the head (not overlapping its own box) -- "the last ledger
        before it" -- the SAME evidence decides line-vs-space exactly
        as cause D already did: evidenced -> the head is ON the NEXT
        ledger (one half-step and a half-step more out); not evidenced
        -> the head is in the SPACE beyond that last real ledger, never
        a guessed further one (CLAUDE.md rule 8).
      * every rung drops out this way (none ever sits between the staff
        and the head) -> ABSTAIN (`no_rung_before_the_head`) -- never a
        guess from ink that was only ever the head's own outline.

    `img_gray`/`head_box`/`exclude_boxes` omitted (every caller that has
    no image) means evidence can never be found, so a candidate that
    used to be accepted as "through" on distance alone is now ALWAYS
    dropped, never guessed -- a real behaviour change from before cause
    D existed, and the point of it (CLAUDE.md rule 8: "cannot tell" is
    never answered as "yes, a line").

    `near_edge_ledgers` (lane-ledger-edge-fix, 2026-10-04, Sean: "Start the
    fix"; default False = every caller before it, bit-identical): a rung
    that is NOT evidenced at the head's middle row but is a real, thin,
    flat ledger touching the head's NEAR-staff edge
    (`rung_is_near_edge_ledger`) is no longer dropped as the head's own
    outline -- it is counted, and the head sits in the SPACE beyond it
    (offset `2n + 1`, exactly as for a rung properly between staff and
    head). A rung at the FAR edge is never counted (it can only be
    another head's ledger or the outline), so the far-edge pop is
    unchanged.

    Returns `{"offset": int|None, "kind": "line"|"space"|None,
    "reason": str}`. `offset` is in half-steps outward from the edge; the
    caller adds it to (or subtracts it from, by `sign`) the edge's own
    staff position.
    """
    if not rungs_y or spacing <= 0:
        return dict(offset=None, kind=None, reason="no_rungs")
    # ONE question, asked ONCE, always at the head's own geometric
    # MIDDLE (never a candidate's own row -- manager review, DECISIONS
    # 2026-10-0x: a head sitting in the space beside a real ledger
    # touches that ledger at its OWN top/bottom edge, so probing at a
    # candidate's row let an edge-touching ledger read as "through" it.
    # Whether THIS rung passes through the head, or a hidden further
    # one exists beyond the last rung found, is the SAME fact about the
    # head -- is there a line at its own middle -- so it is computed
    # once and reused by every branch below.
    evidenced = head_middle_rung_evidence(
        img_gray, head_box, spacing, exclude_boxes, head_center_y
    )
    remaining = list(rungs_y)
    while remaining:
        last = remaining[-1]
        # ROUND 2 BUG (DECISIONS 2026-10-01, Sean on `glyph/3/0/0/2/3`,
        # his C6: "Fix the one line change that allowed the code to
        # step further out"): trust the walk's own COUNT (2 half-steps
        # per rung), never a re-measurement of the last one's raw pixel
        # position against the nominal half-step -- hand-drawn ledgers
        # are not evenly spaced, so that re-measurement could round a
        # correctly-placed 2nd rung up to a 3rd.
        last_half_steps = 2 * len(remaining)
        gap_spaces = (sign * (head_near_y - last)) / spacing
        if gap_spaces <= -TOUCH_TOL_SPACES:
            if evidenced:
                return dict(offset=last_half_steps, kind="line",
                           reason=f"last rung passes through the head "
                                  f"itself, confirmed by a jut connected "
                                  f"to it at the head's own middle row "
                                  f"(gap {gap_spaces:.2f} sp)")
            # cause D (coordinator, DECISIONS 2026-10-0x): not evidenced
            # AT THE HEAD'S OWN MIDDLE -- this rung only touches the
            # head's own edge, it was never a ledger running through
            # it (the head's own outline, or an accidental's edge).
            # Drop it and test the one before it -- unless it is a real
            # ledger printed against the head's NEAR edge (`near_edge_
            # ledgers`): then it is counted and the head is in the space
            # beyond it.
            if near_edge_ledgers and rung_is_near_edge_ledger(
                    img_gray, last, head_box, sign, spacing, exclude_boxes,
                    head_center_y):
                return dict(offset=last_half_steps + 1, kind="space",
                           reason=f"a thin flat ledger touches the head's "
                                  f"near edge (rung {gap_spaces:.2f} sp "
                                  f"inside the box): counted, head in the "
                                  f"space beyond it")
            remaining.pop()
            continue
        # `last` sits between the staff and the head (or touching it) --
        # a genuine candidate, "the last ledger before it". Decide
        # line-vs-space by the SAME evidence, never the gap's raw size.
        if evidenced:
            return dict(offset=last_half_steps + 2, kind="line",
                       reason=f"{gap_spaces:.2f} sp beyond the last clean "
                              f"rung -- a jut connected to the head's own "
                              f"middle, on at least one side")
        return dict(offset=last_half_steps + 1, kind="space",
                   reason=f"{gap_spaces:.2f} sp beyond the last clean "
                          f"rung -- no evidenced line at the head's own "
                          f"middle, space beyond it")
    return dict(offset=None, kind=None,
               reason="every found rung was the head's own outline, not "
                      "a ledger before it -- no_rung_before_the_head")


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


# How far past a box's own edge the round-7 through-rung re-validation
# probes for a STUB -- a through-head rung is by definition buried in the
# notehead's own (much taller) ink at the box's CENTRE, so centre-
# sampling can never confirm one; it must be checked where the line pokes
# out past the head instead, same scale as `RUNG_STUB_MIN_SPACES`.
THROUGH_RUNG_STUB_PROBE_SPACES = 0.25


def has_through_head_rung(
    rungs_y: "list[float]", box: "tuple[float, float, float, float]",
    tol_px: float = THROUGH_HEAD_TOL_PX,
    img_gray: "np.ndarray | None" = None, spacing: "float | None" = None,
) -> bool:
    """Does any already-found rung in `rungs_y` pass through this head's
    OWN box? (DECISIONS 2026-10-0x's guard: a pair where either head
    already has a line through it gets NOTHING implied -- the convention
    only forces a ledger between two heads that both lack one.)

    `img_gray`/`spacing`, when given (round 7): a candidate is also
    re-validated before it counts -- round 6 measured that a confound
    (flag ink, an oversized merged box's own widest row) can register a
    false "through" rung and wrongly block the stacked-thirds guard on
    exactly the pairs it was built for. The re-check is done at the
    box's own STUB points (just past its left and right edge), never at
    its centre: measured directly (`glyph/3/0/0/2/3`, a real print-
    verified through rung, DECISIONS 2026-09-30) -- the centre column
    reads 29-47px thick there, because a through rung by definition runs
    BEHIND the notehead's own (much taller) body ink; the SAME rung
    measures 4-5px, genuinely thin and flat, at both stubs just past the
    box's edges, which is where a through rung is actually visible as a
    line. At least ONE stub passing is enough (the convention's own
    both-sides rung-finding already required two-sided ink to get this
    far into `rungs_y` in the first place; this is a sanity re-check, not
    a re-derivation). `img_gray=None` (the default, and every
    pre-existing caller) keeps the old proximity-only behaviour."""
    y0, y1 = box[1], box[3]
    for ry in rungs_y:
        if not (y0 - tol_px <= ry <= y1 + tol_px):
            continue
        if img_gray is not None and spacing is not None:
            stub = THROUGH_RUNG_STUB_PROBE_SPACES * spacing
            left_x, right_x = box[0] - stub, box[2] + stub
            left_ok = rung_is_thin_and_flat(img_gray, ry, left_x, spacing,
                                            require_all_sides=False)
            right_ok = rung_is_thin_and_flat(img_gray, ry, right_x, spacing,
                                             require_all_sides=False)
            if not (left_ok or right_ok):
                continue
        return True
    return False


# Manager review of the design-3 sheet (DECISIONS 2026-10-0x, tiles 3,
# 4, 5, 6 and the new-wrong `glyph/3/0/0/2/9`): probing AT an already-
# found CANDIDATE's own row made a head sitting in the space just
# below (or above) a real ledger touch that ledger at its own TOP (or
# BOTTOM) edge -- the connectivity test then fired on the head's own
# edge and declared it "through" a ledger that is really the one
# BEFORE (or beyond) it. Sean's rule: the line must jut out of the head
# at the head's own MIDDLE row, not wherever a candidate happens to
# sit. Probed at the box's own vertical centre, +/- this tolerance (in
# staff spaces) -- narrow enough to stay clear of a box's own top/
# bottom edge for a realistically-sized head (~1 staff space tall), not
# a second, wider window.
MIDDLE_ROW_TOL_SPACES = 0.15


def head_middle_rung_evidence(
    img_gray: "np.ndarray | None",
    head_box: "tuple[float, float, float, float] | None",
    spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    head_center_y: "float | None" = None,
) -> bool:
    """Cause D's evidence test (DECISIONS 2026-10-01, "four causes behind
    the 8 far heads neither reader gets right", Sean on tiles 6-8:
    *"slightly low but should read as underneath that ledger line"* --
    the head sits in the SPACE beyond the last clean rung found, not on
    a FURTHER hidden one, unless the page actually shows a line there).
    Always probed at the head's own vertical MIDDLE (`(y0+y1)/2`),
    +/- `MIDDLE_ROW_TOL_SPACES` -- a rung touching only the head's top
    or bottom edge is the ledger BEFORE (or beyond) it, never through
    it, whatever the gap arithmetic or an already-found candidate's own
    row would otherwise suggest (manager review, DECISIONS 2026-10-0x:
    probing at a candidate's own row made an edge-touching ledger read
    as "through").

    Three refinements from Sean, same DECISIONS line, after round 8's
    real-data measurement showed the first (both-sides-required) design
    wrongly rejected known-good, print-verified through rungs:

      1. *"there are rare cases where the ledger line will only come
         out on one side not both but any line jutting out of a
         notehead outside of the staff where we think a ledger line
         should be is enough"* -- ONE side jutting past the box is
         enough, never both required.
      2. *"Examples with accidentals that I saw in the crops never had
         any ink touching the note head"* -- CONNECTIVITY is the
         primary test: the jutting ink must be part of the SAME
         contiguous ink run as the head's own body at the middle row
         (no bridging of any white gap, however small -- unlike
         `_band_centers`' own hollow-notehead bridge, which exists for
         a different reason). Found by taking the run that CONTAINS a
         column inside the head's own box and asking whether THAT run
         extends past either edge.
      3. `exclude_boxes` (cause C) stays as the BACKUP, not the primary
         test: accidental or other-notehead ink is blanked from a local
         copy of the image first, so it can never supply the jut even
         where it would otherwise look connected.

    `head_center_y`, when given (lane-ledger-r8-main, 2026-10-04), is the
    head's own centre row in page px, same frame as the box -- the row the
    middle probe is centred on INSTEAD of the box middle. A detector box
    often covers only the top of a half note, so the box middle is not the
    head's middle; a caller that traced the true centre supplies it here.
    `None` (the default) probes at `(y0+y1)/2`, exactly as before. The
    column probed (the box's x middle) is unchanged.

    `None` for `img_gray`/`head_box`, or a non-positive `spacing`, means
    no evidence is possible at all -- returns `False` (CLAUDE.md rule 8:
    "cannot tell" is never answered as "yes, a line").
    """
    if img_gray is None or head_box is None or spacing is None or spacing <= 0:
        return False
    x0, y0, x1, y1 = head_box
    mid_y = ((y0 + y1) / 2.0 if head_center_y is None
             else float(head_center_y))
    h, w = img_gray.shape
    pad = RUNG_BOX_VISIBILITY_SPACES * spacing
    cx0 = max(0, int(x0 - pad))
    cx1 = min(w, int(x1 + pad))
    tol_px = MIDDLE_ROW_TOL_SPACES * spacing
    wy0 = max(0, int(round(mid_y - tol_px)))
    wy1 = min(h, int(round(mid_y + tol_px)) + 1)
    if cx1 <= cx0 or wy1 <= wy0:
        return False
    window = img_gray[wy0:wy1, cx0:cx1]
    thr = _otsu_threshold(window)
    ink = window <= thr
    if exclude_boxes:
        ink = _exclude_other_heads_ink(
            ink, exclude_boxes, cx0, wy0, spacing, img_gray, thr
        )
    # Union across the middle-row BAND (never a single exact row) --
    # "at the head's own middle" with the stated tolerance, not past
    # it toward either edge.
    ink_cols = ink.any(axis=0)
    n = len(ink_cols)
    runs: list[list[int]] = []
    i = 0
    while i < n:
        if ink_cols[i]:
            j = i
            while j < n and ink_cols[j]:
                j += 1
            # NO bridging here -- Sean's connectivity rule means a
            # white gap of ANY size (he saw none at all in his
            # accidental crops) breaks the connection to the head.
            runs.append([i, j])
            i = j
        else:
            i += 1
    probe_col = int(round((x0 + x1) / 2.0)) - cx0
    containing = [r for r in runs if r[0] <= probe_col < r[1]]
    if not containing:
        return False
    s, e = containing[0]
    stub = THROUGH_RUNG_STUB_PROBE_SPACES * spacing
    left_edge, right_edge = x0 - cx0, x1 - cx0
    left_juts = s <= left_edge - stub
    right_juts = e >= right_edge + stub
    return left_juts or right_juts


# lane-ledger-edge-fix (2026-10-04). Sean's convention: a head is ON a
# ledger only if a thin flat line juts out of it at its MIDDLE row,
# touching; otherwise it is in the SPACE beyond the last ledger, and no
# ledger between the staff and the head is skipped. A ledger printed
# against the head's near edge (the side toward the staff) is therefore a
# ledger to COUNT, not the head's own outline. Constants are DERIVED from
# the scale already used above (nothing here is fitted to the truth set):
# the stub probe is `THROUGH_RUNG_STUB_PROBE_SPACES`, the thin cap is
# `LEDGER_THICKNESS_MAX_SPACES`, the flat tolerance is half of it (as
# `rung_is_thin_and_flat`), and "at the middle row" is the middle probe's
# own band (`MIDDLE_ROW_TOL_SPACES`) widened by the rung's own half
# measured thickness -- a rung whose ink overlaps that band would have
# been seen by `head_middle_rung_evidence`; one that does not cannot be
# the line the head is ON.
def thin_flat_jut_evidence(
    img_gray: "np.ndarray | None",
    y: float,
    box: "tuple[float, float, float, float]",
    spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
) -> dict:
    """Does a thin, flat, CONNECTED line at row `y` jut out of `box`?

    The shared core of the near-edge ledger test and the masked-rung
    restore (both ask the same question of a head: is a ledger printed
    against / through it?). All of:
      * CONNECTED: the ink at the row, unbridged (a white gap of any size
        breaks it -- Sean), joins the box's body at its middle column;
      * JUTTING: it runs past the box on at least one side by
        `RUNG_STUB_MIN_SPACES` (the walk's own stub length);
      * THIN and FLAT there: the vertical ink run over the OUTERMOST
        stub length of that jut (further in can be a stem standing at the
        head's side, or the head's own curve) is no thicker than `LEDGER_THICKNESS_MAX_SPACES` and the
        columns agree within half the cap (as `rung_is_thin_and_flat`).
        A side that fails (an accidental's tall ink, a stem) simply does
        not count; one good side is enough (Sean: "one side is enough"),
        and where both are good they agree within half the cap;
      * `exclude_boxes` (other noteheads, accidentals) are blanked first,
        as in `head_middle_rung_evidence`, so their ink never supplies
        the jut.
    Returns `{"ok", "why", "thickness": [...], "left_jut", "right_jut"}`
    (jut lengths in px).
    """
    bad = lambda why, **k: dict(ok=False, why=why, **k)  # noqa: E731
    if img_gray is None or box is None or not spacing or spacing <= 0:
        return bad("no_image")
    x0, y0, x1, y1 = box
    h, w = img_gray.shape
    pad = RUNG_BOX_VISIBILITY_SPACES * spacing
    cx0, cx1 = max(0, int(x0 - pad)), min(w, int(x1 + pad) + 1)
    margin = int(round(1.5 * spacing))
    ry0, ry1 = max(0, int(round(y)) - margin), min(h, int(round(y)) + margin + 1)
    if cx1 <= cx0 or ry1 <= ry0:
        return bad("off_image")
    window = img_gray[ry0:ry1, cx0:cx1]
    thr = _otsu_threshold(window)
    ink = window <= thr
    if exclude_boxes:
        ink = _exclude_other_heads_ink(ink, exclude_boxes, cx0, ry0, spacing,
                                       img_gray, thr)
    cap = LEDGER_THICKNESS_MAX_SPACES * spacing
    stub_min = RUNG_STUB_MIN_SPACES * spacing
    # the inked row nearest the rung's y (1 px slack for a band centre)
    yy = int(round(y)) - ry0
    cands = [r for r in (yy, yy - 1, yy + 1) if 0 <= r < ink.shape[0]
             and ink[r].any()]
    if not cands:
        return bad("no_ink_at_the_rung_row")
    row = None
    mid_col = int(round((x0 + x1) / 2.0)) - cx0
    for r in cands:
        line = ink[r]
        if 0 <= mid_col < line.size and line[mid_col]:
            row = r
            break
    if row is None:
        return bad("rung_row_not_connected_to_the_head")
    line = ink[row]
    s_i = mid_col
    while s_i > 0 and line[s_i - 1]:
        s_i -= 1
    e_i = mid_col
    while e_i + 1 < line.size and line[e_i + 1]:
        e_i += 1
    e_i += 1                      # exclusive
    left_jut = (x0 - cx0) - s_i   # px the run extends past the box edge
    right_jut = e_i - (x1 - cx0)
    thick = []
    for jut, sgn in ((left_jut, -1), (right_jut, 1)):
        if jut < stub_min:
            continue
        n_out = max(1, int(round(stub_min)))   # the outermost stub length
        cols = ([s_i + k for k in range(n_out)] if sgn < 0
                else [e_i - 1 - k for k in range(n_out)])
        ts_ = []
        for col in cols:
            if not (0 <= col < ink.shape[1]):
                continue
            c = ink[:, col]
            if not c[row]:
                continue
            top = bot = row
            while top > 0 and c[top - 1]:
                top -= 1
            while bot + 1 < c.size and c[bot + 1]:
                bot += 1
            ts_.append(float(bot - top + 1))
        if ts_ and max(ts_) <= cap and (max(ts_) - min(ts_)) <= 0.5 * cap:
            thick.append(max(ts_))
    if not thick:
        return bad("no_thin_flat_jut_past_the_head", left_jut=left_jut,
                   right_jut=right_jut)
    if len(thick) == 2 and abs(thick[0] - thick[1]) > 0.5 * cap:
        return bad("stubs_not_flat", thickness=thick)
    return dict(ok=True, why="thin_flat_connected_jut", thickness=thick,
                left_jut=left_jut, right_jut=right_jut)


# "The head hangs on one side of the line": the head's body ink (inside the
# box, clear of the stem at its side -- the box shrunk by the walk's own
# stub length) is read over a band as tall as the thin-ledger cap on each
# side of the rung. A head ON the line has body on BOTH sides (both bands
# inked, hollow or solid); a head in the space beyond a ledger it touches
# has body on the far side ONLY. "Mostly one side" is a plain majority:
# the staff side must hold at most half the far side's ink fraction, and
# the far side must be mostly ink itself.
HEAD_BODY_MARGIN_SPACES = RUNG_STUB_MIN_SPACES
HEAD_BODY_BAND_SPACES = LEDGER_THICKNESS_MAX_SPACES
HEAD_BODY_ONE_SIDED_RATIO = 0.5
HEAD_BODY_FAR_MIN_FRACTION = 0.5


def head_body_ink_either_side(
    img_gray: np.ndarray, y: float, box: "tuple[float, float, float, float]",
    sign: float, spacing: float, thickness_px: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
) -> "dict[str, float]":
    """Fraction of inked pixels in the head's inner columns over a band
    (`HEAD_BODY_BAND_SPACES`) just beyond the rung's own thickness, on the
    STAFF side and on the FAR side of row `y`. NaN where off the image."""
    x0, y0, x1, y1 = box
    h, w = img_gray.shape
    ix0 = max(0, int(x0 + HEAD_BODY_MARGIN_SPACES * spacing))
    ix1 = min(w, int(x1 - HEAD_BODY_MARGIN_SPACES * spacing))
    ry0 = max(0, int(y - 2 * spacing))
    ry1 = min(h, int(y + 2 * spacing))
    out = {"staff": float("nan"), "far": float("nan")}
    if ix1 <= ix0 or ry1 <= ry0:
        return out
    ref = img_gray[max(0, int(y0) - 10):int(y1) + 10,
                   max(0, int(x0) - 10):int(x1) + 10]
    thr = _otsu_threshold(ref if ref.size else img_gray[ry0:ry1, ix0:ix1])
    ink = img_gray[ry0:ry1, ix0:ix1] <= thr
    if exclude_boxes:
        ink = _exclude_other_heads_ink(ink, exclude_boxes, ix0, ry0, spacing,
                                       img_gray, thr)
    gap = thickness_px / 2.0 + 1.0
    band = HEAD_BODY_BAND_SPACES * spacing
    for name, sgn in (("staff", -sign), ("far", sign)):
        rows = [int(round(y + sgn * d)) - ry0
                for d in np.arange(gap, gap + band, 1.0)]
        rows = [r for r in rows if 0 <= r < ink.shape[0]]
        if rows:
            out[name] = float(ink[rows].mean())
    return out


def near_edge_ledger_evidence(
    img_gray: "np.ndarray | None",
    y: float,
    head_box: "tuple[float, float, float, float] | None",
    sign: float,
    spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    head_center_y: "float | None" = None,
) -> dict:
    """Is the rung at row `y` a real ledger touching this head's NEAR edge?

    Both of: it is a thin flat connected jut (`thin_flat_jut_evidence`);
    and the head's body hangs on its FAR side only
    (`head_body_ink_either_side`): the far band is mostly ink and the
    staff band holds at most `HEAD_BODY_ONE_SIDED_RATIO` of it. A head
    with body on both sides is ON the line (the through-candidate, judged
    at the middle row by `head_middle_rung_evidence`) -- that, and a rung
    at the FAR edge (no body beyond it), are never counted here. This
    reads the head's own ink, not the detector box's middle (a box is
    often taller than the head, and its middle is not the head's).
    `head_center_y` is accepted for call symmetry and unused.
    No image, no box or no spacing -> not ok (rule 8).
    """
    if img_gray is None or head_box is None or not spacing or spacing <= 0:
        return dict(ok=False, why="no_image")
    ev = thin_flat_jut_evidence(img_gray, y, head_box, spacing, exclude_boxes)
    if not ev["ok"]:
        return ev
    bi = head_body_ink_either_side(img_gray, y, head_box, sign, spacing,
                                   max(ev["thickness"]), exclude_boxes)
    st, fa = bi["staff"], bi["far"]
    if not (fa == fa and st == st):   # NaN: cannot tell
        return dict(ok=False, why="head_body_unreadable", body=bi)
    if fa < HEAD_BODY_FAR_MIN_FRACTION:
        return dict(ok=False, why="no_head_body_beyond_the_rung", body=bi)
    if st > HEAD_BODY_ONE_SIDED_RATIO * fa:
        return dict(ok=False, why="head_body_on_both_sides_of_the_rung",
                    body=bi)
    return dict(ok=True, why="thin_flat_jut_head_hangs_beyond_it",
                thickness=ev["thickness"], body=bi)


def rung_is_near_edge_ledger(*args, **kwargs) -> bool:
    """Boolean form of `near_edge_ledger_evidence` (same arguments)."""
    return bool(near_edge_ledger_evidence(*args, **kwargs)["ok"])


def restore_masked_staff_side_ledgers(
    img_gray: np.ndarray, ys: "list[float]", x: float,
    head_y: "float | None", rungs: "list[float]", side: str, sign: float,
    spacing: float, box: "tuple[float, float, float, float]",
    exclude_boxes: "list[tuple[float, float, float, float]]",
) -> "list[float]":
    """Convention: no ledger between the staff and the head is ever
    skipped. The other-head mask exists so a neighbour's own ink cannot
    SUPPLY a stub; it must not delete a ledger the neighbour is itself
    printed ON. A rung that the bare ink offers (no mask) and the masked
    walk lost is put back only if ALL of:
      * it lies between the staff and this head -- not past the head's
        near edge by `TOUCH_TOL_SPACES` or more (`derive_far_head_step`'s
        own "between staff and head" class), so a ledger BEYOND this head
        (another head's, farther out) is never restored;
      * an excluded box covers its row (it was masked because of that
        head, not lost to the walk's cascade), and a thin flat connected
        jut leaves THAT head's box at the row (`thin_flat_jut_evidence`,
        every other excluded box blanked) -- i.e. the masking head is on
        this ledger, so the ledger is real ink of its own, not the
        head's outline.
    Returns `rungs` plus the restored ones, nearest-the-staff first."""
    bare = measure_ledger_rungs(img_gray, ys, x, head_y=head_y).get(side, [])
    x0, y0, x1, y1 = box
    near_y = y1 if sign < 0 else y0
    out = list(rungs)
    for y in bare:
        if any(abs(y - r) <= LEDGER_THICKNESS_MAX_SPACES * spacing for r in out):
            continue
        if sign * (near_y - y) / spacing <= -TOUCH_TOL_SPACES:
            continue   # at or past the head's near edge: not between
        for b in exclude_boxes:
            if not (b[1] - 1 <= y <= b[3] + 1):
                continue
            others = [o for o in exclude_boxes if o is not b]
            if thin_flat_jut_evidence(img_gray, y, b, spacing, others)["ok"]:
                out.append(float(y))
                break
    out.sort(key=lambda v: sign * v)
    return out


# Cause C (DECISIONS 2026-10-01, four causes): a candidate band landing
# within this many staff spaces of the subject's OWN box top/bottom edge
# is that edge itself, not a ledger -- accidental or broken half-note ink
# just beside the head can bridge enough extra length for the head's own
# outline to pass the stub/length tests at those two rows. Small on
# purpose: a genuine ledger a half-step out never sits this close to the
# box's own edge (the box itself is ~1 staff space tall).
HEAD_EDGE_RUNG_TOL_SPACES = 0.25


def collapse_head_edge_rungs_to_middle(
    rungs_y: "list[float]", sign: float,
    head_box: "tuple[float, float, float, float]",
    img_gray: "np.ndarray | None", spacing: float,
    exclude_boxes: "list[tuple[float, float, float, float]] | None" = None,
    head_center_y: "float | None" = None,
) -> "list[float]":
    """Cause C: when accidental (or broken half-note) ink beside a head
    on a ledger fakes two "rungs" at the head's own top and bottom edges,
    drop them -- they are the box's own outline, never a ledger -- and,
    only where the head's own MIDDLE row shows real evidence of a line
    (`head_middle_rung_evidence`, with `exclude_boxes` keeping the same
    accidental ink out of THAT read too), put the one genuine rung back
    in its place. Changes nothing unless two of `rungs_y` are each within
    `HEAD_EDGE_RUNG_TOL_SPACES` of the box's own y0 and y1 AND adjacent
    in the ladder (no other rung between them) -- a real ledger pair
    flanking the head at the normal spacing is never this close to the
    box's own edges and is left untouched.
    """
    if len(rungs_y) < 2 or spacing <= 0:
        return list(rungs_y)
    x0, y0, x1, y1 = head_box
    tol = HEAD_EDGE_RUNG_TOL_SPACES * spacing
    ordered = sorted(rungs_y, key=lambda ry: sign * ry)
    # The candidate NEAREST each edge, not merely "within tolerance" --
    # a box's own height can be smaller than 2x the tolerance, so a
    # membership test alone can match the same candidate (or either
    # candidate) to both edges at once and lose the pairing.
    i_top = min(range(len(ordered)), key=lambda i: abs(ordered[i] - y0))
    i_bot = min(range(len(ordered)), key=lambda i: abs(ordered[i] - y1))
    if abs(ordered[i_top] - y0) > tol or abs(ordered[i_bot] - y1) > tol:
        return list(rungs_y)
    if i_top == i_bot:
        return list(rungs_y)
    lo, hi = min(i_top, i_bot), max(i_top, i_bot)
    if hi != lo + 1:
        return list(rungs_y)
    out = ordered[:lo] + ordered[hi + 1:]
    if head_middle_rung_evidence(img_gray, head_box, spacing, exclude_boxes,
                                 head_center_y):
        mid_y = ((y0 + y1) / 2.0 if head_center_y is None
                 else float(head_center_y))
        out = sorted(out + [mid_y], key=lambda ry: sign * ry)
    return out


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


# ─────────────────────────────────────────────────────────────────────────
# ROADMAP 2.54 (Sean, 2026-10-01, "combine that way"): a far head's FINAL
# position combines geometry (the extrapolated staff grid,
# `Q.NOTEHEAD_STAFF_POSITION`) and the rung count (this module's own
# `measure_ledger_rungs` + `derive_far_head_step`, "as shipped" -- round
# 7's own cleanups measured net negative on the real truth set, FINDINGS
# "lane-ledger-r7", and are NOT part of this combination): AGREE -> take
# it; DISAGREE -> the head's OWN printed ledgers' evenness decides which
# reader to trust (uneven -> rungs, even -> geometry); neither reader can
# settle it -> UNREAD, counted (CLAUDE.md rule 8: a fallback never
# converts "cannot tell" into an answer).
# ─────────────────────────────────────────────────────────────────────────

#: Measured split on the 2.44c truth set (`benchmarks/omr-local-staff-
#: 2026-09/ledger_breakdown_r3.py`, Table D, Litolff n=44): geometry-WRONG
#: heads carry a median |gap/spacing - 1| of 0.419 across their OWN found
#: rung-to-rung gaps; geometry-RIGHT heads carry 0.105. The threshold sits
#: at the midpoint of those two measured medians.
#: CONVENTION ASSUMED (the midpoint of a two-point split, not a boundary
#: measured in its own right) / WHAT WOULD FALSIFY IT: a larger truth set
#: moving either median far enough to put real heads on the wrong side of
#: this exact number / NOT CONFIRMED beyond the 44 Litolff + 11 Brahms
#: heads in `benchmarks/acceptance/quick/out/*/*.record.json`.
FARHEAD_EVEN_UNEVEN_THRESHOLD = 0.26

#: A head needs at least this many rung-to-rung GAPS (i.e. >= 2 rungs
#: found) before evenness means anything at all -- `ledger_breakdown_r3.
#: table_d` itself only reports a deviation for "n with >= 2 rungs found".
FARHEAD_MIN_RUNGS_FOR_EVENNESS = 2

#: "Geometry near a boundary": the raw (pre-rounding)
#: `Q.NOTEHEAD_STAFF_POSITION` value's distance from the nearest half-step
#: integer (that row's own `residual` detail, `gather_notehead_
#: positions`). 0.4 means within 0.1 of the true rounding tie (0.5) --
#: the same rounding-boundary language DECISIONS 2026-10-01 uses for the
#: seeded-comb coin-flip crops (0.13 / 0.03 steps apart).
#: CONVENTION ASSUMED / WHAT WOULD FALSIFY IT: a measured population of
#: near-boundary geometry misses that clusters at a different distance /
#: NOT CONFIRMED -- no such population has been measured yet.
FARHEAD_NEAR_BOUNDARY_RESIDUAL = 0.4


def farhead_gap_evenness(rungs_y: "list[float]", spacing: float
                         ) -> "float | None":
    """The max `|gap/spacing - 1|` across this head's own consecutive
    found rungs (nearest-edge first, `measure_ledger_rungs`'s own order)
    -- the SAME measure `ledger_breakdown_r3.table_d` computes off the
    identical data. `None` with fewer than `FARHEAD_MIN_RUNGS_FOR_
    EVENNESS` rungs (no gap exists to measure) -- an ABSENCE, never a
    false 0.0 "perfectly even" claim."""
    if spacing <= 0 or len(rungs_y) < FARHEAD_MIN_RUNGS_FOR_EVENNESS:
        return None
    devs = [abs(abs(rungs_y[i + 1] - rungs_y[i]) / spacing - 1.0)
           for i in range(len(rungs_y) - 1)]
    return max(devs) if devs else None


def combine_farhead_position(
    geom_pos: "int | None", geom_residual: "float | None",
    rungs_pos: "int | None", rungs_y: "list[float]", spacing: float,
) -> dict:
    """Sean, 2026-10-01, on the two 2.44 ledger readers: *"combine that
    way"* -- geometry and rungs AGREE -> take it; DISAGREE -> measure the
    head's OWN ledger evenness (`farhead_gap_evenness`): uneven -> rungs,
    even -> geometry; neither can tell -> UNREAD, counted.

    `geom_pos` is the rounded `Q.NOTEHEAD_STAFF_POSITION` value -- always
    present for a far head (the gate that puts a head in this population
    at all is that this row exists and is outside the staff).
    `geom_residual` is that same row's own `residual` detail (distance
    from the rounding boundary, `0.0`..`0.5`); `None` only where the
    caller never had it. `rungs_pos` is `derive_far_head_step`'s own
    offset converted to the shared absolute units (`None` where that
    reader abstained); `rungs_y` is the rung ladder it was derived from,
    on this head's own side (nearest-edge first) -- the SAME list used to
    derive `rungs_pos`, so `farhead_gap_evenness` is never a second,
    independent ink read.

    Returns `{"position": int|None, "branch": str, "max_gap_deviation":
    float|None}`. `branch` is one of `"agree"`, `"disagree_rungs"`,
    `"disagree_geometry"`, `"unread"` -- the pure decision, independent of
    whether anything downstream reads it (`FARHEAD_COMBINED_SHIPS`,
    `tools/omr/staged/gather.py`)."""
    dev = farhead_gap_evenness(rungs_y, spacing)

    if rungs_pos is not None and geom_pos is not None and geom_pos == rungs_pos:
        return dict(position=geom_pos, branch="agree", max_gap_deviation=dev)

    # DISAGREE from here on -- a rungs abstention (`rungs_pos is None`) is
    # not an agreement either, and is handled by the same branch logic.
    near_boundary = (geom_residual is not None
                     and geom_residual >= FARHEAD_NEAR_BOUNDARY_RESIDUAL)
    if rungs_pos is None and near_boundary:
        # Neither reader can settle it: the second reader has nothing at
        # all, and the first is itself a rounding coin-flip.
        return dict(position=None, branch="unread", max_gap_deviation=dev)
    if dev is None:
        # Too few rungs found beside this head to measure evenness at
        # all -- "neither can tell" by the OTHER named route.
        return dict(position=None, branch="unread", max_gap_deviation=dev)
    if dev > FARHEAD_EVEN_UNEVEN_THRESHOLD:
        if rungs_pos is None:
            # Uneven says "trust rungs", but rungs has no answer to give
            # -- unread, never a guess (CLAUDE.md rule 8).
            return dict(position=None, branch="unread", max_gap_deviation=dev)
        return dict(position=rungs_pos, branch="disagree_rungs",
                   max_gap_deviation=dev)
    return dict(position=geom_pos, branch="disagree_geometry",
               max_gap_deviation=dev)
