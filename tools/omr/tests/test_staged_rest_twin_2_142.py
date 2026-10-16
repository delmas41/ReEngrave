"""ROADMAP 2.142 -- a stemless notehead box on a non-whole rest box's ink is the rest (STAGED ADJUDICATE,
`adjudicate_notehead_is_not_a_notehead`, flag `OMR_HEAD_IS_A_REST_TWIN`, default OFF).

Sean 2026-10-15 (`out/print/2.141-fix23-review` tile 3): an eighth REST boxed as a black head was written as a note.
Geometry is a 22 x 17 px box (staff space 100 canonical, a head ~1.2 sp wide) on an eighth-rest box of the same ink.
Every CONTROL_ test is green with the rule absent or present, so a rule that refuses everything cannot pass.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import CELL, _staff_space

ENV = {"OMR_HEAD_IS_A_REST_TWIN": "1"}


def _head(log, gi, box, cls="noteheadBlackOnLine"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _rest(log, gi, box, cls="rest8th"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="rest")
    return g


def _stem(log, box):
    x, y, w, h = box
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES, frame="cell:0", x0=x, x1=x + w,
                       y_center=y + h / 2.0, image="no_staff", staff_lines_erased=True)


def _nn(log, g):
    adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


def _fixture(head_box=(300, 200, 130, 100), rest_box=(300, 200, 130, 100), rest_cls="rest8th", stem=None):
    log = Log()
    _staff_space(log, 100)
    h = _head(log, 0, head_box)
    _rest(log, 1, rest_box, rest_cls)
    if stem is not None:
        _stem(log, stem)
    return log, h


class TestRestTwin(unittest.TestCase):
    def test_a_stemless_head_on_an_eighth_rest_box_leaves_the_bar_RED(self):
        log, h = _fixture()
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertTrue(v.value is True and v.reason == "is_a_rest_twin", (v.value, v.reason))
        self.assertGreaterEqual(v.margin, 0.0)

    def test_CONTROL_flag_off_the_head_stands(self):
        log, h = _fixture()
        with mock.patch.dict(os.environ, {"OMR_HEAD_IS_A_REST_TWIN": ""}):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_stem_touching_the_head_declines_the_rule(self):
        log, h = _fixture(stem=(420, 0, 10, 300))        # runs along the head's right edge
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_whole_rest_twin_is_not_this_rules(self):
        log, h = _fixture(rest_cls="restWhole")
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertNotEqual(v.reason, "is_a_rest_twin")

    def test_CONTROL_a_rest_box_beside_the_head_is_no_twin(self):
        log, h = _fixture(rest_box=(700, 200, 130, 100))
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_beam_class_box_on_the_head_is_no_witness(self):
        """29 Litolff heads under a `beam` box are slur-starts and real heads (FINDINGS 2.142): not a twin."""
        log = Log()
        _staff_space(log, 100)
        h = _head(log, 0, (300, 200, 130, 100))
        g = R.glyph(0, 0, 0, 0, 1)
        log.observe(g, Q.GLYPH_BOX, ("beam", 300, 200, 130, 100), reader=READERS.DETECTOR, frame="cell:0",
                    score=0.9, category="beam")
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)


if __name__ == "__main__":
    unittest.main()
