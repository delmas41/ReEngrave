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
from tools.omr.tests.test_staged_narrowed_bar_2_97 import _InferBar
from tools.omr.tests.test_staged_lone_event_fills_bar_2_158 import _v

FLAG = consequences.VALUE_OPEN_WRITTEN_ENV


def _run(log, on=True):
    # the bar-arithmetic rules are held OFF: this rule's value must come from the note's own shape alone
    env = {FLAG: "1" if on else "0", infer.NARROWED_BAR_ENV: "0", infer.BARE_STEM_BAR_ENV: "0"}
    with mock.patch.dict(os.environ, env, clear=False):
        return infer.run(log, evaluate.Report([], [], []))


def _fired(rep):
    return [i for i in rep.inferred if i[0] == infer.Inference.COLLAPSE_VALUE_OPEN_BY_SHAPE.value]


def _with_pitch(b, g, decided=True):
    b.log.record(Verdict(id=b._id(), subject=_sub(0, g, b.cell_idx), quantity=Q.PITCH,
                         outcome=Outcome.DECIDED if decided else Outcome.ABSTAINED, value="C4" if decided else None,
                         decider="adjudicate_pitch", reason="read"))


EVID = {"levels_possible": 1}      # the narrowing carries beam evidence, so an eighth is available (consequences._eighth_evidence)


def _bar(beats, sup, reason="beams_ambiguous", pitch=True, meter=(4, 4), detail=EVID):
    b = _InferBar(*meter)
    g = b.narrowed_chord(n=1, reason=reason, beats=beats, sup=sup, detail=detail)[0]
    _with_pitch(b, g, decided=pitch)
    return b.finish(), g


QE = dict(beats=(1.0, 0.5), sup=(2.0, 1.0))          # quarter certain, eighth possible
EQ = dict(beats=(0.5, 1.0), sup=(2.0, 1.0))          # historical eighth-first order
TIE = dict(beats=(1.0, 0.5), sup=(1.0, 1.0))


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
        log, g = _bar(**QE)
        self.assertEqual(_fired(_run(log, on=False)), [])
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_the_readers_top_support_is_taken_with_its_margin_and_both_candidates_kept(self):
        log, g = _bar(**QE)
        self.assertEqual(len(_fired(_run(log))), 1)
        v = _v(log, g)
        self.assertEqual((v.outcome, v.value["beats"], v.reason), (Outcome.DECIDED, 1.0, inferences.VALUE_OPEN_REASON))
        self.assertTrue(v.decider.startswith("infer:"))
        self.assertEqual(sorted(c.value["beats"] for c in v.candidates), [0.5, 1.0])
        self.assertEqual(v.detail["margin"], 1.0)
        self.assertFalse(v.detail["bar_sum_source"])

    def test_no_beam_read_means_the_unbeamed_value_even_when_the_historical_order_says_eighth(self):
        # CLAUDE section 4: an eighth only on evidence; `beam_discounted_uncertain` is the beam read and discounted
        log, g = _bar(**EQ, reason="beam_discounted_uncertain", detail={})
        _run(log)
        self.assertEqual(_v(log, g).value["beats"], 1.0)
        self.assertEqual(_v(log, g).detail["clause"], "no_eighth_evidence_unbeamed")

    def test_the_same_order_under_another_reason_is_the_readers(self):
        log, g = _bar(**EQ, reason="beams_ambiguous")
        _run(log)
        self.assertEqual(_v(log, g).value["beats"], 0.5)

    def test_a_tie_takes_the_longer_with_margin_zero(self):
        log, g = _bar(**TIE)
        _run(log)
        v = _v(log, g)
        self.assertEqual((v.value["beats"], v.detail["margin"], v.detail["clause"]), (1.0, 0.0, "tie_takes_the_longer"))

    def test_the_bar_does_not_choose_the_value(self):
        # whatever the meter, an UNDERFULL bar leaves the reader's quarter; the eighth that would land a 3/8-less bar is never supplied
        for meter in ((2, 4), (7, 4), (3, 4)):
            log, g = _bar(**QE, meter=meter)
            _run(log)
            self.assertEqual(_v(log, g).value["beats"], 1.0, meter)

    def test_the_bar_only_vetoes_an_overfull_pick_and_the_head_stays_narrowed_for_a_red_write(self):
        # a 1/8 bar (half a beat): the quarter pick overfills it although the bar holds nothing else -> no pick, no invented eighth
        log, g = _bar(**QE, meter=(1, 8))
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_bar_already_full_without_the_head_vetoes_it(self):
        # the Litolff p2 bar 256 case: the decided events fill the bar, the dropped head is a duplicate/extra -> not written blue
        b = _InferBar(2, 4)
        b.decided(1.0)
        b.decided(1.0)
        g = b.narrowed_chord(n=1, detail=EVID)[0]
        _with_pitch(b, g)
        log = b.finish()
        self.assertEqual(_fired(_run(log)), [])
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_no_pitch_means_no_value(self):
        log, g = _bar(**QE, pitch=False)
        _run(log)
        self.assertEqual(_v(log, g).outcome, Outcome.NARROWED)

    def test_a_decided_note_is_never_moved(self):
        b = _InferBar(4, 4)
        b.decided(2.0)
        g = b.narrowed_chord(n=1, detail=EVID)[0]
        _with_pitch(b, g)
        log = b.finish()
        sub = b.durations[0].subject
        before = log.verdict(Q.DURATION, sub)
        _run(log)
        after = log.verdict(Q.DURATION, sub)
        self.assertEqual((before.id, before.value, before.decider), (after.id, after.value, after.decider))


