"""ROADMAP 2.220 milestone 2 -- the CONSUMER of `Q.HEAD_INK` in `rhythm.adjudicate_duration` (STAGED ADJUDICATE) and its blue mark in
EXPORT (`export.head_ink_guess_of`), flag `OMR_FILL_FROM_STROKES`, default OFF.

Sean 2026-10-28: a black box 2.148 could not read (`not_head_sized`) whose head reads hollow is written blue, half and quarter; a black
2.148 READ is never overturned. After Sean's m2 tiles (2026-10-28): the half-not-hollow rule is DROPPED (a written half marks nothing),
and `not_one_head` is recorded on the verdict (under the head's identity) but marks nothing blue and never removes a note. Each positive has a control that differs only in the evidence (CLAUDE.md rule 7)."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate, export
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import ABSTAIN, READERS, Log, Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import _stem
from tools.omr.tests.test_staged_head_fill_first_2_148 import _head as _head_sized
from tools.omr.tests.test_staged_head_fill_located_2_159 import _part_boxed

FLAG = "OMR_FILL_FROM_STROKES"


def _ink(log, g, value=None, why=None, noh=None):
    if value is not None:
        log.observe(g, Q.HEAD_INK, value, reader=READERS.CV_HEAD_INK, frame="cell:0", margin=0.2, slit=0.4, extent_sp=[1.4, 1.1])
    else:
        log.abstain(g, Q.HEAD_INK, reader=READERS.CV_HEAD_INK, frame="cell:0", reason=why, not_one_head=noh, slit=0.0)


def _decide(log, g, on=True):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


def _w(v):
    return (v.value or {}).get("written")


def _guess(v):
    return (v.detail or {}).get(rhythm.HEAD_INK_GUESS_KEY)


def _arms(build):
    on, off = Log(), Log()
    g1, g2 = build(on), build(off)
    return _decide(on, g1), _decide(off, g2, on=False), on, g1


class TestUnreadBlackReadsHollow(unittest.TestCase):

    def _build(self, *, stem=True, value="hollow", why=None, noh=None):
        def b(log):
            g = _part_boxed(log, located_share=None, stem=stem)
            _ink(log, g, value=value, why=why, noh=noh)
            return g
        return b

    def test_on_its_stem_it_is_a_half_written_blue_with_half_and_quarter(self):
        v_on, v_off, _log, _g = _arms(self._build())
        self.assertNotEqual(_w(v_off), 2.0)
        self.assertIsNone(_guess(v_off))
        self.assertEqual(v_on.outcome, Outcome.DECIDED)
        self.assertEqual(_w(v_on), 2.0)
        g = _guess(v_on)
        self.assertEqual(g["rule"], rhythm.HEAD_INK_RULE_HOLLOW)
        self.assertEqual([c["written"] for c in g["candidates"]], [2.0, 1.0])
        self.assertTrue(v_on.detail["head_fill_first"]["head_ink_hollow"])

    def test_no_stem_keeps_the_black_value_blue_and_never_a_whole(self):
        v_on, v_off, _log, _g = _arms(self._build(stem=False))
        self.assertEqual(_w(v_on), _w(v_off))
        self.assertNotEqual(_w(v_on), 4.0)
        g = _guess(v_on)
        self.assertEqual(g["rule"], rhythm.HEAD_INK_RULE_HOLLOW)
        self.assertEqual([c["written"] for c in g["candidates"]], [_w(v_off), 2.0])

    def test_control_the_ink_reads_filled_nothing_changes(self):
        v_on, v_off, _log, _g = _arms(self._build(value="filled"))
        self.assertEqual((v_on.outcome, v_on.reason, v_on.value), (v_off.outcome, v_off.reason, v_off.value))
        self.assertIsNone(_guess(v_on))

    def test_not_one_head_never_turns_hollow_and_only_marks_blue(self):
        v_on, v_off, _log, _g = _arms(self._build(value=None, why=ABSTAIN.NOT_ONE_HEAD, noh="too_wide"))
        self.assertEqual((v_on.outcome, v_on.value), (v_off.outcome, v_off.value))
        g = _guess(v_on)
        self.assertEqual(g["rule"], rhythm.HEAD_INK_RULE_NOT_ONE_HEAD)
        self.assertEqual(g["candidates"][1]["value"], "not_one_head")
        self.assertEqual(g["files_under"], str(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD))
        self.assertFalse(g["marks_blue"])

    def test_not_one_head_is_recorded_but_export_draws_nothing_blue(self):
        log = Log()
        g = _part_boxed(log, located_share=None)
        _ink(log, g, why=ABSTAIN.NOT_ONE_HEAD, noh="too_wide")
        v = _decide(log, g)
        self.assertEqual(_guess(v)["rule"], rhythm.HEAD_INK_RULE_NOT_ONE_HEAD)
        rec = export.Record({"record": {"observations": [], "abstentions": [], "verdicts": log.to_json()["verdicts"]}})
        self.assertIsNone(export.head_ink_guess_of(rec, g.to_key()))

    def test_control_no_head_ink_row_is_unchanged(self):
        on, off = Log(), Log()
        g1, g2 = _part_boxed(on, located_share=None), _part_boxed(off, located_share=None)
        v1, v2 = _decide(on, g1), _decide(off, g2, on=False)
        self.assertEqual((v1.outcome, v1.reason, v1.value), (v2.outcome, v2.reason, v2.value))
        self.assertIsNone(_guess(v1))

    def test_a_located_hollow_read_by_2_159_stays_read(self):
        """2.159 READ the head on its located box: that is the reading, the ink adds no blue."""
        def b(log):
            g = _part_boxed(log, located_share=0.4)
            _ink(log, g, value="hollow")
            return g
        v_on, v_off, _log, _g = _arms(b)
        self.assertEqual(_w(v_on), 2.0)
        self.assertEqual(_w(v_off), 2.0)
        self.assertIsNone(_guess(v_on))


class TestNeverOverturnARead(unittest.TestCase):

    def test_a_black_2_148_read_is_never_turned_hollow(self):
        def b(log):
            g = _head_sized(log, share=0.0)
            _ink(log, g, value="hollow")
            return g
        v_on, v_off, _log, _g = _arms(b)
        self.assertEqual(v_off.detail["head_fill_first"]["settled"], "black")
        self.assertEqual((v_on.outcome, v_on.value), (v_off.outcome, v_off.value))
        self.assertIsNone(_guess(v_on))


class TestAWrittenHalfThatDoesNotReadHollow(unittest.TestCase):

    def _b(self, value=None, why=None):
        def b(log):
            g = _head_sized(log, share=0.4)
            _ink(log, g, value=value, why=why)
            return g
        return b

    def test_ink_filled_the_half_is_written_plain(self):
        """The dropped half_not_hollow rule (Sean's m2 tiles 0 of 2): a half whose ink reads filled marks nothing."""
        v_on, v_off, _log, _g = _arms(self._b(value="filled"))
        self.assertEqual(_w(v_off), 2.0)
        self.assertEqual(_w(v_on), 2.0)
        self.assertIsNone(_guess(v_on))

    def test_ink_unread_split_the_half_is_written_plain(self):
        v_on, _off, _log, _g = _arms(self._b(why=ABSTAIN.READERS_SPLIT))
        self.assertEqual(_w(v_on), 2.0)
        self.assertIsNone(_guess(v_on))

    def test_control_ink_hollow_the_half_stays_plain(self):
        v_on, _off, _log, _g = _arms(self._b(value="hollow"))
        self.assertEqual(_w(v_on), 2.0)
        self.assertIsNone(_guess(v_on))


class TestExportDrawsItBlue(unittest.TestCase):

    def _rec(self, log):
        return export.Record({"record": {"observations": [], "abstentions": [], "verdicts": log.to_json()["verdicts"]}})

    def test_the_guess_reaches_the_export(self):
        log = Log()
        g = _part_boxed(log, located_share=None)
        _ink(log, g, value="hollow")
        _decide(log, g)
        gs = export.head_ink_guess_of(self._rec(log), g.to_key())
        self.assertIsNotNone(gs)
        self.assertEqual(gs["rule"], rhythm.HEAD_INK_RULE_HOLLOW)
        self.assertEqual(gs["chosen"]["written"], 2.0)
        self.assertEqual(export._guess_fields(self._rec(log), g.to_key())["guess"]["rule"], rhythm.HEAD_INK_RULE_HOLLOW)

    def test_control_flag_off_no_guess(self):
        log = Log()
        g = _part_boxed(log, located_share=None)
        _ink(log, g, value="hollow")
        _decide(log, g, on=False)
        self.assertIsNone(export.head_ink_guess_of(self._rec(log), g.to_key()))


if __name__ == "__main__":
    unittest.main()
