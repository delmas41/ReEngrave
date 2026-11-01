"""ROADMAP 2.248 -- a notehead's extent and centre from its own ink (STAGED GATHER, flag OMR_HEAD_INK_EXTENT, default OFF).

Painted heads on a 5-line staff (space 40 px, page frame = cell frame): a detector box cut short of its head is grown to the
whole head and its position read from the ink; a head beside a stem, on a ledger, or stacked with a chord-mate is not grown into
them; with the flag off (the control) the box centre stands.
"""
from __future__ import annotations

import os
import types
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather, head_extent
from tools.omr.staged import record as R
from tools.omr.staged.record import Log, Q
from tools.omr.types import MeasureCell

S = 40.0
LINES = (100.0, 140.0, 180.0, 220.0, 260.0)     # half step 20 px; position = (y - 100) / 20


def _paper(h=400, w=400):
    img = np.full((h, w), 255, np.uint8)
    for y in LINES:
        img[int(y) - 1:int(y) + 2, 20:380] = 0
    return img


def _head(img, cx, cy, w=1.3 * S, h=1.0 * S):
    yy, xx = np.mgrid[0:img.shape[0], 0:img.shape[1]]
    img[((xx - cx) / (w / 2)) ** 2 + ((yy - cy) / (h / 2)) ** 2 <= 1.0] = 0


def _det(name, box):
    x0, y0, x1, y1 = box
    return types.SimpleNamespace(smufl_name=name, x_canonical=x0, y_canonical=y0, width_canonical=x1 - x0,
                                 height_canonical=y1 - y0, x_center=(x0 + x1) / 2.0, y_center=(y0 + y1) / 2.0)


def _cell(img):
    c = MeasureCell(page_index=0, system_index=0, staff_index=0, measure_index=0, image=img, image_no_staff=img,
                    bbox_page_px=(0, 0, img.shape[1], img.shape[0]), staff_line_ys_canonical=list(LINES), upscale_factor=1.0)
    c.__dict__["binary"] = img
    return c


def _position(img, dets, on=True, gi=0):
    pws = types.SimpleNamespace(page=types.SimpleNamespace(binary=img))
    log = Log()
    det = {R.cell(0, 0, 0, 0).to_key(): dets}
    with mock.patch.dict(os.environ, {head_extent.ENV: "1" if on else "0"}):
        gather.gather_notehead_positions(log, [_cell(img)], {0: (0, 0)}, det, pws=pws)
    return log.rows(Q.NOTEHEAD_STAFF_POSITION, R.glyph(0, 0, 0, 0, gi))[-1]


class TestCutShortBoxGrownToTheHead(unittest.TestCase):

    def setUp(self):
        self.img = _paper()
        _head(self.img, 200.0, 200.0)                    # a head in the space below the middle line: position 5
        # the detector box holds only the upper half of the head: centre 185 -> position 4.25 -> rounds to 4
        self.box = (174.0, 180.0, 226.0, 190.0)

    def test_the_extent_is_the_whole_head(self):
        got = head_extent.ink_extent(self.img, self.box, S)
        self.assertIsNone(got["why"])
        x0, y0, x1, y1 = got["extent"]
        self.assertLessEqual(y0, 182.0)
        self.assertGreaterEqual(y1, 218.0)

    def test_the_position_is_read_from_the_ink(self):
        pos = _position(self.img, [_det("noteheadBlackInSpace", self.box)])
        self.assertEqual(int(round(float(pos.value))), 5)
        self.assertAlmostEqual(pos.detail["detector_position_float"], 4.25, delta=0.01)
        self.assertIn("from_head_ink", pos.detail)

    def test_control_flag_off_the_box_centre_stands(self):
        pos = _position(self.img, [_det("noteheadBlackInSpace", self.box)], on=False)
        self.assertEqual(int(round(float(pos.value))), 4)
        self.assertNotIn("from_head_ink", pos.detail or {})

    def test_a_whole_box_moves_nothing(self):
        pos = _position(self.img, [_det("noteheadBlackInSpace", (174.0, 180.0, 226.0, 220.0))])
        self.assertAlmostEqual(float(pos.value), 5.0, delta=1e-6)
        self.assertNotIn("from_head_ink", pos.detail or {})


