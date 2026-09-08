"""Candidate sets — "it is one of these", and what it buys.

⚠️ COHERENCE, NOT ACCURACY. And ⚠️ nothing here treats `support` as a
probability: the assertions are on ORDER and on membership, never on a
normalised number.
"""

from __future__ import annotations

import unittest

from tools.omr.staged import adjudicate, evaluate
from tools.omr.staged import adjudicators, consequences  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.record import (Candidate, Log, Outcome, Q, READERS,
                                     Scope, Subject, Verdict)
from tools.omr.tests.test_staged_duration import CELL, X, _beam, _note


class TestTheShapeIsEnforced(unittest.TestCase):
    def test_abstained_may_not_carry_candidates(self):
        """⚠️ A decision holding survivors has NARROWED. Collapsing the two
        throws away the narrowing, which is the whole point."""
        with self.assertRaises(ValueError):
            Verdict(id="v", subject=R.DOCUMENT, quantity=Q.CLEF,
                    outcome=Outcome.ABSTAINED, value=None, decider="t",
                    reason="r", candidates=(Candidate("alto", 1.0),
                                            Candidate("tenor", 1.0)))

    def test_narrowed_needs_at_least_two(self):
        with self.assertRaises(ValueError):
            Verdict(id="v", subject=R.DOCUMENT, quantity=Q.CLEF,
                    outcome=Outcome.NARROWED, value=None, decider="t",
                    reason="r", candidates=(Candidate("alto", 1.0),))

    def test_narrowed_may_not_carry_a_value(self):
        with self.assertRaises(ValueError):
            Verdict(id="v", subject=R.DOCUMENT, quantity=Q.CLEF,
                    outcome=Outcome.NARROWED, value="alto", decider="t",
                    reason="r", candidates=(Candidate("alto", 2.0),
                                            Candidate("tenor", 1.0)))

    def test_candidates_are_ordered_best_first(self):
        from tools.omr.staged.adjudicate import Ruling
        r = Ruling.narrow([Candidate("b", 1.0), Candidate("a", 3.0)], "r")
        self.assertEqual([c.value for c in r.candidates], ["a", "b"])

    def test_support_is_not_a_probability(self):
        """⚠️ Asserted so a later hand cannot quietly normalise it. This
        project measured an uncalibrated estimator at ECE 0.1277, failing
        WORST exactly where a consumer would set its bar."""
        from tools.omr.staged.adjudicate import Ruling
        r = Ruling.narrow([Candidate("a", 3.0), Candidate("b", 2.0)], "r")
        self.assertNotAlmostEqual(sum(c.support for c in r.candidates), 1.0)


class TestABeamReadingIsNativelyASet(unittest.TestCase):
    """⚠️ The fault this fixes: `_beam_levels` returned an int, collapsing
    "two, possibly three" at the moment of counting -- `pos_float` rounded
    away at `pitch_resolver.py:181`, one layer up."""

    def test_an_unambiguous_note_still_DECIDES(self):
        """⚠️ Sets are for readings that ARE sets. A decision with one answer
        must not be dressed as a set to look uniform."""
        log = Log()
        g = _note(log, 0, levels=1)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.detail["levels_certain"],
                         v.detail["levels_possible"])

    def test_a_stroke_ending_AT_the_note_narrows(self):
        """A beam stroke ends at the last stem it joins, so a note at the end
        of a group is genuinely "under it, possibly not"."""
        log = Log()
        g = _note(log, 0)
        _beam(log, y=40, x0=X - 60, x1=X - 5)      # stops just short
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertIs(v.outcome, Outcome.NARROWED)
        self.assertEqual(v.reason, "beams_ambiguous")
        self.assertEqual([c.value["beam_levels"] for c in v.candidates],
                         [0, 1])

    def test_the_certain_reading_is_ordered_first(self):
        log = Log()
        g = _note(log, 0)
        _beam(log, y=40, x0=X - 60, x1=X - 5)
        adjudicate.run(log)
        v = log.verdict(Q.DURATION, g)
        self.assertGreater(v.candidates[0].support, v.candidates[1].support)


