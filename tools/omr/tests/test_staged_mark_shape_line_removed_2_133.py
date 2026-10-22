"""ROADMAP 2.133 -- the staff line under a dot-family mark is bridged out
before the mark's shape is measured (`OMR_MARK_SHAPE_LINE_REMOVED`, default
OFF; a measurement, adjudication unchanged). Real case: Brahms 317803 p24
tile 11 `glyph/24/1/6/8/18`, a staccatissimo whose body a 7-px staff line
runs through (box 14 x 16 px at 600 dpi).
"""
from __future__ import annotations

import unittest
import numpy as np

from tools.omr.staged import gather


def _tile11_window():
    """The real ink of tile 11, rows 0-16 x cols 0-16 ('#' = ink)."""
    art = """
.......####......
......######.....
...############..
#################
#################
#################
#################
#################
#################
#################
..##############.
..#############..
..#############..
.##############..
.##############..
..#############..
..############...
.....##..........
""".strip("\n").split("\n")
    return np.array([[c == "#" for c in r] for r in art])


class TestLineBridge(unittest.TestCase):
    def test_a_line_crossing_the_mark_is_removed_but_the_mark_keeps_its_cap_and_tip(self):
        ink = _tile11_window()
        raw = gather.mark_shape_of_ink(ink, 34.0)
        out = gather.erase_staff_lines(ink, [(3, 9)])
        m = gather.mark_shape_of_ink(out, 34.0)
        # the line made the mark 17 wide over 7 rows; bridged, the widest row
        # is the body's own (<= 15 wide)
        self.assertEqual(int(ink[5].sum()), 17)
        self.assertLessEqual(int(out[5].sum()), 15)
        self.assertEqual(m["top"] > 0 and m["bot"] > 0, True)
        self.assertLess(m["w_spaces"], raw["w_spaces"])

    def test_CONTROL_a_mark_with_no_line_is_unchanged(self):
        ink = _tile11_window()
        ink[3:10] = False                      # no line, no body there either
        out = gather.erase_staff_lines(ink, [])
        self.assertTrue((out == ink).all())

    def test_the_band_is_read_beside_the_mark_not_from_the_staff_median(self):
        win = np.zeros((30, 40), bool)
        win[10:15, :] = True                   # a 5-row line across the window
        win[8:20, 18:23] = True                # a mark through it
        lo, hi = gather.line_band_beside(win, 12, 18, 23, half_fallback=1)
        self.assertEqual((lo, hi), (10, 14))   # its own thickness, not 12 +- 1
        out = gather.erase_staff_lines(win, [(lo, hi)])
        self.assertFalse(out[12, 5])           # the line beside the mark is gone
        self.assertTrue(out[12, 20])           # the mark's own body is kept

    def test_a_stem_is_not_mistaken_for_the_line(self):
        win = np.zeros((40, 40), bool)
        win[2:38, 13:17] = True                # a stem just left of the mark
        lo, hi = gather.line_band_beside(win, 20, 18, 23, half_fallback=2,
                                         reach=6)
        self.assertEqual((lo, hi), (18, 22))   # fell back to row +- half

    def test_off_by_default(self):
        self.assertFalse(gather.mark_shape_line_removed_enabled())


if __name__ == "__main__":
    unittest.main()
