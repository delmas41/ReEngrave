"""ROADMAP 2.270: a box the shape and the slot call a whole rest is checked against the INK under it.

Sean 2026-11-05 answered 16 refused boxes: 8 whole rests, 8 not (a quarter, three eighths, two dotted halves, an F-clef fragment, a
tremolo slash). The reader said "whole rest" for all 16 because it measured the detector's box and never the ink. Each veto below is
paired with the rest it leaves alone, and every one is flag-gated (default OFF = the old reading exactly).
"""

from __future__ import annotations

import os
import unittest

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_whole_rest_ink import SLOT_Y, _glyph, _run, _staff, _verdict


def _ink(log, g, value, height_sp):
    log.observe(g, Q.HEAD_INK, value, reader=READERS.CV_HEAD_INK, frame="page", margin=0.06,
                extent_sp=[1.3, height_sp])


class _Flag(unittest.TestCase):
    ENV = ()

    def setUp(self):
        self._old = {k: os.environ.get(k) for k in (rhythm.WHOLE_REST_FROM_INK_ENV, rhythm.WHOLE_REST_STEM_RULE_ENV)}
        for k in self._old:
            os.environ.pop(k, None)
        for k in self.ENV:
            os.environ[k] = "1"

    def tearDown(self):
        for k, v in self._old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestFromInk(_Flag):
    ENV = (rhythm.WHOLE_REST_FROM_INK_ENV,)

    def _verdict(self, value, height, stem=False):
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        _ink(log, g, value, height)
        if stem:
            log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [0.0, 0.9], reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK, frame="page")
        return _verdict(_run(log), g)

    def test_a_flat_filled_bar_is_a_whole_rest_and_its_ink_was_read(self):
        v = self._verdict("filled", 0.5)
        self.assertIs(v.value, True)
        self.assertTrue(v.detail["ink"]["ink_read"])

    def test_the_same_box_with_a_head_tall_ink_is_not(self):
        v = self._verdict("filled", 1.1)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ink_is_head_tall")

    def test_ink_narrower_than_a_head_is_neither_rest_nor_head(self):
        """Sean's tile 12: half a sharp sign (0.62 sp wide, 1.5 tall) was freed as a note."""
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        log.observe(g, Q.HEAD_INK, "filled", reader=READERS.CV_HEAD_INK, frame="page", margin=0.06, extent_sp=[0.62, 1.49])
        v = _verdict(_run(log), g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ink_not_head_shaped")

    def test_a_hollow_one_is_not(self):
        v = self._verdict("hollow", 0.5)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "ink_is_hollow")

    def test_a_stem_through_it_is_not(self):
        v = self._verdict("filled", 0.5, stem=True)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "has_a_stem")

    def test_ink_on_both_sides_of_a_stem_is_a_slash_not_a_head(self):
        log = Log()
        _staff(log)
        a = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        b = _glyph(log, 1, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        log.observe(a, Q.NOTEHEAD_STEM_CROSS_INK, [0.58, 0.82], reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK, frame="page",
                    left_share=0.41, right_share=0.59)
        log.observe(b, Q.NOTEHEAD_STEM_CROSS_INK, [0.0, 0.9], reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK, frame="page",
                    left_share=0.0, right_share=1.0)
        _run(log)
        self.assertEqual(_verdict(log, a).reason, "straddles_a_stem")
        self.assertEqual(_verdict(log, b).reason, "has_a_stem")

    def test_no_ink_reading_stays_decided_but_is_not_marked_read(self):
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        v = _verdict(_run(log), g)
        self.assertIs(v.value, True)
        self.assertFalse(v.detail["ink"]["ink_read"])


class TestStemRuleAlone(_Flag):
    ENV = (rhythm.WHOLE_REST_STEM_RULE_ENV,)

    def test_a_stem_vetoes_and_a_tall_ink_does_not(self):
        log = Log()
        _staff(log)
        a = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        b = _glyph(log, 1, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        log.observe(a, Q.NOTEHEAD_STEM_CROSS_INK, [0.0, 0.9], reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK, frame="page")
        _ink(log, b, "filled", 1.3)
        _run(log)
        self.assertEqual(_verdict(log, a).reason, "has_a_stem")
        self.assertIs(_verdict(log, b).value, True)


class TestOffIsTheOldReading(_Flag):
    def test_flags_off_a_stem_and_a_tall_ink_change_nothing(self):
        log = Log()
        _staff(log)
        g = _glyph(log, 0, 0, cy=SLOT_Y, h_spaces=0.7, aspect=2.1)
        _ink(log, g, "hollow", 1.5)
        log.observe(g, Q.NOTEHEAD_STEM_CROSS_INK, [0.0, 0.9], reader=READERS.CV_NOTEHEAD_STEM_CROSS_INK, frame="page")
        v = _verdict(_run(log), g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "shape_and_position_agree")
        self.assertFalse(SX.whole_rest_from_ink_enabled())


if __name__ == "__main__":
    unittest.main()
