"""ROADMAP 2.137 -- a tremolo slash is never oval, so it need not stand away
from the stem's ends (`OMR_SLASH_AT_STEM_END`, STAGED, default ON since 2026-10-15).

Sean, 2026-10-15 (page-facts §1): *"They are never oval shaped - always thick
diagonal lines."* The 20261014-night records keep print-confirmed slashes as
noteheads because 2.49's POSITION test (>= 0.5 box-heights from both stem ends)
and its 20-degree SHAPE floor refuse the first slash of a stack, which sits at
the stem's tip. Numbers in these tests are real: Brahms `glyph/0/0/4/1/6`
(angle 20.2, elongation 2.63, fill 0.535, shares 0.42/0.58, position 0.07),
`glyph/12/0/11/6/5` (angle 10.9, el 2.9, fill 0.40, position 0.11); the real
half head `glyph/12/0/2/8/7` of Litolff (elongation 1.25, a stroke read under it).

RED FIRST: every test that turns the flag on fails on main, where the flag does
not exist. The controls are paired: the same box with one number changed flips
the verdict, so a control can fail (CLAUDE.md rule 7).

NO TEST HERE ASSERTS ON MODULE SOURCE TEXT (CLAUDE.md §6c).
"""

from __future__ import annotations

import os
import unittest
import unittest.mock

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401  registers them
from tools.omr.staged import record as R
from tools.omr.staged.adjudicators import notehead_precision as NP
from tools.omr.staged.record import Log, Q, READERS

from tools.omr.tests.test_staged_notehead_precision import (
    _cell_geometry, _notehead)
from tools.omr.tests.test_staged_stacked_head_fit import _fit_row, _stem_row
from tools.omr.tests.test_staged_tremolo_slash import (
    _cross_ink_row, _run_notehead)

CELL = R.cell(0, 0, 0, 0)
ENV = NP.SLASH_AT_STEM_END_ENV if hasattr(NP, "SLASH_AT_STEM_END_ENV") \
    else "OMR_SLASH_AT_STEM_END"


def _flag(on):
    return unittest.mock.patch.dict(os.environ, {ENV: "1" if on else "0"})


def _slash_at_tip(*, angle=20.2, elong=2.63, fill=0.535, left=0.42,
                  right=0.58, stroke=False):
    """One box 0.2 box-heights from a stem's top end -- the slash of a stack
    that sits at the tip. Returns `(log, glyph)`."""
    log = Log()
    _cell_geometry(log)
    g = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=130.0, y_c=-30.0,
                  w_c=140.0, h_c=100.0)
    stem = _stem_row(log, CELL, x_c=200.0, y_c=0.0, w_c=10.0, h_c=400.0)
    _cross_ink_row(log, g, stem_id=stem.id, left_share=left, right_share=right,
                   angle_deg=angle, elongation=elong, fill=fill)
    if stroke:
        log.observe(CELL, Q.STEM_SLASH, 1, reader=READERS.CV_STEM_SLASH,
                    frame="cell:0", stem_row_id=stem.id,
                    strokes=[{"reason": None, "box": [135.0, -20.0, 265.0, 50.0],
                              "centreline": [135.0, 45.0, 265.0, -15.0],
                              "thickness_px": 30.0, "angle_deg": 25.0,
                              "thickness_ratio": 3.0, "left_reach": 0.6,
                              "right_reach": 0.6, "y": 15.0}],
                    head_at_end={"top": False, "bottom": True})
    return log, g


def _verdict(log, g):
    log = _run_notehead(log)
    return log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, g)


class TestFlagDefault(unittest.TestCase):

    def test_default_ON_and_only_an_off_word_restores_the_old_reader(self):
        env = {k: v for k, v in os.environ.items() if k != ENV}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(NP.slash_at_stem_end_enabled())
        for word in ("0", "", "false", "no", "off", "OFF"):
            with unittest.mock.patch.dict(os.environ, {ENV: word}):
                self.assertFalse(NP.slash_at_stem_end_enabled(), word)
        for word in ("1", "on", "true", "typo"):
            with unittest.mock.patch.dict(os.environ, {ENV: word}):
                self.assertTrue(NP.slash_at_stem_end_enabled(), word)

    def test_off_word_a_slash_at_the_stem_tip_is_still_kept_as_today(self):
        """The 2.49 behaviour is untouched with the flag off: position fails,
        the box stays a head (the residue this lane measured)."""
        log, g = _slash_at_tip()
        with _flag(False):
            v = _verdict(log, g)
        self.assertIs(v.value, False)
        self.assertFalse(v.detail["tremolo_slash_signal"]["position_ok"])


