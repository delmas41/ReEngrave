"""ROADMAP 2.257 round 2 -- the whole rest on its own staff stream (OMR_WHOLE_REST_OWN_STAFF).

Sean 2026-11-03, 12 blind tiles: a displaced whole rest beside notes that fill the bar by themselves is "a whole
note rest, second voice" (10/10), a lone whole rest is "its only voice" / "only voice" (2/2).

Two stages, two functions: ADJUDICATE `rhythm._rest_own_voice_split` (through `adjudicate_voices`) names the voice;
EXPORT `export._size_rest_alone_in_its_voice` sizes the lone rest as the bar. Each test below has its mirror that must
fail to fire, so the rule cannot pass by splitting everything.
"""
from __future__ import annotations

import collections
import os
import unittest

from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import export as SX
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_voices import (
    CELL, _duration, _head, _meter, _run, _staff_geometry, _stem, _v)

ENV = "OMR_WHOLE_REST_OWN_STAFF"


class _Env(unittest.TestCase):
    value = "1"

    def setUp(self):
        self._old = os.environ.get(ENV)
        os.environ[ENV] = self.value

    def tearDown(self):
        if self._old is None:
            os.environ.pop(ENV, None)
        else:
            os.environ[ENV] = self._old


def _whole_rest(log, gi, x, center_y, *, hang=False):
    g = R.glyph(0, 0, 0, 0, gi)
    w, h = 40.0, 10.0
    log.observe(g, Q.REST, "restWhole", reader=READERS.DETECTOR, frame="cell:0", score=0.9)
    log.observe(g, Q.GLYPH_BOX, ("restWhole", x, center_y - h / 2, w, h), reader=READERS.DETECTOR,
                frame="cell:0", score=0.9, category="rest",
                bbox_page_px=[x, center_y - h / 2, x + w, center_y + h / 2])
    _v(log, g, Q.DURATION, Outcome.DECIDED, {"beats": 4.0, "written": 4.0, "dots": 0, "is_rest": True},
       reason="rest_hangs_from_own_line" if hang else "rest_class", detail={"rest": "restWhole"})
    return g


def _bar(quarters_in_other_voice, *, rest_y=60.0, stems="up", meter=(4, 4), hang=False):
    """`quarters_in_other_voice` quarter heads (one event each, spread out) and one whole rest at `rest_y` (staff
    lines y=0..80, middle y=40: 60 is the lower voice's rest, 20 the upper's)."""
    log = Log()
    _staff_geometry(log)
    _meter(log, *meter)
    for i in range(quarters_in_other_voice):
        x = 40 + 60 * i
        g = _head(log, i, x)
        _stem(log, x + (18 if stems == "up" else 0), -60 if stems == "up" else 12, h=64)
        _duration(log, g, 1.0)
    _whole_rest(log, 20, 500, rest_y, hang=hang)
    return log


class TestRestOwnVoiceSplit(_Env):
    def _voices(self, log):
        return _run(log, Q.STEM_DIRECTION, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)

    def test_displaced_whole_rest_beside_a_full_one_way_voice_is_its_own_voice(self):
        v = self._voices(_bar(4, rest_y=60.0, stems="up"))
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(v.reason, "one_voice_plus_displaced_whole_rest")
        self.assertEqual(v.value["n_voices"], 2)
        self.assertEqual(v.value["rest_own_voice"], [20])
        self.assertIn(20, v.value["voices"][1])           # a lower rest is the lower voice's
        self.assertNotIn(20, v.value["voices"][0])

    def test_an_upper_rest_beside_down_stems_is_the_upper_voice(self):
        v = self._voices(_bar(4, rest_y=20.0, stems="down"))
        self.assertEqual(v.reason, "one_voice_plus_displaced_whole_rest")
        self.assertIn(20, v.value["voices"][0])

    def test_the_other_voice_short_of_the_meter_leaves_the_bar_as_it_was(self):
        v = self._voices(_bar(3, rest_y=60.0, stems="up"))
        self.assertNotEqual(v.reason, "one_voice_plus_displaced_whole_rest")
        self.assertNotIn("rest_own_voice", v.value or {})

    def test_a_clashing_stem_leaves_the_bar_as_it_was(self):
        # a LOWER rest wants the notes' stems up; stems down clash with it
        v = self._voices(_bar(4, rest_y=60.0, stems="down"))
        self.assertNotEqual(v.reason, "one_voice_plus_displaced_whole_rest")

    def test_a_lone_whole_rest_is_not_split(self):
        v = self._voices(_bar(0, rest_y=60.0))
        self.assertNotEqual(v.reason, "one_voice_plus_displaced_whole_rest")


