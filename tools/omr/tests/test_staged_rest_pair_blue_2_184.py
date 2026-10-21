"""ROADMAP 2.184 -- one ink boxed under two rest classes: keep the stronger box, written GUESSED (blue), both classes carried.

STAGED ADJUDICATE `family_precision._duplicate_box_refusal` / `adjudicate_rest_is_not_a_rest`, reason `rest_pair_stronger`,
flag `OMR_REST_PAIR_STRONGER_BLUE` (default OFF; only `1/true/yes/on` enables).

CONVENTION ASSUMED: of two class readings of one ink the detector's more confident one is right more often than not (Sean's tiles
2026-10-21, 2.182a: 6 of 7 real pairs). WHAT WOULD FALSIFY IT: blind tiles where the stronger class is wrong on most. NOT CONFIRMED
by Sean for this lane. The write is blue (GUESSED), so a wrong class is visible and fixable.

RED first: OFF (and main) both boxes are refused `rest_is_a_duplicate_box`; the ON tests fail there. Every refusal/keep test has a
control in the same class that can fail.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_family_refusals import _page_box_at_step, _staff_geometry
from tools.omr.tests.test_staged_rest_placement_2_33 import _run

ENV = "OMR_REST_PAIR_STRONGER_BLUE"


def _rest(log, gi, cls, score, *, x_c=200.0, w_c=100.0, h_c=300.0, page_w=20.0):
    g = R.glyph(0, 0, 0, 0, gi)
    log.observe(g, Q.GLYPH_BOX, (cls, x_c, 100.0, w_c, h_c), reader=READERS.DETECTOR, frame="cell:0", score=score,
                category="rest", bbox_page_px=list(_page_box_at_step(4.0, x0=500.0, x1=500.0 + page_w, thickness=60.0)))
    log.observe(g, Q.REST, cls, reader=READERS.DETECTOR, frame="cell:0", score=score, category="rest")
    return g


def _decide(pair, flag, extra_env=None):
    """pair = [(class, score, x_c, w_c), ...]; returns (log, [subjects])."""
    log = Log()
    _staff_geometry(log)
    gs = [_rest(log, i, c, s, x_c=x, w_c=w) for i, (c, s, x, w) in enumerate(pair)]
    env = dict(extra_env or {})
    env[ENV] = "1" if flag else "0"
    with mock.patch.dict(os.environ, env, clear=False):
        _run(log, Q.REST_IS_NOT_A_REST)
    return log, gs


class TestRestPairStrongerBlue(unittest.TestCase):

    PAIR = [("rest8th", 0.43, 200.0, 100.0), ("rest16th", 0.37, 201.0, 100.0)]

    def test_CONTROL_off_refuses_both(self):
        log, (a, b) = _decide(self.PAIR, False)
        for g in (a, b):
            v = log.verdict(Q.REST_IS_NOT_A_REST, g)
            self.assertIs(v.value, True)
            self.assertEqual(v.reason, "rest_is_a_duplicate_box")

    def test_on_the_stronger_is_narrowed_and_the_weaker_refused(self):
        log, (a, b) = _decide(self.PAIR, True)
        va, vb = (log.verdict(Q.REST_IS_NOT_A_REST, g) for g in (a, b))
        self.assertEqual(va.outcome, Outcome.NARROWED)
        self.assertEqual(va.reason, "rest_pair_stronger")
        self.assertIs(vb.value, True)
        self.assertEqual(vb.reason, "rest_is_a_duplicate_box")
        self.assertEqual(vb.detail["duplicate_of"], log.rows(Q.GLYPH_BOX, a)[-1].id)

    def test_on_both_classes_and_the_margin_ride_on_the_winner(self):
        log, (a, b) = _decide(self.PAIR, True)
        va = log.verdict(Q.REST_IS_NOT_A_REST, a)
        cands = va.detail["rest_pair"]["candidates"]
        self.assertEqual([c["class"] for c in cands], ["rest8th", "rest16th"])
        self.assertAlmostEqual(va.margin, 0.06, places=3)

    def test_on_the_higher_confidence_one_wins_whatever_the_order(self):
        log, (a, b) = _decide([("rest8th", 0.30, 200.0, 100.0), ("restQuarter", 0.66, 201.0, 100.0)], True)
        self.assertEqual(log.verdict(Q.REST_IS_NOT_A_REST, b).outcome, Outcome.NARROWED)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, a).value, True)

    def test_on_a_three_way_cluster_keeps_exactly_one(self):
        log, gs = _decide([("rest8th", 0.40, 200.0, 100.0), ("rest16th", 0.55, 201.0, 100.0), ("restQuarter", 0.30, 202.0, 100.0)], True)
        kept = [g for g in gs if log.verdict(Q.REST_IS_NOT_A_REST, g).outcome == Outcome.NARROWED]
        self.assertEqual(kept, [gs[1]])

    def test_on_a_winner_a_later_rule_refuses_stays_refused_with_its_own_reason(self):
        """The stem-wide quarter box (0.45 spaces, the 2.150 width floor) is the stronger of the pair: refused by the rule that
        names it, so the ink is NOT written -- the guard Sean's tiles 2 and 9 ask for."""
        log, (a, b) = _decide([("restQuarter", 0.60, 200.0, 45.0), ("rest8th", 0.40, 201.0, 45.0)], True,
                              {"OMR_REST_WIDTH_FLOOR": "1"})
        va = log.verdict(Q.REST_IS_NOT_A_REST, a)
        self.assertIs(va.value, True)
        self.assertEqual(va.reason, "rest_narrower_than_its_class")

    def test_CONTROL_same_class_twins_behave_as_before_with_the_flag_on(self):
        log, (a, b) = _decide([("rest8th", 0.43, 200.0, 100.0), ("rest8th", 0.37, 201.0, 100.0)], True)
        self.assertIs(log.verdict(Q.REST_IS_NOT_A_REST, a).value, False)
        v = log.verdict(Q.REST_IS_NOT_A_REST, b)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_is_a_duplicate_box")

    def test_CONTROL_a_lone_rest_is_untouched(self):
        log, (a,) = _decide([("rest8th", 0.43, 200.0, 100.0)], True)
        v = log.verdict(Q.REST_IS_NOT_A_REST, a)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_the_export_guess_carries_both_classes(self):
        log, (a, b) = _decide(self.PAIR, True)
        rec = SX.Record({"record": {"observations": [], "abstentions": [], "verdicts": log.to_json()["verdicts"]}})
        sub = "glyph/0/0/0/0/0"
        g = SX.rest_pair_guess_of(rec, sub)
        self.assertIsNotNone(g)
        self.assertEqual(g["rule"], "rest_pair_stronger")
        self.assertEqual([c["value"] for c in g["candidates"]], ["rest8th", "rest16th"])
        self.assertEqual(g["chosen"], {"value": "rest8th"})
        self.assertIsNone(SX.rest_pair_guess_of(rec, 'glyph/0/0/0/0/1'))


if __name__ == "__main__":
    unittest.main()
