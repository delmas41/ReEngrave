"""ROADMAP 2.210 -- a box is a member of a stem only if its own ink can be a notehead (flag `OMR_STEM_MEMBER_INK`, default OFF; ON includes 2.209).

Two kinds beyond the 2.209 beam end, each needing two witnesses from different sources:
  merged_ink  Litolff p4 `glyph/4/1/1/4/17`, an "ff" boxed as a synthesized `stem_end_head` 3.3 x 3.3 sp over 15 strokes, joined the stem of a real
              hollow head. Witnesses: the box (reader + size) and the stroke map (strokes it stands on).
  tremolo     Brahms p12 `glyph/12/0/10/5/8`, a slash across a stem, written as a phantom note. Witnesses: the ownership layer refused the box as
              `tremolo_slash_across_a_stem`; the stem geometry (between two other members, or at the tip with a head >= 2.5 sp away).
RED without the fix: the `_ON` tests (the false box is still a member, the real head is rewritten); each `_TWIN` shows a near case stays a member.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import stem_value as SV
from tools.omr.staged.record import Outcome, Q, READERS
from tools.omr.tests.test_staged_stem_value import Stem, _v, _w

SP = 20.0
FLAG = SV.MEMBER_INK_ENV


def run(st, on):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        st.run()
    return st


def base():
    st = Stem(direction="down")
    st.log.observe(R.cell(0, 0, 0, 0), Q.CELL_STAFF_SPACE, SP, reader=READERS.GEOMETRY, frame="cell:0")
    return st


def synth_box(st, gi, y, *, w, h, source, n_strokes, dur=(0.5, 0, 1)):
    g = st.head(gi, "noteheadBlackOnLine", y, decided=dur, x=60, w=w, h=h)
    st.log.observe(g, Q.GLYPH_BOX, ("noteheadBlackOnLine", 60, y, w, h), reader=READERS.DETECTOR, frame="cell:0", score=0.06,
                   **({"source": source} if source else {}))
    st.log.observe(g, Q.GLYPH_STROKES, list(range(n_strokes)), reader=READERS.CV_GLYPH_STROKES, frame="cell:0",
                   shares=[1.0] * n_strokes, cover_min=0.5, partial=[])
    return g


class TestMergedInk(unittest.TestCase):
    def build(self, *, source="stem_end_head", w=66, h=60, n=15):
        st = base()
        real = st.head(0, "noteheadHalfInSpace", 0, decided=(2.0, 0, 0), x=82)
        false = synth_box(st, 1, 40, w=w, h=h, source=source, n_strokes=n)       # at the tip (stem y 0-80, down), 3.3 x 3 sp
        return st, real, false

    def test_flag_off_is_the_old_behaviour_CONTROL(self):
        st, real, false = self.build()
        run(st, False)
        self.assertEqual(len(st.log.verdict(Q.STEM_VALUE, real).detail["members"]), 2)

    def test_merged_box_is_not_a_member_ON(self):
        st, real, false = self.build()
        run(st, True)
        f = st.log.verdict(Q.STEM_VALUE, false)
        self.assertEqual((f.outcome, f.reason), (Outcome.ABSTAINED, "not_a_member"))
        self.assertEqual(st.log.verdict(Q.STEM_VALUE, real).reason, "lone_head")

    def test_a_detector_box_of_the_same_size_stays_a_member_TWIN(self):          # Litolff merges two seconds into one box
        st, real, false = self.build(source=None)
        run(st, True)
        self.assertEqual(len(st.log.verdict(Q.STEM_VALUE, real).detail["members"]), 2)

    def test_a_synthesized_box_of_head_size_stays_a_member_TWIN(self):
        st, real, false = self.build(w=34, h=30, n=6)
        run(st, True)
        self.assertNotEqual(st.log.verdict(Q.STEM_VALUE, false).reason, "not_a_member")

    def test_big_but_on_few_strokes_stays_a_member_TWIN(self):
        st, real, false = self.build(n=3)
        run(st, True)
        self.assertEqual(len(st.log.verdict(Q.STEM_VALUE, real).detail["members"]), 2)


class TestTremolo(unittest.TestCase):
    def build(self, *, y_slash, refused=True, extra_below=True):
        st = base()
        top = st.head(0, "noteheadBlackOnLine", 0, decided=(1.0, 1, 0), x=82)
        slash = st.head(1, "noteheadBlackInSpace", y_slash, decided=(1.0, 0, 0), x=82, h=12)
        low = st.head(2, "noteheadBlackOnLine", 64, decided=(1.0, 1, 0), x=82) if extra_below else None
        if refused:
            _v(st.log, R.cell(0, 0, 0, 0), Q.STROKE_OWNER, Outcome.DECIDED, {"owned": [], "contested": []},
               detail={"boxes": {slash.to_key(): ["refused", [[9, "refused_claims", None, "tremolo_slash_across_a_stem"]]]}})
        return st, top, slash, low

    def test_slash_between_two_heads_is_not_a_member_ON(self):
        st, top, slash, low = self.build(y_slash=32)
        run(st, True)
        f = st.log.verdict(Q.STEM_VALUE, slash)
        self.assertEqual((f.outcome, f.reason), (Outcome.ABSTAINED, "not_a_member"))

    def test_slash_near_the_tip_with_one_head_is_not_a_member_ON(self):          # Brahms p12 `glyph/12/0/10/5/8`: 1.3 sp from the tip
        st, top, slash, low = self.build(y_slash=58, extra_below=False)          # stem down, tip at y 80; slash centre 64 = 0.8 sp from it
        run(st, True)
        self.assertEqual(st.log.verdict(Q.STEM_VALUE, slash).reason, "not_a_member")

    def test_flag_off_keeps_it_CONTROL(self):
        st, top, slash, low = self.build(y_slash=32)
        run(st, False)
        self.assertNotEqual(st.log.verdict(Q.STEM_VALUE, slash).reason, "not_a_member")

    def test_no_refusal_from_the_ownership_layer_stays_TWIN(self):
        st, top, slash, low = self.build(y_slash=32, refused=False)
        run(st, True)
        self.assertNotEqual(st.log.verdict(Q.STEM_VALUE, slash).reason, "not_a_member")

    def test_refused_box_at_the_root_end_stays_a_member_TWIN(self):               # 5 of 8 refused boxes: a real head beside a sharp and a dot
        st, top, slash, low = self.build(y_slash=0, extra_below=False)
        run(st, True)
        self.assertNotEqual(st.log.verdict(Q.STEM_VALUE, slash).reason, "not_a_member")

    def test_refused_box_far_from_the_tip_with_a_head_above_stays_TWIN(self):     # Litolff p2 `glyph/2/0/1/1/5`: the lower head of a chord
        st, top, slash, low = self.build(y_slash=40, extra_below=False)
        run(st, True)
        self.assertNotEqual(st.log.verdict(Q.STEM_VALUE, slash).reason, "not_a_member")

    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(SV.member_ink_enabled())


if __name__ == "__main__":
    unittest.main()
