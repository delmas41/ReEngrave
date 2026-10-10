"""ROADMAP 3.5: every bar the reader could not read is VISIBLY marked in the
MusicXML and in the LilyPond text, not only in a withheld `measure="yes"`
that no notation program shows.

CLAUDE.md §1's definition of done: "every bar the reader could not read is
MARKED as unread and never invented"; rule 8: "a fallback never converts
'cannot tell' into an answer ... not into a whole rest that means silence."
Before this branch, a bar we read NOTHING in (`empty_bars_padded`) and a bar
roadmap 2.8 held out for not summing to the meter (`bars_held_out_sum`) both
left the file as an ORDINARY whole-measure rest — indistinguishable, to a
notation program, from a bar we genuinely read AS silence (a DECIDED
whole-bar rest, `TestTheControlIsUnmarked` below).

⚠️ RUN RED AGAINST THE UNREPAIRED TREE FIRST — `origin/main` at `fee4d5a0`,
before this branch's `export.py` / `lilypond.py` changes. Every test below
either KeyErrors on `rep["unread_bar_marks"]` (a key the old exporter does
not write at all — MusicXML and, before this branch, LilyPond too, since
`staged.lilypond` never called `_bar_holds_out` at all) or finds no `color`
attribute / no marker word in the output. `TestTheControlIsUnmarked` is the
ONE class that could pass by accident on the unrepaired tree (a plain,
uncoloured rest is exactly what it already wrote) — its siblings are what
make the positive claim, and CLAUDE.md §6b's "a control must be able to
fail" is why it is here at all rather than assumed.

⚠️ No test here reads module source text (CLAUDE.md §6c) — every assertion
is against a rendered MusicXML/LilyPond STRING, never `inspect.getsource`.
"""

import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.staged import lilypond as staged_lily
from tools.omr.tests.test_staged_bar_sum_holdout import TWO_FOUR, _bar
from tools.omr.tests.test_staged_export import QUARTER, _add_rest, _one_staff_page

UNREAD = SX.UNREAD_BAR_MARK_WORDS[SX.UNREAD_BAR_MARK_REASON_UNREAD]
HELD_SUM = SX.UNREAD_BAR_MARK_WORDS[SX._BAR_SUM_REFUSAL]


def _note(xml):
    return ET.fromstring(xml).find(".//note")


def _directions(xml):
    return ET.fromstring(xml).findall(".//direction")


class TestAnUnreadBarIsMarked(unittest.TestCase):
    """(a) A bar with no events -> a red rest plus the word 'unread'."""

    def _page(self):
        return _one_staff_page(notes=[], meter=TWO_FOUR, n_measures=1)

    def test_the_note_is_coloured_and_counted(self):
        xml, rep = SX.to_musicxml(self._page())
        note = _note(xml)
        self.assertEqual(note.get("color"), SX.UNREAD_BAR_MARK_COLOR)
        self.assertEqual(rep["unread_bar_marks"]["unread"], 1)
        self.assertEqual(rep["unread_bar_marks"]["written"], 1)
        # ⚠️ the withheld `measure="yes"` marker still stands beside the new
        # one -- this roadmap item ADDS a marker, it does not replace 2.8's.
        self.assertEqual(note.find("rest").get("measure"), "yes")

    def test_the_direction_names_it_unread(self):
        xml, _rep = SX.to_musicxml(self._page())
        dirs = _directions(xml)
        self.assertEqual(len(dirs), 1)
        self.assertEqual(dirs[0].get("placement"), "above")
        self.assertEqual(dirs[0].find("./direction-type/words").text, UNREAD)

    def test_lilypond_carries_the_same_colour_and_word(self):
        text, rep = staged_lily.to_lilypond(self._page())
        self.assertIn("\\override Rest.color = #red", text)
        self.assertIn(UNREAD, text)
        self.assertEqual(rep["unread_bar_marks"]["unread"], 1)
        self.assertEqual(rep["unread_bar_marks"]["written"], 1)


