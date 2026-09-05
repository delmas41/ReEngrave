"""Phase 1.3 — Barline detection and per-measure cell extraction.

Algorithm:
  1. For each system, search for vertical line segments that span (nearly)
     all staves in the system. Use a vertical-projection-profile approach
     constrained to the system's y-range.
  2. The detected vertical positions are barlines.
  3. For each (staff, measure) cell — bounded by adjacent barlines and the
     staff's vertical band (with some padding) — crop from the original
     page image, then upscale to CANONICAL canonical size.

Public surface:
    detect_barlines(page_with_staves) -> updates PageWithStaves.barlines
    extract_measures(page_with_staves, canonical_staff_span=400, max_cell_width=2048) -> list[MeasureCell]
    resegment_fused_measures(page_with_staves, cells) -> list[MeasureCell]
        Phase 1i: local re-split of cells >2x the staff's median width
        (transcribe.py's phase1_warning outliers) wherever a genuine
        internal barline can be found. Never touches normal-width cells.
"""

from __future__ import annotations

import os
from collections import Counter

import cv2
import numpy as np

from .types import Barline, MeasureCell, PageWithStaves, Staff


# ─── Tuning ──────────────────────────────────────────────────────────────────

# Canonical sizing for extracted measure cells. Plan calls for "as high as
# possible": ~400px staff span, ~2048px max cell width.
CANONICAL_STAFF_SPAN_PX = 400
MAX_CELL_WIDTH_PX = 2048

# Padding around a measure cell (in units of staff line spacing — so it
# scales with score size). Above the staff: ledger lines / dynamics.
# Below the staff: ledger lines / pedal markings.
#
PAD_ABOVE_STAFF_LINES = 4
PAD_BELOW_STAFF_LINES = 4

# THE PAD GROWS WHERE THE PAGE LEAVES ROOM, and never shrinks below the four
# above. Measured inter-staff gaps on the engraved fixtures, in staff spaces:
# Mahler 1.7-1.9, Beethoven 3.2-3.4, Brahms 3.5-8.7. So four already reaches
# through both of Mahler's neighbours — and it must, because a stem is about
# 3.5 spaces and a cell cut to Mahler's 1.7-space gap loses its stems and
# beams: measured, that alone took Mahler's duration rate 0.864 -> 0.455.
#
# What the extra room buys is the case this exists for. Brahms's Violin 1 plays
# up to B6, five spaces above its own top line, and LilyPond opened a 7.8-space
# gap above that staff to fit exactly those notes. At a flat four the cell
# stopped short of them, they fell only into the TIMPANI's cell, and they
# exported as `Ab1` on a timpani while Violin 1's bars 3 and 4 came out empty.
#
# ALL OR NOTHING, never a marginal in-between. Cell height is coupled to
# `OMR_IMGSZ` — a taller cell letterboxes the staff into fewer pixels — so a
# small change in it moves DETECTIONS, not just the crop. Measured: growing the
# authored `ensemble` fixture's pad from 4.0 to 4.6 spaces, because its staves
# happen to sit 5.1 apart, cost it three notes of 45 for no gain. So the pad is
# four, or six where there is unambiguously room for six, and nothing between.
PAD_MAX_STAFF_LINES = 6

# How close a grown cell may come to the NEIGHBOURING staff's nearest line.
# Half a space clears a printed line and its wander at every DPI measured here.
CELL_NEIGHBOUR_CLEARANCE_SPACES = 0.5

# Barline detection — morphological approach. A barline is a vertical
# ink stripe that:
#   - covers at least BARLINE_MIN_HEIGHT_FRAC × staff_span
#   - is thinner than BARLINE_MAX_WIDTH_LINESPACINGS × line spacing
# This filters out note stems (too short), beams (wrong orientation), and
# accidentals/chord clusters (too wide).
BARLINE_MIN_HEIGHT_FRAC = 0.80
# Investigated bumping this 0.80 → 0.85 → 0.95 to fix Beethoven 5
# orchestral over-counting:
#   0.80 (this default): Bach 3.70, Beethoven 98 measures + 18 wide outliers
#   0.85: Bach 3.70 (no change), Beethoven 162 measures (over-segmented)
#   0.95: Bach 3.99 (slight improvement), Beethoven 218 measures (worse over-seg)
# Higher thresholds fragment Beethoven into too many measures because the
# real barlines on the orchestral score don't always span the full staff
# (they sometimes show as section breaks between bracketed groups). A
# proper fix needs cross-staff-system connectivity analysis, not a single
# threshold. Sticking with 0.80 for now and using the `phase1_warning`
# flag on outlier-wide cells (Phase 4i) to identify the problematic
# measures downstream.
BARLINE_MAX_WIDTH_LINESPACINGS = 0.7  # stems are typically ~0.3 line-spacing wide
BARLINE_MIN_DISTANCE_PX = 60      # neighbouring barlines must be ≥60px apart

# How much of the weakest band of a column must be ink before it counts as
# spanning the system (`_spans_system`). Measured over four braced piano systems
# of WTC I: every real interior barline 1.00, every stem 0.52 or below. The gap
# is wide enough that this is a description, not a tuned threshold.
SPAN_MIN_INK = 0.9


# ─── Barline detection ───────────────────────────────────────────────────────


def _detect_barlines_in_window(
    bin_img: np.ndarray,
    staff: Staff,
    x0: int,
    x1: int,
    min_height_frac: float = BARLINE_MIN_HEIGHT_FRAC,
    *,
    prefer: str = "leftmost",
) -> list[int]:
    """Find columns in [x0, x1) where this staff has a vertical barline,
    using morphological vertical opening + connected-component shape
    filtering. Same geometric test as the old `_detect_barlines_per_staff`
    (height / width / aspect ratio), factored out so the x-window and the
    height threshold are both parameters instead of always being the
    staff's full span + the global BARLINE_MIN_HEIGHT_FRAC.

    Two callers:
      - `_detect_barlines_per_staff` (global pass): window = staff's full
        x-span, threshold = BARLINE_MIN_HEIGHT_FRAC. Behavior-identical to
        the pre-refactor implementation.
      - `_find_internal_barline_candidates` (local re-segmentation of
        already-flagged fused cells, see resegment_fused_measures): window
        = one flagged cell, threshold = a more lenient
        RESEGMENT_MIN_HEIGHT_FRAC. Only ever invoked inside a cell
        transcribe.py already flagged as a >2x-median-width outlier, so
        relaxing the threshold there cannot reproduce the global
        over-segmentation regression documented above (raising
        BARLINE_MIN_HEIGHT_FRAC globally 0.80->0.95 blew Beethoven from
        98->218 measures).

    A barline is a vertical ink stripe with these geometric properties:
      - height ≥ min_height_frac × staff span
      - width < ~0.7 × line spacing
      - aspect ratio (h/w) >> 1
    """
    h, w = bin_img.shape
    y0, y1 = staff.top_y, staff.bottom_y + 1
    if y1 <= y0:
        return []
    x0 = max(0, x0)
    x1 = min(w, x1)
    if x1 <= x0:
        return []
    band = bin_img[y0:y1, x0:x1]
    if band.size == 0:
        return []

    staff_span = y1 - y0
    spacing = max(1.0, staff.line_spacing_px)
    min_height = int(staff_span * min_height_frac)
    max_width = max(2, int(spacing * BARLINE_MAX_WIDTH_LINESPACINGS))

    ink = cv2.bitwise_not(band)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_height))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(vertical, connectivity=8)
    found: list[tuple[int, int]] = []          # (x_centre, height)
    for i in range(1, n_labels):
        x_l, y_l, w_l, h_l, area = stats[i]
        if h_l < min_height:
            continue
        if w_l > max_width:
            continue           # too wide — accidental or chord
        if h_l / max(w_l, 1) < 8.0:
            continue           # not skinny enough
        x_center = x0 + x_l + w_l // 2
        found.append((int(x_center), int(h_l)))
    found.sort()
    return _dedup_barline_candidates(found, prefer=prefer)


