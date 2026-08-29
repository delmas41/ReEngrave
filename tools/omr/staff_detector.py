"""Phase 1.2 — Staff line detection and system grouping.

Algorithm:
  1. Compute the horizontal projection profile of the binary image (sum of
     ink pixels per row). Staff line rows have high values because the line
     spans the full page width.
  2. Find peaks in the profile. Each peak is a candidate staff-line row.
  3. Cluster consecutive peaks into groups of 5 — one staff = 5 lines, the
     gaps between them are roughly equal.
  4. Group staves into systems: staves whose horizontal x-extent overlaps
     and whose vertical separation is small (typically < 3× line spacing)
     belong to the same system (e.g., piano grand staff = treble + bass).

Public surface:
    detect_staves(page) -> PageWithStaves
"""

from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks

from .types import PageImage, Staff, PageWithStaves


# ─── Tuning ──────────────────────────────────────────────────────────────────
# These work for typical 600 DPI printed scores. Adjust if very small/large
# staff sizes show up in your input.

MIN_PEAK_DISTANCE_PX = 4         # staff lines won't be closer than this
MIN_LINE_LENGTH_FRAC = 0.35      # staff line spans >= 35% of page width
PEAK_PROMINENCE_FRAC = 0.30      # peak must be 30% of (max - min) profile range
GROUP_LINE_SPACING_TOLERANCE = 0.30  # ±30% gap variation within a 5-line group
MAX_SYSTEM_GAP_FACTOR = 6.0      # fallback if auto-bipartition fails
STAFF_LINE_MAX_GAP_SPACES = 1.0  # a break this wide is still the same staff line
SYSTEM_BREAK_GAP_FACTOR = 2.5    # gap this many × the typical within-system gap = a break
MAX_LINE_INK_RUNS_PER_SPACE = 1.7  # above this the "lines" are rows of text, not staff lines


# ─── Step 1: projection profile + peak detection ─────────────────────────────


def _ink_profile(binary: np.ndarray) -> np.ndarray:
    """Per-row count of ink pixels (where binary == 0). Staff line rows have
    much higher values than text/notehead rows because the line is long."""
    return np.sum(binary == 0, axis=1)


def _candidate_staff_rows(profile: np.ndarray, page_width: int) -> np.ndarray:
    """Find rows that look like staff lines: long horizontal black runs."""
    min_run = int(page_width * MIN_LINE_LENGTH_FRAC)
    # Floor: every peak must clear the min_run threshold (so a row contains
    # at least one long line). Prominence makes peaks stand out vs neighbors.
    prom = max(1, int((profile.max() - profile.min()) * PEAK_PROMINENCE_FRAC))
    peaks, _ = find_peaks(
        profile,
        height=min_run,
        distance=MIN_PEAK_DISTANCE_PX,
        prominence=prom,
    )
    return peaks


# ─── Step 2: group peaks into 5-line staves ──────────────────────────────────


def _group_into_staves(peaks: np.ndarray) -> list[list[int]]:
    """Cluster peak rows into groups of 5 with roughly equal spacing.

    Strategy: slide through the peaks looking for any 5-peak window whose
    inter-peak gaps are all within ±tolerance of their mean. Greedy: once
    a 5-peak group is accepted, skip past it.
    """
    if len(peaks) < 5:
        return []
    peaks = list(map(int, peaks))
    groups: list[list[int]] = []
    i = 0
    while i + 4 < len(peaks):
        window = peaks[i:i + 5]
        gaps = [window[j + 1] - window[j] for j in range(4)]
        mean_gap = sum(gaps) / 4
        if mean_gap <= 0:
            i += 1
            continue
        max_dev = max(abs(g - mean_gap) for g in gaps) / mean_gap
        if max_dev <= GROUP_LINE_SPACING_TOLERANCE:
            groups.append(window)
            i += 5
        else:
            i += 1
    return groups


# ─── Step 3: find horizontal extent of each staff ────────────────────────────


