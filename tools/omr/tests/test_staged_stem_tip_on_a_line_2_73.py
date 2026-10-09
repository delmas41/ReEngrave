"""ROADMAP 2.73 follow-up -- a staff or ledger line at a stem's tip, and a box
that merely touches the tip window, are not ink on the stem.

Coordinator (2026-10-09), after Sean judged the 2.70 tiles: Litolff pdf p6 #4,
#5 (and #2, #6) stop at 2.70's "the stem tip was MEASURED" test because
`Q.STEM_TIP_INK` abstains `occupied`. Measured here (the lane's
`tipwhy.py`, same record): the occupants were NOT line ink in two of the four --
#4's blocker is an `arpeggiato` box that IS the stem's own ink and ends 1 px into
the window, #6's are two neighbouring head boxes ending 1-5 px into it and a
`ledgerLine` detection; #2 the same. So two causes, both fixed, and the hook counter
(`stem_tip_hooks`, 2.69) is not touched:

  1. a detection box overlapping the tip window by LESS than 0.1 staff space in
     either axis (`STEM_TIP_BLOCKER_TOLERANCE_SPACES`; the detector's box edges are
     good to about that) explains none of its ink;
  2. a `ledgerLine` detection is not a blocker, and the ROWS a horizontal line
     stands on at the tip's x (ink in both probes just beyond the two bands: a flag
     hangs from ONE side) are left out of both bands.

Controls (a refusal test passes by refusing everything): a real flag at a tip on a
line still reads as a flag; a box that really overlaps the window still blocks; a
bare stem on a line still reads bare; a ledger-line detection with a real beam stroke
beside it still abstains. NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).

RUN RED FIRST against the unrepaired tree (HEAD before the commit): the
touching-box, ledger-box and flag-on-a-thick-line tests FAIL.
"""

from __future__ import annotations

import unittest

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import ABSTAIN, Log, Q

SP = 20.0
STEM_X0, STEM_X1 = 190.0, 194.0
TOP_Y, BOTTOM_Y = 100.0, 300.0
SUB = R.cell(0, 0, 0, 0)
STEM_BOX = (STEM_X0, TOP_Y, STEM_X1 - STEM_X0, BOTTOM_Y - TOP_Y)


def _paper(h=400, w=400):
    return np.full((h, w), 255, dtype=np.uint8)


def _draw(img, x0, y0, x1, y1):
    img[int(round(y0)):int(round(y1)), int(round(x0)):int(round(x1))] = 0


def _flag(img):
    _draw(img, STEM_X1, 120, 212, 150)          # the tested band, right of the tip


def _line(img, y=130, thick=10):
    """A ledger line through the tip window, running well past both bands."""
    _draw(img, 130, y, 270, y + thick)


class FakeCell:
    def __init__(self, img):
        self.image_no_staff = img


class _Det:
    def __init__(self, name, x, y, w, h):
        self.smufl_name = name
        self.x_canonical, self.y_canonical = x, y
        self.width_canonical, self.height_canonical = w, h


class TestALineAtTheTipIsNotOnTheStem(unittest.TestCase):

    def test_a_real_flag_at_a_tip_on_a_line_still_reads_as_a_flag(self):
        """THE CONTROL. A flag hangs right of the tip; a thick line across the
        window also fills the LEFT band and broke the 'no ink here' guard, so the
        flag read as no flag. With the line rows left out it is found."""
        img = _paper()
        _flag(img)
        _line(img)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertTrue(m["found"])
        self.assertGreater(m["line_rows_left_out"], 0)

    def test_a_bare_stem_ending_on_a_line_still_reads_bare(self):
        """The line must not be read AS the flag either."""
        img = _paper()
        _line(img)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertFalse(m["found"])
        self.assertGreater(m["line_rows_left_out"], 0)

    def test_a_clean_tip_leaves_no_rows_out(self):
        m = gather.stem_tip_ink(_paper(), STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertEqual(m["line_rows_left_out"], 0)

    def test_ink_on_both_sides_that_is_NOT_a_line_still_fails_the_guard(self):
        """A stain or crossing slur on both sides of the stem, not running past
        the bands: not a line, the old guard stands."""
        img = _paper()
        _flag(img)
        _draw(img, 172, 120, STEM_X0, 150)
        m = gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP)
        self.assertFalse(m["found"])
        self.assertEqual(m["line_rows_left_out"], 0)

    def test_a_window_that_is_mostly_lines_is_declined_not_read(self):
        img = _paper()
        _draw(img, 130, 115, 270, 155)             # a 2-space smear across all of it
        self.assertIsNone(
            gather.stem_tip_ink(img, STEM_X0, STEM_X1, TOP_Y, 1.0, SP))


class TestWhatBlocksTheWindow(unittest.TestCase):

    def test_a_ledger_line_detection_is_not_a_blocker(self):
        ledger = _Det("ledgerLine", 170, 125, 60, 10)
        self.assertEqual(gather._stem_tip_blockers([], [ledger], SP), [])

    def test_CONTROL_any_other_local_detection_of_that_box_still_is(self):
        note = _Det("noteheadBlackInSpace", 170, 125, 60, 10)
        self.assertEqual(len(gather._stem_tip_blockers([], [note], SP)), 1)

    def test_a_box_that_only_touches_the_window_edge_does_not_abstain(self):
        """`arpeggiato` over the stem's own ink, 1 px into the window."""
        log = Log()
        touching = (150.0, 100.0, STEM_X1 + 1.0, 300.0)      # reaches 1 px in
        img = _paper()
        _flag(img)
        gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img),
                                     "obs:stem", STEM_BOX, [touching], SP)
        log.freeze()
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertIn("top", rows)
        self.assertTrue(rows["top"].value)

    def test_CONTROL_a_box_that_really_overlaps_still_abstains_occupied(self):
        log = Log()
        real = (150.0, 100.0, STEM_X1 + 10.0, 300.0)        # half a space in
        img = _paper()
        _flag(img)
        gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img),
                                     "obs:stem", STEM_BOX, [real], SP)
        log.freeze()
        abst = {a.detail["end"]: a for a in log.refusals(Q.STEM_TIP_INK, SUB)}
        self.assertEqual(abst["top"].reason, ABSTAIN.OCCUPIED)

    def test_a_flag_at_a_tip_on_a_ledger_line_with_its_detection_is_measured(self):
        """Both fixes together, through the observer: the `ledgerLine` box is not a
        blocker, the line rows are left out, the flag is found."""
        log = Log()
        img = _paper()
        _flag(img)
        _line(img)
        blockers = gather._stem_tip_blockers(
            [], [_Det("ledgerLine", 170, 130, 60, 10)], SP)
        gather._observe_stem_tip_ink(log, SUB, "cell:0", FakeCell(img),
                                     "obs:stem", STEM_BOX, blockers, SP)
        log.freeze()
        rows = {r.detail["end"]: r for r in log.rows(Q.STEM_TIP_INK, SUB)}
        self.assertTrue(rows["top"].value)


if __name__ == "__main__":
    unittest.main()
