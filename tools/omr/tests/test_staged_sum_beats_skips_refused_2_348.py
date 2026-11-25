"""ROADMAP 2.348 (b) -- the voice splitter's bar sum (STAGED ADJUDICATE `rhythm._sum_beats`) leaves out ink already refused as not a note.

`_bar_lengths_for` (the meter's bar sum) stopped summing such ink in 2.346 (flag `OMR_BAR_SUM_SKIPS_REFUSED`); `_sum_beats` summed it still. It now
asks the SAME `_glyph_left_the_bar(..., reinstated_stays=True)` under the same flag -- no second copy of the decision.

CONTROL FROM REAL ROWS (CLAUDE.md rule 7): the rows of Brahms system/6/1 cell 0 staff 6 (bar 107, 6/8, printed 3.0 quarters) in the
20261123-night record, the fixture 2.346 cut (`fixtures/bar_sum_refused_2_346_brahms_p6_s1_c0.json`): three eighth rests and three eighth
notes (3.0), a chord of two clef/key glyphs refused `claimed_by:leading_column` that still carry a decided 1.0, and a sharp boxed as a
head (narrowed, NOT refused). EVENTS = the real `Q.EVENT` grouping of that cell.

NEVER-CONTROLS: a read note never leaves; an undecided head keeps the sum unknown; a refused box reinstated as an eighth rest stays.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Outcome, Q, Subject
from tools.omr.tests.test_staged_bar_sum_skips_refused_2_346 import ENV, _put, _real_log

REAL = [[20, 21], [5], [18], [14], [3], [9], [1], [12]]       # the record's Q.EVENT grouping of the cell, left to right
SHARP = 14                                                     # the narrowed box (a sharp boxed as a head)


def _sum(log, cell, groups, *, on):
    log.freeze()
    adjudicate._ensure_decisions()
    ev = adjudicate.Evidence(log, cell, adjudicate.REGISTRY[Q.VOICES])
    events = [{"_glyphs": tuple(g), "kind": "chord"} for g in groups]
    with mock.patch.dict(os.environ, {ENV: "1" if on else "0"}, clear=False):
        return rhythm._sum_beats(ev, cell, events)


class TestRealBar107(unittest.TestCase):
    NO_SHARP = [g for g in REAL if g != [SHARP]]

    def test_off_sums_the_clef_and_key_ink(self):
        log, cell = _real_log()
        self.assertEqual(_sum(log, cell, self.NO_SHARP, on=False), 4.0)       # 3.0 of notes and rests + the refused chord's 1.0

    def test_on_leaves_the_refused_ink_out_and_the_bar_sums_to_its_meter(self):
        log, cell = _real_log()
        got = _sum(log, cell, self.NO_SHARP, on=True)
        self.assertEqual(got, 3.0)
        self.assertTrue(rhythm._sums_to(got, 3.0))                            # 6/8 = 3.0 quarters

    def test_never_an_undecided_head_makes_the_sum_known(self):
        log, cell = _real_log()
        self.assertIsNone(_sum(log, cell, REAL, on=True))                     # the narrowed sharp keeps the bar unknown, as OFF does
        log, cell = _real_log()
        self.assertIsNone(_sum(log, cell, REAL, on=False))

    def test_never_a_read_note_leaves_when_its_refusal_was_not_decided(self):
        """Take the refusal off the two clef/key boxes (an undecided head): they stay in the bar exactly as before."""
        log, cell = _real_log(drop_refusals=(20, 21))
        self.assertEqual(_sum(log, cell, self.NO_SHARP, on=True), 4.0)

    def test_a_refused_box_read_as_an_eighth_rest_stays(self):
        log, cell = _real_log()
        sub = Subject.from_key("glyph/6/1/6/0/20")
        prior = log.verdict(Q.NOTEHEAD_IS_AN_EIGHTH_REST, sub)           # the saved row abstained; this reads the ink as an eighth rest
        log.record(adjudicate.Verdict(id=log._next_id("vrd"), subject=sub, quantity=Q.NOTEHEAD_IS_AN_EIGHTH_REST,
                                      outcome=Outcome.DECIDED, value=True, decider="t", reason="t", supersedes=prior.id))
        self.assertEqual(_sum(log, cell, self.NO_SHARP, on=True), 4.0)        # 20 is a rest in the bar: it stands for its event

    def test_a_chord_keeps_its_value_when_only_a_twin_is_refused(self):
        log, cell = _real_log(drop_refusals=(20,))                            # 21 refused, 20 not: 20 stands for the event
        self.assertEqual(_sum(log, cell, self.NO_SHARP, on=True), 4.0)

    def test_the_flag_off_is_the_old_sum(self):
        log, cell = _real_log()
        self.assertEqual(_sum(log, cell, self.NO_SHARP, on=False), 4.0)


if __name__ == "__main__":
    unittest.main()
