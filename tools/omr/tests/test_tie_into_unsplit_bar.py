"""A tie from a split bar's upper stream into a one-voice bar is written, and carries its accidental (STAGED EXPORT,
`export._record_tie_spans`).

Cause (Brahms p5, Vl.II bars 42-43, cells `5/1/10/6` -> `5/1/10/7`): the print ties the dotted-quarter chord F#5/A4 (sharp and
natural printed) over the barline to an unmarked F/A chord. ADJUDICATE bound both arcs as ties (`page_binding_same_pitch_adjacent`);
EXPORT refused both as `tie_ends_in_two_voices` because bar 42 is split (the start is stream 1) and bar 43 is not (the stop is
unmapped, voice 0) -- though both are written `<voice>1`. The refusal also undid the tie's carry (page-facts, Sean 2026-10-30:
"A tie carries an accidental even across a bar line"), so the file wrote F5/Ab4 under a printed tie from F#5/A4.
The rows below are that bar's own glyph keys, pitches and voices.
"""
from __future__ import annotations

import collections
import os
import unittest
from unittest import mock

from tools.omr.staged import export as SX

F_START, A_START = "glyph/5/1/10/6/3", "glyph/5/1/10/6/15"
F_STOP, A_STOP = "glyph/5/1/10/7/0", "glyph/5/1/10/7/12"


def _rec():
    return SX.Record({"record": {"observations": [], "verdicts": [], "abstentions": []}})


def _head(glyph, pitch):
    return {"glyph": glyph, "category": "notehead", "pitch": pitch}


def _run(start_voice, stop_voice):
    s0, s1 = _head(F_START, "F#5"), _head(A_START, "A4")
    t0, t1 = _head(F_STOP, "F5"), _head(A_STOP, "Ab4")
    measures = [{"detections": [s0, s1]}, {"detections": [t0, t1]}]
    ties = {"pairs": {(F_START, F_STOP): ["arc-above"], (A_START, A_STOP): ["arc-below"]},
            "consumed": set(), "contradictions": [], "linked": []}
    voice_of = {}
    for d in (s0, s1):
        if start_voice:
            voice_of[id(d)] = start_voice
    for d in (t0, t1):
        if stop_voice:
            voice_of[id(d)] = stop_voice
    dropped, counters = collections.Counter(), {}
    with mock.patch.dict(os.environ, {SX.TIE_CARRY_ENV: "1"}):
        spans = SX._record_tie_spans(measures, ties, voice_of, dropped, rec=_rec(), counters=counters)
    return spans, dropped, counters, (t0["pitch"], t1["pitch"])


class TestTieIntoUnsplitBar(unittest.TestCase):
    def test_brahms_p5_vl2_bar43_tie_written_and_carried(self):
        # the real bar: start in stream 1 of a split bar, stop in a one-voice bar (unmapped)
        spans, dropped, counters, stops = _run(1, 0)
        self.assertEqual(len(spans), 2)
        self.assertNotIn("tie_ends_in_two_voices", dropped)
        self.assertEqual(stops, ("F#5", "A4"))
        self.assertEqual(counters.get("tie_carries_the_accidental"), 2)

    def test_the_other_direction_too(self):
        spans, dropped, _, stops = _run(0, 1)
        self.assertEqual(len(spans), 2)
        self.assertEqual(stops, ("F#5", "A4"))

    def test_lower_stream_into_unsplit_bar_still_refused(self):
        # stream 2 is written `<voice>2`, the one-voice bar `<voice>1`: MusicXML pairs a tie within a voice, so it stays unpaired
        # and the stop keeps its own reading (the carry exists only through a written tie)
        spans, dropped, counters, stops = _run(2, 0)
        self.assertEqual(spans, [])
        self.assertEqual(dropped["tie_ends_in_two_voices"], 2)
        self.assertEqual(stops, ("F5", "Ab4"))
        self.assertEqual(counters.get("tie_carry_undone_not_written"), 2)

    def test_two_unsplit_bars_unchanged(self):
        spans, dropped, _, stops = _run(0, 0)
        self.assertEqual(len(spans), 2)
        self.assertEqual(stops, ("F#5", "A4"))

    def test_no_tie_no_carry(self):
        # the rule's other side: without a tie pair an accidental never crosses the barline
        s0, t0 = _head(F_START, "F#5"), _head(F_STOP, "F5")
        ties = {"pairs": {}, "consumed": set(), "contradictions": [], "linked": []}
        with mock.patch.dict(os.environ, {SX.TIE_CARRY_ENV: "1"}):
            spans = SX._record_tie_spans([{"detections": [s0]}, {"detections": [t0]}], ties, {}, collections.Counter(),
                                         rec=_rec(), counters={})
        self.assertEqual(spans, [])
        self.assertEqual(t0["pitch"], "F5")


if __name__ == "__main__":
    unittest.main()
