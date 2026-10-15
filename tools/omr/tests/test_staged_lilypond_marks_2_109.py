"""ROADMAP 2.109 -- the STAGED LilyPond writer carries the marks the MusicXML
carries: articulations (staccato -., staccatissimo -!, tenuto --, ...) and
dynamics (READ plain, GUESSED a blue `dyn.`), and counts every one it cannot.

STAGED only. RED on the tree before the change: a staccato / dynamic present
in the MusicXML was missing from the `.ly` (`dynamics_not_renderable` counted
the dynamic, the dot-role staccato was not even counted).
"""

import re
import shutil
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as LY
from tools.omr.staged.record import Q
from tools.omr.tests.test_dynamic_guess_2_107 import _narrowed
from tools.omr.tests.test_staged_dots_articulations_2_124 import _with_staccato
from tools.omr.tests.test_staged_export import (
    QUARTER,
    _obs,
    _one_staff_page,
    _vrd,
)
from tools.omr.tests.test_staged_guess_flag_2_103 import _guess
from tools.omr.tests.test_staged_lilypond import _compile

CELL = "cell/0/0/0/0"
_HAS_LILYPOND = shutil.which("lilypond") is not None
_TOKEN = re.compile(r"-[.!>^-]")


def _page(n=2):
    return _one_staff_page(notes=[("C4", QUARTER), ("D4", QUARTER)][:n])


def _add_articulation(page, name, *, owner_gi=0, gi=800):
    """A decided articulation mark owned by head `owner_gi` (the shape gather
    emits: a mark observation plus an owner verdict naming the kind)."""
    sub = f"glyph/0/0/0/0/{gi}"
    page["record"]["observations"].append(
        _obs(gi, sub, Q.ARTICULATION_MARK, name, x0=0, x1=10, y0=0, y1=10))
    v = _vrd(gi, sub, Q.ARTICULATION_OWNER, f"glyph/0/0/0/0/{owner_gi}",
             reason="stem_side")
    v["detail"] = {"articulation": name}
    page["record"]["verdicts"].append(v)
    return page


def _add_read_dynamic(page, word="sf"):
    v = _vrd(7000, CELL, Q.DYNAMIC, [word], reason="spelled")
    v["decider"] = "adjudicate_dynamic"
    v["detail"] = {"words": [{"text": word, "spelled": True, "x_page": 120.0}]}
    page["record"]["verdicts"].append(v)
    return page


def _add_guessed_dynamic(page):
    page["record"]["verdicts"].append(
        _narrowed({"sf": 0.05, "mf": 0.05, "rf": 0.05}))
    return page


def _xml_marks(xml):
    root = ET.fromstring(xml)
    return [e.tag for a in root.iter("articulations") for e in a]


class TestArticulationsReachTheLilyPondFile(unittest.TestCase):
    def test_a_staccato_in_the_musicxml_is_in_the_ly_RED(self):
        page = _with_staccato(_page())
        xml, _ = SX.to_musicxml(page)
        self.assertEqual(_xml_marks(xml), ["staccato"])
        text, rep = LY.to_lilypond(page)
        self.assertEqual(len(_TOKEN.findall(text)), 1, text)
        self.assertIn("c'4-.", text)
        led = rep["marks_ledger"]["articulations"]
        self.assertEqual((led["in_musicxml"], led["written"]), (1, 1))

    def test_staccatissimo_and_tenuto_are_written_RED(self):
        page = _add_articulation(_add_articulation(
            _page(), "staccatissimo", owner_gi=0, gi=800),
            "tenuto", owner_gi=1, gi=801)
        xml, _ = SX.to_musicxml(page)
        self.assertEqual(sorted(_xml_marks(xml)), ["staccatissimo", "tenuto"])
        text, rep = LY.to_lilypond(page)
        self.assertIn("c'4-!", text)
        self.assertIn("d'4--", text)
        self.assertEqual(rep["marks_ledger"]["articulations"]["written"], 2)

    def test_a_mark_on_a_guessed_note_is_blue(self):
        page = _guess(_with_staccato(_page()), 0,
                      decider="infer:collapse_duration_by_column", value=QUARTER)
        text, rep = LY.to_lilypond(page)
        self.assertEqual(rep["guessed"]["notes"], 1)
        self.assertIn("-\\tweak color #guessedColor -.", text)

    def test_a_read_note_mark_is_plain_CONTROL(self):
        text, _ = LY.to_lilypond(_with_staccato(_page()))
        self.assertNotIn("guessedColor", text)


