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


def _drop_paired_strokes(stems, line_spacing: float, gap: float, min_overlap: float):
    """Reject vertical strokes that come in PAIRS, which stems do not.

    A sharp and a natural are each built from two parallel verticals about half
    a staff space apart and roughly two spaces tall — which is to say, they look
    exactly like a pair of short stems, and `detect_stems` was reporting them as
    such. Measured against 14 hand-counted cells, they were most of the error:
    summed |error| 60, and on the two Mahler cells the count was 16 and 14
    against a truth of 5 and 3.

    A stem is single. Two noteheads a second apart share one stem rather than
    standing side by side, and successive notes are set further apart than an
    accidental's own strokes, so the pair is the accidental's signature.

    The gap is bounded by the notation on both sides: wider than the ~0.5-0.7
    staff spaces between a sharp's strokes, narrower than the spacing between
    consecutive notes. Both members of a pair are dropped, since neither is a
    stem.
    """
    if line_spacing <= 0 or len(stems) < 2:
        return list(stems)
    max_dx = line_spacing * gap
    centres = [s.x_canonical + s.width_canonical / 2.0 for s in stems]
    tops = [float(s.y_canonical) for s in stems]
    bottoms = [t + s.height_canonical for t, s in zip(tops, stems)]

    kept = []
    for i, stem in enumerate(stems):
        paired = False
        for j in range(len(stems)):
            if i == j or abs(centres[i] - centres[j]) > max_dx:
                continue
            overlap = min(bottoms[i], bottoms[j]) - max(tops[i], tops[j])
            if overlap <= 0:
                continue
            shorter = min(bottoms[i] - tops[i], bottoms[j] - tops[j])
            if overlap / max(1.0, shorter) >= min_overlap:
                paired = True
                break
        if not paired:
            kept.append(stem)
    return kept