class TestNotGrownIntoNeighbours(unittest.TestCase):

    def test_a_stem_is_not_the_head(self):
        img = _paper()
        _head(img, 200.0, 200.0)
        img[60:200, 224:228] = 0                          # an up-stem on the head's right, 3.5 sp tall
        got = head_extent.ink_extent(img, (174.0, 180.0, 226.0, 190.0), S)
        self.assertIsNone(got["why"])
        self.assertGreaterEqual(got["extent"][1], 175.0)  # the stem's rows are not the head's
        self.assertLessEqual(got["extent"][3] - got["extent"][1], 1.35 * S)

    def test_a_ledger_is_not_the_head(self):
        img = _paper()
        _head(img, 200.0, 300.0)                          # below the staff, on a ledger at 300
        img[299:302, 160:240] = 0                          # ledger 2.0 sp long
        got = head_extent.ink_extent(img, (174.0, 285.0, 226.0, 300.0), S)
        self.assertIsNone(got["why"])
        x0, y0, x1, y1 = got["extent"]
        self.assertGreater(x0, 165.0)
        self.assertLess(x1, 235.0)

    def test_a_chord_mate_stops_the_move(self):
        img = _paper()
        _head(img, 200.0, 200.0)
        _head(img, 200.0, 240.0)                          # the next head of a chord, a third lower, touching
        mate = (174.0, 220.0, 226.0, 260.0)
        box = (174.0, 180.0, 226.0, 196.0)
        got = head_extent.ink_extent(img, box, S, other_heads=[mate])
        self.assertIsNone(got["why"])
        self.assertLessEqual(got["extent"][3], 222.0)      # its own head only, never the mate's
        pos = _position(img, [_det("noteheadBlackInSpace", box), _det("noteheadBlackInSpace", mate)])
        self.assertEqual(int(round(float(pos.value))), 5)
        # a mate box reaching into this head's ink: the ink is shared, nothing moves
        wide_mate = (174.0, 205.0, 226.0, 260.0)
        self.assertEqual(head_extent.ink_extent(img, box, S, other_heads=[wide_mate])["why"], "runs_into_another_head")
        pos = _position(img, [_det("noteheadBlackInSpace", box), _det("noteheadBlackInSpace", wide_mate)])
        self.assertNotIn("from_head_ink", pos.detail or {})

    def test_two_heads_tall_ink_is_not_one_head(self):
        img = _paper()
        _head(img, 200.0, 200.0)
        _head(img, 200.0, 225.0)                          # a second, unboxed, half a space apart
        got = head_extent.ink_extent(img, (174.0, 180.0, 226.0, 195.0), S)
        self.assertIsNotNone(got["why"])


class TestRound2SeansTiles(unittest.TestCase):
    """r2: Sean's tile 2 (a ledger stub touching the head's bottom was taken as head ink) and tile 7 (a far head on the
    boundary); far heads are left to their ledger count (page-facts, DECIDIONS 2026-10-27)."""

    def test_a_ledger_stub_under_the_head_is_not_the_head(self):
        img = _paper()
        _head(img, 200.0, 300.0)                          # below the staff, in the space above a ledger at 321
        img[314:321, 168:232] = 0                          # a short ledger (1.6 sp) merged with the head's bottom, out both sides
        got = head_extent.ink_extent(img, (174.0, 280.0, 226.0, 305.0), S)
        self.assertGreater(got["line_rows_stripped"], 0)
        self.assertLessEqual(got["extent"][3], 321.0)
        self.assertGreater(got["extent"][0], 168.0)

    def test_control_a_head_without_a_ledger_keeps_its_rows(self):
        img = _paper()
        _head(img, 200.0, 300.0)
        got = head_extent.ink_extent(img, (174.0, 280.0, 226.0, 305.0), S)
        self.assertEqual(got.get("line_rows_stripped"), 0)

    def test_a_far_head_is_never_moved_by_its_ink(self):
        # positions above -1 or below 9 are placed by their ledger lines only
        self.assertIsNone(head_extent.ink_position(10.3, (0, 290, 10, 300), (0, 290, 10, 320), 20.0))
        self.assertIsNone(head_extent.ink_position(-2.3, (0, 50, 10, 60), (0, 40, 10, 60), 20.0))
        # control: the same move inside the staff happens
        self.assertIsNotNone(head_extent.ink_position(4.3, (0, 180, 10, 190), (0, 180, 10, 210), 20.0))

    def test_a_boundary_ink_centre_decides_nothing(self):
        # box 4.2 (rounds 4), ink 4.49 / 4.51: on the half-way point -> no move
        self.assertIsNone(head_extent.ink_position(4.2, (0, 180, 10, 190), (0, 180, 10, 202.2), 20.0))
        self.assertIsNotNone(head_extent.ink_position(4.2, (0, 180, 10, 190), (0, 180, 10, 212), 20.0))


class TestInkPosition(unittest.TestCase):

    def test_moves_only_when_the_rounding_changes(self):
        self.assertIsNone(head_extent.ink_position(5.1, (0, 180, 10, 220), (0, 182, 10, 222), 20.0))
        self.assertAlmostEqual(head_extent.ink_position(4.25, (0, 180, 10, 190), (0, 180, 10, 220), 20.0), 5.0)

    def test_default_off(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(head_extent.ENV, None)
            self.assertFalse(head_extent.enabled())


if __name__ == "__main__":
    unittest.main()