class TestDynamics(unittest.TestCase):
    def test_a_read_dynamic_is_written_plain_RED(self):
        page = _add_read_dynamic(_page(), "sf")
        text, rep = LY.to_lilypond(page)
        self.assertIn("c'4\\sf", text)
        self.assertNotIn("guessedColor", text)
        led = rep["marks_ledger"]["dynamics"]
        self.assertEqual((led["in_musicxml"], led["written"]), (1, 1))
        self.assertEqual(rep["lilypond"]["dynamics_not_renderable"], 0)

    def test_a_guessed_dynamic_is_a_blue_dyn_and_never_a_letter_RED(self):
        page = _add_guessed_dynamic(_page())
        xml, _ = SX.to_musicxml(page)
        self.assertIn(">dyn.<", xml)
        text, rep = LY.to_lilypond(page)
        self.assertIn('\\with-color #guessedColor \\italic "dyn."', text)
        self.assertIn("guessedColor = #", text)
        for letter in ("\\sf", "\\mf", "\\rf", "\\dynamic"):
            self.assertNotIn(letter, text)
        self.assertEqual(rep["guessed"]["dynamics"], 1)

    def test_a_dynamic_and_a_hairpin_on_one_note_keep_the_dynamic_first(self):
        page = _add_read_dynamic(_page(), "p")
        text, _ = LY.to_lilypond(page)
        self.assertNotIn("\\<\\p", text)

    @unittest.skipUnless(_HAS_LILYPOND, "lilypond not installed")
    def test_the_file_compiles_without_a_warning(self):
        page = _add_guessed_dynamic(_add_read_dynamic(
            _add_articulation(_with_staccato(_page()), "tenuto", owner_gi=1)))
        text, _ = LY.to_lilypond(page)
        out = _compile(text)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertNotIn("warning", out.stderr.lower(), out.stderr)


class TestTwoDynamicsInOneBar(unittest.TestCase):
    def _page2(self):
        page = _page()
        v = _vrd(7000, CELL, Q.DYNAMIC, ["p", "f"], reason="spelled")
        v["decider"] = "adjudicate_dynamic"
        v["detail"] = {"words": [{"text": "p", "spelled": True, "x_page": 10.0},
                                 {"text": "f", "spelled": True, "x_page": 90.0}]}
        page["record"]["verdicts"].append(v)
        return page

    def test_the_second_is_a_markup_not_a_conflicting_script(self):
        text, rep = LY.to_lilypond(self._page2())
        self.assertIn("c'4\\p-\\markup { \\dynamic f }", text)
        self.assertEqual(rep["marks_ledger"]["dynamics"]["written"], 2)

    @unittest.skipUnless(_HAS_LILYPOND, "lilypond not installed")
    def test_no_dynamic_is_discarded_by_lilypond(self):
        text, _ = LY.to_lilypond(self._page2())
        self.assertNotIn("absolute-dynamic-event", _compile(text).stderr)


class TestNothingIsInvented(unittest.TestCase):
    def test_no_marks_adds_nothing_CONTROL(self):
        text, rep = LY.to_lilypond(_page())
        self.assertEqual(_TOKEN.findall(text), [])
        self.assertNotIn("\\markup", text)
        self.assertNotIn("guessedColor", text)
        for fam in ("articulations", "dynamics"):
            led = rep["marks_ledger"][fam]
            self.assertEqual((led["in_musicxml"], led["written"], led["dropped"]),
                             (0, 0, {}))

    def test_an_absent_dynamic_adds_nothing(self):
        """A DYNAMIC quantity the record never filed is not a dynamic."""
        text, rep = LY.to_lilypond(_page())
        self.assertNotIn("\\p", text)
        self.assertEqual(rep["marks_ledger"]["dynamics"]["in_musicxml"], 0)

    def test_a_dynamic_in_a_bar_with_no_notes_is_counted_dropped_with_a_reason(self):
        page = _add_read_dynamic(_one_staff_page(notes=[], n_measures=1), "f")
        text, rep = LY.to_lilypond(page)
        self.assertNotIn("\\f", text)
        led = rep["marks_ledger"]["dynamics"]
        self.assertEqual(led["written"], 0)
        self.assertEqual(sum(led["dropped"].values()), 1)
        self.assertEqual(led["in_musicxml"], 1)
        self.assertTrue(all(isinstance(k, str) and k for k in led["dropped"]))

    def test_an_unspellable_dynamic_is_dropped_and_counted_not_written(self):
        page = _add_read_dynamic(_page(), "dolce")
        text, rep = LY.to_lilypond(page)
        self.assertNotIn("dolce", text)
        led = rep["marks_ledger"]["dynamics"]
        self.assertEqual(led["dropped"], {"dynamic_text_not_spellable": 1})

    def test_the_ledger_raises_when_it_does_not_balance(self):
        led = {"in_musicxml": 2, "written": 1, "dropped": {}}
        with self.assertRaises(SX.Unbalanced):
            LY._assert_ledger("dynamics", led)


if __name__ == "__main__":
    unittest.main()