def detect_stems(
    cell,
    *,
    min_height_lines: float = 2.0,
    max_height_lines: float = 6.0,
    max_width_lines: float = 0.6,
    accidental_pair_gap_lines: float = 0.9,
    accidental_pair_overlap: float = 0.6,
    drop_accidental_pairs: bool = True,
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
      6. Drop strokes that come in PAIRS — see `_drop_paired_strokes`. A sharp
         and a natural are each two parallel verticals about half a staff space
         apart and about two spaces tall, indistinguishable from a pair of short
         stems by any of the filters above.

    Returns LineDetection objects in canonical-cell coordinates.

    Measured against 14 hand-counted cells across four scores, the pair rule
    takes summed |error| from 60 to 24, and against the LilyPond reference
    sheet from +7/+8/+5/+2 to -1/0/+1/0 on a truth of 48. Raising the height
    floor instead was tried and is worse (36) AND fails asymmetrically: it
    scores well on Boléro while destroying keyboard music, where stems in
    beamed groups are legitimately short (one WTC cell holds 15 stems and a
    2.8-space floor finds 5).
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
    if drop_accidental_pairs:
        out = _drop_paired_strokes(
            out, line_spacing, accidental_pair_gap_lines, accidental_pair_overlap
        )
    return out


# ---------------------------------------------------------------------------
# Beam detection
# ---------------------------------------------------------------------------


def _stacked_bar_count(opened, x: int, y: int, w: int, h: int, max_samples: int = 48) -> int:
    """How many beam bars are stacked here, counted as vertical ink runs.

    Not from the bounding box's height, which was the old approach and is wrong
    for the commonest case: a SLOPED beam. A beam over a rising figure has a
    box far taller than the beam is thick — measured on the reference sheet,
    sloped beams fill only 43-46% of their box against 95% for a level one — so
    dividing the box height by a beam's thickness reported a single sloped bar
    as two, three or eight.

    A column through the component crosses each bar exactly once, whatever the
    slope, so counting runs in a column counts bars. The median over sampled
    columns keeps a stem or a notehead crossing the beam from swaying it.
    """
    roi = opened[y:y + h, x:x + w] > 0
    if roi.size == 0:
        return 1
    step = max(1, roi.shape[1] // max_samples)
    cols = roi[:, ::step]
    # A run starts where ink appears under paper — count those per column.
    above = np.vstack([np.zeros((1, cols.shape[1]), dtype=bool), cols[:-1]])
    counts = (cols & ~above).sum(axis=0)
    counts = counts[counts > 0]
    if counts.size == 0:
        return 1
    return max(1, int(np.median(counts)))


def _attached_stem_count(labels, label: int, stems, x: int, y: int, w: int, h: int,
                         line_spacing: float, tolerance: float, end_reach: float) -> int:
    """How many stems END at this component — which is what makes it a beam.

    A beam exists to join stems, and it joins them at their ENDS. Nothing else
    that draws a long horizontal line in a score does that: a slur or tie runs
    between noteheads, a ledger line sits at a notehead's middle with at most
    one stem beside it, and staff-line residue has no stem at all. Measured on
    Mahler 5 p.11, those three were essentially the entire beam count — one
    cell of half notes under slurs was reporting 27 beams.

    The comparison is made against the component's ink IN THE STEM'S OWN COLUMN
    rather than against its bounding box. A sloped beam's box reaches far above
    and below the bar itself, so box edges put the far stem out of range and a
    sloped double beam lost its lower bar.
    """
    found = 0
    x_lo = x - line_spacing * 0.4
    x_hi = x + w + line_spacing * 0.4
    for s in stems:
        sx = s.x_canonical + s.width_canonical / 2.0
        if not (x_lo <= sx <= x_hi):
            continue
        # Clamp only for the lookup: a beam may stop a hair short of the stem
        # that hangs from its end.
        sx = min(max(int(round(sx)), x), x + w - 1)
        column = labels[y:y + h, sx] == label
        if not column.any():
            continue
        rows = np.flatnonzero(column)
        local_top = y + int(rows[0])
        local_bottom = y + int(rows[-1])
        top = float(s.y_canonical)
        bottom = top + s.height_canonical
        # The stem must meet the beam: end at it, or run through it. A
        # SECONDARY beam is run through rather than ended at — with a double
        # beam the stems stop at the outer bar and cross the inner one — so
        # requiring an end here would find the primary bar of every group and
        # discard the secondary.
        meets = (top - tolerance) <= local_bottom and (bottom + tolerance) >= local_top
        if not meets:
            continue
        # ...but the stem's END still has to be in the neighbourhood, which is
        # what keeps a long horizontal residue INSIDE the staff from being
        # adopted by every stem that happens to cross it. A secondary beam sits
        # less than a bar-pitch from the primary, so the reach only has to
        # cover a stack of them.
        nearest_end = min(abs(top - local_top), abs(top - local_bottom),
                          abs(bottom - local_top), abs(bottom - local_bottom))
        if nearest_end <= end_reach:
            found += 1
    return found


def detect_beams(
    cell,
    *,
    stems: list[LineDetection] | None = None,
    min_width_lines: float = 1.5,
    min_height_lines: float = 0.10,
    max_height_lines: float = 2.5,
    min_height_absolute: int = 2,
    stem_attach_tolerance_lines: float = 1.0,
    stem_end_reach_lines: float = 2.5,
    stem_anchor_min_height_lines: float = 2.8,
    min_attached_stems: int = 2,
) -> list[LineDetection]:
    """Find beams in `cell`.

      1. Pick the cleanest source — staff-removed if available.
      2. Horizontal morphological opening → candidate horizontal runs.
      3. Connected components, filtered on width, height and aspect.
      4. Keep only components that at least `min_attached_stems` stems END at.
      5. Count the stacked bars in each by vertical ink runs, not box height.

    Steps 4 and 5 are what this function got wrong for a long time, and the
    LilyPond reference sheet (`benchmarks/omr-phase4-lines/`) is what made it
    visible: against a known 14 beam bars it reported 51, and against a known
    12 on one staff it reported 41.

    Without step 4 the count is dominated by things that are horizontal but are
    not beams — slurs, ties, ledger lines, staff-line residue. Requiring two
    stem ends removes all four classes at once without a rule per class:
    measured on the reference sheet, error against ground truth falls from 157
    to 3 summed over four staff-line thicknesses, and it holds under
    degradation down to a 150 DPI render.

    `max_height_lines` is 2.5 rather than 1.0 because both a stack of bars and
    a sloped bar are legitimately taller than one beam. At 1.0 an entire
    measure of sixteenths — two bars per group — was rejected outright and
    scored 0 against a known 8.
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

    if stems is None:
        stems = detect_stems(cell)

    ink = _binary_ink(src)
    kernel_w = max(3, int(round(line_spacing * 1.5)))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    opened = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(opened, connectivity=8)
    out: list[LineDetection] = []
    min_w = int(round(line_spacing * min_width_lines))
    # Absolute pixel floor on beam height is critical at orchestral cell
    # resolution where `line_spacing × 0.10` collapses to 2-3 px.
    min_h = max(min_height_absolute, int(round(line_spacing * min_height_lines)))
    max_h = max(3, int(round(line_spacing * max_height_lines)))
    tolerance = line_spacing * stem_attach_tolerance_lines
    end_reach = line_spacing * stem_end_reach_lines

    # Only FULL-LENGTH stems may anchor a beam. `detect_stems` accepts anything
    # from 2 staff spaces up, and at that floor it also picks up the vertical
    # strokes of sharps and naturals, which are about that tall. Those false
    # stems were lending their two-stem quorum to whatever horizontal ink lay
    # near them — on a hand-labeled Mahler cell holding no beams at all, five
    # ledger lines were reported as beams because the accidentals beside them
    # counted. A beam hangs off a real stem: conventionally 3.5 staff spaces,
    # shortened in beamed groups but not to an accidental's height.
    #
    # This filters only the ANCHOR set. `detect_stems`' own output is untouched,
    # because raising its floor would drop about 30% of the stems on real pages
    # and there is no stem ground truth to say whether those are false.
    anchors = [
        s for s in stems
        if s.height_canonical >= line_spacing * stem_anchor_min_height_lines
    ]

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
        attached = _attached_stem_count(
            labels, i, anchors, x, y, w, h, line_spacing, tolerance, end_reach
        )
        if attached < min_attached_stems:
            continue

        n_bars = _stacked_bar_count(opened, x, y, w, h)
        sub_h = max(1, h // n_bars)
        for k in range(n_bars):
            out.append(LineDetection(
                smufl_name="beam",
                category="structural",
                x_canonical=int(x),
                y_canonical=int(y + k * (h / n_bars)),
                width_canonical=int(w),
                height_canonical=int(sub_h),
                confidence=1.0,
            ))
    return out


# ---------------------------------------------------------------------------
# Convenience: detect both at once
# ---------------------------------------------------------------------------


def detect_lines(cell) -> dict[str, list[LineDetection]]:
    """Return {'stems': [...], 'beams': [...]}.

    Stems are found first and handed to the beam pass, which needs them to tell
    a beam from a slur, a tie or a ledger line — and computing them once here
    keeps that from costing a second detection.
    """
    stems = detect_stems(cell)
    return {
        "stems": stems,
        "beams": detect_beams(cell, stems=stems),
    }
