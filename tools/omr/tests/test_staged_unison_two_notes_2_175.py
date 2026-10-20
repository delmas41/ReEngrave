"""ROADMAP 2.175 (flag `OMR_UNISON_TWO_NOTES`, default OFF): a head with a stem each way is TWO notes.

STAGED ADJUDICATE (`unison_two.adjudicate_unison_voices`, `rhythm.adjudicate_event`, `rhythm.adjudicate_voices`,
`stem_value._one_stem_per_head`) and the EXPORT writer (`export_unison`). Fixture: the Litolff p3 unison of 2.141h
(`test_staged_unison_both_stems_2_141h._unison`): one head, an up stem at its right, a down stem at its left.
"""
from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import export_unison
from tools.omr.staged.adjudicators import unison_two
from tools.omr.staged import record as R
from tools.omr.staged.record import Kind, Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_duration import _flag, _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import _head, _real_stem
from tools.omr.tests.test_staged_unison_both_stems_2_141h import _reach, _unison

FLAG = unison_two.ENV


def _run(build, on):
    p = mock.patch.dict(os.environ, {FLAG: "1" if on else "0"})
    p.start()
    try:
        os.environ.pop("OMR_STEM_FINDER", None)
        log = Log()
        g = build(log)
        adjudicate.run(log)
        return log, g
    finally:
        p.stop()


def _flagged(log):
    """The same unison with a flag on each stem instead of beams: eighth up, eighth down."""
    _staff_space(log, 100)
    g = _head(log, 0, (143, 523, 139, 124))
    _real_stem(log, (261, 351, 19, 311))
    _real_stem(log, (146, 560, 26, 413))
    _flag(log, gi=50, cls="flag8thUp", x=270, y=351, w=60, h=200)
    _flag(log, gi=51, cls="flag8thDown", x=150, y=800, w=60, h=170)
    _reach(log, g, "down")
    return g


def _plain(log):
    """A unison with no beam and no flag on either stem."""
    return _unison(log, down_beams=0, up_beams=0)


class TestTheSecondVoiceIsRead(unittest.TestCase):

    def test_flag_OFF_decides_nothing_and_the_event_is_one(self):
        log, g = _run(lambda l: _unison(l, down_beams=2, up_beams=1), False)
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual((v.outcome, v.reason), (Outcome.ABSTAINED, "flag_off"))
        events = _events(log, g)
        self.assertEqual(len(events), 1)
        self.assertNotIn("voice", events[0])

    def test_flag_ON_beams_each_stems_own_value_RED(self):
        log, g = _run(lambda l: _unison(l, down_beams=2, up_beams=1), True)
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual((v.outcome, v.reason), (Outcome.DECIDED, "two_notes"))
        self.assertEqual(v.value["voices"]["up"]["beats"], 0.5)
        self.assertEqual(v.value["voices"]["down"]["beats"], 0.25)
        self.assertEqual(v.value["voices"]["up"]["source"], "beam")
        self.assertFalse(v.value["agree"])

    def test_flag_ON_a_flag_on_each_stem_is_two_eighths(self):
        log, g = _run(_flagged, True)
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual((v.outcome, v.reason), (Outcome.DECIDED, "two_notes"), v.detail)
        self.assertEqual([v.value["voices"][s]["beats"] for s in ("up", "down")], [0.5, 0.5])
        self.assertEqual(v.value["voices"]["up"]["source"], "flag")
        self.assertTrue(v.value["agree"])

    def test_flag_ON_one_voice_marked_the_other_not_makes_no_second_note_CONTROL(self):
        """A quarter by absence is not read: the unmarked voice refuses, the head stays one note (rule 8)."""
        log, g = _run(lambda l: _unison(l, down_beams=0, up_beams=1), True)
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual((v.outcome, v.reason), (Outcome.ABSTAINED, "one_voice_unmarked"))
        self.assertEqual(len(_events(log, g)), 1)

    def test_flag_ON_two_unmarked_stems_are_two_quarters(self):
        log, g = _run(_plain, True)
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual([v.value["voices"][s]["beats"] for s in ("up", "down")], [1.0, 1.0])

    def test_flag_ON_one_stem_is_not_a_unison_CONTROL(self):
        log, g = _run(lambda l: _unison(l, with_up_stem=False), True)
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual((v.outcome, v.reason), (Outcome.ABSTAINED, "not_a_unison"))


