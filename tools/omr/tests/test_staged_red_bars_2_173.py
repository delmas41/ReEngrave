"""ROADMAP 2.173: a bar that does not add up is WRITTEN in red, never held out.

Sean, 2026-10-19: *"Written in red instead of held out is the way to go."*
STAGED EXPORT, behind `OMR_RED_BARS` (OFF). Each pair below differs by the
flag only, so the rule is a test and not a switch.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest import mock

from tools.omr import acceptance as ACC
from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page

FOUR_FOUR = {"numerator": 4, "denominator": 4, "raw": "4/4"}
RED = "#D00000"
SHORT = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)]            # 3 of 4
OVER = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER),
        ("F4", QUARTER), ("G4", QUARTER)]                              # 5 of 4
FULL = [("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER), ("F4", QUARTER)]


def _xml(notes, flag):
    with mock.patch.dict(os.environ, {"OMR_RED_BARS": flag,
                                      "OMR_PARTIAL_BARS": "on"}):
        return SX.to_musicxml(_one_staff_page(notes=notes, meter=FOUR_FOUR))


def _ly(notes, flag):
    with mock.patch.dict(os.environ, {"OMR_RED_BARS": flag,
                                      "OMR_PARTIAL_BARS": "on"}):
        return LY.to_lilypond(_one_staff_page(notes=notes, meter=FOUR_FOUR))


def _steps(xml):
    return [n.find("pitch/step").text
            for n in ET.fromstring(xml).findall(".//note")
            if n.find("pitch") is not None]


class TestOffIsTheHoldOut(unittest.TestCase):
    def test_off_holds_the_short_bar_out_exactly_as_before(self):
        xml, rep = _xml(SHORT, "0")
        self.assertEqual(_steps(xml), [])
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertNotIn("bars_written_red", rep)

    def test_off_and_unset_are_the_same_file(self):
        a, _ = _xml(SHORT, "0")
        env = {k: v for k, v in os.environ.items() if k != "OMR_RED_BARS"}
        with mock.patch.dict(os.environ, env, clear=True):
            b, _ = SX.to_musicxml(_one_staff_page(notes=SHORT, meter=FOUR_FOUR))
        self.assertEqual(a, b)


class TestShortBarIsWrittenRed(unittest.TestCase):
    def test_every_read_note_is_in_the_file_at_its_read_value_and_red(self):
        xml, rep = _xml(SHORT, "1")
        self.assertEqual(_steps(xml), ["C", "D", "E"])
        notes = ET.fromstring(xml).findall(".//note")
        self.assertEqual([n.get("color") for n in notes], [RED] * 3)
        self.assertEqual({n.findtext("type") for n in notes}, {"quarter"})
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 0)

    def test_nothing_is_padded_no_rest_no_forward(self):
        xml, _ = _xml(SHORT, "1")
        root = ET.fromstring(xml)
        self.assertEqual(root.findall(".//note/rest"), [])
        self.assertEqual(root.findall(".//measure/forward"), [])
        meas = root.find(".//measure")
        dur = sum(int(n.findtext("duration")) for n in meas.findall("note"))
        div = int(root.find(".//divisions").text)
        self.assertEqual(dur / div, 3.0)              # counted 3, not padded to 4

    def test_one_bar_level_marking_says_want_and_counted(self):
        xml, rep = _xml(SHORT, "1")
        root = ET.fromstring(xml)
        words = [w.text for w in root.findall(".//words")]
        self.assertEqual(words, ["does not add up: should hold 4, counted 3 "
                                 "(quarters)"])
        br = root.findall(".//bracket")
        self.assertEqual([b.get("type") for b in br], ["start", "stop"])
        self.assertTrue(all(b.get("color") == RED for b in br))
        self.assertEqual(rep["bars_written_red"]["bars"], 1)

    def test_the_coverage_keeps_each_event_and_its_status(self):
        _xml_, rep = _xml(SHORT, "1")
        b = rep["bars_written_red"]["bars_list"][0]
        self.assertEqual([(r["pitch"], r["beats"], r["status"])
                          for r in b["rows"] if r["kind"] == "note"],
                         [(r["pitch"], 1.0, "READ") for r in b["rows"]])
        self.assertEqual((b["read"], b["guessed"]), (3, 0))
        self.assertEqual((b["want_quarters"], b["counted_quarters"]),
                         (4.0, [3.0]))

    def test_the_red_bar_events_equal_the_held_bars_events(self):
        """A control that can fail: the SAME bar under OFF names the same rows."""
        _x, off = _xml(SHORT, "0")
        _y, on = _xml(SHORT, "1")
        held = off["bars_held_out_sum"]["held"][0]
        red = on["bars_written_red"]["bars_list"][0]
        self.assertEqual(held["noteheads_and_rests"], red["noteheads_and_rests"])
        self.assertEqual(held["bar_key"], red["bar_key"])

    def test_the_accounting_balances_nothing_is_dropped_for_the_sum(self):
        _x, rep = _xml(SHORT, "1")
        self.assertEqual(rep["notes_not_written"].get("bar_does_not_add_up", 0), 0)
        self.assertEqual(rep["written"]["notes"], 3)

    def test_a_bar_that_adds_up_is_untouched(self):
        xml, rep = _xml(FULL, "1")
        notes = ET.fromstring(xml).findall(".//note")
        self.assertTrue(all(n.get("color") is None for n in notes))
        self.assertEqual(rep["bars_written_red"]["bars"], 0)


class TestOverfullBar(unittest.TestCase):
    def test_all_five_notes_are_written_at_their_read_value(self):
        xml, rep = _xml(OVER, "1")
        self.assertEqual(_steps(xml), ["C", "D", "E", "F", "G"])
        self.assertIn("counted 5", rep["bars_written_red"]["bars_list"][0]["words"])


class TestAcceptanceControl(unittest.TestCase):
    def test_a_red_bar_is_not_a_bar_that_adds_up_and_is_its_own_number(self):
        xml, rep = _xml(SHORT, "1")
        c = ACC.bars_add_up(xml)
        self.assertEqual((c["exact"], c["short"], c["written_red"]), (0, 0, 1))
        p = ACC.machine_proxies(xml, rep)
        self.assertEqual(p["bars_written_red"]["n"], 1)
        self.assertTrue(p["bars_written_red"]["flag_on"])

    def test_off_reports_no_red(self):
        xml, rep = _xml(SHORT, "0")
        self.assertEqual(ACC.bars_add_up(xml)["written_red"], 0)
        self.assertFalse(ACC.machine_proxies(xml, rep)["bars_written_red"]["flag_on"])


class TestLilyPond(unittest.TestCase):
    def test_off_has_no_red_text(self):
        ly, _ = _ly(SHORT, "0")
        self.assertNotIn("does not add up", ly)

    def test_short_bar_is_an_invisible_skip_never_a_rest_or_a_stretch(self):
        ly, rep = _ly(SHORT, "1")
        line = next(l for l in ly.splitlines() if "does not add up" in l)
        self.assertIn("s1*1/4", line)
        self.assertNotIn("scaleDurations", line)
        self.assertNotRegex(line, r"(?<![a-zA-Z\\])r[0-9]")
        self.assertEqual(rep["written"]["bars_written_red"], 1)

    def test_overfull_bar_keeps_printed_values_and_fits_the_clock(self):
        ly, _ = _ly(OVER, "1")
        line = next(l for l in ly.splitlines() if "does not add up" in l)
        self.assertIn("\\scaleDurations 4/5", line)
        self.assertIn("g'4", line)                              # a quarter stays a quarter
        self.assertNotIn("measureLength", line)

    @unittest.skipUnless(shutil.which("lilypond"), "lilypond not installed")
    def test_both_compile_with_no_barcheck_failure(self):
        for notes in (SHORT, OVER):
            ly, _ = _ly(notes, "1")
            with tempfile.TemporaryDirectory() as d:
                p = os.path.join(d, "t.ly")
                open(p, "w").write(ly)
                r = subprocess.run(["lilypond", "-o", os.path.join(d, "t"), p],
                                   capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr[-400:])
                self.assertNotIn("barcheck", r.stderr)


if __name__ == "__main__":
    unittest.main()
