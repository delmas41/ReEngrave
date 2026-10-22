"""ROADMAP 2.138 (`OMR_WEDGE_RESCUE`, default ON since 2026-10-15): a staccatissimo wedge the production detector boxed BELOW the 0.25 floor.

STAGED GATHER only. `gather.gather_wedge_rescue` re-runs the same detector at `WEDGE_RESCUE_FLOOR`, mark classes only, and keeps a
box only where (a) production has no box on that mark, (b) its staff-free ink is a wedge by 2.131's cut, (c) a production head
stands in its staccato window on the side the point faces. A round dot, a wedge pointing away from the only head, a duplicate of a
production box and a box above the floor are each REFUSED (the controls that can fail). Sean's page facts: the measured boxes are
`24/0/1/4/15`, `24/0/1/4/17`, `24/1/2/3/25` (benchmarks/omr-staccatissimo-2026-10/FINDINGS.md Sec.9).
"""
from __future__ import annotations

import os
import unittest
from unittest import mock

import numpy as np

from tools.omr.staged import gather
from tools.omr.staged.record import ABSTAIN, Log, Q, READERS, cell as R_cell

LINES = [20.0, 40.0, 60.0, 80.0, 100.0]      # space 20 px
H, W = 200, 140
# the head: x 50, y 100, 26 x 20 -> centre (63, 110)


class _Det:
    def __init__(self, name, conf, x, y, w, h, category="articulations"):
        self.smufl_name, self.confidence, self.category = name, conf, category
        self.x_canonical, self.y_canonical, self.width_canonical, self.height_canonical = x, y, w, h


class _Cell:
    def __init__(self, img):
        self.image_no_staff = img
        self.staff_line_ys_canonical = list(LINES)
        self.page_index, self.staff_index, self.measure_index = 0, 0, 0
        self.bbox_page_px, self.upscale_factor = None, None


class _Detector:
    def __init__(self, results):
        self.results, self.calls = list(results), []

    def detect(self, cell, conf_threshold=0.25, imgsz=None):
        self.calls.append(conf_threshold)
        return list(self.results)


def _img(shape):
    """A 14-row mark whose box is x 57..69 (12 wide), y 140..154, ink 0 on white."""
    img = np.full((H, W), 255, dtype=np.uint8)
    for i, y in enumerate(range(141, 153)):
        if shape == "wedge_tip_up":          # narrow at the top, wide at the bottom
            half = 1 + int(i * 3 / 11)
        elif shape == "wedge_tip_down":      # wide at the top, narrow at the bottom
            half = 4 - int(i * 3 / 11)
        else:                                # a round-ish dot: equal ends, as wide as tall
            half = 6
        img[y, 63 - half:63 + half] = 0
    if shape == "dot":
        img[:, :] = 255
        img[143:153, 58:68] = 0
    return img


def _mark(conf=0.14, name="articStaccatissimoBelow"):
    return _Det(name, conf, 57.0, 140.0, 12.0, 14.0)


def _run(img, results, *, existing_extra=()):
    head = _Det("noteheadBlackInSpace", 0.9, 50.0, 100.0, 26.0, 20.0, category="noteheads")
    detections = {R_cell(0, 0, 0, 0).to_key(): [head, *existing_extra]}
    log = Log()
    det = _Detector(results)
    gather.gather_wedge_rescue(log, [_Cell(img)], {0: (0, 0)}, detections, detector=det)
    return log, detections, det


def _wedge_rows(log):
    return [r for r in log.all_rows() if getattr(r, "reader", None) == READERS.RESCUE_WEDGE] \
        if hasattr(log, "all_rows") else [r for r in list(log._obs.values()) + list(log._abs.values())
                                         if r.reader == READERS.RESCUE_WEDGE]


