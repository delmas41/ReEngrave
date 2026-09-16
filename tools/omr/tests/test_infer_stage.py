"""The INFER stage's five rules, each asserted rather than described.

⚠️ Every test here names a rule from `infer.py`'s module docstring. If one of
them goes red, the property it names has stopped being true of the machine --
which is the point of enforcing them in the harness rather than in prose.
"""

import os
import unittest
from unittest import mock

from tools.omr.staged import evaluate, infer
from tools.omr.staged.record import (Candidate, Kind, Log, Outcome, Q, Subject,
                                     Verdict)


def _glyph(g=0):
    return Subject(Kind.GLYPH, page=0, system=0, staff=0, cell=0, glyph=g)


def _narrowed(log, sub, values=(1.0, 2.0)):
    v = Verdict(
        id=log._next_id("vrd"), subject=sub, quantity=Q.DURATION,
        outcome=Outcome.NARROWED, value=None, decider="test",
        reason="narrowed_for_the_test",
        candidates=tuple(Candidate({"beats": b}, support=1.0) for b in values))
    return log.record(v)


def _decided(log, sub, beats=1.0):
    v = Verdict(id=log._next_id("vrd"), subject=sub, quantity=Q.DURATION,
                outcome=Outcome.DECIDED, value={"beats": beats},
                decider="test", reason="read")
    return log.record(v)


def _rule(fn, **kw):
    """A one-off rule registered for one test, then removed."""
    kw.setdefault("inference", infer.Inference.COLLAPSE_DURATION_BY_COLUMN)
    kw.setdefault("target", Q.DURATION)
    kw.setdefault("reads", (Q.DURATION,))
    kw.setdefault("scope", Kind.GLYPH)
    kw.setdefault("bound", "the test's own fixture")
    kw.setdefault("sideways", True)
    kw.setdefault("why_witnesses_are_independent", "the test says so")
    return infer.rule(**kw)(fn)


class _WithRule:
    """Install exactly one rule for the duration of a test."""

    def __init__(self, fn, **kw):
        self.fn, self.kw = fn, kw

    def __enter__(self):
        self.saved = list(infer.RULES)
        infer.RULES.clear()
        _rule(self.fn, **self.kw)
        return self

    def __exit__(self, *exc):
        infer.RULES.clear()
        infer.RULES.extend(self.saved)


def _frozen_log():
    log = Log()
    log.freeze()
    return log


class TestTheFlag(unittest.TestCase):
    """⚠️ Default OFF, so the test is an ALLOW-list. A default-OFF flag
    written as a deny-list is switched ON by a typo -- and this stage's whole
    job is putting values in the file that nobody read."""

    def test_off_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(infer.infer_enabled())

    def test_a_typo_does_not_switch_it_on(self):
        for bad in ("", "yess", "ON!", "0", "no", "maybe"):
            with mock.patch.dict(os.environ, {infer.INFER_ENV: bad}):
                self.assertFalse(infer.infer_enabled(), bad)

    def test_the_on_words_work(self):
        for good in ("1", "true", "YES", "on"):
            with mock.patch.dict(os.environ, {infer.INFER_ENV: good}):
                self.assertTrue(infer.infer_enabled(), good)


class TestRule1ItMayNotRunBeforeEvaluate(unittest.TestCase):

    def test_it_refuses_without_evaluates_report(self):
        with self.assertRaises(infer.NotEvaluated):
            infer.run(_frozen_log(), None)

    def test_the_report_is_a_positional_argument(self):
        """⚠️ THE ORDERING IS STRUCTURAL, NOT A CONVENTION. A caller that has
        not run EVALUATE has nothing to pass, so the stage cannot be called
        early even by someone who has never read the docstring."""
        with self.assertRaises(TypeError):
            infer.run(_frozen_log())          # noqa: E1120 -- that is the test


class TestRule2ItMayNotLoosenGather(unittest.TestCase):

    def test_an_unfrozen_log_is_refused(self):
        with self.assertRaises(infer.LogNotFrozen):
            infer.run(Log(), evaluate.Report(fired=[], skipped=[], stubs=[]))


