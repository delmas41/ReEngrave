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

    The staff line row in the binary image is a long horizontal black run.
    We scan the row for the first and last ink pixel that's part of a
    sufficiently long contiguous run.
    """
    h, w = binary.shape
    # Use the middle line as the reference for x-extent
    mid_y = line_ys[len(line_ys) // 2]
    # Look in a ±2 px neighborhood to be robust to sub-pixel position
    y0 = max(0, mid_y - 2)
    y1 = min(h, mid_y + 3)
    band = binary[y0:y1].min(axis=0)  # ink anywhere in band → ink pixel

    ink_mask = band == 0
    if not ink_mask.any():
        return 0, w - 1

    # Find longest contiguous run of ink (the staff line itself)
    runs: list[tuple[int, int]] = []
    in_run = False
    run_start = 0
    for x in range(w):
        if ink_mask[x] and not in_run:
            run_start = x
            in_run = True
        elif not ink_mask[x] and in_run:
            runs.append((run_start, x - 1))
            in_run = False
    if in_run:
        runs.append((run_start, w - 1))
    if not runs:
        return 0, w - 1
    longest = max(runs, key=lambda r: r[1] - r[0])
    return longest


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


def _assign_systems(staves: list[Staff]) -> list[Staff]:
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
            or x_overlap_frac <= 0.5
        )
        if is_break:
            current_system += 1
        cur.system_index = current_system
    return staves_sorted


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

    staves = _assign_systems(staves)
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
