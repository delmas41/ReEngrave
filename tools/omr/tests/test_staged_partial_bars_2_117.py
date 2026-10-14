"""ROADMAP 2.117: a bar that does not add up keeps what was read.

Sean, 2026-10-14: *"If we have a bar and know that there is a quarter note in
the measure on beat 1, I don't want that [lost] because we can't figure out
beat 3."* STAGED EXPORT, behind `OMR_PARTIAL_BARS` (off | measure | on).

The pairs below differ by one fact each (a glyph's position, whether a glyph
was refused at all, the flag), so the rule is a TEST and not a switch.
"""

import os
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr.staged import export as SX
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page

FOUR_FOUR = {"numerator": 4, "denominator": 4, "raw": "4/4"}
RED = "#D00000"


def _export(notes, mode="on", meter=FOUR_FOUR):
    with mock.patch.dict(os.environ, {"OMR_PARTIAL_BARS": mode}):
        return SX.to_musicxml(_one_staff_page(notes=notes, meter=meter))


def _steps(xml):
    return [n.find("pitch/step").text
            for n in ET.fromstring(xml).findall(".//note")
            if n.find("pitch") is not None]


class TestPrefixAndSuffixAreKept(unittest.TestCase):
    NOTES = [("C4", QUARTER), ("D4", None), ("E4", QUARTER), ("F4", QUARTER)]

    def test_a_quarter_on_beat_one_survives_an_unread_head_after_it(self):
        xml, rep = _export(self.NOTES)
        self.assertEqual(_steps(xml), ["C", "E", "F"])
        self.assertEqual(rep["partial_bars"]["written"], 1)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)

    def test_the_suffix_is_anchored_back_from_the_barline(self):
        """C(1) gap(1) E F: E sits on beat 3, not beat 2."""
        xml, _ = _export(self.NOTES)
        offs, t = {}, 0
        for n in ET.fromstring(xml).find(".//measure"):
            if n.tag != "note":
                continue
            step = n.find("pitch/step")
            if step is not None:
                offs[step.text] = t
            t += int(n.find("duration").text)
        div = int(ET.fromstring(xml).find(".//divisions").text)
        self.assertEqual({k: v / div for k, v in offs.items()},
                         {"C": 0.0, "E": 2.0, "F": 3.0})

    def test_the_gap_is_red_worded_unread_and_never_a_plain_rest(self):
        xml, _ = _export(self.NOTES)
        root = ET.fromstring(xml)
        rests = root.findall(".//note/rest/..")
        self.assertEqual(len(rests), 1)
        self.assertEqual(rests[0].get("color"), RED)
        self.assertIsNone(rests[0].find("rest").get("measure"))
        words = [w.text for w in root.findall(".//words")]
        self.assertIn("unread", words)

    def test_every_row_still_balances_and_the_gap_head_is_counted(self):
        _xml, rep = _export(self.NOTES)
        self.assertEqual(rep["notes_not_written"].get(SX._GAP_REFUSAL, 0)
                         + rep["notes_not_written"].get("duration_narrowed", 0),
                         1)
        self.assertEqual(rep["written"]["notes"], 3)

    def test_partial_bars_are_reported_apart_from_held_ones(self):
        _xml, rep = _export(self.NOTES)
        b = rep["partial_bars"]["bars"][0]
        self.assertEqual((b["status"], b["rows_written"]), ("partial", 3))


class TestABarWithNoLocatableGapStaysHeld(unittest.TestCase):
    def test_short_with_no_refused_glyph_is_held(self):
        """The 109 kind: a note was never boxed, so it may be anywhere --
        before the quarter on beat 1 as well as after it."""
        xml, rep = _export([("C4", QUARTER), ("E4", QUARTER)])
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["partial_bars"]["written"], 0)
        self.assertEqual(_steps(xml), [])
        self.assertEqual(
            rep["partial_bars"]["stay_held_by_reason"],
            {"short_without_an_unread_symbol": 1})

    def test_an_overfull_bar_stays_held(self):
        notes = [("C4", QUARTER)] * 4 + [("D4", None)]
        notes = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER),
                 ("F4", QUARTER), ("G4", QUARTER), ("A4", None)]
        _xml, rep = _export(notes)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["partial_bars"]["written"], 0)

    def test_a_bar_with_no_read_event_is_the_old_unread_bar(self):
        _xml, rep = _export([("C4", None)])
        self.assertEqual(rep["partial_bars"]["written"], 0)
        self.assertEqual(rep["written"]["empty_bars_padded"], 1)


class TestTheFlag(unittest.TestCase):
    NOTES = TestPrefixAndSuffixAreKept.NOTES

    def test_off_and_measure_write_the_identical_file(self):
        off, _ = _export(self.NOTES, mode="")
        meas, rep = _export(self.NOTES, mode="measure")
        self.assertEqual(off, meas)
        self.assertEqual(rep["partial_bars"]["planned_bars"], 1)
        self.assertEqual(rep["partial_bars"]["written"], 0)

    def test_off_holds_the_bar_as_before(self):
        xml, rep = _export(self.NOTES, mode="")
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(_steps(xml), [])

    def test_an_unknown_value_is_off(self):
        _xml, rep = _export(self.NOTES, mode="maybe")
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)


class TestAGuessedDurationEndsThePrefix(unittest.TestCase):
    def test_events_after_a_duration_guess_are_not_prefix(self):
        def ev(x, guessed):
            h = {"bbox": [x, 0, 40, 40], "duration_beats": 1.0}
            if guessed:
                h["guess"] = {"quantity": SX.Q.DURATION}
            return {"kind": "chord", "x_position": x + 20, "noteheads": [h],
                    "duration_beats": 1.0}
        stream = [ev(0, True), ev(100, False), ev(400, False)]
        p = SX._plan_one_stream(stream, 4 * 8, 8, [250.0], 24.0)
        # events 0 and 1 are left of the gap, but 0's duration is a guess:
        # 0 is kept (its onset is certain), 1's onset is not.
        self.assertEqual(len(p["pre"]), 1)
        self.assertEqual(len(p["mid"]), 1)
        self.assertEqual(len(p["suf"]), 1)


if __name__ == "__main__":
    unittest.main()
