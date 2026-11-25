"""ROADMAP 2.348 (a) -- a system whose meter ADJUDICATE never decided is MARKED `meter?` in both files.

STAGED EXPORT. Before: a system whose `Q.METER` verdict is abstained (`carry_outweighed_by_the_bars`, Brahms 1 system/6/1 and
system/21/0 in the 20261123-night record) wrote a bare `<attributes>` block with no `<time>` (key and clef restated in every part)
and nothing said the meter was unread; only `meter_return_not_read` got the red `meter?` (2.12k). Now `_meter_unread_marker` names
the system's first bar and the SAME red word is written above it, in MusicXML and in the LilyPond twin, and counted.

CONTROL FROM REAL ROWS (CLAUDE.md rule 7): `fixtures/meter_abstained_2_348_brahms.json` is the two abstained verdicts as the saved
record filed them. NEVER-CONTROLS: a decided meter is not marked; `meter_return_not_read` keeps its single mark on its own bar (not
a second one on bar 0); no `<time>` is written by the mark; the bars' notes are kept.
"""
from __future__ import annotations

import json
import pathlib
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as staged_lily
from tools.omr.staged.record import Q
from tools.omr.tests.test_staged_export import QUARTER, _log_json, _obs, _vrd

FIX = pathlib.Path(__file__).parent / "fixtures" / "meter_abstained_2_348_brahms.json"
ROWS = {r["subject"]: r for r in json.loads(FIX.read_text())["rows"]}


def _notes(obs, vrd, page, system, cell, pitches, start_id):
    for k, pitch in enumerate(pitches):
        sub = f"glyph/{page}/{system}/0/{cell}/{100 * cell + k}"
        obs.append(_obs(start_id + 4 * k, sub, Q.GLYPH_BOX, ["noteheadBlackOnLine", 100 * k, 50, 40, 40], category="notehead"))
        obs.append(_obs(start_id + 4 * k + 1, sub, Q.NOTEHEAD_CLASS, "noteheadBlackOnLine"))
        vrd.append(_vrd(start_id + 4 * k + 2, sub, Q.PITCH, pitch))
        vrd.append(_vrd(start_id + 4 * k + 3, sub, Q.DURATION, QUARTER))


def _page(subject, meter_row):
    """One system on the REAL page/system of the saved verdict, one staff, two bars of notes."""
    _, page, system = subject.split("/")
    obs, vrd = [], []
    _notes(obs, vrd, page, system, 0, ["C4", "D4"], 0)
    _notes(obs, vrd, page, system, 1, ["E4", "F4", "G4"], 100)
    vrd.append(_vrd(900, f"staff/{page}/{system}/0", Q.MEASURE_PARTITION, 2))
    vrd.append(_vrd(901, f"staff/{page}/{system}/0", Q.CLEF, "treble"))
    vrd.append(_vrd(902, subject, Q.SYSTEM_STAFF_COUNT, 1))
    vrd.append(_vrd(903, "document", Q.PART_PARTITION, {"join": "ordinal", "staves_per_system": 1}, reason="ordinal"))
    if meter_row is not None:
        v = _vrd(904, subject, Q.METER, meter_row["value"], outcome=meter_row["outcome"], reason=meter_row["reason"])
        v["detail"] = dict(meter_row.get("detail") or {})
        vrd.append(v)
    return _log_json(obs, vrd)


def _words(xml):
    return [d.find("./direction-type/words") for d in ET.fromstring(xml).findall(".//direction")
            if d.find("./direction-type/words") is not None]


class TestRealAbstainedMeters(unittest.TestCase):

    def test_the_saved_rows_are_what_the_test_claims(self):
        for sub, row in ROWS.items():
            self.assertEqual((row["outcome"], row["reason"]), ("abstained", "carry_outweighed_by_the_bars"), sub)

    def test_musicxml_marks_the_first_bar_in_red_and_writes_no_time(self):
        for sub, row in ROWS.items():
            xml, rep = SX.to_musicxml(_page(sub, row))
            measures = ET.fromstring(xml).findall(".//measure")
            self.assertEqual(len(measures), 2, sub)
            marks = [w for w in _words(xml) if w.text == "meter?"]
            self.assertEqual(len(marks), 1, sub)
            self.assertEqual(marks[0].get("color"), SX.UNREAD_BAR_MARK_COLOR)
            self.assertEqual([w.text for w in _words(ET.tostring(measures[0]).decode())], ["meter?"], sub)       # on bar 0
            self.assertEqual(ET.fromstring(xml).findall(".//time"), [], sub)                                      # nothing invented
            self.assertEqual([p.text for p in measures[0].findall(".//note/pitch/step")], ["C", "D"], sub)        # the notes stay
            self.assertEqual(rep["meters_not_read"], 1, sub)

    def test_lilypond_draws_the_same_mark_and_counts_it(self):
        for sub, row in ROWS.items():
            text, rep = staged_lily.to_lilypond(_page(sub, row))
            self.assertEqual(text.count('\\mark \\markup { \\with-color #red "meter?" }'), 1, sub)
            self.assertEqual(rep["meters_not_read"], 1, sub)
            self.assertEqual(rep["meter_returns_not_read"], 0, sub)

    def test_the_word_is_the_one_the_unread_return_already_uses(self):
        self.assertEqual(SX.UNREAD_BAR_MARK_WORDS[SX.METER_RETURN_NOT_READ_REASON], "meter?")


class TestNevers(unittest.TestCase):

    def test_a_decided_meter_is_not_marked(self):
        sub = "system/6/1"
        row = {"outcome": "decided", "reason": "carried", "value": {"numerator": 6, "denominator": 8, "raw": "6/8"}, "detail": {}}
        xml, rep = SX.to_musicxml(_page(sub, row))
        self.assertNotIn("meter?", [w.text for w in _words(xml)])
        self.assertEqual(rep["meters_not_read"], 0)
        text, ly = staged_lily.to_lilypond(_page(sub, row))
        self.assertNotIn("meter?", text)
        self.assertEqual(ly["meters_not_read"], 0)

    def test_an_unread_return_keeps_its_one_mark_on_its_own_bar(self):
        sub = "system/6/1"
        row = {"outcome": "abstained", "reason": SX.METER_RETURN_NOT_READ_REASON, "value": None,
               "detail": {"at_cell": 1, "carried_via_cautionary": True}}
        xml, rep = SX.to_musicxml(_page(sub, row))
        measures = ET.fromstring(xml).findall(".//measure")
        self.assertEqual(_words(ET.tostring(measures[0]).decode()), [])          # bar 0 is not marked a second time
        self.assertEqual([w.text for w in _words(ET.tostring(measures[1]).decode())], ["meter?"])
        self.assertEqual((rep["meter_returns_not_read"], rep["meters_not_read"]), (1, 0))

    def test_no_meter_verdict_at_all_is_not_marked(self):
        """A system with no `Q.METER` verdict (nothing asked) is not an abstention; the mark is for a verdict that said it could not tell."""
        xml, rep = SX.to_musicxml(_page("system/6/1", None))
        self.assertNotIn("meter?", [w.text for w in _words(xml)])
        self.assertEqual(rep["meters_not_read"], 0)


if __name__ == "__main__":
    unittest.main()
