"""Tests for the CV key-signature locator's ANCHOR
(`tools/omr/key_signature_locator.locate_key_signature`).

The locator's premise is positional: a key signature is printed hard against
its clef, so "where the clef ends" is what separates a signature from the
music behind it. These tests are about that anchor, because it is where the
locator goes wrong when the geometry around it moves.

Cells are drawn rather than loaded, so the whole path runs — rule stripping,
staff-line tracing, clustering, the slot fit. The accidentals are drawn as
plain bars at the right POSITIONS rather than as font glyphs: the module reads
positions, and a synthetic Bravura outline would test the drawing, not the
reading.
"""

from __future__ import annotations

import cv2
import numpy as np

from tools.omr.key_signature_locator import (
    DEFAULT_LOCATOR_CONFIG,
    locate_key_signature,
)
from tools.omr.types import MeasureCell

SPACING = 20
STAFF_LINES = [100, 120, 140, 160, 180]   # top line … bottom line
CELL_H, CELL_W = 340, 420


def _blank() -> np.ndarray:
    img = np.full((CELL_H, CELL_W), 255, dtype=np.uint8)
    for y in STAFF_LINES:
        cv2.line(img, (0, y), (CELL_W - 1, y), 0, 2)
    return img


# A clef stand-in: tall enough to be oversized (>= clef_min_height_spaces),
# narrow enough that `erase_staff_lines` bridges it back together where the
# lines cross it (its 1.2-space bridge limit), and short enough not to be taken
# for a heavy system rule (header_ink strips those at 5 spaces). Real clefs sit
# inside all three bounds; a solid block that does not is a fixture artefact.
CLEF_X, CLEF_W = 24, 22
CLEF_TOP, CLEF_BOTTOM = 66, 156


def _draw_treble_clef(img: np.ndarray, x: int = CLEF_X) -> None:
    cv2.rectangle(img, (x, CLEF_TOP), (x + CLEF_W, CLEF_BOTTOM), 0, -1)


def _draw_flat(img: np.ndarray, x: int, pos: float) -> None:
    """A flat whose BOX CENTRE sits at `pos` diatonic steps below the top line.

    Position is what the fit reads, so that is what the fixture controls.
    """
    cy = int(round(STAFF_LINES[0] + pos * (SPACING / 2.0)))
    cv2.rectangle(img, (x, cy - 14), (x + 12, cy + 14), 0, -1)


def _draw_beam(img: np.ndarray, x: int) -> None:
    """A beam: far too wide to be an accidental, far too flat to be a clef.

    Under the old rule this counted as "the clef" simply for being oversized,
    and dragged the anchor to it.
    """
    cv2.rectangle(img, (x, 150), (x + 90, 162), 0, -1)


def _cell(img: np.ndarray) -> MeasureCell:
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=-1,
        image=img, image_no_staff=None,
        bbox_page_px=(0, 0, CELL_W, CELL_H),
        staff_line_ys_canonical=list(STAFF_LINES),
        upscale_factor=1.0,
    )


# Treble flat slots, in steps below the top line: B4 → 4, E5 → 1, A4 → 5.
TREBLE_FLAT_POS = [4.0, 1.0, 5.0]


def _three_flats(x0: int = 62) -> np.ndarray:
    img = _blank()
    _draw_treble_clef(img)
    for i, pos in enumerate(TREBLE_FLAT_POS):
        _draw_flat(img, x0 + i * 22, pos)
    return img


class TestReadsASignature:
    def test_three_flats_after_a_clef(self):
        # The fixture has to work before any of the abstention tests mean
        # anything: without this they would pass on a locator that never reads.
        located = locate_key_signature(_cell(_three_flats()), "treble")
        assert located is not None
        assert located.read.fifths == -3


