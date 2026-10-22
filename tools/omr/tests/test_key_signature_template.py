"""The template key-signature reader, and the two rules that keep it honest."""
from __future__ import annotations

import cv2
import numpy as np

from tools.omr.key_signature_template import (
    DEFAULT_TEMPLATE_CONFIG,
    _templates,
    read_key_signature,
)
from tools.omr.key_signature_vote import StaffCandidate, reconcile
from tools.omr.types import MeasureCell

CELL_W, CELL_H = 700, 400
SPACING = 24
STAFF_LINES = [140, 164, 188, 212, 236]


def _blank() -> np.ndarray:
    img = np.full((CELL_H, CELL_W), 255, dtype=np.uint8)
    for y in STAFF_LINES:
        cv2.line(img, (0, y), (CELL_W - 1, y), 0, 2)
    return img


def _paste(img: np.ndarray, smufl_name: str, x: int, position: float,
           height_spaces: float = 2.8) -> None:
    """Draw a library glyph with its box centred `position` steps below the top
    staff line — the unit the slot tables use."""
    glyph = _templates(DEFAULT_TEMPLATE_CONFIG.template_em_px)[smufl_name]
    height = int(round(height_spaces * SPACING))
    width = max(2, int(round(glyph.shape[1] * height / glyph.shape[0])))
    scaled = cv2.resize(glyph, (width, height), interpolation=cv2.INTER_AREA)
    centre = STAFF_LINES[0] + position * (SPACING / 2.0)
    y0 = int(round(centre - height / 2.0))
    region = img[y0:y0 + height, x:x + width]
    if region.shape != scaled.shape:
        return
    region[:] = np.minimum(region, 255 - scaled)


def _cell(img: np.ndarray) -> MeasureCell:
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=-1,
        image=img, image_no_staff=img,
        bbox_page_px=(0, 0, CELL_W, CELL_H),
        staff_line_ys_canonical=list(STAFF_LINES),
        upscale_factor=1.0,
    )


#: Treble flat slots, in steps below the top line: B4 -> 4, E5 -> 1, A4 -> 5.
TREBLE_FLATS = (4.0, 1.0, 5.0)


def _three_flats() -> np.ndarray:
    img = _blank()
    _paste(img, "gClef", 40, 4.0, height_spaces=7.0)
    for i, position in enumerate(TREBLE_FLATS):
        _paste(img, "accidentalFlat", 150 + i * 34, position)
    return img


class TestReads:
    def test_three_flats_after_a_clef(self):
        read = read_key_signature(_cell(_three_flats()), "treble")
        assert read is not None and read.fifths == -3

    def test_one_flat(self):
        img = _blank()
        _paste(img, "gClef", 40, 4.0, height_spaces=7.0)
        _paste(img, "accidentalFlat", 150, TREBLE_FLATS[0])
        read = read_key_signature(_cell(img), "treble")
        assert read is not None and read.fifths == -1

    def test_empty_header_is_a_reading_of_no_signature(self):
        img = _blank()
        _paste(img, "gClef", 40, 4.0, height_spaces=7.0)
        read = read_key_signature(_cell(img), "treble")
        assert read is not None and read.fifths == 0

    def test_no_clef_no_reading(self):
        # The slot table is chosen by the clef; without one there is nothing to
        # fit against, and a signature fitted to a guess is a guess squared.
        assert read_key_signature(_cell(_three_flats()), None) is None


class TestDoesNotInfer:
    def test_a_fit_that_recovers_an_unseen_accidental_is_refused(self):
        # Drawn as the SECOND and THIRD flats of a treble signature with nothing
        # at the first slot. `fit_key_signature` would recover the missing one
        # and call it three flats; this reader must not, because its own failure
        # mode is over-counting, not under-counting. See WTC I p.17 in the
        # module docstring.
        img = _blank()
        _paste(img, "gClef", 40, 4.0, height_spaces=7.0)
        for i, position in enumerate(TREBLE_FLATS[1:]):
            _paste(img, "accidentalFlat", 150 + i * 34, position)
        read = read_key_signature(_cell(img), "treble")
        assert read is None or not read.inferred_slots


class TestDoesNotCarry:
    def _cands(self, can_carry):
        # Two systems of two staves. The top staff reads 4 sharps in three
        # systems' worth of evidence and 5 in one — the WTC failure in
        # miniature, where the 5 was carried onto every other system.
        out = []
        for system in range(4):
            fifths = 5 if system == 0 else 4
            out.append(StaffCandidate(
                staff_index=system * 2, system_index=system, ordinal=0,
                fifths=fifths, weight=float(abs(fifths)),
                source="template" if system == 0 else "detector",
                can_carry=can_carry if system == 0 else True,
            ))
            out.append(StaffCandidate(
                staff_index=system * 2 + 1, system_index=system, ordinal=1,
                fifths=4, weight=4.0, source="detector",
            ))
        return out

    def test_a_carrying_reading_spreads_its_error(self):
        verdicts = reconcile(self._cands(can_carry=True)).verdicts
        assert verdicts[2].fifths == 5, "the spurious 5 reached another system"

    def test_a_non_carrying_one_does_not(self):
        verdicts = reconcile(self._cands(can_carry=False)).verdicts
        assert verdicts[2].fifths == 4
        assert verdicts[6].fifths == 4
