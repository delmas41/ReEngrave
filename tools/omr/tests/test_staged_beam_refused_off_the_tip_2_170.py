"""ROADMAP 2.170 (STAGED ADJUDICATE `rhythm.adjudicate_duration`), flag `OMR_BEAM_REFUSED_OFF_THE_TIP`, default OFF.

Where every stroke over a stemmed head was refused (`beam_discounted_uncertain`) and the 2.146 clean-tip rule could not decide
because the FLAG window at the tip was unread, the head is read as any unmarked head is -- IF no beam stroke of the cell
(either reader; kept, refused, or a detector box `_kept_beams` dropped) stands at its own stem tip AND the tip's beam-run
reader read that tip and found no run. A beam joins its stems at their ends. Each positive has a control beside it that
differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.tests.test_staged_stem_tip_decides_beam_2_146 import CELL, _discounted

FLAG = rhythm.BEAM_REFUSED_OFF_THE_TIP_ENV


def _run(log, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)


def _box_at_the_tip(log, reader=READERS.DETECTOR):
    """A stroke box at the up-stem's tip (stem x 105-109, tip y 80). As a DETECTOR box it overlaps the CV neighbour stroke
    (x 90-130) in x, so `_kept_beams` drops it -- the shattered-beam case: the CV piece stops short, the box reaches."""
    log.observe(CELL, Q.BEAM_STROKE, (100, 76, 30, 6), reader=reader, frame="cell:0", x0=100, x1=130, y_center=79,
                image="original", staff_lines_erased=False)


class TestOffTheTip(unittest.TestCase):

    def test_unread_flag_window_nothing_at_the_tip_decides_the_head(self):
        log = Log()
        g = _discounted(log, tip_found=None, runs=())
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertIn("beam_refused_off_the_tip", v.detail)

    def test_control_flag_off_keeps_the_narrowing(self):
        log = Log()
        g = _discounted(log, tip_found=None, runs=())
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_a_dropped_detector_box_at_the_tip_keeps_the_narrowing(self):
        log = Log()
        g = _discounted(log, tip_found=None, runs=())
        _box_at_the_tip(log)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_beam_runs_at_the_tip_keep_the_narrowing(self):
        log = Log()
        g = _discounted(log, tip_found=None, runs=[(70, 80, 0.5, 2.0)])
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_no_tip_levels_row_keeps_the_narrowing(self):
        log = Log()
        g = _discounted(log, tip_found=None, levels_row=False)
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)

    def test_a_hook_at_the_tip_is_never_read_as_a_quarter(self):
        log = Log()
        g = _discounted(log, tip_found=True, runs=())
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn("beam_refused_off_the_tip", v.detail or {})
        self.assertFalse(v.outcome is Outcome.DECIDED and (v.value or {}).get("beam_levels") == 0)


class TestTheFlag(unittest.TestCase):

    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(rhythm.beam_refused_off_the_tip_enabled())

    def test_on_words(self):
        for w in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertTrue(rhythm.beam_refused_off_the_tip_enabled())
        for w in ("0", "false", "", "maybe"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertFalse(rhythm.beam_refused_off_the_tip_enabled())


if __name__ == "__main__":
    unittest.main()
