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
    # ⚠️ A ONE-OFF RULE IS ALWAYS ON. `run()` honours each rule's own switch
    # since 2026-09-21, and while the default switch is `OMR_INFER` (default
    # ON since 2026-09-23, roadmap 2.3) a test process's environment is not
    # controlled -- so without this every test here would depend on whatever
    # `OMR_INFER` happens to be set to outside the test, which is the purest
    # form of *a test named for a hazard it does not reach*. The switch
    # mechanism itself is covered by `TestRunHonoursEachRulesOwnGate`, which
    # is what stops this default from taking the coverage with it.
    kw.setdefault("switch", infer.Switch("OMR_TEST_ALWAYS_ON", lambda: True))
    return infer.rule(**kw)(fn)


class _WithRule:
    """Install exactly one rule for the duration of a test."""

    def __init__(self, fn, **kw):
        self.fn, self.kw = fn, kw

    def __enter__(self):
        # ⚠️⚠️ LOAD BEFORE SAVING, or this helper PERMANENTLY EMPTIES THE
        # STAGE for the rest of the process. `infer._ensure_rules` imports
        # `inferences` only `if not RULES`; once that module is in
        # `sys.modules` the import is a no-op and nothing re-registers. So a
        # `_WithRule` that entered while `RULES` was still empty saved `[]`,
        # restored `[]` on exit, and every later test reading `infer.RULES`
        # saw a stage with no rules -- which raises `NoRulesRegistered` or, in
        # a `next(...)` over the registry, a bare `StopIteration` in an
        # unrelated file. Found 2026-09-23 when `test_infer_clef_gap` passed
        # alone and failed in the suite.
        infer._ensure_rules()
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
    """⚠️ Default ON since 2026-09-23 (roadmap 2.3, Sean's decision -- three
    subjects checked against the print, all three corrected by wiring
    `Q.GLYPH_OWNER` in; see
    `benchmarks/omr-infer-duration-print-2026-09/FINDINGS.md` §7-§9 and
    `benchmarks/omr-infer-default-2026-09/FINDINGS.md`), so the test is a
    DENY-list. A default-ON flag written as an allow-list is switched OFF by
    a typo -- `OMR_INFER=` or `OMR_INFER=yess` would silently turn a shipped
    stage back into the bypass it used to be."""

    def test_on_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(infer.infer_enabled())

    def test_a_typo_does_not_switch_it_off(self):
        for bad in ("1", "yess", "ON!", "true", "maybe", "TRUE"):
            with mock.patch.dict(os.environ, {infer.INFER_ENV: bad}):
                self.assertTrue(infer.infer_enabled(), bad)

    def test_the_off_words_work(self):
        """⚠️ THE POSITIVE CONTROL. Without this, the deny-list above could
        be `lambda: True` unconditionally and every test in this class would
        still pass -- a flag that can never fail is not a flag."""
        for good in ("0", "", "false", "NO", "off"):
            with mock.patch.dict(os.environ, {infer.INFER_ENV: good}):
                self.assertFalse(infer.infer_enabled(), good)


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
        """⚠️ REWRITTEN 2026-09-23 FROM A SOURCE-TEXT ASSERTION TO A
        BEHAVIOURAL ONE. It used to `inspect.getsource(evaluate.run)` and look
        for the strings `cause_narrowed` and `Outcome.NARROWED`; roadmap
        2.10 moved that loop body into `evaluate._pass` so both passes share
        one copy of the rule ORDER, and the test went red on code that was
        still correct -- the failure mode CLAUDE.md §6c names when it forbids
        new source-text assertions. What it always meant to say is asserted
        directly now: a NARROWED cause is REPORTED, apart from an abstention,
        and no consequence is written from it."""
        log = Log()
        staff = Subject(Kind.STAFF, page=0, system=0, staff=0)
        head = Subject(Kind.GLYPH, page=0, system=0, staff=0, cell=0, glyph=0)
        log.record(Verdict(
            id=log._next_id("vrd"), subject=staff, quantity=Q.CLEF,
            outcome=Outcome.NARROWED, value=None, decider="adjudicate_clef",
            reason="margin_below_floor",
            candidates=(Candidate("alto", 1.0), Candidate("tenor", 1.0))))
        log.observe(head, Q.NOTEHEAD_STAFF_POSITION, 4.0,
                    reader="cv_lines", frame="cell:0")
        log.freeze()

        rep = evaluate.run(log)
        self.assertIn(("restate_pitch", staff.to_key(), "cause_narrowed"),
                      rep.skipped)
        self.assertNotIn(("restate_pitch", staff.to_key(), "cause_abstained"),
                         rep.skipped)
        self.assertIsNone(log.verdict(Q.PITCH, head))

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
class TestRunHonoursEachRulesOwnGate(unittest.TestCase):
    """⚠️ THE COVERAGE `_rule`'s ALWAYS-ON DEFAULT WOULD OTHERWISE TAKE WITH
    IT. Every other test in this file installs a rule that always fires, so
    nothing else here can tell a switch that is honoured from one that is
    ignored. These four can: each was run RED against `run()` iterating
    `RULES` unconditionally, which is exactly what it did before the rules
    gained separate defaults."""

    def _one(self, switch):
        seen = []

        def fn(log, subject):
            seen.append(subject)
            return ()

        with _WithRule(fn, switch=switch):
            log = _frozen_log()
            _decided(log, _glyph())
            rep = infer.run(log, evaluate.Report([], [], []))
        return seen, rep

    def test_a_gated_off_rule_does_not_run(self):
        seen, _ = self._one(infer.Switch("OMR_TEST_OFF", lambda: False))
        self.assertEqual(seen, [], "the rule's own switch said no and it ran")

    def test_a_gated_off_rule_is_NAMED_rather_than_omitted(self):
        """*Inert* and *nothing to do* must not be the same report."""
        _, rep = self._one(infer.Switch("OMR_TEST_OFF", lambda: False))
        self.assertEqual([d[1] for d in rep.disabled], ["OMR_TEST_OFF"])
        self.assertIn("disabled", rep.to_json())

    def test_a_gated_on_rule_runs_and_is_not_named(self):
        """The positive control: without it the two assertions above pass for
        a `run()` that refuses every rule."""
        seen, rep = self._one(infer.Switch("OMR_TEST_ON", lambda: True))
        self.assertTrue(seen)
        self.assertEqual(rep.disabled, [])

    def test_the_flag_name_travels_with_its_predicate(self):
        """⚠️ A report naming the wrong flag is worse than one naming none --
        it sends the next reader to a variable that changes nothing."""
        for switch, env in ((infer.INFER_SWITCH, "OMR_INFER"),
                          (infer.FAMILY_BLOCK_SWITCH, "OMR_SLOT_FAMILY_BLOCK")):
            self.assertEqual(switch.env, env)


