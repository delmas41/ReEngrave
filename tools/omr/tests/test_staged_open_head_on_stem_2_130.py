"""ROADMAP 2.130 -- dotted half notes read as a whole or a quarter (`OMR_OPEN_HEAD_ON_STEM`, default ON since 2026-10-14, Sean: "Yes").

Sean's 2.127 tiles 9, 10, 13 (Brahms 317803 20261013-night): two heads the detector classed WHOLE with a stem read at their side stayed 4.0
(`stem_value` skips a lone head), one hollow HALF-class head took a flag from the black eighth's stem beside it and became a quarter.
Convention (Sean, DECISIONS 2026-10-09): whole notes never have stems; a hollow note with nothing on its stem is a half; open heads are never
flagged or beamed. RUN RED FIRST on the tree without the change: every flag-ON test fails there; every control passes on both.
NO TEST ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md 6c).
"""

from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS

from tools.omr.tests.test_staged_duration import CELL, SPACE, _flag, _staff_space, _stem, _beam


# ROADMAP 2.173 (`OMR_WHOLE_NEEDS_HOLLOW_NO_STEM` default ON, Sean 2026-10-19/20): this file tests the
# pre-2.173 path (bar held out / old whole value); pinned OFF here.
_PIN_2_173 = None


def setUpModule():
    global _PIN_2_173
    import os as _os
    from unittest import mock as _mock
    _PIN_2_173 = _mock.patch.dict(_os.environ, {"OMR_WHOLE_NEEDS_HOLLOW_NO_STEM": "0"})
    _PIN_2_173.start()


def tearDownModule():
    _PIN_2_173.stop()

ON = {"OMR_OPEN_HEAD_ON_STEM": "1"}


def _ink(log, g, *, center=0.50, ring=0.85, filled=False, off_line=None):
    c, r = (1.0, 1.0) if filled else (center, ring)
    detail = {k: {"best": max(c, r), "best_window": "ring", "windows": {"center": c, "ring": r}} for k in ("ink_raw", "ink_net")}
    if off_line is not None:
        detail["ink_off_line"] = {"best": max(off_line, r), "best_window": "ring", "windows": {"center": off_line, "ring": r}}
    return log.observe(g, Q.NOTEHEAD_INK, round(max(c, r), 4), reader=READERS.CV_NOTEHEAD_INK, frame="cell:0", **detail)


def _head(log, cls, *, stem_x=133, stem_h=50, stem=True, w=26):
    _staff_space(log)
    g = R.glyph(0, 0, 0, 0, 0)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls, 135, 90, w, 14), reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    if stem:
        _stem(log, x=stem_x, y=60, h=stem_h)
    return g


