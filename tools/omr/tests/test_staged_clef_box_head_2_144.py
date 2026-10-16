"""ROADMAP 2.144 -- a stemless notehead box wholly inside a clef-sized detector clef box is that clef's ink
(STAGED ADJUDICATE, `adjudicate_notehead_is_not_a_notehead`, flag `OMR_HEAD_INSIDE_A_CLEF_BOX`, default OFF).

Sean 2026-10-16 (Brahms 317803 p3 sys0 staff12 cell8): 'a C clef' boxed as a note. Staff space is 100 canonical units.
The CONTROL_ tests are green with the rule absent or present; each of the others fails if the rule is absent, and each
control fails if the rule is made broader (any clef box, any overlap, a stem ignored, a short box).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, adjudicators            # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q, READERS
from tools.omr.tests.test_staged_duration import CELL, _staff_space

ENV = {"OMR_HEAD_INSIDE_A_CLEF_BOX": "1"}
CLEF_BOX = (250, 50, 270, 330)          # an F clef: 2.7 x 3.3 spaces
BALL = (270, 80, 140, 130)              # the ball: wholly inside it


def _head(log, gi, box, cls="noteheadBlackOnLine"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.NOTEHEAD_CLASS, cls, reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.9,
                category="notehead")
    return g


def _clef(log, gi, box, cls="clefF"):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls,) + tuple(box), reader=READERS.DETECTOR, frame="cell:0", score=0.5,
                category="clef")
    return g


def _stem(log, box):
    x, y, w, h = box
    return log.observe(CELL, Q.STEM, (x, y, w, h), reader=READERS.CV_LINES, frame="cell:0", x0=x, x1=x + w,
                       y_center=y + h / 2.0, image="no_staff", staff_lines_erased=True)


def _nn(log, g):
    adjudicate.run(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


def _fixture(head_box=BALL, clef_box=CLEF_BOX, clef_cls="clefF", stem=None):
    log = Log()
    _staff_space(log, 100)
    h = _head(log, 0, head_box)
    _clef(log, 1, clef_box, clef_cls)
    if stem is not None:
        _stem(log, stem)
    return log, h


class TestHeadInsideAClefBox(unittest.TestCase):
    def test_a_stemless_head_inside_a_clef_box_leaves_the_bar_RED(self):
        log, h = _fixture()
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertTrue(v.value is True and v.reason == "inside_a_clef_box", (v.value, v.reason))
        self.assertGreaterEqual(v.margin, 0.0)

    def test_a_c_clef_lobe_is_refused_too_RED(self):
        log, h = _fixture(head_box=(300, 60, 110, 90), clef_box=(280, 40, 160, 330), clef_cls="clefCAlto")
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertTrue(v.value is True and v.reason == "inside_a_clef_box", (v.value, v.reason))

    def test_flag_is_off_by_default(self):
        from tools.omr.staged.adjudicators import notehead_precision as npz
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(npz.CLEF_BOX_ENV, None)
            self.assertFalse(npz.head_inside_a_clef_box_enabled())
        for on in ("1", "true", "yes", "on"):
            with mock.patch.dict(os.environ, {npz.CLEF_BOX_ENV: on}):
                self.assertTrue(npz.head_inside_a_clef_box_enabled())

    def test_CONTROL_flag_off_the_head_stands(self):
        log, h = _fixture()
        with mock.patch.dict(os.environ, {"OMR_HEAD_INSIDE_A_CLEF_BOX": "0"}):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_real_head_beside_a_clef_survives(self):
        # a note just right of the clef: boxes do not overlap at all
        log, h = _fixture(head_box=(560, 80, 140, 130))
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_head_only_half_inside_survives(self):
        log, h = _fixture(head_box=(450, 80, 140, 130))      # 0.43 of the head box inside
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_stem_touching_the_head_declines_the_rule(self):
        log, h = _fixture(stem=(400, 0, 10, 300))             # along the ball's right edge
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_short_clef_class_box_is_not_a_clef(self):
        # a clef-class box 1.0 space tall (an arc or clutter box): not clef-sized
        log, h = _fixture(head_box=(270, 90, 140, 90), clef_box=(250, 80, 270, 100))
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)

    def test_CONTROL_a_non_clef_box_does_not_count(self):
        log, h = _fixture(clef_cls="slur")
        with mock.patch.dict(os.environ, ENV):
            v = _nn(log, h)
        self.assertFalse(v.value)


if __name__ == "__main__":
    unittest.main()