class TestTheTwoDefaultsAreSeparate(unittest.TestCase):
    """⚠️⚠️ THE POINT OF THE WHOLE CHANGE: the flags are independent dials,
    and flipping any one does not flip the others -- true whether all default
    ON (as of 2026-09-23) or, as originally shipped 2026-09-21, only the slot
    rule did. The tests below force every flag explicitly, so they assert the
    independence rather than any flag's own default.

    ⚠️ THREE FLAGS SINCE 2026-09-23 (roadmap 2.10 added `OMR_CLEF_GAP`), and
    the name of this class is left alone: it is about the SEPARATION, and
    renaming it per rule added would make the class a list. Each `_on` call
    names every flag, so a FOURTH rule fails these tests loudly rather than
    sliding into an assertion that only enumerated two."""

    #: ⚠️ EVERY per-rule flag, DERIVED from the registry rather than typed, so
    #: a rule added without a line here cannot pass silently.
    def _all_off(self):
        infer._ensure_rules()
        return {r.switch.env: "0" for r in infer.RULES}

    def _on(self, env):
        forced = self._all_off()
        forced.update(env)
        with mock.patch.dict(os.environ, forced, clear=False):
            return sorted(r.inference.value for r in infer.enabled_rules())

    def test_only_the_slot_rule_is_on_by_default(self):
        self.assertEqual(self._on({"OMR_SLOT_FAMILY_BLOCK": "1"}),
                         ["collapse_slot_index_to_family_block"])

    def test_only_the_clef_gap_rule_is_on_when_only_its_flag_is(self):
        self.assertEqual(self._on({"OMR_CLEF_GAP": "1"}), ["fill_clef_gap"])

    def test_raising_OMR_INFER_does_not_silence_the_slot_rule(self):
        self.assertIn("collapse_slot_index_to_family_block",
                      self._on({"OMR_INFER": "1",
                                "OMR_SLOT_FAMILY_BLOCK": "1"}))

    def test_silencing_the_slot_rule_does_not_raise_the_duration_rules(self):
        self.assertEqual(self._on({}), [])

    def test_the_stage_runs_when_any_single_rule_is_on(self):
        for flag in self._all_off():
            with self.subTest(flag):
                env = self._all_off()
                env[flag] = "1"
                with mock.patch.dict(os.environ, env, clear=False):
                    self.assertTrue(infer.stage_should_run())
        with mock.patch.dict(os.environ, self._all_off(), clear=False):
            self.assertFalse(infer.stage_should_run())
