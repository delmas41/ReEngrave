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
"""

from __future__ import annotations

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
PAD_ABOVE_STAFF_LINES = 4
PAD_BELOW_STAFF_LINES = 4

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


# ─── Barline detection ───────────────────────────────────────────────────────


def _detect_barlines_per_staff(bin_img: np.ndarray, staff: Staff) -> list[int]:
    """Find columns where this single staff has a vertical barline using
    morphological vertical opening + connected-component shape filtering.

    A barline is a vertical ink stripe with these geometric properties:
      - height ≥ 80% of staff span
      - width < ~0.7 × line spacing
      - aspect ratio (h/w) >> 1

    NOTE: A notehead-attachment rejection step was tried (commit history
    in this file) but it was too easily fooled by ink near barlines that
    isn't actually attached to them. Over-detection on very dense
    orchestral pages is handled at the system level via gap-bipartition
    outlier rejection (see _drop_close_outliers).
    """
    h, w = bin_img.shape
    y0, y1 = staff.top_y, staff.bottom_y + 1
    if y1 <= y0:
        return []
    band = bin_img[y0:y1, staff.x_start:staff.x_end + 1]
    if band.size == 0:
        return []

    staff_span = y1 - y0
    spacing = max(1.0, staff.line_spacing_px)
    min_height = int(staff_span * BARLINE_MIN_HEIGHT_FRAC)
    max_width = max(2, int(spacing * BARLINE_MAX_WIDTH_LINESPACINGS))

    ink = cv2.bitwise_not(band)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, min_height))
    vertical = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(vertical, connectivity=8)
    barline_xs: list[int] = []
    for i in range(1, n_labels):
        x_l, y_l, w_l, h_l, area = stats[i]
        if h_l < min_height:
            continue
        if w_l > max_width:
            continue           # too wide — accidental or chord
        if h_l / max(w_l, 1) < 8.0:
            continue           # not skinny enough
        x_center = staff.x_start + x_l + w_l // 2
        barline_xs.append(int(x_center))
    barline_xs.sort()
    deduped: list[int] = []
    for x in barline_xs:
        if not deduped or x - deduped[-1] >= BARLINE_MIN_DISTANCE_PX:
            deduped.append(x)
    return deduped


def detect_barlines(pws: PageWithStaves) -> PageWithStaves:
    """Detect barlines via per-staff scanning + system-level voting.

    A column counts as a system barline if it shows up as a barline on
    AT LEAST half of the staves in the system (with a small x-tolerance
    to handle slight skew). Per-staff detection avoids the orchestral
    failure mode where whitespace between sections dilutes the ink
    fraction over the full system height.
    """
    bin_img = pws.page.binary

    # Group staves by system
    systems: dict[int, list[Staff]] = {}
    for s in pws.staves:
        systems.setdefault(s.system_index, []).append(s)

    pws.barlines = []
    x_tolerance = 12  # px: barlines on different staves may not align exactly

    for sys_idx, staves in systems.items():
        # Gather candidate x positions across all staves
        all_xs: list[int] = []
        for staff in staves:
            all_xs.extend(_detect_barlines_per_staff(bin_img, staff))
        if not all_xs:
            continue
        all_xs.sort()

        # Cluster close x's together (within x_tolerance) and count how many
        # staves in the system voted for each cluster.
        clusters: list[list[int]] = []
        for x in all_xs:
            if clusters and x - clusters[-1][-1] <= x_tolerance:
                clusters[-1].append(x)
            else:
                clusters.append([x])

        n_staves = len(staves)
        # Vote threshold: real barlines are drawn across every staff of the
        # system. False positives (stems aligned by chance) appear on only a
        # few staves. Require ≥80% of staves to agree, with floor of 2 for
        # tiny systems and a "allow 1 staff to miss" rule for moderate ones.
        if n_staves <= 2:
            min_votes = n_staves                     # both must agree
        elif n_staves <= 4:
            min_votes = n_staves - 1                 # tolerate 1 miss
        else:
            min_votes = max(n_staves - 1, int(round(0.80 * n_staves)))

        y_top = min(s.top_y for s in staves)
        y_bot = max(s.bottom_y for s in staves)
        # First pass: collect accepted x's (those meeting the vote threshold).
        accepted: list[int] = []
        for cluster in clusters:
            if len(cluster) >= min_votes:
                accepted.append(int(round(sum(cluster) / len(cluster))))
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

    The first measure starts at the system's leftmost staff content (after
    any clef/key signature — we use the staff's x_start) and runs to the
    first barline. Subsequent measures run between barlines. The last
    measure runs from the final barline to the rightmost staff edge.
    """
    if not staves:
        return []
    x_lo = min(s.x_start for s in staves)
    x_hi = max(s.x_end for s in staves)
    xs = sorted({bl.x for bl in barlines})
    boundaries: list[tuple[int, int]] = []
    # Drop barlines that coincide with the system edges (some scores have a
    # leftmost system barline as part of the bracket).
    xs = [x for x in xs if x > x_lo + 10 and x < x_hi - 10]
    prev = x_lo
    for x in xs:
        boundaries.append((prev, x))
        prev = x
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
    sys_staves: dict[int, list[Staff]] = {}
    for s in pws.staves:
        sys_staves.setdefault(s.system_index, []).append(s)
    sys_barlines: dict[int, list[Barline]] = {}
    for bl in pws.barlines:
        sys_barlines.setdefault(bl.system_index, []).append(bl)

    rgb = pws.page.rgb
    binary = pws.page.binary

    for sys_idx, staves in sys_staves.items():
        bls = sys_barlines.get(sys_idx, [])
        xb = _measure_x_boundaries(bls, staves)
        for staff in staves:
            spacing = max(1.0, staff.line_spacing_px)
            pad_above = int(PAD_ABOVE_STAFF_LINES * spacing)
            pad_below = int(PAD_BELOW_STAFF_LINES * spacing)
            y0 = max(0, staff.top_y - pad_above)
            y1 = min(rgb.shape[0], staff.bottom_y + pad_below)
            for m_idx, (x0, x1) in enumerate(xb):
                x0 = max(0, x0)
                x1 = min(rgb.shape[1], x1)
                if x1 - x0 < 10:
                    continue  # too narrow, skip
                cell_rgb = rgb[y0:y1, x0:x1].copy()
                # Staff line ys in the cell's local coordinate frame
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

                cells.append(MeasureCell(
                    page_index=pws.page.page_index,
                    system_index=sys_idx,
                    staff_index=staff.staff_index,
                    measure_index=m_idx,
                    image=up_rgb,
                    image_no_staff=None,  # filled in by staff_line_removal
                    bbox_page_px=(x0, y0, x1, y1),
                    staff_line_ys_canonical=up_ys,
                    upscale_factor=scale,
                ))
                # Stash binary on the cell as a side-channel attribute for
                # the staff-line-removal step. (Not part of MeasureCell's
                # formal schema — kept dynamic for now.)
                cells[-1].__dict__["binary"] = up_bin
    return cells


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