class TestRule3ItMayNotOverturnAReading(unittest.TestCase):

    def test_decided_is_not_inferable(self):
        self.assertNotIn(Outcome.DECIDED, infer.INFERABLE)

    def test_a_proposal_onto_a_decided_verdict_is_refused_and_named(self):
        log = Log()
        sub = _glyph()
        _decided(log, sub, 1.0)
        log.freeze()

        def fn(log_, subject):
            if subject != sub:
                return []
            return [infer.Proposal(subject=sub, value={"beats": 99.0},
                                   reason="should_never_land")]

        with _WithRule(fn):
            rep = infer.run(log, evaluate.Report([], [], []))
        self.assertEqual(rep.inferred, [])
        self.assertIn("prior_is_decided", [s[2] for s in rep.skipped])
        # and the reading is untouched
        self.assertEqual(log.verdict(Q.DURATION, sub).value, {"beats": 1.0})


class TestRule4ItMayNotInventAValue(unittest.TestCase):

    def test_a_value_the_reader_never_admitted_raises(self):
        log = Log()
        sub = _glyph()
        _narrowed(log, sub, (1.0, 2.0))
        log.freeze()

        def fn(log_, subject):
            if subject != sub:
                return []
            return [infer.Proposal(subject=sub, value={"beats": 4.0},
                                   reason="invented")]

        with _WithRule(fn), self.assertRaises(infer.ValueNotAdmitted):
            infer.run(log, evaluate.Report([], [], []))

    def test_an_admitted_candidate_lands(self):
        """The positive control. ⚠️ A battery of refusal tests passes by
        refusing everything, so the accept case is in the same class."""
        log = Log()
        sub = _glyph()
        _narrowed(log, sub, (1.0, 2.0))
        log.freeze()

        def fn(log_, subject):
            if subject != sub:
                return []
            return [infer.Proposal(subject=sub, value={"beats": 2.0},
                                   reason="admitted")]

        with _WithRule(fn):
            rep = infer.run(log, evaluate.Report([], [], []))
        self.assertEqual(len(rep.inferred), 1)
        self.assertEqual(log.verdict(Q.DURATION, sub).value, {"beats": 2.0})

    def test_it_survives_a_json_round_trip_of_the_candidate(self):
        """⚠️ `reinfer.py` rebuilds a log from a SAVED record, where a tuple
        has become a list. Comparing with a raw `==` would make a rebuilt arm
        admit nothing, which reads as *the rule is inert* -- this repository's
        most expensive failure shape."""
        log = Log()
        sub = _glyph()
        v = Verdict(id=log._next_id("vrd"), subject=sub, quantity=Q.DURATION,
                    outcome=Outcome.NARROWED, value=None, decider="test",
                    reason="r",
                    candidates=(Candidate({"beats": 1.0, "members": (1, 2)}, 1.0),
                                Candidate({"beats": 2.0}, 0.5)))
        log.record(v)
        log.freeze()

        def fn(log_, subject):
            if subject != sub:
                return []
            # the same value as it comes back from JSON: a LIST, not a tuple
            return [infer.Proposal(subject=sub,
                                   value={"beats": 1.0, "members": [1, 2]},
                                   reason="round_tripped")]

        with _WithRule(fn):
            rep = infer.run(log, evaluate.Report([], [], []))
        self.assertEqual(len(rep.inferred), 1)


