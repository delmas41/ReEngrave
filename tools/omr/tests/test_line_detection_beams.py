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

from tools.omr.line_detection import (
    _stacked_bar_count,
    detect_beams,
    detect_stems,
)
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


class TestStackedBarCountReadsItsOwnComponent:
    """The bar count must read the component's ink, not the box's contents.

    A sloped bar's bounding box is far taller than the bar, so it reaches over
    whatever lies beside it. On Brahms's Violin 2 — a dotted eighth beamed to
    three sixteenths — the primary bar's box (canonical y 1082-1203, 36% filled)
    covered the lower part of the SECONDARY bar, which is a different component.
    Counting runs in the opened image found two runs in 26 of 51 sampled
    columns, the median came out 2, the primary was cut into two equal bands,
    and every note under it gained a beam level.

    Built directly as a label array, because the shape needs a slope steep
    enough to swallow its neighbour and a horizontal opening erodes exactly
    that off a synthetic cell.
    """

    @staticmethod
    def _labels():
        # One sloped bar as label 1, and a second bar as label 2 lying inside
        # label 1's bounding box without touching it.
        labels = np.zeros((200, 400), dtype=np.int32)
        for x in range(400):
            y = 20 + x // 4                 # the sloped primary
            labels[y:y + 12, x] = 1
        for x in range(150, 400):
            y = x // 4                      # the secondary, a clear gap above
            labels[y:y + 12, x] = 2
        return labels

    def test_one_sloped_bar_counts_once_despite_a_neighbour_in_its_box(self):
        labels = self._labels()
        ys, xs = np.nonzero(labels == 1)
        x, y = xs.min(), ys.min()
        w, h = xs.max() - x + 1, ys.max() - y + 1
        assert _stacked_bar_count(labels, 1, int(x), int(y), int(w), int(h)) == 1

    def test_the_neighbour_lies_inside_that_box(self):
        # Guards the fixture itself: without the overlap there is nothing to
        # regress against, and the test above would pass for the wrong reason.
        labels = self._labels()
        ys, _ = np.nonzero(labels == 1)
        ys2, _ = np.nonzero(labels == 2)
        assert ys2.min() < ys.min() + (ys.max() - ys.min())
        assert ys2.max() > ys.min()
        # ...and over MOST of the columns, since the count is a median.
        _, xs1 = np.nonzero(labels == 1)
        _, xs2 = np.nonzero(labels == 2)
        assert len(set(xs2.tolist())) > len(set(xs1.tolist())) / 2

    def test_two_real_bars_in_one_component_still_count_twice(self):
        labels = np.zeros((200, 400), dtype=np.int32)
        for x in range(400):
            labels[40:52, x] = 1
            labels[90:102, x] = 1           # same component, genuinely stacked
        assert _stacked_bar_count(labels, 1, 0, 40, 400, 62) == 2
