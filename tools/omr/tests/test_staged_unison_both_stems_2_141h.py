"""ROADMAP 2.141h fix 2 (STAGED ADJUDICATE `rhythm.adjudicate_duration` / `_own_stem_side`), flag
`OMR_OWN_STEM_UNISON_BOTH`, default OFF.

Litolff p5 tile 6 g0: the CV `Q.HEAD_STEM` verdict reads a stem each way (`unison_two_voices`) but `Q.HEAD_STEM_REACH`
reads ONE direction (the up stem stands at the head's right edge: `up_ext` ~ 0), and `_own_stem_side` took the ruler's
single side, so the OTHER voice's beam was "far side" and one voice's count stood for the head. With the flag the head has
no single side and 2.75's per-voice count runs on both stems (a range where the voices differ, rule 8).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import (_head, _ink_row, _real_stem, _stroke)

FLAG = rhythm.UNISON_BOTH_STEMS_ENV


def _reach(log, g, direction, ext=4.1):
    return log.observe(g, Q.HEAD_STEM_REACH, direction, reader=READERS.CV_HEAD_STEM_REACH, frame="page",
                       head_box_page=[0.0, 0.0, 20.0, 16.0], sp=16.0,
                       up_ext=ext if direction == "up" else 0.0, down_ext=ext if direction == "down" else 0.0,
                       up_tip_y=None, down_tip_y=None, up_clipped=False, down_clipped=False)


def _unison(log, down_beams=2, up_beams=1, with_up_stem=True):
    """One head, a stem each way (right-up, left-down), the up voice with `up_beams` beams, the down voice with
    `down_beams`; the ruler says DOWN only."""
    _staff_space(log, 100)
    g = _head(log, 0, (143, 523, 139, 124))
    if with_up_stem:
        _real_stem(log, (261, 351, 19, 311))      # up, at the right edge
    _real_stem(log, (146, 560, 26, 413))          # down, at the left edge
    _real_stem(log, (400, 351, 26, 311))
    _real_stem(log, (565, 566, 25, 394))
    ups = [(255, 343, 622, 64), (255, 290, 622, 40)][:up_beams]
    downs = [(154, 895, 628, 70), (154, 840, 628, 40)][:down_beams]
    for b in ups + downs:
        _ink_row(log, _stroke(log, b), 2.3, 0.01, (True, True))
    _reach(log, g, "down")
    return g


class TestAHeadWithAStemEachWayIsCountedOnBoth(unittest.TestCase):

    def _dur(self, on, **kw):
        log = Log()
        g = _unison(log, **kw)
        with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
            adjudicate.run(log)
        return log, log.verdict(Q.DURATION, g)

    def test_CONTROL_the_head_really_has_a_unison_head_stem_verdict(self):
        log, v = self._dur(False)
        hs = log.verdict(Q.HEAD_STEM, v.subject)
        self.assertEqual(hs.reason, "unison_two_voices")

    def test_flag_OFF_the_ruler_side_counts_the_down_voice_only_as_on_main(self):
        _log, v = self._dur(False)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beam_levels"], 2)
        self.assertEqual(v.detail["beam_side"], "down")

    def test_flag_ON_the_voices_differ_so_the_head_is_a_RANGE_never_one_voices_value_RED(self):
        _log, v = self._dur(True)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beam_levels"] for c in v.candidates), [1, 2])
        self.assertIsNone(v.detail["beam_side"])
        self.assertEqual(v.detail["beam_voices"]["up"], [1, 1])

    def test_flag_ON_voices_that_AGREE_decide_that_value(self):
        _log, v = self._dur(True, down_beams=1)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beam_levels"], 1)

    def test_CONTROL_flag_ON_a_head_with_ONE_stem_keeps_the_rulers_side(self):
        _log, v = self._dur(True, with_up_stem=False)
        # no up stem was found: not a unison, the ruler's direction stands exactly as before
        self.assertEqual(v.detail["beam_side"], "down")

    def test_the_default_is_OFF_and_a_typo_leaves_it_off(self):
        for word, on in (("", False), ("yess", False), ("0", False), ("1", True), ("true", True)):
            with mock.patch.dict(os.environ, {FLAG: word}):
                self.assertEqual(rhythm.unison_both_stems_enabled(), on, word)
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(rhythm.unison_both_stems_enabled())


if __name__ == "__main__":
    unittest.main()
