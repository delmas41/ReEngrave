"""ROADMAP 2.79 -- the two other EVALUATE rules that read a `Q.METER` verdict.

`size_measure_rest` is `test_staged_rest_meter_2_79.py`. `reconcile_duration`
and `reinstate_rest_between_staves` read the same top-level numerator/
denominator -- the OPENING segment of the system's verdict -- for every bar of
the system, so in a 6/8 bar of a system that opens in 9/8 the first was
trying to land the bar on 4.5 beats and the second judged a staff's shortfall
against 4.5. A separate change from the rest sizing because it lets
`reconcile_duration` fire on bars it could not fire on before (Brahms 1/i
Breitkopf p0-1: four bars, of which the print shows one wrong note).

The `*_RED` tests fail on the tree without it.
"""
from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import consequences
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, Verdict
from tools.omr.tests import test_staged_rest_between_staves_2_45 as BETWEEN

SEGMENTED = {
    "numerator": 9, "denominator": 8, "raw": "9/8",
    "segments": [
        {"from_cell": 0, "numerator": 9, "denominator": 8, "raw": "9/8"},
        {"from_cell": 1, "numerator": 6, "denominator": 8, "raw": "6/8",
         "corroborated": True},
    ],
}


def _v(log, sub, q, outcome, value, reason="t", detail=None, candidates=()):
    return log.record(Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=q, outcome=outcome,
        value=value, decider="test", reason=reason, detail=detail or {},
        candidates=candidates))


def _system_meter(log, value):
    return _v(log, R.system(0, 0), Q.METER, Outcome.DECIDED, value)




def _dur(beats, levels=0):
    return {"beats": beats, "written": beats, "dots": 0,
            "beam_levels": levels}


class TestReconcileDurationReadsTheSameMeter(unittest.TestCase):
    """`reconcile_duration` re-reads ONE note so the bar lands on its meter;
    it read the opening segment too, so in a 6/8 bar of a system that opens in
    9/8 it was trying to land on 4.5 beats."""

    CELL = R.cell(0, 0, 1, 4)

    def _bar(self, log):
        """1.0 + 1.0 + an eighth read one beam too short = 2.5 beats. In 6/8
        the eighth is a quarter: ONE landing. In 9/8 nothing lands."""
        for g, (b, lv) in enumerate(((1.0, 0), (1.0, 0), (0.5, 1))):
            _v(log, R.glyph(0, 0, 1, 4, g), Q.DURATION, Outcome.DECIDED,
               _dur(b, lv), reason="head_and_marks")
        _v(log, self.CELL, Q.EVENT, Outcome.DECIDED,
           {"events": [{"glyphs": [0]}, {"glyphs": [1]}, {"glyphs": [2]}]})

    def test_a_bar_under_the_returned_meter_lands_on_it_RED(self):
        log = Log()
        meter = _system_meter(log, SEGMENTED)
        self._bar(log)
        out = consequences.reconcile_duration(log, self.CELL, meter)
        self.assertEqual(len(out), 1)
        self.assertEqual(
            log.verdict(Q.DURATION, R.glyph(0, 0, 1, 4, 2)).value["beats"],
            1.0)

    def test_the_SAME_bar_under_the_opening_segment_is_NOT_repaired(self):
        """Control: cell 0 is a 9/8 bar, 2.5 beats lands on nothing, and
        the rule refuses -- the repair above comes from the segment, not from
        a rule that now repairs everything."""
        log = Log()
        meter = _system_meter(log, SEGMENTED)
        cell = R.cell(0, 0, 1, 0)
        for g, (b, lv) in enumerate(((1.0, 0), (1.0, 0), (0.5, 1))):
            _v(log, R.glyph(0, 0, 1, 0, g), Q.DURATION, Outcome.DECIDED,
               _dur(b, lv), reason="head_and_marks")
        _v(log, cell, Q.EVENT, Outcome.DECIDED,
           {"events": [{"glyphs": [0]}, {"glyphs": [1]}, {"glyphs": [2]}]})
        self.assertEqual(consequences.reconcile_duration(log, cell, meter), [])


class TestReinstateRestBetweenStavesReadsTheSameMeter(unittest.TestCase):
    """Sean's 2.45 shape, in a system that opens in 9/8 and returns to 6/8 at
    cell 1 (`CELL_IDX` is 5): the bar is 3.0, the group reinstates."""

    def test_the_whole_group_reinstates_under_the_returned_meter_RED(self):
        meters = []

        def segmented(log, num=6, den=8):
            v = _v(log, R.system(BETWEEN.PAGE, BETWEEN.SYSTEM), Q.METER,
                   Outcome.DECIDED, dict(SEGMENTED))
            meters.append(v)
            return v

        with mock.patch.object(BETWEEN, "_meter", segmented):
            log, meter, lo_rests, up_rests = (
                BETWEEN.TestSeansCase()._build())
        self.assertEqual(meter.value["numerator"], 9)   # the OPENING
        for r in lo_rests:
            out = consequences.reinstate_rest_between_staves(log, r, meter)
            self.assertEqual(len(out), 1, msg=f"{r.to_key()} did not fire")
            self.assertIs(out[0].value, False)
        for r in up_rests:
            self.assertEqual(
                consequences.reinstate_rest_between_staves(log, r, meter), [])


if __name__ == "__main__":
    unittest.main()
