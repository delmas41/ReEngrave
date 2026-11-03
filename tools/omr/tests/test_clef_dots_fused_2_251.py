"""ROADMAP 2.251 step 3 -- the F clef's dot pair where the dots FUSE with the staff lines (a fat print) or touch a stem.

Cause (Litolff bar 111): `f_dot_pairs` cleared every column holding an unbroken RAW vertical run of 1.8 sp, and a dot that fuses with
the line above and the line below makes a column of 2.4 sp of raw ink -- the dots were cleared as if they were a stem. With
`OMR_CLEF_DOT_FUSED` a column is a stroke only where its ink also runs on past the staff. Twins: a fused pair is seen (and was not
before); a stem through the F line with NO dots, a barline, and a lone dot are refused."""
import os
import unittest

import numpy as np

from tools.omr.staged import clef_pagewide as CP

SP = 16.0
TOP = 100.0
LINES = [TOP + i * SP for i in range(5)]
FLINE = LINES[1]


def page(w=500, h=260):
    ink = np.zeros((h, w), dtype=bool)
    for y in LINES:
        ink[int(y) - 2:int(y) + 2, 10:w - 10] = True        # a fat 4 px line
    return ink


def disc(ink, cx, cy, r):
    yy, xx = np.mgrid[:ink.shape[0], :ink.shape[1]]
    ink[(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = True


def pairs(ink, x0=40, x1=460):
    return CP.f_dot_pairs(ink, LINES, SP, x0, x1)


class _Flag(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get(CP.ENV_DOT_FUSED)
        os.environ[CP.ENV_DOT_FUSED] = "1"

    def tearDown(self):
        if self._old is None:
            os.environ.pop(CP.ENV_DOT_FUSED, None)
        else:
            os.environ[CP.ENV_DOT_FUSED] = self._old


class FusedDots(_Flag):
    def test_dots_fused_with_the_lines_are_seen(self):
        ink = page()
        disc(ink, 200, FLINE - 0.5 * SP, 6)                 # radius 6: touches the line above and the F line
        disc(ink, 200, FLINE + 0.5 * SP, 6)
        self.assertGreaterEqual(len(pairs(ink)), 1)         # (overlapping scan windows may report the same pair twice)

    def test_the_cause_is_the_old_stroke_test(self):
        ink = page()
        disc(ink, 200, FLINE - 0.5 * SP, 6)
        disc(ink, 200, FLINE + 0.5 * SP, 6)
        whole = max(p["x_right"] - p["x_left"] for p in pairs(ink))
        os.environ[CP.ENV_DOT_FUSED] = "0"
        shreds = [p["x_right"] - p["x_left"] for p in pairs(ink)]
        # flag off: the fused columns are cleared as a stem and only the dots' two sides are left (the bug, kept OFF): never the whole dot
        self.assertTrue(all(w < whole - 3 for w in shreds))

    def test_dot_beside_a_stem_is_seen(self):
        ink = page()
        disc(ink, 200, FLINE - 0.5 * SP, 4)
        disc(ink, 200, FLINE + 0.5 * SP, 4)
        ink[40:200, 205:209] = True                         # a stem touching the dots' right edge and running past the staff
        self.assertGreaterEqual(len(pairs(ink)), 1)


class Refused(_Flag):
    def test_stem_through_the_f_line_with_no_dots(self):
        ink = page()
        ink[40:200, 200:206] = True                         # 6 px stem from above the staff to below line 3
        self.assertEqual(pairs(ink), [])

    def test_barline(self):
        ink = page()
        ink[LINES[0].__int__() - 3:LINES[4].__int__() + 3, 200:204] = True
        self.assertEqual(pairs(ink), [])

    def test_one_dot_is_no_pair(self):
        ink = page()
        disc(ink, 200, FLINE - 0.5 * SP, 6)
        self.assertEqual(pairs(ink), [])

    def test_dots_a_space_apart_in_x_are_no_pair(self):
        ink = page()
        disc(ink, 200, FLINE - 0.5 * SP, 6)
        disc(ink, 230, FLINE + 0.5 * SP, 6)
        self.assertEqual(pairs(ink), [])

    def test_dots_on_the_wrong_line_are_no_f_pair(self):
        ink = page()
        disc(ink, 200, LINES[2] + 0.5 * SP, 6)              # straddle line 3 from the top, the C-clef line: no F pair
        disc(ink, 200, LINES[2] - 0.5 * SP, 6)
        self.assertEqual(pairs(ink), [])


if __name__ == "__main__":
    unittest.main()
