"""ROADMAP 2.279 -- a read head whose VALUE is narrowed is written GUESSED (blue) where the bar confirms one of the reader's own
candidates, instead of being dropped: `OMR_DROPPED_BLUE`, default OFF (Sean 2026-11-08: "red reserved for we can't read this; for
that which we can read I want the most likely option in blue").

STAGED INFER `collapse_narrowed_by_bar`. Nothing is created: `solve_bare_stem_bar`'s own proposals (every guard it has) that 2.154's
filter dropped are re-labelled `narrowed_bar_lands_blue`; the harness stamps `infer:`, carries the reader's candidates, and EXPORT's
`guess_of` writes it blue. Each refusal test fails with the guard it names removed.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate, infer, inferences
from tools.omr.staged.record import Outcome, Q
from tools.omr.tests.test_staged_lone_event_fills_bar_2_158 import _LoneBar, _v

BLUE = consequences.DROPPED_BLUE_ENV
ARM = consequences.BAR_SUM_CONFIRM_ONLY_ENV
LONE = consequences.LONE_EVENT_FILLS_BAR_ENV
QE = ((1.0, 2.0, {"beam_levels": 0}), (0.5, 1.0, {"beam_levels": 1}))                  # quarter (certain), eighth (possible): `beams_ambiguous`'s shape


def _run(log, *, blue=True, arm="narrowed"):
    env = {infer.NARROWED_BAR_ENV: "1", infer.BARE_STEM_BAR_ENV: "1", ARM: arm, LONE: "0", BLUE: "1" if blue else "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        return infer.run(log, evaluate.Report([], [], []))


def _fired(rep):
    return [i for i in rep.inferred if i[0] == infer.Inference.COLLAPSE_NARROWED_BY_BAR.value]


def _quarter_then_narrowed(meter=(2, 4), cands=QE, decided=1.0):
    b = _LoneBar(*meter)
    b.decided(decided)
    g = b.head(cands=cands, reason="beams_ambiguous")
    return b.finish(), g


class TestTheFlag(unittest.TestCase):

    def test_default_off_only_an_on_word_enables(self):
        for word, on in ((None, False), ("", False), ("0", False), ("off", False), ("nope", False),
                         ("1", True), ("on", True), ("yes", True), ("true", True)):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(BLUE, None)
                if word is not None:
                    os.environ[BLUE] = word
                self.assertEqual(consequences.dropped_blue_enabled(), on, word)


class TestTheBarLandsOnOneCandidate(unittest.TestCase):

    def test_CONTROL_flag_off_the_note_stays_narrowed_and_is_dropped(self):
        log, g = _quarter_then_narrowed()
        rep = _run(log, blue=False)
        self.assertEqual(_fired(rep), [])
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_flag_on_the_quarter_the_bar_confirms_is_guessed_with_both_candidates(self):
        log, g = _quarter_then_narrowed()
        rep = _run(log)
        self.assertEqual(len(_fired(rep)), 1)
        v = _v(log, g)
        self.assertEqual((v.outcome, v.value["beats"], v.reason), (Outcome.DECIDED, 1.0, inferences.DROPPED_BLUE_REASON))
        self.assertTrue(v.decider.startswith("infer:"))
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.5, 1.0])      # the reader's own, both carried

    def test_it_chooses_from_the_readers_candidates_only(self):
        # a decided quarter in 3/4 leaves 2 beats: no candidate of {1, 0.5} is 2, so nothing is invented
        log, g = _quarter_then_narrowed(meter=(3, 4))
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_two_landings_that_disagree_leave_it_narrowed(self):
        # 3/4 with two narrowed {1, 2} events: (1, 2) and (2, 1) both land -> the bar cannot tell
        b = _LoneBar(3, 4)
        g1 = b.head(cands=((1.0, 1.0), (2.0, 1.0)), stem="stem:1", reason="beams_ambiguous")
        g2 = b.head(cands=((1.0, 1.0), (2.0, 1.0)), stem="stem:2", reason="beams_ambiguous")
        log = b.finish()
        _run(log)
        self.assertEqual(_v(log, g1).outcome, Outcome.NARROWED)
        self.assertEqual(_v(log, g2).outcome, Outcome.NARROWED)

    def test_a_tuplet_marker_in_the_bar_leaves_it_narrowed(self):
        from tools.omr.staged.record import READERS
        from tools.omr.tests.test_staged_bare_stem_2_81 import _sub
        b = _LoneBar(2, 4)
        b.decided(1.0)
        g = b.head(cands=QE, reason="beams_ambiguous")
        b.log.observe(_sub(0, 9, b.cell_idx), Q.TUPLET_MARKER, "tuplet3", reader=READERS.DETECTOR, frame="cell", x0=0, x1=10,
                      x_center=5)
        log = b.finish()
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_the_eighth_is_not_supplied_by_the_bar(self):
        # 2/4: a decided dotted quarter (1.5) leaves half a beat; {quarter certain, eighth possible}: only the EIGHTH lands.
        # CLAUDE section 4: bar arithmetic never SUPPLIES an eighth the page does not show (`_shortens_without_evidence`)
        log, g = _quarter_then_narrowed(decided=1.5)
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_meter_the_bars_chose_leaves_it_narrowed(self):
        b = _LoneBar(2, 4)
        b.decided(1.0)
        g = b.head(cands=QE, reason="beams_ambiguous")
        log = b.finish()
        from tools.omr.staged.record import Verdict
        meter = log.verdict(Q.METER, _meter_subject(log))
        log.record(Verdict(id=log._next_id("vrd"), subject=meter.subject, quantity=Q.METER, outcome=Outcome.DECIDED,
                           value=dict(meter.value), decider="adjudicate_meter", reason="from_the_bars", supersedes=meter.id))
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)


def _meter_subject(log):
    from tools.omr.tests.test_staged_bare_stem_2_81 import _cell
    return _cell(0, 0).at(inferences.Kind.SYSTEM)


if __name__ == "__main__":
    unittest.main()