def _verdict(log, g, on=True):
    with mock.patch.dict(os.environ, ON if on else {"OMR_OPEN_HEAD_ON_STEM": "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


class TestAWholeClassHeadWithAStemIsAHalf(unittest.TestCase):

    def test_whole_class_hollow_with_a_flush_stem_is_a_decided_half_RED(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine")
        _ink(log, g)
        v = _verdict(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "whole_class_on_a_stem")
        self.assertEqual(v.value["beats"], 2.0)
        self.assertEqual(v.value["head_fill"], "half")

    def test_a_stem_on_the_right_side_too_RED(self):
        log = Log()
        g = _head(log, "noteheadWholeInSpace", stem_x=157)
        _ink(log, g)
        v = _verdict(log, g)
        self.assertEqual(v.reason, "whole_class_on_a_stem")

    def test_FLAG_OFF_is_the_old_whole(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine")
        _ink(log, g)
        v = _verdict(log, g, on=False)
        self.assertEqual(v.reason, "head_and_marks")
        self.assertEqual(v.value["beats"], 4.0)

    def test_a_filled_whole_class_head_with_a_stem_NARROWS_black_or_half_RED(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine")
        _ink(log, g, filled=True)
        v = _verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "whole_class_filled_on_a_stem")
        self.assertEqual({c.value["beats"] for c in v.candidates}, {1.0, 2.0})

    def test_one_dark_raster_among_hollow_ones_is_not_filled_RED(self):
        """Brahms 6/1/5/8/6: raw 0.92 / net 0.92 / off-line 0.79 -- a hollow head with a line through it."""
        log = Log()
        g = _head(log, "noteheadWholeOnLine")
        _ink(log, g, center=0.92, ring=0.74, off_line=0.79)
        v = _verdict(log, g)
        self.assertEqual(v.reason, "whole_class_on_a_stem")

    # ---- controls: each passes with the flag OFF as well ----
    def test_CONTROL_a_real_whole_note_without_a_stem_stays_whole(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem=False)
        _ink(log, g)
        v = _verdict(log, g)
        self.assertEqual(v.value["beats"], 4.0)
        self.assertNotEqual(v.reason, "whole_class_on_a_stem")

    def test_CONTROL_a_stem_through_the_middle_of_a_whole_is_not_its_stem(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem_x=146)
        _ink(log, g)
        v = _verdict(log, g)
        self.assertEqual(v.value["beats"], 4.0)

    def test_CONTROL_a_short_stroke_at_the_side_is_not_a_stem(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine", stem_h=20)
        _ink(log, g)
        v = _verdict(log, g)
        self.assertEqual(v.value["beats"], 4.0)

    def test_CONTROL_a_half_class_head_with_a_stem_stays_a_half(self):
        log = Log()
        g = _head(log, "noteheadHalfOnLine")
        _ink(log, g)
        v = _verdict(log, g)
        self.assertEqual(v.value["beats"], 2.0)

    def test_CONTROL_a_black_quarter_with_a_stem_stays_a_quarter(self):
        log = Log()
        g = _head(log, "noteheadBlackOnLine")
        _ink(log, g, filled=True)
        _beam(log, y=300, x0=0, x1=10)
        v = _verdict(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)


class TestAFlagOnAnOpenHeadIsNotItsValue(unittest.TestCase):

    def _half_with_flag(self, log, cls="noteheadHalfOnLine"):
        g = _head(log, cls)
        _ink(log, g)
        _flag(log, gi=1, cls="flag8thUp", x=133, y=40, w=12, h=30)
        return g

    def test_a_flag_on_a_hollow_half_class_head_NARROWS_the_half_first_RED(self):
        log = Log()
        g = self._half_with_flag(log)
        v = _verdict(log, g)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "open_head_flag_contradiction")
        self.assertEqual(v.candidates[0].value["beats"], 2.0)
        self.assertIn(1.0, {c.value["beats"] for c in v.candidates})

    def test_FLAG_OFF_is_the_old_quarter(self):
        log = Log()
        g = self._half_with_flag(log)
        v = _verdict(log, g, on=False)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 1.0)

    def test_CONTROL_a_flag_on_a_black_head_is_still_an_eighth(self):
        log = Log()
        g = _head(log, "noteheadBlackOnLine")
        _ink(log, g, filled=True)
        _flag(log, gi=1, cls="flag8thUp", x=133, y=40, w=12, h=30)
        v = _verdict(log, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], 0.5)


if __name__ == "__main__":
    unittest.main()


class TestOnByDefault(unittest.TestCase):
    """Landed ON (Sean, 2026-10-14: "Yes"): no env word means the rule runs; only an explicit off word turns it off."""

    def test_RED_default_is_on_and_off_words_turn_it_off(self):
        from tools.omr.staged.adjudicators import rhythm
        with mock.patch.dict(os.environ, {}):
            os.environ.pop("OMR_OPEN_HEAD_ON_STEM", None)
            self.assertTrue(rhythm.open_head_on_stem_enabled())
        for w in ("0", "false", "no", "off", "OFF"):
            with mock.patch.dict(os.environ, {"OMR_OPEN_HEAD_ON_STEM": w}):
                self.assertFalse(rhythm.open_head_on_stem_enabled(), w)

    def test_RED_a_whole_class_stemmed_head_is_a_half_with_no_env(self):
        log = Log()
        g = _head(log, "noteheadWholeOnLine")
        _ink(log, g)
        with mock.patch.dict(os.environ, {}):
            os.environ.pop("OMR_OPEN_HEAD_ON_STEM", None)
            adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertEqual(v.reason, "whole_class_on_a_stem")
        self.assertEqual(v.value["beats"], 2.0)
