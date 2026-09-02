"""Find a staff's key-signature accidentals by matching glyphs, not clustering ink.

`key_signature_locator` finds accidentals by thresholding the header to an ink
mask, clustering connected components, and keeping the accidental-sized ones.
That works on clean engraving and falls apart on a degraded scan, where the
staff-line removal leaves each glyph in pieces: on page 1 of the IMSLP
Beethoven 5, GIVEN the correct clef for every staff, it reads 2 of the 12 — and
eight of the ten it misses print three flats plainly enough to read by eye.

This finds them the way `time_signature_locator` finds a meter: by sliding the
Bravura `accidentalFlat` and `accidentalSharp` templates the symbol library
already ships. A shattered glyph still correlates with its own outline; it just
does not survive being reassembled from components.

## The search is bounded on both sides, and that is most of the work

Matched over a whole header, a flat's outline correlates with all sorts of
things — most of all with the clef, which produced a column of eleven "flats"
at one x, scoring 0.57 to 0.59 against the real flats' 0.65 to 0.76. Too close
to separate by score.

So the window is closed to what is between the clef and the meter:

  *left* — the clef's own template is matched (the caller supplies which clef,
  so there is one template to try) and the search starts past its right edge;
  *right* — `time_signature_locator.locate_time_signature` says where the meter
  begins, so its digits cannot be read as accidentals.

Both bounds come from glyphs this repo can already find. Within them, one
candidate is kept per x-column, because a key signature prints one accidental
per column and a stack at a single x is something else.

## Positions are taken from the ink, not the box

`fit_key_signature` solves for a constant anchor offset across the run, so what
matters is the SPACING between accidentals, not where a glyph's box sits. Using
the matched box's centre leaves ±0.5 step of jitter in that spacing, which is
enough for the fit to prefer a five-flat reading of three flats: two of the
twelve staves here read -5 that way. Taking the centroid of the ink inside the
matched box instead fixes both. The remaining error is what the cross-staff vote
in `key_signature_vote` is for.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np

from tools.omr.header_ink import staff_metrics
from tools.omr.key_signature_geometry import KeySignatureRead, fit_key_signature
from tools.omr.symbol_library.loader import SymbolLibrary
from tools.omr.time_signature_locator import locate_time_signature
from tools.omr.types import MeasureCell

#: Which clef template bounds the search on the left. Every C clef is the same
#: glyph on a different line, so they share one entry.
CLEF_GLYPHS = {
    "treble": "gClef", "bass": "fClef",
    "alto": "cClef", "tenor": "cClef", "soprano": "cClef",
    "mezzosoprano": "cClef", "baritone": "cClef",
}

ACCIDENTAL_GLYPHS = (("b", "accidentalFlat"), ("#", "accidentalSharp"))


@dataclass(frozen=True)
class KeySignatureTemplateConfig:
    #: Bravura em size to take templates at; the em is four staff spaces.
    template_em_px: int = 120

    #: Minimum NCC for an accidental. Real accidentals on the scan measured
    #: 0.65-0.76 and the clef's best impersonation 0.59 — but the clef is
    #: excluded by the left bound, so this is not the thing keeping it out, and
    #: the reading is unchanged anywhere in 0.50-0.60.
    min_score: float = 0.55

    #: Minimum NCC before a clef match is trusted to place the left bound. Below
    #: it the search starts at the window's left edge and the run-fit has to
    #: cope alone.
    clef_min_score: float = 0.40

    #: Two matches closer than this in x are the same glyph. A key signature
    #: prints one accidental per column.
    column_merge_spaces: float = 0.7


DEFAULT_TEMPLATE_CONFIG = KeySignatureTemplateConfig()


@lru_cache(maxsize=4)
def _templates(em_px: int) -> dict[str, np.ndarray]:
    """Ink-positive rasters for the clefs and accidentals, by SMuFL name."""
    wanted = set(CLEF_GLYPHS.values()) | {name for _sign, name in ACCIDENTAL_GLYPHS}
    library = SymbolLibrary.load()
    return {
        entry.smufl_name: (255 - entry.load_image()).astype(np.uint8)
        for entry in library.entries
        if entry.smufl_name in wanted and entry.size_px == em_px
    }


def _ink_centre_y(ink: np.ndarray, box: tuple[int, int, int, int]) -> float:
    """Vertical centroid of the ink inside a matched box. See the module note on
    why this and not the box's own centre."""
    x, y, w, h = box
    patch = ink[y:y + h, x:x + w] > 96
    total = float(patch.sum())
    if total <= 0:
        return y + h / 2.0
    rows = np.arange(h, dtype=float)[:, None]
    return y + float((rows * patch).sum() / total)


