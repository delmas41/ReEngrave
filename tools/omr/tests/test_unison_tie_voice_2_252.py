"""ROADMAP 2.252 r3 -- at a UNISON each voice carries its own tie (`OMR_UNISON_TIE_VOICE`, default OFF).

Sean 2026-11-02 (r2 tile 4): a unison half note with ties above and below on both sides -- the arc above is the up-stem
voice's tie, the arc below the down-stem voice's. `Q.TIE_PAIR` names glyphs; a unison is one glyph written as two
notes (2.175: head = up voice, twin = down voice), so every arc of a pair landed on the up voice."""
from __future__ import annotations

import os
import unittest

from tools.omr.staged import export as E
from tools.omr.staged import export_unison as U


def _rec(arc_boxes, groups=()):
    obs = [{"id": "o%d" % i, "quantity": "glyph_box", "subject": a, "value": ["tie", 0, 0, 1, 1],
            "detail": {"bbox_page_px": list(b)}} for i, (a, b) in enumerate(arc_boxes.items())]
    obs += [{"id": "g%d" % i, "quantity": "mark_group", "subject": s, "value": gid} for i, (s, gid) in enumerate(groups)]
    return E.Record({"record": {"observations": obs, "verdicts": [], "abstentions": []}})


def _head(y=100.0):                       # bbox_page [x, y, w, h]: centre 110
    return {"bbox_page": [0.0, y, 20.0, 20.0], "category": "notehead"}


ABOVE, BELOW, ACROSS = (0, 80, 50, 98), (0, 122, 50, 140), (0, 100, 50, 120)


class TestUnisonTieVoice(unittest.TestCase):

    def setUp(self):
        self.h1, self.h2, self.t1, self.t2 = _head(), _head(), _head(), _head()

    def ends(self, boxes, t1=True, t2=True):
        d, c = {}, {}
        out = U.tie_ends(_rec(boxes), list(boxes), self.h1, self.h2, self.t1 if t1 else None,
                         self.t2 if t2 else None, d, c)
        return out, d, c

    def test_arcs_above_and_below_tie_both_voices(self):
        out, d, c = self.ends({"a": ABOVE, "b": BELOW})
        self.assertEqual(out, [(self.h1, self.h2), (self.t1, self.t2)])
        self.assertEqual(c.get("unison_tie_down_voice_written"), 1)

    def test_an_arc_below_only_ties_the_down_voice(self):
        out, _d, c = self.ends({"b": BELOW})
        self.assertEqual(out, [(self.t1, self.t2)])
        self.assertEqual(c.get("unison_tie_moved_to_down_voice"), 1)

    def test_an_arc_above_only_is_unchanged(self):
        self.assertEqual(self.ends({"a": ABOVE})[0], [(self.h1, self.h2)])

    def test_an_arc_across_the_heads_is_not_read_for_a_side(self):    # the control that can fail
        out, _d, c = self.ends({"x": ACROSS})
        self.assertEqual(out, [(self.h1, self.h2)])
        self.assertEqual(c.get("unison_tie_side_unread"), 1)

    def test_no_twin_is_the_old_behaviour_and_a_second_arc_is_counted(self):
        out, d, _c = self.ends({"a": ABOVE, "b": BELOW}, t1=False, t2=False)
        self.assertEqual(out, [(self.h1, self.h2)])
        self.assertEqual(d.get("unison_tie_second_voice_has_no_note"), 1)

    def test_one_end_one_voice_is_unchanged_and_counted(self):
        out, d, _c = self.ends({"b": BELOW}, t2=False)
        self.assertEqual(out, [(self.h1, self.h2)])
        self.assertEqual(d.get("unison_tie_one_end_one_voice"), 1)

    def test_written_member_maps_an_unwritten_box_to_its_marks_written_box(self):
        rec = _rec({}, groups=[("g/a", "m1"), ("g/b", "m1"), ("g/c", "m2"), ("g/d", "m2")])
        self.assertEqual(U.written_member(rec, {"g/a": 1}), {"g/b": "g/a"})
        self.assertEqual(U.written_member(rec, {"g/a": 1, "g/c": 1, "g/d": 1}), {"g/b": "g/a"})  # two written: nothing

    def test_flag_default_off(self):
        old = os.environ.pop(U.TIE_VOICE_ENV, None)
        try:
            self.assertFalse(U.tie_voice_enabled())
            os.environ[U.TIE_VOICE_ENV] = "1"
            self.assertTrue(U.tie_voice_enabled())
        finally:
            os.environ.pop(U.TIE_VOICE_ENV, None)
            if old is not None:
                os.environ[U.TIE_VOICE_ENV] = old


class TestRecordTieSpans(unittest.TestCase):
    """`export._record_tie_spans` end to end on a fake part: OFF writes one span on the heads; ON writes each voice's."""

    def _measures(self):
        h1 = dict(_head(), glyph="glyph/1/0/0/0/0", pitch="E5")
        t1 = dict(h1, unison_twin=True)
        h2 = dict(_head(), glyph="glyph/1/0/0/1/0", pitch="E5")
        t2 = dict(h2, unison_twin=True)
        return [{"detections": [h1, t1]}, {"detections": [h2, t2]}], (h1, t1, h2, t2)

    def _run(self, on):
        measures, (h1, t1, h2, t2) = self._measures()
        rec = _rec({"arc/up": ABOVE, "arc/lo": BELOW})
        ties = {"pairs": {("glyph/1/0/0/0/0", "glyph/1/0/0/1/0"): ["arc/up", "arc/lo"]}, "refused": {},
                "consumed": set(), "contradictions": [], "linked": []}
        voice = {id(h1): 1, id(h2): 1, id(t1): 2, id(t2): 2}
        old = os.environ.get(U.TIE_VOICE_ENV)
        os.environ[U.TIE_VOICE_ENV] = "1" if on else "0"
        try:
            import collections
            spans = E._record_tie_spans(measures, ties, voice, collections.Counter(), rec=rec, counters={})
        finally:
            os.environ.pop(U.TIE_VOICE_ENV, None)
            if old is not None:
                os.environ[U.TIE_VOICE_ENV] = old
        return [(s[2], s[3]) for s in spans], (h1, t1, h2, t2)

    def test_off_one_span_on_the_heads(self):
        spans, (h1, t1, h2, t2) = self._run(False)
        self.assertEqual(len(spans), 1)
        self.assertIs(spans[0][0], h1)

    def test_on_a_span_per_voice(self):
        spans, (h1, t1, h2, t2) = self._run(True)
        self.assertEqual(len(spans), 2)
        self.assertIs(spans[1][0], t1)
        self.assertIs(spans[1][1], t2)


if __name__ == "__main__":
    unittest.main()
