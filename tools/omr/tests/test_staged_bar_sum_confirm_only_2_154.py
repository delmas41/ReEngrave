"""ROADMAP 2.154 -- the bar sum never picks: `OMR_BAR_SUM_CONFIRM_ONLY`, default OFF (STAGED EVALUATE + INFER).

Sean's standing rule (DECISIONS 2026-10-12/13): bar arithmetic may CONFIRM a value the page already supports; it never
SUPPLIES one. Arm a (`narrowed`): the bar never chooses among a NARROWED note's candidates. Arm b (`all`): it also never
moves a DECIDED value. Every positive has its control: flag off decides exactly as before.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate, infer
from tools.omr.staged.record import Outcome, Q
from tools.omr.tests.test_staged_bare_stem_2_81 import _Bar, _sub
from tools.omr.tests.test_staged_narrowed_bar_2_97 import _EvalBar, _InferBar

ENV = consequences.BAR_SUM_CONFIRM_ONLY_ENV


def _with(word):
    env = {ENV: word} if word is not None else {}
    patch = mock.patch.dict(os.environ, env, clear=False)
    return patch


def _reconcile(bar, word):
    with _with(word):
        if word is None:
            os.environ.pop(ENV, None)
        return bar.fire()


def _narrowed_bar():
    """2/4: a narrowed {8, 4} head and a decided quarter. Only the eighth lands the bar (0.5 + 1.0 != 2; 1.0 + 1.0 = 2)."""
    b = _EvalBar(2, 4)
    n = b.narrowed()
    b.decided(1.0)
    return b, n


def _decided_bar():
    """2/4: a decided quarter, a decided eighth and a quarter rest -- over by an eighth; one +/-1 landing (the quarter -> an eighth
    leaves exactly 2/4, and no other single +/-1 does)."""
    b = _EvalBar(2, 4)
    d = b.decided(1.0)
    b.decided(0.5)
    b.decided(1.0, rest=True)
    return b, d


class TestTheWord(unittest.TestCase):

    def test_default_is_off(self):
        with _with(None):
            os.environ.pop(ENV, None)
            self.assertEqual(consequences.bar_sum_confirm_only(), "")

    def test_words(self):
        for word, want in (("narrowed", "narrowed"), ("a", "narrowed"), ("all", "all"), ("b", "all"), ("1", "all"),
                           ("on", "all"), ("0", ""), ("", ""), ("nope", ""), ("off", "")):
            with _with(word):
                self.assertEqual(consequences.bar_sum_confirm_only(), want, word)


class TestReconcileDurationPicks(unittest.TestCase):

    def test_CONTROL_flag_off_the_bar_picks_the_narrowed_note(self):
        b, n = _narrowed_bar()
        log, out = _reconcile(b, None)
        self.assertEqual(len(out), 1)
        v = log.verdict(Q.DURATION, n)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "meter_reconciliation")

    def test_arm_a_the_narrowed_note_stays_narrowed_RED(self):
        b, n = _narrowed_bar()
        log, out = _reconcile(b, "narrowed")
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, n).outcome, Outcome.NARROWED)

    def test_arm_b_the_narrowed_note_stays_narrowed(self):
        b, n = _narrowed_bar()
        log, out = _reconcile(b, "all")
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, n).outcome, Outcome.NARROWED)

    def test_arm_a_a_decided_neighbour_is_not_moved_through_a_narrowed_note(self):
        # the 2.97 shape: flag off, the DECIDED quarter is moved to an eighth while the narrowed head beside it counts at its
        # best candidate -- an assumed value. Arm a: a bar holding a narrowed note has no known sum.
        b = _EvalBar(2, 4)
        n = b.narrowed()
        d = b.decided(1.0)
        b.decided(1.0, rest=True)
        log, _ = _reconcile(b, None)
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 0.5)        # CONTROL
        b = _EvalBar(2, 4)
        n = b.narrowed()
        d = b.decided(1.0)
        b.decided(1.0, rest=True)
        log, out = _reconcile(b, "narrowed")
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 1.0)
        self.assertEqual(log.verdict(Q.DURATION, n).outcome, Outcome.NARROWED)


class TestReconcileDurationMovesADecidedValue(unittest.TestCase):

    def test_CONTROL_flag_off_moves_the_decided_note(self):
        b, d = _decided_bar()
        log, out = _reconcile(b, None)
        self.assertTrue(out)
        self.assertTrue(any(v.reason == "meter_reconciliation" for v in out))

    def test_arm_a_still_moves_a_decided_note_in_a_bar_with_no_narrowing(self):
        b, d = _decided_bar()
        log, out = _reconcile(b, "narrowed")
        self.assertTrue(out)

    def test_arm_b_never_moves_a_decided_note_RED(self):
        b, d = _decided_bar()
        log, out = _reconcile(b, "all")
        self.assertEqual(out, [])
        self.assertEqual(log.verdict(Q.DURATION, d).value["beats"], 1.0)
        self.assertEqual(log.verdict(Q.DURATION, d).reason, "head_and_marks")


def _infer(log, word, *, bare=True):
    env = {infer.NARROWED_BAR_ENV: "1", infer.BARE_STEM_BAR_ENV: "1" if bare else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        if word is None:
            os.environ.pop(ENV, None)
        else:
            os.environ[ENV] = word
        return infer.run(log, evaluate.Report([], [], []))


def _fired(report, rule):
    return [i for i in report.inferred if i[0] == rule.value]


class TestInferCollapses(unittest.TestCase):

    def _bare_bar(self):
        b = _Bar()
        for _ in range(3):
            b.decided(1.0)
        g = b.bare()
        return b.finish(), g

    def test_CONTROL_flag_off_the_bare_stem_is_settled(self):
        log, g = self._bare_bar()
        rep = _infer(log, None)
        fired = _fired(rep, infer.Inference.COLLAPSE_BARE_STEM_BY_BAR) \
            + _fired(rep, infer.Inference.COLLAPSE_NARROWED_BY_BAR)
        self.assertEqual(len(fired), 1)
        self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome, Outcome.DECIDED)

    def test_either_arm_leaves_the_bare_stem_narrowed_RED(self):
        for word in ("narrowed", "all"):
            log, g = self._bare_bar()
            rep = _infer(log, word)
            self.assertEqual(_fired(rep, infer.Inference.COLLAPSE_BARE_STEM_BY_BAR), [], word)
            self.assertEqual(_fired(rep, infer.Inference.COLLAPSE_NARROWED_BY_BAR), [], word)
            self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome, Outcome.NARROWED, word)

    def _chord_bar(self):
        b = _InferBar()
        for _ in range(3):
            b.decided(1.0)
        (g,) = b.narrowed_chord(1)
        return b.finish(), g

    def test_CONTROL_flag_off_a_beams_ambiguous_head_is_settled(self):
        log, g = self._chord_bar()
        rep = _infer(log, None, bare=False)
        self.assertEqual(len(_fired(rep, infer.Inference.COLLAPSE_NARROWED_BY_BAR)), 1)

    def test_either_arm_leaves_a_beams_ambiguous_head_narrowed_RED(self):
        for word in ("narrowed", "all"):
            log, g = self._chord_bar()
            rep = _infer(log, word, bare=False)
            self.assertEqual(_fired(rep, infer.Inference.COLLAPSE_NARROWED_BY_BAR), [], word)
            self.assertEqual(log.verdict(Q.DURATION, _sub(0, g)).outcome, Outcome.NARROWED, word)


if __name__ == "__main__":
    unittest.main()
