"""ROADMAP 2.165 -- the ONE-NOTE CORRECTION: `OMR_BAR_CORRECTS_ONE_NOTE`, default OFF (Sean 2026-10-18/19).

"with a collection of solid evidence ... if we know the meter and we feel solid about all the other notes ... change the one note
that it's unsure about if it adds up to the right bar math." STAGED EVALUATE (`reconcile_duration`'s blocked branch) + EXPORT.
Each gate has a control that fails it; the OFF control writes no correction."""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import consequences, export, one_note
from tools.omr.staged import record as R
from tools.omr.staged.record import Outcome, Q
from tools.omr.tests.test_staged_missed_rest_2_80 import ink
from tools.omr.tests.test_staged_narrowed_bar_2_97 import CELL, _dv, _v

ENV = {consequences.NARROWED_BAR_LENGTH_UNKNOWN_ENV: "1", consequences.BAR_SUM_CONFIRM_ONLY_ENV: "narrowed",
       consequences.BAR_DISAGREES_BLUE_ENV: "1"}


class _Bar:
    """2/4: a disputed quarter A (head_and_marks, beams in the cell) and three solid eighths = 2.5 beats; only A -> eighth lands."""

    def __init__(self, meter_reason="voted", voices=1, companion_reason="stem_tip_reads_no_beam", a_detail=None,
                 companion_detail=None, a_levels=0, a_beats=1.0, a_reason="head_and_marks"):
        self.log = R.Log()
        self.events = []
        self.sub = []
        a = self._note(a_beats, a_levels, a_reason, a_detail if a_detail is not None else {"yolo_beams": 1,
                                                                                                 "beam_evidence": "none_over_this_note"})
        self.a = a
        for _ in range(3):
            self._note(0.5, 1, companion_reason, companion_detail or {})
        _v(self.log, CELL, Q.EVENT, Outcome.DECIDED, {"events": [{"glyphs": e} for e in self.events]})
        _v(self.log, CELL, Q.VOICES, Outcome.DECIDED, {"n_voices": voices}, reason="one_voice" if voices == 1 else "two_voices")
        ink(self.log, cell=CELL)
        self.meter = _v(self.log, R.system(0, 0), Q.METER, Outcome.DECIDED,
                        {"numerator": 2, "denominator": 4, "raw": "2/4"}, reason=meter_reason)

    def _note(self, beats, levels, reason, detail):
        s = R.glyph(0, 0, 1, 3, len(self.sub))
        self.sub.append(s)
        _v(self.log, s, Q.DURATION, Outcome.DECIDED, _dv(beats, levels), reason=reason, detail=detail)
        self.events.append([s.glyph])
        return s

    def fire(self, mode):
        env = dict(ENV, **{one_note.ONE_NOTE_ENV: mode})
        with mock.patch.dict(os.environ, env, clear=False):
            out = consequences.reconcile_duration(self.log, CELL, self.meter)
        return out


