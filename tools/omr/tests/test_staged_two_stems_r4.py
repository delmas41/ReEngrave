"""ROADMAP 2.314 r4 (`OMR_TWO_STEMS_TWO_NOTES`): a bar the two-stems split cannot write with every voice adding up is written exactly as
flag OFF writes it (`one_chord.bar_declines`), so the flag never turns a written bar red. Shapes from round 3's still-red set (Litolff P1 m20:
"counted 2 / 1", a voice whose fuller stream does not come to the bar)."""
import collections
import os
import unittest
from unittest import mock

from tools.omr.staged import export as E
from tools.omr.staged import one_chord

D = 8


def _chord(x, beats, stem):
    h = {"glyph": "n%d%s" % (x, stem), "duration_beats": beats, "bbox": [x, 40 if stem == "a" else 60, 20, 14],
         "stem_id": stem, "stem_direction": "up"}
    return {"kind": "chord", "x_position": x, "noteheads": [h]}


class _Cell:
    def __init__(self, events):
        self.detections = [h for e in events for h in e["noteheads"]]
        self.unplaced = ()
        self._events = events


class BarDeclines(unittest.TestCase):
    def setUp(self):
        for p in (mock.patch.dict(os.environ, {one_chord.STEMS_APART_ENV: "1"}),
                  mock.patch.object(E, "_bar_quarters", lambda m: 2.0)):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(one_chord.bar_declines, False)

    def adds_up(self, events):
        cell = _Cell(events)
        with mock.patch.object(E, "_events", lambda c: c._events if c is not None else []), \
                mock.patch.object(E, "_voice_split", lambda rec, run, i, evs, why=None: E._stem_pair_streams(evs)):
            return E._two_stems_bar_adds_up(None, None, 0, cell, {"numerator": 2, "denominator": 4}, D)

    def test_a_split_that_adds_up_is_written_by_the_flag(self):
        # two quarters above, a half below: both voices come to 2/4
        self.assertTrue(self.adds_up([_chord(100, 1.0, "a"), _chord(100, 2.0, "b"), _chord(300, 1.0, "a")]))

    def test_a_split_short_bar_declines(self):
        # the real P1 m20 shape: "counted 2 / 1" -- a short bar the split cannot place is written as OFF writes it
        self.assertFalse(self.adds_up([_chord(100, 1.0, "a"), _chord(100, 1.0, "b")]))

    def test_the_decline_turns_the_flag_off_for_the_bar_only(self):
        self.assertTrue(one_chord.stems_apart_enabled())
        one_chord.bar_declines(True)
        self.assertFalse(one_chord.stems_apart_enabled())
        self.assertEqual(E._events_flag_on(None), [])
        self.assertFalse(one_chord.stems_apart_enabled())     # restored after the counter's question
        one_chord.bar_declines(False)
        self.assertTrue(one_chord.stems_apart_enabled())

    def test_flag_off_never_declines(self):
        with mock.patch.dict(os.environ, {one_chord.STEMS_APART_ENV: "0"}):
            self.assertTrue(self.adds_up([_chord(100, 1.0, "a"), _chord(100, 1.0, "b")]))


if __name__ == "__main__":
    unittest.main()
