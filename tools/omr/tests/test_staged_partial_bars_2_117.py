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
from tools.omr.staged import lilypond as LY
from tools.omr.tests.test_staged_export import QUARTER, _one_staff_page


# ROADMAP 2.173 (`OMR_RED_BARS` default ON, Sean 2026-10-19/20): this file tests the
# pre-2.173 path (bar held out / old whole value); pinned OFF here.
_PIN_2_173 = None


def setUpModule():
    global _PIN_2_173
    import os as _os
    from unittest import mock as _mock
    _PIN_2_173 = _mock.patch.dict(_os.environ, {"OMR_RED_BARS": "0"})
    _PIN_2_173.start()


def tearDownModule():
    _PIN_2_173.stop()

FOUR_FOUR = {"numerator": 4, "denominator": 4, "raw": "4/4"}
RED = "#D00000"
BLUE = "#1F6FEB"


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
            if n.tag == "forward":
                t += int(n.find("duration").text)
            if n.tag != "note":
                continue
            step = n.find("pitch/step")
            if step is not None:
                offs[step.text] = t
            t += int(n.find("duration").text)
        div = int(ET.fromstring(xml).find(".//divisions").text)
        self.assertEqual({k: v / div for k, v in offs.items()},
                         {"C": 0.0, "E": 2.0, "F": 3.0})

    def test_the_gap_is_a_red_bracket_and_NO_rest_glyph(self):
        """Sean, 2026-10-14: *"Use a red bracket instead"* -- a rest, even
        red, reads as silence (rule 8). The gap is an invisible `<forward>`
        under a red bracket and the word `unread`."""
        xml, _ = _export(self.NOTES)
        root = ET.fromstring(xml)
        self.assertEqual(root.findall(".//note/rest"), [])
        fw = root.findall(".//measure/forward")
        self.assertEqual(len(fw), 1)
        br = root.findall(".//bracket")
        self.assertEqual([b.get("type") for b in br], ["start", "stop"])
        self.assertTrue(all(b.get("color") == RED for b in br))
        words = [w.text for w in root.findall(".//words")]
        self.assertIn("unread", words)

    def test_every_kept_note_is_BLUE_and_counted_as_a_partial_bar_guess(self):
        xml, rep = _export(self.NOTES)
        notes = [n for n in ET.fromstring(xml).findall(".//note")
                 if n.find("pitch") is not None]
        self.assertEqual([n.get("color") for n in notes], [BLUE] * 3)
        by_rule = rep["guessed"]["by_rule"]
        self.assertEqual(by_rule.get("onset_from_partial_bar_prefix"), 1)
        self.assertEqual(by_rule.get("onset_from_partial_bar_suffix"), 2)

    def test_a_bar_that_adds_up_on_its_own_stays_plain_black(self):
        xml, rep = _export([("C4", QUARTER), ("D4", QUARTER),
                            ("E4", QUARTER), ("F4", QUARTER)])
        notes = ET.fromstring(xml).findall(".//note")
        self.assertTrue(all(n.get("color") is None for n in notes))
        self.assertEqual(rep["partial_bars"]["written"], 0)

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


class TestTheLilyPondTwin(unittest.TestCase):
    NOTES = TestPrefixAndSuffixAreKept.NOTES

    def _ly(self, mode="on"):
        with mock.patch.dict(os.environ, {"OMR_PARTIAL_BARS": mode}):
            return LY.to_lilypond(_one_staff_page(notes=self.NOTES,
                                                  meter=FOUR_FOUR))

    def test_the_gap_is_an_invisible_skip_under_a_red_unread_bracket(self):
        ly, rep = self._ly()
        bar = next(l for l in ly.splitlines() if "startTextSpan" in l)
        self.assertIn("s1*1/4\\startTextSpan", bar)
        self.assertIn('"unread"', bar)
        self.assertIn("#red", bar)
        self.assertNotRegex(bar, r"(?<![a-zA-Z\\])r[0-9]")   # no rest token
        self.assertEqual(rep["partial_bars"]["written"], 1)

    def test_every_kept_note_is_blue(self):
        ly, rep = self._ly()
        bar = next(l for l in ly.splitlines() if "startTextSpan" in l)
        self.assertEqual(bar.count("\\tweak color #guessedColor"), 3)
        self.assertEqual(rep["guessed"]["by_rule"][
            "onset_from_partial_bar_suffix"], 2)

    def test_off_keeps_no_note_of_the_held_bar(self):
        """Off, the bar is held whole: one bracket over the whole bar and not
        one kept note (on keeps three)."""
        ly, _rep = self._ly("off")
        self.assertIn("s1*1\\startTextSpan", ly)
        self.assertNotIn("\\tweak color", ly)
        self.assertNotRegex(ly, r"[a-g]'4")


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
        off, _ = _export(self.NOTES, mode="off")
        meas, rep = _export(self.NOTES, mode="measure")
        self.assertEqual(off, meas)
        self.assertEqual(rep["partial_bars"]["planned_bars"], 1)
        self.assertEqual(rep["partial_bars"]["written"], 0)

    def test_off_holds_the_bar_as_before(self):
        xml, rep = _export(self.NOTES, mode="off")
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


