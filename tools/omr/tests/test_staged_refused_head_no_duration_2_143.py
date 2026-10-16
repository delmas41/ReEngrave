"""ROADMAP 2.143 -- a head box ADJUDICATE refused as not-a-notehead decides no duration (STAGED ADJUDICATE
`adjudicate_duration`, flag `OMR_REFUSED_HEAD_NO_DURATION`, default OFF; CLAUDE.md rule 8).

Sean 2026-10-15 (2.141 fix-1 tiles 9, 12, 13): 'no note'. The box was refused (`too_narrow` / `is_a_beam_piece`) yet a DECIDED
duration stood on it for every consumer that reads durations (tiles, reports, `reconcile_chord_duration` mates).
The CONTROL_ tests are green with the rule absent: a rule that abstains every head cannot pass them.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import consequences                        # noqa: F401
from tools.omr.staged.record import Kind, Outcome, Q
from tools.omr.staged.adjudicators import rhythm
from tools.omr.tests.test_staged_rest_twin_2_142 import _fixture

ON = {"OMR_REFUSED_HEAD_NO_DURATION": "1", "OMR_HEAD_IS_A_REST_TWIN": "1"}


def _decide(env, **kw):
    log, h = _fixture(**kw)
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log, h


class TestRefusedHeadNoDuration(unittest.TestCase):
    def test_a_refused_head_has_no_duration_flag_on_RED(self):
        log, h = _decide(ON)
        nn = log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h)
        self.assertTrue(nn.value is True and nn.outcome is Outcome.DECIDED)
        d = log.verdict(Q.DURATION, h)
        self.assertEqual(d.outcome, Outcome.ABSTAINED)
        self.assertEqual(d.reason, "refused_as_a_notehead")

    def test_CONTROL_flag_off_the_refused_head_keeps_its_duration(self):
        log, h = _decide({"OMR_REFUSED_HEAD_NO_DURATION": "0", "OMR_HEAD_IS_A_REST_TWIN": "1"})
        self.assertTrue(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value is True)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)

    def test_CONTROL_a_head_that_is_not_refused_keeps_its_duration_flag_on(self):
        log, h = _decide(ON, rest_box=(900, 200, 130, 100))        # the rest box is far: the head stands
        self.assertFalse(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, h).value)
        self.assertEqual(log.verdict(Q.DURATION, h).outcome, Outcome.DECIDED)

    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(rhythm.REFUSED_HEAD_NO_DURATION_ENV, None)
            self.assertFalse(rhythm.refused_head_no_duration_enabled())
        with mock.patch.dict(os.environ, {rhythm.REFUSED_HEAD_NO_DURATION_ENV: "on"}):
            self.assertTrue(rhythm.refused_head_no_duration_enabled())

    def test_the_bar_does_not_stand_the_refused_head(self):
        """EVALUATE `_standing` hands consumers no DECIDED/NARROWED duration for the refused head."""
        log, h = _decide(ON)
        standing = consequences._standing(log, h.at(Kind.CELL), Q.DURATION)
        self.assertFalse([v for v in standing
                          if v.subject == h and v.outcome in (Outcome.DECIDED, Outcome.NARROWED)])


if __name__ == "__main__":
    unittest.main()
