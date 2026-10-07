"""ROADMAP 2.60 -- an arc box whose ink is a straight line (a staff line, a barline) is REFUSED, never kept as an arc.

Sean, 2026-10-07: *"it is still occasionally calling a staff line an arc"*. Two halves:

  GATHER   `gather.arc_ink_shape` -- what is inside the box once the staff lines are erased.
  ADJUDICATE `adjudicate_arc_is_not_an_arc` reads it: `ink_is_a_staff_line` / `ink_is_a_barline`.

THE TESTS THAT MATTER MOST ARE THE ONES THAT KEEP A REAL ARC: a refusal rule that refuses every arc passes every refusal test.
"""
from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import gather as G
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

SP = 20.0          # one staff space, px
LINES = [100.0 + SP * i for i in range(5)]


def _blank(h=400, w=800):
    return np.full((h, w), 255, np.uint8)          # 0 == ink


def _curve(img, x0, x1, y_mid, sag, thick=4):
    """A thin parabolic arc: a real tie/slur stroke."""
    for x in range(int(x0), int(x1)):
        t = (x - x0) / (x1 - x0)
        y = int(round(y_mid + sag * 4 * t * (1 - t)))
        img[y:y + thick, x] = 0


def _row(log, gi, cov, *, width, height, tall=0.0, lines=0, declined=False):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.ARC_BOX, "slur", reader=READERS.DETECTOR, frame="cell:0", score=0.6,
                x0=0, x1=100, y0=0, y1=10, bbox_page_px=[0, 0, 100, 10])
    if declined:
        log.abstain(g, Q.ARC_INK_SHAPE, reader=READERS.CV_ARC_INK, frame="cell:0", reason="no_mask")
    else:
        log.observe(g, Q.ARC_INK_SHAPE, cov, reader=READERS.CV_ARC_INK, frame="cell:0", tall_cols=tall,
                    lines_in_box=lines, width_spaces=width, height_spaces=height)
    return g


def _decide(log, g):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.ARC_IS_NOT_AN_ARC,))
    return log.verdict(Q.ARC_IS_NOT_AN_ARC, g)


def _staff(img, ys=LINES, x0=0, x1=800, thick=4, tilt=0):
    """Paint the staff lines (0 == ink); `tilt` px of drift across the width, as a scanned staff has."""
    for y in ys:
        for x in range(x0, x1):
            yy = int(round(y + tilt * (x - x0) / max(1, x1 - x0)))
            img[yy:yy + thick, x] = 0


class TestTheInkMeasurement(unittest.TestCase):

    def test_a_box_that_is_only_a_staff_line_holds_nothing_curved(self):
        img = _blank()
        _staff(img)
        m = G.arc_ink_shape(img, (100, LINES[1] - 5, 500, LINES[1] + 9), SP, LINES)
        self.assertEqual(m["coverage"], 0.0)
        self.assertEqual(m["lines_in_box"], 1)

    def test_the_line_is_found_on_the_ink_row_not_the_staff_wide_value(self):
        """A tilted staff: the given line value is 6 px off the ink at the box. Snapped locally, still no curve."""
        img = _blank()
        _staff(img, tilt=6)
        m = G.arc_ink_shape(img, (700, LINES[1] - 4, 790, LINES[1] + 16), SP, LINES)   # the lines drift ~5 px down here
        self.assertEqual(m["coverage"], 0.0)

    def test_a_thick_scanned_line_is_taken_out_whole(self):
        """A heavy plate: 11 px staff line (0.55 sp). A fixed +-2 px band would leave 7 px of it reading as a 'curve'."""
        img = _blank()
        _staff(img, thick=11)
        m = G.arc_ink_shape(img, (100, LINES[1] - 3, 500, LINES[1] + 14), SP, LINES)
        self.assertEqual(m["coverage"], 0.0)

    def test_a_real_curve_survives_with_the_line_taken_out(self):    # positive control, same function
        img = _blank()
        _staff(img)
        _curve(img, 100, 500, LINES[1] + 6, 8)
        m = G.arc_ink_shape(img, (100, LINES[1] - 2, 500, LINES[1] + 26), SP, LINES)
        self.assertGreater(m["coverage"], 0.9)

    def test_a_neighbour_staffs_line_counts_when_it_is_passed(self):
        """The box was cut from another staff's cell: its lines are in `line_ys` too (page-wide), so the line goes."""
        img = _blank()
        _staff(img, ys=[300.0])
        self.assertEqual(G.arc_ink_shape(img, (100, 295, 500, 310), SP, [300.0])["coverage"], 0.0)
        self.assertGreater(G.arc_ink_shape(img, (100, 295, 500, 310), SP, [])["coverage"], 0.9)    # the control: unaware of it, it reads as a curve

    def test_a_barline_is_one_tall_stroke(self):
        img = _blank()
        img[80:210, 300:304] = 0
        m = G.arc_ink_shape(img, (296, 80, 308, 210), SP, [])
        self.assertGreater(m["tall_cols"], 0.25)
        self.assertEqual(m["coverage"], 0.0)

    def test_off_the_raster_or_no_unit_is_declined_not_zero(self):
        self.assertIsNone(G.arc_ink_shape(_blank(), (900, 10, 950, 20), SP, LINES))
        self.assertIsNone(G.arc_ink_shape(_blank(), (10, 10, 50, 20), 0.0, LINES))


class TestTheDecision(unittest.TestCase):

    def test_a_flat_box_on_a_staff_line_is_refused_as_a_staff_line(self):
        log = Log()
        g = _row(log, 0, 0.0, width=22.0, height=1.4, lines=1)
        v = _decide(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "ink_is_a_staff_line")
        self.assertTrue(v.used)

    def test_a_narrow_tall_stroke_is_refused_as_a_barline(self):
        log = Log()
        g = _row(log, 0, 0.0, width=0.5, height=3.0, tall=0.9)
        v = _decide(log, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "ink_is_a_barline")

    def test_a_real_tie_over_a_line_stays(self):
        log = Log()
        g = _row(log, 0, 0.97, width=6.0, height=0.6, lines=1)     # curved ink on nearly every column
        v = _decide(log, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "arc")

    def test_a_wide_box_with_no_line_through_it_is_not_called_a_line(self):
        log = Log()
        g = _row(log, 0, 0.1, width=10.0, height=1.0, lines=0)
        self.assertEqual(_decide(log, g).reason, "arc")

    def test_a_short_box_is_not_called_a_line(self):
        log = Log()
        g = _row(log, 0, 0.0, width=1.5, height=0.5, lines=1)
        self.assertEqual(_decide(log, g).reason, "arc")

    def test_a_declined_reading_refuses_nothing(self):             # rule 8: cannot tell != an answer
        log = Log()
        g = _row(log, 0, 0.0, width=22.0, height=1.4, lines=1, declined=True)
        v = _decide(log, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "arc")

    def test_a_wide_flat_arc_box_is_not_a_barline(self):
        log = Log()
        g = _row(log, 0, 0.9, width=8.0, height=3.0, tall=0.9)
        self.assertEqual(_decide(log, g).reason, "arc")


class TestTheConsumersSkipIt(unittest.TestCase):

    def test_a_refused_tie_is_not_paired(self):
        """`arc_owner` already abstains `not_an_arc` where this verdict is True."""
        log = Log()
        g = _row(log, 0, 0.0, width=22.0, height=1.4, lines=1)
        _decide(log, g)
        v = log.verdict(Q.ARC_IS_NOT_AN_ARC, g)
        self.assertIs(v.value, True)


if __name__ == "__main__":
    unittest.main()
