"""ROADMAP 2.252 r6 (STAGED; rides `OMR_HEAD_HOLE_POSITION`, default OFF): a staff line found LOCALLY through an arc box on a tilted
staff (Sean's r5 tile 10: a 'tie' box on the fourth line kept as an arc), and a head whose own two readings name two positions."""
import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather as G
from tools.omr.staged import head_hole_position as HP

SP = 16.0


def _page_with_line(y_line: int, w: int = 200, h: int = 120):
    img = np.full((h, w), 255, dtype=np.uint8)
    img[y_line - 1:y_line + 2, :] = 0                  # a 3 px staff line across the page
    return img


class TestArcBoxOnATiltedLine(unittest.TestCase):
    """The staff-wide line ys stand 6-8 px off the line at the box's x; the box is a 5 px sliver ON the line."""

    def setUp(self):
        self.img = _page_with_line(60)
        self.box = (40.0, 57.5, 100.0, 62.5)             # the line inside, a 'tie' box 0.31 sp tall
        self.lines = [52.0, 68.0]                       # staff-wide values 8 px above and below: outside the 0.15 sp pad

    def test_OFF_reads_no_line_and_a_full_curve(self):
        m = G.arc_ink_shape(self.img, self.box, SP, self.lines)
        self.assertEqual(m["lines_in_box"], 0)
        self.assertEqual(m["coverage"], 1.0)

    def test_local_line_is_found_once_and_taken_out(self):
        m = G.arc_ink_shape(self.img, self.box, SP, self.lines, local_lines=True)
        self.assertEqual(m["lines_in_box"], 1)          # two staff-wide ys snap to ONE line run
        self.assertEqual(m.get("lines_found_locally"), 1)
        self.assertLess(m["coverage"], 0.35)            # nothing curved is left: the decision refuses it as a staff line

    def test_a_curved_tie_near_a_line_is_not_a_line(self):
        img = np.full((120, 200), 255, dtype=np.uint8)
        for x in range(40, 100):                         # a bowed stroke: no row is ink across the box
            yc = int(round(58 + 4 * ((x - 70) / 30.0) ** 2))
            img[yc - 1:yc + 1, x] = 0
        m = G.arc_ink_shape(img, (40.0, 55.0, 100.0, 64.0), SP, self.lines, local_lines=True)
        self.assertEqual(m["lines_in_box"], 0)
        self.assertGreater(m["coverage"], 0.9)


class TestContestedPosition(unittest.TestCase):
    def test_hole_one_step_off_the_box_is_contested(self):
        c = HP.contested_position({"rounded": 0, "hole_refused": "off_grid", "hole_steps": [0.59]}, 0.1)
        self.assertEqual((c["own"], c["alternative"]), (0, 1))

    def test_ink_disagreeing_hole_is_contested(self):
        c = HP.contested_position({"rounded": 1, "hole_refused": "ink_disagrees", "hole_steps": [2.02]}, 1.34)
        self.assertEqual(c["alternative"], 2)

    def test_settled_heads_are_not_contested(self):
        self.assertIsNone(HP.contested_position({"rounded": 1, "from_head_hole": [1.05]}, 1.05))
        self.assertIsNone(HP.contested_position({"rounded": 1}, 1.2))
        self.assertIsNone(HP.contested_position({"rounded": 1, "hole_refused": "same_position", "hole_steps": [1.1]}, 1.2))
        self.assertIsNone(HP.contested_position({"rounded": 1, "hole_refused": "holes:2", "hole_steps": [0.9, 3.0]}, 1.2))
        self.assertIsNone(HP.contested_position({"rounded": 1, "hole_refused": "off_grid", "hole_steps": [3.4]}, 1.2))

    def test_flag(self):
        with mock.patch.dict(os.environ, {"OMR_HEAD_HOLE_POSITION": "0"}):
            self.assertFalse(HP.r6_enabled())
        with mock.patch.dict(os.environ, {"OMR_HEAD_HOLE_POSITION": "1"}):
            self.assertTrue(HP.r6_enabled())


if __name__ == "__main__":
    unittest.main()
