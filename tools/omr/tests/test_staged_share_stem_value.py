"""ROADMAP 2.78 -- `consequences.share_stem_value`: one stem, one value, REACHING the duration.

`Q.STEM_VALUE` (ADJUDICATE, `adjudicators/stem_value.py`) decides what a stem's value is. This EVALUATE
consequence is its consumer: where a head's own stem value is DECIDED and its standing `Q.DURATION` says
something else, the duration is restated to the stem's value -- so the bar sums, INFER and EXPORT's mode vote
over a chord's heads all read heads that agree. Sean (DECISIONS 2026-10-09): *"no exceptions"*.

RED against the unrepaired tree (a clean `git archive` of the commit before the rule, 2026-10-09): 7 FAIL
-- the five positives (a duration restated to its stem's value) on an assertion that the duration is
unchanged, the order test and the declaration test on the missing `Consequence.SHARE_STEM_VALUE` -- and the
5 stay-silent controls PASS, as they must on a tree with no rule (they can only fail once a rule exists that
fires where it should not; the agree-already control is the one that would catch a rule rewriting
everything).

Controls that can fail: a head that already agrees is NOT revised (the rule is not rewriting everything); a
NARROWED stem value fires nothing (EVALUATE goes silent where two answers both fit); a head whose duration
ABSTAINED is not given one; a REFUSED head has no stem value so its duration is left alone; and the revision
must pass `Log.record`'s fixpoint guard, which refuses it without `single_pass_revision`.
"""
from __future__ import annotations

import unittest

from tools.omr.staged import evaluate
from tools.omr.staged import consequences  # noqa: F401  (registers the rules)
from tools.omr.staged import record as R
from tools.omr.staged.record import Outcome, Q, Verdict
from tools.omr.tests.test_staged_stem_value import Stem, _dur, _v


def _fire(s):
    """Run EVALUATE over the log (`cause_absent` skips for every other rule)."""
    s.run()
    return evaluate.run(s.log)


def _standing(s, gi):
    return s.log.verdict(Q.DURATION, s.heads[gi])


def _written(v):
    return (v.value["written"], v.value["dots"], v.value["beam_levels"])


