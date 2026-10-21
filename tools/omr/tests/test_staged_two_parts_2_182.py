"""ROADMAP 2.182 -- two parts sharing one staff (`OMR_TWO_PARTS_ONE_STAFF`, default OFF) and the rest chain
(`OMR_REST_CHAIN_KEPT_OUTRANKS`, default OFF). STAGED ADJUDICATE. Microscopic fixtures (injected directions, durations,
positions), the style of `test_staged_voices.py`."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import two_parts
from tools.omr.staged.record import Log, Outcome, Q, READERS, Verdict
from tools.omr.tests.test_staged_voices import (CELL, _direction, _duration, _head_pf, _meter, _position,
                                                _rest_positioned, _spacing, _staff_geometry)

ON = {two_parts.ENV: "1"}
OFF = {two_parts.ENV: "0"}


def _run(log):
    log.freeze()
    adjudicate._ensure_decisions()
    adjudicate.run(log, order=(Q.EVENT, Q.VOICES))
    return log.verdict(Q.VOICES, CELL)


def _note(log, gi, x, direction, beats, pos):
    g = _head_pf(log, gi, x, 0, page_x=x, page_y=0.0)
    if direction:
        _direction(log, g, direction)
    _duration(log, g, beats)
    _position(log, g, pos)
    return g


def _upper_lower(log):
    """3/4: the upper part three quarters (stems up, high), the lower a half (stem down, low; a dot unread, so it does
    not fill -- Sean's rule 2 cannot fire), not lined up."""
    _spacing(log)
    _meter(log, 3, 4)
    _note(log, 0, 120, "up", 1.0, 1.0)
    _note(log, 1, 400, "up", 1.0, 0.0)
    _note(log, 2, 700, "up", 1.0, 1.0)
    _note(log, 3, 250, "down", 2.0, 6.0)


class TestTwoPartsByStemsAndHeight(unittest.TestCase):
    def test_OFF_the_bar_abstains_as_on_main(self):
        with mock.patch.dict(os.environ, OFF):
            log = Log()
            _upper_lower(log)
            v = _run(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "no_voice_convention_fits")

    def test_ON_upper_stems_up_above_lower_stems_down_is_two_parts(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _upper_lower(log)
            v = _run(log)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, two_parts.BY_STEMS)
        self.assertEqual(v.value["voices"], [[0, 1, 2], [3]])

    def test_CONTROL_one_line_whose_stems_flip_at_the_middle_is_not_split(self):
        """One line: the HIGH notes stem down, the LOW notes stem up -- the opposite order. Must stay unsplit."""
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _spacing(log)
            _meter(log, 3, 4)
            _note(log, 0, 120, "down", 1.0, 1.0)
            _note(log, 1, 400, "up", 1.0, 7.0)
            _note(log, 2, 700, "up", 2.0, 6.0)      # overfull: 4 quarters in 3/4
            v = _run(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)

    def test_the_bar_sum_never_picks_the_split(self):
        """Two parts that do NOT each fill the bar are still two parts (written red at EXPORT), never refused for it."""
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _spacing(log)
            _meter(log, 3, 4)
            _note(log, 0, 120, "up", 1.0, 1.0)
            _note(log, 1, 400, "up", 1.0, 0.0)       # upper sums 2.0, not 3.0
            _note(log, 3, 250, "down", 3.0, 6.0)
            v = _run(log)
        self.assertEqual(v.reason, two_parts.BY_STEMS)

    def test_rule_3_still_comes_first(self):
        """A merged line that sums to the meter stays ONE voice (Sean 2026-09-29), even with the parts' order."""
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _spacing(log)
            _meter(log, 3, 4)
            _note(log, 0, 120, "up", 1.0, 1.0)
            _note(log, 1, 400, "up", 1.0, 0.0)
            _note(log, 3, 250, "down", 1.0, 6.0)
            v = _run(log)
        self.assertEqual(v.reason, "one_voice_sums")

    def test_an_unread_stem_goes_to_the_likelier_part_and_is_named_guessed(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _upper_lower(log)
            _note(log, 4, 550, None, 1.0, 7.0)       # low head, stem unread -> lower part, GUESSED
            v = _run(log)
        self.assertEqual(v.reason, two_parts.BY_STEMS)
        self.assertIn(4, v.value["voices"][1])
        self.assertNotIn(4, v.value["voices"][0])
        self.assertEqual(v.value["voice_guessed"], [4])

    def test_a2_in_the_bar_means_one_line(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _upper_lower(log)
            log.observe(R.glyph(0, 0, 0, 0, 90000), Q.DIRECTION_WORD, "a2", reader=READERS.TESSERACT,
                        frame="page", terms=["a2"], category="part")
            v = _run(log)
        self.assertIs(v.outcome, Outcome.ABSTAINED)


class TestOnePartResting(unittest.TestCase):
    """The case the splitter gave up on (2.167c): one part plays (stems down), the other only rests (a rest high)."""

    def _bar(self, log, rest_y):
        _spacing(log, px=20.0)
        _staff_geometry(log)
        _meter(log, 2, 4)
        _note(log, 0, 120, "down", 1.0, 6.0)
        _note(log, 1, 400, "down", 1.0, 6.0)
        _rest_positioned(log, 2, 250, center_y=rest_y)
        _duration(log, R.glyph(0, 0, 0, 0, 2), 2.0)

    def test_ON_a_rest_high_with_down_stems_is_two_parts_one_resting(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            self._bar(log, rest_y=10.0)            # step 7 -- high
            v = _run(log)
        self.assertEqual(v.reason, two_parts.BY_RESTS)
        self.assertEqual(v.value["voices"], [[2], [0, 1]])

    def test_OFF_it_is_one_voice(self):
        with mock.patch.dict(os.environ, OFF):
            log = Log()
            self._bar(log, rest_y=10.0)
            v = _run(log)
        self.assertEqual(v.reason, "one_voice")

    def test_CONTROL_a_high_rest_beside_one_line_high_notes_stems_down_is_one_line(self):
        """Heads ABOVE the middle line stem down in ONE line too -- a high rest beside them is no witness of a part."""
        with mock.patch.dict(os.environ, ON):
            log = Log()
            _spacing(log, px=20.0)
            _staff_geometry(log)
            _meter(log, 2, 4)
            _note(log, 0, 120, "down", 1.0, 1.0)
            _note(log, 1, 400, "down", 1.0, 2.0)
            _rest_positioned(log, 2, 250, center_y=10.0)
            _duration(log, R.glyph(0, 0, 0, 0, 2), 2.0)
            v = _run(log)
        self.assertEqual(v.reason, "one_voice")

    def test_CONTROL_an_unread_stem_blocks_the_resting_split(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            self._bar(log, rest_y=10.0)
            _note(log, 3, 600, None, 1.0, 6.0)
            v = _run(log)
        self.assertEqual(v.reason, "one_voice")

    def test_CONTROL_a_rest_far_above_the_staff_is_another_staffs(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            self._bar(log, rest_y=-40.0)           # step 12 -- two spaces above the top line
            v = _run(log)
        self.assertEqual(v.reason, "one_voice")

    def test_CONTROL_a_centred_rest_is_one_line(self):
        with mock.patch.dict(os.environ, ON):
            log = Log()
            self._bar(log, rest_y=40.0)            # step 4 -- the middle line
            v = _run(log)
        self.assertEqual(v.reason, "one_voice")


class TestTheExportMarksTheGuess(unittest.TestCase):
    def test_marked_once_blue_and_never_over_another_guess(self):
        from tools.omr.staged.export_two_parts import mark_voice_guessed
        a = {"glyph": "glyph/0/0/0/0/4"}
        b = {"glyph": "glyph/0/0/0/0/5", "guess": {"rule": "other"}}
        streams = [[{"noteheads": [b]}], [{"noteheads": [a]}]]
        self.assertEqual(mark_voice_guessed(streams, [4, 5]), 1)
        self.assertEqual(a["guess"]["rule"], "voice_guessed")
        self.assertEqual(a["guess"]["chosen"], {"voice": 2})
        self.assertEqual(b["guess"]["rule"], "other")
        self.assertEqual(mark_voice_guessed(streams, [4]), 0)


class TestTheRestChain(unittest.TestCase):
    """Part B: a rest refused `rest_is_a_duplicate_box` because the box that outranked it was itself refused (here by a
    human, the simplest independent refusal) must not lose. A refused box cannot outrank a kept one."""

    def _cell(self, log, *, cls_b="rest8th"):
        from tools.omr.tests.test_staged_duplicate_rest import _rest_box
        a = _rest_box(log, 0, "rest8th", x_c=100.0, y_c=100.0, score=0.5)
        b = _rest_box(log, 1, cls_b, x_c=120.0, y_c=100.0, score=0.7)
        log.observe(b, Q.HUMAN_BOX_VERDICT, "not_a_symbol", reader=READERS.SEAN, frame="review:box",
                    sidecar="t.json", action="act-0001")
        return a, b

    def _run(self, log):
        log.freeze()
        adjudicate._ensure_decisions()
        adjudicate.run(log, order=(Q.REST_IS_NOT_A_REST,))
        return log

    def test_OFF_the_weaker_rest_loses_to_a_refused_box(self):
        with mock.patch.dict(os.environ, {"OMR_REST_CHAIN_KEPT_OUTRANKS": "0"}):
            log = Log()
            a, b = self._cell(log)
            self._run(log)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, a).reason, "rest_is_a_duplicate_box")
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, b).reason, "human_not_a_symbol")

    def test_ON_the_weaker_rest_is_kept(self):
        with mock.patch.dict(os.environ, {"OMR_REST_CHAIN_KEPT_OUTRANKS": "1"}):
            log = Log()
            a, b = self._cell(log)
            self._run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, a).value, False)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, b).reason, "human_not_a_symbol")

    def test_ON_a_refused_box_of_another_class_does_not_refuse_it_either(self):
        with mock.patch.dict(os.environ, {"OMR_REST_CHAIN_KEPT_OUTRANKS": "1"}):
            log = Log()
            a, _b = self._cell(log, cls_b="rest16th")
            self._run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, a).value, False)

    def test_CONTROL_ON_a_kept_stronger_box_still_wins(self):
        from tools.omr.tests.test_staged_duplicate_rest import _rest_box
        with mock.patch.dict(os.environ, {"OMR_REST_CHAIN_KEPT_OUTRANKS": "1"}):
            log = Log()
            lo = _rest_box(log, 0, "rest8th", x_c=100.0, y_c=100.0, score=0.5)
            hi = _rest_box(log, 1, "rest8th", x_c=120.0, y_c=100.0, score=0.7)
            self._run(log)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, lo).reason, "rest_is_a_duplicate_box")
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, hi).value, False)

    def test_CONTROL_ON_a_kept_box_of_another_class_still_refuses_both(self):
        from tools.omr.tests.test_staged_duplicate_rest import _rest_box
        with mock.patch.dict(os.environ, {"OMR_REST_CHAIN_KEPT_OUTRANKS": "1"}):
            log = Log()
            a = _rest_box(log, 0, "rest8th", x_c=100.0, y_c=100.0, score=0.5)
            b = _rest_box(log, 1, "rest16th", x_c=105.0, y_c=100.0, score=0.4)
            self._run(log)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, a).reason, "rest_is_a_duplicate_box")
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, b).reason, "rest_is_a_duplicate_box")

    def test_ON_a_box_that_lost_outranks_nobody(self):
        """a < b < c in score; b overlaps both, a and c do not overlap: c beats b, so a stands."""
        from tools.omr.tests.test_staged_duplicate_rest import _rest_box
        with mock.patch.dict(os.environ, {"OMR_REST_CHAIN_KEPT_OUTRANKS": "1"}):
            log = Log()
            a = _rest_box(log, 0, "rest8th", x_c=100.0, y_c=100.0, score=0.5)
            b = _rest_box(log, 1, "rest8th", x_c=160.0, y_c=100.0, score=0.6)
            c = _rest_box(log, 2, "rest8th", x_c=220.0, y_c=100.0, score=0.7)
            self._run(log)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, a).value, False)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, b).reason, "rest_is_a_duplicate_box")
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, c).value, False)


if __name__ == "__main__":
    unittest.main()
