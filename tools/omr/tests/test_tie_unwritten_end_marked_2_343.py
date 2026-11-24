"""ROADMAP 2.343: an arc (tie or slur) whose other note is not in the file is MARKED, never dropped silently (STAGED EXPORT,
`export._record_tie_spans`, `_page_bound_slur_spans`, `_register_unread_kind_runs`, `_mark_half_written_arcs`).

The controls are REAL cases (rule 7), rows saved from the Litolff 20261123-night record:
* ties: p2 staff 7 bars 9-11, a half-note F4 tied through a half note whose duration was abstained (`wide_box_unread`): the middle note is
  not written, so the first note's tie goes to a note that is not there and the third note's tie comes from one
  (`fixtures/tie_unwritten_middle_litolff_p2_20261123.json`);
* slurs and arcs of unread kind (`fixtures/arc_unwritten_end_litolff_20261123.json`): a page slur on p14 (run obs:564481, F4 -> G4) whose
  stop note has no duration (not written); and a page run on p1 (obs:013999, E4 -> F4, both notes written) whose kind the binder could not read
  (`step_between`) and which the file wrote as nothing.
Before 2.343 the notes standing beside them were written plain: only totals moved.
"""
from __future__ import annotations

import collections
import json
import pathlib
import unittest

from tools.omr.staged import export as SX

FIX = pathlib.Path(__file__).parent / "fixtures"
FIRST, MIDDLE, LAST = "glyph/2/0/7/9/1", "glyph/2/0/7/10/3", "glyph/2/0/7/11/2"
SLUR_ROW, SLUR_START, SLUR_STOP = "obs:564481", "glyph/14/1/2/10/3", "glyph/14/1/2/11/5"
UNREAD_ROW, UNREAD_START, UNREAD_STOP = "obs:013999", "glyph/1/0/2/3/1", "glyph/1/0/2/4/1"


def _record(name, drop_pitch_of=()):
    d = json.loads((FIX / name).read_text())
    rows = [v for v in d["verdicts"] if not (v["quantity"] == "pitch" and v["subject"] in drop_pitch_of)]
    return SX.Record({"record": {"observations": d.get("observations", []), "verdicts": rows, "abstentions": []}})


def _head(glyph):
    return {"glyph": glyph, "category": "notehead", "pitch": "F4", "duration_beats": 2.0, "duration_type": "half", "dots": 0}


def _xml(head):
    lines, _ = SX._measure_events_xml([{"kind": "note", "noteheads": [head]}], 2, collections.Counter())
    return "\n".join(lines)


def _words(head):
    return head.get("unread_arc_words") or []


class TestWording(unittest.TestCase):
    def test_the_final_strings(self):
        self.assertEqual(SX.TIE_FROM_UNREAD_NOTE_WORD, "tie from unread note")
        self.assertEqual(SX.TIE_TO_UNREAD_NOTE_WORD, "tie to unread note")
        self.assertEqual(SX.SLUR_FROM_UNREAD_NOTE_WORD, "slur from unread note")
        self.assertEqual(SX.SLUR_TO_UNREAD_NOTE_WORD, "slur to unread note")
        self.assertEqual(SX.ARC_FROM_UNREAD_NOTE_WORD, "arc from unread note")
        self.assertEqual(SX.ARC_TO_UNREAD_NOTE_WORD, "arc to unread note")
        self.assertEqual(SX.ARC_KIND_UNREAD_WORD, "arc: tie or slur unread")

    def test_the_term_is_the_2_333_spot_marks(self):
        for w in (SX.TIE_FROM_UNREAD_NOTE_WORD, SX.SLUR_TO_UNREAD_NOTE_WORD, SX.ARC_FROM_UNREAD_NOTE_WORD):
            self.assertTrue(w.endswith(SX.DROPPED_HEAD_SPOT_WORD))


