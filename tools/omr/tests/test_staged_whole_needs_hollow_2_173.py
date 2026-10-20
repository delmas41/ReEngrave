"""ROADMAP 2.173 (Sean 2026-10-19 "Do both"): `OMR_WHOLE_NEEDS_HOLLOW_NO_STEM` -- a whole value only for a HOLLOW head no stem touches.

Evidence: 53 of the 56 whole notes in the red-bars export were not notes (digit loops, rest curls, whole-rest blocks); Brahms p8 s1 staff8
cell11 is a quarter rest's lower curl boxed whole at 0.285 and `adjudicate_duration` wrote 4.0 from the CLASS, marked READ. Engraving: a whole
note has a hollow head and no stem. Pairs differ by one fact (flag, fill, a stem). No test reads module source text.
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged.record import Outcome, Q, Log

from tools.omr.tests.test_staged_open_head_on_stem_2_130 import _head, _ink

FLAG = "OMR_WHOLE_NEEDS_HOLLOW_NO_STEM"


def _v(log, g, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0", "OMR_OPEN_HEAD_ON_STEM": "1"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


class TestWholeNeedsHollowNoStem(unittest.TestCase):
    def test_a_filled_whole_class_box_with_no_stem_is_unread_RED(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem=False)
        _ink(log, g, filled=True)
        v = _v(log, g)
        self.assertIsNone(v.value)
        self.assertEqual(v.reason, "whole_class_filled_or_stemmed")

    def test_FLAG_OFF_the_filled_box_is_still_a_decided_whole(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem=False)
        _ink(log, g, filled=True)
        v = _v(log, g, on=False)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 4.0)

    def test_a_stem_through_the_middle_of_a_hollow_whole_is_unread_RED(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem_x=146)
        _ink(log, g)
        v = _v(log, g)
        self.assertIsNone(v.value)
        self.assertEqual(v.reason, "whole_class_filled_or_stemmed")

    def test_CONTROL_a_hollow_whole_with_no_stem_stays_a_decided_whole(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem=False)
        _ink(log, g)
        v = _v(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 4.0)

    def test_CONTROL_a_flush_stem_still_makes_a_half_by_2_130(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine")
        _ink(log, g)
        v = _v(log, g)
        self.assertEqual(v.reason, "whole_class_on_a_stem")
        self.assertEqual(v.value["beats"], 2.0)

    def test_CONTROL_a_half_class_head_is_untouched(self):
        log = Log()
        g = _head(log, "noteheadHalf", stem=True)
        _ink(log, g)
        v = _v(log, g)
        self.assertEqual(v.value["beats"], 2.0)


if __name__ == "__main__":
    unittest.main()
