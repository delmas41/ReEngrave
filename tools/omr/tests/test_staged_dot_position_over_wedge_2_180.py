"""ROADMAP 2.180 -- a mark the wedge test calls a wedge, with no head above or
below it to point at, standing right of a head at that head's own dot step, is
the head's augmentation dot (`OMR_DOT_POSITION_OVER_WEDGE`, default OFF).

Measured on the 20261018-night Brahms record
(`benchmarks/omr-augmentation-dots-2026-10/FINDINGS.md`): such marks abstain
`wedge_without_a_head` and their note is written PLAIN; in the crops they are
round dots stretched by the staff line they touch. Shape numbers are 2.131's real
wedge (h/w 1.45, thirds 11/7). RED first; every refusal has its control.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import aug_dot_join as AJ
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests.test_staged_dot_position_2_128 import _dot, _head, _jlog, _role

ON = {"OMR_DOT_POSITION_OVER_WEDGE": "1", "OMR_STACCATISSIMO_SHAPE": "1",
      "OMR_DOT_POSITION_JOIN": "1"}
OFF = {"OMR_DOT_POSITION_OVER_WEDGE": "0", "OMR_STACCATISSIMO_SHAPE": "1",
       "OMR_DOT_POSITION_JOIN": "1"}
WEDGE = (1.45, 11, 7, 0.48)
ROUND = (1.0, 11, 11, 0.36)


def _shape(log, glyph, m):
    hw, top, bot, hs = m
    log.observe(glyph, Q.MARK_SHAPE, hw, reader=READERS.CV_MARK_SHAPE,
                frame="cell:0", top=top, bot=bot, h_spaces=hs)


def _case(env, *, dot_pos=5.0, head_pos=5.0, shape=WEDGE, x=112, y=4,
          second_head=None, cls="noteheadBlack"):
    log = _jlog()
    head = _head(log, 0, head_pos, cls=cls)
    if second_head is not None:
        _head(log, 2, second_head[0], x=second_head[1], cls=cls)
    d = _dot(log, 1, x=x, y=y, pos=dot_pos, w=6, h=9)
    _shape(log, d, shape)
    with mock.patch.dict(os.environ, env):
        adjudicate.run(log)
    return log, _role(log, 1), head


class TestWedgeBesideAHead(unittest.TestCase):
    def test_RED_a_wedge_beside_a_space_note_in_its_space_is_its_dot(self):
        log, role, head = _case(ON)
        self.assertEqual((role.outcome, role.value), (Outcome.DECIDED, "augmentation"))
        self.assertEqual(role.reason, "beside_a_head_in_its_dot_space")
        self.assertEqual(role.detail["head"], head.to_key())
        self.assertEqual(role.detail["shape_read_as"], "wedge")
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 1)

    def test_RED_a_line_note_takes_it_in_the_space_above(self):
        log, role, head = _case(ON, head_pos=4.0, dot_pos=3.0, y=0)
        self.assertEqual(role.value, "augmentation")
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 1)

    def test_FLAG_OFF_it_abstains_and_the_note_stays_plain(self):
        log, role, head = _case(OFF)
        self.assertEqual(role.outcome, Outcome.ABSTAINED)
        self.assertEqual(role.reason, "wedge_without_a_head")
        self.assertEqual(log.verdict(Q.DURATION, head).value["dots"], 0)

    def test_DEFAULT_is_OFF(self):
        env = {k: v for k, v in os.environ.items() if k != AJ.DOT_POSITION_OVER_WEDGE_ENV}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(AJ.dot_position_over_wedge_enabled())
        for w in ("1", "on", "true", "yes"):
            with mock.patch.dict(os.environ, {AJ.DOT_POSITION_OVER_WEDGE_ENV: w}):
                self.assertTrue(AJ.dot_position_over_wedge_enabled())

    def test_CONTROL_a_mark_on_a_line_is_not_a_dot(self):
        """Always in a space: a mark measured clearly ON a line is never the dot."""
        _log, role, _h = _case(ON, head_pos=4.0, dot_pos=4.0)
        self.assertNotEqual(role.value, "augmentation")
        self.assertEqual(role.reason, "wedge_without_a_head")

    def test_CONTROL_no_staff_position_cannot_tell(self):
        """Position unknown (`None`) is not a witness: the wedge abstains."""
        _log, role, _h = _case(ON, dot_pos=None)
        self.assertEqual(role.reason, "wedge_without_a_head")

    def test_CONTROL_a_mark_far_right_of_the_head_is_not_its_dot(self):
        _log, role, _h = _case(ON, x=200)
        self.assertEqual(role.reason, "wedge_without_a_head")

    def test_CONTROL_two_heads_placed_alike_cannot_tell(self):
        """Two heads at the same dot step, left of the mark within 0.25 sp of
        each other's placement: two owners fit, nothing is chosen (rule 8).
        Called on the helper itself (two synthetic boxes 2 px apart)."""
        from tools.omr.staged.adjudicators import rhythm as RH
        log = _jlog()
        h0 = _head(log, 0, 5.0)
        h2 = _head(log, 2, 5.0, x=98)
        d = _dot(log, 1, x=112, y=4, pos=5.0, w=6, h=9)

        class _Ev:
            def rows(self, q, scope=None, subject=None):
                return log.rows(q, subject or d) if scope is None else log.rows(q, subject, scope=scope)
        ev = _Ev()
        from tools.omr.staged.record import Kind
        cell = d.at(Kind.CELL)
        keys = [h0.to_key(), h2.to_key()]
        boxes = [(90, 0, 20, 16), (88, 0, 20, 16)]
        with mock.patch.dict(os.environ, ON):
            self.assertIsNone(RH._wedge_beside_a_head(
                ev, cell, "staff/0/0/0", (112, 4, 6, 9), 16.0, keys, boxes, None, True))
            # CONTROL: one of them alone is chosen
            self.assertEqual(RH._wedge_beside_a_head(
                ev, cell, "staff/0/0/0", (112, 4, 6, 9), 16.0, keys[:1], boxes[:1], None, True), keys[0])

    def test_CONTROL_a_round_dot_beside_a_head_is_augmentation_either_way(self):
        for env in (ON, OFF):
            with self.subTest(env=env["OMR_DOT_POSITION_OVER_WEDGE"]):
                _log, role, _h = _case(env, shape=ROUND)
                self.assertEqual(role.value, "augmentation")
                self.assertNotEqual(role.reason, "beside_a_head_in_its_dot_space")

    def test_CONTROL_a_wedge_ABOVE_a_head_stays_its_staccatissimo(self):
        """The 2.131 ruling stands: a wedge that points at a head is that
        head's staccatissimo, flag on or off."""
        _log, role, head = _case(ON, x=97, y=-17)
        self.assertEqual(role.value, "staccatissimo")
        self.assertEqual(role.detail["owner"], head.to_key())


if __name__ == "__main__":
    unittest.main()
