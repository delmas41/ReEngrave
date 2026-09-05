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
>= `BRIDGE_INK_FRACTION` of the band running from the **top line of the upper
staff to the bottom line of the lower staff**.

Measuring the gap alone is not enough. On a tightly-packed page the gap band is
only a few line spacings tall, and a stem hanging below the upper staff plus a
stem rising into the lower one will fill it: Beethoven 9 p25 gap 11 — a real
system break — had 66 "crossing" columns scattered across the page, all of them
music ink. Extending the band through both staves discriminates, because a
barline or bracket is inked over that whole height while a stem is not (a
column crossing a staff away from a barline only meets its five lines, ~15%
coverage).

Measured counts are sharply trimodal:

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

import os
import statistics

import cv2
import numpy as np

from .types import Staff

# A column counts as crossing the gap only if it is near-solid ink over the
# whole band. Keeps slurs, hairpins, text and speckle from bridging.
BRIDGE_INK_FRACTION = 0.8

# Printed rules break. A bracket that is solid at 300 dpi resolves into a
# dotted line at 600 dpi, and then no column clears BRIDGE_INK_FRACTION and a
# system splits at every bracket-group gap — measured on Beethoven 5 p10, which
# grouped correctly as 2 systems at 300 dpi and wrongly as 4 at 600. So small
# vertical gaps are closed before coverage is measured, with a tolerance tied
# to staff line spacing so it scales with resolution rather than being a
# pixel constant. (`staff_header._walk_left` bridges gaps for the same reason.)
BRIDGE_GAP_TOLERANCE_SPACINGS = 0.6

# Within a system, a gap bridged by less than this fraction of the system's
# typical bridging is a bracket-group boundary (winds | brass | strings).
GROUP_BOUNDARY_RATIO = 0.5

# The scan window must reach PAST the staff lines on both sides: the system
# bracket is engraved just left of where the staff lines start, and the closing
# system barline just right of where they end. On Beethoven 5 p10 at 600 dpi the
# only columns crossing two bracket-group gaps sat at x=334-353 and x=2630+,
# against a median staff extent of 355..2629 — so a window clipped to the staff
# extent saw nothing and split the system. Margin scales with line spacing.
WINDOW_MARGIN_SPACINGS = 4.0

# Two staves that barely overlap horizontally are in different columns of a
# multi-column layout, never the same system — regardless of connectivity.
MIN_X_OVERLAP_FRAC = 0.5

# NOTE: an earlier revision also required a break to be a larger-than-median
# gap, as a guard against a scan defect splitting a system. Measurement killed
# it: on Beethoven 9 p25 the true break between two 12-staff systems has a
# 68 px gap while intra-system gaps reach 99 px, so the guard suppressed a real
# break. Gap size is exactly the assumption this module exists to reject — the
# connectivity signal stands alone.

# ── Left-edge system-start split (`OMR_LEFT_EDGE_SPLIT`) ───────────────────────
# The window above scans the whole staff width, so music ink out in the staff
# body — a stem, an "a 2." marking, a measure number, a brace curve — can be
# counted as a crossing column and fake a connection across a real system
# boundary, MERGING two stacked systems into one. Measured over-merges: Beethoven
# 9 p60 had 324 crossing columns at the true break but ZERO at the shared left
# edge; Beethoven 5 p40 the same (3/11 body ink, 0 at the edge); Eroica p36 read
# one 22-staff system for a true [11, 11].
#
# The systemic barline is the one rule engraved through a whole system and absent
# between systems, so a SECOND, narrow band anchored at the shared left edge
# recovers the boundary the wide window fumbled: a gap whose left-edge column is
# empty is a system start. This only ever ADDS a break (union with the rule
# above); it can never merge, so it cannot reintroduce an over-split the wide
# rule already avoids.
#
# `RIGHT` (how far right of x_start the band reaches) is the load-bearing knob:
# the leftmost barline sits at a different offset per edition — ~0 spacings on
# Beethoven, +1.4-3 on La Mer, because `x_start` is measured after the clef
# margin — so the band must reach >= 3 spacings right to admit every edition's
# barline. Measured flat for RIGHT >= 3; 4.5 sits well inside that plateau.
# Validated in benchmarks/omr-system-grouping-2026-09/fix/PHASE1_RESULTS.md:
# fixes 2/3 known over-merges + Eroica, 0/37 control regressions, stable across
# 45/45 RIGHT>=3 settings and 300/600 dpi.
LEFT_BAND_LEFT_SPACINGS = 2.0
LEFT_BAND_RIGHT_SPACINGS = 4.5
LEFT_BAND_MIN_CROSS = 1
# Trust the empty-left signal only on a page that actually uses a continuous left
# barline: require this fraction of the wide rule's within-system gaps to BE
# left-edge crossed before adding any left-edge break. Guards a degraded
# multi-system scan (broken interior barlines) from being shattered. Inactive on
# the validation corpus; kept as insurance.
LEFT_BAND_GATE_FRAC = 0.7