class TestRule5ItSupersedesVisibly(unittest.TestCase):

    def setUp(self):
        self.log = Log()
        self.sub = _glyph()
        self.prior = _narrowed(self.log, self.sub, (1.0, 2.0))
        self.log.freeze()

        def fn(log_, subject):
            if subject != self.sub:
                return []
            return [infer.Proposal(subject=self.sub, value={"beats": 2.0},
                                   reason="admitted")]

        with _WithRule(fn):
            self.rep = infer.run(self.log, evaluate.Report([], [], []))
        self.v = self.log.verdict(Q.DURATION, self.sub)

    def test_the_narrowing_is_still_in_the_record(self):
        found = self.log.verdicts(Q.DURATION, self.sub)
        self.assertIn(self.prior.id, [x.id for x in found])
        kept = [x for x in found if x.id == self.prior.id][0]
        self.assertEqual(kept.outcome, Outcome.NARROWED)
        self.assertEqual(len(kept.candidates), 2)

    def test_it_names_what_it_superseded(self):
        self.assertEqual(self.v.supersedes, self.prior.id)
        self.assertIn(self.prior.id, self.v.basis)

    def test_it_is_labelled(self):
        self.assertTrue(infer.is_inferred(self.v))
        self.assertTrue(self.v.decider.startswith(infer.DECIDER_PREFIX))
        self.assertIs(self.v.detail["inferred"], True)

    def test_the_label_survives_serialisation(self):
        self.assertTrue(infer.is_inferred(self.v.to_json()))

    def test_a_rule_cannot_write_an_unlabelled_verdict(self):
        """⚠️ THE STRUCTURAL CLAIM: a rule returns a `Proposal`, which has no
        `decider` field at all, so there is no path by which an inference
        reaches the log unstamped."""
        self.assertNotIn("decider", infer.Proposal.__dataclass_fields__)
        self.assertNotIn("outcome", infer.Proposal.__dataclass_fields__)

    def test_the_candidates_travel_forward(self):
        self.assertEqual(len(self.v.candidates), 2)

    def test_inferred_verdicts_is_a_query_not_a_list(self):
        self.assertEqual([x.id for x in infer.inferred_verdicts(self.log)],
                         [self.v.id])


class TestTheStageBoundary(unittest.TestCase):
    """⚠️ The plan's own testable form of the boundary.

    *No EVALUATE consequence may contain a tie-break*, and its mirror: INFER
    is the ONLY stage allowed to collapse a narrowing. If a consequence ever
    starts choosing, the boundary has moved and nothing would otherwise
    notice.
    """

    def test_evaluate_skips_a_narrowed_cause_rather_than_choosing(self):
        import inspect
        src = inspect.getsource(evaluate.run)
        self.assertIn("cause_narrowed", src)
        self.assertIn("Outcome.NARROWED", src)

    def test_only_infer_may_supersede_a_narrowing(self):
        """Run over a log where both stages have acted."""
        log = Log()
        sub = _glyph()
        _narrowed(log, sub, (1.0, 2.0))
        log.freeze()

        def fn(log_, subject):
            if subject != sub:
                return []
            return [infer.Proposal(subject=sub, value={"beats": 1.0},
                                   reason="ok")]

        with _WithRule(fn):
            infer.run(log, evaluate.Report([], [], []))

        by_id = {v.id: v for v in log.all_verdicts()}
        for v in log.all_verdicts():
            if v.supersedes and by_id[v.supersedes].outcome is Outcome.NARROWED:
                self.assertTrue(
                    infer.is_inferred(v),
                    f"{v.decider} superseded a NARROWED verdict and is not an "
                    f"inference. The stage boundary has moved.")