class TestTheRule(unittest.TestCase):

    def test_a_decided_duration_that_disagrees_with_its_stem_is_restated_RED(self):
        """Tile 13: a dotted half and an undotted half on one stem. The undotted head's duration is
        restated to the stem's dotted half; the dotted head, which agrees, is not touched."""
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        s.head(1, "noteheadHalfInSpace", 20, decided=(2.0, 0, 0))
        before = [_standing(s, 0).id, _standing(s, 1).id]
        rep = _fire(s)
        self.assertEqual(_written(_standing(s, 1)), (3.0, 1, 0))
        self.assertEqual(_standing(s, 1).decider, "share_stem_value")
        self.assertEqual(_standing(s, 1).reason, "stem_value_follows")
        self.assertEqual(_standing(s, 1).supersedes, before[1])
        self.assertTrue(_standing(s, 1).single_pass_revision)
        self.assertEqual(_standing(s, 0).id, before[0])          # the agreeing head is untouched
        fired = [f for f in rep.fired if f[0] == "share_stem_value"]
        self.assertEqual(len(fired), 1)

    def test_CONTROL_a_stem_that_already_agrees_fires_nothing(self):
        """The control that can fail: two heads that already agree are not rewritten."""
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(2.0, 0, 0))
        s.head(1, "noteheadHalfOnLine", 30, decided=(2.0, 0, 0))
        rep = _fire(s)
        self.assertEqual([f for f in rep.fired if f[0] == "share_stem_value"], [])

    def test_a_NARROWED_duration_is_settled_to_the_stems_value(self):
        """Tile 14: a black box narrowed eighth|quarter beside a decided half takes the half."""
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackOnLine", 56, narrowed=[(0.5, 0, 1), (1.0, 0, 0)])
        _fire(s)
        v = _standing(s, 1)
        self.assertIs(v.outcome, Outcome.DECIDED)
        self.assertEqual(_written(v), (2.0, 0, 0))

    def test_a_decided_black_box_beside_a_half_becomes_the_half(self):
        """Tiles 6 / 7: a decided quarter box on a hollow stem."""
        s = Stem(direction="up")
        s.head(0, "noteheadHalfInSpace", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackOnLine", 8, decided=(1.0, 0, 0))
        _fire(s)
        self.assertEqual(_written(_standing(s, 1)), (2.0, 0, 0))

    def test_tile_1_the_tip_nearest_heads_beam_count_reaches_the_duration(self):
        s = Stem(direction="up")
        s.head(0, "noteheadBlackOnLine", 68, decided=(0.25, 0, 2))
        s.head(1, "noteheadBlackInSpace", 24, decided=(0.5, 0, 1))
        _fire(s)
        self.assertEqual(_written(_standing(s, 0)), (0.5, 0, 1))

    def test_the_heads_own_tuplet_scale_survives_the_restatement(self):
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        g = s.head(1, "noteheadHalfInSpace", 20, decided=(2.0, 0, 0))
        s.log.record(Verdict(
            id=s.log._next_id("vrd"), subject=g, quantity=Q.DURATION, outcome=Outcome.DECIDED,
            value=_dur(2.0, 0, 0, scale=2.0 / 3.0), decider="t2", reason="head_and_marks",
            supersedes=s.log.verdict(Q.DURATION, g).id))
        _fire(s)
        v = _standing(s, 1)
        self.assertAlmostEqual(v.value["written"], 3.0)
        self.assertAlmostEqual(v.value["beats"], 3.0 * 2.0 / 3.0)

    # -- where it must stay silent -----------------------------------------------------------

    def test_a_NARROWED_stem_value_fires_nothing(self):
        """Tile 9: the stem's value is itself a narrowing (levels unread): EVALUATE goes silent."""
        s = Stem(direction="down")
        s.head(0, "noteheadBlackOnLine", 6, narrowed=[(1.0, 0, 0), (0.5, 0, 1)])
        s.head(1, "noteheadWholeOnLine", 66, decided=(4.0, 0, 0))
        rep = _fire(s)
        self.assertEqual([f for f in rep.fired if f[0] == "share_stem_value"], [])
        self.assertEqual(_written(_standing(s, 1)), (4.0, 0, 0))     # untouched: no decided stem value

    def test_a_head_whose_duration_ABSTAINED_is_not_given_one(self):
        s = Stem()
        s.head(0, "noteheadHalfInSpace", 60, decided=(3.0, 1, 0))
        s.head(1, "noteheadHalfInSpace", 20, abstain=True)
        s.run()
        evaluate.run(s.log)
        self.assertIs(s.log.verdict(Q.DURATION, s.heads[1]).outcome, Outcome.ABSTAINED)

    def test_a_REFUSED_head_has_no_stem_value_so_its_duration_is_left_alone(self):
        s = Stem()
        s.head(0, "noteheadHalfOnLine", 62, decided=(2.0, 0, 0))
        s.head(1, "noteheadBlackInSpace", 30, decided=(1.0, 0, 0))
        s.refuse(1)
        _fire(s)
        self.assertEqual(_written(_standing(s, 1)), (1.0, 0, 0))

    def test_a_lone_head_is_left_alone(self):
        s = Stem()
        s.head(0, "noteheadBlack", 60, decided=(1.0, 0, 0))
        rep = _fire(s)
        self.assertEqual([f for f in rep.fired if f[0] == "share_stem_value"], [])


class TestOrderAndDeclaration(unittest.TestCase):

    def _rules(self):
        return [r for r in evaluate.execution_order()]

    def test_it_runs_BEFORE_every_meter_caused_rule(self):
        names = [r.consequence for r in self._rules()]
        mine = names.index(evaluate.Consequence.SHARE_STEM_VALUE)
        for later in (evaluate.Consequence.SIZE_MEASURE_REST,
                      evaluate.Consequence.RECONCILE_CHORD_DURATION,
                      evaluate.Consequence.RECONCILE_DURATION):
            self.assertLess(mine, names.index(later), later)

    def test_it_is_downhill_declared_single_pass_and_carries_a_bound(self):
        r = [r for r in evaluate.RULES
             if r.consequence is evaluate.Consequence.SHARE_STEM_VALUE]
        self.assertEqual(len(r), 1)
        r = r[0]
        self.assertEqual((r.cause, r.effect), (Q.STEM_VALUE, Q.DURATION))
        self.assertTrue(r.single_pass)
        self.assertGreater(len(r.bound), 80)
        self.assertLess(evaluate.DOWNHILL.index(Q.STEM_VALUE),
                        evaluate.DOWNHILL.index(Q.METER))


if __name__ == "__main__":
    unittest.main()