def _events(log, g):
    v = log.verdict(Q.EVENT, g.at(Kind.CELL))
    return v.value["events"]


class TestOneEventHereTwoVoicesThere(unittest.TestCase):
    """`Q.EVENT` keeps ONE event per head (every single-stream bar sum counts a head once); `adjudicate_voices` stands it
    in two streams only where the two voices then sum alike."""

    @staticmethod
    def _frame(l, g0):
        # rule 1 of `adjudicate_voices` reads the PAGE-frame box and the staff spacing
        l.observe(g0, Q.GLYPH_BOX, ("noteheadBlackInSpace", 143, 523, 139, 124), reader=READERS.DETECTOR,
                  frame="cell:0", score=0.9, bbox_page_px=[143, 523, 282, 647])
        l.observe(R.staff(0, 0, 0), Q.STAFF_SPACING, 100.0, reader=READERS.GEOMETRY, frame="page")
        return g0

    def test_flag_ON_the_event_is_one_and_carries_each_voices_value(self):
        log, g = _run(lambda l: self._frame(l, _unison(l, down_beams=2, up_beams=1)), True)
        events = _events(log, g)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["unison"], {"up": 0.5, "down": 0.25})

    def test_flag_ON_voices_that_sum_alike_are_two_voices_each_on_its_own_value(self):
        log, g = _run(lambda l: self._frame(l, _flagged(l)), True)
        vo = log.verdict(Q.VOICES, g.at(Kind.CELL))
        self.assertEqual((vo.outcome, vo.reason), (Outcome.DECIDED, "two_voices_same_beat"))
        self.assertEqual(vo.value["n_voices"], 2)
        self.assertEqual(vo.value["voices"], [[g.glyph], [g.glyph]])

    def test_flag_ON_voices_that_do_not_sum_alike_stay_one_stream_RED(self):
        """An eighth in one voice and a sixteenth in the other is not a bar either voice fills alike: the head stays one
        event in one voice, as with the flag OFF, and the reason is on the record."""
        log, g = _run(lambda l: self._frame(l, _unison(l, down_beams=2, up_beams=1)), True)
        vo = log.verdict(Q.VOICES, g.at(Kind.CELL))
        self.assertNotEqual(vo.value and vo.value.get("n_voices"), 2)

    def test_flag_ON_each_voice_sums_on_its_own_stem_value(self):
        from tools.omr.staged.adjudicators import rhythm
        events = [{"kind": "chord", "_glyphs": [0], "unison_beats": 0.5},
                  {"kind": "chord", "_glyphs": [0], "unison_beats": 0.25}]
        ev = SimpleNamespace(verdict=lambda *a, **k: None)
        cell = SimpleNamespace(page=0, system=0, staff=0, cell=0)
        self.assertEqual(rhythm._sum_beats(ev, cell, events[:1]), 0.5)
        self.assertEqual(rhythm._sum_beats(ev, cell, events[1:]), 0.25)