def _dedup_barline_candidates(
    found: list[tuple[int, int]],
    *,
    prefer: str = "leftmost",
) -> list[int]:
    """Thin a staff's barline candidates to one per `BARLINE_MIN_DISTANCE_PX`.

    Two columns closer together than a bar can be are not two barlines, so one
    of them goes. WHICH one matters more than it looks.

    `prefer="leftmost"` is the original rule and is what the whole-page pass
    keeps: it is cheap, and over a full staff the surviving candidates are
    thinned consistently.

    `prefer="tallest"` exists because the leftmost rule loses a real barline to
    a note stem. Measured on Beethoven 5 p.2 system 0: the final beat before
    the barline at x~1710 carries a full-height stem 27-35px to its LEFT on
    four of the six staves that see the barline, and that stem independently
    clears every filter the barline clears (81-100% of staff span against the
    barline's 98-100%). Keeping the leftmost throws the barline away and keeps
    the stem, so only 2 of 6 real votes reach the caller's vote gate, one short
    of its floor. Height is the discriminator the shape test already computes
    and then discards: a barline spans the staff, a stem usually stops short.

    The window is ANCHORED on the candidate that opens it rather than sliding
    with each one kept. A sliding anchor lets a dense stem-and-ornament region
    chain transitively into one wide group whose representative is a mean, not
    a barline — measured as x=1697 against a true x~1707-1711, and a silently
    wrong candidate is worse than the empty result it replaces.
    """
    out: list[int] = []
    i = 0
    while i < len(found):
        j = i
        while (j + 1 < len(found)
               and found[j + 1][0] - found[i][0] < BARLINE_MIN_DISTANCE_PX):
            j += 1
        group = found[i:j + 1]
        if prefer == "tallest":
            out.append(max(group, key=lambda c: (c[1], -c[0]))[0])
        else:
            out.append(group[0][0])
        i = j + 1
    return out


def _detect_barlines_per_staff(bin_img: np.ndarray, staff: Staff) -> list[int]:
    """Find columns where this single staff has a vertical barline (global
    pass — full staff x-span, global BARLINE_MIN_HEIGHT_FRAC threshold).

    NOTE: A notehead-attachment rejection step was tried (commit history
    in this file) but it was too easily fooled by ink near barlines that
    isn't actually attached to them. Over-detection on very dense
    orchestral pages is handled at the system level via gap-bipartition
    outlier rejection (see _drop_close_outliers).
    """
    return _detect_barlines_in_window(
        bin_img, staff, staff.x_start, staff.x_end + 1, BARLINE_MIN_HEIGHT_FRAC
    )


def _barline_x_at(
    x_by_staff: dict[int, int] | None, staves: list[Staff], y: float, fallback: int
) -> int:
    """Where this barline is expected to cross height `y`.

    A barline is a straight line across the system. On a flat scan it is also a
    VERTICAL one, and everything here used to assume the two are the same thing.
    They are not: on the IMSLP Beethoven 5 the paper is warped, and one barline's
    x drifts monotonically by up to 40 px between the top staff and the bottom —
    more than three times the clustering tolerance. A probe dropped straight down
    from the top of the line lands beside it by the third gap.

    So the line is fitted to the staves that actually observed it and evaluated
    at `y`. Fewer than two observations leaves nothing to fit a slope to, and the
    caller's single column stands.

    The fit is Theil-Sen — the median of the pairwise slopes — and not least
    squares, because some of the observations are not the barline. A note stem
    that happens to sit near the column joins the cluster and votes for it, and
    two such among nine dragged the fitted line far enough off that a real
    barline still scored 0.36 with the slope modelled. The median ignores them.
    """
    if not x_by_staff or len(x_by_staff) < 2:
        return fallback
    centres = {s.staff_index: (s.top_y + s.bottom_y) / 2.0 for s in staves}
    points = [(centres[i], float(x)) for i, x in x_by_staff.items() if i in centres]
    if len(points) < 2:
        return fallback
    slopes = [
        (x_b - x_a) / (y_b - y_a)
        for i, (y_a, x_a) in enumerate(points)
        for (y_b, x_b) in points[i + 1:]
        if abs(y_b - y_a) >= 1.0
    ]
    if not slopes:
        return fallback
    slope = float(np.median(slopes))
    intercept = float(np.median([x - slope * y_i for y_i, x in points]))
    return int(round(slope * y + intercept))


def _spans_system(
    bin_img: np.ndarray,
    staves: list[Staff],
    x_col: int,
    *,
    x_by_staff: dict[int, int] | None = None,
    bands: int = 8,
    half_width: int = 4,
) -> float:
    """Ink fraction of the WEAKEST band of a column drawn down the whole system.

    Stricter than `_intersystem_connectivity`, which asks only whether the gaps
    between staves are inked. A long stem in a fugue can cross a gap — WTC I
    page 6 has one at x=3018 that scores 1.00 connectivity and is not a barline
    — but nothing except a barline is inked from the top of the top staff to the
    bottom of the bottom one. Measured over four braced piano systems of WTC I:
    every real interior barline 1.00, every stem and every false candidate 0.52
    or below. Not a threshold that needs tuning.

    The band-by-band minimum is what makes it a SPAN test rather than a coverage
    one: a column half-inked over its whole length would average the same as a
    barline broken in the middle, and only one of those is a barline. Each band
    is probed at the x the line is expected to cross it, so a leaning barline
    still reads as continuous.
    """
    ordered = sorted(staves, key=lambda s: s.top_y)
    top, bottom = ordered[0].top_y, ordered[-1].bottom_y
    if bottom <= top:
        return 0.0
    height, width = bin_img.shape
    step = (bottom - top) / float(bands)
    weakest = 1.0
    for i in range(bands):
        y0 = max(0, int(round(top + i * step)))
        y1 = min(height, int(round(top + (i + 1) * step)))
        if y1 <= y0:
            continue
        x_here = _barline_x_at(x_by_staff, staves, (y0 + y1) / 2.0, x_col)
        x0 = max(0, x_here - half_width)
        x1 = min(width, x_here + half_width + 1)
        if x1 <= x0:
            return 0.0
        strip = bin_img[y0:y1, x0:x1] < 128
        if strip.size == 0:
            return 0.0
        weakest = min(weakest, float(strip.mean(axis=0).max()))
    return weakest


def _intersystem_connectivity(
    bin_img: np.ndarray,
    staves: list[Staff],
    x_col: int,
    x_tolerance: int = 5,
    *,
    x_by_staff: dict[int, int] | None = None,
) -> float:
    """Fraction of inter-staff gaps in this system that have continuous
    ink where this barline runs (within ±`x_tolerance` px).

    `x_by_staff` gives the x each staff observed the line at; with it the probe
    follows the line's slope rather than dropping a vertical column. Without it
    the behaviour is the old vertical probe.

    A real barline is drawn THROUGH the whitespace between staves — it
    connects the top staff to the bottom staff visually. A false-positive
    stem only exists within a single staff and has no ink in the gaps
    between staves. This is a strong discriminator on orchestral pages.

    Diagnostic data from `tools.omr._phase1_diagnostic` on Bach,
    Beethoven 5 p14, and Ravel Boléro p9:
      - On Bach (2-staff piano): perfect separation — accepted barlines
        have connectivity 1.0, rejected have 0.0.
      - On Beethoven multi-staff systems: 2 currently-accepted columns
        with 8-9/11 votes had connectivity 0.1-0.3 (stem-aligned chord
        columns — NOT real barlines). 6 currently-rejected columns had
        votes 3-6 of 5-11 staves but connectivity 0.8-1.0 (real
        barlines that the strict vote rule was missing).
      - On Ravel: 1 rescue (6/8 votes, 0.71 conn); current rule was
        already clean.

    For single-staff systems (no inter-staff gaps) returns 1.0 so the
    connectivity gate never rejects them.
    """
    if len(staves) < 2:
        return 1.0
    ordered = sorted(staves, key=lambda s: s.top_y)
    n_gaps = len(ordered) - 1
    n_connected = 0
    h, w = bin_img.shape
    for i in range(n_gaps):
        gap_top = ordered[i].bottom_y + 1
        gap_bot = ordered[i + 1].top_y
        if gap_bot <= gap_top:
            n_connected += 1  # adjacent staves, no actual gap
            continue
        x_here = _barline_x_at(
            x_by_staff, staves, (gap_top + gap_bot) / 2.0, x_col
        )
        x0 = max(0, x_here - x_tolerance)
        x1 = min(w, x_here + x_tolerance + 1)
        gap_top_c = max(0, gap_top)
        gap_bot_c = min(h, gap_bot)
        if gap_top_c >= gap_bot_c or x0 >= x1:
            continue
        gap_strip = bin_img[gap_top_c:gap_bot_c, x0:x1]
        if gap_strip.size == 0:
            continue
        # Binarized convention: 0 = ink, 255 = paper.
        col_ink_fraction = (gap_strip < 128).mean(axis=0)
        if col_ink_fraction.max() > 0.5:
            n_connected += 1
    return n_connected / max(n_gaps, 1)


