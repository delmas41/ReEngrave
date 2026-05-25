"""Classical-CV detection of line-like elements (stems, beams).

Phase 4f. YOLO bounding boxes are structurally poor at thin lines (extreme
aspect ratios, mostly-empty boxes). The Phase 3.3 model misses **stems**
entirely (0 detections even at conf=0.05) and emits **beam** bboxes with
endpoints that systematically fall short of the actual beam strokes.

This module replaces both with classical CV (morphological filtering +
connected components), which:

  * is fast (a few ms per cell on CPU)
  * is deterministic (no model weights, no GPU)
  * naturally handles thin lines (no bbox-aspect-ratio bias)
  * picks up the actual ink, not a learned approximation of it

The output integrates with `rhythm.py` and `voicing.py` by providing a
`LineDetection` dataclass that exposes the same `x_canonical`,
`y_canonical`, `width_canonical`, `height_canonical` attributes the YOLO
`SymbolDetection` exposes — so downstream code can treat them
interchangeably.

Public API:

    detect_stems(cell)  -> list[LineDetection]
    detect_beams(cell)  -> list[LineDetection]

Both operate on the cell's canonical-coord image. The staff-removed
variant (`cell.image_no_staff`) is preferred when available — it makes
the projections much cleaner since the long horizontal staff-line ink
doesn't confuse the vertical-projection step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Public data type
# ---------------------------------------------------------------------------


@dataclass
class LineDetection:
    """Quack-compatible with template_matcher.SymbolDetection — exposes the
    fields rhythm.py + voicing.py read, so a list of these can be mixed
    with YOLO SymbolDetections without special-casing.
    """
    smufl_name: str          # 'stem' / 'beam' (used by rhythm.py category checks)
    category: str            # 'stem' / 'structural'
    x_canonical: int
    y_canonical: int
    width_canonical: int
    height_canonical: int
    confidence: float = 1.0  # classical CV is deterministic; conf is arbitrary
    pitch: str | None = None

    @property
    def x_center(self) -> int:
        return self.x_canonical + self.width_canonical // 2

    @property
    def y_center(self) -> int:
        return self.y_canonical + self.height_canonical // 2


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def _binary_ink(image: np.ndarray, threshold: int = 180) -> np.ndarray:
    """Return a uint8 mask where ink=255, paper=0. Matches Phase 1's
    convention (255=foreground in `connectedComponentsWithStats`).

    Note: opencv ops like morphology expect "ink" to be the bright value.
    Phase 1's PageImage.binary stores 0=ink/255=paper (Sauvola), so we
    re-threshold here from the source image to get the right polarity.
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return mask


def _staff_line_spacing(cell) -> float:
    """Average staff-line spacing in canonical coords. Fallback default is
    24 px (the canonical reference spacing used in pitch_resolver.py).
    """
    lines = getattr(cell, "staff_line_ys_canonical", None) or []
    if len(lines) >= 2:
        ys = sorted(lines)
        gaps = [ys[i + 1] - ys[i] for i in range(len(ys) - 1)]
        return sum(gaps) / len(gaps)
    return 24.0


# ---------------------------------------------------------------------------
# Stem detection
# ---------------------------------------------------------------------------