class TestAConsumerNeedNotCollapseEarly(unittest.TestCase):
    def test_admitted_returns_the_whole_set(self):
        """⚠️ A consumer can carry the ambiguity forward and let its OWN
        evidence settle it -- which is exactly what `reconcile_duration` does
        with the meter."""
        from tools.omr.staged.adjudicate import Evidence
        log = Log()
        g = _note(log, 0)
        _beam(log, y=40, x0=X - 60, x1=X - 5)
        adjudicate.run(log)
        # ⚠️ METER's spec, because it DECLARES Q.DURATION in `wants` --
        # the declaration is enforced, so a probe cannot read what it did
        # not declare.
        ev = Evidence(log, g, adjudicate.REGISTRY[Q.METER])
        self.assertEqual(len(ev.admitted(Q.DURATION)), 2)

    def test_admitted_returns_ONE_for_a_decided_verdict(self):
        from tools.omr.staged.adjudicate import Evidence
        log = Log()
        g = _note(log, 0, levels=1)
        adjudicate.run(log)
        ev = Evidence(log, g, adjudicate.REGISTRY[Q.METER])
        self.assertEqual(len(ev.admitted(Q.DURATION)), 1)


class TestTheMeterResolvesWhatTheBeamsCouldNot(unittest.TestCase):
    """⚠️ THE PAYOFF. `reconcile_duration` searches the levels a note ADMITS
    rather than arithmetic +/-1, so the meter chooses among readings the beams
    actually support."""

    def _bar(self, meter, raw):
        """A half note in its own column (2.0, unambiguous) plus a quarter
        under a stroke that stops just short of it (1.0 **or** 0.5).

        ⚠️ The half note sits at a DIFFERENT x on purpose: beams are
        cell-scoped, so two notes in one column see the same strokes and BOTH
        narrow -- which is a fixture bug that looks exactly like the repair
        refusing.
        """
        log = Log()
        _note(log, 0, "noteheadHalf", x=400)        # 2.0, its own column
        g = _note(log, 1)                           # 1.0 or 0.5
        _beam(log, y=40, x0=X - 60, x1=X - 5)
        log.observe(R.staff(0, 0, 0), Q.METER_TEMPLATE, meter,
                    reader=READERS.TEMPLATE, frame="header_window",
                    score=0.9, raw=raw)
        return log, g

    def test_the_meter_settles_a_narrowed_note(self):
        log, g = self._bar(meter=(5, 8), raw="5/8")   # 2.5 beats
        adjudicate.run(log)
        self.assertIs(log.verdict(Q.DURATION, g).outcome, Outcome.NARROWED)
        report = evaluate.run(log)
        fired = [f for f in report.fired if f[0] == "reconcile_duration"]
        self.assertTrue(fired, "the 0.5 reading lands 2.0 + 0.5 = 2.5")
        now = log.verdict(Q.DURATION, g)
        self.assertIs(now.outcome, Outcome.DECIDED)
        self.assertEqual(now.value["beats"], 0.5)
        self.assertTrue(now.value["reconciled"])

    def test_a_bar_that_already_fits_is_left_alone(self):
        log, g = self._bar(meter=(3, 4), raw="3/4")   # 2.0 + 1.0 = 3.0
        adjudicate.run(log)
        report = evaluate.run(log)
        self.assertEqual([f for f in report.fired
                          if f[0] == "reconcile_duration"], [])

    def test_it_refuses_when_no_admitted_reading_lands_the_bar(self):
        """⚠️ An arithmetic +/-1 the STROKES DO NOT SUPPORT is no longer
        reachable -- which is what makes this bound strictly better."""
        log, g = self._bar(meter=(7, 8), raw="7/8")   # 3.5, unreachable
        adjudicate.run(log)
        report = evaluate.run(log)
        self.assertEqual([f for f in report.fired
                          if f[0] == "reconcile_duration"], [])

    def test_the_superseded_reading_stays_on_the_record(self):
        log, g = self._bar(meter=(5, 8), raw="5/8")
        adjudicate.run(log)
        before = log.verdict(Q.DURATION, g)
        evaluate.run(log)
        self.assertIsNotNone(log.row(before.id))
        self.assertEqual(log.verdict(Q.DURATION, g).supersedes, before.id)


if __name__ == "__main__":
    unittest.main()
