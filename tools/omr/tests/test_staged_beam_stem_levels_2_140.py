"""ROADMAP 2.140 (STAGED GATHER `gather.beam_runs_at_stem_end` + ADJUDICATE `rhythm.adjudicate_duration`), flag `OMR_BEAM_STEM_LEVELS`,
default OFF. Brahms p18 sys1 staff12 cell7 (2.136 control tile 4, Sean: "16,16"): sixteenths under a double beam decided plain eighths.

GATHER reads the strokes AT A STEM'S TIP down a column beside it (a staff line never one); ADJUDICATE counts a second level from that
(one witness) and from the detector's stack box (a second source). Both -> decided; the page alone -> narrowed; the box alone ->
nothing. Each test that says RED can fail: the control beside it is the same input with the evidence removed."""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators, consequences          # noqa: F401
from tools.omr.staged import gather
from tools.omr.staged.adjudicators import rhythm
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_duration import _staff_space
from tools.omr.tests.test_staged_rhythm_leftovers import CELL, _head, _ink_row, _real_stem, _stroke

FLAG = rhythm.BEAM_STEM_LEVELS_ENV
SP = 100.0


def _raster(h=900, w=900):
    return np.zeros((h, w), bool)


def _stem(img, x, y0, y1, w=14):
    img[y0:y1, int(x - w // 2):int(x + w // 2)] = True


def _beam(img, x0, x1, y, th=60):
    img[y:y + th, x0:x1] = True


class TestGatherReadsTheStrokesAtAStemTip(unittest.TestCase):

    def _runs(self, img, lines=(), end="bottom", x=300, tip=700, line_px=20.0):
        return gather.beam_runs_at_stem_end(img, x, tip, end, SP, list(lines), line_px)

    def test_two_beams_with_a_gap_are_two_strokes_on_the_side_they_run(self):
        img = _raster(); _stem(img, 300, 300, 700); _beam(img, 300, 700, 640, 60); _beam(img, 300, 700, 550, 60)
        r = self._runs(img)
        self.assertEqual(len(r["right"]), 2)
        self.assertEqual(r["left"], [])
        self.assertAlmostEqual(r["right"][0][2], 0.6, places=2)

    def test_CONTROL_one_beam_is_one_stroke(self):
        img = _raster(); _stem(img, 300, 300, 700); _beam(img, 300, 700, 640, 60)
        self.assertEqual(len(self._runs(img)["right"]), 1)

    def test_a_lone_staff_line_is_never_a_stroke(self):
        img = _raster(); _stem(img, 300, 300, 700); img[595:605, :] = True
        r = self._runs(img, lines=(600,))
        self.assertEqual((r["left"], r["right"]), ([], []))

    def test_CONTROL_without_the_erasure_the_same_line_WOULD_be_a_thick_enough_stroke(self):
        # the control that can fail: a 40-px line (0.4 sp) read with NO line positions is counted -- so the erasure above is doing the work
        img = _raster(); _stem(img, 300, 300, 700); img[580:620, :] = True
        self.assertEqual(len(self._runs(img, lines=())["right"]), 1)
        self.assertEqual(len(self._runs(img, lines=(600,), line_px=40.0)["right"]), 0)

    def test_a_beam_crossing_a_staff_line_is_still_a_stroke(self):
        img = _raster(); _stem(img, 300, 300, 700); _beam(img, 300, 700, 600, 60); img[625:633, :] = True
        r = self._runs(img, lines=(629,))
        self.assertEqual(len(r["right"]), 1)

    def test_a_notehead_beside_the_stem_is_not_a_stroke_it_has_no_reach(self):
        img = _raster(); _stem(img, 300, 300, 700); img[560:660, 306:420] = True   # 1.1 sp wide blob
        r = self._runs(img)
        self.assertEqual(r["right"], [])

    def test_a_run_thinner_than_1_75_staff_lines_is_not_a_stroke(self):
        # 2.140 tiles 3 and 5 (Litolff; Sean: eighths): the second "stroke" was one staff line thick
        img = _raster(); _stem(img, 300, 300, 700); _beam(img, 300, 700, 640, 60); _beam(img, 300, 700, 550, 40)
        self.assertEqual(len(self._runs(img, line_px=0.0)["right"]), 2)          # no line measured: both read
        self.assertEqual(len(self._runs(img, line_px=30.0)["right"]), 1)         # 40 px < 1.75 x 30: a line, not a beam
        self.assertEqual(len(self._runs(img, line_px=20.0)["right"]), 2)         # 40 px >= 35: a beam

    def test_the_top_end_reads_down_from_the_tip(self):
        img = _raster(); _stem(img, 300, 100, 500); _beam(img, 300, 700, 100, 60); _beam(img, 300, 700, 190, 60)
        self.assertEqual(len(self._runs(img, end="top", tip=100)["right"]), 2)


class TestTheStackBoxWitness(unittest.TestCase):
    # tile 4: CV stroke 364 x 63 (thickness 54), detector box 696 x 113
    TILE4 = ([(1289, 1653, (1289, 535, 364, 63), 54.0)], [(946, 1642, (946, 553, 696, 113))])

    def test_the_tile4_box_stands_a_beam_taller_than_one_beam_would(self):
        ex, how = rhythm.stack_box_excess_beams(*self.TILE4, 1300)
        self.assertGreaterEqual(ex, rhythm.BEAM_STACK_BOX_EXCESS_MIN)
        self.assertAlmostEqual(ex, 0.774, places=2)

    def test_CONTROL_a_box_one_beam_tall_for_its_slope_is_not(self):
        cv = [(1289, 1653, (1289, 535, 364, 63), 54.0)]
        ex, _ = rhythm.stack_box_excess_beams(cv, [(946, 1642, (946, 553, 696, 72))], 1300)
        self.assertLess(ex, rhythm.BEAM_STACK_BOX_EXCESS_MIN)

    def test_CONTROL_a_box_over_TWO_counted_beams_is_not_a_third_level(self):
        # 2.140 tiles 1 and 4 (Brahms; Sean: sixteenths): two CV strokes already counted, the box spans both
        cv = [(100, 900, (100, 600, 800, 63), 62.0), (100, 900, (100, 700, 800, 63), 62.0)]
        ex, how = rhythm.stack_box_excess_beams(cv, [(50, 950, (50, 590, 900, 175))], 300)
        self.assertLess(ex, rhythm.BEAM_STACK_BOX_EXCESS_MIN)
        self.assertEqual(how["counted_strokes"], 2)
        ex1, _ = rhythm.stack_box_excess_beams(cv[:1], [(50, 950, (50, 590, 900, 175))], 300)
        self.assertGreater(ex1, rhythm.BEAM_STACK_BOX_EXCESS_MIN)     # the same box against ONE stroke reads a level more

    def test_no_measured_thickness_or_no_box_is_cannot_tell_not_one(self):
        self.assertEqual(rhythm.stack_box_excess_beams([(1289, 1653, (1289, 535, 364, 63), None)], self.TILE4[1], 1300)[0], None)
        self.assertEqual(rhythm.stack_box_excess_beams(self.TILE4[0], [], 1300)[0], None)
        self.assertEqual(rhythm.stack_box_excess_beams(self.TILE4[0], self.TILE4[1], 100)[0], None)   # x outside both


def _stem_levels_row(log, stem_row, top=(), bottom=(), unit=None):
    ends = {"top": {"left": [list(r) for r in top], "right": []}, "bottom": {"left": [], "right": [list(r) for r in bottom]}}
    return log.observe(CELL, Q.BEAM_STEM_LEVELS, max(len(top), len(bottom)), reader=READERS.CV_BEAM_LEVELS, frame="cell:0",
                       stem_row_id=stem_row.id, ends=ends)


def _thick(log, stroke, thickness_px):
    return log.observe(CELL, Q.BEAM_STROKE_INK, thickness_px / SP, reader=READERS.CV_BEAM_SHAPE, frame="cell:0",
                       beam_row_id=stroke.id, thickness_px=float(thickness_px), line_px=28.0, thickness_ratio=thickness_px / 28.0,
                       thickness_spaces=thickness_px / SP, sagitta_spaces=0.01,
                       end_stems=[{"found": True, "x": 250.0}, {"found": True, "x": 590.0}], columns=350, cover=1.0, band=[0.0, 1.0])


def _tile(log, *, page_runs=2, box_h=113, runs=None):
    """Three heads on down stems, one CV stroke (thickness 54) and a detector box over them of `box_h`; the stem-levels row of the
    FIRST head's stem says `page_runs` strokes at its bottom tip (None: no row at all)."""
    _staff_space(log, SP)
    g = _head(log, 0, (235, 355, 135, 142))
    _head(log, 1, (393, 348, 127, 118))
    _head(log, 2, (554, 354, 143, 125))
    stems = [_real_stem(log, (x, 383, 31, 820 - 383)) for x in (244, 400, 563)]
    cv = _stroke(log, (251, 757, 364, 63))
    _ink_row(log, cv, 2.8, 0.03, (True, True))
    _thick(log, cv, 54)
    _stroke(log, (150, 740, 696, box_h), cv=False)
    if page_runs:
        rr = runs or [(757, 777, 0.6, 3.0)] + [(700, 720, 0.6, 3.0)] * (page_runs - 1)
        _stem_levels_row(log, stems[0], bottom=rr[:page_runs])
    return g


def _dur(on, **kw):
    log = Log()
    g = _tile(log, **kw)
    with mock.patch.dict(os.environ, {FLAG: "1" if on else "0"}):
        adjudicate.run(log)
    return log.verdict(Q.DURATION, g)


class TestTheDecision(unittest.TestCase):

    def test_flag_OFF_the_double_beam_is_one_level_as_on_main(self):
        v = _dur(False)
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        self.assertNotIn("beam_stem_levels", v.detail)

    def test_flag_ON_page_two_strokes_and_the_tall_box_DECIDE_the_sixteenth_RED(self):
        v = _dur(True)
        self.assertEqual((v.outcome, v.value["beam_levels"], v.value["beats"]), (Outcome.DECIDED, 2, 0.25))
        d = v.detail["beam_stem_levels"]
        self.assertEqual((d["settled"], d["page_count"]), ("decided_two_witnesses", 2))
        self.assertGreater(d["box_margin"], 0)

    def test_flag_ON_the_page_alone_NARROWS_eighth_or_sixteenth_never_a_plain_eighth(self):
        v = _dur(True, box_h=72)       # the same box one beam tall for its slope
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertEqual(sorted(c.value["beam_levels"] for c in v.candidates), [1, 2])
        self.assertEqual(v.detail["beam_stem_levels"]["settled"], "narrowed_one_witness")

    def test_CONTROL_flag_ON_the_tall_box_alone_changes_nothing(self):
        v = _dur(True, page_runs=None)
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        self.assertNotIn("beam_stem_levels", v.detail)

    def test_CONTROL_flag_ON_one_stroke_at_the_tip_is_one_level(self):
        v = _dur(True, page_runs=1)
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))

    def test_flag_ON_a_stroke_twice_one_beam_thick_counts_as_two(self):
        v = _dur(True, page_runs=1, runs=[(700, 820, 1.2, 3.0)])      # 1.2 sp against a 0.54 sp beam: two fused
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 2))

    def test_flag_ON_a_third_run_thinner_than_0_7_of_a_beam_is_not_a_level_and_changes_nothing(self):
        # 2.140 tiles 1 and 4 (Brahms; Sean: sixteenths, we made 32nds): the third run read 0.62 of one beam (a staff line and a sliver)
        v = _dur(True, page_runs=1, runs=[(700, 745, 0.25, 3.0)])      # 0.25 sp vs a 0.54 sp beam: no stroke
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        v = _dur(True, page_runs=2, runs=[(757, 777, 0.6, 3.0), (700, 710, 0.3, 3.0)])
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 1))
        v = _dur(True, page_runs=2, runs=[(757, 777, 0.6, 3.0), (700, 720, 0.5, 3.0)])   # control: 0.5 sp is 0.93 of a beam
        self.assertEqual((v.outcome, v.value["beam_levels"]), (Outcome.DECIDED, 2))

    def test_flag_ON_a_box_that_clears_its_cut_by_less_than_the_near_miss_only_NARROWS(self):
        # round 2, Litolff (6,1,7,0) glyph 5: box excess 0.616 against 0.6, Sean read an eighth
        # tile box_h 113 -> 0.774 (margin 0.174, decides); the box that is 0.6x0.54+... is built by trimming its height to excess ~0.62
        v = _dur(True, box_h=105)
        d = v.detail["beam_stem_levels"]
        self.assertTrue(rhythm.BEAM_STACK_BOX_EXCESS_MIN <= d["box_excess_beams"] < rhythm.BEAM_STACK_BOX_EXCESS_MIN + rhythm.BEAM_STACK_BOX_NEAR_MISS, d)
        self.assertEqual(v.outcome, Outcome.NARROWED)
        self.assertTrue(d["box_near_miss"])

    def test_the_flag_defaults_OFF_and_only_an_on_word_enables(self):
        for word, on in (("", False), ("0", False), ("off", False), ("yess", False), ("1", True), ("true", True), ("on", True)):
            with mock.patch.dict(os.environ, {FLAG: word}):
                self.assertEqual(rhythm.beam_stem_levels_enabled(), on, word)
                self.assertEqual(gather.beam_stem_levels_gather_enabled(), on, word)
        env = {k: v for k, v in os.environ.items() if k != FLAG}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(rhythm.beam_stem_levels_enabled())


if __name__ == "__main__":
    unittest.main()