class TestWhichHeadsAreUnisons(unittest.TestCase):

    def _tile3(self, log):
        """The 2.167e tile-3 shape: the up stem's row also runs 1.0 space below the head (the strokes touch at it)."""
        _staff_space(log, 100)
        g = _head(log, 0, (143, 523, 139, 124))
        _real_stem(log, (261, 250, 19, 497))       # up at the right: 2.73 sp above, 1.0 sp below
        _real_stem(log, (146, 560, 26, 413))       # down at the left
        _flag(log, gi=50, cls="flag8thUp", x=280, y=250, w=60, h=200)
        _flag(log, gi=51, cls="flag8thDown", x=150, y=860, w=60, h=110)
        _reach(log, g, "down")
        return g

    def test_OFF_the_touching_stem_leaves_two_stems_and_flag_ON_reads_the_unison_RED(self):
        log, g = _run(self._tile3, False)
        self.assertEqual(log.verdict(Q.HEAD_STEM, g).reason, "two_stems")
        log, g = _run(self._tile3, True)
        self.assertEqual(log.verdict(Q.HEAD_STEM, g).reason, "unison_two_voices")
        v = log.verdict(Q.UNISON_VOICES, g)
        self.assertEqual(v.outcome, Outcome.DECIDED, v.detail)

    def test_CONTROL_a_stem_as_long_each_way_is_not_a_unison_stem(self):
        """A barline-like stroke (the same reach above and below, on the right) never reads as an up stem."""
        def build(log):
            _staff_space(log, 100)
            g = _head(log, 0, (143, 523, 139, 124))
            _real_stem(log, (261, 250, 19, 650))   # 2.73 sp above, 2.7 sp below: neither dominates
            _real_stem(log, (146, 560, 26, 413))
            return g
        log, g = _run(build, True)
        self.assertNotEqual(log.verdict(Q.HEAD_STEM, g).reason, "unison_two_voices")


def _det(**kw):
    return {"duration_beats": 1.0, "duration_type": "quarter", "dots": 0, "beam_levels": 0, "stem_direction": None,
            "glyph": "glyph/0/0/0/0/0", "pitch": "C4", **kw}


class _Rec:
    def __init__(self, v):
        self.v = v

    def verdict(self, q, sub):
        return self.v if q == Q.UNISON_VOICES else None


def _decided(up=0.5, down=0.25):
    def voice(b):
        return {"beats": b, "written": b, "dots": 0, "beam_levels": {1.0: 0, 0.5: 1, 0.25: 2}[b], "source": "beam"}
    return {"outcome": "decided", "value": {"voices": {"up": voice(up), "down": voice(down)}}}


class TestExportWritesTwoNotes(unittest.TestCase):

    def setUp(self):
        p = mock.patch.dict(os.environ, {FLAG: "1"})
        p.start()
        self.addCleanup(p.stop)

    def test_split_gives_the_up_voice_to_the_head_and_the_down_voice_to_its_twin(self):
        det = _det()
        self.assertTrue(export_unison.split(_Rec(_decided()), "glyph/0/0/0/0/0", det))
        self.assertEqual((det["duration_beats"], det["duration_type"], det["stem_direction"]), (0.5, "eighth", "up"))
        tw = det["_unison_twin"]
        self.assertEqual((tw["duration_beats"], tw["duration_type"], tw["stem_direction"], tw["pitch"]),
                         (0.25, "sixteenth", "down", "C4"))
        self.assertTrue(tw["unison_twin"])

    def test_split_does_nothing_for_an_abstained_verdict_or_the_flag_off(self):
        det = _det()
        self.assertFalse(export_unison.split(_Rec({"outcome": "abstained", "value": None}), "g", det))
        self.assertNotIn("_unison_twin", det)
        with mock.patch.dict(os.environ, {FLAG: "0"}):
            self.assertFalse(export_unison.split(_Rec(_decided()), "g", det))

    def _runs(self, directions_kept):
        det = _det()
        export_unison.split(_Rec(_decided()), "g", det)
        cell = SimpleNamespace(detections=[det])
        runs = {"k": SimpleNamespace(cells={0: cell})}
        self.assertEqual(export_unison.expand(runs), 1)
        self.assertEqual(len(cell.detections), 2)
        if not directions_kept:                 # `_settle_divisi_pairs` left the bar fused
            for d in cell.detections:
                d["stem_direction"] = None
        return runs, cell

    def test_a_bar_kept_as_two_voices_keeps_both_notes(self):
        runs, cell = self._runs(True)
        stats = {}
        export_unison.settle(runs, stats)
        self.assertEqual(len(cell.detections), 2)
        self.assertEqual(stats, {"unison_twins_kept": 1})

    def test_a_bar_left_fused_drops_the_twin_and_restores_the_head_RED(self):
        runs, cell = self._runs(False)
        stats = {}
        export_unison.settle(runs, stats)
        self.assertEqual(len(cell.detections), 1)
        d = cell.detections[0]
        self.assertEqual((d["duration_beats"], d["duration_type"]), (1.0, "quarter"))
        self.assertEqual(stats, {"unison_twins_dropped_bar_left_fused": 1})

    def test_the_default_is_OFF(self):
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(unison_two.enabled())
        for word, on in (("1", True), ("on", True), ("yes", True), ("0", False), ("", False), ("maybe", False)):
            with mock.patch.dict(os.environ, {FLAG: word}):
                self.assertEqual(unison_two.enabled(), on, word)


