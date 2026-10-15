"""ROADMAP 2.131 -- a staccato DOT and a staccatissimo TRIANGLE
(`OMR_STACCATISSIMO_SHAPE`, default OFF until Sean's tiles).

Numbers are real: Brahms 317803 (`benchmarks/omr-staccatissimo-2026-10/
FINDINGS.md`), height/width and the top/bottom-third ink widths of boxes read
off the 600 dpi page raster. Wedge `glyph/24/1/1/3/15` (articStaccatoAbove,
h/w 1.45, thirds 11/7, 0.48 sp tall), wedge `glyph/24/0/5/6/14`
(articStaccatoBelow, 1.40, 6/10, 0.42 sp), round dot `glyph/25/0/3/3/8`
(articStaccatoAbove, 1.0, 9/9, 0.31 sp), round dot `glyph/24/0/5/1/1`
(augmentationDot, 1.0, 11/11, 0.36 sp). RED first: every rule fires with the
flag on, is silent with it off, and every refusal has its control.
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import adjudicate
from tools.omr.staged import adjudicators  # noqa: F401
from tools.omr.staged import export as SX
from tools.omr.staged import gather
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Outcome, Q, READERS
from tools.omr.tests.test_staged_dot_role import (
    X, _mark, _note, _obs, _page, _staff_space, _vrd)

ON = {"OMR_STACCATISSIMO_SHAPE": "1"}
SPACE = 16.0
# (hw, top, bot, h_spaces)
WEDGE_ABOVE = (1.45, 11, 7, 0.48)        # point at the bottom, toward the head
WEDGE_BELOW = (1.40, 6, 10, 0.42)        # point at the top, toward the head
ROUND_STACC = (1.0, 9, 9, 0.31)
ROUND_DOT = (1.0, 11, 11, 0.36)


def _shape(log, glyph, m):
    hw, top, bot, hs = m
    log.observe(glyph, Q.MARK_SHAPE, hw, reader=READERS.CV_MARK_SHAPE,
                frame="cell:0", top=top, bot=bot, h_spaces=hs)


def _above(log, m, cls="articStaccatoAbove"):
    _staff_space(log)
    _note(log, 0)
    d = _mark(log, gi=1, cls=cls, x=X - 3, y=-17, w=6, h=9)
    _shape(log, d, m)
    return d


def _below(log, m, cls="articStaccatoBelow"):
    _staff_space(log)
    _note(log, 0)
    d = _mark(log, gi=1, cls=cls, x=X - 3, y=24, w=6, h=9)
    _shape(log, d, m)
    return d


def _role(log, d):
    adjudicate.run(log)
    return log.verdict(Q.DOT_ROLE, d)


class TestWedgeIsStaccatissimo(unittest.TestCase):
    @mock.patch.dict(os.environ, ON)
    def test_a_wedge_above_a_head_is_staccatissimo_not_staccato(self):
        log = Log()
        d = _above(log, WEDGE_ABOVE)
        r = _role(log, d)
        self.assertEqual((r.outcome, r.value), (Outcome.DECIDED, "staccatissimo"))
        self.assertEqual(r.detail["owner"], R.glyph(0, 0, 0, 0, 0).to_key())
        self.assertEqual(r.detail["candidates"], ["staccatissimo", "staccato"])

    @mock.patch.dict(os.environ, ON)
    def test_a_wedge_below_a_head_is_staccatissimo(self):
        log = Log()
        d = _below(log, WEDGE_BELOW)
        self.assertEqual(_role(log, d).value, "staccatissimo")

    def test_FLAG_OFF_the_same_wedge_stays_staccato(self):
        log = Log()
        d = _above(log, WEDGE_ABOVE)
        self.assertEqual(_role(log, d).value, "staccato")

    @mock.patch.dict(os.environ, ON)
    def test_CONTROL_a_round_staccato_stays_staccato(self):
        log = Log()
        d = _above(log, ROUND_STACC)
        self.assertEqual(_role(log, d).value, "staccato")

    @mock.patch.dict(os.environ, ON)
    def test_CONTROL_no_shape_row_changes_nothing(self):
        log = Log()
        _staff_space(log)
        _note(log, 0)
        d = _mark(log, gi=1, cls="articStaccatoAbove", x=X - 3, y=-17, w=6, h=9)
        self.assertEqual(_role(log, d).value, "staccato")

    @mock.patch.dict(os.environ, ON)
    def test_a_wedge_pointing_AWAY_from_the_head_is_not_called_anything(self):
        log = Log()
        d = _above(log, (1.45, 7, 11, 0.48))      # point at the top, mark above
        r = _role(log, d)
        self.assertEqual(r.outcome, Outcome.ABSTAINED)
        self.assertEqual(r.reason, "wedge_points_away")

    @mock.patch.dict(os.environ, ON)
    def test_a_speck_is_not_a_wedge(self):
        log = Log()
        d = _above(log, (1.5, 2, 1, 0.09))        # real junk box, 0.09 sp tall
        self.assertEqual(_role(log, d).value, "staccato")


class TestWedgeIsNeverAnAugmentationDot(unittest.TestCase):
    @mock.patch.dict(os.environ, ON)
    def test_a_wedge_boxed_as_a_dot_beside_a_head_is_not_augmentation(self):
        """A dot-class box level with a head, right of it: today the
        augmentation window takes it. A wedge there has no staccato window
        either, so it abstains -- never augmentation."""
        log = Log()
        _staff_space(log)
        _note(log, 0)
        d = _mark(log, gi=1, cls="augmentationDot", x=X + 12, y=3, w=6, h=9)
        _shape(log, d, (1.5, 11, 6, 0.55))
        r = _role(log, d)
        self.assertNotEqual(r.value, "augmentation")
        self.assertEqual(r.reason, "wedge_without_a_head")

    @mock.patch.dict(os.environ, ON)
    def test_a_dot_class_wedge_over_a_head_is_staccatissimo(self):
        log = Log()
        d = _above(log, WEDGE_ABOVE, cls="augmentationDot")
        self.assertEqual(_role(log, d).value, "staccatissimo")

    @mock.patch.dict(os.environ, ON)
    def test_CONTROL_a_round_dot_beside_a_head_is_still_augmentation(self):
        log = Log()
        _staff_space(log)
        _note(log, 0)
        d = _mark(log, gi=1, cls="augmentationDot", x=X + 12, y=3, w=6, h=6)
        _shape(log, d, ROUND_DOT)
        self.assertEqual(_role(log, d).value, "augmentation")


class TestMarkShapeGather(unittest.TestCase):
    """`gather.mark_shape` on synthetic rasters (0 = ink)."""
    def _img(self):
        return np.full((60, 60), 255, np.uint8)

    def test_a_round_dot_reads_one_and_equal_thirds(self):
        img = self._img()
        yy, xx = np.ogrid[:60, :60]
        img[(yy - 30) ** 2 + (xx - 30) ** 2 <= 36] = 0
        m = gather.mark_shape(img, (22, 22, 17, 17), 16.0)
        self.assertAlmostEqual(m["hw"], 1.0, delta=0.15)
        self.assertGreaterEqual(min(m["top"], m["bot"]) / max(m["top"], m["bot"]), 0.5)

    def test_a_triangle_pointing_down_reads_tall_with_a_narrow_bottom(self):
        img = self._img()
        for i, y in enumerate(range(20, 38)):       # 18 rows, 12 wide -> 2 wide
            half = max(1, 6 - i // 3)
            img[y, 30 - half:30 + half] = 0
        m = gather.mark_shape(img, (22, 18, 17, 22), 16.0)
        self.assertGreaterEqual(m["hw"], 1.3)
        self.assertLess(m["bot"], m["top"])

    def test_declined_where_unusable(self):
        self.assertIsNone(gather.mark_shape(None, (1, 1, 5, 5), 16.0))
        self.assertIsNone(gather.mark_shape(self._img(), (1, 1, 5, 5), 16.0))   # no ink
        self.assertIsNone(gather.mark_shape(self._img(), (1, 1, 5, 5), 0.0))

    def test_flag_off_by_default(self):
        self.assertFalse(gather.mark_shape_enabled())


class TestExportWritesStaccatissimo(unittest.TestCase):
    def test_a_staccatissimo_role_reaches_the_file_as_staccatissimo(self):
        page, note_sub = _page()
        dot_sub = "glyph/0/0/0/0/950"
        page["record"]["observations"].append(
            _obs(950, dot_sub, Q.AUG_DOT, [104.0, 46.0],
                detector_role="staccato", detector_class="articStaccatoAbove"))
        page["record"]["verdicts"].append(
            _vrd(950, dot_sub, Q.DOT_ROLE, "staccatissimo",
                reason="wedge_pointing_at_a_head",
                detail={"owner": note_sub, "articulation": "staccatissimo"}))
        xml, rep = SX.to_musicxml(page)
        self.assertIn("<staccatissimo/>", xml)
        self.assertNotIn("<staccato/>", xml)
        b = rep["dot_role_balance"]
        self.assertEqual(b["attached_staccatissimo_before_hold_out"], 1)
        self.assertTrue(b["balanced"], b)

    def test_CONTROL_a_staccato_role_still_writes_staccato(self):
        page, note_sub = _page()
        dot_sub = "glyph/0/0/0/0/951"
        page["record"]["observations"].append(
            _obs(951, dot_sub, Q.AUG_DOT, [104.0, 46.0],
                detector_role="staccato", detector_class="articStaccatoAbove"))
        page["record"]["verdicts"].append(
            _vrd(951, dot_sub, Q.DOT_ROLE, "staccato",
                reason="centred_and_offset_from_a_head",
                detail={"owner": note_sub, "articulation": "staccato"}))
        xml, rep = SX.to_musicxml(page)
        self.assertIn("<staccato/>", xml)
        self.assertNotIn("<staccatissimo/>", xml)


if __name__ == "__main__":
    unittest.main()