def detect_barlines(pws: PageWithStaves) -> PageWithStaves:
    """Detect barlines via per-staff scanning + system-level voting.

    A column counts as a system barline if it shows up as a barline on
    AT LEAST half of the staves in the system (with a small x-tolerance
    to handle slight skew). Per-staff detection avoids the orchestral
    failure mode where whitespace between sections dilutes the ink
    fraction over the full system height.
    """
    bin_img = pws.page.binary

    # Group staves by system. One-line percussion staves are left out of the
    # vote on purpose: the vote is a fraction of the staves in the system, and
    # a staff two spaces tall answers "there is a barline here" for any stem
    # that crosses it, so it would both add noise and move the denominator for
    # every real staff. Their own barlines come from the system they sit in.
    systems: dict[int, list[Staff]] = {}
    for s in pws.staves:
        if len(s.line_ys) >= 5:
            systems.setdefault(s.system_index, []).append(s)

    pws.barlines = []
    x_tolerance = 12  # px: barlines on different staves may not align exactly

    for sys_idx, staves in systems.items():
        # Gather candidate x positions across all staves, keeping WHICH staff
        # saw each one: that is what lets the connectivity probe follow a
        # barline that leans (see `_barline_x_at`).
        observations: list[tuple[int, int]] = []
        for staff in staves:
            for x in _detect_barlines_per_staff(bin_img, staff):
                observations.append((x, staff.staff_index))
        if not observations:
            continue
        observations.sort()

        # Cluster close x's together (within x_tolerance) and count how many
        # staves in the system voted for each cluster.
        clusters: list[list[int]] = []
        cluster_obs: list[list[tuple[int, int]]] = []
        for x, staff_index in observations:
            if clusters and x - clusters[-1][-1] <= x_tolerance:
                clusters[-1].append(x)
                cluster_obs[-1].append((x, staff_index))
            else:
                clusters.append([x])
                cluster_obs.append([(x, staff_index)])

        def _x_by_staff(index: int) -> dict[int, int]:
            """One x per staff for this cluster, nearest the cluster's mean
            where a staff fired twice."""
            members = cluster_obs[index]
            mean = sum(x for x, _ in members) / len(members)
            best: dict[int, int] = {}
            for x, staff_index in members:
                if staff_index not in best or abs(x - mean) < abs(best[staff_index] - mean):
                    best[staff_index] = x
            return best

        n_staves = len(staves)
        # Vote threshold: real barlines are drawn across the SYSTEM but
        # not necessarily detected on every staff (orchestral pages often
        # have sparse staves where the barline is faint or implicit; the
        # snare drum staff in particular has many false-positive stems
        # that fire as barlines on that one staff). Tiered rule:
        #   - ≤2 staves: both must agree
        #   - ≤4 staves: tolerate 1 miss
        #   - ≤8 staves: 75% of staves (still strict)
        #   - >8 staves (large orchestral systems): just 50%
        #                                            (with a min of 4 votes
        #                                            so we don't get noise)
        # The previous rule (max(n_staves-1, 80%)) effectively required
        # ALL-BUT-ONE staves to agree even at 32-staff orchestral systems,
        # which missed real barlines on Bolero where only 10/16 staves
        # had a clear barline at each measure boundary.
        if n_staves <= 2:
            min_votes = n_staves
        elif n_staves <= 4:
            min_votes = n_staves - 1
        elif n_staves <= 8:
            # Strict threshold for small-to-medium systems where stems
            # don't usually align across most staves.
            min_votes = max(n_staves - 1, int(round(0.80 * n_staves)))
        elif n_staves <= 12:
            min_votes = int(round(0.65 * n_staves))
        else:
            # Very large orchestral systems (>12 staves): real barlines
            # often only show on a subset of staves (sparse instruments
            # or doubled lines). 50% catches Bolero-style sparseness.
            min_votes = max(5, int(round(0.50 * n_staves)))

        y_top = min(s.top_y for s in staves)
        y_bot = max(s.bottom_y for s in staves)
        # Acceptance rule. On 1-2 staff systems (piano, duet, lead sheet)
        # the vote rule is enough — the diagnostic showed perfect
        # separation, no false positives or missed barlines.
        # On 3+ staff systems (orchestral) two failure modes appear:
        #   (a) Chord stems align across staves at a non-barline column,
        #       passing the vote threshold despite no ink in the
        #       inter-staff gaps. Filter via `connectivity >= 0.4`.
        #   (b) A real barline is faint or partly obscured and only
        #       fires on 3-6 of 11 staves, below the strict vote
        #       threshold. Rescue when `connectivity >= 0.7` (the line
        #       is clearly drawn through the gaps even though few
        #       staves voted).
        # Thresholds were chosen from the cluster-distribution data
        # captured by `_phase1_diagnostic` on Bach + Beethoven + Ravel.
        # Does this system draw its barlines THROUGH the gaps between staves?
        # An orchestral score does, which is what makes connectivity a good
        # filter there. An open score — one staff per voice, as counterpoint
        # and vocal music are set — does not: each voice's barlines stop at
        # its own staff, so every real barline scores connectivity 0.00 and
        # the filter throws all of them away. (Measured on Nottebohm p.31: 4/4
        # votes and 0.00 connectivity on every barline of every system, versus
        # Mahler 5 p.11 where real barlines run 0.4-1.0 and it is the stem
        # alignments that score 0.00.)
        #
        # So ask the system which kind it is, rather than assuming. If most
        # of the columns the votes already accept are connected, connectivity
        # is meaningful here and gets to filter; if hardly any are, this is an
        # open score and the votes stand alone. Either way the answer comes
        # from the page in hand.
        vote_passed = [
            (int(round(sum(c) / len(c))), i) for i, c in enumerate(clusters)
            if len(c) >= min_votes
        ]
        connectivity_of = {
            x: _intersystem_connectivity(
                bin_img, staves, x, x_by_staff=_x_by_staff(i)
            )
            for x, i in vote_passed
        } if n_staves >= 2 else {}
        n_connected = sum(1 for v in connectivity_of.values() if v >= 0.4)
        barlines_cross_gaps = (
            len(vote_passed) < 2 or n_connected * 2 >= len(vote_passed)
        )

        accepted: list[int] = []
        for cluster_index, cluster in enumerate(clusters):
            x_mean = int(round(sum(cluster) / len(cluster)))
            n_votes = len(cluster)
            if n_staves < 3:
                # Small systems keep the vote-only acceptance, and gain a
                # rescue on top of it. The vote — both staves must agree — is
                # right when both can see, and on a page where one hand plays
                # continuously the busy staff stops seeing: on WTC I Prelude 1
                # page 4 the left hand reads all four barlines of every system
                # while the right hand, thick with sixteenths, reads none of
                # them and thirty-one of its own stems instead, and five systems
                # of three bars each came out as ONE bar.
                #
                # The rescue tests the span, not the gap. A fugue's long stem
                # can cross the brace gap and score full connectivity (WTC I
                # p.6 has one), but only a barline is inked from the top of the
                # upper staff to the bottom of the lower.
                #
                # Acceptance stays vote-FIRST: a system's opening rule often
                # does not span the brace either (the brace is drawn separately)
                # and letting the span test veto costs every system its first
                # barline — measured, four per system down to three.
                if n_votes >= min_votes:
                    accepted.append(x_mean)
                    continue
                if n_votes >= 1 and _spans_system(
                    bin_img, staves, x_mean, x_by_staff=_x_by_staff(cluster_index)
                ) >= SPAN_MIN_INK:
                    accepted.append(x_mean)
                continue
            if not barlines_cross_gaps:
                # Open score: the votes are the whole of the evidence.
                if n_votes >= min_votes:
                    accepted.append(x_mean)
                continue
            connectivity = connectivity_of.get(x_mean)
            if connectivity is None:
                connectivity = _intersystem_connectivity(
                    bin_img, staves, x_mean, x_by_staff=_x_by_staff(cluster_index)
                )
            # Prong A: vote-pass + connectivity sanity check.
            if n_votes >= min_votes and connectivity >= 0.4:
                accepted.append(x_mean)
                continue
            # Prong B: rescue sparse real barlines via strong connectivity.
            #
            # A braced piano system needs its own floor. Requiring both staves
            # to vote is right when both can see, and on a page where one hand
            # plays continuously the busy staff stops seeing: on WTC I Prelude 1
            # page 2 the left hand reads all four barlines of every system and
            # the right hand, thick with sixteenths, reads none of them and
            # thirty-one of its own stems instead — so five systems of three
            # bars each came out as one bar. The brace gap tells those apart
            # exactly: every real barline there scores 1.00 across it and every
            # stem 0.00, because a stem stops at its own staff.
            rescue_min_votes = 1 if n_staves <= 2 else max(3, int(0.3 * n_staves))
            if connectivity >= 0.7 and n_votes >= rescue_min_votes:
                accepted.append(x_mean)
        accepted.sort()
        # Second pass: outlier-small-gap rejection. Real measure widths
        # cluster tightly; false-positive columns produce abnormally small
        # gaps. Remove the smaller member of any adjacent pair whose gap is
        # < 0.5 × median gap.
        accepted = _drop_close_outliers(accepted)
        for x_mean in accepted:
            pws.barlines.append(Barline(
                page_index=pws.page.page_index,
                x=x_mean,
                y_top=y_top,
                y_bottom=y_bot,
                system_index=sys_idx,
            ))
    return pws