class TestClefAnchor:
    def test_a_beam_deeper_in_the_bar_is_not_the_clef(self):
        """The regression this gate exists for.

        `clef_right` used to be the max over every oversized cluster, so a beam
        two thirds of the way across the window became "the clef" and the
        "printed hard against the clef" rule then licensed the ink beside it as
        a key signature. Measured on Beethoven 6 p.2, that put the anchor at
        14.5 of 16 staff spaces and read two noteheads as three flats.
        """
        img = _blank()
        _draw_treble_clef(img)
        _draw_beam(img, 250)
        # Accidental-sized ink just past the beam, at positions that DO fit a
        # signature — flat slots 1 and 3, which is the shape that read as three
        # flats on the real page. Only the anchor can reject this.
        _draw_flat(img, 350, TREBLE_FLAT_POS[0])
        _draw_flat(img, 372, TREBLE_FLAT_POS[2])
        assert locate_key_signature(_cell(img), "treble") is None

    def test_a_signature_is_still_read_when_a_beam_follows_it(self):
        # The complement: rejecting the beam as an anchor must not reject the
        # signature that is genuinely there in front of it.
        img = _three_flats()
        _draw_beam(img, 250)
        located = locate_key_signature(_cell(img), "treble")
        assert located is not None
        assert located.read.fifths == -3

    def test_no_clef_means_no_reading(self):
        """A `clef_right` of 0 is "no anchor", not "the anchor is at x=0".

        Read the other way it put the search window at the very left of the
        cell — over the bracket, the initial rule and the instrument name —
        which is where a bass staff's margin ink was read as one sharp. So the
        ink here is drawn hard against x=0, which is where that window sat.
        """
        img = _blank()
        for i, pos in enumerate(TREBLE_FLAT_POS):
            _draw_flat(img, 6 + i * 22, pos)   # accidental-sized, but no clef
        assert locate_key_signature(_cell(img), "treble") is None

    def test_a_clef_split_in_two_still_anchors_past_all_of_it(self):
        # Thick prints break a clef into pieces. Both are at the head of the
        # window, so the anchor is the far edge of the LAST one, not the first.
        img = _blank()
        cv2.rectangle(img, (16, CLEF_TOP), (16 + 10, CLEF_BOTTOM), 0, -1)
        cv2.rectangle(img, (32, CLEF_TOP), (32 + 14, CLEF_BOTTOM), 0, -1)
        for i, pos in enumerate(TREBLE_FLAT_POS):
            _draw_flat(img, 62 + i * 22, pos)
        located = locate_key_signature(_cell(img), "treble")
        assert located is not None
        assert located.read.fifths == -3

    def test_the_anchor_must_stand_at_the_head_of_the_window(self):
        # A clef-shaped cluster far into the bar is not this staff's clef.
        img = _blank()
        _draw_treble_clef(
            img,
            x=int(DEFAULT_LOCATOR_CONFIG.clef_anchor_max_start_spaces * SPACING) + 30,
        )
        for i, pos in enumerate(TREBLE_FLAT_POS):
            _draw_flat(img, 300 + i * 22, pos)
        assert locate_key_signature(_cell(img), "treble") is None


class TestFragmentedClef:
    """A clef cut up by staff-line erasure is still a clef.

    On a degraded print the clef does not survive erasure in one piece: it
    breaks into accidental-sized fragments, they join the run ahead of the real
    signature, and the fit then fails over a run that is half clef. Measured on
    Beethoven 5 p.15 staff 7, whose three flats sit at slot positions 3.91, 1.01
    and 4.96 against a treble table of 4, 1, 5 — correctly placed, correctly
    ordered, and unread.

    The tail pass reads them. What keeps it from undoing the anchor rule is the
    evidence it demands: ink at the HEAD of the window taller than any
    accidental. `TestClefAnchor` above draws the two cases that must stay
    silent — no clef at all, and a clef far into the bar — and they do.
    """

    @staticmethod
    def _fragmented_clef(img):
        """A clef in three pieces, none tall enough to anchor on its own, the
        tallest still taller than an accidental."""
        cv2.rectangle(img, (CLEF_X, 70), (CLEF_X + CLEF_W, 112), 0, -1)
        cv2.rectangle(img, (CLEF_X, 118), (CLEF_X + CLEF_W, 134), 0, -1)
        cv2.rectangle(img, (CLEF_X, 140), (CLEF_X + CLEF_W, 156), 0, -1)

    def test_a_signature_after_a_fragmented_clef_is_read(self):
        img = _blank()
        self._fragmented_clef(img)
        for i, pos in enumerate(TREBLE_FLAT_POS):
            _draw_flat(img, 90 + i * 26, pos)
        found = locate_key_signature(_cell(img), "treble")
        assert found is not None, "three flats, correctly placed, after a clef"
        assert found.read.fifths == -3

    def test_the_head_must_still_carry_something_clef_tall(self):
        """The same three flats with no clef at all stay unread — this is
        `TestClefAnchor`'s rule, restated against the tail path."""
        img = _blank()
        for i, pos in enumerate(TREBLE_FLAT_POS):
            _draw_flat(img, 90 + i * 26, pos)
        assert locate_key_signature(_cell(img), "treble") is None