def detect_stems(
    cell,
    *,
    min_height_lines: float = 2.0,
    max_height_lines: float = 6.0,
    max_width_lines: float = 0.6,
) -> list[LineDetection]:
    """Find stem-like vertical ink runs in `cell`.

    Algorithm:
      1. Pick the cleanest source image — staff-removed if available.
      2. Threshold → binary ink mask.
      3. Vertical morphological opening with a (line_spacing × 1)
         structuring element. This isolates ink runs that are tall and
         narrow — everything else (noteheads, beams, accidentals) gets
         erased.
      4. Connected components on the result. Each component is a candidate
         stem.
      5. Filter:
           - height between min/max_height_lines × line_spacing
             (rejects too-short noise + too-tall full-staff barlines)
           - width ≤ max_width_lines × line_spacing
           - not at the cell edges (rejects measure-boundary barlines)
           - aspect ratio ≥ 3:1 vertical (rejects square noise blobs)

    Returns LineDetection objects in canonical-cell coordinates.
    """
    if cell is None:
        return []
    src = (
        cell.image_no_staff
        if getattr(cell, "image_no_staff", None) is not None
        else cell.image
    )
    if src is None or src.size == 0:
        return []

    line_spacing = _staff_line_spacing(cell)
    if line_spacing <= 1.0:
        return []

    cell_w = cell.width
    edge_margin = max(int(round(line_spacing * 0.8)), 12)

    ink = _binary_ink(src)
    # Vertical structuring element: width 1, height ~= 1 line spacing.
    kernel_h = max(3, int(round(line_spacing * 1.0)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel_h))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    # Connected components
    num, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out: list[LineDetection] = []
    min_h = int(round(line_spacing * min_height_lines))
    max_h = int(round(line_spacing * max_height_lines))
    max_w = max(3, int(round(line_spacing * max_width_lines)))
    for i in range(1, num):  # skip background (label 0)
        x, y, w, h, area = stats[i]
        # Range filters
        if h < min_h or h > max_h:
            continue
        if w > max_w:
            continue
        # Edge filter — barlines live at the cell boundaries.
        if x < edge_margin or x + w > cell_w - edge_margin:
            continue
        if area < max(4, line_spacing * 0.5):
            continue
        if h / max(1, w) < 3.0:
            continue
        out.append(LineDetection(
            smufl_name="stem",
            category="stem",
            x_canonical=int(x),
            y_canonical=int(y),
            width_canonical=int(w),
            height_canonical=int(h),
            confidence=1.0,
        ))
    return out


# ---------------------------------------------------------------------------
# Beam detection
# ---------------------------------------------------------------------------


