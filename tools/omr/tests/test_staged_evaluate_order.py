"""ROADMAP 2.63: the order EVALUATE runs its rules in is DECLARED, not typed.

`evaluate._pass` sorted `RULES` by the cause's DOWNHILL rank alone. The four
`meter`-caused rules share one rank, so they ran in the order they were
registered -- their line numbers in `consequences.py` -- and the comment on
`Q.REST_IS_NOT_A_REST` in `DOWNHILL` credited `reinstate_rest_between_staves`'s
place after `reconcile_duration` to the effect's position, which did not
enter the sort (`docs/evaluate-sequence-2026-10-07.md` §3).

`execution_order` now keys on (cause rank, effect rank). These tests read
that order directly and prove, with a reversed registration as the control,
which pairs the key governs and which pair file order still governs.

⚠️ RUN RED FIRST against the tree before `execution_order` existed: every
test here fails on `AttributeError`, and the control test's own assertion
would fail against the old cause-only key (reversed registration put the
reinstate rule FIRST among the meter rules).
"""
from __future__ import annotations

import unittest
from unittest import mock

from tools.omr.staged import consequences  # noqa: F401 -- registers rules
from tools.omr.staged import evaluate
from tools.omr.staged.record import Q


def _names(rules):
    return [r.fn.__name__ for r in rules]


def _meter_rules():
    return [r for r in evaluate.RULES if r.cause == Q.METER]


class TestTheExecutionOrderIsDeclared(unittest.TestCase):
    def test_the_real_order_runs_the_documented_sequence(self):
        """What `_pass` runs, read off the function rather than inferred
        from a report. The meter-caused rules come last, with the
        reinstatement after every `duration` writer."""
        order = _names(evaluate.execution_order())
        self.assertEqual(order, [
            "name_part", "join_parts", "restate_pitch", "respell_accidental",
            "move_glyph", "apply_printed_accidental", "size_measure_rest",
            "reconcile_chord_duration", "reconcile_duration",
            "reinstate_rest_between_staves",
            # ROADMAP 2.68: text pairs last -- it changes no note
            "pair_word_and_dynamic"])

    def test_reinstate_runs_after_reconcile_even_if_registered_first(self):
        """⚠️ THE CONTROL. Reverse the registration order of the meter rules
        and the effect key must STILL put `reinstate_rest_between_staves`
        (effect `rest_is_not_a_rest`) after every `meter -> duration` rule.
        Against the old cause-only key the reinstatement came FIRST here."""
        reversed_meter = list(reversed(_meter_rules()))
        others = [r for r in evaluate.RULES if r.cause != Q.METER]
        with mock.patch.object(evaluate, "RULES", others + reversed_meter):
            order = _names(evaluate.execution_order())
        meter_part = [n for n in order
                      if n in _names(reversed_meter)]
        self.assertEqual(meter_part[-1], "reinstate_rest_between_staves")
        self.assertEqual(set(meter_part[:-1]),
                         {"size_measure_rest", "reconcile_chord_duration",
                          "reconcile_duration"})

    def test_a_pair_sharing_cause_and_effect_still_follows_registration(self):
        """`reconcile_chord_duration` before `reconcile_duration` is a real
        dependency (both `meter -> duration`), and it is FILE ORDER that
        carries it -- `test_staged_chord_duration` pins that on purpose.
        Reversing the registration must therefore reverse this pair: the
        key does not pretend to order what it cannot see."""
        reversed_meter = list(reversed(_meter_rules()))
        others = [r for r in evaluate.RULES if r.cause != Q.METER]
        with mock.patch.object(evaluate, "RULES", others + reversed_meter):
            order = _names(evaluate.execution_order())
        self.assertLess(order.index("reconcile_duration"),
                        order.index("reconcile_chord_duration"))
        # ... and on the real registration the pair is the right way round.
        real = _names(evaluate.execution_order())
        self.assertLess(real.index("reconcile_chord_duration"),
                        real.index("reconcile_duration"))

    def test_the_pass_runs_the_rules_in_that_order(self):
        """`_pass` must consume `execution_order`, not keep a second sort.
        Proved by behaviour, not by reading the source (CLAUDE.md §6c): with
        every rule replaced by a recorder, the order `_pass` calls them in
        is the order `execution_order` returns."""
        import dataclasses
        from tools.omr.staged.record import Kind, Log

        called = []

        def recorder(name):
            def fn(log, subject, cause):
                called.append(name)
                return []
            fn.__name__ = name          # `_names` reads it
            return fn

        stand_ins = [dataclasses.replace(r, fn=recorder(r.fn.__name__),
                                         stub=False)
                     for r in reversed(evaluate.RULES)]
        log = Log()
        log.freeze()
        # One subject per scope so every rule is visited once; a cause that
        # is absent is reported `cause_absent` BEFORE `fn` is called, so the
        # recorder must be reached another way: patch `_cause_for` to hand
        # back a DECIDED-looking cause.
        fake_cause = mock.Mock(outcome=evaluate.Outcome.DECIDED, id="v")
        with mock.patch.object(evaluate, "RULES", stand_ins), \
                mock.patch.object(evaluate, "_cause_for",
                                  return_value=fake_cause), \
                mock.patch.object(Log, "subjects",
                                  return_value=(mock.Mock(
                                      to_key=lambda: "s"),)):
            evaluate._pass(log, evaluate.Report([], [], []), progress=False)
        self.assertEqual(called, _names(evaluate.execution_order(stand_ins)))
        # the reinstatement is still the last MUSIC rule; ROADMAP 2.68's text
        # pairing (`Q.DIRECTION -> Q.MARKING`) runs after every one of them
        self.assertEqual(called[-2:], ["reinstate_rest_between_staves",
                                       "pair_word_and_dynamic"])


if __name__ == "__main__":
    unittest.main()
