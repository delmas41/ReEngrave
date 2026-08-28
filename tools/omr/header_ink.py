"""Ink primitives shared by the header readers.

`clef_locator` and `key_signature_locator` face the same picture: a strip at the
start of a staff, on old paper, where the staff lines have survived the upstream
removal and the initial barline sits a few pixels from the first glyph. Both have
to get from that to clean, glyph-sized ink clusters before they can measure
anything, and both must do it identically — a clef and a key signature are
neighbours in the same crop, and two different notions of "what counts as ink"
between them would put the boundary between clef and signature in two places.

These functions were written for the C-clef locator and are unchanged here; this
module is where they live now so there is one copy.

Phase 1's convention holds throughout: in a cell image 255 is paper and 0 is ink,
while in the masks these functions return 255 is ink.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .types import MeasureCell


@dataclass(frozen=True)
class InkMaskConfig:
    """Thresholds for turning a header crop into glyph ink. Lengths are in
    staff spaces.

    Any object with these three attributes will do — `ClefLocatorConfig`
    carries them itself, so the clef locator passes its own config straight
    through and keeps a single set of knobs.
    """

    vertical_rule_max_width_spaces: float = 0.5   # thinner ⇒ a rule, not a glyph
    vertical_rule_min_height_spaces: float = 2.0
    min_ink_height_spaces: float = 0.2


DEFAULT_INK_CONFIG = InkMaskConfig()


def strip_vertical_rules(
    mask: np.ndarray, spacing: float, config: InkMaskConfig
) -> np.ndarray:
    """Erase thin, tall vertical runs: the initial barline, the system bracket,
    and any long stem in the header.

    Necessary because the barline at the start of a system sits within a few
    pixels of the clef — far too close for any proximity-based grouping to keep
    them apart, so without this the clef arrives fused to a full-height rule
    and fails every shape test. Thinness is what identifies a rule: a barline
    is a fraction of a staff space wide, while the narrowest part of a clef is
    comfortably wider.
    """
    tall = max(3, int(round(config.vertical_rule_min_height_spaces * spacing)))
    vert = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, tall))
    )
    n, labels, stats, _ = cv2.connectedComponentsWithStats(vert, connectivity=8)
    max_w = config.vertical_rule_max_width_spaces * spacing
    rules = np.zeros_like(mask)
    for i in range(1, n):
        if stats[i, cv2.CC_STAT_WIDTH] <= max_w:
            rules[labels == i] = 255
    # Grow slightly so the rule's soft edges go too, instead of surviving as a
    # hairline that still bridges the clef to whatever is beside it.
    rules = cv2.dilate(rules, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)))
    return cv2.subtract(mask, rules)


def strip_horizontal_rules(mask: np.ndarray, spacing: float) -> np.ndarray:
    """Erase long horizontal runs — staff lines, and whatever the upstream
    staff-line removal left behind.

    Opening with a wide, one-pixel-tall kernel keeps only ink belonging to a
    run at least 1.5 staff spaces long, which no part of a clef is: even a
    broad archaic C clef's bars are about one space wide. The dilation clears
    anti-aliased edges that would otherwise survive as a dotted line and
    re-bridge the glyphs the stripping was meant to separate.
    """
    k = max(3, int(round(1.5 * spacing)))
    horiz = cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (k, 1))
    )
    horiz = cv2.dilate(horiz, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    return cv2.subtract(mask, horiz)


def drop_flat_residue(mask: np.ndarray, spacing: float, config: InkMaskConfig) -> np.ndarray:
    """Remove ink with no vertical substance — the dashes and hairlines that a
    staff line leaves once its long runs have been cut out.

    Without this the fragments act as stepping stones: each is individually
    tiny, but strung together they connect the clef to the barline, to the key
    signature, and to the first notehead, and the glyph never appears as a
    cluster of its own. Opening with a one-pixel-wide, short vertical kernel
    keeps only ink belonging to a vertical run of at least
    `min_ink_height_spaces`, which every stroke of a clef satisfies and no
    remnant of a line does.
    """
    k = max(3, int(round(config.min_ink_height_spaces * spacing)))
    return cv2.morphologyEx(
        mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, k))
    )


def ink_mask(
    cell: MeasureCell, spacing: float, config: InkMaskConfig
) -> np.ndarray | None:
    """Binary ink mask (255 = ink) for the cell, with rules removed.

    Starts from the staff-line-removed variant when there is one, but does not
    rely on it: on old engravings with thick, uneven lines it leaves most of
    the staff behind — which is exactly the material this locator exists for.
    Vertical rules go first, while the barline is still whole; stripping the
    horizontals first would cut it into short pieces that no longer look like
    a rule.
    """
    img = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if img is None or img.size == 0:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    # Phase 1 convention: 255 = paper, 0 = ink.
    _, mask = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)
    mask = strip_vertical_rules(mask, spacing, config)
    mask = strip_horizontal_rules(mask, spacing)
    return drop_flat_residue(mask, spacing, config)


def staff_metrics(cell: MeasureCell) -> tuple[float, float, float] | None:
    """(line_spacing, top_line_y, bottom_line_y) in canonical pixels, or None
    when the cell has no usable 5-line staff."""
    ys = cell.staff_line_ys_canonical
    if not ys or len(ys) != 5:
        return None
    s = sorted(float(y) for y in ys)
    gaps = [s[i + 1] - s[i] for i in range(4)]
    spacing = sum(gaps) / len(gaps)
    if spacing <= 0:
        return None
    return spacing, s[0], s[-1]


def cluster_components(
    boxes: list[tuple[int, int, int, int, int]], max_gap: float
) -> list[tuple[int, int, int, int]]:
    """Merge components into glyph-sized clusters by horizontal proximity.

    An archaic C clef is drawn as a stack of separate bars, and stripping the
    staff lines cuts even a solid glyph into pieces, so a clef is routinely
    several components that belong together. Grouping by x-gap rejoins them
    without assuming how many pieces the engraver — or the morphology — left.

    `boxes` are (x, y, w, h, area); returns merged (x, y, w, h), left to right.
    """
    if not boxes:
        return []
    ordered = sorted(boxes, key=lambda b: b[0])
    clusters: list[list[tuple[int, int, int, int, int]]] = [[ordered[0]]]
    for b in ordered[1:]:
        cur_right = max(c[0] + c[2] for c in clusters[-1])
        if b[0] - cur_right <= max_gap:
            clusters[-1].append(b)
        else:
            clusters.append([b])
    merged: list[tuple[int, int, int, int]] = []
    for cl in clusters:
        x0 = min(c[0] for c in cl)
        y0 = min(c[1] for c in cl)
        x1 = max(c[0] + c[2] for c in cl)
        y1 = max(c[1] + c[3] for c in cl)
        merged.append((int(x0), int(y0), int(x1 - x0), int(y1 - y0)))
    return merged

