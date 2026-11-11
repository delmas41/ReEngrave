"""ROADMAP 2.300 -- ONE CHORD IS ONE EVENT (flag `OMR_ONE_CHORD_ONE_EVENT`, default ON).

Controls are cut from the REAL gather rows of Sean's 2.291 red-bar tiles (`fixtures/one_chord_2_300/*.json`, made by
`benchmarks/one-chord-one-event-2026-11/cut_fixture.py`; rows exactly as saved, nothing edited):
  tile 7  (Litolff p2 s1 st4 c14)  two half notes a second apart, one stem: OFF two events (1.0 + 2.0, 3.0 in a 2/4 bar), ON one chord (2.0)
  tile 10 (Litolff p2 s0 st2 c3)   two quarters on one stem: ONE chord OFF already; its bar is red for a false 16th rest (the sharp), NOT
                                    a chord split -- the flag must not touch it
  tile 6  (Litolff p2 s1 st6 c9)   quarter + quarter rest, ONE voice: no voice gained
  tile 11 (Brahms p4 s1 st2 c0)    a chord first, one voice in the print: the chord is ONE event OFF already; the two voices come from heads
                                    owned by another staff (not this lane's); the flag must not change them
  tile 12 (Brahms p4 s1 st13 c7)   an eighth then rests: unchanged
  tile 1  (Brahms p0 s0 st10 c1)   one voice: unchanged
  MIRROR  (Brahms p0 s0 st11 c0)   a real two-voice onset (up and down stems at one onset, different pitches), UNJUDGED (picked by the rule
                                    "first plain bar on Brahms p0/p4 with an up-stem and a down-stem chord at one x"): two events, two voices, unchanged
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import unittest
from unittest import mock

from tools.omr import voicing
from tools.omr.staged import export as E
from tools.omr.staged import one_chord as OC
from tools.omr.staged.review import rerun as RR

FX = pathlib.Path(__file__).parent / "fixtures" / "one_chord_2_300"
FLAG = OC.ENV
_CACHE = {}
_XML = {}


def _replay(name: str, on: bool):
    """{(page, system, staff, cell): (events, streams)} for every bar of the fixture, flag ON or OFF (same rows, same stages)."""
    key = (name, on)
    if key in _CACHE:
        return _CACHE[key]
    seen = {}
    orig = E._voice_split

    def spy(rec, run, ci, events, why=None):
        r = orig(rec, run, ci, events, why)
        seen[(run.page, run.system, run.staff, ci)] = (
            [{"kind": e["kind"], "beats": e["duration_beats"], "heads": len(e.get("noteheads") or ()),
              "glyphs": sorted(h["glyph"] for h in e.get("noteheads") or ())} for e in events],
            None if r is None else [[events.index(e) for e in s] for s in r])
        return r

    env = {FLAG: "1"} if on else {FLAG: "0"}
    rows = json.load(open(FX / name))
    with mock.patch.dict(os.environ, {**env, "OMR_SURYA_KEEP_ALIVE": "0"}), mock.patch.object(E, "_voice_split", spy):
        log, _ = RR.rebuild_gather(rows)
        RR.run_stages(log)
        xml, _rep = E.to_musicxml({"record": log.to_json(), "summary": log.summary()})
    _XML[key] = xml
    _CACHE[key] = seen
    return seen


def _sum(events):
    return sum(e["beats"] for e in events)


class TestTheGeometry(unittest.TestCase):
    def test_default_is_on(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertTrue(OC.enabled())
        for off in ("0", "false", "no", "off"):
            with mock.patch.dict(os.environ, {FLAG: off}):
                self.assertFalse(OC.enabled())

    def test_a_second_is_beside_and_one_step_off(self):
        self.assertTrue(OC.is_second((0, 0, 24, 14), (24, 7, 24, 14)))
        self.assertFalse(OC.is_second((0, 0, 24, 14), (24, 0, 24, 14)))      # same height: the next repeated note
        self.assertFalse(OC.is_second((0, 0, 24, 14), (24, 28, 24, 14)))     # a third: not a second
        self.assertFalse(OC.is_second((0, 0, 24, 14), (50, 7, 24, 14)))      # two heads away: the next note

    def test_a_head_that_cannot_reach_the_stem_gets_none(self):
        touches = lambda stem, head: not (stem[0] > head[0] + head[2] + 1 or stem[0] + stem[2] < head[0] - 1)
        head = (0, 0, 24, 14)
        partner = ("p", (24, 7, 24, 14))
        stem_at_seam = ("s", (22, -20, 4, 60))
        stem_far = ("s", (60, -20, 4, 60))
        self.assertEqual(len(OC.partner_stems(head, [partner], [stem_at_seam], touches)), 1)
        self.assertEqual(OC.partner_stems(head, [partner], [stem_far], touches), [])
        self.assertEqual(OC.partner_stems(head, [], [stem_at_seam], touches), [])


class TestTheGrouper(unittest.TestCase):
    def _heads(self, stem_a, stem_b, dur_a=(2.0, "half", 0), dur_b=(2.0, "half", 0), y_b=7):
        def head(x, y, dur, sid, pitch):
            return {"category": "notehead", "pitch": pitch, "duration_beats": dur[0], "duration_type": dur[1], "dots": dur[2],
                    "bbox": [x, y, 24, 14], "stem_id": sid, "stem_direction": "down"}
        return [head(0, 0, dur_a, stem_a, "D5"), head(24, y_b, dur_b, stem_b, "F5")]

    def test_default_off_two_events(self):
        self.assertEqual(len(voicing.group_chords_in_measure(self._heads("s1", "s1"))), 2)

    def test_one_stem_is_one_event(self):
        evs = voicing.group_chords_in_measure(self._heads("s1", "s1"), merge_seconds_on_one_stem=True)
        self.assertEqual([len(e["noteheads"]) for e in evs], [2])
        self.assertEqual(evs[0]["duration_beats"], 2.0)

    def test_control_two_stems_stay_two_events(self):
        """Can fail: two neighbours each on their OWN stem are two notes (beamed run), flag ON."""
        evs = voicing.group_chords_in_measure(self._heads("s1", "s2"), merge_seconds_on_one_stem=True)
        self.assertEqual(len(evs), 2)

    def test_control_unread_stem_stays_two_events(self):
        evs = voicing.group_chords_in_measure(self._heads(None, None), merge_seconds_on_one_stem=True)
        self.assertEqual(len(evs), 2)

    def test_values_that_disagree_are_not_merged(self):
        evs = voicing.group_chords_in_measure(self._heads("s1", "s1", dur_b=(1.0, "quarter", 0)), merge_seconds_on_one_stem=True)
        self.assertEqual(len(evs), 2)

    def test_not_a_second_is_not_merged(self):
        evs = voicing.group_chords_in_measure(self._heads("s1", "s1", y_b=0), merge_seconds_on_one_stem=True)
        self.assertEqual(len(evs), 2)


class TestSeansBars(unittest.TestCase):
    L = "litolff_p2_sean_bars.json"
    B = "brahms_sean_bars.json"

    def test_tile_7_two_half_notes_a_second_apart_are_one_chord(self):
        key = (2, 1, 4, 14)
        off = _replay(self.L, False)[key]
        on = _replay(self.L, True)[key]
        self.assertEqual([e["heads"] for e in off[0]], [1, 1])
        self.assertAlmostEqual(_sum(off[0]), 3.0)                 # the red bar Sean saw
        self.assertEqual([e["heads"] for e in on[0]], [2])
        self.assertAlmostEqual(_sum(on[0]), 2.0)                  # his 2/4 bar: one chord of 2.0

    def test_the_partner_head_is_written_blue_and_only_with_the_flag(self):
        """The partner's stem is inferred from the geometry of a second, so the head is GUESSED (CLAUDE.md §4); OFF writes none blue."""
        _replay(self.L, False)
        _replay(self.L, True)
        blue = lambda xml: [m for m in re.findall(r"<note[^>]*>", xml) if "1F6FEB" in m.upper()]
        n_off = len(blue(_XML[(self.L, False)]))
        n_on = len(blue(_XML[(self.L, True)]))
        self.assertEqual(n_on - n_off, 1)

    def test_tile_10_was_never_a_chord_split_and_is_untouched(self):
        key = (2, 0, 2, 3)
        off, on = _replay(self.L, False)[key], _replay(self.L, True)[key]
        self.assertEqual([(e["kind"], e["heads"], e["beats"]) for e in off[0]],
                         [("rest", 0, 0.25), ("chord", 2, 1.0), ("rest", 0, 1.0)])
        self.assertEqual(off, on)

    def test_tile_6_one_voice_gains_no_voice(self):
        key = (2, 1, 6, 9)
        off, on = _replay(self.L, False)[key], _replay(self.L, True)[key]
        self.assertEqual(off, on)

    def test_tile_11_chord_is_one_event_and_the_voices_are_not_made_worse(self):
        key = (4, 1, 2, 0)
        off, on = _replay(self.B, False)[key], _replay(self.B, True)[key]
        self.assertIn(2, [e["heads"] for e in off[0]])            # the chord was ONE event already
        self.assertEqual(off, on)

    def test_tile_12_and_tile_1_unchanged(self):
        for key in ((4, 1, 13, 7), (0, 0, 10, 1)):
            self.assertEqual(_replay(self.B, False)[key], _replay(self.B, True)[key], key)

    def test_mirror_two_voices_at_one_onset_stay_two_events_in_two_voices(self):
        key = (0, 0, 11, 0)
        off, on = _replay(self.B, False)[key], _replay(self.B, True)[key]
        self.assertIsNotNone(off[1])
        self.assertEqual(len(off[1]), 2)
        self.assertEqual(off, on)


if __name__ == "__main__":
    unittest.main()