def _drop_close_outliers(xs: list[int]) -> list[int]:
    """Given a sorted list of barline x's on a system, drop entries that
    create gaps much smaller than the median gap (likely false positives).

    Conservative: only applies when there are ≥6 barlines (enough samples
    for median to be meaningful) AND the gap is < 0.35 × median. In real
    music, the shortest legitimate measure is rarely less than ~40% of the
    median. The 0.35 threshold leaves a small margin.

    On WTC and other simple piano scores this filter is a no-op. On dense
    orchestral pages where false positives cluster between real barlines,
    it removes the spurious entries.
    """
    if len(xs) < 6:
        return list(xs)
    arr = list(xs)
    # Iterate until stable, but cap iterations to avoid pathological loops.
    for _ in range(20):
        if len(arr) < 6:
            break
        gaps = [arr[i + 1] - arr[i] for i in range(len(arr) - 1)]
        median_gap = float(np.median(gaps))
        if median_gap <= 0:
            break
        too_small = [(i, gaps[i]) for i in range(len(gaps)) if gaps[i] < 0.35 * median_gap]
        if not too_small:
            break
        i, _ = min(too_small, key=lambda t: t[1])
        # Drop the member whose OTHER neighbor gap is also abnormally small
        # (likely the spurious entry). Default: drop the left entry.
        left_neighbor_gap = gaps[i - 1] if i - 1 >= 0 else median_gap
        right_neighbor_gap = gaps[i + 1] if i + 1 < len(gaps) else median_gap
        if right_neighbor_gap < left_neighbor_gap:
            arr.pop(i + 1)
        else:
            arr.pop(i)
    return arr


# ─── Per-measure cell extraction ─────────────────────────────────────────────


