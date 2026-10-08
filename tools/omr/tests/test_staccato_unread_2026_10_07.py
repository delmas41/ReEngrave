"""ROADMAP 2.59 follow-up (lane-staccato-unread) -- Sean, 2026-10-07, Litolff
`12/1/6/2/9`: "Not sure why it can't see that the first cell is a staccato note."

THE CAUSE (measured on the 10-07 day record): the dot is a staccato above a
note that is filed in (and owned by) the NEXT strip down. `dot_role` tried the
staccato window against this strip's own notes only, so the note it stands
over was never a candidate and the dot stayed "cannot tell". 39 of 39
staccato-placed unread dots on the Litolff record had exactly that note.

The fix reads the staccato window against every real head, whichever strip
filed it or owner holds it, within the reader's own stacked reach; it answers
STACCATO only. Every refusal here has a positive control in the same class.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

from tools.omr.tests.test_dot_not_a_note_2026_10_07 import (
    X, SPACE, _log, _pnote, _pdot)


def _run(log, flag=True):
    env = {"OMR_DOT_FOLLOWS_NOTE": "1" if flag else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        adjudicate.run(log)


class TestAStaccatoOverTheNextStripsNote(unittest.TestCase):
    def _page(self, below_x=(X + 10, X + 30), below_y=(18, 34), with_below=True):
        log = _log()
        # this strip's own note, left of the dot and level with it
        _pnote(log, 0, 0, "noteheadBlack", (X - 10, 0, X + 10, 16))
        dot = _pdot(log, 1, (X + 14, 2, X + 22, 10))      # centre x = X + 18
        below = None
        if with_below:
            # the NEXT strip's note: centre x = X + 20, the dot 12 px above it
            below = _pnote(log, 1, 2, "noteheadBlack",
                           (below_x[0], below_y[0], below_x[1], below_y[1]))
        return log, dot, below

    def test_RED_the_dot_is_a_staccato_on_the_note_below_it(self):
        log, dot, below = self._page()
        _run(log)
        role = log.verdict(Q.DOT_ROLE, dot)
        self.assertEqual(role.outcome, Outcome.DECIDED)
        self.assertEqual(role.value, "staccato")
        self.assertEqual(role.detail.get("owner"), below.to_key())

    def test_a_staccato_is_never_lengthening(self):
        log, dot, _ = self._page()
        _run(log)
        self.assertNotEqual(log.verdict(Q.DOT_ROLE, dot).value, "augmentation")

    def test_POSITIVE_CONTROL_without_that_note_the_dot_is_the_old_reading(self):
        log, dot, _ = self._page(with_below=False)
        _run(log)
        self.assertEqual(log.verdict(Q.DOT_ROLE, dot).value, "augmentation")

    def test_a_note_whose_column_is_a_head_away_does_not_take_the_dot(self):
        # centre 20 px right of the dot's centre = 1.25 sp > the 0.5 sp window
        log, dot, _ = self._page(below_x=(X + 28, X + 48))
        _run(log)
        self.assertNotEqual(log.verdict(Q.DOT_ROLE, dot).value, "staccato")

    def test_a_note_beyond_the_stacked_reach_does_not_take_the_dot(self):
        # head top 3 sp (48 px) below the dot's centre > the 2 sp reach
        log, dot, _ = self._page(below_y=(54, 70))
        _run(log)
        self.assertNotEqual(log.verdict(Q.DOT_ROLE, dot).value, "staccato")

    def test_the_flag_off_reading_is_unchanged(self):
        log, dot, _ = self._page()
        _run(log, flag=False)
        self.assertEqual(log.verdict(Q.DOT_ROLE, dot).value, "augmentation")


if __name__ == "__main__":
    unittest.main()