class TestTieWithAnUnwrittenNote(unittest.TestCase):
    def _run(self, written, drop_pitch_of=()):
        rec = _record("tie_unwritten_middle_litolff_p2_20261123.json", drop_pitch_of)
        ties = SX._record_tie_pairs(rec)
        heads = {g: _head(g) for g in written}
        bars = [{"detections": [heads[g]]} if g in heads else {"detections": []} for g in (FIRST, MIDDLE, LAST)]
        dropped, counters = collections.Counter(), collections.Counter()
        spans = SX._record_tie_spans(bars, ties, {}, dropped, rec=rec, counters=counters)
        lost = {("tie", k) for k in ties["pairs"] if k not in ties["consumed"]}
        SX._mark_half_written_arcs(ties.get("half_written", []), lost, rec, counters)
        return heads, counters, spans, lost

    def test_the_fixture_is_the_real_chain(self):
        ties = SX._record_tie_pairs(_record("tie_unwritten_middle_litolff_p2_20261123.json"))
        self.assertEqual(set(ties["pairs"]), {(FIRST, MIDDLE), (MIDDLE, LAST)})

    def test_first_note_unwritten_marks_the_surviving_second_note(self):
        heads, counters, spans, lost = self._run([FIRST, LAST])
        self.assertEqual(spans, [])                                   # no tie is written onto a note that is not there
        self.assertEqual(_words(heads[LAST]), ["tie from unread note"])
        self.assertFalse(heads[LAST].get("tied_from_prev"))
        self.assertEqual(counters["tie_from_unread_note_marked"], 1)
        xml = _xml(heads[LAST])
        self.assertIn("tie from unread note", xml)
        self.assertIn(SX.UNREAD_BAR_MARK_COLOR, xml)
        self.assertNotIn("<tie", xml)
        self.assertEqual(xml.count("<note>"), 1)                      # nothing invented

    def test_last_note_unwritten_marks_the_surviving_first_note(self):
        heads, counters, spans, lost = self._run([FIRST, LAST])
        self.assertEqual(_words(heads[FIRST]), ["tie to unread note"])
        self.assertFalse(heads[FIRST].get("tied_to_next"))
        self.assertEqual(counters["tie_to_unread_note_marked"], 1)

    def test_both_written_is_untouched(self):
        heads, counters, spans, lost = self._run([FIRST, MIDDLE, LAST])
        self.assertEqual(len(spans), 2)
        self.assertEqual(lost, set())
        for h in heads.values():
            self.assertEqual(_words(h), [])
            self.assertNotIn("unread note", _xml(h))

    def test_both_unwritten_is_counted_not_marked(self):
        heads, counters, spans, lost = self._run([FIRST])
        self.assertEqual(counters["tie_both_ends_unwritten"], 1)
        self.assertEqual(_words(heads[FIRST]), ["tie to unread note"])

    def test_an_end_whose_pitch_was_not_read_makes_it_an_arc(self):
        # the kind rests on the unwritten end's position and pitch: where its pitch was not decided, the mark says only `arc`
        heads, counters, spans, lost = self._run([FIRST, LAST], drop_pitch_of=(MIDDLE,))
        self.assertEqual(_words(heads[LAST]), ["arc from unread note"])
        self.assertEqual(_words(heads[FIRST]), ["arc to unread note"])
        self.assertEqual(counters["arc_from_unread_note_marked"], 1)

    def test_a_pair_another_part_wrote_is_not_marked(self):
        rec = _record("tie_unwritten_middle_litolff_p2_20261123.json")
        ties = SX._record_tie_pairs(rec)
        a = _head(FIRST)
        SX._record_tie_spans([{"detections": [a]}, {"detections": []}, {"detections": []}], ties, {}, collections.Counter(), rec=rec, counters={})
        ties["consumed"].add((FIRST, MIDDLE))
        SX._mark_half_written_arcs(ties["half_written"], {("tie", k) for k in ties["pairs"] if k not in ties["consumed"]}, rec, collections.Counter())
        self.assertEqual(_words(a), [])

    def test_a_note_already_tied_on_that_side_is_not_marked(self):
        rec = _record("tie_unwritten_middle_litolff_p2_20261123.json")
        ties = SX._record_tie_pairs(rec)
        a = _head(FIRST)
        a["tied_to_next"] = True                                       # another pair wrote it
        SX._record_tie_spans([{"detections": [a]}, {"detections": []}, {"detections": []}], ties, {}, collections.Counter(), rec=rec, counters={})
        SX._mark_half_written_arcs(ties["half_written"], {("tie", k) for k in ties["pairs"]}, rec, collections.Counter())
        self.assertEqual(_words(a), [])


