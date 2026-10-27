"""ROADMAP 2.209 -- a detector "notehead" on a BEAM'S END is not a member of the stem (flag `OMR_STEM_BEAM_END`, default OFF).

The case is 2.206b tile 5 (Brahms p0 `glyph/0/0/12/1/1`, a sixteenth): the real head reads two beam levels; a 0.25-score box on the beam's thick
end at the stem's foot reads one; `stem_value` reads the levels from the member nearest the tip -- the box on the beam -- and the real head is
rewritten to an eighth. Every case is a synthetic down stem (the box on the beam is at the BOTTOM = the tip) with the real stroke-map row shapes.

RED without the fix: `test_beam_end_box_is_not_a_member` (flag ON keeps the real head's own two levels) fails on a tree without
`_on_beam_ink`; `test_flag_off_is_the_old_behaviour_CONTROL` shows the same fixture rewrites the head with the flag off, so the fixture CAN fail.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import stem_value as SV
from tools.omr.staged.record import Outcome, Q, READERS, STROKE_GLYPH_BASE
from tools.omr.tests.test_staged_stem_value import Stem, _dur, _w

SP = 100.0
FLAG = SV.BEAM_END_ENV


def S(kind, box, L, T, touches=()):
    return dict(kind=kind, box=box, L=L, T=T, touches=list(touches))


# stem (x 100-104, y 0-80, down: the tip is the bottom); a second stem and the beam (thick, joins both) hang at the bottom
STROKES = [
    S("vertical", (100, 0, 4, 80), 0.8, 0.04, [2]),            # 0: this stem
    S("vertical", (300, 0, 4, 80), 0.8, 0.04, [2]),            # 1: its neighbour
    S("horizontal", (100, 64, 204, 16), 2.04, 0.62, [0, 1]),   # 2: the beam
    S("blob", (82, 0, 20, 16), 0.2, 0.16),                     # 3: the real head's own blob
]


def build(*, false_head_strokes=None, real_head_row=True, strokes=STROKES, false_cls="noteheadBlackOnLine"):
    """The real head (top, two beam levels, decided) and the box on the beam's end (bottom, one level, decided)."""
    st = Stem(direction="down")
    real = st.head(0, "noteheadBlackOnLine", 0, decided=(0.25, 0, 2), x=82)
    false = st.head(1, false_cls, 64, decided=(0.5, 0, 1), x=82)
    for i, s in enumerate(strokes):
        st.log.observe(R.glyph(0, 0, 0, 0, STROKE_GLYPH_BASE + i), Q.STROKE, s["kind"], reader=READERS.CV_STROKE, frame="cell:0",
                       stroke_box=list(s["box"]), length_spaces=s["L"], angle_deg=0.0, thickness_spaces=s["T"],
                       thickness_spread_spaces=0.02, fill=0.9, sagitta_spaces=0.02,
                       touches=[[j, 1.0] for j in s["touches"]], staff_space_local_px=SP, ends=[0, 0, 0, 0],
                       end_steps_from_top=[0.0, 0.0], component=0)
    if real_head_row:
        st.log.observe(real, Q.GLYPH_STROKES, [3], reader=READERS.CV_GLYPH_STROKES, frame="cell:0", shares=[1.0], cover_min=0.5, partial=[])
    if false_head_strokes is not None:
        covered, partial = false_head_strokes
        st.log.observe(false, Q.GLYPH_STROKES, covered, reader=READERS.CV_GLYPH_STROKES, frame="cell:0",
                       shares=[1.0] * len(covered), cover_min=0.5, partial=partial)
    return st, real, false


ON_BEAM_END = ([], [[2, 0.22], [0, 0.33]])      # covers no stroke; partly on the beam and the stem (the Brahms p0 numbers)


def run(st, on):
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        st.run()
    return st


class TestBeamEndIsNotAMember(unittest.TestCase):
    def test_flag_off_is_the_old_behaviour_CONTROL(self):
        st, real, false = build(false_head_strokes=ON_BEAM_END)
        run(st, False)
        v = st.log.verdict(Q.STEM_VALUE, real)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertEqual(_w(v), (0.5, 0, 1), "the box on the beam sets the real head's levels (the bug this lane fixes)")

    def test_beam_end_box_is_not_a_member(self):
        st, real, false = build(false_head_strokes=ON_BEAM_END)
        run(st, True)
        v = st.log.verdict(Q.STEM_VALUE, real)
        self.assertEqual(v.outcome, Outcome.ABSTAINED)
        self.assertEqual(v.reason, "lone_head")                # the stem has one head left; nothing is rewritten
        f = st.log.verdict(Q.STEM_VALUE, false)
        self.assertEqual((f.outcome, f.reason), (Outcome.ABSTAINED, "not_a_member"))

    def test_a_box_that_covers_a_blob_of_its_own_stays_a_member_TWIN(self):
        st, real, false = build(false_head_strokes=([3], [[2, 0.22], [0, 0.33]]))
        run(st, True)
        self.assertEqual(_w(st.log.verdict(Q.STEM_VALUE, real)), (0.5, 0, 1))

    def test_partial_ink_that_is_not_a_beam_stays_a_member_TWIN(self):
        thin = [dict(s) for s in STROKES]
        thin[2] = S("horizontal", (100, 64, 204, 16), 2.04, 0.3, [0, 1])       # a slur remnant, not a beam
        st, real, false = build(false_head_strokes=ON_BEAM_END, strokes=thin)
        run(st, True)
        self.assertEqual(_w(st.log.verdict(Q.STEM_VALUE, real)), (0.5, 0, 1))

    def test_no_stroke_row_is_cannot_tell_so_a_member_TWIN(self):
        st, real, false = build(false_head_strokes=None)
        run(st, True)
        self.assertEqual(_w(st.log.verdict(Q.STEM_VALUE, real)), (0.5, 0, 1))

    def test_default_is_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(FLAG, None)
            self.assertFalse(SV.beam_end_enabled())


if __name__ == "__main__":
    unittest.main()
