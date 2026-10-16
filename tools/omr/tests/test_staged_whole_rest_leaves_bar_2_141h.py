"""ROADMAP 2.141h fix 3 (STAGED EVALUATE `consequences._left_the_bar` + INFER `solve_bare_stem_bar`), flag
`OMR_WHOLE_REST_INK_LEAVES_BAR`, default OFF.

Litolff p3 tile 10 (Sean: whole rest, 4): the detector boxed a displaced whole rest TWICE (`restWhole`, abstained;
`noteheadBlackInSpace`, ADJUDICATE DECIDED it a whole rest's ink). EXPORT refuses the notehead box; INFER's sum counted
it as a note (cause W) and skipped the abstained rest as zero time (cause U). The RED tests fail with the flag OFF (as on
main); the controls show each part does not fire where its condition is absent.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate, infer, inferences
from tools.omr.staged.record import Kind, Outcome, Q, Subject, Verdict
from tools.omr.tests.test_staged_bare_stem_2_81 import _cell, _sub
from tools.omr.tests.test_staged_narrowed_bar_2_97 import _InferBar

FLAG = consequences.WHOLE_REST_INK_LEAVES_BAR_ENV


def _decline(log, *, on):
    env = {FLAG: "1" if on else "0", infer.CARRIED_METER_FIX_ENV: "1"}
    with mock.patch.dict(os.environ, env, clear=False):
        return inferences.solve_bare_stem_bar(log, _cell(), any_reason=True)


def _verdict(b, g, q, outcome, value=None, reason="x"):
    return b.log.record(Verdict(
        id=b._id(), subject=_sub(0, g, b.cell_idx), quantity=q, outcome=outcome, value=value,
        decider="test", reason=reason))


def _bar_with_whole_rest_ink(wr_outcome=Outcome.DECIDED, wr_value=True, is_rest=False):
    """4/4: three decided quarters + one head narrowed {eighth, quarter} (needs a quarter) + a notehead-class box whose
    ink ADJUDICATE read as a whole rest (4 beats if it were counted as a note)."""
    b = _InferBar()
    for _ in range(3):
        b.decided(1.0)
    (g,) = b.narrowed_chord(1)
    w = b.decided(4.0)
    if is_rest:
        b.durations[-1] = b.log.record(Verdict(
            id=b._id(), subject=_sub(0, w, b.cell_idx), quantity=Q.DURATION, outcome=Outcome.DECIDED,
            value={"beats": 4.0, "written": 4.0, "is_rest": True}, decider="t", reason="rest_class",
            supersedes=b.durations[-1].id))
    _verdict(b, w, Q.NOTEHEAD_IS_A_WHOLE_REST, wr_outcome, wr_value, "shape_and_position_agree")
    return b.finish(), g, w


class TestADecidedWholeRestInkLeavesTheBar(unittest.TestCase):

    def test_the_ink_is_not_summed_as_a_note_RED(self):
        log, g, w = _bar_with_whole_rest_ink()
        out = _decline(log, on=True)
        self.assertIsNone(out.decline)
        self.assertEqual(out.landings, 1)
        self.assertEqual(len(out.proposals), 1)
        self.assertEqual(out.proposals[0].subject.glyph, g)

    def test_CONTROL_flag_OFF_the_ink_is_counted_and_the_bar_does_not_add_up(self):
        log, g, w = _bar_with_whole_rest_ink()
        self.assertEqual(_decline(log, on=False).decline, "bar_does_not_add_up")

    def test_the_default_is_OFF_and_a_typo_leaves_it_off(self):
        log, _g, w = _bar_with_whole_rest_ink()
        for word, on in (("", False), ("yess", False), ("0", False), ("1", True), ("true", True), ("ON", True)):
            with mock.patch.dict(os.environ, {FLAG: word}):
                self.assertEqual(consequences._left_the_bar(log, _sub(0, w)) is not None, on, word)
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertIsNone(consequences._left_the_bar(log, _sub(0, w)))

    def test_CONTROL_an_ABSTAINED_verdict_does_not_take_a_box_out_(self):
        log, _g, w = _bar_with_whole_rest_ink(wr_outcome=Outcome.ABSTAINED, wr_value=None)
        self.assertEqual(_decline(log, on=True).decline, "bar_does_not_add_up")

    def test_CONTROL_a_verdict_of_False_does_not_take_a_box_out(self):
        log, _g, w = _bar_with_whole_rest_ink(wr_value=False)
        self.assertEqual(_decline(log, on=True).decline, "bar_does_not_add_up")

    def test_CONTROL_a_box_that_IS_a_rest_stays(self):
        log, _g, w = _bar_with_whole_rest_ink(is_rest=True)
        self.assertEqual(_decline(log, on=True).decline, "bar_does_not_add_up")

    def test_CONTROL_where_EXPORT_would_write_it_as_a_note_it_stays_in_the_bar(self):
        log, _g, w = _bar_with_whole_rest_ink()
        with mock.patch.dict(os.environ, {FLAG: "1", "OMR_WHOLE_REST_INK": "0"}):
            self.assertIsNone(consequences._left_the_bar(log, _sub(0, w)))


def _bar_with_abstained_element(left_the_bar=False):
    """4/4: three decided quarters + a head narrowed {eighth, quarter} + an ABSTAINED element (a rest nobody sized)."""
    b = _InferBar()
    for _ in range(3):
        b.decided(1.0)
    (g,) = b.narrowed_chord(1)
    a = b.g
    b.g += 1
    _verdict(b, a, Q.DURATION, Outcome.ABSTAINED, None, "rest_stands_where_no_rest_hangs")
    if left_the_bar:
        _verdict(b, a, Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, Outcome.DECIDED, True, "too_narrow")
    return b.finish(), g, a


class TestAnAbstainedElementIsNotZeroTime(unittest.TestCase):

    def test_the_sum_declines_RED(self):
        log, g, a = _bar_with_abstained_element()
        out = _decline(log, on=True)
        self.assertEqual(out.decline, "abstained_element_in_bar")
        self.assertFalse(out.proposals)

    def test_CONTROL_flag_OFF_the_abstained_element_is_skipped_as_zero_and_the_bar_settles(self):
        log, g, a = _bar_with_abstained_element()
        out = _decline(log, on=False)
        self.assertIsNone(out.decline)
        self.assertEqual(len(out.proposals), 1)

    def test_CONTROL_an_abstained_box_a_DECIDED_refusal_took_out_of_the_bar_is_not_an_element(self):
        log, g, a = _bar_with_abstained_element(left_the_bar=True)
        out = _decline(log, on=True)
        self.assertIsNone(out.decline)
        self.assertEqual(len(out.proposals), 1)

    def test_CONTROL_a_bar_with_no_abstained_element_is_untouched(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        log = b.finish()
        out = _decline(log, on=True)
        self.assertIsNone(out.decline)
        self.assertEqual(len(out.proposals), 1)


class TestTile10EndToEnd(unittest.TestCase):
    """Cause W and U together, as in tile 10: the notehead box is the whole rest's ink (DECIDED), the rest box is
    ABSTAINED. Flag ON: the ink leaves, the abstained rest stands in the bar, the sum declines (a refusal, not 'quarter,
    quarter + nothing')."""

    def test_the_bar_is_refused_not_settled(self):
        b = _InferBar()
        b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        w = b.decided(4.0)
        _verdict(b, w, Q.NOTEHEAD_IS_A_WHOLE_REST, Outcome.DECIDED, True, "shape_and_position_agree")
        a = b.g
        b.g += 1
        _verdict(b, a, Q.DURATION, Outcome.ABSTAINED, None, "rest_stands_where_no_rest_hangs")
        log = b.finish()
        self.assertEqual(_decline(log, on=True).decline, "abstained_element_in_bar")


if __name__ == "__main__":
    unittest.main()