def _staff_x_extent(binary: np.ndarray, line_ys: list[int]) -> tuple[int, int]:
    """Find the left/right edges of the staff lines themselves.

    The staff line row in the binary image is a long horizontal black run — but
    on a real scan it is not an UNBROKEN one. Printed lines drop out, scans
    lose ink, and the line arrives as a dashed sequence. Taking the longest
    strictly-contiguous run therefore returns whichever fragment happens to be
    longest, not the line, and the staff's left edge lands wherever the first
    break was.

    That edge is where the first measure cell starts, so the damage is
    concrete: everything to the left of it — clef, key signature, often the
    opening notes — is cropped out of every cell and cannot be read by anything
    downstream. Measured on a Bach page the offset is 1.2 staff spaces (enough
    to lose the first measure's start); on a 19th-century engraving it reaches
    46 staff spaces, well past the clef and into the middle of the music.

    So bridge breaks up to `STAFF_LINE_MAX_GAP_SPACES` of a staff space. That
    is far wider than any printing dropout and far narrower than the gap
    between two separate staves set side by side on one row, which is the case
    the tolerance must not merge.
    """
    h, w = binary.shape
    # Use the middle line as the reference for x-extent
    mid_y = line_ys[len(line_ys) // 2]
    # Look in a ±2 px neighborhood to be robust to sub-pixel position
    y0 = max(0, mid_y - 2)
    y1 = min(h, mid_y + 3)
    band = binary[y0:y1].min(axis=0)  # ink anywhere in band → ink pixel

    ink_x = np.flatnonzero(band == 0)
    if ink_x.size == 0:
        return 0, w - 1

    # Gap tolerance in pixels, from this staff's own line spacing, so the rule
    # holds at any DPI or engraving size.
    if len(line_ys) >= 2:
        spacing = (max(line_ys) - min(line_ys)) / (len(line_ys) - 1)
    else:
        spacing = 0.0
    max_gap = max(1, int(round(STAFF_LINE_MAX_GAP_SPACES * spacing)))

    # Split the ink into runs, allowing gaps of up to `max_gap` blank pixels.
    # Consecutive ink pixels differ by 1, so a run of `g` blanks shows up as a
    # difference of g + 1.
    breaks = np.flatnonzero(np.diff(ink_x) > max_gap + 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [ink_x.size - 1]))
    best = int(np.argmax(ink_x[ends] - ink_x[starts]))
    return int(ink_x[starts[best]]), int(ink_x[ends[best]])


# ─── Step 4: group staves into systems ───────────────────────────────────────


def _bipartition_threshold(values: list[float]) -> float | None:
    """Given a 1D list of values that fall into two clusters (small/large),
    return a threshold that separates them via 1D k-means (Lloyd's, k=2,
    Otsu-like). Returns None if values look unimodal."""
    if len(values) < 2:
        return None
    arr = np.asarray(values, dtype=float)
    arr_min, arr_max = float(arr.min()), float(arr.max())
    if arr_max - arr_min < 1e-6:
        return None
    # 1D Lloyd's algorithm
    c1, c2 = arr_min, arr_max
    for _ in range(20):
        mask = arr <= (c1 + c2) / 2
        if mask.all() or (~mask).all():
            return None  # all values in one cluster → unimodal
        new_c1 = float(arr[mask].mean())
        new_c2 = float(arr[~mask].mean())
        if abs(new_c1 - c1) < 1e-6 and abs(new_c2 - c2) < 1e-6:
            break
        c1, c2 = new_c1, new_c2
    # Require the gap between clusters to be at least 2x the spread of the
    # smaller cluster — otherwise this isn't really bimodal.
    intra_spread = float(np.std(arr[arr <= (c1 + c2) / 2])) or 1.0
    if (c2 - c1) < 2.0 * intra_spread:
        return None
    return (c1 + c2) / 2


# A gap counts as bridged when some column is this solidly inked through the
# whole of it. A barline or a system bracket is a continuous vertical stroke, so
# it approaches 1.0; a slur or a beam crossing the gap is nearly horizontal and
# contributes almost nothing to any single column.
_BRIDGE_INK_FRACTION = 0.8


def _gap_is_bridged(binary: np.ndarray, prev: Staff, cur: Staff) -> bool:
    """Is there a continuous vertical stroke crossing the gap between two staves?

    This is the question the gap heuristics below are really trying to answer,
    and cannot. Measured on engraved orchestral excerpts, the gaps WITHIN one
    Brahms system run 17–237 px and within one Beethoven system 130–345 px —
    both wider than the gaps BETWEEN systems on a piano page. No threshold on
    distance separates those cases, which is why one 21-staff Brahms system was
    being reported as twelve systems and an 18-staff Beethoven system as four.
    Every pair on both pages also had x-overlap 1.00, so that rule is silent
    here too.

    What actually defines a system is what connects it: barlines run the full
    height of a system, and the bracket encloses exactly it. Neither crosses a
    system break. So the scan covers the full page width — the bracket sits in
    the margin, left of any staff's ink — and asks for one column inked through
    the entire gap.
    """
    gap_top = prev.bottom_y + 1
    gap_bot = cur.top_y
    if gap_bot <= gap_top:
        return True  # touching staves — no gap to bridge
    h, w = binary.shape
    gap_top = max(0, gap_top)
    gap_bot = min(h, gap_bot)
    if gap_top >= gap_bot:
        return True
    strip = binary[gap_top:gap_bot, 0:w]
    if strip.size == 0:
        return False
    # Binarized convention: 0 = ink, 255 = paper.
    col_ink_fraction = (strip < 128).mean(axis=0)
    return bool(col_ink_fraction.max() >= _BRIDGE_INK_FRACTION)