def detect_beams(
    cell,
    *,
    min_width_lines: float = 1.5,
    min_height_lines: float = 0.10,
    max_height_lines: float = 1.0,
    typical_single_beam_lines: float = 0.22,
    min_height_absolute: int = 2,
    max_width_cell_fraction: float = 0.70,
) -> list[LineDetection]:
    """Find beam-like horizontal ink runs in `cell`.

    Algorithm mirrors stems but with a horizontal structuring element:
      1. Pick the cleanest source — staff-removed if available.
      2. Threshold → binary ink.
      3. Horizontal morphological opening with a (line_spacing×1.5 × 1)
         element. Erases everything that isn't a long horizontal run.
      4. Connected components → candidate beams.
      5. Filter:
           - width ≥ min_width_lines × line_spacing
           - **width ≤ max_width_cell_fraction × cell_width**
             (rejects staff-line residue: real beams are local within a
             measure; staff lines span the whole cell. A blob wider than
             ~70 % of the cell is almost certainly staff-line ink.)
           - height between min/max_height_lines × line_spacing
           - aspect ratio ≥ 2:1 horizontal
      6. **Split stacked beams.** A double-beam (16th notes) or triple-
         beam (32nds) often appears as one tall component because the
         vertical gap between parallel beams is too small to survive
         binarization at this resolution. If a component's height is
         ≥ 1.7× the typical single-beam height, split it into
         `round(h / typical_beam_h)` equal sub-beams.

    `typical_single_beam_lines` controls when split fires. 0.22×
    line_spacing ≈ 10-12 px at canonical resolution, which matches a
    single engraved beam. Set this lower to split more aggressively,
    higher to split less.
    """
    if cell is None:
        return []
    src = (
        cell.image_no_staff
        if getattr(cell, "image_no_staff", None) is not None
        else cell.image
    )
    if src is None or src.size == 0:
        return []

    line_spacing = _staff_line_spacing(cell)
    if line_spacing <= 1.0:
        return []

    ink = _binary_ink(src)
    kernel_w = max(3, int(round(line_spacing * 1.5)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    num, _, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out: list[LineDetection] = []
    min_w = int(round(line_spacing * min_width_lines))
    # Real beams are local within a measure (typically span 2-4 noteheads).
    # Staff lines span the entire cell. Reject anything wider than this
    # fraction of the cell — it's almost certainly staff-line ink that
    # survived horizontal morphology.
    cell_w = cell.width
    max_w_abs = max(int(round(cell_w * max_width_cell_fraction)), int(round(line_spacing * 3.0)))
    # Absolute pixel floor on beam height is critical at orchestral cell
    # resolution where `line_spacing × 0.15` collapses to 2-3 px. Staff-line
    # residuals + ledger-line fragments are typically 1-3 px tall; real
    # beams are 5+ px even on the smallest cells.
    min_h = max(min_height_absolute, int(round(line_spacing * min_height_lines)))
    max_h = max(3, int(round(line_spacing * max_height_lines)))

    # Staff-line proximity filter: a beam whose y-range straddles a staff
    # line is almost certainly residual ink from imperfect staff removal,
    # not a real beam. Real beams sit between staves OR distinctly above /
    # below the staff (at the end of a stem). Reject candidates that
    # vertically overlap any staff line within `staff_line_band` pixels.
    staff_lines = getattr(cell, "staff_line_ys_canonical", None) or []
    staff_line_band = max(2, int(round(line_spacing * 0.10)))
    typical_h = max(3, int(round(line_spacing * typical_single_beam_lines)))
    # Only split components clearly thicker than a single beam — 1.7× is
    # the safety margin against engraving variance on solo beams.
    split_threshold = int(typical_h * 1.7)

    for i in range(1, num):
        x, y, w, h, area = stats[i]
        if w < min_w:
            continue
        if w > max_w_abs:
            # Cell-spanning blob — staff line residue, not a real beam.
            continue
        if h < min_h or h > max_h:
            continue
        if area < max(6, line_spacing):
            continue
        if w / max(1, h) < 2.0:
            continue

        # Reject components that straddle a staff line (residual ink).
        # A real beam has its y-center clearly off the staff lines.
        y_center = y + h // 2
        on_staff_line = any(
            abs(y_center - sl) <= staff_line_band for sl in staff_lines
        )
        if on_staff_line:
            continue

        if h >= split_threshold:
            # Cap at 5 levels — real music tops out at 1/128th-note beams.
            # Without the cap a 64-px tall noise blob can split into 20+
            # phantom sub-beams (see notes near `_merge_tilted_fragments`).
            n_levels = max(2, min(5, round(h / typical_h)))
            sub_h = max(1, h // n_levels)
            for k in range(n_levels):
                sub_y = int(y + k * (h / n_levels))
                out.append(LineDetection(
                    smufl_name="beam",
                    category="structural",
                    x_canonical=int(x),
                    y_canonical=sub_y,
                    width_canonical=int(w),
                    height_canonical=int(sub_h),
                    confidence=1.0,
                ))
        else:
            out.append(LineDetection(
                smufl_name="beam",
                category="structural",
                x_canonical=int(x),
                y_canonical=int(y),
                width_canonical=int(w),
                height_canonical=int(h),
                confidence=1.0,
            ))

    # Post-process: merge tilted-beam fragments, then NMS-dedupe overlaps.
    # Order matters — merging first allows two small adjacent fragments to
    # become one wide bbox that then survives NMS over a nearby duplicate.
    out = _merge_tilted_fragments(out, line_spacing)
    out = _nms_dedup(out)
    return out


# ---------------------------------------------------------------------------
# Post-processing — fragment merge + NMS-style dedup
# ---------------------------------------------------------------------------


def _bbox_iou(a: LineDetection, b: LineDetection) -> float:
    """Standard IoU between two axis-aligned bboxes."""
    ax1, ay1 = a.x_canonical, a.y_canonical
    ax2, ay2 = ax1 + a.width_canonical, ay1 + a.height_canonical
    bx1, by1 = b.x_canonical, b.y_canonical
    bx2, by2 = bx1 + b.width_canonical, by1 + b.height_canonical
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    a_area = max(1, a.width_canonical * a.height_canonical)
    b_area = max(1, b.width_canonical * b.height_canonical)
    union = a_area + b_area - inter
    return inter / union if union > 0 else 0.0


def _merge_two(a: LineDetection, b: LineDetection) -> LineDetection:
    """Bbox-union two detections into one."""
    x1 = min(a.x_canonical, b.x_canonical)
    y1 = min(a.y_canonical, b.y_canonical)
    x2 = max(a.x_canonical + a.width_canonical, b.x_canonical + b.width_canonical)
    y2 = max(a.y_canonical + a.height_canonical, b.y_canonical + b.height_canonical)
    return LineDetection(
        smufl_name=a.smufl_name,
        category=a.category,
        x_canonical=int(x1),
        y_canonical=int(y1),
        width_canonical=int(x2 - x1),
        height_canonical=int(y2 - y1),
        confidence=max(a.confidence, b.confidence),
    )


def _merge_tilted_fragments(
    beams: list[LineDetection],
    line_spacing: float,
    *,
    max_x_gap_lines: float = 0.5,
    max_y_drift_lines: float = 1.2,
    max_x_overlap_fraction: float = 0.30,
) -> list[LineDetection]:
    """A tilted beam often opens into 2-3 adjacent fragments (the horizontal
    morphological kernel can't sweep a slanted shape cleanly). Merge any
    detections that look like fragments of the same beam.

    Two detections merge if all three are true:
      - **Adjacent in x** — the x-gap between them is ≤ max_x_gap_lines × line_spacing.
      - **NOT heavily overlapping in x** — if they overlap by more than
        max_x_overlap_fraction of the smaller width, they're treated as
        parallel sub-beams (8th+16th double-beam structure) and kept separate.
      - **Close in y** — y-midpoints differ by ≤ max_y_drift_lines × line_spacing
        (allows for tilt staircase + thickness variance).
    """
    if len(beams) <= 1:
        return list(beams)
    sorted_beams = sorted(beams, key=lambda b: b.x_canonical)
    n = len(sorted_beams)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    max_gap = max(1, int(round(line_spacing * max_x_gap_lines)))
    max_drift = max(1, int(round(line_spacing * max_y_drift_lines)))

    for i in range(n):
        a = sorted_beams[i]
        a_x_end = a.x_canonical + a.width_canonical
        a_y_mid = a.y_canonical + a.height_canonical / 2
        # Sorted by x_canonical, so we only need to look forward until the
        # gap exceeds the threshold.
        for j in range(i + 1, n):
            b = sorted_beams[j]
            gap = b.x_canonical - a_x_end
            if gap > max_gap:
                break  # subsequent beams are even further right
            # y closeness
            b_y_mid = b.y_canonical + b.height_canonical / 2
            if abs(a_y_mid - b_y_mid) > max_drift:
                continue
            # x-overlap check — sub-beams (parallel) heavily overlap; fragments don't
            b_x_end = b.x_canonical + b.width_canonical
            x_overlap = min(a_x_end, b_x_end) - max(a.x_canonical, b.x_canonical)
            min_w = max(1, min(a.width_canonical, b.width_canonical))
            if x_overlap > min_w * max_x_overlap_fraction:
                continue
            union(i, j)

    groups: dict[int, list[LineDetection]] = {}
    for i, b in enumerate(sorted_beams):
        groups.setdefault(find(i), []).append(b)

    merged: list[LineDetection] = []
    for group in groups.values():
        if len(group) == 1:
            merged.append(group[0])
        else:
            m = group[0]
            for other in group[1:]:
                m = _merge_two(m, other)
            merged.append(m)
    return merged


def _nms_dedup(
    beams: list[LineDetection],
    *,
    iou_threshold: float = 0.55,
) -> list[LineDetection]:
    """Non-maximum suppression for over-detected beams: when two boxes have
    IoU ≥ threshold, keep the wider one (it's almost always the more
    complete detection)."""
    if len(beams) <= 1:
        return list(beams)
    # Sort by width descending so we keep the largest detections first
    sorted_beams = sorted(beams, key=lambda b: b.width_canonical, reverse=True)
    kept: list[LineDetection] = []
    for b in sorted_beams:
        suppressed = False
        for k in kept:
            if _bbox_iou(b, k) >= iou_threshold:
                suppressed = True
                break
        if not suppressed:
            kept.append(b)
    return kept


# ---------------------------------------------------------------------------
# Convenience: detect both at once
# ---------------------------------------------------------------------------


def detect_lines(cell) -> dict[str, list[LineDetection]]:
    """Return {'stems': [...], 'beams': [...]}."""
    return {
        "stems": detect_stems(cell),
        "beams": detect_beams(cell),
    }
