"""ROADMAP 2.174 (STAGED ADJUDICATE `rhythm.adjudicate_duration`), flag `OMR_STROKE_AT_STEM_TIP_NARROWS`, default OFF.

A head about to be written `head_and_marks` at its plain value (a quarter) while a stroke the filters KEPT stands at its own stem's end is
NARROWED between the plain value and one beam level -- a beam joins every stem it spans at the stem's end. It never decides an eighth.
The CV beam reader erases stems before it traces, so a beam meeting a group-edge stem is traced from just PAST it and the join reader says
"does not reach the stem horizontally": that is the fixture. Each positive has a control beside it that differs only in the evidence."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import CELL, _stem, _two_staff

FLAG = rhythm.QUARTER_UNDER_BEAM_ENV


def _run(log, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)


def _head_with_stroke(log, *, x0, y=76, join=False):
    """An up-stem head (stem x 105-109, tip y 80) and one CV stroke of the cell starting at `x0` at height `y`; the join reader's verdict on it
    (`join` False = "does not reach the stem horizontally")."""
    g = _two_staff(log)
    s = _stem(log, x=105, y=80)
    log.observe(CELL, Q.BEAM_STROKE, (x0, y, 80, 6), reader=READERS.CV_LINES, frame="cell:0", x0=x0, x1=x0 + 80,
                y_center=y + 3, image="no_staff", staff_lines_erased=True)
    b = log.rows(Q.BEAM_STROKE, CELL)[-1]
    log.observe(CELL, Q.BEAM_STEM_JOIN, join, reader=READERS.CV_BEAM_JOIN, frame="cell:0", stem_row_id=s.id,
                beam_row_id=b.id, end="top", gap_px=None, max_blank_run_px=None, gap_tolerance_px=12.0,
                window_canonical=None, reason=None if join else "stroke_does_not_reach_stem_horizontally")
    return g


class TestStrokeAtStemTip(unittest.TestCase):

    def test_control_stroke_far_across_from_the_stem_is_not_at_its_end(self):
        log = Log()
        g = _head_with_stroke(log, x0=136)   # 27 px past the stem's right edge = 1.7 spaces
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "head_and_marks")

    def test_stroke_just_past_the_stem_narrows(self):
        log = Log()
        g = _head_with_stroke(log, x0=118)   # 9 px = 0.56 space past the stem
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.5, 1.0])
        self.assertTrue(v.detail.get("stroke_at_stem_tip"))

    def test_control_flag_off_decides_the_quarter(self):
        log = Log()
        g = _head_with_stroke(log, x0=118)
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "head_and_marks")
        self.assertEqual(v.value["beats"], 1.0)

    def test_control_stroke_far_along_the_stem_is_not_at_its_end(self):
        log = Log()
        g = _head_with_stroke(log, x0=118, y=20)   # 60 px above the tip
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.reason, "beams_ambiguous")

    def test_never_decides_an_eighth(self):
        log = Log()
        g = _head_with_stroke(log, x0=118)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotEqual(v.outcome, Outcome.DECIDED)


if __name__ == "__main__":
    unittest.main()
