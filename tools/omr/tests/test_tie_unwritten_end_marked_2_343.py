"""ROADMAP 2.343: a tie whose one note is not in the file is MARKED, never dropped silently (STAGED EXPORT,
`export._record_tie_spans` + `_mark_half_written_ties`).

The control is a REAL case (rule 7): Litolff p2 staff 7, bars 9-11 (overnight 20261123-night record), a half-note F4 tied to a half-note
F4 tied to a half-note F4. The middle note (`glyph/2/0/7/10/3`) was never written (its duration was abstained `wide_box_unread`), so
BOTH ties of the chain lose a note: the first note's tie goes to a note that is not there (the mirror case: last note unwritten), the
third note's tie comes from one (first note unwritten). The rows below are that record's own verdicts, saved in the fixture.
Before 2.343 both surviving notes were written plain: only the total `tie_end_not_in_file` moved.
"""
from __future__ import annotations

import collections
import json
import pathlib
import unittest

from tools.omr.staged import export as SX

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "tie_unwritten_middle_litolff_p2_20261123.json"
FIRST, MIDDLE, LAST = "glyph/2/0/7/9/1", "glyph/2/0/7/10/3", "glyph/2/0/7/11/2"


def _rec():
    rows = json.loads(FIXTURE.read_text())["verdicts"]
    return SX.Record({"record": {"observations": [], "verdicts": rows, "abstentions": []}})


def _head(glyph):
    return {"glyph": glyph, "category": "notehead", "pitch": "F4", "duration_beats": 2.0, "duration_type": "half", "dots": 0}


def _export(written):
    """Run the part pass over the bars of the chain holding only the `written` heads; return (heads, dropped, counters, spans)."""
    rec = _rec()
    ties = SX._record_tie_pairs(rec)
    heads = {g: _head(g) for g in written}
    bars = [{"detections": [heads[g]]} if g in heads else {"detections": []} for g in (FIRST, MIDDLE, LAST)]
    dropped, counters = collections.Counter(), collections.Counter()
    spans = SX._record_tie_spans(bars, ties, {}, dropped, rec=rec, counters=counters)
    lost = {k for k in ties["pairs"] if k not in ties["consumed"]}
    SX._mark_half_written_ties(ties, lost, counters)
    return heads, dropped, counters, spans, lost


def _xml(head):
    lines, _ = SX._measure_events_xml([{"kind": "note", "noteheads": [head]}], 2, collections.Counter())
    return "\n".join(lines)


class TestTieWithAnUnwrittenNote(unittest.TestCase):
    def test_the_fixture_is_the_real_chain(self):
        ties = SX._record_tie_pairs(_rec())
        self.assertEqual(set(ties["pairs"]), {(FIRST, MIDDLE), (MIDDLE, LAST)})

    def test_first_note_unwritten_marks_the_surviving_stop(self):
        heads, dropped, counters, spans, lost = _export([FIRST, LAST])
        self.assertEqual(spans, [])                                  # no tie is written onto a note that is not there
        self.assertEqual(len(lost), 2)
        self.assertFalse(heads[LAST].get("tied_from_prev"))
        self.assertTrue(heads[LAST].get("tie_unread_from_prev"))
        self.assertEqual(counters["tie_first_note_unwritten_marked"], 1)
        xml = _xml(heads[LAST])
        self.assertIn(SX.TIE_UNREAD_WORD_FROM, xml)
        self.assertIn(SX.UNREAD_BAR_MARK_COLOR, xml)
        self.assertNotIn("<tie", xml)
        self.assertEqual(xml.count("<note>"), 1)                     # nothing invented: the one written note

    def test_last_note_unwritten_marks_the_surviving_start(self):
        # the mirror: the written note's tie goes to a note that is not there
        heads, dropped, counters, spans, lost = _export([FIRST, LAST])
        self.assertTrue(heads[FIRST].get("tie_unread_to_next"))
        self.assertFalse(heads[FIRST].get("tied_to_next"))
        self.assertEqual(counters["tie_last_note_unwritten_marked"], 1)
        self.assertIn(SX.TIE_UNREAD_WORD_TO, _xml(heads[FIRST]))

    def test_both_notes_written_is_untouched(self):
        heads, dropped, counters, spans, lost = _export([FIRST, MIDDLE, LAST])
        self.assertEqual(len(spans), 2)
        self.assertEqual(lost, set())
        for h in heads.values():
            self.assertFalse(h.get("tie_unread_from_prev") or h.get("tie_unread_to_next"))
            self.assertNotIn("tie not written", _xml(h))

    def test_both_ends_unwritten_is_counted_not_marked(self):
        heads, dropped, counters, spans, lost = _export([FIRST])    # (MIDDLE, LAST): neither written
        self.assertEqual(counters["tie_both_ends_unwritten"], 1)
        self.assertEqual(counters["tie_one_end_unwritten_pairs"], 1)

    def test_a_pair_another_part_wrote_is_not_marked(self):
        # `consumed` is shared by every part: a pair some part wrote both ends of is not "lost" and marks nothing
        rec = _rec()
        ties = SX._record_tie_pairs(rec)
        a = _head(FIRST)
        SX._record_tie_spans([{"detections": [a]}, {"detections": []}, {"detections": []}], ties, {}, collections.Counter(), rec=rec, counters={})
        ties["consumed"].add((FIRST, MIDDLE))
        counters = collections.Counter()
        SX._mark_half_written_ties(ties, {k for k in ties["pairs"] if k not in ties["consumed"]}, counters)
        self.assertFalse(a.get("tie_unread_to_next"))

    def test_a_note_already_tied_on_that_side_is_not_marked(self):
        rec = _rec()
        ties = SX._record_tie_pairs(rec)
        a = _head(FIRST)
        a["tied_to_next"] = True                                      # another pair wrote it
        SX._record_tie_spans([{"detections": [a]}, {"detections": []}, {"detections": []}], ties, {}, collections.Counter(), rec=rec, counters={})
        SX._mark_half_written_ties(ties, set(ties["pairs"]), collections.Counter())
        self.assertFalse(a.get("tie_unread_to_next"))


if __name__ == "__main__":
    unittest.main()
