"""ROADMAP 2.173 (Sean 2026-10-19 "Yes"): a WHOLE-class box on a rest's ink is the rest (`on_a_rest`); on a meter the meter reader READ at this
cell it is the meter (`on_a_read_meter`). Flag `OMR_WHOLE_NEEDS_HOLLOW_NO_STEM`. Whole-class boxes only: a black head is never touched.
Every CONTROL passes with the rule absent or present, so a rule that refuses everything cannot pass.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space

ON = {"OMR_WHOLE_NEEDS_HOLLOW_NO_STEM": "1"}
OFF = {"OMR_WHOLE_NEEDS_HOLLOW_NO_STEM": "0"}


def _box(log, gi, box, cls, cell=0, rest=False):
    g = R.glyph(0, 0, 0, cell, gi)
    if rest:
        log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    else:
        log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="rest" if rest else "notehead")
    return g


def _meter_read(log, cell=None):
    st = R.staff(0, 0, 0)
    if cell is None:
        log.observe(st, Q.METER_TEMPLATE, (9, 8), reader=READERS.DETECTOR, frame="staff:0", raw="9/8")
    else:
        log.observe(st, Q.METER_TEMPLATE_AT_BAR, (9, 8), reader=READERS.DETECTOR, frame="staff:0", raw="9/8", cell=cell)


def _nn(log, g, env=ON):
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestWholeOnARest(unittest.TestCase):
    def _fx(self, rest_box=(300, 270, 130, 80)):
        log = Log()
        _staff_space(log, 100)
        h = _box(log, 0, (300, 200, 130, 100), "noteheadWholeInSpace")
        _box(log, 1, rest_box, "restQuarter", rest=True)
        return log, h

    def test_a_whole_class_box_on_a_rest_box_is_the_rest_RED(self):
        log, h = self._fx()
        v = _nn(log, h)
        self.assertTrue(v.value is True and v.reason == "on_a_rest", (v.value, v.reason))

    def test_FLAG_OFF_the_whole_box_stands(self):
        log, h = self._fx()
        self.assertFalse(_nn(log, h, OFF).value)

    def test_CONTROL_a_rest_a_space_away_leaves_a_real_whole_alone(self):
        log, h = self._fx(rest_box=(300, 600, 130, 80))
        self.assertFalse(_nn(log, h).value)

    def test_CONTROL_a_black_head_on_a_rest_box_is_not_this_rules(self):
        log = Log()
        _staff_space(log, 100)
        g = _box(log, 0, (300, 200, 130, 100), "noteheadBlackOnLine")
        _box(log, 1, (300, 220, 130, 80), "restQuarter", rest=True)
        self.assertNotEqual(_nn(log, g).reason, "on_a_rest")


class TestWholeOnAReadMeter(unittest.TestCase):
    def _fx(self, read=True, cell=0, partner_gap=70, second_cls="noteheadWholeInSpace", at_bar=False):
        log = Log()
        _staff_space(log, 100)
        a = _box(log, 0, (40, 100, 130, 100), "noteheadWholeInSpace", cell=cell)
        _box(log, 1, (40, 100 + partner_gap, 130, 100), second_cls, cell=cell)
        if read:
            _meter_read(log, cell if at_bar else None)
        return log, a

    def test_the_leftmost_stacked_pair_on_a_read_meter_is_the_meter_RED(self):
        log, a = self._fx()
        v = _nn(log, a)
        self.assertTrue(v.value is True and v.reason == "on_a_read_meter", (v.value, v.reason))

    def test_a_change_bar_read_at_this_cell_counts_RED(self):
        log, a = self._fx(at_bar=True)
        self.assertEqual(_nn(log, a).reason, "on_a_read_meter")

    def test_FLAG_OFF_nothing_changes(self):
        log, a = self._fx()
        self.assertFalse(_nn(log, a, OFF).value)

    def test_CONTROL_no_meter_read_at_this_cell_nothing_fires(self):
        log, a = self._fx(read=False)
        self.assertFalse(_nn(log, a).value)

    def test_CONTROL_a_read_for_another_cell_does_not_fire_here(self):
        log = Log()
        _staff_space(log, 100)
        a = _box(log, 0, (40, 100, 130, 100), "noteheadWholeInSpace", cell=2)
        _box(log, 1, (40, 170, 130, 100), "noteheadWholeInSpace", cell=2)
        _meter_read(log, cell=5)
        self.assertFalse(_nn(log, a).value)

    def test_CONTROL_a_lone_whole_note_with_a_meter_read_stands(self):
        log = Log()
        _staff_space(log, 100)
        a = _box(log, 0, (400, 100, 130, 100), "noteheadWholeInSpace")
        _meter_read(log)
        self.assertFalse(_nn(log, a).value)

    def test_CONTROL_a_chord_to_the_right_of_the_meter_pair_stands(self):
        """Digits stand before every note: only the LEFTMOST pair is the meter."""
        log = Log()
        _staff_space(log, 100)
        _box(log, 0, (40, 100, 130, 100), "noteheadWholeInSpace")
        _box(log, 1, (40, 170, 130, 100), "noteheadWholeInSpace")
        c = _box(log, 2, (500, 100, 130, 100), "noteheadWholeInSpace")
        _box(log, 3, (500, 170, 130, 100), "noteheadWholeInSpace")
        _meter_read(log)
        self.assertFalse(_nn(log, c).value)

    def test_CONTROL_a_far_apart_pair_is_not_a_digit_pair(self):
        log, a = self._fx(partner_gap=400)
        self.assertFalse(_nn(log, a).value)


class TestStackedColumn(unittest.TestCase):
    """Digits boxed piecemeal (a 6 over an 8 = three loops): a column at one x spanning more than a whole chord can."""

    def _fx(self, left_note=False):
        log = Log()
        _staff_space(log, 100)
        top = _box(log, 0, (400, 100, 130, 100), "noteheadWholeInSpace")
        _box(log, 1, (400, 280, 130, 100), "noteheadWholeInSpace")
        _box(log, 2, (400, 460, 130, 100), "noteheadWholeOnLine")
        if left_note:
            _box(log, 3, (40, 100, 130, 100), "noteheadBlackOnLine")
        _meter_read(log)
        return log, top

    def test_a_tall_column_at_one_x_on_a_read_meter_is_the_meter_RED(self):
        log, g = self._fx()
        self.assertEqual(_nn(log, g).reason, "on_a_read_meter")

    def test_CONTROL_a_note_to_its_left_means_these_are_not_the_numerals(self):
        log, g = self._fx(left_note=True)
        self.assertFalse(_nn(log, g).value)

    def test_CONTROL_flag_off(self):
        log, g = self._fx()
        self.assertFalse(_nn(log, g, OFF).value)


if __name__ == "__main__":
    unittest.main()