class TestCorrection(unittest.TestCase):

    def test_CONTROL_off_the_note_is_only_marked(self):
        b = _Bar()
        out = b.fire("0")
        v = b.log.verdict(Q.DURATION, b.a)
        self.assertEqual(len(out), 1)
        self.assertEqual(v.reason, consequences.BAR_DISAGREES_REASON)
        self.assertEqual(v.value["beats"], 1.0)

    def test_on_every_gate_holds_the_note_is_corrected_with_both_candidates_RED(self):
        b = _Bar()
        b.fire("strict")
        v = b.log.verdict(Q.DURATION, b.a)
        self.assertEqual(v.reason, one_note.CORRECTS_REASON)
        self.assertEqual(v.value["beats"], 0.5)
        self.assertEqual([c.value["beats"] for c in v.candidates], [0.5, 1.0])
        self.assertIs(v.outcome, Outcome.DECIDED)

    def test_a_companion_read_by_head_and_marks_is_not_solid_in_strict(self):
        b = _Bar(companion_reason="head_and_marks")
        b.fire("strict")
        v = b.log.verdict(Q.DURATION, b.a)
        self.assertEqual(v.reason, consequences.BAR_DISAGREES_REASON)       # marked, not moved
        self.assertEqual(v.value["beats"], 1.0)
        self.assertTrue(v.detail["one_note_refusal"].startswith("other_note_not_solid"))

    def test_relaxed_accepts_a_two_source_beamed_eighth(self):
        two = {"beam_evidence": "read", "yolo_beams": 1, "cv_beams": 1}
        b = _Bar(companion_reason="head_and_marks", companion_detail=two)
        b.fire("relaxed")
        self.assertEqual(b.log.verdict(Q.DURATION, b.a).reason, one_note.CORRECTS_REASON)
        b2 = _Bar(companion_reason="head_and_marks", companion_detail=two)
        b2.fire("strict")                                                     # the same bar, strict: refused
        self.assertEqual(b2.log.verdict(Q.DURATION, b2.a).reason, consequences.BAR_DISAGREES_REASON)

    def test_a_meter_the_bars_derived_is_refused(self):
        b = _Bar(meter_reason="derived_from_bars")
        b.fire("strict")
        v = b.log.verdict(Q.DURATION, b.a)
        self.assertEqual(v.reason, consequences.BAR_DISAGREES_REASON)
        self.assertTrue(v.detail["one_note_refusal"].startswith("meter_derived_from_the_bars"))

    def test_two_voices_are_refused(self):
        b = _Bar(voices=2)
        b.fire("strict")
        self.assertEqual(b.log.verdict(Q.DURATION, b.a).detail["one_note_refusal"], "not_one_voice")

    def test_a_shortening_with_no_beam_seen_in_the_cell_is_refused(self):
        b = _Bar(a_detail={"beam_evidence": "reader_declined"})
        b.fire("strict")
        self.assertEqual(b.log.verdict(Q.DURATION, b.a).detail["one_note_refusal"],
                         "shortening_without_a_beam_seen_in_the_cell")

    def test_a_disputed_note_that_is_itself_solid_is_never_changed(self):
        b = _Bar(a_reason="stem_tip_reads_no_beam")
        b.fire("strict")
        v = b.log.verdict(Q.DURATION, b.a)
        self.assertEqual(v.value["beats"], 1.0)
        self.assertEqual(v.detail["one_note_refusal"], "disputed_note_is_itself_solid")

    def test_an_unexplained_ink_piece_is_refused(self):
        b = _Bar()
        with mock.patch.object(consequences, "_missed_rest_witness", return_value=(consequences.WITNESS_UNEXPLAINED, 1)):
            b.fire("strict")
        self.assertEqual(b.log.verdict(Q.DURATION, b.a).detail["one_note_refusal"], "unexplained_ink_in_the_bar")


class TestExport(unittest.TestCase):

    def test_the_corrected_note_is_GUESSED_blue_with_its_rule_and_both_candidates(self):
        b = _Bar()
        b.fire("strict")
        rec = export.Record({"record": {"observations": [], "abstentions": [],
                                        "verdicts": [x.to_json() for x in b.log.all_verdicts()]}})
        g = export.guess_of(rec, b.a.to_key())
        self.assertEqual(g["rule"], one_note.CORRECTS_REASON)
        self.assertEqual([c["beats"] for c in g["candidates"]], [0.5, 1.0])
        self.assertEqual(g["chosen"]["beats"], 0.5)

    def test_a_correction_with_one_candidate_RAISES(self):
        b = _Bar()
        b.fire("strict")
        rec = export.Record({"record": {"observations": [], "abstentions": [],
                                        "verdicts": [x.to_json() for x in b.log.all_verdicts()]}})
        rec.verdict(Q.DURATION, b.a.to_key())["candidates"] = rec.verdict(Q.DURATION, b.a.to_key())["candidates"][:1]
        with self.assertRaises(RuntimeError):
            export.guess_of(rec, b.a.to_key())


if __name__ == "__main__":
    unittest.main()
