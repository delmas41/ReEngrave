"""Beam detection: what makes a horizontal line a beam is the stems on it.

Synthetic cells, so these run without LilyPond or a PDF. Each shape here is one
the reference sheet or a real page actually produced:

  * a sloped beam, which used to be counted two to eight times because the
    stacked-bar count came from the bounding box's HEIGHT, and a sloped bar has
    a tall box;
  * a slur, a tie, a ledger line and a staff-line fragment, which are all long
    horizontal ink and were all counted as beams — one Mahler cell of half
    notes under slurs reported 27.
"""

from __future__ import annotations

import cv2
import numpy as np

from tools.omr.line_detection import detect_beams, detect_stems
from tools.omr.types import MeasureCell


SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]
BEAM_H = int(0.48 * SPACING)


def _cell(paint, width: int = 900) -> MeasureCell:
    img = np.full((800, width), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, width, 800),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _stem(img, x: int, y_top: int, y_bot: int) -> None:
    img[y_top:y_bot, x - 5:x + 5] = 0


def _beamed_pair(img, x0: int, x1: int, y_top: int, slope: int = 0, bars: int = 1):
    """Two stems joined at the top by `bars` beam bars, optionally sloped."""
    _stem(img, x0, y_top, y_top + int(3.5 * SPACING))
    _stem(img, x1, y_top + slope, y_top + slope + int(3.5 * SPACING))
    for b in range(bars):
        off = b * int(0.75 * SPACING)
        pts = np.array([
            [x0 - 5, y_top + off], [x1 + 5, y_top + slope + off],
            [x1 + 5, y_top + slope + off + BEAM_H], [x0 - 5, y_top + off + BEAM_H],
        ], dtype=np.int32)
        cv2.fillPoly(img, [pts], 0)


class TestBeamsNeedStems:

    def test_a_beamed_pair_is_one_beam(self):
        cell = _cell(lambda img: _beamed_pair(img, 300, 550, 150))
        assert len(detect_beams(cell)) == 1

    def test_a_slur_between_noteheads_is_not_a_beam(self):
        """A slur is long and horizontal and joins noteheads, not stem ends."""
        def paint(img):
            cv2.ellipse(img, (300, 300), (60, 50), 0, 0, 360, 0, -1)
            cv2.ellipse(img, (600, 300), (60, 50), 0, 0, 360, 0, -1)
            cv2.ellipse(img, (450, 380), (150, 40), 0, 180, 360, 0, 12)
        assert detect_beams(_cell(paint)) == []

    def test_a_bare_horizontal_line_is_not_a_beam(self):
        """Staff-line residue: long, horizontal, and nothing hangs off it."""
        def paint(img):
            img[300:310, 100:800] = 0
        assert detect_beams(_cell(paint)) == []

    def test_a_ledger_line_through_a_stemmed_note_is_not_a_beam(self):
        """One stem is not enough — a beam joins two."""
        def paint(img):
            cv2.ellipse(img, (400, 620), (62, 50), 0, 0, 360, 0, -1)
            img[610:626, 320:480] = 0                      # the ledger line
            _stem(img, 455, 620 - int(3.5 * SPACING), 620)
        assert detect_beams(_cell(paint)) == []


class TestStackedAndSlopedBars:

    def test_a_sloped_beam_counts_once(self):
        """The regression: a sloped bar's bounding box is tall, and dividing
        that height by a beam's thickness reported it as several bars."""
        cell = _cell(lambda img: _beamed_pair(img, 250, 650, 150, slope=120))
        found = detect_beams(cell)
        assert len(found) == 1, f"a single sloped beam counted {len(found)} times"

    def test_a_double_beam_counts_twice(self):
        cell = _cell(lambda img: _beamed_pair(img, 300, 600, 150, bars=2))
        assert len(detect_beams(cell)) == 2

    def test_a_sloped_double_beam_still_counts_twice(self):
        cell = _cell(lambda img: _beamed_pair(img, 250, 650, 150, slope=100, bars=2))
        assert len(detect_beams(cell)) == 2

    def test_stems_can_be_supplied_to_avoid_a_second_detection(self):
        cell = _cell(lambda img: _beamed_pair(img, 300, 550, 150))
        stems = detect_stems(cell)
        assert detect_beams(cell, stems=stems) == detect_beams(cell)


class TestOnlyFullLengthStemsAnchorABeam:
    """`detect_stems` accepts anything from 2 staff spaces up, and at that floor
    it also picks up the vertical strokes of sharps and naturals. Those false
    stems used to lend their two-stem quorum to whatever horizontal ink lay near
    them: on a hand-labeled Mahler cell holding no beams at all, five ledger
    lines were reported as beams because the accidentals beside them counted.
    """

    def test_two_short_verticals_do_not_make_a_ledger_line_a_beam(self):
        def paint(img):
            # A ledger line with two accidental-height strokes beside it, the
            # shape that produced the false positives.
            img[600:616, 300:500] = 0
            for x in (330, 470):
                img[500:500 + int(2.2 * SPACING), x - 5:x + 5] = 0
        assert detect_beams(_cell(paint)) == []

    def test_the_same_line_with_full_length_stems_is_a_beam(self):
        """The veto is about stem LENGTH, not about being a horizontal line."""
        def paint(img):
            img[600:616, 300:500] = 0
            for x in (330, 470):
                img[600 - int(3.5 * SPACING):600, x - 5:x + 5] = 0
        assert len(detect_beams(_cell(paint))) == 1

    def test_the_anchor_floor_can_be_relaxed_by_the_caller(self):
        def paint(img):
            img[600:616, 300:500] = 0
            for x in (330, 470):
                img[500:500 + int(2.2 * SPACING), x - 5:x + 5] = 0
        cell = _cell(paint)
        assert detect_beams(cell) == []
        assert len(detect_beams(cell, stem_anchor_min_height_lines=1.5)) == 1