# On by default: measured across 964 library pages it corrected 27 over-merged
# symphony pages (e.g. Bach Brandenburg, Schubert, Schumann, Wagner, Tchaikovsky
# read as one system where there were two) against a single mild residual
# over-split (Mozart K22 p4, a movement-start left-edge defect — the B9-p25
# family, Phase 3), with zero size-1 systems created. Set OMR_LEFT_EDGE_SPLIT=0
# to disable.
def _left_edge_split_enabled() -> bool:
    return os.environ.get("OMR_LEFT_EDGE_SPLIT", "1").strip().lower() not in (
        "0", "", "false", "no", "off",
    )


# ── Cue B: pair-local left-edge merge (`OMR_CHOIR_GROUPING`, default OFF) ─────
# The wide window and cue A's narrow band are both anchored on the MEDIAN
# x_start across the page's staves — robust to a single broken staff, and
# poisoned outright on a page whose systems are indented DIFFERENTLY: on the
# Peters Brandenburg 3 (p.59) system 1 is indented for full instrument names
# (x_start 792–836) while system 2 runs full width (178–200), the median (450)
# lands in the empty land between the modes, and the window [359, 4554] cuts
# system 2's bracket + systemic barline (x 178–227) out of the scan. That page
# is also choir-barred — interior barlines are drawn per instrument choir and
# cross no choir gap — so with the left-edge complex unseen its choir gaps read
# bridging = 0 and one 12-staff system shatters into 3/3/3/1/2 fragments
# (whose stems then out-vote the barlines: 122 measure-cells against 10).
# Measured: benchmarks/omr-choir-grouping-2026-09/FINDINGS.md.
#
# Cue B is the mirror of cue A, additive in the opposite direction: where cue A
# reads the ABSENCE of the left-edge complex (in a page-anchored band) to ADD a
# break, cue B reads its PRESENCE — in a band anchored at the PAIR's own shared
# left edge, immune to the page-median poisoning — to CANCEL a break the wide
# rule made for lack of evidence. It is merge-only: it never splits, never
# touches a multi-column break (x-overlap ≤ 0.5), and a band that finds nothing
# changes nothing, so a page where it never fires is byte-identical. A broken
# pair x_start can only mis-anchor the band AWAY from the complex, declining a
# rescue rather than inventing one (measured on the Bach page's gap 2, whose
# upper staff reports x_start 700 against a true ~792: the band reads 0).
#
# The band geometry is cue A's — the same physical objects (bracket, systemic
# barline) at the same measured offset from x_start (flat for RIGHT ≥ 3
# spacings, benchmarks/omr-system-grouping-2026-09/fix/PHASE1_RESULTS.md) —
# so no new tuned constants. The acceptance threshold mirrors cue A's
# LEFT_BAND_MIN_CROSS; on the Bach page the gaps this cue examines read
# either 0 (the true system break) or 6–22 (the four wrongly-broken choir
# gaps — 6 is the Cembalo gap, whose only witness is the 6-px systemic
# barline), so any floor in 1..6 reads that page identically. The library
# probe in the benchmark dir prices the floor over the wider population.
#
# Cue B runs before cue A, and a cue-B merge is exempt from cue A's re-split:
# the two cues act on disjoint gap sets (cue A splits gaps kept interior by
# body ink, bridging > 0; cue B merges gaps broken for lack of evidence,
# bridging == 0), so the exemption cannot reach cue A's validated fix set —
# see the comment at the exemption site in `assign_systems`.
CHOIR_MERGE_MIN_CROSS = 1


