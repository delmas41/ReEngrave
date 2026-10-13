"""ROADMAP 2.89. EXPORT does not mode-vote a chord's value.

`voicing.group_chords_in_measure` gives a chord the MODE of its heads' values.
Where the heads disagree that is an argmax over "cannot tell" (rule 8). The
exporter now refuses every member of such a chord, counted under
`chord_value_undecided`, and the accounting equality still holds.
"""
import unittest
import xml.etree.ElementTree as ET

from tools.omr.staged import export as SX
from tools.omr.tests.test_staged_export import _one_staff_page, QUARTER

HALF = {"beats": 2.0, "written": 2.0, "dots": 0}
WHOLE = {"beats": 4.0, "written": 4.0, "dots": 0}


def _chord_page(durs):
    """One chord: every head at the same x, stacked in y."""
    page = _one_staff_page(
        notes=[(p, d) for p, d in zip(("C4", "E4", "G4", "B4"), durs)])
    k = 0
    for o in page["record"]["observations"]:
        if o["quantity"] == "glyph_box":
            o["value"][1] = 100
            o["value"][2] = 50 + 12 * k
            k += 1
    return page


def _pitches(xml):
    return [n.find("pitch/step").text
            for n in ET.fromstring(xml).findall(".//note")
            if n.find("pitch") is not None]


class TestAChordIsNotVoted(unittest.TestCase):
    def test_a_chord_whose_heads_disagree_is_refused_whole(self):
        xml, rep = SX.to_musicxml(_chord_page([HALF, HALF, WHOLE]))
        self.assertEqual(rep["notes_not_written"]["chord_value_undecided"], 3)
        self.assertEqual(_pitches(xml), [])
        self.assertTrue(rep["balance"]["balanced"])
        self.assertEqual(rep["balance"]["events_not_written"], 3)

    def test_a_two_against_one_is_still_a_vote_and_is_refused(self):
        _xml, rep = SX.to_musicxml(_chord_page([QUARTER, QUARTER, HALF]))
        self.assertEqual(rep["notes_not_written"]["chord_value_undecided"], 3)

    def test_POSITIVE_CONTROL_a_chord_that_agrees_is_written_with_its_value(self):
        xml, rep = SX.to_musicxml(_chord_page([HALF, HALF, HALF]))
        self.assertNotIn("chord_value_undecided", rep["notes_not_written"])
        self.assertEqual(sorted(_pitches(xml)), ["C", "E", "G"])
        self.assertEqual(
            {t.text for t in ET.fromstring(xml).findall(".//note/type")},
            {"half"})
        self.assertTrue(rep["balance"]["balanced"])

    def test_POSITIVE_CONTROL_separate_notes_of_different_value_are_untouched(self):
        xml, rep = SX.to_musicxml(_one_staff_page(
            notes=[("C4", HALF), ("E4", QUARTER)]))
        self.assertNotIn("chord_value_undecided", rep["notes_not_written"])
        self.assertEqual(len(_pitches(xml)), 2)

    def test_the_bar_it_leaves_is_padded_unread_never_a_read_rest(self):
        _xml, rep = SX.to_musicxml(_chord_page([HALF, HALF, WHOLE]))
        self.assertEqual(rep["written"].get("empty_bars_padded"), 1)
        self.assertEqual(rep["written"].get("measure_rests_read", 0), 0)


if __name__ == "__main__":
    unittest.main()
