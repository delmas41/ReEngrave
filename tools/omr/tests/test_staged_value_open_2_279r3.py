"""ROADMAP 2.279 r3 -- a note whose PITCH is read and whose VALUE is open (Sean 2026-11-09 ruling): `OMR_VALUE_OPEN_WRITTEN`, default OFF.

BLUE at its pitch with the most likely value by its own shape (INFER `collapse_value_open_by_shape`, the reader's own candidates, the
bar never supplies it), RED at its pitch with nothing invented (EXPORT, a zero-duration `x` grace head) where no candidate exists.
Each refusal test fails with the guard it names removed.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, evaluate, export, infer, inferences
from tools.omr.staged.record import Candidate, Outcome, Q, Verdict
from tools.omr.tests.test_staged_bare_stem_2_81 import _sub
from tools.omr.tests.test_staged_lone_event_fills_bar_2_158 import _LoneBar, _v

FLAG = consequences.VALUE_OPEN_WRITTEN_ENV


def _run(log, on=True):
    env = {FLAG: "1" if on else "0", infer.NARROWED_BAR_ENV: "1", infer.BARE_STEM_BAR_ENV: "1"}
    with mock.patch.dict(os.environ, env, clear=False):
        return infer.run(log, evaluate.Report([], [], []))


def _fired(rep):
    return [i for i in rep.inferred if i[0] == infer.Inference.COLLAPSE_VALUE_OPEN_BY_SHAPE.value]


def _with_pitch(b, g, decided=True):
    b.log.record(Verdict(id=b._id(), subject=_sub(0, g, b.cell_idx), quantity=Q.PITCH,
                         outcome=Outcome.DECIDED if decided else Outcome.ABSTAINED, value="C4" if decided else None,
                         decider="adjudicate_pitch", reason="read"))


def _bar(cands, reason="beams_ambiguous", pitch=True, meter=(4, 4)):
    b = _LoneBar(*meter)
    g = b.head(cands=cands, reason=reason)
    _with_pitch(b, g, decided=pitch)
    return b.finish(), g


QE = ((1.0, 2.0, {"beam_levels": 0}), (0.5, 1.0, {"beam_levels": 1}))          # quarter certain, eighth possible
EQ = ((0.5, 2.0, {"beam_levels": 1}), (1.0, 1.0, {"beam_levels": 0}))          # historical eighth-first order
TIE = ((1.0, 1.0, {"beam_levels": 0}), (0.5, 1.0, {"beam_levels": 1}))


class TestTheFlag(unittest.TestCase):

    def test_default_off_only_an_on_word_enables(self):
        for word, on in ((None, False), ("", False), ("0", False), ("nope", False), ("1", True), ("on", True), ("yes", True)):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(FLAG, None)
                if word is not None:
                    os.environ[FLAG] = word
                self.assertEqual(consequences.value_open_written_enabled(), on, word)


class TestTheBlueValue(unittest.TestCase):

    def test_CONTROL_flag_off_the_note_stays_narrowed(self):
        log, g = _bar(QE)
        self.assertEqual(_fired(_run(log, on=False)), [])
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_the_readers_top_support_is_taken_with_its_margin_and_both_candidates_kept(self):
        log, g = _bar(QE)
        self.assertEqual(len(_fired(_run(log))), 1)
        v = _v(log, g)
        self.assertEqual((v.outcome, v.value["beats"], v.reason), (Outcome.DECIDED, 1.0, inferences.VALUE_OPEN_REASON))
        self.assertTrue(v.decider.startswith("infer:"))
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.5, 1.0])
        self.assertEqual(v.detail["margin"], 1.0)
        self.assertFalse(v.detail["bar_sum_read"])

    def test_no_beam_read_means_the_unbeamed_value_even_when_the_historical_order_says_eighth(self):
        # CLAUDE section 4: an eighth only on evidence; `beam_discounted_uncertain` is the beam read and discounted
        log, g = _bar(EQ, reason="beam_discounted_uncertain")
        _run(log)
        self.assertEqual(_v(log, g).value["beats"], 1.0)
        self.assertEqual(_v(log, g).detail["clause"], "no_beam_read_unbeamed")

    def test_the_same_order_under_another_reason_is_the_readers(self):
        log, g = _bar(EQ, reason="beams_ambiguous")
        _run(log)
        self.assertEqual(_v(log, g).value["beats"], 0.5)

    def test_a_tie_takes_the_longer_with_margin_zero(self):
        log, g = _bar(TIE)
        _run(log)
        v = _v(log, g)
        self.assertEqual((v.value["beats"], v.detail["margin"], v.detail["clause"]), (1.0, 0.0, "tie_takes_the_longer"))

    def test_the_bar_does_not_choose_the_value(self):
        # a 2/4 bar with a decided quarter beside: the bar would land only on the quarter, but a bar that would land on the
        # EIGHTH must not move the choice -- the same head in a 1/8 meter still takes the reader's quarter
        for meter in ((2, 4), (1, 8), (7, 4)):
            log, g = _bar(QE, meter=meter)
            _run(log)
            self.assertEqual(_v(log, g).value["beats"], 1.0, meter)

    def test_no_pitch_means_no_value(self):
        log, g = _bar(QE, pitch=False)
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_decided_note_is_never_moved(self):
        b = _LoneBar(4, 4)
        b.decided(2.0)
        g = b.head(cands=QE)
        _with_pitch(b, g)
        log = b.finish()
        sub = b.durations[0].subject
        before = log.verdict(Q.DURATION, sub)
        _run(log)
        after = log.verdict(Q.DURATION, sub)
        self.assertEqual((before.id, before.value, before.decider), (after.id, after.value, after.decider))

    def test_a_rest_is_not_touched(self):
        b = _LoneBar(4, 4)
        r = b.head(cands=((1.0, 2.0, {"is_rest": True}), (0.5, 1.0, {"is_rest": True})))
        _with_pitch(b, r)
        log = b.finish()
        _run(log)
        self.assertEqual(_v(log, r).outcome, Outcome.NARROWED)


class TestPickByShape(unittest.TestCase):

    def _v(self, cands, reason="beams_ambiguous"):
        # a record NARROWED verdict always holds >= 2 candidates; `pick_by_shape` is also asked of a candidate set whose values are not all
        # note values, so it is exercised on a stand-in
        from types import SimpleNamespace as NS
        return NS(reason=reason, candidates=tuple(NS(value={"beats": b, "written": b, "dots": 0, "beam_levels": lv}, support=s)
                                                   for b, s, lv in cands))

    def test_no_candidate_value_returns_none(self):
        self.assertIsNone(inferences.pick_by_shape(self._v([])))
        from types import SimpleNamespace as NS
        self.assertIsNone(inferences.pick_by_shape(NS(reason="x", candidates=(NS(value="whole_rest", support=1.0),))))

    def test_one_usable_candidate_is_the_only_candidate(self):
        p = inferences.pick_by_shape(self._v([(1.0, 1.0, 0)]))
        self.assertEqual((p["cand"].value["beats"], p["clause"]), (1.0, "only_candidate"))

    def test_flag_level_votes_are_the_readers_support(self):
        p = inferences.pick_by_shape(self._v([(1.0, 1.0, 0), (0.5, 3.0, 1), (0.25, 1.0, 2)], reason="flags_disagree"))
        self.assertEqual((p["cand"].value["beats"], p["margin"]), (0.5, 2.0))


class TestTheRedHead(unittest.TestCase):

    U = {"sub": "glyph/0/0/0/1/2", "pitch": "E4", "x": 10.0, "reason": "duration_abstained", "candidates": []}

    def test_the_head_is_a_zero_duration_red_x_grace_with_no_duration(self):
        xml = export._unread_head_xml(self.U, 1)
        self.assertIn("<grace/>", xml)
        self.assertNotIn("<duration>", xml)
        self.assertIn(export.UNREAD_BAR_MARK_COLOR, xml)
        self.assertIn("<notehead color=", xml)
        self.assertIn(">x</notehead>", xml)
        self.assertIn("<step>E</step>", xml)
        self.assertIn("reengrave:unread_value", xml)

    def test_it_adds_no_time_to_the_voice(self):
        ev = {"kind": "note", "x_position": 10.0, "noteheads": [{"pitch": "E4", "duration_beats": 1.0, "duration_type": "quarter",
                                                                 "dots": 0}], "unread_heads": [self.U]}
        import collections
        c = collections.Counter()
        lines, units = export._measure_events_xml([ev], 4, c, voice=1)
        self.assertEqual(c["unread_heads_written"], 1)
        self.assertEqual(units, 4)

    def test_events_ride_the_nearest_event_in_x_and_nothing_without_the_flag_data(self):
        cell = export.Cell(0, 0, 0, 0)
        cell.detections.append({"pitch": "C4", "duration_beats": 1.0, "duration_type": "quarter", "dots": 0, "bbox": [0, 0, 10, 10],
                                "category": "notehead", "glyph": "g1"})
        self.assertNotIn("unread_heads", export._events(cell)[0])
        cell.unread_heads.append(self.U)
        self.assertEqual(len(export._events(cell)[0]["unread_heads"]), 1)


if __name__ == "__main__":
    unittest.main()
