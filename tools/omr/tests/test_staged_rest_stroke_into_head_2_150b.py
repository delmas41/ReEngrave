"""ROADMAP 2.150b -- a rest stands free: a rest box whose ink is one thin stroke running into a notehead is a stem.

STAGED. GATHER `gather.gather_rest_ink_contact` (Q.REST_INK_CONTACT, off the staff-erased raster, via the pure
`rest_ink.measure`) and ADJUDICATE `family_precision.adjudicate_rest_is_not_a_rest` (reason `rest_stroke_into_a_head`),
flag `OMR_REST_STROKE_INTO_HEAD` (default ON since 2026-10-16; only `0/false/no/off` disables).

CONVENTION ASSUMED: a rest is a free-standing glyph (Gould, Behind Bars); a thin stroke of a few spaces ending in a
solid head is a stem. WHAT WOULD FALSIFY IT: a print-confirmed rest whose box shows the thin stroke AND a head's ink
in contact. NOT CONFIRMED by Sean beyond the 21 tiles of 2.150; the cuts (1.0 / 0.9 / 0.4) are read off them.

Note on order: the measurement was prototyped against the 21 printed tiles first, then these tests were written;
`TestTheTestsCanFail` proves each refusal test goes RED when its cut is broken.
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather, margins, rest_ink
from tools.omr.staged.adjudicators import family_precision as FP
from tools.omr.staged.record import Log, Observation, Outcome, Q, READERS
from tools.omr.tests.test_staged_family_refusals import _box, _page_box_at_step, _staff_geometry
from tools.omr.tests.test_staged_rest_placement_2_33 import _run

SP = 20  # staff space, px, for the synthetic masks


def _blank():
    return np.zeros((300, 300), bool)


def _ellipse(m, cx, cy, rx, ry):
    yy, xx = np.ogrid[:m.shape[0], :m.shape[1]]
    m |= ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1.0


def _stem_and_head(m, x=150):
    """A 3-px stem 3 spaces tall with a solid head (1.3 x 1.0 spaces) at its bottom end."""
    m[100:160, x:x + 3] = True
    _ellipse(m, x - 10, 160, 13, 10)
    return (x - 4, 100, x + 8, 160)               # the box a detector draws on the stem


def _free_quarter_rest(m, x=150):
    """A thick Z-shaped glyph ~1 space wide, 3 spaces tall, no thin stroke: thick lines (0.7 space)."""
    import cv2
    img = m.astype(np.uint8)
    for a, b in (((x, 100), (x + 20, 100)), ((x + 20, 100), (x + 2, 130)), ((x + 2, 130), (x + 18, 140)),
                 ((x + 18, 140), (x + 4, 160))):
        cv2.line(img, a, b, 1, 14)
    m[:] = img > 0
    return (x - 8, 96, x + 28, 168)


class TestMeasure(unittest.TestCase):

    def test_a_stem_running_into_its_head_has_a_thin_stroke_and_head_evidence(self):
        m = _blank()
        box = _stem_and_head(m)
        got = rest_ink.measure(m, box, [("h", "noteheadBlackOnLine", 130, 150, 156, 171)], SP)
        self.assertGreaterEqual(got["thin_run_sp"], 1.0)
        self.assertTrue(got["blob_sp"] >= 0.9 or got["head_ink_sp2"] >= 0.4, got)

    def test_CONTROL_a_free_rest_beside_a_head_box_has_no_ink_contact(self):
        """A twin head box standing beside a free rest (10 of 32 real quarter rests had one) owns none of its ink."""
        m = _blank()
        box = _free_quarter_rest(m)
        _ellipse(m, 230, 160, 13, 10)                 # a head 2 spaces to the right, NOT touching
        got = rest_ink.measure(m, box, [("h", "noteheadBlackOnLine", 217, 150, 243, 171)], SP)
        self.assertEqual(got["head_ink_sp2"], 0.0)
        self.assertLess(got["thin_run_sp"], 1.0)

    def test_CONTROL_a_head_in_contact_with_the_rest_gives_ink_but_still_no_thin_stroke(self):
        """A head touching a free rest is head evidence only; the stroke gate (thin_run) keeps the rest."""
        m = _blank()
        box = _free_quarter_rest(m)
        _ellipse(m, 190, 160, 13, 10)                 # touches the rest's tail
        got = rest_ink.measure(m, box, [("h", "noteheadBlackOnLine", 177, 150, 203, 171)], SP)
        self.assertLess(got["thin_run_sp"], 1.0)

    def test_declines_without_a_mask_or_staff_space_or_ink(self):
        m = _blank()
        self.assertIsNone(rest_ink.measure(None, (0, 0, 10, 10), [], SP))
        self.assertIsNone(rest_ink.measure(m, (140, 100, 160, 160), [], 0))
        self.assertIsNone(rest_ink.measure(m, (140, 100, 160, 160), [], SP))   # no ink under the box

    def test_the_head_box_ink_is_outside_the_rest_box_only(self):
        """Ink inside the (grown) rest box is not 'in the head box': a head box lying on the rest box's own ink
        measures nothing unless the piece runs on beyond the box."""
        m = _blank()
        box = _free_quarter_rest(m)
        got = rest_ink.measure(m, box, [("h", "noteheadBlackOnLine", box[0], box[1], box[2], box[3])], SP)
        self.assertEqual(got["head_ink_sp2"], 0.0)


def _decide(cls, row, env, *, width=45.0):
    log = Log()
    _staff_geometry(log)
    g = _box(log, 0, cls, quantity=Q.REST, page_box=_page_box_at_step(4.0, x0=500.0, x1=500.0 + width / 5.0,
                                                                         thickness=60.0),
             w_c=width, h_c=300.0, x_c=200.0, y_c=100.0)
    if row is not None:
        log.observe(g, Q.REST_INK_CONTACT, row["thin_run_sp"], reader=READERS.CV_REST_INK_CONTACT, frame="cell:0",
                    **row)
    with mock.patch.dict(os.environ, env, clear=False):
        if not env:
            os.environ.pop("OMR_REST_STROKE_INTO_HEAD", None)
        _run(log, Q.REST_IS_NOT_A_REST)
    return log.verdict(Q.REST_IS_NOT_A_REST, g)


ON = {"OMR_REST_STROKE_INTO_HEAD": "1"}
STEM = {"thin_run_sp": 2.5, "thin_beyond_sp": 0.0, "blob_sp": 1.2, "head_ink_sp2": 1.0, "box_height_sp": 3.1,
        "head": 3}
STEM_HEAD_BOX_ONLY = {"thin_run_sp": 2.9, "thin_beyond_sp": 0.1, "blob_sp": 0.0, "head_ink_sp2": 1.4,
                      "box_height_sp": 1.8, "head": 7}
FREE = {"thin_run_sp": 0.5, "thin_beyond_sp": 0.0, "blob_sp": 0.29, "head_ink_sp2": 0.0, "box_height_sp": 2.9,
        "head": None}


class TestRestStrokeIntoHead(unittest.TestCase):

    def test_a_stem_boxed_as_a_rest_is_refused_with_its_margin(self):
        v = _decide("restQuarter", STEM, ON)
        self.assertEqual(v.outcome, Outcome.DECIDED)
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_stroke_into_a_head")
        # binding one of {stroke 2.5/1.0-1=1.5, head max(1.2/0.9-1=0.333, 1.0/0.4-1=1.5)} = 1.5 -> min = 1.5
        self.assertAlmostEqual(v.margin, 1.5, places=3)
        self.assertEqual(v.detail["stroke_into_head"]["thin_run_sp"], 2.5)

    def test_a_stem_whose_head_is_only_a_neighbouring_box_is_refused(self):
        v = _decide("restQuarter", STEM_HEAD_BOX_ONLY, ON)
        self.assertEqual(v.reason, "rest_stroke_into_a_head")

    def test_an_eighth_rest_class_is_measured_too(self):
        v = _decide("rest8th", STEM, ON)
        self.assertEqual(v.reason, "rest_stroke_into_a_head")

    def test_CONTROL_a_free_standing_quarter_rest_is_kept_and_carries_its_margin(self):
        v = _decide("restQuarter", FREE, ON)
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")
        self.assertLess(v.detail["stroke_into_head"]["margin"], 0.0)

    def test_CONTROL_a_narrow_real_rest_is_kept(self):
        """Tile 11's shape of problem: a rest box only 0.45 spaces wide (the width floor refuses it) whose ink is not
        a stroke into a head (a free rest: short thin run, no blob, no head ink) is kept."""
        v = _decide("restQuarter", FREE, ON, width=45.0)
        self.assertIs(v.value, False)

    def test_CONTROL_a_thin_stroke_with_no_head_is_kept(self):
        """A barline-like stroke alone is not 'into a notehead': this rule leaves it to the others (rule 8)."""
        row = dict(STEM, blob_sp=0.0, head_ink_sp2=0.0)
        v = _decide("restQuarter", row, ON)
        self.assertIs(v.value, False)

    def test_CONTROL_a_head_in_contact_but_no_thin_stroke_is_kept(self):
        row = dict(FREE, head_ink_sp2=1.0, blob_sp=1.0)
        v = _decide("restQuarter", row, ON)
        self.assertIs(v.value, False)

    def test_default_is_ON_and_refuses_the_stem(self):
        """Sean 2026-10-16: 'Land the 2.150b ink test ... ON': no env var at all means ON."""
        v = _decide("restQuarter", STEM, {})
        self.assertIs(v.value, True)
        self.assertEqual(v.reason, "rest_stroke_into_a_head")
        self.assertTrue(rest_ink.enabled())

    def test_CONTROL_flag_off_keeps_everything(self):
        v = _decide("restQuarter", STEM, {"OMR_REST_STROKE_INTO_HEAD": "0"})
        self.assertIs(v.value, False)
        self.assertEqual(v.reason, "rest")

    def test_CONTROL_an_off_word_keeps_everything(self):
        v = _decide("restQuarter", STEM, {"OMR_REST_STROKE_INTO_HEAD": "off"})
        self.assertIs(v.value, False)

    def test_CONTROL_no_row_declines(self):
        """No raster / no staff space: GATHER filed nothing; the rule declines, never refuses (rule 8)."""
        v = _decide("restQuarter", None, ON)
        self.assertNotEqual(v.reason, "rest_stroke_into_a_head")

    def test_the_reason_is_classified_in_the_margin_registry(self):
        problems, _notes = margins.check_margins()
        self.assertFalse([p for p in problems if "rest_stroke_into_a_head" in str(p)], problems)
        self.assertIn("rest_stroke_into_a_head", margins.PARTIAL["adjudicate_rest_is_not_a_rest"])


class TestTheTestsCanFail(unittest.TestCase):
    """A control must be able to fail: break each cut and the verdict flips."""

    def test_raising_the_stroke_cut_above_a_stem_keeps_it(self):
        with mock.patch.object(FP, "REST_STROKE_MIN_SP", 9.0):
            self.assertIs(_decide("restQuarter", STEM, ON).value, False)

    def test_lowering_the_stroke_cut_to_zero_refuses_a_free_rest_with_a_head(self):
        row = dict(FREE, head_ink_sp2=1.0, blob_sp=1.0)
        with mock.patch.object(FP, "REST_STROKE_MIN_SP", 0.1):
            self.assertIs(_decide("restQuarter", row, ON).value, True)

    def test_raising_the_head_cuts_keeps_a_stem(self):
        with mock.patch.object(FP, "REST_HEAD_BLOB_MIN_SP", 9.0), mock.patch.object(FP, "REST_HEAD_INK_MIN_SP2", 9.0):
            self.assertIs(_decide("restQuarter", STEM, ON).value, False)


def _rows(log):
    return [r for r in log.all_rows() if r.quantity == Q.REST_INK_CONTACT and isinstance(r, Observation)]


def _abstained(log):
    return [r for r in log.all_rows() if r.quantity == Q.REST_INK_CONTACT and not isinstance(r, Observation)]


def _cell(img, lines, up=1.0):
    return types.SimpleNamespace(page_index=0, system_index=0, staff_index=0, measure_index=0,
                                 image_no_staff=np.where(img, 0, 255).astype(np.uint8),
                                 staff_line_ys_canonical=lines, upscale_factor=up, bbox_page_px=[0, 0, 300, 300])


def _det(cls, x0, y0, x1, y1):
    return types.SimpleNamespace(smufl_name=cls, x_canonical=x0, y_canonical=y0, width_canonical=x1 - x0,
                                 height_canonical=y1 - y0)


class TestGather(unittest.TestCase):
    LINES = [60, 80, 100, 120, 140]

    def _run(self, img, dets, env=ON):
        from tools.omr.staged import record as R
        log = Log()
        c = _cell(img, self.LINES)
        sub = R.cell(0, 0, 0, 0)
        with mock.patch.dict(os.environ, env, clear=False):
            if not env:
                os.environ.pop("OMR_REST_STROKE_INTO_HEAD", None)
            gather.gather_rest_ink_contact(log, [c], {0: (0, 0)}, {sub.to_key(): dets})
        return log

    def test_files_the_row_for_a_stem_boxed_as_a_rest(self):
        m = _blank()
        box = _stem_and_head(m)
        log = self._run(m, [_det("restQuarter", *box), _det("noteheadBlackOnLine", 130, 150, 156, 171)])
        rows = _rows(log)
        self.assertEqual(len(rows), 1)
        d = rows[0].detail
        self.assertGreaterEqual(d["thin_run_sp"], 1.0)
        self.assertTrue(d["blob_sp"] >= 0.9 or d["head_ink_sp2"] >= 0.4)

    def test_CONTROL_a_free_rest_files_no_contact(self):
        m = _blank()
        box = _free_quarter_rest(m)
        _ellipse(m, 230, 160, 13, 10)
        log = self._run(m, [_det("restQuarter", *box), _det("noteheadBlackOnLine", 217, 150, 243, 171)])
        d = _rows(log)[0].detail
        self.assertEqual(d["head_ink_sp2"], 0.0)
        self.assertLess(d["thin_run_sp"], 1.0)

    def test_CONTROL_flag_off_files_nothing(self):
        m = _blank()
        box = _stem_and_head(m)
        log = self._run(m, [_det("restQuarter", *box)], env={"OMR_REST_STROKE_INTO_HEAD": "0"})
        self.assertEqual(_rows(log), [])

    def test_CONTROL_no_raster_abstains_never_defaults(self):
        from tools.omr.staged import record as R
        log = Log()
        c = _cell(_blank(), self.LINES)
        c.image_no_staff = None
        sub = R.cell(0, 0, 0, 0)
        with mock.patch.dict(os.environ, ON, clear=False):
            gather.gather_rest_ink_contact(log, [c], {0: (0, 0)}, {sub.to_key(): [_det("restQuarter", 1, 1, 9, 30)]})
        self.assertEqual(_rows(log), [])
        self.assertEqual(len(_abstained(log)), 1)


if __name__ == "__main__":
    unittest.main()