def _assign_systems(staves: list[Staff],
                    binary: np.ndarray | None = None) -> list[Staff]:
    """A 'system' is a group of staves that are read together (e.g. grand
    staff, full orchestral score). Algorithm:

      1. Compute all inter-staff vertical gaps on the page.
      2. If the gaps cleanly bipartition into "small" (intra-system) and
         "large" (inter-system) clusters, use the midpoint as the threshold.
      3. Otherwise fall back to MAX_SYSTEM_GAP_FACTOR × line_spacing.

    Also requires horizontal overlap > 50% for two staves to be in the same
    system (catches multi-column scores).
    """
    if not staves:
        return staves
    staves_sorted = sorted(staves, key=lambda s: s.top_y)
    if len(staves_sorted) == 1:
        staves_sorted[0].system_index = 0
        return staves_sorted

    gaps = [staves_sorted[i + 1].top_y - staves_sorted[i].bottom_y
            for i in range(len(staves_sorted) - 1)]
    threshold = _bipartition_threshold(gaps)
    mean_spacing = float(np.mean([s.line_spacing_px for s in staves_sorted]))
    if threshold is None:
        threshold = mean_spacing * MAX_SYSTEM_GAP_FACTOR

    # Secondary MAD-based threshold: catches mid-magnitude system breaks
    # that bipartition merges with the small-gap cluster. Common on
    # orchestral scores where there's a clearly-bigger-than-normal gap
    # between bracketed sub-systems (e.g., winds vs brass vs strings)
    # but it's still much smaller than the page-spanning system break.
    # Rule: a gap > 2.0 × median + max(0, gap > min(fallback, ...)) is
    # also a break. This is additive — a gap counts as break if EITHER
    # threshold fires.
    if gaps:
        median_gap = float(np.median(gaps))
        mad_threshold = median_gap * 2.0
    else:
        mad_threshold = float("inf")

    # Third threshold, against a statistic the breaks cannot contaminate.
    # Both rules above are computed over ALL gaps, so on a page where system
    # breaks are a large share of them — a monograph laying out many short
    # music examples between paragraphs, say — the breaks drag the median and
    # the bipartition up past themselves and the page reads as one system.
    # (Observed on Nottebohm p.90: gaps of 65, 65, 65, 341, 394, 830, where a
    # median of 203 puts both thresholds above the 341 and 394 breaks.)
    #
    # Staves WITHIN a system are set at a consistent small distance, so the
    # low quartile of the gaps estimates that distance whatever fraction of
    # the page is system breaks — and a break is a clear multiple of it.
    if gaps:
        typical_within_system = float(np.percentile(gaps, 25))
        quartile_threshold = max(
            typical_within_system * SYSTEM_BREAK_GAP_FACTOR,
            mean_spacing * 2.0,   # floor: never split on a hair's difference
        )
    else:
        quartile_threshold = float("inf")

    current_system = 0
    staves_sorted[0].system_index = 0
    for i in range(1, len(staves_sorted)):
        prev = staves_sorted[i - 1]
        cur = staves_sorted[i]
        gap = cur.top_y - prev.bottom_y
        overlap = min(prev.x_end, cur.x_end) - max(prev.x_start, cur.x_start)
        min_extent = min(prev.x_end - prev.x_start, cur.x_end - cur.x_start)
        x_overlap_frac = overlap / max(1, min_extent)
        is_break = (
            gap >= threshold
            or gap >= mad_threshold
            or gap >= quartile_threshold
            or x_overlap_frac <= 0.5
        )
        # A continuous vertical stroke through the gap VETOES the break: a
        # barline or bracket crossing it means these staves are read together,
        # whatever the distance says. Veto only — this can merge systems the
        # gap rules over-split, never split one they accepted — so a page that
        # groups correctly today is unchanged. See _gap_is_bridged.
        if is_break and binary is not None and _gap_is_bridged(binary, prev, cur):
            is_break = False
        if is_break:
            current_system += 1
        cur.system_index = current_system
    return staves_sorted


