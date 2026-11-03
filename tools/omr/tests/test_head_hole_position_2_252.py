"""ROADMAP 2.252 r4 -- a hollow head's staff position from its own HOLE where the detector box does not centre on it (STAGED GATHER,
flag `OMR_HEAD_HOLE_POSITION`, default OFF; `tools/omr/staged/head_hole_position.py`).

The cause (2.252 r4 census, Litolff p10-11): a tie's head box CLIPPED (the box holds the lower part of the oval) or TALL (head + stem)
reads its position at the box centre, a step off the head, and the tie is written as a slur or refused. The hole is at the head's
centre; the head's own ink centre must agree (a second reading that can only narrow).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import head_hole_position as HP

SP = 40.0            # one staff space (canonical == page here: upscale 1)
HALF = SP / 2.0
TOP = 200.0
LINES = [200, 240, 280, 320, 360]


def _staff(h=600, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in LINES:
        img[y - 2:y + 2, :] = 0
    return img


def _half(img, cx, cy):
    import cv2
    cv2.ellipse(img, (int(cx), int(cy)), (27, 20), -20, 0, 360, 0, -1)
    cv2.ellipse(img, (int(cx), int(cy)), (20, 8), -30, 0, 360, 255, -1)
    for y in LINES:
        if cy - 20 <= y <= cy + 20:
            img[y - 2:y + 2, int(cx) - 30:int(cx) + 30] = 0


def _stem_up(img, cx, cy):
    img[int(cy) - 140:int(cy), int(cx) + 25:int(cx) + 28] = 0


def _read(img, box):
    pos_box = ((box[1] + box[3]) / 2.0 - TOP) / HALF
    return HP.hole_position(img, box, HALF, TOP, LINES, pos_box, img, box, HALF), pos_box


class TestHolePosition(unittest.TestCase):
    def test_clipped_box_reads_the_hole(self):
        img = _staff()
        _half(img, 200, 260)                       # a head in the second space: position 3
        res, pos_box = _read(img, (172, 262, 228, 290))    # the box holds the lower part of the oval only
        self.assertEqual(int(round(pos_box)), 4)
        self.assertIsNotNone(res["position"], res)
        self.assertEqual(int(round(res["position"])), 3)

    def test_tall_box_with_stem_reads_the_hole(self):
        img = _staff()
        _half(img, 200, 300)                       # third space: position 5
        _stem_up(img, 200, 300)
        res, pos_box = _read(img, (172, 155, 230, 322))    # head and stem in one box, its centre on the stem
        self.assertNotEqual(int(round(pos_box)), 5)
        self.assertEqual(int(round(res["position"])), 5, res)

    def test_head_on_a_line_reads_the_line(self):
        img = _staff()
        _half(img, 200, 240)                       # on the second line: position 2
        res, pos_box = _read(img, (172, 242, 228, 268))    # clipped below
        self.assertEqual(int(round(pos_box)), 3)
        self.assertEqual(int(round(res["position"])), 2, res)

    def test_centred_box_moves_nothing(self):
        img = _staff()
        _half(img, 200, 260)
        res, _ = _read(img, (172, 240, 228, 280))
        self.assertIsNone(res["position"])
        self.assertEqual(res["why"], "same_position")

    def test_black_head_has_no_hole(self):
        import cv2
        img = _staff()
        cv2.ellipse(img, (200, 260), (27, 20), -20, 0, 360, 0, -1)
        res, _ = _read(img, (172, 255, 228, 282))
        self.assertIsNone(res["position"])
        self.assertEqual(res["why"], "holes:0")

    def test_two_holes_are_not_read(self):
        img = _staff()
        _half(img, 200, 260)
        _half(img, 200, 300)
        res, _ = _read(img, (172, 230, 228, 330))
        self.assertIsNone(res["position"])
        self.assertTrue(res["why"].startswith("holes:"), res)

    def test_far_head_never_moves(self):
        img = np.full((700, 400), 255, np.uint8)
        for y in LINES:
            img[y - 2:y + 2, :] = 0
        _half(img, 200, 460)                       # far below the staff: position 13
        res, _ = _read(img, (172, 465, 228, 492))
        self.assertIsNone(res["position"])
        self.assertEqual(res["why"], "off_staff")

    def test_a_narrow_ring_is_not_a_head(self):
        """r4 move sheet: a narrow mark holding a hole (a 'p'-like curl, 0.76 sp wide) is refused by its ink width."""
        import cv2
        img = _staff()
        cv2.ellipse(img, (200, 260), (10, 20), 0, 0, 360, 0, -1)
        cv2.ellipse(img, (200, 260), (5, 10), 0, 0, 360, 255, -1)
        res, pos_box = _read(img, (188, 262, 212, 290))
        self.assertIsNone(res["position"])
        self.assertIn(res["why"], ("ink_too_narrow", "ink_not_one_head", "holes:0"), res)

    def test_no_raster(self):
        res = HP.hole_position(None, (0, 0, 10, 10), HALF, TOP, LINES, 3.0, None, None, None)
        self.assertEqual(res["why"], "no_raster")

    def test_ink_must_agree(self):
        img = _staff()
        _half(img, 200, 260)
        pos_box = 4.0
        # the page witness is a blank raster: the ink is unread, nothing moves (the witness can only narrow)
        blank = np.full_like(img, 255)
        res = HP.hole_position(img, (172, 255, 228, 282), HALF, TOP, LINES, pos_box, blank, (172, 255, 228, 282), HALF)
        self.assertIsNone(res["position"])


class TestFlag(unittest.TestCase):
    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(HP.ENV, None)
            self.assertFalse(HP.enabled())
        with mock.patch.dict(os.environ, {HP.ENV: "1"}):
            self.assertTrue(HP.enabled())

    def test_regular_classes_only(self):
        self.assertTrue(HP.is_candidate("noteheadHalf"))
        self.assertTrue(HP.is_candidate("noteheadHalfInSpace"))
        self.assertTrue(HP.is_candidate("noteheadBlackInSpace"))     # the detector calls hollow heads black; the hole decides
        self.assertFalse(HP.is_candidate("noteheadWhole"))
        self.assertFalse(HP.is_candidate("noteheadHalfSmall"))


if __name__ == "__main__":
    unittest.main()
