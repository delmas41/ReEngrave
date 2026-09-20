"""The page-frame vertical-run reader: it must not clip, and must not filter.

⚠️ EVERY TEST HERE IS ABOUT THE TWO THINGS THAT DISTINGUISH THIS READER FROM
`detect_stems`, because those are the only things it claims: the WINDOW (the
page, so a mark taller than a measure cell keeps both its ends) and the
FILTERS (none, so the population is not pre-decided). The opening recipe is
shared, and one test asserts that it is SHARED rather than copied.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr import line_detection as LD
from tools.omr.types import Staff
from tools.omr.vertical_runs_page import (KERNEL_REFERENCE_SPACES,
                                          page_staff_spacing,
                                          read_page_vertical_runs)

SPACING = 20


class _Page:
    """The smallest thing `read_page_vertical_runs` reads: an `rgb` render."""

    def __init__(self, h: int, w: int):
        self.rgb = np.full((h, w, 3), 255, np.uint8)

    def ink_column(self, x: int, y0: int, y1: int, width: int = 3) -> None:
        self.rgb[y0:y1, x:x + width] = 0

    def ink_row(self, y: int, x0: int, x1: int, thickness: int = 2) -> None:
        self.rgb[y:y + thickness, x0:x1] = 0


def _staff(index: int, top: int, x0: int = 50, x1: int = 550) -> Staff:
    return Staff(page_index=0, staff_index=index,
                 line_ys=[top + i * SPACING for i in range(5)],
                 x_start=x0, x_end=x1)


def _two_staff_page():
    """Two staves 10 spaces apart — far enough that a mark spanning both is
    taller than the 4 + 4 + 4 space reach of either one's measure cell."""
    page = _Page(h=700, w=600)
    staves = [_staff(0, top=100), _staff(1, top=400)]
    for s in staves:
        for y in s.line_ys:
            page.ink_row(y, s.x_start, s.x_end)
    return page, staves


class TestItDoesNotClip(unittest.TestCase):
    """The fault this module exists to remove."""

    def test_a_mark_spanning_two_staves_is_ONE_run_with_both_its_ends(self):
        page, staves = _two_staff_page()
        top, bottom = staves[0].line_ys[0], staves[1].line_ys[-1]
        page.ink_column(300, top, bottom + 1)

        runs = read_page_vertical_runs(page, staves, spacing=SPACING)
        tall = [r for r in runs if r.h > 5 * SPACING]
        self.assertEqual(len(tall), 1, "one mark must come back as one run")
        run = tall[0]
        # ⚠️ THE ASSERTION IS THE ENDS, NOT THE COUNT. A cell-frame reader also
        # returns "one run" for this ink — two of them, each with one end
        # belonging to the crop. What only a page reader can do is give back
        # the ink's own endpoints.
        self.assertAlmostEqual(run.y_top, top, delta=2)
        self.assertAlmostEqual(run.y_bottom, bottom + 1, delta=2)
        self.assertEqual(run.staves_spanned, 2)

    def test_the_cell_pad_signature_is_absent(self):
        """The predecessor's diagnosis in one assertion: a clipped run's ends
        sit at exactly −4.00 / +4.00 staff spaces from its own staff's outer
        lines, because that is `PAD_ABOVE_STAFF_LINES` / `PAD_BELOW`. A page
        reader's must not."""
        page, staves = _two_staff_page()
        top, bottom = staves[0].line_ys[0], staves[1].line_ys[-1]
        page.ink_column(300, top, bottom + 1)
        run = max(read_page_vertical_runs(page, staves, spacing=SPACING),
                  key=lambda r: r.h)
        d_top = (run.y_top - staves[0].line_ys[0]) / SPACING
        self.assertLess(abs(d_top), 0.5, "the top end is the INK's")
        d_bot = (run.y_bottom - staves[0].line_ys[-1]) / SPACING
        self.assertGreater(d_bot, 4.5,
                           "a run crossing into the next staff must read past "
                           "the cell's 4.0-space reach, not at it")


