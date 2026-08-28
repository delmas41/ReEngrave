"""Find the C clef at the start of a staff with classical CV, when the detector
can't see one at all.

`clef_geometry` fixes *which* clef a detection is. This module fixes the case
where there is no detection to fix. On the material that motivated it —
19th-century engravings like Nottebohm's *Beethovens Studien*, whose
counterpoint exercises are written throughout in C clefs — the production model
and the clef-specialist model between them find **zero** C clefs on a page that
has one on every staff, even at confidence 0.03. The glyph is an archaic
"ladder" C clef that looks nothing like the modern fonts DeepScoresV2 was
rendered from, so no confidence threshold reaches it: a domain gap, not a
calibration problem. Every staff then falls back to the position default and
the whole page transcribes as treble, which is how a page of soprano-, alto-
and tenor-clef counterpoint comes out as nonsense.

Classical CV doesn't care what font a clef is set in. This is the division of
labour Phase 4f already settled on for stems and beams, and that barlines use:
hand the geometric, font-independent problems to morphology and leave YOLO the
ones that are genuinely about appearance.

## Why C clefs only

The locator identifies **C clefs and nothing else**, on purpose. A C clef is
the one clef with a shape signature that survives any engraving style: it is
vertically symmetric about the line it names, because that is what the glyph
is for. That symmetry is both how we recognise it and how we read it — the
centre of the ink IS the named line, so recognising the glyph and deciding
between soprano, alto and tenor are the same measurement.

G and F clefs are deliberately left alone. They have no comparably robust
font-independent signature, they are what the detector already reads *well*,
and the cost of being wrong is asymmetric: a missed clef leaves a staff on the
default it would have had anyway, but a wrongly-invented one transposes every
pitch on that staff. So a cluster that doesn't look like a C clef yields
nothing, and the existing behaviour stands.

## How it works

Take the staff-start cell; erase the vertical rules (the barline and bracket
that sit immediately left of the clef, often only a few pixels away) and the
horizontal ones (staff lines and the residue upstream removal leaves behind);
group what's left in the header strip into glyph-sized clusters; and test the
leftmost one for the C-clef signature — right size, and symmetric top-to-bottom.
Then hand its box to `clef_geometry`, which snaps the centre to a staff line
and names the clef.

## What it will not do

It only ever speaks when the detectors are silent (see `transcribe.py`), so a
score that reads correctly today cannot be made worse by it. And it abstains
rather than guesses: no cluster, an off-signature shape, an ambiguous snap, or
a staff without clean 5-line geometry all return None.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .clef_geometry import ClefGeometryConfig, ClefRead, DEFAULT_CONFIG, resolve_clef
from .types import MeasureCell


@dataclass(frozen=True)
class ClefLocatorConfig:
    """Shape gates for the header C-clef locator. Every length is in staff
    spaces (the distance between adjacent staff lines) so the thresholds hold
    at any DPI or engraving size.
    """

    header_frac: float = 0.30       # left fraction of the start cell to search
    # A clef is printed at the HEAD of the staff, so a candidate has to start
    # near it. A generous backstop rather than the main defence — on orchestral
    # scores the clef can sit several spaces in, behind a bracket and the
    # stacked instrument numbers engravers print to the left of it, so a tight
    # bound here would cost real viola and trombone clefs. The load-bearing
    # rule is "stop at the first glyph-sized cluster", below.
    max_start_spaces: float = 6.0
    min_width_spaces: float = 0.55  # narrower ⇒ barline / bracket / stem
    max_width_spaces: float = 4.5
    # A C clef spans about 4 spaces in modern fonts and about 3 in the older
    # narrow engravings; the ceiling is what keeps a G clef (≈7) out.
    min_height_spaces: float = 2.2
    max_height_spaces: float = 5.0
    min_symmetry: float = 0.72      # the C-clef signature — see _vertical_symmetry
    # How far the measured axis of symmetry may sit from the box centre. Big
    # enough to undo a stray fragment's pull, small enough that it can never
    # reach the next staff line (half a space would be the tipping point).
    axis_refine_spaces: float = 0.35
    min_ink_fraction: float = 0.10  # of the cluster's bbox — rejects stray rules
    cluster_gap_spaces: float = 0.6  # x-gap that still counts as one glyph
    min_component_area_spaces: float = 0.02  # speck filter, in (staff space)²
    vertical_rule_max_width_spaces: float = 0.5   # thinner ⇒ a rule, not a glyph
    vertical_rule_min_height_spaces: float = 2.0
    # Ink with less vertical extent than this is a staff-line fragment, not
    # part of a glyph — see _drop_flat_residue.
    min_ink_height_spaces: float = 0.2
    # How far beyond the staff's own lines a component may be centred and
    # still belong to this staff — see the band filter in locate_clef. A C
    # clef on the bottom line reaches about two spaces below it; anything
    # centred further out belongs to the neighbouring staff.
    staff_band_spaces: float = 2.2


DEFAULT_LOCATOR_CONFIG = ClefLocatorConfig()


@dataclass(frozen=True)
class LocatedClef:
    """A C clef found by shape alone.

    read:      the resolved clef, line included — the same `ClefRead` type the
               detector path produces.
    bbox:      (x, y, w, h) of the ink cluster, canonical coordinates.
    symmetry:  how symmetric the cluster's vertical ink profile is, 0…1.
    """

    read: ClefRead
    bbox: tuple[int, int, int, int]
    symmetry: float


def _strip_vertical_rules(
    mask: np.ndarray, spacing: float, config: ClefLocatorConfig
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


def _strip_horizontal_rules(mask: np.ndarray, spacing: float) -> np.ndarray:
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


def _drop_flat_residue(mask: np.ndarray, spacing: float, config: ClefLocatorConfig) -> np.ndarray:
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


def _ink_mask(
    cell: MeasureCell, spacing: float, config: ClefLocatorConfig
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
    mask = _strip_vertical_rules(mask, spacing, config)
    mask = _strip_horizontal_rules(mask, spacing)
    return _drop_flat_residue(mask, spacing, config)


def _staff_metrics(cell: MeasureCell) -> tuple[float, float, float] | None:
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


def _cluster_components(
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


def _vertical_symmetry(mask: np.ndarray, bbox: tuple[int, int, int, int]) -> float:
    """How symmetric a cluster is about its own centre, top-to-bottom, 0 … 1.

    This is the C-clef signature, and the gate the locator lives or dies by.
    The glyph exists to mark a staff line and is drawn balanced about it, so
    its row-wise ink profile reads nearly the same upside down — while a G clef
    (long tail below) and an F clef (heavy head at the top, dots to one side)
    do not.

    Measured about the box's own centre, deliberately. An unconstrained search
    for the best axis of symmetry scores far too kindly on lopsided glyphs —
    every shape has *some* axis it half-balances about — and on real pages that
    turned treble clefs into tenor clefs. Asking "is this thing symmetric where
    a C clef would be symmetric" is the question worth answering.
    """
    x, y, w, h = bbox
    sub = mask[y : y + h, x : x + w]
    if sub.size == 0:
        return 0.0
    profile = (sub > 0).sum(axis=1).astype(float)
    denominator = float((profile * profile).sum())
    if denominator <= 0:
        return 0.0
    return float((profile * profile[::-1]).sum() / denominator)


def _refine_symmetry_axis(
    mask: np.ndarray, bbox: tuple[int, int, int, int], max_shift: float
) -> float:
    """Locate the axis a cluster balances about, searching within `max_shift`
    pixels of the box's centre. Returns the axis y in mask coordinates.

    Once a cluster is known to be a C clef, this is what reads it: the axis of
    symmetry IS the line the clef names. Refining beyond the bounding box's
    midpoint matters because a stray fragment that survives the rule stripping
    — a beam stub, a scrap of a ledger line — drags the box's midpoint off by a
    fraction of a staff space, and here a fraction of a space is the difference
    between an alto clef and a tenor one. Scoring by mirror OVERLAP charges
    that fragment against the fit (ink with no partner counts in the
    denominator only) instead of letting it move the answer.

    The search is bounded because it is a refinement, not a rediscovery: the
    gate has already established what the glyph is and roughly where it sits,
    and an unbounded search would happily wander onto a neighbouring line.
    """
    x, y, w, h = bbox
    sub = mask[y : y + h, x : x + w]
    profile = (sub > 0).sum(axis=1).astype(float)
    total = float(profile.sum())
    centre = (len(profile) - 1) / 2.0
    if total <= 0 or len(profile) == 0:
        return float(y + centre)

    n = len(profile)
    indices = np.arange(n)
    best_axis, best_score = centre, -1.0
    # Half-pixel steps: a glyph balanced between two rows is common at these
    # scales, and rounding it to one of them is itself a measurable error.
    lo = int(np.floor((centre - max_shift) * 2))
    hi = int(np.ceil((centre + max_shift) * 2))
    for doubled_axis in range(lo, hi + 1):
        axis = doubled_axis / 2.0
        mirrored = np.rint(2 * axis - indices).astype(int)
        valid = (mirrored >= 0) & (mirrored < n)
        overlap = np.zeros(n)
        overlap[valid] = np.minimum(profile[valid], profile[mirrored[valid]])
        score = float(overlap.sum() / total)
        if score > best_score:
            best_axis, best_score = axis, score
    return float(y + best_axis)


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


def locate_clef(
    cell: MeasureCell,
    *,
    occupied_boxes: list[tuple[int, int, int, int]] | None = None,
    config: ClefLocatorConfig = DEFAULT_LOCATOR_CONFIG,
    geometry: ClefGeometryConfig = DEFAULT_CONFIG,
) -> LocatedClef | None:
    """Locate a C clef at the start of `cell` and name it, or return None.

    `cell` must be a staff-START cell — the clef only appears there, and on an
    interior measure this would happily nominate the first notehead cluster.

    `occupied_boxes` are canonical (x, y, w, h) boxes the detector has already
    identified as something other than a clef — noteheads and rests. A clef
    never overlaps one, so a candidate that does is rejected. This matters
    where a cell begins PAST its clef (see NOTES.md on staff x-extent): the
    first cluster is then real notation, and a stacked chord in particular is
    tall, glyph-sized and vertically symmetric enough to pass for a C clef.
    Reusing the detector's own output costs nothing and settles it.
    """
    metrics = _staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, bottom_y = metrics
    mask = _ink_mask(cell, spacing, config)
    if mask is None:
        return None

    # Search the header strip only. The clef is the first thing on the staff,
    # and limiting the x-range keeps note ink from ever becoming a candidate.
    hw = max(1, int(round(cell.width * config.header_frac)))
    strip = mask[:, :hw]

    n, _labels, stats, _centroids = cv2.connectedComponentsWithStats(
        strip, connectivity=8
    )
    min_area = config.min_component_area_spaces * spacing * spacing
    # A cell is taller than its own staff, so it catches ink from the staves
    # above and below — on closely-spaced systems their clefs and noteheads
    # land in this crop too, and grouping them in produces one tall blob that
    # looks like nothing. Keep only components CENTRED on this staff's band.
    # Note the test is on the centre, not the extent: a glyph is measured at
    # its true full height afterwards, so a tall G clef still reads as a tall
    # G clef and gets rejected on height, instead of being clipped to the band
    # and passing as a C clef.
    band_margin = config.staff_band_spaces * spacing
    band_top, band_bottom = top_y - band_margin, bottom_y + band_margin
    boxes: list[tuple[int, int, int, int, int]] = []
    for i in range(1, n):  # 0 is background
        area = int(stats[i, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        y_i = int(stats[i, cv2.CC_STAT_TOP])
        h_i = int(stats[i, cv2.CC_STAT_HEIGHT])
        if not (band_top <= y_i + h_i / 2.0 <= band_bottom):
            continue
        boxes.append(
            (
                int(stats[i, cv2.CC_STAT_LEFT]),
                y_i,
                int(stats[i, cv2.CC_STAT_WIDTH]),
                h_i,
                area,
            )
        )

    for bbox in _cluster_components(
        boxes, max_gap=config.cluster_gap_spaces * spacing
    ):
        x, y, w, h = bbox
        w_sp, h_sp = w / spacing, h / spacing
        if x / spacing > config.max_start_spaces:
            # Too far in to be a clef, and everything further right is further
            # still — whatever is at the head of this staff, we didn't find it.
            return None
        if h_sp > config.max_height_spaces or w_sp > config.max_width_spaces:
            # Glyph-sized but bigger than any C clef — overwhelmingly a G clef,
            # which is exactly two-thirds of all clefs. STOP here rather than
            # look past it. Scanning on was the locator's one dangerous bug: a
            # treble clef would be skipped for being too tall and the key
            # signature's sharp behind it — narrow, tall, and beautifully
            # symmetric — would be read as the staff's clef instead.
            return None
        if w_sp < config.min_width_spaces or h_sp < config.min_height_spaces:
            continue  # debris: a fragment, a speck, a rule that survived
        ink = int(np.count_nonzero(strip[y : y + h, x : x + w]))
        if w * h == 0 or ink / float(w * h) < config.min_ink_fraction:
            continue

        if _overlaps_any(bbox, occupied_boxes):
            # The head of this staff is a notehead or a rest, so the clef is
            # not in this cell at all. Stop, exactly as for a G clef.
            return None

        symmetry = _vertical_symmetry(strip, bbox)
        if symmetry < config.min_symmetry:
            # Not a C clef. Stop rather than look further right: whatever sits
            # at the head of the staff is what the clef would have been, and
            # scanning on would only find noteheads to misread.
            return None

        # Hand the measurement to the same resolver the detector path uses, so
        # a located clef is named exactly as a detected one is — the only
        # difference being that here the named line was measured from the ink
        # rather than inferred from a box.
        axis_y = _refine_symmetry_axis(
            strip, bbox, max_shift=config.axis_refine_spaces * spacing
        )
        read = resolve_clef(
            "cClefAlto",
            anchor_y=axis_y,
            staff_line_ys=cell.staff_line_ys_canonical,
            config=geometry,
        )
        if read is None or read.source != "geometry":
            return None  # the snap was ambiguous — abstain
        return LocatedClef(read=read, bbox=bbox, symmetry=round(symmetry, 4))

    return None