class TestRestOwnVoiceSplitFlagOff(_Env):
    value = "0"

    def test_flag_off_the_bar_is_never_split(self):
        v = _run(_bar(4, rest_y=60.0, stems="up"), Q.STEM_DIRECTION, Q.EVENT, Q.VOICES).verdict(Q.VOICES, CELL)
        self.assertNotEqual(v.reason, "one_voice_plus_displaced_whole_rest")


def _chord(beats=1.0, stem="up"):
    return {"kind": "chord", "dots": 0, "stem_direction": stem,
            "noteheads": [{"pitch": "C5", "duration_beats": beats}], "_glyphs": set()}


def _hang_rest(glyph="glyph/0/0/0/0/20"):
    return {"kind": "rest", "dots": 0, "duration_beats": 4.0, "beats": 4.0,
            "rest": {"class": "restWhole", "glyph": glyph, "duration_beats": 4.0}}


class _FakeRec:
    def __init__(self, reason="rest_hangs_from_own_line"):
        self.reason = reason

    def verdict(self, q, key):
        if q == Q.DURATION:
            return {"outcome": "decided", "reason": self.reason}
        return None


class TestSizeRestAloneInItsVoice(_Env):
    JUDGED = {"numerator": 4, "denominator": 4}

    def _size(self, events, judged="default", rec=None):
        judged = self.JUDGED if judged == "default" else judged
        counters = collections.Counter()
        return SX._own_voice_from_written_events(rec or _FakeRec(), events, judged, counters, 4), counters

    def test_the_rest_beside_a_full_one_way_voice_is_sized_as_the_bar_in_its_own_stream(self):
        events = [_chord(), _chord(), _chord(), _chord(), _hang_rest()]
        (new_events, streams), counters = self._size(events)
        self.assertIsNotNone(streams)
        self.assertEqual(len(streams), 2)
        self.assertEqual(len(streams[1]), 1)
        self.assertTrue(streams[1][0]["rest"]["measure_rest"])
        self.assertEqual(counters["measure_rests_sized_alone_in_their_voice"], 1)

    def test_the_other_voice_short_of_the_meter_is_unchanged(self):
        events = [_chord(), _chord(), _chord(), _hang_rest()]
        (new_events, streams), _ = self._size(events)
        self.assertIsNone(streams)
        self.assertIs(new_events, events)

    def test_a_clashing_stem_is_unchanged(self):
        events = [_chord(stem="down"), _chord(), _chord(), _chord(), _hang_rest()]
        (_, streams), _ = self._size(events)
        self.assertIsNone(streams)

    def test_a_lone_whole_rest_is_unchanged_here(self):
        (_, streams), _ = self._size([_hang_rest()])
        self.assertIsNone(streams)

    def test_no_meter_in_force_is_unchanged(self):
        events = [_chord(), _chord(), _chord(), _chord(), _hang_rest()]
        (_, streams), _ = self._size(events, judged=None)
        self.assertIsNone(streams)

    def test_a_rest_not_read_by_the_hang_test_is_unchanged(self):
        events = [_chord(), _chord(), _chord(), _chord(), _hang_rest()]
        (_, streams), _ = self._size(events, rec=_FakeRec("rest_class"))
        self.assertIsNone(streams)


class TestSizeRestFlagOff(_Env):
    value = "0"

    def test_flag_off_the_entry_point_changes_nothing(self):
        events = [_chord(), _chord(), _chord(), _chord(), _hang_rest()]
        out = SX._size_rest_alone_in_its_voice(_FakeRec(), None, 0, events, None, {"numerator": 4, "denominator": 4},
                                                collections.Counter(), 4)
        self.assertEqual(out, (events, None))


class TestDefaultOn(unittest.TestCase):
    def test_default_on_deny_list_in_both_modules(self):
        old = os.environ.pop(ENV, None)
        try:
            self.assertEqual(rhythm.WHOLE_REST_OWN_STAFF_ENV, ENV)
            self.assertEqual(SX.WHOLE_REST_OWN_STAFF_ENV, ENV)
            self.assertTrue(rhythm._whole_rest_own_staff_on() and SX._whole_rest_own_staff_on())
            for v in ("0", "false", "no", "off", "OFF"):
                os.environ[ENV] = v
                self.assertFalse(rhythm._whole_rest_own_staff_on() or SX._whole_rest_own_staff_on(), v)
            os.environ[ENV] = "1"
            self.assertTrue(rhythm._whole_rest_own_staff_on() and SX._whole_rest_own_staff_on())
        finally:
            if old is None:
                os.environ.pop(ENV, None)
            else:
                os.environ[ENV] = old


if __name__ == "__main__":
    unittest.main()
