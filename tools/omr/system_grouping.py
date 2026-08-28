"""Group staves into systems by vertical CONNECTIVITY rather than gap size.

## Why the gap heuristic fails on orchestral scores

`staff_detector._assign_systems` decides system boundaries from the *size* of the
vertical gap between adjacent staves: it bipartitions the gaps into "small"
(intra-system) and "large" (inter-system) clusters, plus a MAD rule for
"mid-magnitude" breaks. Its own comment names what that MAD rule was aimed at —
"a clearly-bigger-than-normal gap between bracketed sub-systems (e.g. winds vs
brass vs strings)".

But those bracketed sub-groups are **inside one system**, not separate systems.
On a conductor's score the gaps genuinely are bimodal — winds sit closer to each
other than the wind block sits to the brass block — so the bipartition finds a
clean split and reports it as a system break. Measured on Beethoven 9
(imslp-516488, 300 dpi), 12 pages sampled every 5 from p20:

    gap-based : 52 "systems", 12 distinct sizes, most common size = 1 staff
                (19 occurrences, 37% of all systems detected)
    bridging  : 18 systems, sizes clustered 10-13 (15 of 18), no 1-staff systems

Single-staff "systems" at 37% is the tell. Page 40 alone came out as
`[3, 1, 2, 1, 5]` — one 12-staff system reported as five.

## The signal this module uses instead

**A system break is a gap that no vertical ink crosses.** Barlines are engraved
through the whole system and the system bracket spans it end to end, so every
gap *inside* a system is crossed by ink; the gap *between* two systems is
crossed by nothing. `measure_extractor._intersystem_connectivity` already relies
on the same fact to separate real barlines from stem columns — this module
applies it one level earlier, to decide the grouping in the first place.

Per adjacent staff pair we count the columns whose ink covers
>= `BRIDGE_INK_FRACTION` of the gap band. Measured counts are sharply trimodal:

    0            -> system break
    ~4-18        -> a bracket-GROUP boundary inside a system: only the bracket
                    and the barlines that are drawn through it cross here
    ~35-95       -> inside a bracket group

That middle tier is a bonus: it recovers the instrument-family grouping
(winds | brass | strings) as `Staff.group_index`. On Beethoven 9 p5 the
bridging counts were `[43,45,45, 8, 50,49,46, 10, 49,46,50,50]` — one system of
13 staves split into groups of 4 | 4 | 5, which is exactly what the gap
heuristic had been reporting as three separate *systems*.

## Robustness note — do not use `Staff.x_start` for the scan window

`Staff.x_start` is the longest contiguous ink run on the middle staff line, so on
a degraded scan it lands wherever the line happens to be unbroken. Beethoven 9
p60 staff 3 reports `x_start=885, x_end=1826` against ~275/~2485 for its
neighbours. Intersecting the two staves' own extents therefore produced a scan
window that missed the bracket entirely and reported a false system break. The
window here is the **median** x_start/x_end across the page's staves, which
absorbs those outliers. (Same root cause as the header-window problem documented
in `staff_header.py` on the key-signature branch.)
"""

from __future__ import annotations

import statistics

import numpy as np

from .types import Staff

# A column counts as crossing the gap only if it is near-solid ink over the
# whole band. Keeps slurs, hairpins, text and speckle from bridging.
BRIDGE_INK_FRACTION = 0.8

# Within a system, a gap bridged by less than this fraction of the system's
# typical bridging is a bracket-group boundary (winds | brass | strings).
GROUP_BOUNDARY_RATIO = 0.5

# Two staves that barely overlap horizontally are in different columns of a
# multi-column layout, never the same system — regardless of connectivity.
MIN_X_OVERLAP_FRAC = 0.5

# NOTE: an earlier revision also required a break to be a larger-than-median
# gap, as a guard against a scan defect splitting a system. Measurement killed
# it: on Beethoven 9 p25 the true break between two 12-staff systems has a
# 68 px gap while intra-system gaps reach 99 px, so the guard suppressed a real
# break. Gap size is exactly the assumption this module exists to reject — the
# connectivity signal stands alone.


