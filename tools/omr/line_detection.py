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


# The stem-isolating opening kernel, as a fraction of `min_height_lines` (see
# detect_stems). Anything at or above 0.8 gives the same answer on the
# reference sheet at every line thickness tested; below it, noteheads start
# surviving the opening again.
STEM_KERNEL_MARGIN = 0.8


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
    # Vertical structuring element: width 1, height just under the shortest
    # stem this function will accept.
    #
    # It used to be one line spacing, which is exactly a notehead's height — so
    # a notehead survived the opening, stayed joined to its own stem, and the
    # component came out as wide as the notehead. The width filter below then
    # threw the stem away along with it. That stayed hidden while staff-line
    # removal was a no-op, because an un-removed staff line broke the notehead
    # up for us; fixing removal exposed it, and Mahler 5 p.11 fell from 178
    # stems to 145. Measured against the LilyPond reference sheet (which knows
    # its own stem count), the 1.0 kernel scored 35 of 48 stems at 0.29 staff
    # spaces of line thickness and 11 of 48 at 0.39; at this height, 53 and 50.
    #
    # The principle sets the value: a component shorter than `min_height_lines`
    # is rejected a few lines below regardless, so erasing it here costs
    # nothing, and the taller the kernel the more non-stem ink it clears first.
    # So take it just under that floor — the margin absorbs a stem sitting
    # exactly at the limit and the pixel or two rasterisation moves it.
    kernel_h = max(3, int(round(line_spacing * min_height_lines * STEM_KERNEL_MARGIN)))
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
            n_levels = max(2, round(h / typical_h))
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
    return out


# ---------------------------------------------------------------------------
# Convenience: detect both at once
# ---------------------------------------------------------------------------


def detect_lines(cell) -> dict[str, list[LineDetection]]:
    """Return {'stems': [...], 'beams': [...]}."""
    return {
        "stems": detect_stems(cell),
        "beams": detect_beams(cell),
    }