def _line_ink_runs_per_space(binary: np.ndarray, staff: Staff) -> float:
    """How many separate ink runs lie along this staff's lines, per staff-space
    of line length (median over the five lines).

    This is the test for whether a detected "staff" is a staff at all. The
    row-projection detector finds staves by looking for rows with a lot of ink,
    and a row of justified body text has a lot of ink — enough to clear the
    line-length threshold — while five consecutive text baselines are evenly
    enough spaced to pass the 5-line grouping. So paragraphs become staves,
    complete with a clef and measures of their own.

    What actually separates them is not how MUCH ink is in the row but how it
    is arranged. A staff line is one continuous stroke: a handful of runs over
    its whole length even on a scan that has broken it into dashes. A text
    baseline is one run per letter. Measured over 310 staves on seven scores
    and 20 text blocks, the two do not come close to overlapping — music tops
    out at 1.39 runs per staff-space and text starts at 2.02, with the bulk two
    orders of magnitude apart (music median 0.017, text median 2.59).

    Note this deliberately does NOT test ink coverage, the obvious near-miss.
    Coverage does separate on clean pages but overlaps on real ones: heavy
    notation ink interrupts the line, so genuine staves in Beethoven 5 and
    La Mer fall to 0.62-0.70, right on top of body text at 0.62-0.72.
    """
    height = binary.shape[0]
    spacing = max(staff.line_spacing_px, 1.0)
    length_spaces = max((staff.x_end - staff.x_start + 1) / spacing, 1e-6)
    per_line: list[float] = []
    for y in staff.line_ys:
        band = binary[max(0, y - 1) : min(height, y + 2), staff.x_start : staff.x_end + 1]
        if band.size == 0:
            per_line.append(float("inf"))
            continue
        ink = (band == 0).any(axis=0).astype(np.int8)
        # A run starts at each 0→1 transition, plus one if the line opens in ink.
        runs = int(np.count_nonzero(np.diff(ink) == 1)) + (1 if ink[0] else 0)
        per_line.append(runs / length_spaces)
    return float(np.median(per_line)) if per_line else float("inf")


# ─── Public entry point ──────────────────────────────────────────────────────


def detect_staves(page: PageImage) -> PageWithStaves:
    """Detect every five-line staff on the page, group into systems."""
    profile = _ink_profile(page.binary)
    peaks = _candidate_staff_rows(profile, page.width)
    groups = _group_into_staves(peaks)

    staves: list[Staff] = []
    for idx, line_ys in enumerate(groups):
        x_start, x_end = _staff_x_extent(page.binary, line_ys)
        staves.append(Staff(
            page_index=page.page_index,
            staff_index=idx,
            line_ys=line_ys,
            x_start=x_start,
            x_end=x_end,
            system_index=0,
        ))

    # Drop the "staves" that are paragraphs of body text (see
    # _line_ink_runs_per_space). Done before system assignment so the surviving
    # staves are numbered contiguously, and before x-extent matters downstream.
    staves = [
        st for st in staves
        if _line_ink_runs_per_space(page.binary, st) <= MAX_LINE_INK_RUNS_PER_SPACE
    ]
    for idx, st in enumerate(staves):
        st.staff_index = idx

    staves = _assign_systems(staves, page.binary)
    return PageWithStaves(page=page, staves=staves)


# ─── CLI / smoke test ────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse
    from .preprocessing import render_page

    ap = argparse.ArgumentParser(description="Detect staves on a PDF page")
    ap.add_argument("pdf")
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--dpi", type=int, default=600)
    args = ap.parse_args()

    pi = render_page(args.pdf, args.page, dpi=args.dpi)
    print(f"page {args.page}: {pi.width}x{pi.height} @ {args.dpi} DPI")
    pws = detect_staves(pi)
    print(f"detected {len(pws.staves)} staves in {1 + max((s.system_index for s in pws.staves), default=-1)} systems")
    for s in pws.staves:
        print(f"  staff {s.staff_index} sys={s.system_index}: "
              f"y={s.top_y}..{s.bottom_y} (span {s.span_px}px, spacing {s.line_spacing_px:.1f}px) "
              f"x={s.x_start}..{s.x_end}")