def read_key_signature(
    cell: MeasureCell,
    clef: str | None,
    *,
    config: KeySignatureTemplateConfig = DEFAULT_TEMPLATE_CONFIG,
) -> KeySignatureRead | None:
    """Read this staff's key signature from its header cell, or return None.

    `clef` chooses both the slot table the accidentals are fitted to and the
    template that bounds the search on the left, so without one there is no
    reading — the same rule `key_signature_locator` follows, and for the same
    reason: a signature fitted against a guessed clef is a guess squared.

    Returns a `KeySignatureRead` with `fifths` 0 when the window between clef
    and meter is clean — that is a positive reading of "no signature here", not
    an abstention.
    """
    if not clef:
        return None
    metrics = staff_metrics(cell)
    if metrics is None:
        return None
    spacing, top_y, _bottom_y = metrics
    if spacing <= 0:
        return None

    image = cell.image_no_staff if cell.image_no_staff is not None else cell.image
    if image is None:
        return None
    if image.ndim == 3:
        image = image[:, :, 0]

    space = config.template_em_px / 4.0
    scale = space / spacing
    ink = cv2.resize((255 - image).astype(np.uint8), None, fx=scale, fy=scale,
                     interpolation=cv2.INTER_AREA)
    templates = _templates(config.template_em_px)

    def _fits(template: np.ndarray) -> bool:
        return (template.shape[0] <= ink.shape[0]
                and template.shape[1] <= ink.shape[1])

    # Left bound: past the clef.
    x_lo = 0
    clef_glyph = templates.get(CLEF_GLYPHS.get(clef, ""))
    if clef_glyph is not None and _fits(clef_glyph):
        response = cv2.matchTemplate(ink, clef_glyph, cv2.TM_CCOEFF_NORMED)
        _, score, _, location = cv2.minMaxLoc(response)
        if score >= config.clef_min_score:
            x_lo = location[0] + clef_glyph.shape[1]

    # Right bound: before the meter, when there is one to find.
    x_hi = ink.shape[1]
    meter = locate_time_signature(cell)
    if meter is not None:
        x_hi = min(x_hi, int(round(meter.x_canonical * scale)))
    if x_hi <= x_lo:
        return None

    candidates: list[tuple[float, int, int, int, int, str]] = []
    for sign, glyph_name in ACCIDENTAL_GLYPHS:
        template = templates.get(glyph_name)
        if template is None or not _fits(template):
            continue
        response = cv2.matchTemplate(ink, template, cv2.TM_CCOEFF_NORMED)
        height, width = template.shape
        ys, xs = np.where(response >= config.min_score)
        for y, x in zip(ys, xs):
            if x < x_lo or x + width > x_hi:
                continue
            candidates.append((float(response[y, x]), int(x), int(y), width, height, sign))

    # One accidental per column, best match first.
    candidates.sort(reverse=True)
    merge = config.column_merge_spaces * space
    kept: list[tuple[float, int, int, int, int, str]] = []
    for candidate in candidates:
        if all(abs(candidate[1] - other[1]) > merge for other in kept):
            kept.append(candidate)
    if not kept:
        # Nothing between clef and meter: the staff prints no signature.
        return KeySignatureRead(0, None, (), (), 0.0, 0.0)

    kept.sort(key=lambda c: c[1])
    signs = [c[5] for c in kept]
    dominant = max(set(signs), key=signs.count)
    run = [c for c in kept if c[5] == dominant]

    half = space / 2.0
    top_scaled = top_y * scale
    positions = [
        (_ink_centre_y(ink, (c[1], c[2], c[3], c[4])) - top_scaled) / half
        for c in run
    ]
    read = fit_key_signature(positions, clef, dominant)
    if read is not None and read.inferred_slots:
        # This reader does not get to recover a glyph it did not see.
        #
        # `fit_key_signature` will fill in slots nothing was detected at, which
        # is right for the CV locator — that one loses accidentals to broken ink
        # and cannot invent them. This one fails the other way round: a spurious
        # match adds an accidental, and inference then compounds it into a
        # signature nobody printed. Measured on WTC I p.17, four sharps on every
        # staff: five matches on one staff were fitted as SEVEN sharps, and with
        # that reading allowed to outrank the detector the page went from 10
        # correct to 5 correct and 5 wrong.
        #
        # Refusing to infer turns that failure into an abstention, which the
        # detector or the locator is then free to answer.
        return None
    return read
