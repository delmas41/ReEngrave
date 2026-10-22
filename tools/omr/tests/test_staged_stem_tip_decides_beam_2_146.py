"""ROADMAP 2.146 (STAGED ADJUDICATE `rhythm.adjudicate_duration`), flag `OMR_STEM_TIP_DECIDES_BEAM`, default ON since 2026-10-16 (Sean).

Sean 2026-10-16: "the connection to the end of stems is the most important factor - more important than width"; "the stem
tip decides beamed or not". Where every stroke over a stemmed head was refused (`beam_discounted_uncertain`), the head's OWN
stem tip decides: a clean tip (no beam run in `Q.BEAM_STEM_LEVELS`, no flag ink in `Q.STEM_TIP_INK`) is no beam; n beam runs
at the tip are n levels. Anything unread at the tip leaves the narrowing as it was (rule 8). Each positive has a control
beside it that differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import READERS, Log, Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import CELL, _stem, _tip, _two_staff

FLAG = rhythm.STEM_TIP_DECIDES_BEAM_ENV


def _discounted(log, *, tip_found=False, runs=(), levels_row=True, end="top"):
    """The 2.81 fixture: an up-stem head whose only stroke is the neighbour staff's beam -> `beam_discounted_uncertain`;
    plus the 2.140 tip reading of its own stem (`runs` = beam runs at the top end)."""
    g = _two_staff(log)
    log.observe(CELL, Q.BEAM_STROKE, (90, 150, 40, 4), reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=130,
                y_center=152, image="no_staff", staff_lines_erased=True)
    s = _stem(log, x=105, y=80)
    from tools.omr.staged import record as R
    log.observe(R.cell(0, 0, 1, 0), Q.STEM, (90, -10, 4, 50), reader=READERS.CV_LINES, frame="cell:0", x0=90, x1=94,
                y_center=15, image="no_staff", staff_lines_erased=True)
    if tip_found is not None:
        _tip(log, s, found=tip_found, end=end)
    if levels_row:
        ends = {"top": {"left": [list(r) for r in runs], "right": []}, "bottom": {"left": [], "right": []}}
        log.observe(CELL, Q.BEAM_STEM_LEVELS, len(runs), reader=READERS.CV_BEAM_LEVELS, frame="cell:0",
                    stem_row_id=s.id, ends=ends)
    return g


def _run(log, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)


class TestTheTipDecides(unittest.TestCase):

    def test_clean_tip_decides_no_beam(self):
        log = Log()
        g = _discounted(log, tip_found=False, runs=())
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "stem_tip_reads_no_beam")
        self.assertEqual(v.value["beam_levels"], 0)
        self.assertEqual(v.value["beats"], 1.0)

    def test_control_flag_off_keeps_the_narrowing(self):
        log = Log()
        g = _discounted(log, tip_found=False, runs=())
        _run(log, on=False)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beam_discounted_uncertain")

    def test_beam_runs_at_the_tip_do_not_decide(self):
        """Sean 2026-10-16 tile 13: the one 'a beam at the tip' decision was a quarter. Runs at the tip leave the narrowing."""
        for runs in ([(70, 80, 0.5, 2.0)], [(70, 80, 0.5, 2.0), (82, 92, 0.5, 2.0)]):
            log = Log()
            g = _discounted(log, tip_found=False, runs=runs)
            _run(log)
            v = log.verdict(Q.DURATION, g)
            self.assertEqual(v.outcome, Outcome.NARROWED)
            self.assertEqual(v.reason, "beam_discounted_uncertain")


class TestCannotTellLeavesTheNarrowing(unittest.TestCase):

    def _assert_narrowed(self, log, g):
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertNotIn(v.reason, ("stem_tip_reads_no_beam",))

    def test_no_tip_levels_row(self):
        log = Log()
        g = _discounted(log, tip_found=False, levels_row=False)
        _run(log)
        self._assert_narrowed(log, g)

    def test_flag_window_unread(self):
        log = Log()
        g = _discounted(log, tip_found=None, runs=())
        _run(log)
        self._assert_narrowed(log, g)

    def test_flag_window_read_at_the_other_end_only(self):
        log = Log()
        g = _discounted(log, tip_found=False, runs=(), end="bottom")
        _run(log)
        self._assert_narrowed(log, g)

    def test_a_hook_at_the_tip_is_not_a_beam_decision(self):
        log = Log()
        g = _discounted(log, tip_found=True, runs=())
        _run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertNotIn(v.reason, ("stem_tip_reads_no_beam",))


class TestTheFlag(unittest.TestCase):

    def test_default_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertTrue(rhythm.stem_tip_decides_beam_enabled())

    def test_off_word_disables(self):
        for w in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {FLAG: w}):
                self.assertFalse(rhythm.stem_tip_decides_beam_enabled())


if __name__ == "__main__":
    unittest.main()
