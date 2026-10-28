"""ROADMAP 2.202b, fault 1: a horizontal stroke's thickness is read on the UNERASED raster (CLAUDE §7). Constructed cells: the staff-line erase
(`staff_line_removal`) takes a beam that HANGS from a line out of the line down to ~0.44 sp below it (the bounded walk, FINDINGS 2.202 section 5c), so the
erased raster holds a 0.17 sp sliver of a 0.6 sp beam. The map must read 0.6 (RED); a slur beside the same line, a beam well off every line and a beam
printed OVER a line must read as before (twins); and the control turns the fix off and shows the RED test fail."""
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import stroke_map as SM

SP = 100
LINES = [300 + SP * i for i in range(5)]
LT = 3                      # half thickness of a printed line (7 px = 0.07 sp)


def cell(beam_rows=None, erase_rows=None, other=()):
    """raw = the staff lines + a beam of `beam_rows` (y0, y1) x 600..1000; erased = raw with the lines taken out and, when `erase_rows` is given, those rows
    of the beam taken out too (what the bounded-walk erase does)."""
    raw = np.full((1000, 1400), 255, np.uint8)
    for y in LINES:
        raw[y - LT:y + LT + 1, :] = 0
    if beam_rows:
        raw[beam_rows[0]:beam_rows[1], 600:1000] = 0
    for (y0, y1, x0, x1) in other:
        raw[y0:y1, x0:x1] = 0
    er = raw.copy()
    for y in LINES:
        er[y - LT:y + LT + 1, :] = 255
    if beam_rows:                                    # a beam over a line (> 0.45 sp run) is not erased at all: the eraser keeps what it cannot wholly take
        er[beam_rows[0]:beam_rows[1], 600:1000] = 0
    if erase_rows:
        er[erase_rows[0]:erase_rows[1], 600:1000] = 255
    return er, raw


def horiz(res, near=(600, 0)):
    c = [s for s in res.strokes if s.kind == "horizontal" and abs(s.box[0] - near[0]) < 80]
    assert len(c) == 1, [(s.kind, s.box) for s in res.strokes]
    return c[0]


def read(er, raw, on=True):
    with mock.patch.object(SM, "THICKNESS_FROM_UNERASED", on):
        return horiz(SM.map_strokes(er, SP, LINES, raw))


class TestBeamOnALine(unittest.TestCase):

    def hanging(self):
        # the beam hangs from the line at y=500: rows 497..557 (0.6 sp); the erase took rows 497..540 (the line and 0.4 sp of the beam)
        return cell(beam_rows=(497, 557), erase_rows=(497, 541))

    def test_RED_the_erased_sliver_is_read_back_to_the_printed_beam(self):
        er, raw = self.hanging()
        s = read(er, raw)
        self.assertGreaterEqual(s.thickness_sp, 0.5, s.thickness_sp)
        self.assertLessEqual(s.thickness_sp, 0.65)

    def test_twin_a_beam_off_every_line_reads_the_same_with_or_without_the_fix(self):
        er, raw = cell(beam_rows=(530, 590))
        self.assertEqual(read(er, raw, True).thickness_sp, read(er, raw, False).thickness_sp)
        self.assertAlmostEqual(read(er, raw, True).thickness_sp, 0.6, delta=0.08)

    def test_twin_a_beam_printed_over_a_line_is_read_whole(self):
        er, raw = cell(beam_rows=(470, 530))               # the line at 500 lies inside the beam (rows 497..503)
        s = read(er, raw)
        self.assertAlmostEqual(s.thickness_sp, 0.6, delta=0.08)

    def test_twin_a_thin_slur_next_to_a_line_is_not_thickened(self):
        # a 0.2 sp line-parallel remnant 0.1 sp clear of the line: the erase touched nothing of it, so nothing is put back
        er, raw = cell(other=[(512, 532, 600, 1000)])
        s = read(er, raw)
        self.assertLess(s.thickness_sp, 0.3, s.thickness_sp)

    def test_twin_a_thin_slur_touching_the_line_gets_back_at_most_the_line(self):
        # 0.2 sp slur hanging from the line at 500 (rows 497..520, the erase took rows 497..520 whole, no stroke left): nothing there to read
        er, raw = cell(other=[(497, 520, 600, 1000)])
        er[497:521, 600:1000] = 255
        self.assertEqual([s for s in SM.map_strokes(er, SP, LINES, raw).strokes if s.kind == "horizontal"], [])


class TestControlCanFail(unittest.TestCase):
    def test_with_the_fix_off_the_same_cell_reads_the_sliver_and_the_RED_test_would_fail(self):
        er, raw = TestBeamOnALine().hanging()
        old = read(er, raw, on=False).thickness_sp
        self.assertLess(old, 0.3, old)                       # the 2.202 reading: 0.17 sp, under the 0.5 cut
        self.assertGreaterEqual(read(er, raw, on=True).thickness_sp, 0.5)

    def test_the_reading_is_what_moves_the_beam_role(self):
        from tools.omr.staged import beam_strokes as BS
        er, raw = TestBeamOnALine().hanging()
        for on, role in ((False, "span_thin"), (True, "beam")):
            s = read(er, raw, on)
            v = [BS.StrokeView(0, "vertical", (590, 400, 20, 200), 2.0, 0.2, 0.0, 90.0, ((2, 1.0),), 100.0),
                 BS.StrokeView(1, "vertical", (990, 400, 20, 200), 2.0, 0.2, 0.0, 90.0, ((2, 1.0),), 100.0),
                 BS.StrokeView(2, "horizontal", s.box, s.length_sp, s.thickness_sp, 0.0, 0.0, ((0, 1.0), (1, 1.0)), 100.0)]
            self.assertEqual(BS.roles(v)[2]["role"], role, on)


if __name__ == "__main__":
    unittest.main()