def _robust_x_window(staves: list[Staff]) -> tuple[int, int]:
    """Median staff extent across the page — robust to broken `x_start`."""
    x0 = int(statistics.median([s.x_start for s in staves]))
    x1 = int(statistics.median([s.x_end for s in staves]))
    return x0, x1


def _x_overlap_frac(a: Staff, b: Staff) -> float:
    overlap = min(a.x_end, b.x_end) - max(a.x_start, b.x_start)
    min_extent = min(a.x_end - a.x_start, b.x_end - b.x_start)
    return overlap / max(1, min_extent)


def gap_bridging_counts(
    binary: np.ndarray,
    staves: list[Staff],
    *,
    ink_fraction: float = BRIDGE_INK_FRACTION,
) -> list[int]:
    """For each adjacent staff pair (top→bottom), the number of columns whose
    ink spans at least `ink_fraction` of the gap between them.

    `staves` must be sorted by `top_y`. Returns `len(staves) - 1` counts; a
    pair whose gap or scan window is degenerate yields `-1` ("no evidence").
    Binarized convention: 0 = ink, 255 = paper.
    """
    if len(staves) < 2:
        return []
    height, width = binary.shape
    x0, x1 = _robust_x_window(staves)
    x0 = max(0, x0)
    x1 = min(width, x1)

    counts: list[int] = []
    for upper, lower in zip(staves, staves[1:]):
        top = upper.bottom_y + 2
        bot = lower.top_y - 2
        if bot <= top or x1 <= x0 or top < 0 or bot > height:
            counts.append(-1)
            continue
        band = binary[top:bot, x0:x1] < 128
        counts.append(int((band.mean(axis=0) > ink_fraction).sum()))
    return counts


def _assign_groups(staves: list[Staff], bridging: list[int]) -> None:
    """Within each system, split at gaps bridged far less than the system's
    typical gap — the bracket-group boundaries. Sets `Staff.group_index`
    (0-based within the system)."""
    by_system: dict[int, list[int]] = {}
    for i, s in enumerate(staves):
        by_system.setdefault(s.system_index, []).append(i)

    for members in by_system.values():
        if len(members) < 3:
            for s_i in members:
                staves[s_i].group_index = 0
            continue
        inner = [bridging[i] for i in members[:-1] if bridging[i] >= 0]
        if not inner:
            for s_i in members:
                staves[s_i].group_index = 0
            continue
        threshold = statistics.median(inner) * GROUP_BOUNDARY_RATIO
        group = 0
        staves[members[0]].group_index = 0
        for prev_pos, s_i in enumerate(members[1:]):
            gap_i = members[prev_pos]
            n = bridging[gap_i]
            if 0 <= n < threshold:
                group += 1
            staves[s_i].group_index = group


def assign_systems(
    binary: np.ndarray,
    staves: list[Staff],
    *,
    fallback: bool = True,
) -> tuple[list[Staff], bool]:
    """Set `system_index` and `group_index` from vertical connectivity.

    Returns `(staves_sorted_by_y, used_bridging)`. `used_bridging` is False when
    the connectivity evidence was unusable and the caller should fall back to
    the gap heuristic — which happens when no gap anywhere on the page is
    bridged (a page whose barlines and bracket are too faint to see, where
    trusting the signal would make every staff its own system).
    """
    staves = sorted(staves, key=lambda s: s.top_y)
    if len(staves) < 2:
        for s in staves:
            s.system_index = 0
            s.group_index = 0
        return staves, True

    bridging = gap_bridging_counts(binary, staves)
    if fallback and not any(n > 0 for n in bridging):
        return staves, False

    system = 0
    staves[0].system_index = 0
    for i, (upper, lower) in enumerate(zip(staves, staves[1:])):
        # Multi-column layouts break regardless of what crosses the gap.
        if _x_overlap_frac(upper, lower) <= MIN_X_OVERLAP_FRAC:
            system += 1
        elif bridging[i] == 0:
            system += 1
        lower.system_index = system

    _assign_groups(staves, bridging)
    return staves, True