class TestSlurAndUnreadKindArc(unittest.TestCase):
    def setUp(self):
        self.rec = _record("arc_unwritten_end_litolff_20261123.json")
        self.plan = SX._page_arc_plan(self.rec)

    def _run(self, row):
        return next(r for r in self.plan["runs"] if r["row"] == row)

    def test_the_fixture_runs_are_the_real_ones(self):
        r = self._run(SLUR_ROW)
        self.assertEqual((r["status"], r["kind"], r["start"], r["stop"]), ("written", "slur", SLUR_START, SLUR_STOP))
        u = self._run(UNREAD_ROW)
        self.assertTrue(u["kind_unread"])
        self.assertEqual((u["start"], u["stop"], u["why"]), (UNREAD_START, UNREAD_STOP, "step_between"))

    def _slur(self, written, rec=None):
        rec = rec or self.rec
        bound = {"page_arc/%s" % SLUR_ROW: {"start": SLUR_START, "stop": SLUR_STOP, "pieces": 1}}
        heads = {g: _head(g) for g in written}
        halves, counters, done = [], collections.Counter(), set()
        spans = SX._page_bound_slur_spans([{"detections": list(heads.values()), "bbox_page_px": None}], bound, {}, set(), done, counters, rec=rec,
                                          halves=halves)
        unwritten = {("slur", c) for c in bound if c not in done}
        SX._mark_half_written_arcs(halves, unwritten, rec, counters)
        return heads, counters, spans

    def test_slur_stop_unwritten_marks_the_surviving_first_note(self):
        heads, counters, spans = self._slur([SLUR_START])
        self.assertEqual(spans, [])
        self.assertEqual(_words(heads[SLUR_START]), ["slur to unread note"])
        self.assertEqual(counters["slur_to_unread_note_marked"], 1)
        self.assertIn("slur to unread note", _xml(heads[SLUR_START]))
        self.assertNotIn("<slur", _xml(heads[SLUR_START]))

    def test_slur_start_unwritten_marks_the_surviving_second_note(self):
        heads, counters, spans = self._slur([SLUR_STOP])
        self.assertEqual(_words(heads[SLUR_STOP]), ["slur from unread note"])

    def test_slur_end_unread_pitch_says_arc(self):
        rec = _record("arc_unwritten_end_litolff_20261123.json", drop_pitch_of=(SLUR_STOP,))
        heads, counters, spans = self._slur([SLUR_START], rec=rec)
        self.assertEqual(_words(heads[SLUR_START]), ["arc to unread note"])

    def test_both_ends_unwritten_is_counted(self):
        heads, counters, spans = self._slur([])
        self.assertEqual(counters["slur_both_ends_unwritten"], 1)

    def _unread(self, written):
        runs = [r for r in self.plan["runs"] if r.get("kind_unread") and r["row"] == UNREAD_ROW]
        heads = {g: _head(g) for g in written}
        halves, counters = [], collections.Counter()
        SX._register_unread_kind_runs([{"detections": list(heads.values())}], runs, halves)
        SX._mark_half_written_arcs(halves, {("run", UNREAD_ROW)}, self.rec, counters)
        return heads, counters

    def test_both_notes_written_arc_of_unread_kind_is_marked_on_its_first_note(self):
        heads, counters = self._unread([UNREAD_START, UNREAD_STOP])
        self.assertEqual(_words(heads[UNREAD_START]), ["arc: tie or slur unread"])
        self.assertEqual(_words(heads[UNREAD_STOP]), [])
        self.assertEqual(counters["arc_kind_unread_marked"], 1)
        xml = _xml(heads[UNREAD_START])
        self.assertIn("arc: tie or slur unread", xml)
        self.assertNotIn("<slur", xml)
        self.assertNotIn("<tie", xml)

    def test_arc_of_unread_kind_with_one_note_says_arc_from_or_to(self):
        heads, _ = self._unread([UNREAD_STOP])
        self.assertEqual(_words(heads[UNREAD_STOP]), ["arc from unread note"])
        heads, _ = self._unread([UNREAD_START])
        self.assertEqual(_words(heads[UNREAD_START]), ["arc to unread note"])


if __name__ == "__main__":
    unittest.main()