class TestWedgeRescue(unittest.TestCase):
    def test_flag_is_on_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(gather.WEDGE_RESCUE_ENV, None)
            self.assertTrue(gather.wedge_rescue_enabled())
        for off in ("0", "false", "no", "off", ""):
            with mock.patch.dict(os.environ, {gather.WEDGE_RESCUE_ENV: off}):
                self.assertFalse(gather.wedge_rescue_enabled())
        with mock.patch.dict(os.environ, {gather.WEDGE_RESCUE_ENV: "1"}):
            self.assertTrue(gather.wedge_rescue_enabled())

    def test_wedge_pointing_at_the_head_above_is_kept(self):
        log, dets, det = _run(_img("wedge_tip_up"), [_mark()])
        key = R_cell(0, 0, 0, 0).to_key()
        self.assertEqual(len(dets[key]), 2)                       # the head + the rescued mark, appended in place
        self.assertEqual(det.calls, [gather.WEDGE_RESCUE_FLOOR])
        box = [o for o in log._obs.values() if o.quantity == Q.GLYPH_BOX and o.reader == READERS.RESCUE_WEDGE]
        self.assertEqual(len(box), 1)
        self.assertEqual(box[0].detail["witness_head"], 0)
        self.assertEqual(box[0].detail["mark_tip"], "top")        # the point faces the head above it

    def test_round_dot_is_refused(self):
        log, dets, _ = _run(_img("dot"), [_mark(name="articStaccatoBelow")])
        self.assertEqual(len(dets[R_cell(0, 0, 0, 0).to_key()]), 1)
        ab = [a for a in log._abs.values() if a.reader == READERS.RESCUE_WEDGE]
        self.assertEqual([a.detail["why"] for a in ab], ["not_a_wedge"])
        self.assertEqual(ab[0].reason, ABSTAIN.RESCUE_UNGUIDED)

    def test_wedge_pointing_away_from_the_only_head_is_refused(self):
        log, dets, _ = _run(_img("wedge_tip_down"), [_mark()])
        self.assertEqual(len(dets[R_cell(0, 0, 0, 0).to_key()]), 1)
        ab = [a for a in log._abs.values() if a.reader == READERS.RESCUE_WEDGE]
        self.assertEqual([a.detail["why"] for a in ab], ["no_head_on_the_points_side"])

    def test_a_mark_production_already_boxed_is_not_boxed_again(self):
        prod = _Det("articStaccatoBelow", 0.6, 57.0, 140.0, 12.0, 14.0)
        log, dets, _ = _run(_img("wedge_tip_up"), [_mark()], existing_extra=(prod,))
        self.assertEqual(len(dets[R_cell(0, 0, 0, 0).to_key()]), 2)   # head + production mark, nothing added
        self.assertEqual(_wedge_rows(log), [])

    def test_a_box_at_or_above_the_production_floor_is_left_to_production(self):
        _, dets, _ = _run(_img("wedge_tip_up"), [_mark(conf=0.3)])
        self.assertEqual(len(dets[R_cell(0, 0, 0, 0).to_key()]), 1)

    def test_two_boxes_on_one_mark_keep_one(self):
        _, dets, _ = _run(_img("wedge_tip_up"), [_mark(conf=0.1), _mark(conf=0.2, name="articStaccatoBelow")])
        self.assertEqual(len(dets[R_cell(0, 0, 0, 0).to_key()]), 2)

    def test_no_detector_does_nothing(self):
        dets = {R_cell(0, 0, 0, 0).to_key(): []}
        gather.gather_wedge_rescue(Log(), [_Cell(_img("dot"))], {0: (0, 0)}, dets, detector=None)
        self.assertEqual(dets[R_cell(0, 0, 0, 0).to_key()], [])

    def test_a_cell_with_no_head_is_not_searched(self):
        det = _Detector([_mark()])
        dets = {R_cell(0, 0, 0, 0).to_key(): [_mark(conf=0.9)]}
        gather.gather_wedge_rescue(Log(), [_Cell(_img("wedge_tip_up"))], {0: (0, 0)}, dets, detector=det)
        self.assertEqual(det.calls, [])


if __name__ == "__main__":
    unittest.main()