def _choir_grouping_enabled() -> bool:
    """ON by default since 2026-09-05 (Sean's call, coupled with Bach's pool
    re-admission). All five guards green when priced: byte-identical on the
    10 pooled scan rows, the 11-work engraved benchmark and the boulanger
    canary; 969-page library probe hand-adjudicated 10/10 changed pages
    toward truth, 0 false merges. Set 0/false/no/off to disable.
    benchmarks/omr-choir-grouping-2026-09/FINDINGS.md."""
    return os.environ.get("OMR_CHOIR_GROUPING", "").strip().lower() not in (
        "0", "false", "no", "off",
    )


def pair_left_edge_count(
    binary: np.ndarray,
    upper: Staff,
    lower: Staff,
    *,
    ink_fraction: float = BRIDGE_INK_FRACTION,
) -> int:
    """Crossing-column count for ONE gap, in a narrow band anchored at the
    PAIR's own shared left edge — `min(upper.x_start, lower.x_start)` — rather
    than the page-median anchor `left_edge_barline_counts` uses.

    Same band geometry (`LEFT_BAND_*_SPACINGS`), closing and coverage test as
    the page-anchored scan; `-1` for a degenerate gap. This is cue B's reading
    of the same physical objects cue A reads: the system bracket and the
    systemic barline, which live at a measured offset from the staff start.
    """
    height, width = binary.shape
    spacing = max(upper.line_spacing_px, lower.line_spacing_px) or 1.0
    anchor = min(upper.x_start, lower.x_start)
    x0 = max(0, int(anchor - LEFT_BAND_LEFT_SPACINGS * spacing))
    x1 = min(width, int(anchor + LEFT_BAND_RIGHT_SPACINGS * spacing))
    top = max(0, upper.bottom_y + 2)
    bot = min(height, lower.top_y - 2)
    if bot <= top or x1 <= x0:
        return -1
    band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
    k = max(3, int(round(spacing * BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
    closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
    return int((closed.mean(axis=0) > ink_fraction).sum())


def _robust_x_window(staves: list[Staff]) -> tuple[int, int]:
    """Scan window: the median staff extent — robust to a broken `x_start` —
    widened by `WINDOW_MARGIN_SPACINGS` so it takes in the bracket on the left
    and the closing system barline on the right."""
    spacing = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    margin = int(round(spacing * WINDOW_MARGIN_SPACINGS))
    x0 = int(statistics.median([s.x_start for s in staves])) - margin
    x1 = int(statistics.median([s.x_end for s in staves])) + margin
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
    ink spans at least `ink_fraction` of the gap between them, after closing
    vertical breaks shorter than `BRIDGE_GAP_TOLERANCE_SPACINGS` of a staff
    line spacing.

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
        top = max(0, upper.bottom_y + 2)
        bot = min(height, lower.top_y - 2)
        if bot <= top or x1 <= x0:
            counts.append(-1)
            continue
        band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
        spacing = max(upper.line_spacing_px, lower.line_spacing_px)
        k = max(3, int(round(spacing * BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
        closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
        counts.append(int((closed.mean(axis=0) > ink_fraction).sum()))
    return counts


def left_edge_barline_counts(
    binary: np.ndarray,
    staves: list[Staff],
    *,
    ink_fraction: float = BRIDGE_INK_FRACTION,
) -> list[int]:
    """Per adjacent staff pair, the number of near-solid crossing columns in a
    NARROW band at the page's shared left edge (the systemic barline), rather
    than the whole staff width `gap_bridging_counts` scans.

    High at a within-system gap (the systemic barline runs the whole system
    height); ~0 at a system boundary, where the wide window is fooled by music
    ink out in the staff body. Same closing and coverage test as
    `gap_bridging_counts`; `-1` for a degenerate pair. `staves` must be sorted
    by `top_y`.
    """
    if len(staves) < 2:
        return []
    height, width = binary.shape
    spacing_pg = statistics.median([s.line_spacing_px for s in staves]) or 1.0
    x_start = int(statistics.median([s.x_start for s in staves]))
    x0 = max(0, int(x_start - LEFT_BAND_LEFT_SPACINGS * spacing_pg))
    x1 = min(width, int(x_start + LEFT_BAND_RIGHT_SPACINGS * spacing_pg))

    counts: list[int] = []
    for upper, lower in zip(staves, staves[1:]):
        top = max(0, upper.bottom_y + 2)
        bot = min(height, lower.top_y - 2)
        if bot <= top or x1 <= x0:
            counts.append(-1)
            continue
        band = (binary[top:bot, x0:x1] < 128).astype(np.uint8)
        spacing = max(upper.line_spacing_px, lower.line_spacing_px)
        k = max(3, int(round(spacing * BRIDGE_GAP_TOLERANCE_SPACINGS)) * 2 + 1)
        closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, np.ones((k, 1), np.uint8))
        counts.append(int((closed.mean(axis=0) > ink_fraction).sum()))
    return counts


def _suppress_orphaning_breaks(
    existing_break: list[bool], left_break: list[bool]
) -> list[bool]:
    """Clear any cue-A break that would isolate a single staff.

    A lone-staff "system" is the over-split signature and essentially never a
    real orchestral system (the connectivity rule proper produces zero of them),
    so cue A must never create one — measured on small-system pages (keyboard
    grand staves, chamber groups, a partial last system) where a faint internal
    connector makes the narrow left band read empty. Only cue-A (`left_break`)
    breaks are cleared; existing-rule breaks are always kept. Clearing only ever
    merges, so the pass converges.
    """
    n_gaps = len(existing_break)
    lb = list(left_break)
    while True:
        combined = [existing_break[i] or lb[i] for i in range(n_gaps)]
        cleared = False
        for j in range(n_gaps + 1):  # staff index; a size-1 system is one staff
            before = combined[j - 1] if j > 0 else True
            after = combined[j] if j < n_gaps else True
            if before and after:  # staff j stands alone
                if j > 0 and lb[j - 1] and not existing_break[j - 1]:
                    lb[j - 1] = False
                    cleared = True
                    break
                if j < n_gaps and lb[j] and not existing_break[j]:
                    lb[j] = False
                    cleared = True
                    break
        if not cleared:
            return lb


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
    left_edge_split: bool | None = None,
    choir_grouping: bool | None = None,
) -> tuple[list[Staff], bool]:
    """Set `system_index` and `group_index` from vertical connectivity.

    Returns `(staves_sorted_by_y, used_bridging)`. `used_bridging` is False when
    the connectivity evidence was unusable and the caller should fall back to
    the gap heuristic — which happens when no gap anywhere on the page is
    bridged (a page whose barlines and bracket are too faint to see, where
    trusting the signal would make every staff its own system).

    When `left_edge_split` is true (default read from `OMR_LEFT_EDGE_SPLIT`, off),
    a second narrow left-edge barline scan ADDS a system break at any gap whose
    shared-left-edge column is empty even though the wide window found body ink —
    recovering two stacked systems merged by that body ink. It never merges, and
    is gated on the page using a continuous left barline. See the `LEFT_BAND_*`
    constants and `left_edge_barline_counts`.

    When `choir_grouping` is true (default read from `OMR_CHOIR_GROUPING`, off),
    cue B re-examines each break the wide rule made for lack of evidence in a
    narrow band anchored at the PAIR's own left edge, and CANCELS the break
    where the system bracket / systemic barline crosses there — recovering a
    system whose left-edge complex the page-median window could not see
    (differently-indented systems; choir-barred pages shatter without this).
    It never splits, and a gap it merges is exempt from cue A's re-split
    (positive pair-local ink outranks absence at the page-median anchor —
    see the comment at the exemption site). See the cue-B comment block and
    `pair_left_edge_count`.
    """
    if left_edge_split is None:
        left_edge_split = _left_edge_split_enabled()
    if choir_grouping is None:
        choir_grouping = _choir_grouping_enabled()
    staves = sorted(staves, key=lambda s: s.top_y)
    if len(staves) < 2:
        for s in staves:
            s.system_index = 0
            s.group_index = 0
        return staves, True

    bridging = gap_bridging_counts(binary, staves)
    if fallback and not any(n > 0 for n in bridging):
        return staves, False

    # The break the connectivity rule decides for each gap: a multi-column
    # layout, or a gap the wide window found nothing crossing.
    existing_break = [
        (_x_overlap_frac(upper, lower) <= MIN_X_OVERLAP_FRAC) or (bridging[i] == 0)
        for i, (upper, lower) in enumerate(zip(staves, staves[1:]))
    ]

    # Cue B (opt-in, merge-only): a no-evidence break whose pair-anchored left
    # band IS crossed was broken by the window, not by the page — cancel it.
    # Multi-column breaks (x-overlap) are never candidates: two side-by-side
    # columns are different systems whatever their left edges carry.
    #
    # A cue-B merge is EXEMPT from cue A's re-split (`cue_b_merged` below).
    # The two cues act on disjoint gap sets by construction — cue A splits
    # gaps the wide rule kept interior (bridging > 0, body ink faking a
    # connection), cue B merges gaps the wide rule broke (bridging == 0) — so
    # the exemption cannot touch any gap of cue A's validated fix set. Where
    # they would meet is only a gap cue B just merged, and there the evidence
    # is asymmetric: cue B holds POSITIVE ink (a near-solid column through the
    # whole gap at the pair's own edge) while cue A holds absence at the
    # page-median anchor — the anchor this whole module documents as poisoned
    # on bimodally-indented pages. Measured on Mozart 40 p32 (Breitkopf 1880):
    # x_starts 206–221 for ten staves and 530–544 for eleven, the median on
    # the SECOND mode, cue A's band reading mid-staff ink of system 1 as "the
    # left edge" — it re-split a gap whose true systemic barline cue B had
    # just found, and the exemption is what lets the page heal to [10, 11].
    cue_b_merged: set[int] = set()
    if choir_grouping:
        for i, (upper, lower) in enumerate(zip(staves, staves[1:])):
            if not existing_break[i] or bridging[i] != 0:
                continue
            if _x_overlap_frac(upper, lower) <= MIN_X_OVERLAP_FRAC:
                continue
            if pair_left_edge_count(binary, upper, lower) >= CHOIR_MERGE_MIN_CROSS:
                existing_break[i] = False
                cue_b_merged.add(i)

    # Cue A (opt-in): a gap whose narrow left-edge column is empty is a system
    # start the wide window missed because body ink bridged it. Only trusted on a
    # page that otherwise keeps a continuous left barline (the gate), so a
    # degraded multi-system scan is left to the wide rule rather than shattered.
    left_break = [False] * len(existing_break)
    if left_edge_split and existing_break:
        left_counts = left_edge_barline_counts(binary, staves)
        interior = [
            i for i in range(len(existing_break))
            if not existing_break[i] and 0 <= left_counts[i]
        ]
        if interior:
            crossed = sum(1 for i in interior if left_counts[i] >= LEFT_BAND_MIN_CROSS)
            if crossed / len(interior) >= LEFT_BAND_GATE_FRAC:
                for i in interior:
                    if left_counts[i] < LEFT_BAND_MIN_CROSS and i not in cue_b_merged:
                        left_break[i] = True
                if any(left_break):
                    left_break = _suppress_orphaning_breaks(existing_break, left_break)

    system = 0
    staves[0].system_index = 0
    for i, lower in enumerate(staves[1:]):
        if existing_break[i] or left_break[i]:
            system += 1
        lower.system_index = system

    _assign_groups(staves, bridging)
    return staves, True
