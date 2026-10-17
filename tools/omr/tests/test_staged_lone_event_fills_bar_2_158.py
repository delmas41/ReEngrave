"""ROADMAP 2.158 -- a lone event in a known meter may be guessed from the bar: `OMR_LONE_EVENT_FILLS_BAR`, default ON (Sean 2026-10-17)
(STAGED INFER `collapse_narrowed_by_bar`, beside 2.154's bare-stem confirm).

Sean 2026-10-17: *"when there is just one note head type in the measure, and we know the meter, then I'm totally okay with it
guessing ... we knew that it was a 2-4 bar and that there was a note head, or two of them in thirds."* Under
`OMR_BAR_SUM_CONFIRM_ONLY` arm a, a bar holding ONE event whose meter reaches the print, where exactly one of the event's own
candidates fills the bar, is GUESSED to that candidate (reason `lone_event_fills_bar`, candidates kept). Every refusal test
names the guard it stands on and fails with that guard removed from `inferences.lone_event_decline`.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate, infer, inferences
from tools.omr.staged.record import Candidate, Outcome, Q, Verdict
from tools.omr.tests.test_staged_bare_stem_2_81 import _cell, _sub
from tools.omr.tests.test_staged_narrowed_bar_2_97 import _InferBar, _stem

LONE = consequences.LONE_EVENT_FILLS_BAR_ENV
ARM = consequences.BAR_SUM_CONFIRM_ONLY_ENV
HEAD_FILL = ((2.0, 2.0), (1.0, 1.0), (4.0, 1.0))      # the head-fill reader's {half, quarter, whole}, half first


class _LoneBar(_InferBar):
    def head(self, cands=HEAD_FILL, stem="stem:1", event=None, reason="head_fill_from_ink"):
        """A NARROWED head over `cands` ((beats, support), ...), no beam levels; `event` joins an existing event."""
        g = self.g
        self.g += 1
        self.members.append(self.log.record(Verdict(
            id=self._id(), subject=_sub(0, g, self.cell_idx), quantity=Q.DURATION, outcome=Outcome.NARROWED, value=None,
            decider="adjudicate_duration", reason=reason,
            candidates=tuple(Candidate(dict({"beats": b, "written": b, "dots": 0, "beam_levels": 0}, **extra), support=s)
                             for b, s, *rest in cands for extra in [rest[0] if rest else {}]))))
        _stem(self.log, _sub(0, g, self.cell_idx), stem)
        if event is None:
            self.events.append([g])
        else:
            self.events[event].append(g)
        return g

    def rest(self, beats):
        g = self.g
        self.g += 1
        self.durations.append(self.log.record(Verdict(
            id=self._id(), subject=_sub(0, g, self.cell_idx), quantity=Q.DURATION, outcome=Outcome.DECIDED,
            value={"beats": beats, "written": beats, "is_rest": True}, decider="adjudicate_duration", reason="rest_class")))
        self.events.append([g])
        return g


def _run(log, *, lone=True, arm="narrowed"):
    env = {infer.NARROWED_BAR_ENV: "1", infer.BARE_STEM_BAR_ENV: "1", ARM: arm, LONE: "1" if lone else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        return infer.run(log, evaluate.Report([], [], []))


def _fired(rep):
    return [i for i in rep.inferred if i[0] == infer.Inference.COLLAPSE_NARROWED_BY_BAR.value]


def _v(log, g):
    return log.verdict(Q.DURATION, _sub(0, g))


def _lone_half():
    b = _LoneBar(2, 4)
    g = b.head()
    return b.finish(), g


class TestTheFlag(unittest.TestCase):

    def test_default_on_only_an_off_word_disables(self):
        for word, on in ((None, True), ("", False), ("0", False), ("off", False), ("no", False), ("false", False),
                         ("nope", True), ("1", True), ("on", True), ("yes", True), ("true", True)):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(LONE, None)
                if word is not None:
                    os.environ[LONE] = word
                self.assertEqual(consequences.lone_event_fills_bar_enabled(), on, word)


class TestALoneHalfIn24(unittest.TestCase):

    def test_CONTROL_flag_off_the_lone_half_stays_narrowed(self):
        log, g = _lone_half()
        rep = _run(log, lone=False)
        self.assertEqual(_fired(rep), [])
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_flag_on_the_lone_half_is_guessed_RED(self):
        log, g = _lone_half()
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0)), (None, 2.0))
        rep = _run(log)
        self.assertEqual(len(_fired(rep)), 1)
        v = _v(log, g)
        self.assertEqual((v.outcome, v.value["beats"], v.reason), (Outcome.DECIDED, 2.0, inferences.LONE_EVENT_REASON))
        self.assertTrue(v.decider.startswith("infer:"))
        # GUESSED: the reader's candidates travel forward onto the inferred verdict
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [1.0, 2.0, 4.0])

    def test_two_heads_in_thirds_on_one_stem_are_one_event(self):
        b = _LoneBar(2, 4)
        g1 = b.head()
        g2 = b.head(event=0)
        log = b.finish()
        _run(log)
        for g in (g1, g2):
            v = _v(log, g)
            self.assertEqual((v.outcome, v.value["beats"], v.reason), (Outcome.DECIDED, 2.0, inferences.LONE_EVENT_REASON))

    def test_CONTROL_with_confirm_only_off_the_old_rule_decides_it_by_its_own_reason(self):
        log, g = _lone_half()
        _run(log, lone=True, arm="off")
        v = _v(log, g)
        self.assertEqual((v.outcome, v.value["beats"]), (Outcome.DECIDED, 2.0))
        self.assertEqual(v.reason, "the_bars_arithmetic_forces_this_length")


class TestRefusals(unittest.TestCase):

    def test_two_events_refuse_guard_not_one_event(self):
        # a decided quarter beside a narrowed {2, 1, 4}: the quarter lands 2/4 uniquely (the old bar pick), but two events
        b = _LoneBar(2, 4)
        b.decided(1.0)
        g = b.head()
        log = b.finish()
        _run(log, lone=False, arm="off")
        self.assertEqual(_v(log, g).value["beats"], 1.0)          # CONTROL: the bar alone would pick the quarter
        b = _LoneBar(2, 4)
        b.decided(1.0)
        g = b.head()
        log = b.finish()
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0))[0], "not_one_event")
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_rest_beside_the_note_refuses_guard_a_rest_in_the_bar(self):
        b = _LoneBar(2, 4)
        g = b.head(cands=((1.0, 2.0), (2.0, 1.0)))
        b.rest(1.0)
        log = b.finish()
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0))[0], "a_rest_in_the_bar")
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_an_undecided_meter_refuses_guard_meter_not_decided(self):
        log, g = _lone_half()
        meter = log.verdict(Q.METER, _cell(0, 0).at(inferences.Kind.SYSTEM))
        log.record(Verdict(id=log._next_id("vrd"), subject=meter.subject, quantity=Q.METER, outcome=Outcome.NARROWED,
                           value=None, decider="adjudicate_meter", reason="readers_disagree", supersedes=meter.id,
                           candidates=(Candidate(dict(meter.value), support=1.0),
                                       Candidate({"numerator": 3, "denominator": 4}, support=1.0))))
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0)), ("meter_not_decided", None))
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_meter_the_bars_chose_refuses_guard_meter_not_from_the_print(self):
        b = _LoneBar(2, 4)
        b.head()
        log = b.finish()
        meter = log.verdict(Q.METER, _cell(0, 0).at(inferences.Kind.SYSTEM))
        log.record(Verdict(id=log._next_id("vrd"), subject=meter.subject, quantity=Q.METER, outcome=Outcome.DECIDED,
                           value=dict(meter.value), decider="adjudicate_meter", reason="from_the_bars",
                           supersedes=meter.id))
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0)), ("meter_not_from_the_print", None))

    def test_two_candidates_that_both_fill_refuse_guard_exactly_one(self):
        b = _LoneBar(2, 4)
        g = b.head(cands=((2.0, 2.0), (2.0, 1.0, {"head": "x"}), (1.0, 1.0)))
        log = b.finish()
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0)), ("not_exactly_one_candidate_fills", None))
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_no_candidate_fills_nothing_is_written(self):
        b = _LoneBar(3, 4)
        g = b.head(cands=((2.0, 2.0), (1.0, 1.0)))
        log = b.finish()
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0))[0], "not_exactly_one_candidate_fills")
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_tuplet_marker_refuses_guard_tuplet_in_bar(self):
        from tools.omr.staged.record import READERS
        b = _LoneBar(2, 4)
        g = b.head()
        b.log.observe(_sub(0, 9, b.cell_idx), Q.TUPLET_MARKER, "tuplet3", reader=READERS.DETECTOR, frame="cell", x0=0,
                      x1=10, x_center=5)
        log = b.finish()
        self.assertEqual(inferences.lone_event_decline(log, _cell(0, 0)), ("tuplet_in_bar", None))
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)


if __name__ == "__main__":
    unittest.main()