def _measure_x_boundaries(barlines: list[Barline], staves: list[Staff]) -> list[tuple[int, int]]:
    """Given barlines for a system and that system's staves, produce the
    list of (x_start, x_end) per measure.

    The first measure starts at the system's leftmost staff content (the
    staff's x_start, which is the left end of the staff lines) and runs to the
    first barline. Subsequent measures run between barlines. The last measure
    runs from the final barline to the rightmost staff edge.
    """
    if not staves:
        return []
    # The staves of a system are engraved flush — bracketed together and
    # starting at the same x — so the system's edges are a CONSENSUS across its
    # staves, not the extreme. Taking min/max lets a single staff whose line
    # extent came out long (a brace stroke picked up, a margin mark bridged)
    # drag the whole system's left edge out with it, and everything between the
    # false edge and the real one becomes a sliver "measure" holding the clef.
    # Observed on Boléro p.31: one staff of seventeen read 4.5 staff spaces
    # wider than its neighbours and cost that system its clefs.
    x_lo = int(round(float(np.median([s.x_start for s in staves]))))
    x_hi = max(s.x_end for s in staves)
    xs = sorted({bl.x for bl in barlines})
    # Drop barlines that coincide with the system edges: the rule closing the
    # system, and the one opening it as part of the bracket. Neither divides
    # two measures, and treating the opening one as a boundary manufactures a
    # sliver "measure" a couple of staff spaces wide in front of the real
    # first measure — which then swallows the clef, since the clef sits in
    # exactly that strip.
    #
    # The margin scales with the staff because that is what it is really
    # measuring: engravers set the opening rule a small fraction of a staff
    # space from the line start, but "small" in pixels depends on the print
    # size and the DPI (observed at 1.5 staff spaces on Boléro, where a fixed
    # 10px margin missed it). Two staff spaces is far wider than any opening
    # rule's offset and far narrower than the narrowest real measure.
    spacing = float(np.median([s.line_spacing_px for s in staves]))
    edge_margin = max(10, int(round(2.0 * spacing)))
    xs = [x for x in xs if x > x_lo + edge_margin and x < x_hi - edge_margin]
    boundaries: list[tuple[int, int]] = []
    prev = x_lo
    for x in xs:
        boundaries.append((prev, x))
        prev = x
    # Trailing tail: from the final barline to x_hi. A tail much narrower than
    # a real measure is usually the strip between the score's final barline and
    # the end of the staff lines, which holds nothing and is not a measure.
    #
    # It is not, however, safe to DISCARD it. Doing so assumes the last
    # detected barline is the last real one, and when a spurious barline is
    # detected near the end of a system — two stems that happen to align across
    # the staves will do it — everything after it is silently deleted from the
    # page. Measured on WTC p.6 system 2: a false barline at x=4476 (no ink
    # crosses the staves there; the notes on either side merely line up) made
    # the last 340px its tail, and the notes standing in it never reached the
    # detector. The measure COUNT was right, so nothing downstream could tell.
    #
    # So absorb the tail into the last measure instead. When the assumption
    # holds, the cost is a sliver of blank paper on one cell; when it does not,
    # the music is still there.
    widths = [x1 - x0 for (x0, x1) in boundaries]
    tail_width = x_hi - prev
    if boundaries and widths:
        median_w = sorted(widths)[len(widths) // 2]
        if tail_width >= median_w * 0.20:
            boundaries.append((prev, x_hi))
        else:
            last_start, _ = boundaries[-1]
            boundaries[-1] = (last_start, x_hi)
    else:
        boundaries.append((prev, x_hi))
    return boundaries


def _upscale_to_canonical(
    cell: np.ndarray, staff_span_px: int, staff_line_ys_local: list[int],
    max_width: int,
) -> tuple[np.ndarray, float, list[int]]:
    """Upscale a measure cell so its staff span equals CANONICAL_STAFF_SPAN_PX.
    If the resulting width would exceed `max_width`, scale by width instead
    (so the staff stays smaller than canonical but the cell fits the budget).
    Returns (image, scale_factor, new_staff_line_ys)."""
    if staff_span_px <= 0:
        return cell, 1.0, staff_line_ys_local

    h, w = cell.shape[:2]
    scale_by_height = CANONICAL_STAFF_SPAN_PX / staff_span_px
    new_w = int(w * scale_by_height)
    if new_w > max_width:
        scale = max_width / w
    else:
        scale = scale_by_height

    new_w = int(w * scale)
    new_h = int(h * scale)
    interp = cv2.INTER_CUBIC if scale >= 1.0 else cv2.INTER_AREA
    out = cv2.resize(cell, (new_w, new_h), interpolation=interp)
    new_line_ys = [int(round(y * scale)) for y in staff_line_ys_local]
    return out, scale, new_line_ys


def _neighbour_room(pws: PageWithStaves, staff: Staff) -> tuple[float, float]:
    """Px from this staff's top and bottom lines to the nearest neighbouring
    staff line, above and below. `inf` where there is no neighbour that side,
    which the caller clamps to the ceiling.

    Page order rather than system order on purpose: a staff at the foot of one
    system and one at the head of the next are far apart, so the gap is large
    and the ceiling applies anyway — while a page whose systems interleave
    badly still gets a cell that stays off its neighbour's lines.
    """
    above = below = float("inf")
    for other in pws.staves:
        if other is staff or len(other.line_ys) < 5:
            continue
        if other.bottom_y <= staff.top_y:
            above = min(above, float(staff.top_y - other.bottom_y))
        elif other.top_y >= staff.bottom_y:
            below = min(below, float(other.top_y - staff.bottom_y))
    return above, below


# ─── Localizing a cell's staff-line grid to the ink under it ─────────────────
#
# `Staff.line_ys` is five ideal horizontal rows fitted across the staff's whole
# width (`types.Staff`), and `_build_measure_cell` copies those five constants
# into every one of the staff's cells. On a SCAN the printed staff tilts or
# bows: measured over 7 staves of 5 editions, the residual (printed − modeled)
# is a smooth ramp, near zero mid-staff and 8–17 page px at the ends — 0.3–0.65
# staff spaces (`benchmarks/omr-cell-grid-tilt-2026-09/FINDINGS.md`). Half a
# space is the distance from a line to the space beside it, so an end-of-staff
# cell's stored grid can name the wrong slot for every note in the bar, and
# `pitch_resolver` reads exactly these per-cell rows.
#
# So the staff-level model stays as it is — five ideal rows, one description of
# the whole staff — and only the PER-CELL copy is moved onto the ink beneath
# that cell. `header_ink.refine_staff_lines_in_cell` does exactly this for
# HEADER cells already, and measured the fault's shape there: the staff is
# DISPLACED, not distorted, so one rigid offset for all five rows is the right
# correction — and it is also all the canonical cell frame can express without
# changing the span every cell is normalised by.
#
# ⚠️ THE FIVE ROWS ARE SLID AS ONE COMB, NOT MEASURED ONE AT A TIME, and the
# reason is the largest case in the corpus. Following each line to its own
# nearest ink (`header_ink.trace_staff_line`, re-seeded to extend its reach)
# agrees with the hand-traced residual to within 0.08 spaces on six of the
# seven flagged cells — and on the seventh, Dvořák 9 p.8 staff 4 at −0.55
# spaces, it ALIASES: past half a space the nearest printed line to a modeled
# row is the row BELOW it, some of the five lock onto their neighbours and some
# do not, and the five offsets it returns spread 20.5 px against 0.5–2.0 px on
# every coherent case. It answered +0.32 where the truth is −0.55 — a
# correction 0.87 spaces the wrong way, worse than leaving the grid alone.
# Sliding the whole comb cannot alias inside a bound smaller than one spacing,
# because moving a five-line comb by a spacing leaves only four of its rows on
# a printed line.
#
# Measured cost, and why this is behind a flag rather than shipped:
# `benchmarks/omr-cell-grid-tilt-2026-09/RESULTS_TILT_COST.md`. It recovers
# every displacement traced by hand and moves the scan e2e benchmark by 4 edits
# of 7894 — because 0.4% of that benchmark's cells are affected against 8–16%
# of pages sampled deeper into the same editions. A null result on a corpus
# without the defect is not evidence either way.
ENV_CELL_LINE_TRACE = "OMR_CELL_LINE_TRACE"

# How far the comb may slide. Bounded BELOW one spacing on purpose — that is
# what makes aliasing unreachable rather than merely unlikely — and above the
# 0.65 spaces of the largest displacement measured.
CELL_LINE_MAX_SHIFT_SPACES = 0.75

# At the winning shift, this much of the cell's width must be inked at
# `CELL_LINE_MIN_ROWS_COVERED` of the five rows. This is the coherence test
# that replaces per-line matching's missing one: it asserts that printed staff
# lines really are there, so a cell whose profile is dominated by a beam or a
# chord — one strong row, not a comb — abstains instead of dragging its grid
# onto the glyph.
CELL_LINE_MIN_ROW_COVERAGE = 0.45

# ⚠️ FOUR OF FIVE, NOT ALL FIVE, and requiring all five threw away a correct
# answer on one of the two labels this whole thread exists to have prevented.
# `brahms1-p2-sys1-s20-m6` (FINDINGS §3's second silent wrong label) fits at
# −0.436 spaces against a hand-measured −0.40, with row coverage
# [1.00, 1.00, 0.374, 1.00, 1.00] — because the staff's own modeled rows are
# unevenly spaced (gaps 27, 22, 33, 28 px at spacing 27.5), so one comb row
# cannot sit on the print at ANY shift. The staff is not merely displaced
# there; phase 1's fit is itself distorted, and a rigid comb inherits that.
# Four rows agreeing at 1.00 is overwhelming evidence of a staff either way.
# This does not reopen the narrow-cell alias, which passes coverage on all
# five rows and is refused by width instead.
CELL_LINE_MIN_ROWS_COVERED = 4

# Below this, the fit has measured nothing — the comb is scored at integer
# page rows, so a one-pixel "displacement" is its own quantization. Measured on
# the engraved Beethoven fixture, a LilyPond page whose staves are straight by
# construction: 32 of its 144 cells answer a non-zero shift and the largest is
# 0.024 spaces, which is exactly 1 px at that spacing. Refusing those is what
# makes the engraved control a no-op that can be PROVED rather than hoped for,
# and it forfeits nothing on the scan side, where every displacement measured
# by hand is 8–17 px.
CELL_LINE_MIN_SHIFT_SPACES = 0.05

# A cell this narrow has too little horizontal evidence to fit a comb to, and
# it aliases rather than failing quietly. Measured on the scan corpus with the
# shift bound deliberately raised past a spacing: every cell that then answered
# beyond half a space is 2.2–3.7 staff spaces wide, they cluster within a few
# percent of ±1.0 SPACING, and their row coverage is 1.00 — so the coherence
# test cannot see it. It is the comb sliding a whole line: four of its five
# rows still land on a printed line, and in a narrow cell nothing else votes.
# Six of them are Dvořák's brace cells, the system furniture that
# `benchmarks/omr-scan-e2e-2026-09/RESULTS.md` §1 measures at 2.2 spaces.
# The shift bound already refuses a full-spacing alias; this refuses the
# partial ones it would let through, and every displacement measured by hand
# lives in a cell 9 spaces wide or wider.
CELL_LINE_MIN_WIDTH_SPACES = 4.0


def _cell_line_trace_enabled() -> bool:
    """`OMR_CELL_LINE_TRACE` env; default OFF while it is being measured."""
    raw = os.environ.get(ENV_CELL_LINE_TRACE, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _cell_line_offset(
    pws: PageWithStaves, staff: Staff, x0: int, x1: int
) -> tuple[int, dict] | None:
    """How far this cell's printed staff sits from the rows the page-wide fit
    assigned it, in page pixels — `(offset, provenance)`, or None to abstain.

    Positive means the print sits BELOW the model. One number for all five
    rows; see the section comment above for why rigid, and why a comb.
    """
    binary = pws.page.binary
    ys = [int(y) for y in staff.line_ys]
    spacing = float(staff.line_spacing_px)
    if len(ys) < 5 or spacing <= 0:
        return None
    height, width = binary.shape[:2]
    lo, hi = max(0, int(x0)), min(width, int(x1))
    if (hi - lo) < max(2.0, CELL_LINE_MIN_WIDTH_SPACES * spacing):
        return None

    limit = int(round(CELL_LINE_MAX_SHIFT_SPACES * spacing))
    band_lo = max(0, min(ys) - limit - 2)
    band_hi = min(height, max(ys) + limit + 3)
    if band_hi - band_lo < 5:
        return None
    # Phase 1's binary is 0=ink. Per-row ink counts over the cell's own columns
    # — a printed line spans the cell's whole width, so it is a peak here
    # however much glyph ink sits on top of it.
    row_ink = (binary[band_lo:band_hi, lo:hi] == 0).sum(axis=1).astype(float)
    n_rows = row_ink.shape[0]
    cell_width = float(hi - lo)

    def rows_at(shift: int) -> list[int]:
        return [y + shift - band_lo for y in ys]

    def bands_at(shift: int) -> list[tuple[int, int]]:
        return [(max(0, r - 1), min(n_rows, r + 2)) for r in rows_at(shift)]

    def score(shift: int) -> float:
        return sum(float(row_ink[a:b].sum()) for a, b in bands_at(shift) if a < b)

    # Ties go to the SMALLER move: "do not move without a reason" is the whole
    # posture here, and on a cell whose grid is already right the modeled rows
    # and a neighbouring shift can score identically.
    best_shift = max(range(-limit, limit + 1), key=lambda s: (score(s), -abs(s)))
    if score(best_shift) <= 0:
        return None
    if abs(best_shift) < CELL_LINE_MIN_SHIFT_SPACES * spacing:
        return None  # nothing measured — see the constant

    coverage = [float(row_ink[a:b].max()) / cell_width if a < b else 0.0
                for a, b in bands_at(best_shift)]
    covered = sum(1 for c in coverage if c >= CELL_LINE_MIN_ROW_COVERAGE)
    if covered < CELL_LINE_MIN_ROWS_COVERED:
        return None  # no staff-line comb under this cell — see the constants

    return best_shift, {
        "offset_px": best_shift,
        "offset_spaces": round(best_shift / spacing, 3),
        "rows_covered": covered,
        "min_row_coverage": round(min(coverage), 3),
    }


def _build_measure_cell(
    pws: PageWithStaves,
    staff: Staff,
    system_index: int,
    x0: int,
    x1: int,
    measure_index: int,
    max_cell_width: int = MAX_CELL_WIDTH_PX,
) -> MeasureCell | None:
    """Crop + canonically-upscale one (staff, x0:x1) cell from the page.

    Shared by `extract_measures` (the initial page-wide scan) and
    `resegment_fused_measures` (local re-split of a single already-flagged
    fused cell) so both paths produce identically-shaped MeasureCell
    objects. Returns None if the x-range is degenerate (<10px wide after
    clamping to the page) — mirrors the "too narrow, skip" guard that used
    to live inline in extract_measures.
    """
    rgb = pws.page.rgb
    binary = pws.page.binary
    spacing = max(1.0, staff.line_spacing_px)
    clearance = CELL_NEIGHBOUR_CLEARANCE_SPACES * spacing
    room_above, room_below = _neighbour_room(pws, staff)
    ceiling = PAD_MAX_STAFF_LINES * spacing

    def grown(default_spaces: float, room: float) -> int:
        default = default_spaces * spacing
        return int(ceiling if room - clearance >= ceiling else default)

    pad_above = grown(PAD_ABOVE_STAFF_LINES, room_above)
    pad_below = grown(PAD_BELOW_STAFF_LINES, room_below)
    y0 = max(0, staff.top_y - pad_above)
    y1 = min(rgb.shape[0], staff.bottom_y + pad_below)
    x0 = max(0, x0)
    x1 = min(rgb.shape[1], x1)
    if x1 - x0 < 10:
        return None  # too narrow, skip
    cell_rgb = rgb[y0:y1, x0:x1].copy()
    # Staff line ys in the cell's local coordinate frame.
    #
    # The CROP is deliberately left where the staff-level model put it — only
    # the stored grid localizes. A cell is normalised by its staff's span and
    # padded in staff spaces, so moving the crop would move the canonical frame
    # that every saved box in the labeling batches lives in, for a shift that
    # is a small fraction of a four-space pad.
    line_offset = (
        _cell_line_offset(pws, staff, x0, x1)
        if _cell_line_trace_enabled() else None
    )
    if line_offset is not None:
        shift, line_prov = line_offset
        local_ys = [int(round(y + shift)) - y0 for y in staff.line_ys]
    else:
        line_prov = None
        local_ys = [y - y0 for y in staff.line_ys]
    page_span = staff.span_px
    up_rgb, scale, up_ys = _upscale_to_canonical(
        cell_rgb, page_span, local_ys, max_cell_width,
    )
    # Convert binary slice too, with the same scale, for later use
    cell_bin = binary[y0:y1, x0:x1]
    up_bin = cv2.resize(
        cell_bin,
        (up_rgb.shape[1], up_rgb.shape[0]),
        interpolation=cv2.INTER_NEAREST,
    )

    cell = MeasureCell(
        page_index=pws.page.page_index,
        system_index=system_index,
        staff_index=staff.staff_index,
        measure_index=measure_index,
        image=up_rgb,
        image_no_staff=None,  # filled in by staff_line_removal
        bbox_page_px=(x0, y0, x1, y1),
        staff_line_ys_canonical=up_ys,
        upscale_factor=scale,
        staff_line_thickness_canonical=(
            round(staff.median_line_thickness_px * scale, 3)
            if staff.median_line_thickness_px is not None
            else None
        ),
    )
    # Stash binary on the cell as a side-channel attribute for the
    # staff-line-removal step. (Not part of MeasureCell's formal schema —
    # kept dynamic for now.)
    cell.__dict__["binary"] = up_bin
    if line_prov is not None:
        cell.__dict__["line_grid_localized"] = line_prov
    return cell


def extract_measures(
    pws: PageWithStaves,
    canonical_staff_span: int = CANONICAL_STAFF_SPAN_PX,
    max_cell_width: int = MAX_CELL_WIDTH_PX,
) -> list[MeasureCell]:
    """Crop one MeasureCell per (staff × measure) on the page, upscaled to
    canonical size for downstream symbol detection."""
    if not pws.barlines:
        detect_barlines(pws)
    cells: list[MeasureCell] = []

    # Group staves & barlines by system
    # As in `detect_barlines`, one-line percussion staves are skipped. They are
    # detected so that the staves below them keep their slots (see
    # `staff_detector._single_line_staff_rows`); reading their CONTENT is a
    # separate piece of work, because a cell is canonicalised by its staff's
    # five-line span and a single rule has none.
    sys_staves: dict[int, list[Staff]] = {}
    for s in pws.staves:
        if len(s.line_ys) >= 5:
            sys_staves.setdefault(s.system_index, []).append(s)
    sys_barlines: dict[int, list[Barline]] = {}
    for bl in pws.barlines:
        sys_barlines.setdefault(bl.system_index, []).append(bl)

    for sys_idx, staves in sys_staves.items():
        bls = sys_barlines.get(sys_idx, [])
        xb = _measure_x_boundaries(bls, staves)
        for staff in staves:
            for m_idx, (x0, x1) in enumerate(xb):
                cell = _build_measure_cell(
                    pws, staff, sys_idx, x0, x1, m_idx,
                    max_cell_width=max_cell_width,
                )
                if cell is not None:
                    cells.append(cell)
    return cells


# ─── Local re-segmentation of fused measures (Phase 1i) ──────────────────────
#
# Problem: on dense orchestral pages, the system-level barline vote in
# `detect_barlines` sometimes misses a real internal barline (faint ink,
# partial staff occlusion, a column that only a minority of staves voted
# for). The result is one over-wide MeasureCell that actually contains 2+
# real measures fused together. transcribe.py already detects this after
# the fact — any cell wider than 2x its staff's median measure width gets
# `phase1_warning` set (see the width check in transcribe.py's per-staff
# loop). Beethoven 5 p15: 18 of 98 measures were such outliers.
#
# Fix: re-run barline detection *inside* each already-flagged wide cell,
# with a lower height threshold (real barlines are sometimes exactly what
# got missed at the global threshold) and a lower cross-staff vote
# requirement (justified because the search window is now narrow — far
# fewer candidate columns, so false positives are much less likely to slip
# through). A candidate is only trusted if the resulting sub-measures all
# land within a plausible width band of the staff's median; otherwise the
# whole split is rejected and the cell is left exactly as Phase 1 produced
# it (still carrying its width outlier, still eligible for phase1_warning
# downstream).
#
# This pass is intentionally narrow in scope:
#   - It NEVER touches a normal-width cell — only cells already flagged as
#     >2x-median outliers are examined at all.
#   - It NEVER changes the global BARLINE_MIN_HEIGHT_FRAC or the global
#     per-system vote thresholds in detect_barlines/_detect_barlines_per_staff.
#   - It is MULTI-STAFF ONLY: a candidate must be voted for by ≥2 staves
#     AND drawn through the inter-staff gap ink (connectivity). Single-staff
#     "systems" (isolated instrument lines, or staff-detector mis-groupings)
#     get no cross-staff corroboration, and the relaxed height test alone is
#     fooled by dense tremolo/beam ink — so they are skipped. (On the
#     Debussy validation set the single-staff path produced the one
#     unverifiable split; every multi-staff split landed on a real barline.)
#   - Barline x-positions are shared by every staff in a system (see
#     `_measure_x_boundaries` — one `xb` list is reused for all staves), so
#     a flagged measure_index is a SYSTEM-level event: candidates are
#     searched using every staff in the system for corroboration, and an
#     accepted split is applied identically to every staff in that system,
#     then measure_index is renumbered sequentially so downstream code
#     (transcribe.py) sees an ordinary 0..N-1 run per staff.
# Together these make it categorically different from (and much safer
# than) globally raising BARLINE_MIN_HEIGHT_FRAC, which over-segmented
# Beethoven 98->162->218 measures (see the tuning note at the top of this
# file) because it fires on *every* cell, not just already-fused ones.

# Height threshold used when searching INSIDE an already-flagged cell.
# Deliberately more lenient than the global BARLINE_MIN_HEIGHT_FRAC (0.80)
# because a faint/partially-obscured barline is a plausible reason Phase 1
# missed it in the first place. Safe to relax here because this function is
# never called on a normal-width cell.
RESEGMENT_MIN_HEIGHT_FRAC = 0.60
# Minimum fraction of staves in the system that must vote for a candidate
# column (vs. up to 0.80 for the global per-system vote in detect_barlines).
# Safe to relax because the search window is a single narrow cell, not the
# whole page, so there are far fewer candidate columns to false-positive on.
RESEGMENT_MIN_VOTE_FRAC = 0.30
# Minimum inter-staff-gap ink continuity (see _intersystem_connectivity) a
# candidate column must show. A genuine barline is drawn through the
# whitespace between staves; a stem or chord-column coincidence is not.
RESEGMENT_MIN_CONNECTIVITY = 0.5
# Matches the >2x-median check transcribe.py uses to set phase1_warning —
# a cell is only a re-segmentation CANDIDATE if it's already flagged there.
RESEGMENT_WIDTH_WARN_FACTOR = 2.0
# Acceptance band (guardrail c): every resulting sub-measure's width must
# land within [MIN_PIECE_FRAC, MAX_PIECE_FRAC] x the staff's median measure
# width, or the whole split is rejected — never emit a sliver, and never
# emit a piece that's still an implausible-width outlier.
RESEGMENT_MIN_PIECE_FRAC = 0.5
RESEGMENT_MAX_PIECE_FRAC = 1.75
# STEERED mode only (a system's true bar count is known and the conservative pass
# left it SHORT): a lower width threshold, so a fused pair of narrowish bars
# (below the 2x flag) is still reconsidered. The upper-width
# guard (MAX_PIECE_FRAC) is dropped under steering — the known count overrides
# the "still an outlier" heuristic — but the sliver floor (MIN_PIECE_FRAC) is
# always kept, and a genuine internal barline (ink) is still required. Bounded:
# never split past the known count.
RESEGMENT_STEER_WIDTH_FACTOR = 1.5


def _find_internal_barline_candidates(
    bin_img: np.ndarray, staves: list[Staff], x0: int, x1: int,
) -> list[int]:
    """Search the narrow window [x0, x1) — a cell transcribe.py already
    flagged as a fused-measure outlier — for internal barlines.

    Uses relaxed per-staff height thresholds (RESEGMENT_MIN_HEIGHT_FRAC)
    plus the same inter-staff connectivity check the global pass uses
    (`_intersystem_connectivity`), scaled down (RESEGMENT_MIN_VOTE_FRAC /
    RESEGMENT_MIN_CONNECTIVITY) to reflect that a narrow, already-suspect
    window has far less room for false positives than a whole page.

    MULTI-STAFF ONLY. A candidate must be corroborated by ≥2 staves of the
    system AND drawn through the inter-staff whitespace (connectivity). A
    single-staff "system" (an isolated instrument line, or a staff-detector
    mis-grouping) has no cross-staff corroboration available, so the only
    discriminator left is the relaxed height test — which dense
    tremolo/beam ink on orchestral pages readily fools. Empirically, the
    single-staff path produced the one unverifiable Debussy split (p9 sys0,
    a dense tremolo staff) while every multi-staff split landed on a real
    barline (e.g. p10 sys4, 7 staves). So we skip single-staff systems
    entirely and lean on connectivity for the rest — that's exactly the
    "consistent across staves of the system" signal a real barline gives.

    Returns accepted x positions, sorted, strictly inside (x0, x1) —
    candidates within BARLINE_MIN_DISTANCE_PX of either edge are dropped
    because those are almost always the cell's OWN bounding barlines
    getting re-detected, not a genuine internal split point.
    """
    n_staves = len(staves)
    if n_staves < 2 or x1 - x0 < 2 * BARLINE_MIN_DISTANCE_PX:
        return []  # single-staff (no corroboration) or too narrow

    all_xs: list[int] = []
    for staff in staves:
        all_xs.extend(
            _detect_barlines_in_window(
                bin_img, staff, x0, x1, RESEGMENT_MIN_HEIGHT_FRAC,
                # Inside a fused cell a competing note stem is the norm, not the
                # exception, so height decides — see _dedup_barline_candidates.
                # The whole-page pass keeps the leftmost rule unchanged.
                prefer="tallest",
            )
        )
    if not all_xs:
        return []
    all_xs.sort()

    # Cluster close x's together (same tolerance the global pass uses).
    x_tolerance = 12
    clusters: list[list[int]] = []
    for x in all_xs:
        if clusters and x - clusters[-1][-1] <= x_tolerance:
            clusters[-1].append(x)
        else:
            clusters.append([x])

    # ≥2 votes always required (a lone staff firing can never carry a
    # split); scale up with system size but keep the floor at 2.
    min_votes = max(2, int(round(RESEGMENT_MIN_VOTE_FRAC * n_staves)))

    accepted: list[int] = []
    for cluster in clusters:
        x_mean = int(round(sum(cluster) / len(cluster)))
        if x_mean <= x0 + BARLINE_MIN_DISTANCE_PX or x_mean >= x1 - BARLINE_MIN_DISTANCE_PX:
            continue  # too close to the cell's own edges
        n_votes = len(cluster)
        # Connectivity is meaningful for ≥2 staves (≥1 inter-staff gap): a
        # real barline is drawn through the gap ink, a coincidental stem
        # column is not.
        connectivity = _intersystem_connectivity(bin_img, staves, x_mean)
        if n_votes >= min_votes and connectivity >= RESEGMENT_MIN_CONNECTIVITY:
            accepted.append(x_mean)
    accepted.sort()
    deduped: list[int] = []
    for x in accepted:
        if not deduped or x - deduped[-1] >= BARLINE_MIN_DISTANCE_PX:
            deduped.append(x)
    return deduped


def majority_bars_by_system(
    cells: list[MeasureCell],
    *,
    min_staves: int = 2,
) -> dict[int, int]:
    """Per system, the bar count held by a strict majority of its staves.

    Every staff in a system is printed against the same barlines, so its staves
    should agree on how many bars the system has. When they do not, the majority
    is the count and a short staff has a fused pair somewhere. That is the same
    reasoning `transcribe._flag_measure_count_inconsistency` uses to FLAG the
    disagreement after detection; computing it here, straight off the cells, is
    what lets `resegment_fused_measures` ACT on it instead — and it needs nothing
    but cell counts, so it runs before a single symbol has been detected.

    Deliberately narrow, because the output steers a split:

    - **Strict majority required.** `mode_k * 2 > total` means the modal group
      holds MORE than half the staves, so the modal count is the unique mode and
      the deviating staves are unambiguously the minority. A 2-2 or 3-3 split
      abstains — there is no basis to call either side wrong.
    - **Systems below `min_staves` abstain.** One staff has no sibling to be
      checked against, and asserting a count from it is circular.
    - **Only the majority is reported**, never a per-staff target, so the caller
      cannot be steered toward a count no staff actually read.

    A system that abstains is simply absent from the result, which
    `resegment_fused_measures` reads as "no expectation here".
    """
    per_staff: Counter[tuple[int, int]] = Counter()
    for c in cells:
        per_staff[(c.system_index, c.staff_index)] += 1

    by_system: dict[int, list[int]] = {}
    for (sys_idx, _staff_idx), n in per_staff.items():
        by_system.setdefault(sys_idx, []).append(n)

    out: dict[int, int] = {}
    for sys_idx, counts in by_system.items():
        total = len(counts)
        if total < min_staves:
            continue
        mode_value, mode_k = Counter(counts).most_common(1)[0]
        if mode_k * 2 <= total:
            continue  # no strict majority -> abstain
        out[sys_idx] = mode_value
    return out


def _select_steered_splits(
    candidate_cells: list[tuple[int, int, int, list[int]]],
    shortfall: int,
    median_w: float,
    *,
    min_piece_frac: float = RESEGMENT_MIN_PIECE_FRAC,
) -> dict[int, list[int]]:
    """Pick steered splits to fill a `shortfall` of bars in a system.

    `candidate_cells` are the un-split, wide-enough cells
    `(measure_index, x0, x1, barline_candidates)` in WIDEST-first order. A cell's
    split adds `len(candidates)` bars. A split is accepted only when it is backed
    by genuine barline candidates, no resulting piece is a sliver
    (< `min_piece_frac` x median — the false-barline guard, always kept), and it
    does NOT overshoot the shortfall. The upper-width guard is deliberately
    absent: the known count overrides "this piece is still an outlier". Pure (no
    image) so it's unit-testable. Returns `{measure_index: [x0, ...cands, x1]}`.
    """
    out: dict[int, list[int]] = {}
    remaining = shortfall
    for measure_index, x0, x1, candidates in candidate_cells:
        if remaining <= 0:
            break
        if not candidates:
            continue
        added = len(candidates)
        if added > remaining:
            continue  # would split past the known count -> skip (never overshoot)
        boundaries = [x0] + list(candidates) + [x1]
        pieces = [boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)]
        if any(p < median_w * min_piece_frac for p in pieces):
            continue  # a resulting piece would be a sliver -> reject (false barline)
        out[measure_index] = boundaries
        remaining -= added
    return out


def resegment_fused_measures(
    pws: PageWithStaves,
    cells: list[MeasureCell],
    max_cell_width: int = MAX_CELL_WIDTH_PX,
    *,
    expected_bars_by_system: dict[int, int] | None = None,
) -> list[MeasureCell]:
    """Local re-segmentation pass over cells `extract_measures` already
    produced: split cells that are >2x-median-width outliers back into
    their real sub-measures wherever a genuine internal barline can be
    found, WITHOUT ever touching normal-width cells or global thresholds.
    See the module-level comment above for the full rationale.

    Cells that aren't split are returned unchanged (same object identity).
    Cells that ARE split are replaced by 2+ new cells built via
    `_build_measure_cell`, and every staff in the affected system has its
    measure_index renumbered 0..N-1 afterward (barline x-positions are
    shared across a system's staves, so a flagged cell at measure_index m
    implies every staff in that system needs the same split at m).

    `expected_bars_by_system` (steered mode) maps system_index -> the known bar
    count; a system the conservative pass left SHORT is re-examined with relaxed
    width gates (`_select_steered_splits`), still requiring genuine barline ink
    and rejecting slivers, bounded so it never over-splits. Omitted (the default)
    ⇒ conservative behaviour, byte-identical to today.

    `majority_bars_by_system` is the intended source of that mapping: the count
    the system's own staves agree on. An external count (a dossier, a human)
    fits the same parameter, but note that a dossier generated from MusicXML
    describes the engraver's page breaks, not the scan being read.
    """
    if not cells:
        return cells

    bin_img = pws.page.binary

    # Group cells by system, then by staff, sorted by measure_index.
    by_system: dict[int, dict[int, list[MeasureCell]]] = {}
    for c in cells:
        by_system.setdefault(c.system_index, {}).setdefault(c.staff_index, []).append(c)
    for sys_idx in by_system:
        for staff_idx in by_system[sys_idx]:
            by_system[sys_idx][staff_idx].sort(key=lambda c: c.measure_index)

    result: list[MeasureCell] = []
    for sys_idx, staff_groups in by_system.items():
        # One-line percussion staves are excluded here for the same reason
        # `detect_barlines` and `extract_measures` exclude them: a staff with no
        # five-line span answers "there is a barline here" for any stem that
        # crosses it. It is also a hard error rather than merely noise —
        # `_detect_barlines_in_window` sizes its morphological kernel from the
        # staff span, and a span of 0 makes that kernel 1x0, which OpenCV
        # rejects outright. Before this filter, transcribing La Mer p.25 —
        # the very page the one-line-staff support was validated on — raised
        # cv2.error from Phase 1.
        staves = sorted(
            (s for s in pws.staves_in_system(sys_idx) if len(s.line_ys) >= 5),
            key=lambda s: s.staff_index,
        )
        if not staves:
            for staff_cells in staff_groups.values():
                result.extend(staff_cells)
            continue

        # Representative per-measure-index widths: pick the staff with the
        # most cells (guards against a staff that dropped a trailing
        # sliver cell in extract_measures) to compute the staff's median
        # measure width and to decide which measure_index values are
        # flagged. Barline x-positions — and therefore widths — are shared
        # across every staff in the system by construction
        # (_measure_x_boundaries), so any staff's cells give the same
        # answer in the normal case.
        rep_staff_idx = max(staff_groups, key=lambda k: len(staff_groups[k]))
        rep_cells = staff_groups[rep_staff_idx]
        widths = [c.bbox_page_px[2] - c.bbox_page_px[0] for c in rep_cells]
        median_w = sorted(widths)[len(widths) // 2] if widths else 0

        # measure_index -> accepted split boundaries [x0, x_mid.., x1].
        split_boundaries: dict[int, list[int]] = {}
        if median_w > 0:
            for c in rep_cells:
                x0, _, x1, _ = c.bbox_page_px
                w = x1 - x0
                if w <= median_w * RESEGMENT_WIDTH_WARN_FACTOR:
                    continue  # not a flagged outlier -- leave untouched
                candidates = _find_internal_barline_candidates(bin_img, staves, x0, x1)
                if not candidates:
                    continue  # no genuine internal barline found -- stays fused
                boundaries = [x0] + candidates + [x1]
                piece_widths = [boundaries[i + 1] - boundaries[i] for i in range(len(boundaries) - 1)]
                lo = median_w * RESEGMENT_MIN_PIECE_FRAC
                hi = median_w * RESEGMENT_MAX_PIECE_FRAC
                if all(lo <= pw <= hi for pw in piece_widths):
                    split_boundaries[c.measure_index] = boundaries
                # else: at least one resulting piece would be a sliver (or
                # still an implausible-width outlier) -- reject the WHOLE
                # split and keep the cell as Phase 1 produced it. Never
                # emit a partial/best-effort split.

        # Steered relaxation: if this system's bar count is known and the
        # conservative pass left it SHORT, reconsider the
        # wide-ish un-split cells with relaxed gates — lower width threshold, the
        # upper-width guard dropped — but still requiring a genuine internal
        # barline (ink) and rejecting slivers, bounded so we never split past the
        # known count. Inert when `expected_bars_by_system` is None or has no
        # entry for this system, so an abstaining system is byte-identical.
        if expected_bars_by_system is not None and median_w > 0:
            expected = expected_bars_by_system.get(sys_idx)
            if expected is not None:
                conservative_bars = len(rep_cells) + sum(
                    len(b) - 2 for b in split_boundaries.values()
                )
                shortfall = expected - conservative_bars
                if shortfall > 0:
                    steer_min_w = median_w * RESEGMENT_STEER_WIDTH_FACTOR
                    wide_unsplit = sorted(
                        (c for c in rep_cells
                         if c.measure_index not in split_boundaries
                         and (c.bbox_page_px[2] - c.bbox_page_px[0]) > steer_min_w),
                        key=lambda c: c.bbox_page_px[2] - c.bbox_page_px[0],
                        reverse=True,
                    )
                    candidate_cells = []
                    for c in wide_unsplit:
                        x0, _, x1, _ = c.bbox_page_px
                        cand = _find_internal_barline_candidates(bin_img, staves, x0, x1)
                        candidate_cells.append((c.measure_index, x0, x1, cand))
                    split_boundaries.update(
                        _select_steered_splits(candidate_cells, shortfall, median_w)
                    )

        if not split_boundaries:
            # Nothing splittable in this system -- pass every cell through
            # unchanged.
            for staff_cells in staff_groups.values():
                result.extend(staff_cells)
            continue

        # Apply the accepted splits identically to every staff in the
        # system, then renumber measure_index sequentially.
        for staff_idx, staff_cells in staff_groups.items():
            staff = next((s for s in staves if s.staff_index == staff_idx), None)
            new_cells: list[MeasureCell] = []
            for c in staff_cells:
                boundaries = split_boundaries.get(c.measure_index)
                if boundaries is None or staff is None:
                    new_cells.append(c)
                    continue
                for i in range(len(boundaries) - 1):
                    sub = _build_measure_cell(
                        pws, staff, sys_idx, boundaries[i], boundaries[i + 1],
                        measure_index=-1,  # placeholder -- renumbered below
                        max_cell_width=max_cell_width,
                    )
                    if sub is not None:
                        new_cells.append(sub)
            for new_idx, c in enumerate(new_cells):
                c.measure_index = new_idx
            result.extend(new_cells)

    return result


# ─── CLI ─────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse
    from .preprocessing import render_page
    from .staff_detector import detect_staves

    ap = argparse.ArgumentParser(description="Detect barlines and extract measure cells")
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    pws = detect_staves(pi)
    pws = detect_barlines(pws)
    print(f"page {args.page}: {len(pws.staves)} staves, {len(pws.barlines)} barlines")
    by_sys = {}
    for bl in pws.barlines:
        by_sys.setdefault(bl.system_index, []).append(bl.x)
    for sys, xs in sorted(by_sys.items()):
        print(f"  system {sys}: {len(xs)} barlines at x={sorted(xs)}")

    cells = extract_measures(pws)
    print(f"extracted {len(cells)} measure cells")
    if cells:
        c = cells[0]
        print(f"  first cell: {c.width}x{c.height}, scale={c.upscale_factor:.2f}, staff_ys={c.staff_line_ys_canonical}")
