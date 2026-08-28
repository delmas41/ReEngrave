"""Stem detection: the notehead must not take its own stem down with it.

Synthetic cells, so these run without LilyPond or a PDF. The shape under test
is the one the LilyPond ground-truth sheet exposed: a notehead is exactly one
staff space tall, so an opening kernel of one staff space leaves it standing,
still joined to its stem, and the component comes out as wide as the notehead.
The width filter then rejects the stem.

That stayed invisible while staff-line removal was a no-op — an un-removed
staff line broke the notehead up as a side effect — so these tests build the
cell WITHOUT staff lines, the way a working removal pass now leaves it.
"""

from __future__ import annotations

import numpy as np
import pytest

from tools.omr.line_detection import STEM_KERNEL_MARGIN, detect_stems
from tools.omr.types import MeasureCell


SPACING = 100
LINE_YS = [100, 200, 300, 400, 500]


def _cell(paint, width: int = 900) -> MeasureCell:
    img = np.full((700, width), 255, dtype=np.uint8)
    paint(img)
    return MeasureCell(
        page_index=0, system_index=0, staff_index=0, measure_index=0,
        image=img, image_no_staff=img.copy(), bbox_page_px=(0, 0, width, 700),
        staff_line_ys_canonical=list(LINE_YS), upscale_factor=1.0,
    )


def _note(img, x: int, head_y: int, stem_up: bool = True) -> None:
    """A filled notehead one staff space tall, with a stem 3.5 spaces long."""
    import cv2
    cv2.ellipse(img, (x, head_y), (int(SPACING * 0.62), SPACING // 2), 0, 0, 360, 0, -1)
    sx = x + int(SPACING * 0.55) if stem_up else x - int(SPACING * 0.55)
    y0, y1 = (head_y - int(3.5 * SPACING), head_y) if stem_up else (head_y, head_y + int(3.5 * SPACING))
    img[max(0, y0):y1, sx - 5:sx + 5] = 0


class TestStemVsNotehead:

    def test_a_note_yields_exactly_one_stem(self):
        cell = _cell(lambda img: _note(img, 400, 450))
        found = detect_stems(cell)
        assert len(found) == 1, f"expected 1 stem, got {len(found)}"

    def test_the_stem_is_not_widened_by_its_notehead(self):
        """The regression: the component must be stem-wide, not notehead-wide."""
        cell = _cell(lambda img: _note(img, 400, 450))
        found = detect_stems(cell)
        assert found, "the stem was rejected — the notehead widened the component"
        assert found[0].width_canonical < SPACING * 0.6

    def test_several_notes_yield_several_stems(self):
        def paint(img):
            for i, x in enumerate((250, 450, 650)):
                _note(img, x, 400 + 40 * i)
        cell = _cell(paint)
        assert len(detect_stems(cell)) == 3

    def test_a_stemless_notehead_yields_nothing(self):
        import cv2
        def paint(img):
            cv2.ellipse(img, (400, 350), (int(SPACING * 0.62), SPACING // 2), 0, 0, 360, 0, -1)
        assert detect_stems(_cell(paint)) == []

    def test_down_stems_are_found_too(self):
        cell = _cell(lambda img: _note(img, 400, 250, stem_up=False))
        assert len(detect_stems(cell)) == 1

    def test_the_kernel_stays_below_the_minimum_stem_height(self):
        """A component shorter than min_height_lines is rejected anyway, so the
        kernel may grow up to that floor — but not past it, or it would erase
        stems the filter would have accepted."""
        assert 0 < STEM_KERNEL_MARGIN < 1.0

    def test_a_short_stem_at_the_accepted_floor_survives(self):
        """A stem of exactly min_height_lines must not be erased by the opening."""
        def paint(img):
            import cv2
            cv2.ellipse(img, (400, 500), (int(SPACING * 0.62), SPACING // 2), 0, 0, 360, 0, -1)
            img[500 - 2 * SPACING:500, 450:460] = 0     # exactly 2.0 spaces
        found = detect_stems(_cell(paint))
        assert len(found) == 1


class TestAccidentalStrokesAreNotStems:
    """A sharp and a natural are each two parallel verticals about half a staff
    space apart and roughly two spaces tall — which passes every shape filter a
    stem passes. What separates them is that they come in PAIRS: two noteheads a
    second apart share one stem rather than standing side by side, and
    successive notes are set further apart than an accidental's own strokes.

    Measured on 14 hand-counted cells, this was most of the stem error (summed
    |error| 60 -> 24), and on the LilyPond reference sheet it took the count
    from +7 to -1 against a truth of 48.
    """

    @staticmethod
    def _sharp(img, x: int, y_centre: int) -> None:
        """Two verticals 0.55 spaces apart, two spaces tall — a sharp's strokes."""
        h = int(2.0 * SPACING)
        for dx in (0, int(0.55 * SPACING)):
            img[y_centre - h // 2:y_centre + h // 2, x + dx - 4:x + dx + 4] = 0

    def test_a_lone_sharp_yields_no_stems(self):
        cell = _cell(lambda img: self._sharp(img, 300, 300))
        assert detect_stems(cell) == []

    def test_a_sharp_beside_a_note_leaves_only_the_note_s_stem(self):
        def paint(img):
            self._sharp(img, 250, 300)
            _note(img, 500, 400)
        found = detect_stems(_cell(paint))
        assert len(found) == 1
        assert found[0].x_canonical > 450, "the surviving stroke should be the note's"

    def test_two_notes_a_normal_distance_apart_both_survive(self):
        """The rule must not eat real stems: consecutive notes are set further
        apart than an accidental's strokes."""
        def paint(img):
            _note(img, 300, 400)
            _note(img, 300 + int(1.6 * SPACING), 400)
        assert len(detect_stems(_cell(paint))) == 2

    def test_the_rule_can_be_switched_off(self):
        cell = _cell(lambda img: self._sharp(img, 300, 300))
        assert len(detect_stems(cell, drop_accidental_pairs=False)) == 2