class TestAHeldOutBarIsMarked(unittest.TestCase):
    """(b) A bar roadmap 2.8 holds out (its durations do not sum to the
    meter in force) -> a red rest plus the word 'unread' (Sean 2026-09-28: one word for every reason)."""

    def _page(self):
        return _bar([("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)])

    def test_the_note_is_coloured_and_still_held_out(self):
        xml, rep = SX.to_musicxml(self._page())
        note = _note(xml)
        self.assertEqual(note.get("color"), SX.UNREAD_BAR_MARK_COLOR)
        self.assertEqual(rep["unread_bar_marks"]["held_out_sum"], 1)
        # ⚠️ marking is cosmetic -- 2.8's own accounting is unchanged by it.
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)
        self.assertEqual(rep["notes_not_written"]["bar_does_not_add_up"], 3)

    def test_the_direction_names_the_reason(self):
        xml, _rep = SX.to_musicxml(self._page())
        dirs = _directions(xml)
        self.assertEqual(len(dirs), 1)
        self.assertEqual(dirs[0].get("placement"), "above")
        self.assertEqual(dirs[0].find("./direction-type/words").text, HELD_SUM)

    def test_lilypond_carries_the_same_colour_and_word(self):
        text, rep = staged_lily.to_lilypond(self._page())
        self.assertIn("\\override Rest.color = #red", text)
        self.assertIn(HELD_SUM, text)
        self.assertEqual(rep["unread_bar_marks"]["held_out_sum"], 1)
        self.assertEqual(rep["bars_held_out_sum"]["bars"], 1)


class TestTheControlIsUnmarked(unittest.TestCase):
    """(c) CONTROL: a bar whose one event is a DECIDED measure rest -> a
    plain rest, no marker. Sean's convention (CLAUDE.md §10): a whole rest
    means the BAR, and this reader READ it -- it must stay black."""

    def _page(self):
        page = _bar([])
        # ⚠️ ROADMAP 2.79: 2.0 beats, the length of `_bar`'s 2/4 -- a measure
        # rest IS the written bar. It was written 4.0 (a whole rest in a 2/4
        # bar), which EXPORT now holds out as a bar that does not add up.
        _add_rest(page, 5, "restWhole",
                  {"beats": 2.0, "written": 2.0, "dots": 0, "is_rest": True,
                   "measure_rest": True})
        return page

    def test_the_note_carries_no_colour(self):
        xml, rep = SX.to_musicxml(self._page())
        note = _note(xml)
        self.assertIsNone(note.get("color"))
        self.assertEqual(rep["unread_bar_marks"]["written"], 0)
        self.assertEqual(rep["written"]["measure_rests_read"], 1)

    def test_no_marker_direction_is_written(self):
        xml, _rep = SX.to_musicxml(self._page())
        self.assertEqual(_directions(xml), [])

    def test_lilypond_carries_no_override(self):
        text, rep = staged_lily.to_lilypond(self._page())
        self.assertNotIn("\\override Rest.color", text)
        self.assertNotIn("\\override MultiMeasureRest.color", text)
        self.assertEqual(rep["unread_bar_marks"]["written"], 0)


class TestTheAccountingStillBalances(unittest.TestCase):
    """(d) One document, BOTH reasons at once: `to_musicxml`/`to_lilypond`
    would RAISE `Unbalanced` if a bar were refused without being marked (or
    marked without being refused), and `status_census["unaccounted"]` stays
    empty regardless."""

    def _page(self):
        # cell 0: three quarters in 2/4 -- held out by sum.
        # cell 1 (n_measures=2, no glyphs there): a bar we read nothing in.
        return _one_staff_page(
            notes=[("C4", QUARTER), ("D4", QUARTER), ("E4", QUARTER)],
            meter=TWO_FOUR, n_measures=2)

    def test_musicxml(self):
        xml, rep = SX.to_musicxml(self._page())   # raises Unbalanced on fail
        marks = rep["unread_bar_marks"]
        self.assertEqual(marks["unread"], 1)
        self.assertEqual(marks["held_out_sum"], 1)
        self.assertEqual(marks["written"], 2)
        self.assertEqual(len(_directions(xml)), 2)
        self.assertEqual(rep["status_census"]["unaccounted"], [])
        self.assertTrue(rep["balance"]["balanced"])

    def test_lilypond(self):
        _text, rep = staged_lily.to_lilypond(self._page())  # raises on fail
        marks = rep["unread_bar_marks"]
        self.assertEqual(marks["unread"], 1)
        self.assertEqual(marks["held_out_sum"], 1)
        self.assertEqual(marks["written"], 2)


if __name__ == "__main__":
    unittest.main()
