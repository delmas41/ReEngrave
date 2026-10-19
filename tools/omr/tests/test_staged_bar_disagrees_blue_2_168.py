"""ROADMAP 2.168 -- the bar MARKS, never moves, a decided note it disagrees with: `OMR_BAR_DISAGREES_BLUE`, default OFF
(Sean 2026-10-18, DECISIONS). STAGED EVALUATE (`reconcile_duration`'s blocked branch) + EXPORT (`guess_of`).

Under 2.162's block a decided note is never moved. Under this flag the note the old rule WOULD have moved keeps its value and
is written GUESSED (blue) with the bar's alternative as a candidate. Each test has a flag-off control, so removing the mark
turns the flag-on test red."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, export
from tools.omr.staged.record import Outcome, Q
from tools.omr.tests.test_staged_narrowed_bar_2_97 import CELL, _EvalBar

BLOCK = consequences.NARROWED_BAR_LENGTH_UNKNOWN_ENV
FLAG = consequences.BAR_DISAGREES_BLUE_ENV
CONFIRM = consequences.BAR_SUM_CONFIRM_ONLY_ENV
REASON = consequences.BAR_DISAGREES_REASON


def _fire(b, blue):
    env = {BLOCK: "1", CONFIRM: "narrowed", FLAG: "1" if blue else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        return b.fire()


def _decided_bar():
    b = _EvalBar(2, 4)
    d = b.decided(1.0)                       # the quarter the bar would turn into an eighth
    e = b.decided(0.5, levels=1)
    b.decided(1.0, rest=True)
    return b, d, e


class TestMark(unittest.TestCase):

    def test_CONTROL_flag_off_nothing_is_written(self):
        b, d, e = _decided_bar()
        log, out = _fire(b, blue=False)
        self.assertEqual(out, [])
        self.assertNotEqual(log.verdict(Q.DURATION, d).reason, REASON)

    def test_on_the_disputed_note_keeps_its_value_and_carries_the_alternative_RED(self):
        b, d, e = _decided_bar()
        before = {s: b.log.verdict(Q.DURATION, s).value for s in (d, e)}
        log, out = _fire(b, blue=True)
        self.assertEqual(len(out), 1)
        v = log.verdict(Q.DURATION, d)
        self.assertEqual(v.reason, REASON)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.value["beats"], before[d]["beats"])          # the value never changes
        self.assertEqual(v.value["beam_levels"], before[d]["beam_levels"])
        self.assertEqual([c.value["beats"] for c in v.candidates], [1.0, 0.5])
        # the neighbour is not marked: only the note the bar would have moved
        self.assertNotEqual(log.verdict(Q.DURATION, e).reason, REASON)

    def test_on_a_bar_that_fits_marks_nothing(self):
        b = _EvalBar(2, 4)
        b.decided(1.0)
        b.decided(1.0)
        log, out = _fire(b, blue=True)
        self.assertEqual(out, [])

    def test_on_a_bar_holding_a_narrowed_note_marks_nothing(self):
        b = _EvalBar(2, 4)
        b.narrowed()
        b.decided(1.0)
        b.decided(1.0, rest=True)
        log, out = _fire(b, blue=True)
        self.assertEqual(out, [])

    def test_on_two_landings_mark_nothing(self):
        # 2/4 holding two decided quarters and a decided half-length rest-free surplus: two notes can each fix it
        b = _EvalBar(2, 4)
        b.decided(1.0)
        b.decided(1.0)
        b.decided(0.5, levels=1)
        log, out = _fire(b, blue=True)
        self.assertEqual(out, [])            # quarter -> eighth either way: not unique, so no note is singled out


class TestExport(unittest.TestCase):

    def _record(self, blue=True):
        b, d, e = _decided_bar()
        log, out = _fire(b, blue=blue)
        res = {"record": {"observations": [], "abstentions": [],
                          "verdicts": [x.to_json() if hasattr(x, "to_json") else x for x in log.all_verdicts()]}}
        return export.Record(res), d

    def test_the_marked_note_is_GUESSED_with_both_candidates_RED(self):
        rec, d = self._record()
        g = export.guess_of(rec, d.to_key())
        self.assertIsNotNone(g)
        self.assertEqual(g["rule"], REASON)
        self.assertEqual(g["stage"], "EVALUATE")
        self.assertEqual([c["beats"] for c in g["candidates"]], [1.0, 0.5])
        self.assertEqual(g["chosen"]["beats"], 1.0)

    def test_CONTROL_off_the_same_note_is_READ(self):
        rec, d = self._record(blue=False)
        self.assertIsNone(export.guess_of(rec, d.to_key()))

    def test_a_dispute_without_an_alternative_RAISES(self):
        rec, d = self._record()
        v = rec.verdict(Q.DURATION, d.to_key())
        v["candidates"] = v["candidates"][:1]
        with self.assertRaises(RuntimeError):
            export.guess_of(rec, d.to_key())


if __name__ == "__main__":
    unittest.main()
