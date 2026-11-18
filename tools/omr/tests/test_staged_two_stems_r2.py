"""ROADMAP 2.314 r2 (`OMR_TWO_STEMS_TWO_NOTES`): (A) a head inside a dynamic letter's box with a thin ink disc is the letter's curl; (B) a rest printed once belongs to the
voice that is silent there. Numbers are the real ones (Litolff 20261029 slices: curls 0.903 / 0.964 / 0.975 inside the box, real heads 1.22-1.35; the real pairs of the round-1
look: a half beside a quarter + a quarter rest in 2/4)."""
import os
import unittest
from unittest import mock

from tools.omr.staged import export as E
from tools.omr.staged.adjudicators import notehead_precision as NP

FLAG = "OMR_TWO_STEMS_TWO_NOTES"


class LetterCurl(unittest.TestCase):
    def test_off_keeps_the_old_cut(self):
        with mock.patch.dict(os.environ, {FLAG: "0"}):
            self.assertEqual(NP.stroke_disc_cut(1.0), NP.DYNAMIC_LETTER_STROKE_DISC_SPACES)

    def test_on_wholly_inside_uses_the_higher_cut(self):
        with mock.patch.dict(os.environ, {FLAG: "1"}):
            cut = NP.stroke_disc_cut(1.0)
            for curl in (0.903, 0.964, 0.975):
                self.assertLess(curl, cut)
            for real in (1.224, 1.294, 1.345):
                self.assertGreater(real, cut)
            self.assertEqual(NP.stroke_disc_cut(0.3), NP.DYNAMIC_LETTER_STROKE_DISC_SPACES)   # partly inside: never refused by the new cut


def _rest(x):
    return {"kind": "rest", "x_position": x, "duration_beats": 1.0, "duration_type": "quarter", "dots": 0, "rest": {"glyph": "g%d" % x}}


def _chord(x, beats):
    return {"kind": "chord", "x_position": x, "duration_beats": beats, "duration_type": "q", "dots": 0, "noteheads": [{"glyph": "n%d" % x}]}


class RestInTheSilentVoice(unittest.TestCase):
    def setUp(self):
        self.units = mock.patch.object(E, "_event_units", lambda ev, d: int(ev["duration_beats"] * d))
        self.meter = mock.patch.object(E, "_bar_quarters", lambda m: 2.0)
        self.units.start(); self.meter.start()
        self.addCleanup(self.units.stop); self.addCleanup(self.meter.stop)

    def test_a_full_voice_gets_no_rest(self):
        q, h, r = _chord(100, 1.0), _chord(100, 2.0), _rest(300)
        out = E._rests_to_the_silent_voice([[q, r], [h, r]], {}, 8, {})
        self.assertEqual([e["kind"] for e in out[0]], ["chord", "rest"])
        self.assertEqual([e["kind"] for e in out[1]], ["chord"])

    def test_a_rest_printed_once_is_written_once(self):
        a, b, r = _chord(100, 1.0), _chord(100, 1.0), _rest(300)
        out = E._rests_to_the_silent_voice([[a, r], [b, r]], {}, 8, {})
        self.assertEqual(sum(1 for st in out for e in st if e is r), 1)
        self.assertIs(out[0][1], r)

    def test_nothing_fits_still_written_once(self):
        a, b, r = _chord(100, 2.0), _chord(100, 2.0), _rest(300)
        out = E._rests_to_the_silent_voice([[a, r], [b, r]], {}, 8, {})
        self.assertEqual(sum(1 for st in out for e in st if e is r), 1)

    def test_the_lower_voice_takes_it_when_only_it_has_room(self):
        a, b, r = _chord(100, 2.0), _chord(100, 1.0), _rest(300)
        out = E._rests_to_the_silent_voice([[a, r], [b, r]], {}, 8, {})
        self.assertEqual([e["kind"] for e in out[0]], ["chord"])
        self.assertIs(out[1][1], r)


if __name__ == "__main__":
    unittest.main()