class TestIndependence(unittest.TestCase):
    """Hazard (b), computed rather than argued."""

    def test_witnesses_sharing_provenance_count_once(self):
        log = Log()
        shared = log.observe(Subject(Kind.STAFF, page=0, system=0, staff=0),
                             Q.STAFF_SPACING, 10.0, reader="geometry",
                             frame="page")
        a = Verdict(id=log._next_id("vrd"), subject=_glyph(1),
                    quantity=Q.DURATION, outcome=Outcome.DECIDED,
                    value={"beats": 1.0}, decider="t", reason="r",
                    basis=(shared.id,))
        b = Verdict(id=log._next_id("vrd"), subject=_glyph(2),
                    quantity=Q.DURATION, outcome=Outcome.DECIDED,
                    value={"beats": 1.0}, decider="t", reason="r",
                    basis=(shared.id,))
        log.record(a)
        log.record(b)
        self.assertEqual(len(infer.independent_groups(log, (a.id, b.id))), 1)

    def test_witnesses_resting_on_different_ink_count_twice(self):
        """The positive control for the same mechanism."""
        log = Log()
        o1 = log.observe(Subject(Kind.STAFF, page=0, system=0, staff=0),
                         Q.STAFF_SPACING, 10.0, reader="geometry", frame="page")
        o2 = log.observe(Subject(Kind.STAFF, page=0, system=0, staff=1),
                         Q.STAFF_SPACING, 10.0, reader="geometry", frame="page")
        a = Verdict(id=log._next_id("vrd"), subject=_glyph(1),
                    quantity=Q.DURATION, outcome=Outcome.DECIDED,
                    value={"beats": 1.0}, decider="t", reason="r",
                    basis=(o1.id,))
        b = Verdict(id=log._next_id("vrd"), subject=_glyph(2),
                    quantity=Q.DURATION, outcome=Outcome.DECIDED,
                    value={"beats": 1.0}, decider="t", reason="r",
                    basis=(o2.id,))
        log.record(a)
        log.record(b)
        self.assertEqual(len(infer.independent_groups(log, (a.id, b.id))), 2)

    def test_it_is_recorded_on_the_verdict(self):
        log = Log()
        sub = _glyph()
        _narrowed(log, sub, (1.0, 2.0))
        o1 = log.observe(Subject(Kind.STAFF, page=0, system=0, staff=0),
                         Q.STAFF_SPACING, 10.0, reader="geometry", frame="page")
        w = Verdict(id=log._next_id("vrd"), subject=_glyph(9),
                    quantity=Q.DURATION, outcome=Outcome.DECIDED,
                    value={"beats": 1.0}, decider="t", reason="r",
                    basis=(o1.id,))
        log.record(w)
        log.freeze()

        def fn(log_, subject):
            if subject != sub:
                return []
            return [infer.Proposal(subject=sub, value={"beats": 1.0},
                                   reason="ok", witnesses=(w.id,))]

        with _WithRule(fn):
            infer.run(log, evaluate.Report([], [], []))
        v = log.verdict(Q.DURATION, sub)
        self.assertEqual(len(v.correlated), 1)
        self.assertEqual(v.detail["n_independent_witnesses"], 1)


class TestNoRulesIsAnError(unittest.TestCase):

    def test_an_empty_stage_is_not_an_empty_result(self):
        saved = list(infer.RULES)
        infer.RULES.clear()
        try:
            with mock.patch.object(infer, "_ensure_rules",
                                   side_effect=infer.NoRulesRegistered("x")):
                with self.assertRaises(infer.NoRulesRegistered):
                    infer.run(_frozen_log(), evaluate.Report([], [], []))
        finally:
            infer.RULES.clear()
            infer.RULES.extend(saved)


class TestEveryRuleDeclaresItsDiscipline(unittest.TestCase):
    """Derived from the registry, never a hand list."""

    def setUp(self):
        infer._ensure_rules()

    def test_every_rule_states_a_bound(self):
        for r in infer.RULES:
            self.assertGreater(len(r.bound.split()), 8, r.inference)

    def test_every_rule_says_why_its_witnesses_are_independent(self):
        for r in infer.RULES:
            self.assertGreater(
                len(r.why_witnesses_are_independent.split()), 8, r.inference)

    def test_no_rule_may_choose_by_support_alone(self):
        for r in infer.RULES:
            self.assertTrue(r.forbids_argmax, r.inference)

    def test_every_rule_declares_what_it_reads(self):
        for r in infer.RULES:
            self.assertTrue(r.reads, r.inference)
            for q in r.reads:
                self.assertIn(q, Q.all())


class TestScoringConflict(unittest.TestCase):
    """⚠️ Do not score an inference by the quantity it consumed."""

    def setUp(self):
        infer._ensure_rules()
        self.r = infer.RULES[0]

    def test_the_column_rule_does_not_read_the_meter(self):
        """So `bar_fill.py` is a legitimate independent self-check for it."""
        self.assertEqual(infer.scoring_conflict(self.r, (Q.METER,)), ())

    def test_a_conflict_is_reported_when_there_is_one(self):
        self.assertEqual(infer.scoring_conflict(self.r, (Q.DURATION,)),
                         (Q.DURATION,))


if __name__ == "__main__":
    unittest.main()
