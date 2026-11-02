"""ROADMAP 2.252 r2 -- a thick tie lying ON a staff line is not erased with the line (`OMR_ARC_LINE_THICKNESS`, default OFF).

Sean's 2.252 tiles 3, 5, 6, 7 (Litolff): ties along a line were refused `ink_is_a_staff_line` because the line's stroke was grown
by how full the box's rows were, and a flat tie beside the line fills those rows too. With the flag the stroke is the staff's own
measured thickness, found on the page rows around the line (a box cut at the line's edge holds only part of it).
Controls that can fail: a box that is only a thick staff line still holds nothing curved, with the flag."""
from __future__ import annotations

import os
import unittest

import numpy as np

from tools.omr.staged import gather as G

SP = 16.0
LINES = [100.0 + SP * i for i in range(5)]


def _blank(h=300, w=600):
    return np.full((h, w), 255, np.uint8)


def _staff(img, thick=5):
    for y in LINES:
        img[int(y) - thick // 2:int(y) - thick // 2 + thick, :] = 0


def _flat_tie_on_line(img, x0, x1, y_top, thick=6):
    """A thick tie whose body lies flat on a line's top edge `y_top` for most of its width and rises only at its left end (Litolff
    p2 `2/1/3/12/3`: the five rows above the line are 53-68% ink)."""
    for x in range(x0, x1):
        t = (x - x0) / (x1 - x0)
        bottom = int(round(y_top - 1 - max(0.0, 0.3 - t) * 40))
        img[bottom - thick + 1:bottom + 1, x] = 0


class TestThickTieOnALine(unittest.TestCase):

    def setUp(self):
        self.img = _blank()
        _staff(self.img)
        _flat_tie_on_line(self.img, 100, 180, int(LINES[1]) - 2)
        self.box = (100, LINES[1] - 18, 180, LINES[1] + 4)

    def test_off_the_fill_grown_stroke_erases_the_tie(self):        # the fault, reproduced
        m = G.arc_ink_shape(self.img, self.box, SP, LINES)
        self.assertLess(m["coverage"], 0.35)

    def test_with_the_measured_thickness_the_tie_survives(self):
        m = G.arc_ink_shape(self.img, self.box, SP, LINES, line_thickness=[5.0] * 5)
        self.assertGreater(m["coverage"], 0.6)

    def test_a_box_that_is_only_a_line_still_holds_nothing(self):    # the control that can fail
        img = _blank()
        _staff(img, thick=6)
        m = G.arc_ink_shape(img, (100, LINES[1] - 5, 300, LINES[1] + 5), SP, LINES, line_thickness=[6.0] * 5)
        self.assertEqual(m["coverage"], 0.0)

    def test_a_line_just_outside_the_box_is_found_on_the_page_not_on_the_tie(self):
        """The box ends one pixel above a line: snapping inside the box would land on the tie and erase it."""
        img = _blank()
        _staff(img)
        _flat_tie_on_line(img, 100, 180, int(LINES[2]) - 2)
        box = (100, LINES[2] - 24, 180, LINES[2] - 2)
        self.assertLess(G.arc_ink_shape(img, box, SP, LINES)["coverage"], 0.35)       # OFF: snapped onto the tie (2/1/4/11/4)
        self.assertGreater(G.arc_ink_shape(img, box, SP, LINES, line_thickness=[5.0] * 5)["coverage"], 0.6)

    def test_flag_default_off(self):
        old = os.environ.pop(G.ARC_LINE_THICKNESS_ENV, None)
        try:
            self.assertFalse(G.arc_line_thickness_enabled())
            os.environ[G.ARC_LINE_THICKNESS_ENV] = "1"
            self.assertTrue(G.arc_line_thickness_enabled())
        finally:
            os.environ.pop(G.ARC_LINE_THICKNESS_ENV, None)
            if old is not None:
                os.environ[G.ARC_LINE_THICKNESS_ENV] = old


if __name__ == "__main__":
    unittest.main()