class TestARedUnisonBarKeepsBothVoices(unittest.TestCase):
    """ROADMAP 2.175 + 2.173 (Sean 2026-10-20 "Yes"): a unison bar whose voices do not both add up keeps BOTH voices."""

    def _runs(self, other_direction):
        def det(g, x, pitch, beats, direction, twin=False):
            return {"category": "notehead", "class": "noteheadBlack", "bbox": [x, 0, 20, 16], "pitch": pitch,
                    "duration_beats": beats, "duration_type": "eighth", "dots": 0, "beam_levels": 1, "glyph": g,
                    "stem_direction": direction, **({"unison_twin": True} if twin else {})}
        dets = [det("g1", 0, "C4", 0.5, "up"), det("g1", 0, "C4", 0.25, "down", True),
                det("g2", 100, "D4", 1.0, other_direction)]
        return {"k": SimpleNamespace(cells={0: SimpleNamespace(detections=dets)})}

    def test_unequal_streams_are_kept_as_two_voices_when_red_bars_are_on(self):
        from tools.omr.staged import export as E
        for other, key in (("up", "unison_bars_kept_two_voices_streams_carry_unequal_time"),
                           (None, "unison_bars_kept_two_voices_an_undecided_direction_in_the_bar")):
            runs = self._runs(other)
            stats = {}
            with mock.patch.dict(os.environ, {"OMR_RED_BARS": "1"}):
                E._settle_divisi_pairs(runs, stats)
            dets = runs["k"].cells[0].detections
            self.assertEqual([d["stem_direction"] for d in dets[:2]], ["up", "down"], other)
            self.assertEqual(stats.get(key), 1, stats)

    def test_CONTROL_with_red_bars_off_the_bar_is_left_fused(self):
        from tools.omr.staged import export as E
        runs = self._runs("up")
        stats = {}
        with mock.patch.dict(os.environ, {"OMR_RED_BARS": "0"}):
            E._settle_divisi_pairs(runs, stats)
        self.assertTrue(all(d["stem_direction"] is None for d in runs["k"].cells[0].detections))

    def test_an_unread_direction_note_in_a_kept_unison_bar_is_a_GUESSED_voice(self):
        from tools.omr.staged import export as E
        runs = self._runs(None)
        stats = {}
        with mock.patch.dict(os.environ, {"OMR_RED_BARS": "1", FLAG: "1"}):
            E._settle_divisi_pairs(runs, stats)
            export_unison.settle(runs, stats)
        other = runs["k"].cells[0].detections[2]
        self.assertEqual(other["guess"]["rule"], "voice_guessed")
        self.assertEqual(other["guess"]["chosen"], {"voice": 1})
        self.assertEqual(stats["unison_voice_guessed_notes"], 1)

    def test_CONTROL_a_note_that_already_has_a_status_keeps_it_and_the_guess_is_only_counted(self):
        from tools.omr.staged import export as E
        runs = self._runs(None)
        runs["k"].cells[0].detections[2]["guess"] = {"rule": "other_rule"}
        stats = {}
        with mock.patch.dict(os.environ, {"OMR_RED_BARS": "1", FLAG: "1"}):
            E._settle_divisi_pairs(runs, stats)
            export_unison.settle(runs, stats)
        self.assertEqual(runs["k"].cells[0].detections[2]["guess"], {"rule": "other_rule"})
        self.assertEqual(stats["unison_voice_guess_in_a_coloured_note"], 1)


if __name__ == "__main__":
    unittest.main()
