"""Find the key signature at the start of a staff with classical CV, when the
detector can't see one at all.

`key_signature_geometry` reads a key signature once its accidentals have been
located. This module locates them, for the case that turns out to be the normal
one on real prints: nothing was detected.

Measured on Beethoven 5 p.1 (IMSLP 984073, the production weights, the run
saved in `benchmarks/omr-clef-demo/beet5_p1_production.omr.json`): across 3,246
detections on a page whose every string and woodwind staff carries three flats,
the model emits **zero** `keySharp` or `keyFlat` detections, and one
`accidentalSharp` in total. Every staff on the page reads as no key signature.
That is the same domain gap the archaic C clefs hit — DeepScoresV2 is rendered
from modern fonts, and a 19th-century key signature printed small, at the head
of a staff, on browned paper, is not in that distribution.

Classical CV doesn't care what font a signature is set in, and a key signature
is unusually well suited to being found rather than recognised:

  * It is **one glyph repeated**. The accidentals in a signature are the same
    size and shape as each other, which is a much stronger and more checkable
    signal than any single one of them being identifiable.
  * It sits in a **known place** — immediately after the clef, before the time
    signature and the first note.
  * Its members are **evenly spaced** in a short run.

So the locator looks for a run of similar, glyph-sized ink clusters after the
clef, and hands their positions to the geometric fit, which is what decides
whether they really are a key signature. A run that doesn't fit any signature
under this staff's clef is discarded rather than reported.

## Sharps or flats

Two answers, from two independent signals:

  * **Position pattern** (used whenever there are two or more accidentals).
    Sharps and flats zigzag in opposite directions — sharps step down a fourth
    then up a fifth, flats up a fourth then down a fifth — so the shape of the
    run alone says which it is, in a way that no font choice can affect. This
    is the strong signal and it wins where it applies.
  * **Ink distribution** (needed for a run of one — a single flat is a common
    signature, and its position alone can't distinguish it from a single
    sharp). A flat is bottom-heavy with a thin ascender; a sharp is balanced
    about its middle. See `_accidental_shape`.

## What it will not do

It speaks only when the detector found no key-signature accidentals, so a score
that reads correctly today cannot be made worse by it. It abstains — no run, an
off-pattern run, a clef with no slot table, a staff without clean 5-line
geometry — rather than guessing, because a wrong key signature re-pitches every
note on the staff for the rest of the system.

## STATUS: not yet working on degraded prints

Measured on Beethoven 5 p.2 (IMSLP 575951), whose eleven staves carry a known
mix of three flats, one flat and none: **0 of 8 signatures located**, no false
positives. It abstains rather than misreading, so it is harmless, but it is not
yet earning its place.

The failure is upstream of everything this module does, and it is not the fit.
On that print the staff lines are **0.15–0.31 staff spaces thick** (a modern
engraving is nearer 0.08) and they wander in canonical coordinates, so they
survive every removal this pipeline offers: `image_no_staff` leaves heavy
residue, morphological opening by a wide kernel shreds the accidentals along
with the lines, and erasing a straight band at each measured line y misses the
parts that wander out of it. Whichever is tried, the header comes back as one
connected mass spanning the full window — connected components merge into a
single 16-space blob, and a column projection finds ink in every column.

The fix belongs in staff-line removal — erasing along each line's actual traced
path rather than a straight row band — not here. Until then this module is
loaded but silent on exactly the material it was written for.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .header_ink import (
    DEFAULT_INK_CONFIG,
    InkMaskConfig,
    cluster_components,
    ink_mask,
    staff_metrics,
)
from .key_signature_geometry import (
    DEFAULT_CONFIG as DEFAULT_FIT_CONFIG,
    KeySignatureFitConfig,
    KeySignatureRead,
    fit_key_signature,
)
from .types import MeasureCell


@dataclass(frozen=True)
class KeySignatureLocatorConfig:
    """Shape gates for the header key-signature locator. Every length is in
    staff spaces, so the thresholds hold at any DPI or engraving size.
    """

    # One accidental. A sharp is the tallest at roughly 2.5 spaces and about a
    # space wide; a flat is shorter. The bounds are loose enough for the
    # squashed, uneven glyphs of a 19th-century print and tight enough to keep
    # out a clef (much bigger) and a lone notehead (much shorter).
    min_width_spaces: float = 0.30
    max_width_spaces: float = 1.70
    min_height_spaces: float = 1.10
    max_height_spaces: float = 3.60

    # Fragments this close together are one glyph — a flat cut in two by staff
    # line removal, for instance. Smaller than the gap BETWEEN accidentals, or
    # a whole signature would merge into a single cluster.
    cluster_gap_spaces: float = 0.40
    # And accidentals this close together are one run. A key signature is set
    # tight; the first note of the bar is much further off.
    run_gap_spaces: float = 1.90

    # Members of a run must be the same size, because they are the same glyph.
    # This is the gate that rejects "a stem, then a notehead, then a rest".
    size_tolerance: float = 0.35
    # How far off this staff's own band a cluster may be centred. Cells are
    # taller than their staff, so ink from the staves above and below is in
    # the picture too.
    staff_band_spaces: float = 2.50
    min_ink_fraction: float = 0.10
    min_component_area_spaces: float = 0.02

    # A signature has at most seven accidentals. A longer run is note ink.
    max_run_length: int = 7
    # Clusters bigger than this are the clef, not an accidental — the run
    # starts after them.
    clef_min_height_spaces: float = 3.60


DEFAULT_LOCATOR_CONFIG = KeySignatureLocatorConfig()


@dataclass(frozen=True)
class LocatedKeySignature:
    """A key signature found by shape alone.

    read:        the fitted signature — the same type the detector path yields.
    boxes:       (x, y, w, h) of each accidental found, canonical coordinates,
                 left to right.
    accidental:  "#" or "b".
    decided_by:  "pattern" when the zigzag settled sharp-vs-flat, "shape" when
                 the run was too short for that and ink distribution decided.
    """

    read: KeySignatureRead
    boxes: tuple[tuple[int, int, int, int], ...]
    accidental: str
    decided_by: str


def _accidental_shape(mask: np.ndarray, bbox: tuple[int, int, int, int]) -> float:
    """How bottom-heavy a glyph is, 0 … 1 — the flat/sharp discriminator for a
    run too short for the position pattern to speak.

    A flat is a bowl with an ascender: nearly all of its ink is in the lower
    half, and what is above is a single thin stroke. A sharp is two horizontal
    bars crossed by two verticals, balanced about its centre; a natural is the
    same balance in a narrower box. Measuring the share of ink below the box's
    middle separates them without reference to any particular font's outline —
    the property is what the glyphs ARE, not how they are drawn.
    """
    x, y, w, h = bbox
    sub = mask[y : y + h, x : x + w] > 0
    total = float(sub.sum())
    if total <= 0:
        return 0.5
    return float(sub[h // 2 :].sum() / total)


# Above this share of ink below the middle, a glyph is a flat. Sharps and
# naturals measure close to 0.5 by construction (they are symmetric about their
# centre); a flat's bowl carries the great majority of its ink.
FLAT_SHAPE_THRESHOLD = 0.62


def _positions(
    boxes: list[tuple[int, int, int, int]], top_y: float, spacing: float
) -> list[float]:
    """Box centres as diatonic steps below the top staff line — the unit the
    slot tables use. The glyph-anchor error this leaves is constant across a
    run and is solved for by the fit.
    """
    half = spacing / 2.0
    return [((y + h / 2.0) - top_y) / half for (_x, y, _w, h) in boxes]


def _candidate_runs(
    boxes: list[tuple[int, int, int, int]],
    spacing: float,
    config: KeySignatureLocatorConfig,
) -> list[list[tuple[int, int, int, int]]]:
    """Split glyph clusters, left to right, into runs of same-sized neighbours.

    A run breaks on a wide gap or on a change of glyph size; both mean the next
    thing is not another copy of what we have been reading.
    """
    runs: list[list[tuple[int, int, int, int]]] = []
    current: list[tuple[int, int, int, int]] = []
    for box in boxes:
        if not current:
            current = [box]
            continue
        px, _py, pw, ph = current[-1]
        gap = box[0] - (px + pw)
        heights = [b[3] for b in current]
        median_h = sorted(heights)[len(heights) // 2]
        same_size = abs(box[3] - median_h) <= config.size_tolerance * median_h
        if gap <= config.run_gap_spaces * spacing and same_size:
            current.append(box)
        else:
            runs.append(current)
            current = [box]
    if current:
        runs.append(current)
    return runs


def locate_key_signature(
    cell: MeasureCell,
    clef: str | None,
    *,
    occupied_boxes: list[tuple[int, int, int, int]] | None = None,
    config: KeySignatureLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    ink_config: InkMaskConfig = DEFAULT_INK_CONFIG,
    fit_config: KeySignatureFitConfig = DEFAULT_FIT_CONFIG,
) -> LocatedKeySignature | None:
    """Locate the key signature in a staff header cell and read it, or return
    None.

    `cell` should be a header cell from `staff_header.extract_header_cell` — a
    crop that starts at the staff's left edge and ends at the first barline.
    `clef` is this staff's clef, which decides the slot table; without it (or
    with a clef the table doesn't cover) the read cannot be made and None comes
    back.

    `occupied_boxes` are canonical (x, y, w, h) boxes the detector has already
    claimed for something else — noteheads and rests. An accidental in a key
    signature never overlaps one.
    """
    if not clef:
        return None
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, bottom_y = metrics
    mask = ink_mask(cell, spacing, ink_config)
    if mask is None:
        return None

    n, _labels, stats, _cent = cv2.connectedComponentsWithStats(mask, connectivity=8)
    min_area = config.min_component_area_spaces * spacing * spacing
    band_margin = config.staff_band_spaces * spacing
    band_top, band_bottom = top_y - band_margin, bottom_y + band_margin
    components: list[tuple[int, int, int, int, int]] = []
    for i in range(1, n):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        y_i = int(stats[i, cv2.CC_STAT_TOP])
        h_i = int(stats[i, cv2.CC_STAT_HEIGHT])
        if not (band_top <= y_i + h_i / 2.0 <= band_bottom):
            continue
        components.append(
            (int(stats[i, cv2.CC_STAT_LEFT]), y_i, int(stats[i, cv2.CC_STAT_WIDTH]), h_i, area)
        )

    clusters = cluster_components(components, max_gap=config.cluster_gap_spaces * spacing)

    # Keep accidental-sized clusters, and remember where the clef ended: the
    # signature is printed after it, and starting the search before it invites
    # the clef's own strokes into the run.
    clef_right = 0
    glyphs: list[tuple[int, int, int, int]] = []
    for bbox in clusters:
        x, y, w, h = bbox
        w_sp, h_sp = w / spacing, h / spacing
        if h_sp >= config.clef_min_height_spaces or w_sp > config.max_width_spaces:
            clef_right = max(clef_right, x + w)
            continue
        if not (config.min_width_spaces <= w_sp <= config.max_width_spaces):
            continue
        if not (config.min_height_spaces <= h_sp <= config.max_height_spaces):
            continue
        ink = int(np.count_nonzero(mask[y : y + h, x : x + w]))
        if w * h == 0 or ink / float(w * h) < config.min_ink_fraction:
            continue
        if _overlaps_any(bbox, occupied_boxes):
            continue
        glyphs.append(bbox)

    glyphs = [g for g in glyphs if g[0] >= clef_right]
    if not glyphs:
        return None

    for run in _candidate_runs(glyphs, spacing, config):
        run = run[: config.max_run_length]
        positions = _positions(run, top_y, spacing)
        sharp_fit = fit_key_signature(positions, clef, "#", fit_config)
        flat_fit = fit_key_signature(positions, clef, "b", fit_config)
        if sharp_fit is None and flat_fit is None:
            continue
        if len(run) >= 2 and sharp_fit is not None and flat_fit is not None:
            # Both patterns can be made to fit a short run; the zigzag runs in
            # opposite directions, so whichever fits more tightly is the truth.
            best = sharp_fit if sharp_fit.residual <= flat_fit.residual else flat_fit
            decided_by = "pattern"
        elif sharp_fit is not None and flat_fit is not None:
            # One accidental: position says nothing, so the ink does.
            bottom_heavy = _accidental_shape(mask, run[0]) >= FLAT_SHAPE_THRESHOLD
            best = flat_fit if bottom_heavy else sharp_fit
            decided_by = "shape"
        else:
            best = sharp_fit or flat_fit
            decided_by = "pattern"
        assert best is not None and best.accidental is not None
        return LocatedKeySignature(
            read=best,
            boxes=tuple(run),
            accidental=best.accidental,
            decided_by=decided_by,
        )
    return None


def _overlaps_any(
    bbox: tuple[int, int, int, int],
    boxes: list[tuple[int, int, int, int]] | None,
) -> bool:
    """Whether `bbox` shares any area with a box the detector already claimed."""
    if not boxes:
        return False
    x, y, w, h = bbox
    for bx, by, bw, bh in boxes:
        if x < bx + bw and bx < x + w and y < by + bh and by < y + h:
            return True
    return False