class TestHeldBarsUseTheBracketToo(unittest.TestCase):
    """Sean, 2026-10-14: *"use the bracket for held bars too"*. A bar held out
    whole is an empty red `unread` bracket over an invisible span of the bar,
    never a rest glyph; a bar we READ as silent keeps its whole rest."""
    SHORT = [("C4", QUARTER), ("E4", QUARTER)]     # held: no locatable gap

    def test_a_held_bar_is_a_red_bracket_and_no_rest(self):
        xml, rep = _export(self.SHORT)
        root = ET.fromstring(xml)
        m = root.find(".//measure")
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(list(m.iter("note")), [])
        self.assertEqual([b.get("type") for b in m.iter("bracket")],
                         ["start", "stop"])
        self.assertTrue(all(b.get("color") == RED for b in m.iter("bracket")))
        self.assertEqual([(x.text, x.get("color")) for x in m.iter("words")],
                         [("unread", RED)])
        div = int(root.find(".//divisions").text)
        self.assertEqual(int(m.find("forward/duration").text), 4 * div)

    def test_an_eventless_unread_bar_is_the_same_bracket(self):
        xml, rep = _export([("C4", None)])
        m = ET.fromstring(xml).find(".//measure")
        self.assertEqual(rep["written"]["empty_bars_padded"], 1)
        self.assertEqual(list(m.iter("note")), [])
        self.assertEqual(len(list(m.iter("bracket"))), 2)

    def test_the_counts_still_balance(self):
        _xml, rep = _export(self.SHORT)
        ubm = rep["unread_bar_marks"]
        self.assertEqual(ubm["written"], ubm["held_out_sum"] + ubm["unread"]
                         + ubm["partial"])

    def test_a_bar_read_as_silent_keeps_its_rest(self):
        # the READ whole-bar rest / tacet takes the legacy renderer directly
        from tools.omr import export as legacy
        lines = legacy._mxl_empty_measure(FOUR_FOUR, 8, None, "")
        self.assertTrue(any("<rest" in l for l in lines))
        self.assertNotIn("bracket", "".join(lines))

    def test_lilypond_held_bar_is_a_skip_under_a_red_bracket(self):
        with mock.patch.dict(os.environ, {"OMR_PARTIAL_BARS": "on"}):
            ly, rep = LY.to_lilypond(_one_staff_page(notes=self.SHORT,
                                                     meter=FOUR_FOUR))
        bar = next(l for l in ly.splitlines() if "startTextSpan" in l)
        self.assertIn("s1*1\\startTextSpan", bar)
        self.assertIn('"unread"', bar)
        self.assertNotRegex(bar, r"(?<![a-zA-Z\\])[rR][0-9]")
        self.assertNotIn("MultiMeasureRest", bar)
        ubm = rep["unread_bar_marks"]
        self.assertEqual(ubm["written"], ubm["held_out_sum"] + ubm["unread"]
                         + ubm["partial"])


class TestDefaultIsOn(unittest.TestCase):
    def test_unset_is_on_and_zero_is_off(self):
        env = {k: v for k, v in os.environ.items() if k != "OMR_PARTIAL_BARS"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(SX.partial_bars_mode(), "on")
        for v, want in (("0", "off"), ("off", "off"), ("measure", "measure")):
            with mock.patch.dict(os.environ, {"OMR_PARTIAL_BARS": v}):
                self.assertEqual(SX.partial_bars_mode(), want)


if __name__ == "__main__":
    unittest.main()
