"""ROADMAP 2.176 -- a head box standing on ink another reading owns (STAGED ADJUDICATE `adjudicate_notehead_is_not_a_notehead`,
reasons `on_the_staffs_leading_barline` and `on_another_symbols_box`; flag `OMR_HEAD_ON_ANOTHER_MARK`, default OFF).

CONVENTION ASSUMED: nothing is printed at the left end of a system's first bar but the system barline; one ink is one mark, so a
head box inside a clef box the detector scored at least as high, with no stem on it, is that mark. WHAT WOULD FALSIFY IT: a print-confirmed head with no stem the finder saw inside such a box. NOT CONFIRMED beyond two plates.
Every CONTROL_ test is green with the rule absent or present, and each refusal test goes RED when the rule is removed.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import head_on_mark as HM
from tools.omr.staged.record import Log, Q, READERS

ON = {HM.ENV: "1"}
# canonical frame: 100 per staff space; page frame: 20 px per space, cell box starts at x=400
CELL_BOX = [400.0, 100.0, 700.0, 300.0]


def _fixture(cell=1, head_page_x0=440.0, conf=0.3, other=None, other_conf=0.5, stem=None):
    """One head glyph (canonical x derived from its page x) and optionally one other-class box / one stem in the same cell."""
    log = Log()
    c = R.cell(0, 0, 0, cell)
    log.observe(c, Q.CELL_BOX, CELL_BOX, reader=READERS.GEOMETRY, frame="cell:%d" % cell)
    log.observe(c, Q.CELL_STAFF_SPACE, 100.0, reader=READERS.GEOMETRY, frame="cell:%d" % cell)
    g = R.glyph(0, 0, 0, cell, 0)
    cx = (head_page_x0 - 400.0) * 5
    cls = "noteheadBlackInSpace"
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:%d" % cell, score=conf)
    log.observe(g, Q.GLYPH_CONF, conf, reader=READERS.DETECTOR, frame="cell:%d" % cell)
    log.observe(g, Q.GLYPH_BOX, (cls, cx, 450.0, 130.0, 100.0), reader=READERS.DETECTOR, frame="cell:%d" % cell,
                score=conf, category="notehead", bbox_page_px=[head_page_x0, 190.0, head_page_x0 + 26.0, 210.0])
    if other is not None:
        name, ox, oy, ow, oh = other
        o = R.glyph(0, 0, 0, cell, 1)
        log.observe(o, Q.GLYPH_BOX, (name, ox, oy, ow, oh), reader=READERS.DETECTOR, frame="cell:%d" % cell,
                    score=other_conf, category="other", bbox_page_px=[400.0 + ox / 5, 100.0 + oy / 5,
                                                                      400.0 + (ox + ow) / 5, 100.0 + (oy + oh) / 5])
        log.observe(o, Q.GLYPH_CONF, other_conf, reader=READERS.DETECTOR, frame="cell:%d" % cell)
    if stem is not None:
        log.observe(c, Q.STEM, stem, reader=READERS.GEOMETRY, frame="cell:%d" % cell)
    return log, g, cx


def _nn(log, g):
    adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestLeadingBarline(unittest.TestCase):

    def test_the_refusal_needs_the_rule(self):
        """RED when the rule is removed: a head box at the left end of a system's first cell is the barline."""
        log, g, _ = _fixture(cell=0, head_page_x0=402.0)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertTrue(v.value is True and v.reason == "on_the_staffs_leading_barline", (v.value, v.reason))
        self.assertGreater(v.margin, 0.0)

    def test_CONTROL_flag_off_the_box_stands(self):
        log, g, _ = _fixture(cell=0, head_page_x0=402.0)
        with mock.patch.dict(os.environ, {HM.ENV: "0"}):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_default_is_off(self):
        log, g, _ = _fixture(cell=0, head_page_x0=402.0)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(HM.ENV, None)
            self.assertFalse(HM.enabled())
            self.assertFalse(_nn(log, g).value)

    def test_CONTROL_a_later_bar_at_the_same_edge_is_kept(self):
        log, g, _ = _fixture(cell=1, head_page_x0=402.0)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_head_two_spaces_into_the_first_bar_is_kept(self):
        log, g, _ = _fixture(cell=0, head_page_x0=440.0)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)


class TestAnotherMark(unittest.TestCase):

    def _on_mark(self, name, **kw):
        # a box 3 x 2 spaces round the head box (canonical 100 per space; head at cx, 450, 130 x 100)
        _, _, cx = _fixture(cell=1, head_page_x0=440.0)
        return _fixture(cell=1, head_page_x0=440.0, other=(name, cx - 20, 430, 170, 140), **kw)

    def test_CONTROL_an_accidental_box_is_not_this_rules(self):
        """Tried and dropped (Litolff: real heads in the same ink as an accidental): the head stands."""
        log, g, _ = self._on_mark("accidentalFlat", conf=0.3, other_conf=0.6)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_curled_rest_box_is_not_this_rules(self):
        log, g, _ = self._on_mark("rest8th", conf=0.3, other_conf=0.6)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_the_refusal_needs_the_rule_clef(self):
        # a clef box that starts 2 spaces into the cell and holds the head box whole
        log, g, _ = _fixture(cell=1, head_page_x0=440.0, conf=0.3, other=("clefF", 200.0, 300.0, 700.0, 400.0), other_conf=0.6)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertTrue(v.value is True and v.reason == "on_another_symbols_box", (v.value, v.reason))

    def test_CONTROL_a_clef_box_far_into_the_bar_is_not_a_clef(self):
        # the clef box starts 7 spaces into the cell and holds the head box whole
        log, g, _ = _fixture(cell=1, head_page_x0=440.0 + 60.0, conf=0.6,
                             other=("clefF", 700.0, 300.0, 900.0, 400.0), other_conf=0.2)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_the_detector_preferred_the_head_keeps_it(self):
        log, g, _ = _fixture(cell=1, head_page_x0=440.0, conf=0.8, other=("clefF", 200.0, 300.0, 700.0, 400.0), other_conf=0.4)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_stem_on_the_head_keeps_it(self):
        _, _, cx = _fixture(cell=1, head_page_x0=440.0)
        log, g, _ = _fixture(cell=1, head_page_x0=440.0, conf=0.3, other=("clefF", 200.0, 300.0, 700.0, 400.0),
                             other_conf=0.6, stem=(cx + 100.0, 300.0, 20.0, 500.0))
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_whole_rest_box_is_not_this_rules(self):
        log, g, _ = self._on_mark("restWhole", conf=0.3, other_conf=0.6)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_a_small_overlap_keeps_it(self):
        # the clef box covers only the head's left sliver
        _, _, cx = _fixture(cell=1, head_page_x0=440.0)
        log, g, _ = _fixture(cell=1, head_page_x0=440.0, conf=0.3, other=("clefF", 200.0, 300.0, cx - 100.0, 400.0),
                             other_conf=0.6)
        with mock.patch.dict(os.environ, ON):
            v = _nn(log, g)
        self.assertFalse(v.value)

    def test_CONTROL_flag_off_the_box_stands(self):
        log, g, _ = _fixture(cell=1, head_page_x0=440.0, conf=0.3, other=("clefF", 200.0, 300.0, 700.0, 400.0), other_conf=0.6)
        with mock.patch.dict(os.environ, {HM.ENV: "0"}):
            v = _nn(log, g)
        self.assertFalse(v.value)


if __name__ == "__main__":
    unittest.main()
