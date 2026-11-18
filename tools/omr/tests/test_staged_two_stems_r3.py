"""ROADMAP 2.314 r3 (`OMR_TWO_STEMS_TWO_NOTES`): a two-voice bar is written with each voice's own printed marks and a `<forward>` for a stretch
where that voice prints nothing -- never a rest; and it still fails where a voice overflows, a value is not read, or a glyph of the bar was refused.
Shapes are the real bars of round 2's newly red set (Litolff P1 m20: a half beside quarter + quarter rest; Litolff P1 m22 a lower voice that stops)."""
import unittest
from unittest import mock

from tools.omr.staged import export as E

D = 8


def _rest(x, beats=1.0, cls="restQuarter", y=50):
    return {"kind": "rest", "x_position": x, "duration_beats": beats, "noteheads": [],
            "rest": {"glyph": "r%d" % x, "class": cls, "bbox": [x, y, 10, 10], "duration_beats": beats}}


def _chord(x, beats, guess=None):
    h = {"glyph": "n%d" % x, "duration_beats": beats, "bbox": [x, 40, 20, 14]}
    if guess:
        h["guess"] = guess
    return {"kind": "chord", "x_position": x, "noteheads": [h]}


class PlaceInTime(unittest.TestCase):
    def setUp(self):
        p = mock.patch.object(E, "_bar_quarters", lambda m: 2.0)       # 2/4
        p.start()
        self.addCleanup(p.stop)

    def place(self, v1, v2, unplaced=()):
        c = {}
        import collections
        c = collections.Counter()
        return E._place_voices_in_time([v1, v2], {"numerator": 2, "denominator": 4}, D, unplaced, c), c

    def kinds(self, st):
        return [(e["kind"], E._event_units(e, D)) for e in st]

    def test_a_half_beside_quarter_and_rest_needs_no_forward(self):
        q, h, r = _chord(100, 1.0), _chord(100, 2.0), _rest(300)
        out, _ = self.place([q, r], [h, r])
        self.assertEqual(self.kinds(out[0]), [("chord", 8), ("rest", 8)])
        self.assertEqual(self.kinds(out[1]), [("chord", 16)])

    def test_a_voice_that_stops_gets_a_trailing_forward_not_a_rest(self):
        a, b, c = _chord(100, 1.0), _chord(100, 1.0), _chord(300, 1.0)
        out, _ = self.place([a, c], [b])
        self.assertEqual(self.kinds(out[1]), [("chord", 8), ("forward", 8)])
        self.assertFalse(any(e["kind"] == "rest" for st in out for e in st))

    def test_a_voice_that_enters_late_gets_a_leading_gap(self):
        a, c, d = _chord(100, 1.0), _chord(300, 1.0), _chord(300, 1.0)
        out, _ = self.place([a, c], [d])
        self.assertEqual(self.kinds(out[1]), [("forward", 8), ("chord", 8)])
        self.assertTrue(E._bar_holds_out([], out, D, {"numerator": 2, "denominator": 4}) is None)

    def test_a_shared_rest_is_written_once_in_the_free_voice(self):
        h, q, r = _chord(100, 2.0), _chord(100, 1.0), _rest(300)
        out, _ = self.place([h, r], [q, r])
        self.assertEqual(sum(1 for st in out for e in st if e is r), 1)
        self.assertIs(out[1][-1], r)

    def test_an_overflowing_voice_still_fails(self):
        a, b, c = _chord(100, 2.0), _chord(100, 1.0), _chord(300, 1.0)
        out, cnt = self.place([a, c], [b])
        self.assertIsNone(out)

    def test_a_short_bar_still_fails(self):
        a, b = _chord(100, 1.0), _chord(100, 1.0)
        out, cnt = self.place([a], [b])
        self.assertIsNone(out)
        self.assertEqual(cnt["two_voice_bars_not_placed_the_fuller_voice_does_not_come_to_the_bar"], 1)

    def test_a_guessed_value_is_not_placed(self):
        a, b, c = _chord(100, 1.0, guess={"quantity": "duration"}), _chord(100, 1.0), _chord(300, 1.0)
        with mock.patch.object(E.Q, "DURATION", "duration"):
            out, _ = self.place([a, c], [b])
        self.assertIsNone(out)

    def test_a_refused_glyph_in_the_bar_is_not_placed(self):
        a, b, c = _chord(100, 1.0), _chord(100, 1.0), _chord(300, 1.0)
        out, cnt = self.place([a, c], [b], unplaced=[{"sub": "g"}])
        self.assertIsNone(out)

    def test_a_whole_rest_beside_notes_is_not_placed(self):
        a, b, c = _chord(100, 1.0), _chord(100, 1.0), _chord(300, 1.0)
        w = _rest(200, 4.0, "restWhole")
        out, _ = self.place([a, c, w], [b, w])
        self.assertIsNone(out)

    def test_forward_is_written_as_forward(self):
        lines, units = E._measure_events_xml([E._forward_event(8, 0.0, D)], D, __import__("collections").Counter(), voice=2)
        self.assertIn("<forward>", lines[0])
        self.assertIn("<voice>2</voice>", lines[0])
        self.assertEqual(units, 8)


if __name__ == "__main__":
    unittest.main()