class TestSlashAtStemEnd(unittest.TestCase):

    def test_RED_a_non_oval_slash_at_the_tip_is_refused_with_its_margin(self):
        log, g = _slash_at_tip()
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tremolo_slash_crosses_stem")
        self.assertIsNotNone(v.margin)
        self.assertGreaterEqual(v.margin, 0.0)
        self.assertIn("margin_axis", v.detail)
        self.assertFalse(v.detail["tremolo_slash_signal"]["position_ok"])

    def test_RED_a_slash_below_the_old_20_degree_floor_is_refused(self):
        """Brahms `glyph/12/0/11/6/5`: 10.9 degrees, position 0.11."""
        log, g = _slash_at_tip(angle=10.9, elong=2.9, fill=0.40)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "tremolo_slash_crosses_stem")

    def test_RED_a_one_sided_ink_with_a_read_stroke_under_it_is_refused(self):
        """Brahms `glyph/0/0/8/5/5`: the ink split reads 0.16/0.84 (the stem
        sits in the box's left third) but GATHER read a stroke reaching both
        sides of the stem under it."""
        log, g = _slash_at_tip(angle=33.6, elong=2.08, fill=0.50, left=0.156,
                               right=0.844, stroke=True)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, True)
        self.assertEqual(v.detail["margin_axis"] is not None, True)
        self.assertEqual(v.detail["refused_via"], "stem_slash_stroke")

    def test_CONTROL_the_same_one_sided_ink_without_a_stroke_is_kept(self):
        """Pairs with the test above: only the stroke row differs."""
        log, g = _slash_at_tip(angle=33.6, elong=2.08, fill=0.50, left=0.156,
                               right=0.844, stroke=False)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)
        self.assertIsNone(v.detail["tremolo_slash_signal"]["at_stem_end"]
                          ["via"])

    def test_CONTROL_an_oval_head_at_the_stem_end_is_kept(self):
        """A real head: elongation 1.25, fill 0.58, both sides of a stem."""
        log, g = _slash_at_tip(angle=27.3, elong=1.25, fill=0.58)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")

    def test_CONTROL_an_oval_head_with_a_stroke_read_under_it_is_kept(self):
        """Litolff `glyph/12/0/2/8/7`: a real half head a stroke was read
        under (position 0.25). The stroke alone never decides; the ink is
        oval."""
        log, g = _slash_at_tip(angle=27.3, elong=1.25, fill=0.58, left=0.05,
                               right=0.95, stroke=True)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)

    def test_the_controls_can_fail_elongation_alone_flips_the_verdict(self):
        """Proof the oval control discriminates: raise elongation 1.25 -> 2.0
        and the same box is refused."""
        log, g = _slash_at_tip(angle=27.3, elong=2.0, fill=0.58 - 0.1)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, True)

    def test_CONTROL_a_steep_rest_zigzag_is_not_asked(self):
        """Brahms quarter rests boxed as heads read 64-67 degrees."""
        log, g = _slash_at_tip(angle=64.2, elong=1.86, fill=0.26)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)

    def test_CONTROL_a_thin_sliver_is_not_a_thick_stroke(self):
        """Litolff `glyph/6/0/6/11/13`: fill 0.067 (a slur's sliver)."""
        log, g = _slash_at_tip(angle=10.5, elong=4.58, fill=0.067)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)

    def test_CONTROL_a_tiny_bleed_is_kept(self):
        log, g = _slash_at_tip(left=0.05, right=0.95)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)

    def test_a_kept_near_miss_files_its_negative_margin(self):
        log, g = _slash_at_tip(angle=8.0)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)
        near = v.detail["tremolo_slash_signal"]["at_stem_end"]
        self.assertFalse(near["fires"])
        self.assertLess(near["margin"], 0.0)
        self.assertEqual(near["axis"], "angle_floor")

    def test_no_shape_read_is_not_a_slash(self):
        log = Log()
        _cell_geometry(log)
        g = _notehead(log, 0, cls="noteheadBlackInSpace", x_c=130.0,
                      y_c=-30.0, w_c=140.0, h_c=100.0)
        with _flag(True):
            v = _verdict(log, g)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "notehead")


class TestStackedGroupNeverKeepsTheSlash(unittest.TestCase):

    def test_RED_with_the_flag_the_slash_loses_the_keep_choice(self):
        log = Log()
        _cell_geometry(log)
        head = _notehead(log, 0, cls="noteheadHalfOnLine", pos_float=4.0,
                         y_c=200.0)
        slash = _notehead(log, 1, cls="noteheadHalfOnLine", pos_float=4.0,
                          x_c=130.0, y_c=-30.0, w_c=140.0, h_c=100.0)
        _fit_row(log, head, k=1, slot=0, pos_float=4.0, ink=0.30)
        _fit_row(log, slash, k=1, slot=0, pos_float=4.0, ink=0.90)
        stem = _stem_row(log, CELL, x_c=200.0, y_c=0.0, w_c=10.0, h_c=400.0)
        _cross_ink_row(log, slash, stem_id=stem.id, left_share=0.42,
                       right_share=0.58, angle_deg=20.2, elongation=2.63,
                       fill=0.535)
        with _flag(True):
            log = _run_notehead(log)
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, slash).value,
                      True)
        self.assertIs(log.verdict(Q.NOTEHEAD_IS_NOT_A_NOTEHEAD, head).value,
                      False, "the real head beside the slash is kept")


if __name__ == "__main__":
    unittest.main()