class TestItDoesNotFilter(unittest.TestCase):
    """`detect_stems` refuses 64.7% of its candidates by a DIMENSION bound.
    This reader refuses nothing, and each test names a bound it does not have."""

    def test_a_run_taller_than_the_stem_ceiling_is_kept(self):
        page, staves = _two_staff_page()
        page.ink_column(300, 100, 480)          # ~19 spaces, over the 8.0 cap
        runs = read_page_vertical_runs(page, staves, spacing=SPACING)
        self.assertTrue(any(r.height_spaces > LD.STEM_MAX_HEIGHT_LINES
                            for r in runs))

    def test_a_run_wider_than_the_stem_width_cap_is_kept(self):
        page, staves = _two_staff_page()
        page.ink_column(300, 150, 260, width=int(SPACING))   # 1.0 space wide
        runs = read_page_vertical_runs(page, staves, spacing=SPACING)
        self.assertTrue(any(r.width_spaces > 0.6 for r in runs),
                        "the 0.6-space width cap must not apply here")

    def test_a_run_at_the_page_edge_is_kept(self):
        """`detect_stems` drops a run at the CELL edge because that is where a
        barline lives — the filter that refuses the very population this
        reader is for."""
        page, staves = _two_staff_page()
        page.ink_column(1, 150, 260)
        runs = read_page_vertical_runs(page, staves, spacing=SPACING)
        self.assertTrue(any(r.x <= 2 for r in runs))


class TestAttribution(unittest.TestCase):

    def test_a_run_outside_every_staffs_x_reach_is_attributed_to_NONE(self):
        """*Cannot tell* must not be written down as an answer."""
        page, staves = _two_staff_page()
        page.ink_column(580, 150, 260)      # past x_end = 550
        runs = [r for r in read_page_vertical_runs(page, staves,
                                                   spacing=SPACING)
                if r.x >= 570]
        self.assertTrue(runs, "the fixture must produce the run it tests")
        self.assertIsNone(runs[0].staff_index)

    def test_a_run_inside_one_staff_names_that_staff(self):
        page, staves = _two_staff_page()
        page.ink_column(300, 405, 470)
        runs = [r for r in read_page_vertical_runs(page, staves,
                                                   spacing=SPACING)
                if r.y > 390]
        self.assertTrue(runs)
        self.assertEqual(runs[0].staff_index, 1)


class TestTheUnit(unittest.TestCase):

    def test_the_spacing_is_the_MEDIAN_over_staves(self):
        wide = Staff(page_index=0, staff_index=2,
                     line_ys=[0, 40, 80, 120, 160], x_start=50, x_end=550)
        _, staves = _two_staff_page()
        self.assertEqual(page_staff_spacing(staves + [wide]), SPACING,
                         "one odd staff must not move the page's unit")

    def test_no_unit_RAISES_rather_than_reporting_px_as_spaces(self):
        page, _ = _two_staff_page()
        with self.assertRaises(ValueError):
            read_page_vertical_runs(page, [])


class TestTheRecipeIsSHARED(unittest.TestCase):
    """⚠️ ANTI-DRIFT. The claim under test in the benchmark is that the WINDOW
    and the FILTERS differ; if the opening recipe drifted too, a delta between
    the two readers could not be attributed to either."""

    def test_the_kernel_margin_is_line_detections_own(self):
        import tools.omr.vertical_runs_page as VRP
        self.assertIs(VRP.STEM_KERNEL_MARGIN, LD.STEM_KERNEL_MARGIN)

    def test_the_ink_threshold_is_line_detections_own(self):
        import tools.omr.vertical_runs_page as VRP
        self.assertIs(VRP._binary_ink, LD._binary_ink)

    def test_the_kernel_reference_matches_detect_stems_min_height(self):
        import inspect
        sig = inspect.signature(LD.detect_stems)
        self.assertEqual(sig.parameters["min_height_lines"].default,
                         KERNEL_REFERENCE_SPACES)


if __name__ == "__main__":
    unittest.main()