class TestPickByShape(unittest.TestCase):

    def _v(self, cands, reason="beams_ambiguous"):
        # a record NARROWED verdict always holds >= 2 candidates; `pick_by_shape` is also asked of a candidate set whose values are not all
        # note values, so it is exercised on a stand-in
        from types import SimpleNamespace as NS
        return NS(reason=reason, detail=dict(EVID), candidates=tuple(NS(value={"beats": b, "written": b, "dots": 0, "beam_levels": lv}, support=s)
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


class TestNothingWrittenIsMoved(unittest.TestCase):

    def _det(self, pitch, beats, glyph, guess=None, x=0.0):
        return {"category": "notehead", "pitch": pitch, "duration_beats": beats, "duration_type": "quarter" if beats == 1.0 else "eighth",
                "dots": 0, "bbox": [x, 0, 10, 10], "bbox_page": [x, 0, 10, 10], "glyph": glyph, **({"guess": guess} if guess else {})}

    def _runs(self, dets):
        cell = export.Cell(0, 0, 0, 0)
        cell.detections.extend(dets)
        run = export.StaffRun(key="staff/0/0/0", page=0, system=0, staff=0)
        run.cells[0] = cell
        return {"staff/0/0/0": run}, cell

    def test_a_guessed_value_that_disagrees_with_a_written_chord_mate_is_refused_alone(self):
        # the Litolff p8 tile 8 case: the written eighth keeps its place, only the guess is taken out (and later filed red)
        mine = {"rule": "collapse_value_open_by_shape", "stage": "INFER", "candidates": []}
        runs, cell = self._runs([self._det("C4", 0.5, "glyph/0/0/0/0/1"), self._det("C4", 1.0, "glyph/0/0/0/0/2", guess=mine)])
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            removed = export._chords_whose_value_would_be_voted(runs)
        self.assertEqual([d["glyph"] for d in removed], ["glyph/0/0/0/0/2"])
        self.assertEqual([d["glyph"] for d in cell.detections], ["glyph/0/0/0/0/1"])

    def test_CONTROL_flag_off_both_are_refused_as_before(self):
        mine = {"rule": "collapse_value_open_by_shape", "stage": "INFER", "candidates": []}
        runs, cell = self._runs([self._det("C4", 0.5, "glyph/0/0/0/0/1"), self._det("C4", 1.0, "glyph/0/0/0/0/2", guess=mine)])
        with mock.patch.dict(os.environ, {FLAG: "0"}):
            removed = export._chords_whose_value_would_be_voted(runs)
        self.assertEqual(len(removed), 2)

    def test_the_same_ink_as_a_written_head_is_not_filed_red(self):
        cell = export.Cell(0, 0, 0, 0)
        cell.detections.append(self._det("C4", 0.5, "g1"))
        near = {"pitch": "C4", "bbox_page": [2, 1, 10, 10]}
        self.assertTrue(export._same_ink_as_written(cell, near, 10.0))
        self.assertFalse(export._same_ink_as_written(cell, dict(near, pitch="D4"), 10.0))            # another pitch is another note
        self.assertFalse(export._same_ink_as_written(cell, dict(near, bbox_page=[200, 1, 10, 10]), 10.0))   # far away is another note


class TestR4NoGuessMovesAReadNote(unittest.TestCase):

    def test_the_judged_scorer_takes_the_tiles_own_glyph_before_a_red_head_at_its_slot(self):
        from tools.omr.staged import lane_report as LR
        place = (1, 2)
        with mock.patch.object(LR, "place_of", lambda h: place):
            red = {"rg": "g/2", "type": "unread-value", "pitch": "C4", "kind": "note"}
            own = {"rg": "g/1", "type": "eighth", "pitch": "C4", "kind": "note"}
            self.assertIs(LR.event_at([red, own], place, "C4", "note", "g/1"), own)
            self.assertIs(LR.event_at([red, own], place, "C4", "note"), own)          # even without the glyph the red head is last

    def test_a_value_open_event_is_one_whose_every_head_is_this_lanes_guess(self):
        mine = {"guess": {"rule": "collapse_value_open_by_shape"}}
        self.assertTrue(export._is_value_open_guess({"noteheads": [mine, mine]}))
        self.assertFalse(export._is_value_open_guess({"noteheads": [mine, {}]}))
        self.assertFalse(export._is_value_open_guess({"noteheads": [{"guess": {"rule": "lone_event_fills_bar"}}]}))

    def test_the_wrapper_is_the_core_with_the_flag_off(self):
        ev = [{"kind": "note", "x_position": 1.0, "noteheads": [{"guess": {"rule": "collapse_value_open_by_shape"}, "duration_beats": 1.0}]}]
        with mock.patch.dict(os.environ, {FLAG: "0"}), mock.patch.object(export, "_partial_bar_plan_core", return_value={"ok": True, "x": 1}) as c:
            self.assertEqual(export._partial_bar_plan(ev, None, 4, None, []), {"ok": True, "x": 1})
            self.assertEqual(c.call_count, 1)

    def test_a_guess_may_not_turn_a_held_bar_partial(self):
        ev = [{"kind": "note", "x_position": 1.0, "noteheads": [{"guess": {"rule": "collapse_value_open_by_shape"}, "duration_beats": 1.0}]},
              {"kind": "note", "x_position": 2.0, "noteheads": [{"duration_beats": 1.0}]}]
        plans = [{"ok": True, "unwritten": []}, {"ok": False, "why": "nothing_before_or_after_the_gap"}]
        with mock.patch.dict(os.environ, {FLAG: "1"}), mock.patch.object(export, "_partial_bar_plan_core", side_effect=plans):
            r = export._partial_bar_plan(ev, None, 4, None, [])
        self.assertFalse(r["ok"])


if __name__ == "__main__":
    unittest.main()
